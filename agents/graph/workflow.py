"""
ARGUS Agents — V3 LangGraph workflow: build graph, conditional edge, entrypoint.
Node implementations live in graph/nodes/; this module composes them.
"""
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.config import IS_DEMO_MODE, INVESTIGATION_BUDGET, TOKEN_BUDGET, logger
from agents.graph.state import AuditStateV3


def should_investigate_deeper(state: AuditStateV3) -> str:
    """
    Phase-3: (1) budget/tokens exhausted → correlate; (2) no pending high-priority → correlate;
    (3) last 3 investigations found nothing → correlate. Otherwise investigate.
    """
    budget = state.get("investigation_budget_remaining", 0)
    tokens = state.get("token_budget_remaining", 0)
    hyps = state.get("hypotheses", [])
    inv_log = state.get("investigation_log", [])

    if budget <= 2 or tokens <= 3_000:
        return "correlate"
    pending_high = [h for h in hyps if h.get("status") == "pending" and h.get("priority", 0) > 0.5]
    if not pending_high:
        return "correlate"
    recent = inv_log[-3:] if len(inv_log) >= 3 else inv_log
    if len(recent) == 3 and all(not r.get("found_new_finding") for r in recent):
        return "correlate"
    return "investigate"


def build_v3_graph():
    """Build compiled V3 graph. Entry = recon+initial_scan (demo) or load_context (dev)."""
    from agents.graph import nodes

    graph = StateGraph(AuditStateV3)

    graph.add_node("hypothesis_generation", nodes.hypothesis_generation_node)
    graph.add_node("deep_investigation", nodes.deep_investigation_node)
    graph.add_node("attack_graph", nodes.attack_graph_node)
    graph.add_node("reasoning", nodes.reasoning_node)
    graph.add_node("report_generation", nodes.report_generation_node)

    if IS_DEMO_MODE:
        graph.add_node("reconnaissance", nodes.reconnaissance_node)
        graph.add_node("initial_scan", nodes.initial_scan_node)
        graph.set_entry_point("reconnaissance")
        graph.add_edge("reconnaissance", "initial_scan")
        graph.add_edge("initial_scan", "hypothesis_generation")
    else:
        graph.add_node("load_context", nodes.load_context_node)
        graph.set_entry_point("load_context")
        graph.add_edge("load_context", "hypothesis_generation")

    graph.add_conditional_edges(
        "hypothesis_generation",
        should_investigate_deeper,
        {"investigate": "deep_investigation", "correlate": "attack_graph"},
    )
    graph.add_edge("deep_investigation", "hypothesis_generation")
    graph.add_edge("attack_graph", "reasoning")
    graph.add_edge("reasoning", "report_generation")
    graph.add_edge("report_generation", END)

    return graph.compile(checkpointer=MemorySaver())


async def run_audit_graph(audit_id: str, body: dict[str, Any], events_append: callable) -> dict[str, Any] | None:
    """
    Build initial AuditStateV3 from body, run the compiled graph, push updates to events_append.
    events_append(audit_id, event_dict) is called for each phase/finding/complete.
    Returns final state on success for the caller to store (status/report endpoints); None on error.
    """
    from agents.config import AUDIT_MODE, INVESTIGATION_BUDGET, TOKEN_BUDGET

    initial: AuditStateV3 = {
        "audit_mode": AUDIT_MODE,
        "ssh_key_path": body.get("ssh_key_path", ""),
        "aws_region": body.get("aws_region", "us-east-1"),
        "scope_tag": body.get("scope_tag", "AuditDemo"),
        "scopes": body.get("scopes", ["all"]),
        "context_file_path": body.get("context_file_path"),
        "external_targets": body.get("external_targets", []),
        "internal_targets": body.get("internal_targets", []),
        "jump_box_ip": body.get("jump_box_ip", ""),
        "environment_context": body.get("environment_context", {}),
        "initial_findings": [],
        "deep_findings": [],
        "all_findings": [],
        "hypotheses": [],
        "investigation_log": [],
        "attack_paths": [],
        "reasoning_chains": [],
        "investigation_budget_total": INVESTIGATION_BUDGET,
        "investigation_budget_remaining": INVESTIGATION_BUDGET,
        "investigation_depth_max": 5,
        "tokens_used": 0,
        "token_budget_remaining": TOKEN_BUDGET,
        "external_report": "",
        "executive_summary": "",
        "current_phase": "initialization",
        "phase_progress": 0.0,
        "audit_types_executed": [],
        "errors": [],
        "audit_log": [],
    }

    compiled = build_v3_graph()
    config = {"configurable": {"thread_id": audit_id}}

    logger.info("graph run started audit_id=%s mode=%s", audit_id, initial.get("audit_mode"))

    try:
        final_state = None
        async for state in compiled.astream(initial, config=config, stream_mode="values"):
            final_state = state
            phase = state.get("current_phase", "")
            progress = state.get("phase_progress")
            logger.info("graph phase audit_id=%s phase=%s progress=%s", audit_id, phase, progress)
            events_append(audit_id, {
                "type": "phase_update",
                "phase": phase,
                "progress": progress,
            })
        if final_state is not None:
            events_append(audit_id, {"type": "complete", "state": final_state})
        logger.info("graph run completed audit_id=%s", audit_id)
        return final_state
    except Exception as e:
        logger.exception("graph run error audit_id=%s", audit_id)
        events_append(audit_id, {"type": "error", "error": str(e)})
        return None
