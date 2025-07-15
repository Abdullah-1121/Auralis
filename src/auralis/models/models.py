from typing import List, Literal, Optional
from pydantic import BaseModel , Field 

class Summary(BaseModel):
    summary: str = Field(description="The summary of the call" , default_factory=str)
    keypoints :List[str] = Field(description="The keypoints of the summary" , default_factory=list)

class Insight(BaseModel):
    type: Literal["pain_point", "objection", "intent"] = Field(description=
                                                               "The type of the insight - pain point, objection or intent" , default_factory=str)
    content: str = Field(description="The content of the insight" , default_factory=str)
    confidence: float = Field(description="The confidence of the insight" , default_factory=float)

class Insights(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(description="The sentiment of the conversation" ,default_factory=str)
    pain_points: List[Insight] = Field(description="The pain points of the customer", default_factory=list)
    objections: List[Insight] = Field(description="The objections made by the customer", default_factory=list)
    intents: List[Insight] = Field(description="The intents of the customer", default_factory=list)

class FollowUp_Email(BaseModel):
    email_subject: str = Field(description="The subject of the email", default_factory=str)
    email_body: str = Field(description="The body of the email", default_factory=str)
    action_items: List[str] = Field(description="The action items of the email", default_factory=list)
    next_meeting_suggestion: str  = Field(description="The next meeting suggestion of the email", default_factory=str)

class CRMEntry(BaseModel):
    contact_name: str = Field(description="The name of the contact", default_factory=str)
    company: str   = Field(description="The company of the contact", default_factory=str)
    summary: str = Field(description="The summary of the contact", default_factory=str)
    pain_points: List[str] = Field(description="The pain points of the contact", default_factory=list)
    deal_stage: Literal["Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"] = Field(description="The deal stage of the contact", default_factory=str)
    follow_up_date: str   = Field(description="The follow up date of the contact", default_factory=str)

class CallContext(BaseModel):
    transcript: str = Field(description="The transcript of the call" , default_factory=str)
    summary: Summary = Field( description="The summary of the call" , default_factory=Summary)
    insights: Insights = Field(description="The insights of the call" , default_factory=Insights)
    follow_up: FollowUp_Email   = Field(description="The follow up of the call" , default_factory=FollowUp_Email)
    crm_entry: CRMEntry  = Field(description="The crm entry of the call", default_factory=CRMEntry) 
        