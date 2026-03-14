"""
ARGUS Agents — V3 audit state schema (phase-3 aligned).
No add_messages / unbounded list; each node receives only what it needs via typed state.
"""
from typing import TypedDict, Optional, Any


class AuditFinding(TypedDict, total=False):
    id: str
    title: str
    type: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | INFO
    audit_type: str
    description: str
    evidence: str
    context: dict
    risk_score: float
    cis_benchmark: Optional[str]
    remediation: str
    discovered_by: str  # "initial_scan" | "load_context" | hypothesis_id
    reasoning_chain: Optional[list[str]]


class InvestigationRecord(TypedDict):
    hypothesis_id: str
    question: str
    commands_run: list[str]
    result: str
    found_new_finding: bool
    depth: int
    timestamp: str


class AttackPath(TypedDict):
    entry_point: str
    target: str
    path: list[dict]
    composite_risk: float
    findings_involved: list[str]


class AuditStateV3(TypedDict, total=False):
    # Input
    audit_mode: str
    ssh_key_path: str
    aws_region: str
    scope_tag: str
    context_file_path: Optional[str]

    # Auto-discovered or from load_context
    external_targets: list[str]
    internal_targets: list[str]
    jump_box_ip: str
    environment_context: dict[str, Any]

    # Findings
    initial_findings: list[AuditFinding]
    deep_findings: list[AuditFinding]
    all_findings: list[AuditFinding]

    # Intelligence state
    hypotheses: list[dict]
    investigation_log: list[InvestigationRecord]
    attack_paths: list[AttackPath]
    reasoning_chains: list[dict]

    # Budget
    investigation_budget_total: int
    investigation_budget_remaining: int
    investigation_depth_max: int
    tokens_used: int
    token_budget_remaining: int

    # Output
    external_report: str
    executive_summary: str

    # Metadata
    current_phase: str
    phase_progress: float
    audit_types_executed: list[str]
    errors: list[str]
    audit_log: list[dict]
