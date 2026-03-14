"""
ARGUS Agents — V3 graph nodes (stub/minimal implementations).
All use get_llm() from agents.llm.base; real logic and SecureToolExecutor are follow-ups.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.config import INVESTIGATION_BUDGET, TOKEN_BUDGET, FAST_MODEL, DEEP_MODEL
from agents.graph.state import AuditStateV3, AuditFinding, InvestigationRecord
from agents.llm.base import get_llm


async def reconnaissance_node(state: AuditStateV3) -> dict[str, Any]:
    """Build audit plan from targets; call LLM; return state with audit_types_executed, budget, initial hypotheses."""
    llm = get_llm()
    prompt = f"""You are an infrastructure security auditor. Given targets:
- External: {state.get('external_targets', [])}
- Internal: {state.get('internal_targets', [])}
- Jump box: {state.get('jump_box_ip', 'N/A')}

Produce a JSON object with: "audit_types_priority" (array of 2-3 types), "initial_hypotheses" (array of 1-2 questions).
Return ONLY valid JSON."""
    try:
        reply = await llm.complete([{"role": "user", "content": prompt}], model=FAST_MODEL, max_tokens=800)
        plan = json.loads(reply) if reply.strip() else {}
    except (json.JSONDecodeError, Exception):
        plan = {"audit_types_priority": ["iam_privilege", "network_segmentation"], "initial_hypotheses": []}
    audit_types = plan.get("audit_types_priority", ["iam_privilege", "network_segmentation"])
    initial_hypotheses = [
        {"id": f"recon_hyp_{i}", "question": q, "status": "pending", "priority": 0.75, "triggered_by": "reconnaissance", "audit_type": audit_types[0] if audit_types else "general", "depth": 0}
        for i, q in enumerate(plan.get("initial_hypotheses", []))
    ]
    return {
        "audit_types_executed": audit_types,
        "investigation_budget_total": INVESTIGATION_BUDGET,
        "investigation_budget_remaining": INVESTIGATION_BUDGET,
        "investigation_depth_max": 5,
        "token_budget_remaining": state.get("token_budget_remaining", TOKEN_BUDGET),
        "hypotheses": initial_hypotheses,
        "current_phase": "reconnaissance_complete",
        "phase_progress": 0.1,
        "audit_log": state.get("audit_log", []) + [{"timestamp": datetime.utcnow().isoformat(), "event": "reconnaissance_complete", "plan": plan}],
    }


async def initial_scan_node(state: AuditStateV3) -> dict[str, Any]:
    """Stub: produce a few mock initial_findings. Later: ACTIVE_CHECKS + SecureToolExecutor."""
    mock_findings: list[AuditFinding] = [
        {
            "id": "scan_1",
            "title": "Mock finding (stub)",
            "type": "general",
            "severity": "LOW",
            "audit_type": "initial_scan",
            "description": "Stub initial scan — wire real checks later.",
            "evidence": "",
            "context": {},
            "risk_score": 0.3,
            "cis_benchmark": None,
            "remediation": "",
            "discovered_by": "initial_scan",
            "reasoning_chain": None,
        }
    ]
    return {
        "initial_findings": mock_findings,
        "all_findings": mock_findings,
        "current_phase": "initial_scan_complete",
        "phase_progress": 0.35,
        "audit_log": state.get("audit_log", []) + [{"timestamp": datetime.utcnow().isoformat(), "event": "initial_scan_complete", "findings_count": len(mock_findings)}],
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
    return {
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
        "investigation_budget_total": INVESTIGATION_BUDGET,
        "investigation_budget_remaining": INVESTIGATION_BUDGET,
        "investigation_depth_max": 5,
        "tokens_used": 0,
        "token_budget_remaining": TOKEN_BUDGET,
        "current_phase": "context_loaded",
        "phase_progress": 0.30,
        "audit_types_executed": ["context_import"],
        "errors": [],
        "audit_log": state.get("audit_log", []) + [{"timestamp": datetime.utcnow().isoformat(), "event": "context_loaded", "findings_count": len(initial_findings), "source": str(path)}],
    }


async def hypothesis_generation_node(state: AuditStateV3) -> dict[str, Any]:
    """From all_findings generate/update hypotheses (template-based and/or one LLM call)."""
    all_findings = state.get("all_findings", [])
    existing = state.get("hypotheses", [])
    existing_ids = {h["id"] for h in existing}
    new_hyps = []
    for f in all_findings:
        if f.get("type") in ("security_group_allows_port", "iam_role_can_assume_role", "general"):
            hid = f"hyp_{f.get('id', 'x')}_1"
            if hid not in existing_ids:
                new_hyps.append({
                    "id": hid,
                    "question": f"What resources are affected by: {f.get('title', '')}?",
                    "triggered_by": f.get("id", ""),
                    "audit_type": f.get("audit_type", "general"),
                    "priority": 0.6,
                    "status": "pending",
                    "depth": 0,
                })
                existing_ids.add(hid)
    combined = existing + new_hyps
    return {
        "hypotheses": combined,
        "current_phase": "hypothesis_generation",
        "phase_progress": max(state.get("phase_progress", 0), 0.4),
    }


async def deep_investigation_node(state: AuditStateV3) -> dict[str, Any]:
    """Pick top N pending hypotheses; stub investigate; append investigation_log and deep_findings; decrement budget."""
    hypotheses = list(state.get("hypotheses", []))
    budget = state.get("investigation_budget_remaining", 0)
    pending = sorted([h for h in hypotheses if h.get("status") == "pending"], key=lambda h: h.get("priority", 0), reverse=True)
    if not pending or budget <= 0:
        return {"current_phase": "investigation_complete", "investigation_budget_remaining": budget}
    batch_size = min(2, len(pending), budget)
    batch = pending[:batch_size]
    new_log: list[InvestigationRecord] = list(state.get("investigation_log", []))
    new_deep: list[AuditFinding] = list(state.get("deep_findings", []))
    for h in batch:
        h["status"] = "rejected"
        h["result"] = "Stub investigation — no real commands run."
        new_log.append({
            "hypothesis_id": h["id"],
            "question": h.get("question", ""),
            "commands_run": [],
            "result": "Stub",
            "found_new_finding": False,
            "depth": h.get("depth", 0),
            "timestamp": datetime.utcnow().isoformat(),
        })
    return {
        "hypotheses": hypotheses,
        "investigation_log": new_log,
        "deep_findings": new_deep,
        "investigation_budget_remaining": max(0, budget - batch_size),
        "current_phase": "deep_investigation",
        "phase_progress": max(state.get("phase_progress", 0), 0.6),
    }


async def attack_graph_node(state: AuditStateV3) -> dict[str, Any]:
    """From findings build a simple attack_paths list (and optionally Mermaid)."""
    all_findings = state.get("all_findings", [])
    paths = []
    for f in all_findings[:5]:
        if f.get("severity") in ("CRITICAL", "HIGH"):
            paths.append({
                "entry_point": "stub",
                "target": f.get("id", "unknown"),
                "path": [{"from": "stub", "to": f.get("id", ""), "via": f.get("type", "related")}],
                "composite_risk": f.get("risk_score", 0.5),
                "findings_involved": [f.get("id", "")],
            })
    return {
        "attack_paths": paths,
        "current_phase": "attack_graph_complete",
        "phase_progress": 0.8,
    }


async def reasoning_node(state: AuditStateV3) -> dict[str, Any]:
    """For CRITICAL/HIGH findings call LLM to produce reasoning_chains."""
    all_findings = state.get("all_findings", [])
    critical = [f for f in all_findings if f.get("severity") in ("CRITICAL", "HIGH")][:5]
    chains = []
    for f in critical:
        chains.append({
            "finding_id": f.get("id", ""),
            "reasoning_steps": [f"Discovered: {f.get('title', '')}", "Stub reasoning — wire LLM for full V3."],
            "conclusion": f"{f.get('severity', 'HIGH')} finding requires attention.",
            "severity": f.get("severity", "HIGH"),
        })
    return {
        "reasoning_chains": chains,
        "current_phase": "reasoning_complete",
        "phase_progress": 0.9,
    }


async def report_generation_node(state: AuditStateV3) -> dict[str, Any]:
    """Single LLM call to produce external_report and executive_summary."""
    llm = get_llm()
    all_findings = state.get("all_findings", [])
    attack_paths = state.get("attack_paths", [])
    prompt = f"""You are a security auditor. Write a very short audit report (2-3 paragraphs) based on:
Findings count: {len(all_findings)}
Attack paths count: {len(attack_paths)}
Severity breakdown: {json.dumps([f.get('severity') for f in all_findings])}

Include an "Executive Summary" section and a "Findings" section. Use markdown."""
    try:
        report = await llm.complete([{"role": "user", "content": prompt}], model=DEEP_MODEL, max_tokens=1500)
    except Exception:
        report = "# ARGUS Audit Report\n\n## Executive Summary\n\nStub report — pipeline wired; LLM may have failed.\n\n## Findings\n\nSee state for details."
    summary = report[:500] + "..." if len(report) > 500 else report
    return {
        "external_report": report,
        "executive_summary": summary,
        "current_phase": "complete",
        "phase_progress": 1.0,
    }
