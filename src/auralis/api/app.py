"""
FastAPI layer — deliberately thin. Routes validate, persist, schedule, and
read. All real behavior lives in pipeline/, agents/, crm/, store/.
"""

import asyncio
import base64
import json
import logging
import secrets

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from auralis import mailer
from auralis.api.ui import UI_HTML
from auralis.config import get_settings
from auralis.models import (
    CallListItem,
    CallRecord,
    CallStatus,
    EmailStatus,
    SubmitCallRequest,
    SubmitCallResponse,
)
from auralis.pipeline.runner import process_call
from auralis.store import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auralis",
    description="Post-call sales intelligence: transcript in — summary, "
    "insights, follow-up draft, and CRM record out.",
    version="1.0.0",
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep strong references to background tasks so the event loop never GCs a
# running pipeline mid-flight.
_background_tasks: set[asyncio.Task] = set()


@app.middleware("http")
async def basic_auth_guard(request: Request, call_next):
    """Optional HTTP Basic auth for public deployments.

    The approve endpoint dispatches real email — an open instance would let
    anyone send from the configured account. /health stays open for the
    platform's health checks."""
    creds = get_settings().basic_auth
    if creds and request.url.path != "/health":
        expected = "Basic " + base64.b64encode(creds.encode()).decode()
        provided = request.headers.get("authorization", "")
        if not secrets.compare_digest(provided.encode(), expected.encode()):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="auralis"'},
            )
    return await call_next(request)


@app.post("/calls", response_model=SubmitCallResponse, status_code=202)
async def submit_call(body: SubmitCallRequest) -> SubmitCallResponse:
    """Accept a transcript and return immediately with a call_id.
    Processing (~30-60s) happens in the background; poll GET /calls/{id}."""
    call_id = db.create_call(body.transcript, body.customer)
    task = asyncio.create_task(process_call(call_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info("Accepted call %s (customer=%s)", call_id, body.customer.name)
    return SubmitCallResponse(call_id=call_id, status=CallStatus.QUEUED)


@app.get("/calls/{call_id}", response_model=CallRecord)
async def get_call(call_id: str) -> CallRecord:
    record = db.get_call(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No call with id {call_id}")
    return record


@app.get("/calls", response_model=list[CallListItem])
async def list_calls(limit: int = 50) -> list[CallListItem]:
    return [
        CallListItem(
            call_id=r.call_id,
            status=r.status,
            customer_name=r.customer.name,
            created_at=r.created_at,
        )
        for r in db.list_calls(limit=min(limit, 200))
    ]


@app.post("/calls/{call_id}/approve-followup")
async def approve_followup(call_id: str) -> dict:
    """Human-in-the-loop gate: approve the drafted follow-up AND dispatch it.

    Dispatch outcome is always stated on the record:
    sent (SMTP accepted) / skipped (no mailer configured) / failed (SMTP error).
    Approval itself succeeds regardless — the human's decision is recorded."""
    record = db.get_call(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No call with id {call_id}")
    if record.followup is None:
        raise HTTPException(
            status_code=409,
            detail=f"Call {call_id} has no follow-up draft yet (status: {record.status.value})",
        )
    db.set_followup_approved(call_id)

    if not mailer.is_configured():
        db.set_email_status(call_id, EmailStatus.SKIPPED)
        return {
            "call_id": call_id,
            "followup_approved": True,
            "email_status": EmailStatus.SKIPPED.value,
            "detail": "Approved. No SMTP credentials configured, so nothing was sent.",
        }
    try:
        await asyncio.to_thread(mailer.send_followup, record.followup)
        db.set_email_status(call_id, EmailStatus.SENT)
        return {
            "call_id": call_id,
            "followup_approved": True,
            "email_status": EmailStatus.SENT.value,
            "detail": f"Sent to {record.followup.receiver_email}.",
        }
    except Exception as exc:
        logger.exception("Call %s: email dispatch failed", call_id)
        db.set_email_status(call_id, EmailStatus.FAILED)
        return {
            "call_id": call_id,
            "followup_approved": True,
            "email_status": EmailStatus.FAILED.value,
            "detail": f"Approved, but dispatch failed: {exc}",
        }


@app.get("/calls/{call_id}/events")
async def call_events(call_id: str) -> StreamingResponse:
    """Server-Sent Events: pushes a JSON snapshot whenever the call's state
    changes, so a UI can show live per-step progress without polling."""
    if db.get_call(call_id) is None:
        raise HTTPException(status_code=404, detail=f"No call with id {call_id}")

    async def stream():
        last = None
        # Hard cap: a call takes ~1-3 min; 15 min means something is wrong.
        for _ in range(15 * 60):
            record = db.get_call(call_id)
            snapshot = (
                record.status.value,
                record.failed_step,
                record.crm_status.value,
                record.email_status.value,
                record.followup_approved,
            )
            if snapshot != last:
                last = snapshot
                payload = {
                    "status": record.status.value,
                    "failed_step": record.failed_step,
                    "error": record.error,
                    "crm_status": record.crm_status.value,
                    "email_status": record.email_status.value,
                    "followup_approved": record.followup_approved,
                }
                yield f"data: {json.dumps(payload)}\n\n"
            if record.status in (CallStatus.DONE, CallStatus.FAILED):
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui() -> HTMLResponse:
    """Single-file demo dashboard: submit a transcript, watch the pipeline
    live, review the grounding report and scorecard, approve the send."""
    return HTMLResponse(UI_HTML)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "auralis", "version": "1.0.0"}
