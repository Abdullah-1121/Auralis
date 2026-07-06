"""
Domain models — the typed data that flows through the pipeline.

Salvaged from the v0 prototype (they were its best part) with two additions:
CallStatus for per-step job tracking, and CallRecord as the full persisted
shape returned by the API.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── Pipeline payloads ──────────────────────────────────────────────────────


class CustomerProfile(BaseModel):
    name: str = ""
    company: str = ""
    role: str = ""
    email: str = ""


class Summary(BaseModel):
    summary: str = Field(default="", description="Concise summary of the call")
    keypoints: List[str] = Field(default_factory=list, description="Key discussion points")


class Insights(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    pain_points: List[str] = Field(default_factory=list)
    objections: List[str] = Field(default_factory=list)
    intents: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    sales_stage: str = ""
    next_steps: List[str] = Field(default_factory=list)


class FollowUpEmail(BaseModel):
    email_subject: str = ""
    email_body: str = ""
    receiver_email: str = ""


class GroundingCheck(BaseModel):
    """One extracted claim, verified against the transcript."""

    field: str = Field(description="Insights field the claim came from, e.g. 'pain_points'")
    claim: str = Field(description="The extracted claim being verified")
    supported: bool = Field(description="Is this claim backed by the transcript?")
    evidence: str = Field(
        default="",
        description="Short quote from the transcript that supports the claim, "
        "or the reason it is unsupported",
    )


class GroundingReport(BaseModel):
    """Self-check of the insights against the source transcript.

    Unsupported claims are flagged for human review — and excluded from the
    insights that feed the follow-up email."""

    overall_confidence: Literal["high", "medium", "low"] = "high"
    checks: List[GroundingCheck] = Field(default_factory=list)

    @property
    def flagged(self) -> List[GroundingCheck]:
        return [c for c in self.checks if not c.supported]


class ScoreDimension(BaseModel):
    score: int = Field(ge=1, le=5, description="1 (poor) to 5 (excellent)")
    comment: str = Field(default="", description="One-sentence justification")


class CallScorecard(BaseModel):
    """Coaching-grade assessment of how the rep handled the call."""

    overall_score: int = Field(ge=1, le=10, description="Overall call quality, 1-10")
    discovery_quality: ScoreDimension
    objection_handling: ScoreDimension
    next_step_clarity: ScoreDimension
    missed_questions: List[str] = Field(
        default_factory=list, description="Questions the rep should have asked but didn't"
    )
    deal_risks: List[str] = Field(
        default_factory=list, description="Risks to this deal visible in the call"
    )
    coaching_tips: List[str] = Field(
        default_factory=list, description="Concrete, actionable advice for the rep"
    )


# ── Job tracking ───────────────────────────────────────────────────────────


class CallStatus(str, Enum):
    QUEUED = "queued"
    SUMMARIZING = "summarizing"
    EXTRACTING_INSIGHTS = "extracting_insights"
    VERIFYING_INSIGHTS = "verifying_insights"
    DRAFTING_FOLLOWUP = "drafting_followup"
    SCORING_CALL = "scoring_call"
    WRITING_CRM = "writing_crm"
    DONE = "done"
    FAILED = "failed"


class CRMStatus(str, Enum):
    PENDING = "pending"
    WRITTEN = "written"
    SKIPPED = "skipped"      # no CRM provider configured — stated, not hidden
    FAILED = "failed"        # adapter raised after retries — loud, never silent


class EmailStatus(str, Enum):
    """Dispatch state of the approved follow-up email."""

    NOT_SENT = "not_sent"    # not approved yet, or approval predates dispatch
    SENT = "sent"            # SMTP accepted the message
    SKIPPED = "skipped"      # approved, but no mailer configured — stated
    FAILED = "failed"        # SMTP raised — loud, never silent


class CallRecord(BaseModel):
    """Full persisted state of one processed call — what GET /calls/{id} returns."""

    call_id: str
    status: CallStatus
    failed_step: Optional[str] = None
    error: Optional[str] = None

    customer: CustomerProfile
    transcript: str = ""

    summary: Optional[Summary] = None
    insights: Optional[Insights] = None
    grounding: Optional[GroundingReport] = None
    followup: Optional[FollowUpEmail] = None
    scorecard: Optional[CallScorecard] = None
    followup_approved: bool = False
    email_status: EmailStatus = EmailStatus.NOT_SENT

    crm_status: CRMStatus = CRMStatus.PENDING

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── API request/response shapes ────────────────────────────────────────────


class SubmitCallRequest(BaseModel):
    transcript: str = Field(min_length=20, description="Full call transcript text")
    customer: CustomerProfile


class SubmitCallResponse(BaseModel):
    call_id: str
    status: CallStatus


class CallListItem(BaseModel):
    call_id: str
    status: CallStatus
    customer_name: str
    created_at: datetime
