"""
Pipeline tests with faked LLM steps — no API key, no network.

The LLM steps are monkeypatched, which is exactly why they're plain async
functions: the pipeline's behavior (sequencing, persistence, retries,
failure honesty) is testable without a single real model call.
"""

import asyncio

import pytest

from auralis.models import (
    CallScorecard,
    CallStatus,
    CRMStatus,
    CustomerProfile,
    FollowUpEmail,
    GroundingCheck,
    GroundingReport,
    Insights,
    ScoreDimension,
    Summary,
)
from auralis.pipeline import runner
from auralis.store import db

CUSTOMER = CustomerProfile(
    name="Laura Chen", company="TechNova", role="Ops Lead", email="laura@technova.io"
)
TRANSCRIPT = "Rep: Hi Laura... Laura: We struggle with team visibility and Slack chaos..."

FAKE_SUMMARY = Summary(summary="Laura wants unified team tooling.", keypoints=["visibility", "Slack"])
FAKE_INSIGHTS = Insights(sentiment="neutral", pain_points=["No visibility"], integrations=["Slack"])
FAKE_GROUNDING = GroundingReport(
    overall_confidence="high",
    checks=[
        GroundingCheck(field="pain_points", claim="No visibility", supported=True, evidence="'we struggle with team visibility'"),
        GroundingCheck(field="integrations", claim="Slack", supported=True, evidence="'Slack chaos'"),
    ],
)
FAKE_FOLLOWUP = FollowUpEmail(
    email_subject="Great talking today", email_body="Hi Laura...", receiver_email="laura@technova.io"
)
FAKE_SCORECARD = CallScorecard(
    overall_score=7,
    discovery_quality=ScoreDimension(score=4, comment="Asked about current workflow"),
    objection_handling=ScoreDimension(score=3, comment="Concerns noted, not addressed"),
    next_step_clarity=ScoreDimension(score=4, comment="Demo scheduled"),
    missed_questions=["What is the decision timeline?"],
    deal_risks=["No champion identified"],
    coaching_tips=["Quantify the cost of missed follow-ups"],
)


@pytest.fixture(autouse=True)
def fresh_db():
    db.reset_for_tests(":memory:")
    yield


@pytest.fixture
def happy_steps(monkeypatch):
    async def fake_summarize(transcript):
        return FAKE_SUMMARY

    async def fake_insights(summary):
        return FAKE_INSIGHTS

    async def fake_grounding(transcript, insights):
        return FAKE_GROUNDING

    async def fake_followup(summary, insights, customer):
        return FAKE_FOLLOWUP

    async def fake_scorecard(transcript):
        return FAKE_SCORECARD

    monkeypatch.setattr(runner.llm_steps, "summarize", fake_summarize)
    monkeypatch.setattr(runner.llm_steps, "extract_insights", fake_insights)
    monkeypatch.setattr(runner.llm_steps, "verify_grounding", fake_grounding)
    monkeypatch.setattr(runner.llm_steps, "draft_followup", fake_followup)
    monkeypatch.setattr(runner.llm_steps, "score_call", fake_scorecard)


def _run(call_id):
    asyncio.run(runner.process_call(call_id))


def test_happy_path_completes_with_all_results(happy_steps):
    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert record.status == CallStatus.DONE
    assert record.summary == FAKE_SUMMARY
    assert record.insights == FAKE_INSIGHTS
    assert record.grounding == FAKE_GROUNDING
    assert record.followup == FAKE_FOLLOWUP
    assert record.scorecard == FAKE_SCORECARD
    assert record.crm_status == CRMStatus.SKIPPED  # no CRM configured in tests
    assert record.failed_step is None


def test_unsupported_claims_never_reach_the_email(happy_steps, monkeypatch):
    """The verifier flags a claim -> the follow-up drafter must not see it."""
    dirty_insights = Insights(
        sentiment="neutral",
        pain_points=["No visibility", "Hates their CRM vendor"],  # 2nd is invented
        integrations=["Slack"],
    )
    report = GroundingReport(
        overall_confidence="medium",
        checks=[
            GroundingCheck(field="pain_points", claim="No visibility", supported=True, evidence="quote"),
            GroundingCheck(field="pain_points", claim="Hates their CRM vendor", supported=False, evidence="never mentioned"),
            GroundingCheck(field="integrations", claim="Slack", supported=True, evidence="quote"),
        ],
    )
    seen_by_drafter = {}

    async def fake_insights(summary):
        return dirty_insights

    async def fake_grounding(transcript, insights):
        return report

    async def spy_followup(summary, insights, customer):
        seen_by_drafter["insights"] = insights
        return FAKE_FOLLOWUP

    monkeypatch.setattr(runner.llm_steps, "extract_insights", fake_insights)
    monkeypatch.setattr(runner.llm_steps, "verify_grounding", fake_grounding)
    monkeypatch.setattr(runner.llm_steps, "draft_followup", spy_followup)

    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert record.status == CallStatus.DONE
    # The drafter saw only verified claims
    assert seen_by_drafter["insights"].pain_points == ["No visibility"]
    # But the full record keeps everything, flagged for human review
    assert record.insights.pain_points == ["No visibility", "Hates their CRM vendor"]
    assert len(record.grounding.flagged) == 1


def test_failure_is_honest_and_partial_results_survive(happy_steps, monkeypatch):
    async def broken_followup(summary, insights, customer):
        raise RuntimeError("LLM provider exploded")

    monkeypatch.setattr(runner.llm_steps, "draft_followup", broken_followup)
    # Speed the test up: no real backoff sleeps
    monkeypatch.setattr(runner.asyncio, "sleep", _instant_sleep)

    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert record.status == CallStatus.FAILED
    assert record.failed_step == "draft_followup"
    assert "exploded" in record.error
    # Earlier steps' work is preserved — a late failure loses nothing
    assert record.summary == FAKE_SUMMARY
    assert record.insights == FAKE_INSIGHTS
    assert record.followup is None


def test_step_retries_then_succeeds(happy_steps, monkeypatch):
    attempts = {"n": 0}

    async def flaky_summarize(transcript):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient 503")
        return FAKE_SUMMARY

    monkeypatch.setattr(runner.llm_steps, "summarize", flaky_summarize)
    monkeypatch.setattr(runner.asyncio, "sleep", _instant_sleep)

    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert attempts["n"] == 3
    assert record.status == CallStatus.DONE


def test_slack_failure_does_not_fail_the_call(happy_steps, monkeypatch):
    async def broken_notify(record):
        raise RuntimeError("Slack webhook returned 500")

    monkeypatch.setattr(runner.notify, "notify_call_done", broken_notify)

    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert record.status == CallStatus.DONE  # notification is best-effort


def test_crm_failure_does_not_fail_the_call(happy_steps, monkeypatch):
    class ExplodingCRM:
        def write_lead(self, customer, insights):
            raise RuntimeError("sheets is down")

    monkeypatch.setattr(runner, "get_crm_adapter", lambda: ExplodingCRM())
    monkeypatch.setattr(runner.asyncio, "sleep", _instant_sleep)

    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    _run(call_id)

    record = db.get_call(call_id)
    assert record.status == CallStatus.DONE          # analysis succeeded
    assert record.crm_status == CRMStatus.FAILED     # failure stated loudly


def test_approval_requires_existing_draft(happy_steps):
    call_id = db.create_call(TRANSCRIPT, CUSTOMER)
    # Before processing: no draft yet -> approval must refuse
    assert db.set_followup_approved(call_id) is False
    _run(call_id)
    assert db.set_followup_approved(call_id) is True
    assert db.get_call(call_id).followup_approved is True


async def _instant_sleep(_seconds):
    return None
