"""
ARGUS Agents — FastAPI app: audit start, SSE stream, report, and data endpoints.
"""
import asyncio
import json
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.config import ORIGINS, get_required_api_key, logger, AUDIT_MODE, INVESTIGATION_BUDGET
from agents.graph.workflow import run_audit_graph

app = FastAPI(
    title="ARGUS Agents API",
    version="0.2.0",
    description="Audit start, stream, report, and intelligence data endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
_audits: dict[str, dict[str, Any]] = {}
_audit_events: dict[str, list[dict[str, Any]]] = {}

# Static scope definitions
SCOPE_DEFINITIONS = {
    "iam": {"label": "IAM", "description": "Roles, policies, privilege escalation chains", "budget_weight": 4, "vuln_count": 4},
    "network": {"label": "Network", "description": "Security groups, NACLs, route tables", "budget_weight": 4, "vuln_count": 5},
    "compute": {"label": "Compute", "description": "EC2 instances, user data, metadata", "budget_weight": 3, "vuln_count": 5},
    "monitoring": {"label": "Monitoring", "description": "CloudWatch, CloudTrail, Flow Logs", "budget_weight": 3, "vuln_count": 4},
    "data": {"label": "Data", "description": "RDS, S3, KMS, Secrets Manager", "budget_weight": 3, "vuln_count": 4},
    "ssh": {"label": "SSH", "description": "Jump box access, process inspection", "budget_weight": 5, "vuln_count": 3},
}


class AuditStartRequest(BaseModel):
    """Body for POST /api/audit/start."""
    external_targets: list[str] = Field(default_factory=list)
    internal_targets: list[str] = Field(default_factory=list)
    jump_box_ip: str = ""
    ssh_key_path: str = ""
    environment_context: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str] = Field(default=["iam", "compute", "monitoring"])
    region: str = Field(default="us-east-1")
    scope_tag: str = Field(default="AuditDemo")
    context_file_path: Optional[str] = None


class AuditStartResponse(BaseModel):
    audit_id: str
    stream_url: str
    status_url: str
    report_url: str


@app.get("/health")
async def health():
    try:
        get_required_api_key()
    except ValueError:
        pass
    return {"status": "ok", "service": "argus-agents"}


@app.get("/api/scopes")
async def get_scopes():
    """Return static scope definitions with budget weights and vuln counts."""
    return {"scopes": SCOPE_DEFINITIONS}


@app.post("/api/audit/start", response_model=AuditStartResponse)
async def start_audit(body: AuditStartRequest, background_tasks: BackgroundTasks):
    """Start a new audit. Returns audit_id and URLs for stream/report."""
    audit_id = str(uuid.uuid4())
    logger.info(
        "audit start audit_id=%s mode=%s scopes=%s context_file=%s",
        audit_id, AUDIT_MODE, body.scopes, getattr(body, "context_file_path", None),
    )
    _audits[audit_id] = {
        "config": body.model_dump(),
        "phase": "starting",
        "progress": 0.0,
        "findings": [],
        "hypotheses": [],
        "attack_paths": [],
        "reasoning_chains": [],
        "audit_log": [],
        "report": None,
        "finished": False,
        "cancelled": False,
    }
    _audit_events[audit_id] = []

    def append_event(aid: str, ev: dict) -> None:
        _audit_events[aid].append(ev)

    async def run():
        try:
            logger.info("audit run started audit_id=%s", audit_id)
            body_dict = body.model_dump()
            # Map region -> aws_region for state schema
            body_dict["aws_region"] = body_dict.pop("region", "us-east-1")
            final = await run_audit_graph(audit_id, body_dict, append_event)
            if final:
                _audits[audit_id]["phase"] = final.get("current_phase", "complete")
                _audits[audit_id]["progress"] = final.get("phase_progress", 1.0)
                _audits[audit_id]["findings"] = final.get("all_findings", [])
                _audits[audit_id]["hypotheses"] = final.get("hypotheses", [])
                _audits[audit_id]["attack_paths"] = final.get("attack_paths", [])
                _audits[audit_id]["reasoning_chains"] = final.get("reasoning_chains", [])
                _audits[audit_id]["audit_log"] = final.get("audit_log", [])
                _audits[audit_id]["report"] = final.get("external_report") or final.get("executive_summary", "")
                logger.info(
                    "audit run finished audit_id=%s phase=%s findings=%s",
                    audit_id, final.get("current_phase"), len(final.get("all_findings", [])),
                )
            else:
                logger.warning("audit run finished with no final state audit_id=%s", audit_id)
            _audits[audit_id]["finished"] = True
        except Exception as e:
            logger.exception("audit run error audit_id=%s", audit_id)
            append_event(audit_id, {"type": "error", "error": str(e)})
            _audits[audit_id]["phase"] = "error"
            _audits[audit_id]["finished"] = True

    background_tasks.add_task(run)

    return AuditStartResponse(
        audit_id=audit_id,
        stream_url=f"/api/audit/{audit_id}/stream",
        status_url=f"/api/audit/{audit_id}/status",
        report_url=f"/api/audit/{audit_id}/report",
    )


@app.get("/api/audit/{audit_id}/stream")
async def stream_audit(audit_id: str):
    """SSE stream for audit progress."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")

    async def event_stream():
        seen = 0
        heartbeat_counter = 0
        while True:
            events = _audit_events.get(audit_id, [])
            for i in range(seen, len(events)):
                yield f"data: {json.dumps(events[i])}\n\n"
            seen = len(events)

            # Heartbeat every ~15s (60 * 0.25s sleeps)
            heartbeat_counter += 1
            if heartbeat_counter >= 60:
                yield ": heartbeat\n\n"
                heartbeat_counter = 0

            if _audits.get(audit_id, {}).get("finished"):
                break
            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/audit/{audit_id}/status")
async def audit_status(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    s = _audits[audit_id]
    return {
        "audit_id": audit_id,
        "phase": s.get("phase", "unknown"),
        "progress": s.get("progress", 0.0),
        "finished": s.get("finished", False),
        "cancelled": s.get("cancelled", False),
        "findings_count": len(s.get("findings", [])),
    }


@app.get("/api/audit/{audit_id}/report")
async def audit_report(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    s = _audits[audit_id]
    if not s.get("finished"):
        raise HTTPException(status_code=202, detail="Audit not finished")
    report = s.get("report") or "# ARGUS Audit Report\n\n(Pipeline completed — no report generated.)"
    return {"audit_id": audit_id, "report": report}


@app.get("/api/audit/{audit_id}/findings")
async def audit_findings(
    audit_id: str,
    severity: Optional[str] = Query(None),
    audit_type: Optional[str] = Query(None),
):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    findings = _audits[audit_id].get("findings", [])
    if severity:
        findings = [f for f in findings if f.get("severity", "").upper() == severity.upper()]
    if audit_type:
        findings = [f for f in findings if f.get("audit_type", "") == audit_type]
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "INFO"), 5))
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in _audits[audit_id].get("findings", []):
        sev = f.get("severity", "INFO").lower()
        if sev in summary:
            summary[sev] += 1
    return {"findings": findings, "total": len(findings), "severity_summary": summary}


@app.get("/api/audit/{audit_id}/hypotheses")
async def audit_hypotheses(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    hypotheses = _audits[audit_id].get("hypotheses", [])
    summary = {"pending": 0, "investigating": 0, "confirmed": 0, "rejected": 0, "inconclusive": 0}
    for h in hypotheses:
        status = h.get("status", "pending")
        if status in summary:
            summary[status] += 1
    return {"hypotheses": hypotheses, "total": len(hypotheses), "summary": summary}


@app.get("/api/audit/{audit_id}/attack-paths")
async def audit_attack_paths(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    paths = _audits[audit_id].get("attack_paths", [])
    return {"attack_paths": paths, "total": len(paths)}


@app.get("/api/audit/{audit_id}/logs")
async def audit_logs(
    audit_id: str,
    limit: int = Query(100),
    offset: int = Query(0),
):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    logs = _audits[audit_id].get("audit_log", [])
    page = logs[offset: offset + limit]
    return {"logs": page, "total": len(logs)}


@app.post("/api/audit/{audit_id}/cancel")
async def cancel_audit(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    _audits[audit_id]["cancelled"] = True
    _audits[audit_id]["finished"] = True
    _audit_events[audit_id].append({"type": "cancelled"})
    return {"status": "cancelled", "audit_id": audit_id}
