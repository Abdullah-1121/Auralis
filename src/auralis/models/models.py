from typing import List, Literal, Optional
from pydantic import BaseModel , Field 

class CustomerProfile(BaseModel):
    name : str = Field(description="The name of the customer", default_factory=str)
    company : str = Field(description="The company of the customer", default_factory=str)
    role : str = Field(description="The role of the customer", default_factory=str)
    email : str = Field(description="The email of the customer", default_factory=str)

class Summary(BaseModel):
    summary: str = Field(description="The summary of the conversation", default_factory=str)
    keypoints : List[str] = Field(description="The keypoints of the conversation", default_factory=list)

class Insights(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(description="The sentiment of the conversation" ,default_factory=str)
    pain_points: List[str] = Field(description="The pain points of the customer", default_factory=list)
    objections: List[str] = Field(description="The objections made by the customer", default_factory=list)
    intents: List[str] = Field(description="The intents of the customer", default_factory=list)
    risks : List[str] = Field(description="The risks of the customer", default_factory=list)
    integrations : List[str] = Field(description="The integrations provided ", default_factory=list)
    sales_stage : str = Field(description="The sales stage of the customer", default_factory=str)
    next_steps : List[str] = Field(description="The next steps of the process", default_factory=list)

class FollowUp_Email(BaseModel):
    email_subject: str = Field(description="The subject of the email", default_factory=str)
    email_body: str = Field(description="The body of the email", default_factory=str)
    receiver_email: str = Field(description="The receiver email", default_factory=str)

class CRMEntry(BaseModel):
    contact_name: str = Field(description="The name of the contact", default_factory=str)
    company: str   = Field(description="The company of the contact", default_factory=str)
    summary: str = Field(description="The summary of the contact", default_factory=str)
    pain_points: List[str] = Field(description="The pain points of the contact", default_factory=list)
    deal_stage: Literal["Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"] = Field(description="The deal stage of the contact", default_factory=str)
    follow_up_date: str   = Field(description="The follow up date of the contact", default_factory=str)

class CallContext(BaseModel):
    customer_profile: CustomerProfile = Field(description="The customer profile" , default_factory=CustomerProfile)
    transcript: str = Field(description="The transcript of the call" , default_factory=str)
    summary: Summary = Field( description="The summary of the call" , default_factory=Summary)
    insights: Insights = Field(description="The insights of the call" , default_factory=Insights)
    follow_up: FollowUp_Email   = Field(description="The follow up of the call" , default_factory=FollowUp_Email)
     
        