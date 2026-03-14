"""
ARGUS Agents — V3 graph nodes.
Uses get_llm() from agents.llm.base and SecureToolExecutor for AWS CLI.
"""
import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.config import TOKEN_BUDGET, FAST_MODEL, DEEP_MODEL
from agents.executor import SecureToolExecutor
from agents.graph.checks import (
    resolve_scopes,
    calculate_budget,
    get_active_checks,
    ALL_SCOPES,
)
from agents.graph.state import AuditStateV3, AuditFinding, InvestigationRecord
from agents.llm.base import get_llm


def _parse_json(text: str) -> any:
    """Parse JSON, stripping markdown fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        # drop first line (```json or ```) and last fence line
        inner = "\n".join(lines[1:])
        inner = inner.rstrip("`").rstrip()
        if inner.endswith("```"):
            inner = inner[:-3].rstrip()
        text = inner.strip()
    return json.loads(text)

RECON_PROMPT = """You are an autonomous infrastructure security auditor performing reconnaissance.

Given these inputs:
- AWS Region:  {aws_region}
- Scope tag:   {scope_tag}
- Active scopes: {scopes}

IMPORTANT: Only plan checks relevant to the active scopes.

Produce a JSON audit plan:
{{
    "audit_types_priority": ["most_important_first", ...],
    "initial_hypotheses": [
        "Are there IAM roles that can chain into higher-privilege roles?",
        ...
    ],
    "special_considerations": []
}}

Return ONLY valid JSON, no markdown."""


async def reconnaissance_node(state: AuditStateV3) -> dict[str, Any]:
    """Demo mode: resolve scopes, compute budget, LLM plan, then AWS discovery for jump box and targets."""
    scopes = resolve_scopes(state.get("scopes", ["all"]))
    budget = calculate_budget(scopes, state.get("audit_mode", "demo"))
    scope_tag = state.get("scope_tag", "AuditDemo")
    aws_region = state.get("aws_region", "us-east-1")

    llm = get_llm()
    prompt = RECON_PROMPT.format(
        aws_region=aws_region,
        scope_tag=scope_tag,
        scopes=", ".join(scopes),
    )
    try:
        reply = await llm.complete([{"role": "user", "content": prompt}], model=FAST_MODEL, max_tokens=800)
        plan = _parse_json(reply) if reply and reply.strip() else {}
    except (json.JSONDecodeError, Exception):
        plan = {"audit_types_priority": list(scopes), "initial_hypotheses": [], "special_considerations": []}
    audit_types = plan.get("audit_types_priority", list(scopes))
    initial_hypotheses = [
        {
            "id": f"recon_hyp_{i}",
            "question": q,
            "status": "pending",
            "priority": 0.75,
            "triggered_by": "reconnaissance",
            "audit_type": audit_types[0] if audit_types else "general",
            "depth": 0,
        }
        for i, q in enumerate(plan.get("initial_hypotheses", []))
    ]

    # AWS discovery: jump box and targets by tag
    executor = SecureToolExecutor()
    jump_box_ip = ""
    external_targets: list[str] = []
    internal_targets: list[str] = []

    jb_cmd = (
        "aws ec2 describe-instances "
        "--filters \"Name=tag:Name,Values=audit-jumpbox\" \"Name=instance-state-name,Values=running\" "
        "--query \"Reservations[0].Instances[0].PublicIpAddress\" --output text"
    )
    ext_cmd = (
        "aws ec2 describe-instances "
        f"--filters \"Name=tag:{scope_tag},Values={scope_tag}\" \"Name=instance-state-name,Values=running\" "
        "--query \"Reservations[].Instances[?PublicIpAddress].PublicIpAddress\" --output text"
    )
    int_cmd = (
        "aws ec2 describe-instances "
        f"--filters \"Name=tag:{scope_tag},Values={scope_tag}\" \"Name=instance-state-name,Values=running\" "
        "--query \"Reservations[].Instances[?!PublicIpAddress].PrivateIpAddress\" --output text"
    )
    jb_result, ext_result, int_result = await asyncio.gather(
        executor.execute(jb_cmd, timeout=15),
        executor.execute(ext_cmd, timeout=15),
        executor.execute(int_cmd, timeout=15),
    )
    if jb_result.returncode == 0 and jb_result.stdout.strip() and jb_result.stdout.strip() != "None":
        jump_box_ip = jb_result.stdout.strip()
    if ext_result.returncode == 0 and ext_result.stdout.strip():
        external_targets = [ip for ip in ext_result.stdout.split() if ip and ip != "None"]
    if int_result.returncode == 0 and int_result.stdout.strip():
        internal_targets = [ip for ip in int_result.stdout.split() if ip and ip != "None"]

    tokens_used = 0  # optional: track from LLM response if API provides it
    token_remaining = state.get("token_budget_remaining", TOKEN_BUDGET) - tokens_used

    return {
        "scopes": scopes,
        "jump_box_ip": jump_box_ip,
        "external_targets": external_targets,
        "internal_targets": internal_targets,
        "hypotheses": initial_hypotheses,
        "investigation_budget_total": budget,
        "investigation_budget_remaining": budget,
        "investigation_depth_max": 5,
        "tokens_used": state.get("tokens_used", 0) + tokens_used,
        "token_budget_remaining": token_remaining,
        "audit_types_executed": audit_types,
        "current_phase": "reconnaissance_complete",
        "phase_progress": 0.1,
        "audit_log": state.get("audit_log", []) + [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "reconnaissance_complete",
                "plan": plan,
                "scopes": scopes,
                "budget": budget,
                "jump_box_ip": jump_box_ip,
                "external_targets": external_targets,
                "internal_targets": internal_targets,
            }
        ],
    }


INITIAL_SCAN_PROMPT = """You are an autonomous infrastructure auditor. Analyze the scan results below.

CHECK: {check_name} ({scan_type})
INSTRUCTIONS: {analysis_prompt}

RAW OUTPUT:
{raw_output}

Produce a JSON object:
{{
  "findings": [
    {{
      "id": "scan_N",
      "title": "Short title",
      "type": "security_group_allows_port|iam_role_can_assume_role|nacl_has_deny_rule|monitoring_configured|encryption_disabled|config_drift|other",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "description": "What was found",
      "evidence": "The specific data supporting this",
      "context": {{}},
      "is_suspicious": true,
      "suspicion_reason": "Why this needs deeper investigation"
    }}
  ]
}}

Think like a penetration tester. Flag anything that looks benign but could be dangerous in combination.
Return ONLY valid JSON."""


async def initial_scan_node(state: AuditStateV3) -> dict[str, Any]:
    """Run active discovery checks via SecureToolExecutor; one LLM call per check; merge findings."""
    scopes = state.get("scopes", ALL_SCOPES)
    active_checks = get_active_checks(scopes)
    executor = SecureToolExecutor()
    llm = get_llm()
    all_findings: list[AuditFinding] = []
    total_tokens_used = state.get("tokens_used", 0)

    for check_id, check in active_checks.items():
        cmds = check.get("commands", [])
        results = await asyncio.gather(*(executor.execute(cmd, timeout=15) for cmd in cmds))
        outputs: list[str] = []
        for cmd, result in zip(cmds, results):
            clean = (result.stdout or "").strip()[:3000]
            if result.returncode != 0 and result.stderr:
                clean = f"[stderr] {result.stderr}\n{clean}"
            outputs.append(f"[{cmd}]\n{clean}")

        raw_output = "\n\n".join(outputs)
        prompt = INITIAL_SCAN_PROMPT.format(
            check_name=check["name"],
            scan_type=check.get("type", "general"),
            analysis_prompt=check.get("analysis_prompt", "Analyze for security issues."),
            raw_output=raw_output,
        )
        try:
            reply = await llm.complete(
                [{"role": "user", "content": prompt}],
                model=FAST_MODEL,
                max_tokens=3000,
            )
        except Exception:
            reply = "{}"
        try:
            parsed = _parse_json(reply) if reply and reply.strip() else {}
            for f in parsed.get("findings", []):
                f.setdefault("id", f"scan_{len(all_findings)}")
                f["audit_type"] = check.get("type", "initial_scan")
                f["discovered_by"] = "initial_scan"
                f["risk_score"] = 0.7 if f.get("severity") in ("CRITICAL", "HIGH") else 0.4
                f.setdefault("remediation", "")
                f.setdefault("cis_benchmark", None)
                f.setdefault("reasoning_chain", None)
                f.setdefault("context", {})
                all_findings.append(f)
        except (json.JSONDecodeError, TypeError):
            pass
        total_tokens_used += 1500  # approximate per LLM call

    token_remaining = max(0, TOKEN_BUDGET - total_tokens_used)

    return {
        "initial_findings": all_findings,
        "all_findings": all_findings,
        "tokens_used": total_tokens_used,
        "token_budget_remaining": token_remaining,
        "current_phase": "initial_scan_complete",
        "phase_progress": 0.35,
        "audit_types_executed": list({c.get("type", "general") for c in active_checks.values()}),
        "audit_log": state.get("audit_log", []) + [
            {"timestamp": datetime.utcnow().isoformat(), "event": "initial_scan_complete", "findings_count": len(all_findings)}
        ],
    }


async def load_context_node(state: AuditStateV3) -> dict[str, Any]:
    """Dev mode: read SCAN_CONTEXT from context_file_path (or stub); fill initial_findings and environment_context."""
    context_path = state.get("context_file_path") or "SCAN_CONTEXT.md"
    path = Path(context_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent.parent / context_path
    initial_findings: list[AuditFinding] = []
    external_targets = list(state.get("external_targets", []))
    internal_targets = list(state.get("internal_targets", []))
    jump_box_ip = state.get("jump_box_ip", "")
    try:
        raw = path.read_text()
        for line in raw.splitlines():
            if "EC2 Public" in line or "API Gateway" in line:
                m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
                if m and m.group(1) not in external_targets:
                    external_targets.append(m.group(1))
            if "EC2 Private" in line or "RDS" in line:
                m = re.search(r"\b(10\.\d+\.\d+\.\d+)\b", line)
                if m and m.group(1) not in internal_targets:
                    internal_targets.append(m.group(1))
            if "JumpBox" in line or "jump_box" in line:
                m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
                if m:
                    jump_box_ip = m.group(1)
        anomaly_section = re.search(r"## Observed Anomalies.*?\n(.*?)(?=\n##|\Z)", raw, re.DOTALL)
        if anomaly_section:
            severity_map = {"⚠": "HIGH", "🔴": "CRITICAL", "ℹ": "INFO", "✅": "LOW"}
            for i, line in enumerate(anomaly_section.group(1).splitlines()):
                line = line.strip()
                if not line:
                    continue
                severity = next((v for k, v in severity_map.items() if line.startswith(k)), "MEDIUM")
                initial_findings.append({
                    "id": f"ctx_finding_{i}",
                    "title": line[:80],
                    "type": "general",
                    "severity": severity,
                    "audit_type": "context_import",
                    "description": line,
                    "evidence": f"From {context_path}",
                    "context": {},
                    "risk_score": 0.7 if severity in ("CRITICAL", "HIGH") else 0.4,
                    "cis_benchmark": None,
                    "remediation": "See context file.",
                    "discovered_by": "load_context",
                    "reasoning_chain": None,
                })
    except FileNotFoundError:
        initial_findings = [{
            "id": "ctx_1",
            "title": "No SCAN_CONTEXT.md — using stub",
            "type": "general",
            "severity": "INFO",
            "audit_type": "context_import",
            "description": f"File not found: {path}",
            "evidence": "",
            "context": {},
            "risk_score": 0.0,
            "cis_benchmark": None,
            "remediation": "Run dev scan or add SCAN_CONTEXT.md.",
            "discovered_by": "load_context",
            "reasoning_chain": None,
        }]
    scopes = resolve_scopes(state.get("scopes", ["all"]))
    budget = calculate_budget(scopes, "dev")
    return {
        "scopes": scopes,
        "external_targets": external_targets,
        "internal_targets": internal_targets,
        "jump_box_ip": jump_box_ip,
        "environment_context": {"source": str(path), "raw": ""},
        "initial_findings": initial_findings,
        "all_findings": initial_findings,
        "deep_findings": [],
        "hypotheses": [],
        "investigation_log": [],
        "attack_paths": [],
        "reasoning_chains": [],
        "investigation_budget_total": budget,
        "investigation_budget_remaining": budget,
        "investigation_depth_max": 5,
        "tokens_used": 0,
        "token_budget_remaining": TOKEN_BUDGET,
        "current_phase": "context_loaded",
        "phase_progress": 0.30,
        "audit_types_executed": ["context_import"],
        "errors": [],
        "audit_log": state.get("audit_log", []) + [
            {"timestamp": datetime.utcnow().isoformat(), "event": "context_loaded", "findings_count": len(initial_findings), "source": str(path), "scopes": scopes, "budget": budget},
        ],
    }


# Hypothesis templates by finding type (phase-3); context vars substituted from finding["context"]
HYPOTHESIS_TEMPLATES: dict[str, list[dict]] = {
    "security_group_allows_port": [
        {"question": "Can {src_resource} reach {target_resource} on port {port}? Is there an IAM policy that also grants DB access?", "priority": 0.8, "audit_type": "network"},
    ],
    "iam_role_can_assume_role": [
        {"question": "What is the full assumption chain from {role_name}? Does it reach Secrets Manager?", "priority": 0.9, "audit_type": "iam"},
    ],
    "iam_excessive_permissions": [
        {"question": "The role {role_name} has broad permissions — which EC2 instances use this role? What could they modify?", "priority": 0.85, "audit_type": "iam"},
    ],
    "monitoring_broken": [
        {"question": "The alarm references SNS topic {sns_arn} — does this topic actually exist?", "priority": 0.7, "audit_type": "monitoring", "investigation_commands": ["aws sns get-topic-attributes --topic-arn {sns_arn}"]},
    ],
    "cloudtrail_not_logging": [
        {"question": "CloudTrail is stopped. What does the S3 bucket policy look like? Is it blocking writes?", "priority": 0.8, "audit_type": "monitoring", "investigation_commands": ["aws s3api get-bucket-policy --bucket {bucket_name}"]},
    ],
    "nacl_bypass_via_route": [
        {"question": "NACL denies {denied_cidr} but there may be a route that bypasses it. Check NAT/VPN.", "priority": 0.85, "audit_type": "network"},
    ],
    "encryption_disabled": [
        {"question": "RDS storage is unencrypted. Is there a KMS key available? Check key rotation.", "priority": 0.7, "audit_type": "data", "investigation_commands": ["aws kms list-keys --output json"]},
    ],
    "imds_v1_enabled": [
        {"question": "Instance {instance_id} has IMDSv1 enabled. What IAM role is attached? Could SSRF lead to credential theft?", "priority": 0.8, "audit_type": "compute"},
    ],
    "lambda_wrong_role": [
        {"question": "Lambda {function_name} uses role {wrong_role} — what policies does this role have?", "priority": 0.75, "audit_type": "lambda", "investigation_commands": ["aws iam list-role-policies --role-name {wrong_role}", "aws iam list-attached-role-policies --role-name {wrong_role}"]},
    ],
    "s3_conditional_public": [
        {"question": "Bucket {bucket_name} has Principal=* with a tag condition — what is the public access block config?", "priority": 0.8, "audit_type": "data", "investigation_commands": ["aws s3api get-bucket-policy --bucket {bucket_name}", "aws s3api get-public-access-block --bucket {bucket_name}"]},
    ],
    "kms_rotation_disabled": [
        {"question": "KMS key {key_id} — is key rotation enabled?", "priority": 0.7, "audit_type": "data", "investigation_commands": ["aws kms get-key-rotation-status --key-id {key_id}"]},
    ],
    "userdata_insecure_binding": [
        {"question": "Instance {instance_id} may have insecure user-data. Check for 0.0.0.0 bindings, cron jobs, hardcoded secrets.", "priority": 0.85, "audit_type": "compute", "investigation_commands": ["aws ec2 describe-instance-attribute --instance-id {instance_id} --attribute userData"]},
    ],
    "general": [
        {"question": "What resources are affected by this finding? How could it combine with others?", "priority": 0.6, "audit_type": "general"},
    ],
}

HYPOTHESIS_PROMPT = """You are an autonomous security auditor analyzing findings to generate hypotheses.

CURRENT FINDINGS:
{findings_summary}

ALREADY INVESTIGATED:
{investigated_summary}

Generate 3-5 NEW hypotheses that:
1. Connect dots between multiple findings (composite vulnerabilities)
2. Investigate findings that need deeper commands
3. Look for attack paths (entry point → lateral movement → data access)

For each hypothesis, include what AWS CLI command(s) should be run to investigate it.

Output as JSON array only:
[
  {{"id": "llm_hyp_N", "question": "What happens if...", "priority": 0.9, "triggered_by": "finding_id or llm_reasoning", "audit_type": "scope_name", "investigation_commands": ["aws ec2 describe-instance-attribute --instance-id i-xxx --attribute userData"]}}
]

Return ONLY valid JSON."""


async def hypothesis_generation_node(state: AuditStateV3) -> dict[str, Any]:
    """Template-based hypotheses from finding types + LLM-generated hypotheses; merge and dedupe."""
    all_findings = state.get("all_findings", [])
    existing = state.get("hypotheses", [])
    existing_ids = {h["id"] for h in existing}
    new_hyps: list[dict] = []

    # Template-driven
    for finding in all_findings:
        ftype = finding.get("type", "general")
        context = finding.get("context", {}) or {}
        templates = HYPOTHESIS_TEMPLATES.get(ftype) or HYPOTHESIS_TEMPLATES.get("general", [])
        for idx, tmpl in enumerate(templates):
            hid = f"hyp_{finding.get('id', 'x')}_{ftype}_{idx}"
            if hid in existing_ids:
                continue
            question = tmpl.get("question", "").replace("{{", "{").replace("}}", "}")
            for k, v in context.items():
                question = question.replace(f"{{{k}}}", str(v))
            inv_cmds = list(tmpl.get("investigation_commands", []))
            for k, v in context.items():
                inv_cmds = [c.replace(f"{{{k}}}", str(v)) for c in inv_cmds]
            new_hyps.append({
                "id": hid,
                "question": question or f"What is the impact of: {finding.get('title', '')}?",
                "status": "pending",
                "priority": tmpl.get("priority", 0.6),
                "triggered_by": finding.get("id", ""),
                "audit_type": tmpl.get("audit_type", finding.get("audit_type", "general")),
                "depth": 0,
                "investigation_commands": inv_cmds if inv_cmds else None,
            })
            existing_ids.add(hid)

    # LLM-driven
    if all_findings:
        findings_summary = "\n".join(
            f"[{f.get('id','?')}] [{f.get('severity','INFO')}] {f.get('title','?')} (type={f.get('type','?')})"
            for f in all_findings[:20]
        )
        investigated_summary = "\n".join(
            f"- {h['question']} → {h.get('status','pending')}"
            for h in existing if h.get("status") != "pending"
        ) or "None yet"
        llm = get_llm()
        try:
            reply = await llm.complete(
                [{"role": "user", "content": HYPOTHESIS_PROMPT.format(findings_summary=findings_summary, investigated_summary=investigated_summary)}],
                model=FAST_MODEL,
                max_tokens=2000,
            )
            parsed = _parse_json(reply) if reply and reply.strip() else []
            if isinstance(parsed, list):
                for hyp in parsed:
                    if hyp.get("id") and hyp["id"] not in existing_ids:
                        hyp.setdefault("status", "pending")
                        hyp.setdefault("depth", 0)
                        hyp.setdefault("investigation_commands", hyp.get("investigation_commands", []))
                        new_hyps.append(hyp)
                        existing_ids.add(hyp["id"])
        except (json.JSONDecodeError, TypeError):
            pass

    combined = existing + new_hyps
    return {
        "hypotheses": combined,
        "current_phase": "hypothesis_generation",
        "phase_progress": max(state.get("phase_progress", 0), 0.4),
    }


def _determine_investigation_commands(hypothesis: dict) -> list[str]:
    """Map hypothesis to AWS CLI commands: explicit investigation_commands first, else keyword fallbacks."""
    explicit = hypothesis.get("investigation_commands") or []
    if explicit:
        return [c for c in explicit if isinstance(c, str)][:5]
    question = (hypothesis.get("question") or "").lower()
    commands: list[str] = []
    if "user-data" in question or "userdata" in question or "user data" in question:
        ctx = hypothesis.get("context", {}) or {}
        iid = ctx.get("instance_id", "")
        if iid:
            commands.append(f"aws ec2 describe-instance-attribute --instance-id {iid} --attribute userData")
    if "security group" in question or " sg " in question:
        commands.append("aws ec2 describe-security-groups --output json")
    if "assume" in question or "role" in question or "iam" in question:
        commands.append("aws iam list-roles --output json")
    if "nacl" in question or "route" in question:
        commands.append("aws ec2 describe-network-acls --output json")
        commands.append("aws ec2 describe-route-tables --output json")
    if "sns" in question or "alarm" in question or "cloudwatch" in question:
        commands.append("aws cloudwatch describe-alarms --output json")
        commands.append("aws sns list-topics --output json")
    if "cloudtrail" in question or "logging" in question:
        commands.append("aws cloudtrail get-trail-status --name audit-demo-trail --output json")
    if "s3" in question or "bucket" in question:
        commands.append("aws s3api list-buckets --output json")
    if "kms" in question or "rotation" in question:
        commands.append("aws kms list-keys --output json")
    if "lambda" in question:
        commands.append("aws lambda list-functions --output json")
    if "secret" in question:
        commands.append("aws secretsmanager list-secrets --output json")
    if "imds" in question or "metadata" in question:
        commands.append("aws ec2 describe-instances --query \"Reservations[].Instances[].{Id:InstanceId,MetadataOptions:MetadataOptions}\" --output json")
    if not commands:
        commands = ["aws ec2 describe-instances --output json"]
    return commands[:5]


INVESTIGATION_PROMPT = """You are an autonomous security investigator.

HYPOTHESIS: {hypothesis}

INVESTIGATION COMMANDS AND RESULTS:
{command_outputs}

Analyze thoroughly and produce JSON:
{{
    "hypothesis_status": "confirmed|rejected|inconclusive",
    "evidence_summary": "What the data shows",
    "confidence": 0.0-1.0,
    "new_findings": [
        {{
            "id": "deep_N",
            "title": "Short title",
            "type": "finding_type",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "description": "Full description",
            "evidence": "Raw evidence data",
            "context": {{}},
            "remediation": "How to fix"
        }}
    ],
    "new_questions": ["Follow-up questions that emerged"]
}}

Return ONLY valid JSON."""


async def deep_investigation_node(state: AuditStateV3) -> dict[str, Any]:
    """Pick top pending hypotheses; run commands via executor; LLM analysis; update log and deep_findings."""
    hypotheses = list(state.get("hypotheses", []))
    budget = state.get("investigation_budget_remaining", 0)
    pending = sorted(
        [h for h in hypotheses if h.get("status") == "pending"],
        key=lambda h: h.get("priority", 0),
        reverse=True,
    )
    if not pending or budget <= 0:
        return {"current_phase": "investigation_complete", "investigation_budget_remaining": budget}
    batch_size = min(5, len(pending), budget)
    batch = pending[:batch_size]
    executor = SecureToolExecutor()
    llm = get_llm()
    new_log: list[InvestigationRecord] = list(state.get("investigation_log", []))
    new_deep: list[AuditFinding] = list(state.get("deep_findings", []))
    all_findings = list(state.get("all_findings", []))
    tokens_used = state.get("tokens_used", 0)

    for h in batch:
        commands = _determine_investigation_commands(h)
        results = await asyncio.gather(*(executor.execute(cmd, timeout=15) for cmd in commands))
        outputs: list[str] = []
        for cmd, result in zip(commands, results):
            outputs.append(f"[{cmd}]\n{(result.stdout or '').strip()[:3000]}")
        cmds_run = list(commands)
        command_outputs = "\n\n".join(outputs)

        try:
            reply = await llm.complete(
                [{"role": "user", "content": INVESTIGATION_PROMPT.format(hypothesis=h.get("question", ""), command_outputs=command_outputs)}],
                model=FAST_MODEL,
                max_tokens=3000,
            )
            parsed = _parse_json(reply) if reply and reply.strip() else {}
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        tokens_used += 2000

        h["status"] = parsed.get("hypothesis_status", "inconclusive")
        h["result"] = parsed.get("evidence_summary", "")
        found_new = False
        for i, f in enumerate(parsed.get("new_findings", [])):
            f.setdefault("id", f"deep_{len(new_deep) + i}")
            f["discovered_by"] = h.get("id", "unknown")
            f["audit_type"] = h.get("audit_type", "deep_investigation")
            f.setdefault("risk_score", 0.8 if f.get("severity") in ("CRITICAL", "HIGH") else 0.5)
            f.setdefault("cis_benchmark", None)
            f.setdefault("reasoning_chain", None)
            f.setdefault("context", {})
            new_deep.append(f)
            all_findings.append(f)
            found_new = True
        new_log.append({
            "hypothesis_id": h["id"],
            "question": h.get("question", ""),
            "commands_run": cmds_run,
            "result": h.get("result", ""),
            "found_new_finding": found_new,
            "depth": h.get("depth", 0),
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {
        "hypotheses": hypotheses,
        "investigation_log": new_log,
        "deep_findings": new_deep,
        "all_findings": all_findings,
        "investigation_budget_remaining": max(0, budget - batch_size),
        "tokens_used": tokens_used,
        "token_budget_remaining": max(0, TOKEN_BUDGET - tokens_used),
        "current_phase": "deep_investigation",
        "phase_progress": min(0.7, state.get("phase_progress", 0.4) + 0.05),
    }


def _attack_graph_builder_find_paths(
    nodes: dict[str, dict],
    edges: list[dict],
) -> list[dict]:
    """Build adjacency from edges; DFS from non-critical to critical; return top 10 paths."""
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src and tgt:
            adj[src].append(tgt)
    critical_ids = {nid for nid, n in nodes.items() if n.get("is_critical")}
    paths: list[dict] = []

    def dfs(current: str, path: list[str], visited: set) -> None:
        if current in visited:
            return
        visited.add(current)
        path.append(current)
        if current in critical_ids and len(path) > 1:
            path_findings = []
            for i in range(len(path) - 1):
                for e in edges:
                    if e.get("source") == path[i] and e.get("target") == path[i + 1]:
                        path_findings.append(e.get("finding_id", ""))
            paths.append({
                "entry_point": path[0],
                "target": current,
                "path": [{"node": n, "name": nodes.get(n, {}).get("name", n)} for n in path],
                "composite_risk": min(1.0, 0.3 * len(path)),
                "findings_involved": path_findings,
            })
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                dfs(neighbor, list(path), visited)
        visited.discard(current)

    for nid, node in nodes.items():
        if not node.get("is_critical"):
            dfs(nid, [], set())
    return paths[:10]


ATTACK_GRAPH_PROMPT = """You are building an attack graph from security findings.

FINDINGS:
{findings_json}

Identify attack paths — sequences of findings that, when chained, create a path from an entry point to a critical asset (secrets, databases, admin roles).

Output JSON:
{{
  "nodes": [
    {{"id": "resource_id", "type": "ec2|iam_role|rds|s3|lambda|secret", "name": "human name", "is_critical": false}}
  ],
  "edges": [
    {{"source": "id1", "target": "id2", "relationship": "can_assume|can_reach|has_access", "finding_id": "scan_N"}}
  ]
}}

Return ONLY valid JSON."""


async def attack_graph_node(state: AuditStateV3) -> dict[str, Any]:
    """LLM builds nodes/edges from findings; then DFS to find critical paths."""
    all_findings = state.get("all_findings", [])
    llm = get_llm()
    findings_json = json.dumps(all_findings[:30], indent=2)
    try:
        reply = await llm.complete(
            [{"role": "user", "content": ATTACK_GRAPH_PROMPT.format(findings_json=findings_json)}],
            model=DEEP_MODEL,
            max_tokens=3000,
        )
        data = _parse_json(reply) if reply and reply.strip() else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    nodes = {n["id"]: n for n in data.get("nodes", []) if n.get("id")}
    edges = data.get("edges", [])
    paths = _attack_graph_builder_find_paths(nodes, edges)
    if not paths and all_findings:
        for f in all_findings[:5]:
            if f.get("severity") in ("CRITICAL", "HIGH"):
                paths.append({
                    "entry_point": "entry",
                    "target": f.get("id", "unknown"),
                    "path": [{"node": f.get("id", ""), "name": f.get("title", "")}],
                    "composite_risk": f.get("risk_score", 0.5),
                    "findings_involved": [f.get("id", "")],
                })
    return {
        "attack_paths": paths,
        "current_phase": "attack_graph_complete",
        "phase_progress": 0.8,
    }


REASONING_PROMPT = """You are a senior security analyst performing deep reasoning on audit findings.

CRITICAL/HIGH FINDINGS:
{critical_findings}

ATTACK PATHS:
{attack_paths}

For each critical finding, produce a reasoning chain:
1. What was observed (evidence)
2. Why it matters (impact)
3. How it connects to other findings (composite risk)
4. What an attacker could do (exploit scenario)
5. Severity justification

Output JSON:
{{
  "reasoning_chains": [
    {{
      "finding_id": "scan_N",
      "steps": ["Step 1: ...", "Step 2: ..."],
      "conclusion": "This finding combined with X creates Y risk",
      "severity_justification": "Why CRITICAL/HIGH",
      "composite_risk_score": 0.9
    }}
  ],
  "executive_summary": "2-3 sentence summary for executives"
}}

Return ONLY valid JSON."""


async def reasoning_node(state: AuditStateV3) -> dict[str, Any]:
    """DEEP_MODEL: reasoning chains for CRITICAL/HIGH findings and executive summary."""
    all_findings = state.get("all_findings", [])
    attack_paths = state.get("attack_paths", [])
    critical_findings = [f for f in all_findings if f.get("severity") in ("CRITICAL", "HIGH")][:15]
    llm = get_llm()
    try:
        reply = await llm.complete(
            [{
                "role": "user",
                "content": REASONING_PROMPT.format(
                    critical_findings=json.dumps(critical_findings, indent=2),
                    attack_paths=json.dumps(attack_paths[:5], indent=2),
                ),
            }],
            model=DEEP_MODEL,
            max_tokens=4000,
        )
        data = _parse_json(reply) if reply and reply.strip() else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    reasoning_chains = data.get("reasoning_chains", [])
    executive_summary = data.get("executive_summary", "")
    if not reasoning_chains and critical_findings:
        reasoning_chains = [
            {
                "finding_id": f.get("id", ""),
                "steps": [f"Discovered: {f.get('title', '')}", "Requires remediation."],
                "conclusion": f"{f.get('severity', 'HIGH')} finding.",
                "severity_justification": "See finding.",
                "composite_risk_score": f.get("risk_score", 0.5),
            }
            for f in critical_findings[:5]
        ]
    return {
        "reasoning_chains": reasoning_chains,
        "executive_summary": executive_summary,
        "current_phase": "reasoning_complete",
        "phase_progress": 0.9,
    }


REPORT_PROMPT = """You are generating a professional infrastructure security audit report.

AUDIT SUMMARY:
- Total findings: {total_findings}
- Critical: {critical_count}
- High: {high_count}
- Medium: {medium_count}
- Low: {low_count}
- Attack paths identified: {attack_path_count}

EXECUTIVE SUMMARY:
{executive_summary}

ALL FINDINGS:
{findings_json}

ATTACK PATHS:
{attack_paths_json}

REASONING CHAINS:
{reasoning_json}

Generate a complete Markdown report with these sections:
1. Executive Summary (2-3 paragraphs)
2. Critical Findings (detailed, with evidence and remediation)
3. High-Priority Findings
4. Medium/Low Findings (summarized)
5. Attack Path Analysis (visual chains using arrows)
6. Recommendations (prioritized action items)
7. Methodology (what was checked)

Make it professional but readable. Include specific resource IDs and evidence."""


async def report_generation_node(state: AuditStateV3) -> dict[str, Any]:
    """DEEP_MODEL: full markdown report from findings, attack paths, reasoning chains."""
    all_findings = state.get("all_findings", [])
    attack_paths = state.get("attack_paths", [])
    reasoning_chains = state.get("reasoning_chains", [])
    executive_summary = state.get("executive_summary", "")
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in all_findings:
        sev = f.get("severity", "INFO")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    llm = get_llm()
    try:
        report = await llm.complete(
            [{
                "role": "user",
                "content": REPORT_PROMPT.format(
                    total_findings=len(all_findings),
                    critical_count=severity_counts["CRITICAL"],
                    high_count=severity_counts["HIGH"],
                    medium_count=severity_counts["MEDIUM"],
                    low_count=severity_counts["LOW"],
                    attack_path_count=len(attack_paths),
                    executive_summary=executive_summary,
                    findings_json=json.dumps(all_findings, indent=2),
                    attack_paths_json=json.dumps(attack_paths, indent=2),
                    reasoning_json=json.dumps(reasoning_chains, indent=2),
                ),
            }],
            model=DEEP_MODEL,
            max_tokens=8000,
        )
    except Exception:
        report = "# ARGUS Audit Report\n\n## Executive Summary\n\nPipeline complete; LLM report generation failed.\n\n## Findings\n\nSee state for details."
    summary = (state.get("executive_summary") or report[:500] or "") + ("..." if len(report) > 500 else "")
    return {
        "external_report": report,
        "executive_summary": summary,
        "current_phase": "complete",
        "phase_progress": 1.0,
    }
