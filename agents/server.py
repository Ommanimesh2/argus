"""
ARGUS Agents — FastAPI app: audit start, SSE stream, report.
API-first; LangGraph V3 pipeline wired behind these endpoints.
"""
import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.config import ORIGINS, get_required_api_key
from agents.graph.workflow import run_audit_graph

app = FastAPI(
    title="ARGUS Agents API",
    version="0.1.0",
    description="Audit start, stream, and report endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (replace with DB when needed)
_audits: dict[str, dict[str, Any]] = {}
_audit_events: dict[str, list[dict[str, Any]]] = {}


class AuditStartRequest(BaseModel):
    """Body for POST /api/audit/start."""
    external_targets: list[str] = Field(default_factory=list)
    internal_targets: list[str] = Field(default_factory=list)
    jump_box_ip: str = ""
    ssh_key_path: str = ""
    environment_context: dict[str, Any] = Field(default_factory=dict)


class AuditStartResponse(BaseModel):
    audit_id: str
    stream_url: str
    status_url: str
    report_url: str


@app.get("/health")
async def health():
    """Liveness/readiness."""
    try:
        get_required_api_key()
    except ValueError:
        pass  # optional: fail health if no key
    return {"status": "ok", "service": "argus-agents"}


@app.post("/api/audit/start", response_model=AuditStartResponse)
async def start_audit(body: AuditStartRequest, background_tasks: BackgroundTasks):
    """Start a new audit. Returns audit_id and URLs for stream/report."""
    audit_id = str(uuid.uuid4())
    _audits[audit_id] = {
        "config": body.model_dump(),
        "phase": "starting",
        "progress": 0.0,
        "findings": [],
        "report": None,
        "finished": False,
    }
    _audit_events[audit_id] = []

    def append_event(aid: str, ev: dict) -> None:
        _audit_events[aid].append(ev)

    async def run():
        try:
            body_dict = body.model_dump()
            final = await run_audit_graph(audit_id, body_dict, append_event)
            if final:
                _audits[audit_id]["phase"] = final.get("current_phase", "complete")
                _audits[audit_id]["progress"] = final.get("phase_progress", 1.0)
                _audits[audit_id]["findings"] = final.get("all_findings", [])
                _audits[audit_id]["report"] = final.get("external_report") or final.get("executive_summary", "")
                _audits[audit_id]["attack_paths"] = final.get("attack_paths", [])
            _audits[audit_id]["finished"] = True
        except Exception as e:
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
    """SSE stream for audit progress. Events: phase_update, finding, complete."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")

    async def event_stream():
        seen = 0
        while True:
            events = _audit_events.get(audit_id, [])
            for i in range(seen, len(events)):
                yield f"data: {json.dumps(events[i])}\n\n"
            seen = len(events)
            if _audits.get(audit_id, {}).get("finished"):
                yield "data: {\"type\": \"complete\"}\n\n"
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
    """Current phase and progress."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    s = _audits[audit_id]
    return {
        "audit_id": audit_id,
        "phase": s.get("phase", "unknown"),
        "progress": s.get("progress", 0.0),
        "finished": s.get("finished", False),
        "findings_count": len(s.get("findings", [])),
    }


@app.get("/api/audit/{audit_id}/report")
async def audit_report(audit_id: str):
    """Final report (markdown or JSON). 202 if not finished."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    s = _audits[audit_id]
    if not s.get("finished"):
        raise HTTPException(status_code=202, detail="Audit not finished")
    report = s.get("report") or "# ARGUS Audit Report\n\n(Stub — pipeline not yet wired.)"
    return {"audit_id": audit_id, "report": report}
