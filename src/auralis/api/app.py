"""
FastAPI layer — deliberately thin. Routes validate, persist, schedule, and
read. All real behavior lives in pipeline/, agents/, crm/, store/.
"""

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from auralis.config import get_settings
from auralis.models import (
    CallListItem,
    CallRecord,
    CallStatus,
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
    """Human-in-the-loop gate: mark the drafted follow-up as approved.
    (Actual email dispatch is stage 3 — approval is the contract for it.)"""
    record = db.get_call(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No call with id {call_id}")
    if record.followup is None:
        raise HTTPException(
            status_code=409,
            detail=f"Call {call_id} has no follow-up draft yet (status: {record.status.value})",
        )
    db.set_followup_approved(call_id)
    return {"call_id": call_id, "followup_approved": True}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "auralis", "version": "1.0.0"}
