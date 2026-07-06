"""
Deterministic pipeline runner — the replacement for the v0 supervisor agent.

The sequence never changes (summarize -> insights -> follow-up -> CRM), so
plain code runs it: no orchestration LLM, no prompt telling a model to
"never skip steps" and hoping it listens.

Guarantees:
- Every step retries with exponential backoff before the run fails.
- Each step's result is persisted the moment it exists — a later failure
  never loses earlier work.
- Failures are exact: status=failed + failed_step + error message.
- A CRM failure does NOT fail the call: the analysis succeeded and is shown,
  with crm_status=failed stated loudly next to it.
"""

import asyncio
import logging
import re
from typing import Awaitable, Callable, TypeVar

from auralis.agents import steps as llm_steps
from auralis.config import get_settings
from auralis.crm.base import get_crm_adapter
from auralis.models import CallStatus, CRMStatus, GroundingReport, Insights
from auralis.store import db

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _retry_delay(exc: Exception, default: float) -> float:
    """Honor the provider's requested wait on rate limits.

    Google's 429 payload includes 'Please retry in 32.2s' — retrying sooner
    than that just burns attempts inside the same rate-limit window.
    """
    text = str(exc)
    match = re.search(r"retry in ([0-9.]+)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return max(default, 30.0)
    return default


async def _with_retries(step_name: str, fn: Callable[[], Awaitable[T]]) -> T:
    s = get_settings()
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(1, s.step_max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 — retry any step failure
            last_exc = exc
            if attempt < s.step_max_attempts:
                base = s.step_backoff_seconds * (2 ** (attempt - 1))
                delay = _retry_delay(exc, base)
                logger.warning(
                    "Step %s failed (attempt %d/%d): %s — retrying in %.1fs",
                    step_name, attempt, s.step_max_attempts, exc, delay,
                )
                await asyncio.sleep(delay)
    raise last_exc


def _filter_verified(insights: Insights, report: GroundingReport) -> Insights:
    """Drop claims the verifier could not ground in the transcript.

    The follow-up email is client-facing: it must only ever reference
    verified facts. Flagged claims stay visible on the call record for
    human review — they just don't reach the customer.
    """
    unsupported = {(c.field, c.claim.strip().lower()) for c in report.flagged}
    if not unsupported:
        return insights

    def keep(field: str, items: list[str]) -> list[str]:
        return [i for i in items if (field, i.strip().lower()) not in unsupported]

    return Insights(
        sentiment=insights.sentiment,
        pain_points=keep("pain_points", insights.pain_points),
        objections=keep("objections", insights.objections),
        intents=keep("intents", insights.intents),
        risks=keep("risks", insights.risks),
        integrations=keep("integrations", insights.integrations),
        sales_stage=""
        if ("sales_stage", insights.sales_stage.strip().lower()) in unsupported
        else insights.sales_stage,
        next_steps=keep("next_steps", insights.next_steps),
    )


async def process_call(call_id: str) -> None:
    """Run the full pipeline for one submitted call. Never raises —
    every outcome, good or bad, is recorded on the call record."""
    record = db.get_call(call_id)
    if record is None:
        logger.error("process_call: unknown call_id %s", call_id)
        return

    # ── Step 1: summarize ─────────────────────────────────────────────────
    db.set_status(call_id, CallStatus.SUMMARIZING)
    try:
        summary = await _with_retries(
            "summarize", lambda: llm_steps.summarize(record.transcript)
        )
        db.save_result(call_id, "summary_json", summary)
    except Exception as exc:
        logger.exception("Call %s failed at summarize", call_id)
        db.set_failed(call_id, "summarize", str(exc))
        return

    # ── Step 2: insights ──────────────────────────────────────────────────
    db.set_status(call_id, CallStatus.EXTRACTING_INSIGHTS)
    try:
        insights = await _with_retries(
            "extract_insights", lambda: llm_steps.extract_insights(summary)
        )
        db.save_result(call_id, "insights_json", insights)
    except Exception as exc:
        logger.exception("Call %s failed at extract_insights", call_id)
        db.set_failed(call_id, "extract_insights", str(exc))
        return

    # ── Step 3: verify insights against the transcript ────────────────────
    db.set_status(call_id, CallStatus.VERIFYING_INSIGHTS)
    try:
        grounding = await _with_retries(
            "verify_grounding",
            lambda: llm_steps.verify_grounding(record.transcript, insights),
        )
        db.save_result(call_id, "grounding_json", grounding)
        if grounding.flagged:
            logger.warning(
                "Call %s: %d unsupported claim(s) flagged for review",
                call_id, len(grounding.flagged),
            )
    except Exception as exc:
        logger.exception("Call %s failed at verify_grounding", call_id)
        db.set_failed(call_id, "verify_grounding", str(exc))
        return

    # Client-facing content is drafted from VERIFIED insights only.
    verified_insights = _filter_verified(insights, grounding)

    # ── Step 4: follow-up draft ───────────────────────────────────────────
    db.set_status(call_id, CallStatus.DRAFTING_FOLLOWUP)
    try:
        followup = await _with_retries(
            "draft_followup",
            lambda: llm_steps.draft_followup(summary, verified_insights, record.customer),
        )
        db.save_result(call_id, "followup_json", followup)
    except Exception as exc:
        logger.exception("Call %s failed at draft_followup", call_id)
        db.set_failed(call_id, "draft_followup", str(exc))
        return

    # ── Step 5: call scorecard (rep coaching) ─────────────────────────────
    db.set_status(call_id, CallStatus.SCORING_CALL)
    try:
        scorecard = await _with_retries(
            "score_call", lambda: llm_steps.score_call(record.transcript)
        )
        db.save_result(call_id, "scorecard_json", scorecard)
    except Exception as exc:
        logger.exception("Call %s failed at score_call", call_id)
        db.set_failed(call_id, "score_call", str(exc))
        return

    # ── Step 6: CRM write (plain code — no LLM involved) ──────────────────
    db.set_status(call_id, CallStatus.WRITING_CRM)
    adapter = get_crm_adapter()
    if adapter is None:
        db.set_crm_status(call_id, CRMStatus.SKIPPED)
    else:
        try:
            await _with_retries(
                "crm_write",
                lambda: asyncio.to_thread(
                    adapter.write_lead, record.customer, insights
                ),
            )
            db.set_crm_status(call_id, CRMStatus.WRITTEN)
        except Exception:
            # The analysis is done and valuable — surface it, with the CRM
            # failure stated loudly instead of failing the whole call.
            logger.exception("Call %s: CRM write failed after retries", call_id)
            db.set_crm_status(call_id, CRMStatus.FAILED)

    db.set_status(call_id, CallStatus.DONE)
    logger.info("Call %s processed successfully", call_id)
