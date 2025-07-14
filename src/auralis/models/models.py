from typing import List, Literal, Optional
from pydantic import BaseModel , Field 

class Summary(BaseModel):
    summary: str = Field(description="The summary of the call")
    keypoints :List[str] = Field(description="The keypoints of the summary")

class Insight(BaseModel):
    type: Literal["pain_point", "objection", "intent"] = Field(description=
                                                               "The type of the insight - pain point, objection or intent")
    content: str = Field(description="The content of the insight")
    confidence: Optional[float] = Field(description="The confidence of the insight")

class Insights(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(description="The sentiment of the conversation")
    pain_points: List[Insight] = Field(description="The pain points of the customer")
    objections: List[Insight] = Field(description="The objections made by the customer")
    intents: List[Insight] = Field(description="The intents of the customer")

class FollowUp_Email(BaseModel):
    email_subject: str = Field(description="The subject of the email")
    email_body: str = Field(description="The body of the email")
    action_items: List[str] = Field(description="The action items of the email")
    next_meeting_suggestion: Optional[str] = Field(description="The next meeting suggestion of the email")

class CRMEntry(BaseModel):
    contact_name: str = Field(description="The name of the contact")
    company: Optional[str] = Field(description="The company of the contact")
    summary: str = Field(description="The summary of the contact")
    pain_points: List[str] = Field(description="The pain points of the contact")
    deal_stage: Literal["Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"] = Field(description="The deal stage of the contact")
    follow_up_date: Optional[str] = Field(description="The follow up date of the contact")

class CallContext(BaseModel):
    transcript: str = Field(description="The transcript of the call")
    summary: Summary = Field(description="The summary of the call")
    insights: Insights = Field(description="The insights of the call")
    follow_up: Optional[FollowUp_Email] = Field(description="The follow up of the call")
    crm_entry: Optional[CRMEntry] = Field(description="The crm entry of the call")
        