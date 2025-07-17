import json
from typing import Any
from agents import AgentHooks, ModelSettings, OpenAIChatCompletionsModel, RunConfig, Runner, Tool, set_trace_processors , Agent , function_tool , RunContextWrapper
from openai import AsyncOpenAI
import weave
from weave.integrations.openai_agents.openai_agents import WeaveTracingProcessor
from dotenv import load_dotenv
from auralis.models.models import CallContext , Summary , Insights , FollowUp_Email , CRMEntry , CustomerProfile
load_dotenv()
import os
import asyncio
from auralis.tools.tools import save_to_sheet
gemini_api_key = os.getenv("GEMINI_API_KEY") 


if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please ensure it is defined in your .env file.")




external_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client
)

config = RunConfig(
    model=model,
    model_provider=external_client,
    tracing_disabled=True,
    workflow_name='' \
    'Advanced SDK Workflow',
)

weave.init("Auralis")
# Set up tracing with Weave
set_trace_processors([WeaveTracingProcessor()])
test_transcript = f'''[00:00] Sales Rep: Hi Alex, thanks for making time today. How are things going?

[00:03] Alex (Client): Honestly, not great. I’m frustrated. We’ve been facing the same issues for months, and nothing’s improved.

[00:09] Sales Rep: I’m really sorry to hear that. Can you tell me more about what’s been happening?

[00:12] Alex: Your platform constantly crashes during peak hours. Our agents can’t log in, data gets lost, and our clients are angry. We reported this three times and were promised fixes — but here we are.

[00:24] Sales Rep: I understand that’s unacceptable. I can escalate this personally. Is the crash related to usage spikes or a specific feature?

[00:30] Alex: We think it’s usage load — it happens every Monday and Friday morning, which is when our customer support is busiest.

[00:38] Sales Rep: Got it. That sounds like a scalability issue. Anything else that’s impacting your operations?

[00:43] Alex: Yeah — the reporting dashboard is inaccurate. Numbers don’t match what we pull from our internal systems. It’s throwing off weekly reviews and decisions.

[00:52] Sales Rep: That’s a major concern. Are you currently syncing with any external data sources?

[00:56] Alex: Just Google Sheets via API, and we use Microsoft Teams internally. But we need more reliable integrations — and I’m not confident anymore.

[01:04] Sales Rep: Understood. I’d like to offer a 1:1 session with our lead engineer to diagnose the performance issue. Would that be okay?

[01:09] Alex: Fine. But this is the last chance. If this doesn’t get resolved, we’re switching platforms.

[01:14] Sales Rep: I appreciate your honesty. I’ll get the engineer looped in and send the session details by end of day.

[01:18] Alex: Please do.

 '''
test_summary = Summary(
    summary='Laura from TechNova is exploring tools to unify communication and task management for her distributed team. While she is interested in automation and integrations, she has concerns about vendor reliability, integration stability, and is hesitant to commit to long-term plans due to past negative experiences.',
    keypoints=[
        'Laura manages a distributed team using Slack, Trello, and Google Drive, but struggles with team visibility and accountability.',
        'She is exploring centralized platforms but expressed skepticism about switching due to team resistance and disruption concerns.',
        'Previous platforms failed to deliver on promised integrations, leading to broken workflows and loss of data.',
        'Laura is concerned about vendor lock-in and has questions about long-term data ownership and exportability.',
        'Their budget is limited to $3,000 annually, and she prefers a flexible, month-to-month pricing plan.',
        'She’s interested in features like automated reporting, task assignment, and strong integration with Slack and Google Drive.',
        'Security and compliance are important — she requested details on permission controls and audit logging.',
        'Laura asked for a side-by-side competitor comparison and a formal security documentation pack before scheduling another discussion.'
    ]
)
test_insights = Insights(
    sentiment='neutral',
    pain_points=[
        'Lack of team visibility',
        'Lack of accountability',
        'Previous platforms failed to deliver on promised integrations, leading to broken workflows and loss of data'
    ],
    objections=[
        'Team resistance to switching platforms',
        'Disruption concerns related to platform migration',
        'Vendor lock-in',
        'Long-term data ownership and exportability'
    ],
    intents=[
        'Unify communication and task management',
        'Automated reporting',
        'Task assignment',
        'Centralized platform adoption'
    ],
    risks=[
        'Vendor reliability',
        'Integration stability',
        'Hesitancy to commit to long-term plans'
    ],
    integrations=['Slack', 'Trello', 'Google Drive'],
    sales_stage='Technical evaluation',
    next_steps=[
        'Provide a side-by-side competitor comparison',
        'Provide a formal security documentation pack',
        'Schedule another discussion'
    ]
)

# Define the summarizer instructions
def summarizer_instructions( context : RunContextWrapper[CallContext], agent : Agent[CallContext] )-> str:
    transcript = context.context.transcript
    return f'''You are a highly capable sales assistant AI agent called the Summarizer Agent. Your role is to read and understand a raw transcript of a sales or discovery call, and generate a clean, structured, and concise summary that captures the key business-relevant details.

## 🎯 Objective
Generate a summary of the call that:
- Conveys the main discussion points
- Identifies relevant business context (goals, pain points, product interest)
- Omits irrelevant or casual small talk
- Helps a human sales representative or manager quickly understand what happened in the call

## 📥 Your Input
You will receive a `transcript` object from the context. The object contains:
- `text`: the full transcript of the call (already converted from audio)


## 📝 Instructions
1. Read the entire transcript carefully.
2. Ignore greetings, jokes, and chit-chat unless relevant to business.
3. Identify and extract the key discussion points.
4. Format your output based on transcript length:
   - If under 3 minutes → write a **1–2 sentence** summary.
   - If 3–15 minutes → write **3–5 concise bullet points**.
   - If over 15 minutes → write **5–7 detailed bullet points**.
5. If client name or meeting title is provided, include it in the first sentence of the summary.
6. Keep tone professional, neutral, and business-focused.
7. Avoid guessing or hallucinating any details not explicitly present in the transcript.

## 🌍 Language
Always respond in the same language as the transcript text, if it's not English.

## Think Step by Step 

## Transcript
This is the call transcript that you to summarize : {transcript}


 '''
def insight_instructions( ctx : RunContextWrapper[CallContext], agent : Agent[CallContext] )-> str:
    summary = ctx.context.summary.summary
    keypoints = ctx.context.summary.keypoints
    return f'''You are the InsightAgent, a structured reasoning assistant responsible for analyzing post-call summaries from sales or discovery calls. Your purpose is to extract meaningful, structured business insights from the information provided by the Summarizer Agent.

    Your output is not a summary or a paraphrase — it is a breakdown of actionable insights, technical considerations, business objectives, risks, and readiness signals that can support downstream decision-making, CRM population, and sales automation.

    ## 🎯 Goal
    Your goal is to transform a high-level call summary and a list of detailed keypoints into a precise and structured interpretation of:
   - What the client is trying to achieve
   - What problems they are facing
   - What systems or platforms they need to integrate with
   - What technical requirements or expectations they have
   - What risks, blockers, or concerns could hinder progress
   - How close they are to making a buying decision
   - What follow-up or action has been agreed upon

   ## 📥 Input
   You will receive:
   - A `summary`: a short paragraph that describes the general purpose and discussion in the call
   - A `keypoints` list: detailed bullet points summarizing various client statements, requests, concerns, and next steps

   The keypoints contain the richest information and may mention pain points, goals, tools, concerns, and follow-up plans.

   ## 🧠 Instructions
   1. Carefully read the summary and keypoints together. Consider the keypoints your main source of truth.
   2. Extract meaningful insights about the client’s business situation, technical needs, and decision-making stage.
   3. Be specific and concrete. Avoid vague language like “they want a good product.” Instead, say “they want to replace legacy dashboards with a centralized analytics system.”
   4. Use consistent terminology for categories like goals, pain points, integrations, etc.
   5. Do not repeat or rephrase the input. Your job is to **analyze and classify**, not summarize or beautify.
   6. If a category has no relevant content, it should be left empty (but still included).
   7. Assume this output will be read and used by another AI agent (e.g. a FollowUp Agent or CRM Sync Agent).

   ## 📝 Special Guidelines
   - If the client mentions specific tools or platforms (e.g., “Slack,” “Canvas LMS,” “Airtable”), treat these as **integration requirements**.
   - If the client expresses a concern or limitation (e.g., “we depend on an unreliable contractor”), treat that as a **risk or blocker**.
   - If they mention “budget range,” “follow-up demo,” or “bring in the CTO,” interpret this as part of their **sales readiness**.
   - Only extract insights that are **clearly stated or strongly implied**. Do not hallucinate.

   ## 🧪 Examples of Insight Types
   - Pain points: “Manual reporting is time-consuming,” “No real-time tracking”
   - Goals: “Wants to automate onboarding,” “Seeks better engagement analytics”
   - Integration needs: “Needs to connect with Slack and Salesforce”
   - Technical requirements: “Requires SCIM-based identity sync and S3 export”
   - Risks: “Dependent on a third-party contractor,” “Limited internal bandwidth”
   - Sales readiness: “In technical evaluation stage,” “Early exploration”
   - Next steps: “Follow-up scheduled with CTO,” “Requested pricing breakdown”

   ## 🧠 Final Reminder
   You are not a summarizer. You are a structured business analyst that reads text and derives actionable meaning. Your insights will power intelligent sales automation, CRM updates, and other downstream agents. Be precise, analytical, and grounded in the source information.
   Think step by step and plan for action
   Here is the summary {summary} and here are the keypoints{keypoints}

 '''
def followup_instructions( ctx : RunContextWrapper[CallContext], agent : Agent[CallContext] )-> str:
    summary = ctx.context.summary.summary
    keypoints = ctx.context.summary.keypoints
    insights = ctx.context.insights
    email_address = ctx.context.customer_profile.email
    customer_name = ctx.context.customer_profile.name
    return f'''
You are FollowUpSpecialist, an autonomous assistant responsible for generating thoughtful, personalized, and professional follow-up email after client discovery or sales calls.

You operate inside a multi-agent system. Your job begins **after the InsightAgent has analyzed a call** and extracted structured insights including the client's goals, pain points, objections, integrations, and next steps. Based on these, you will compose a follow-up email that moves the conversation forward, addresses concerns, and helps the sales team convert leads.

---

## 🎯 Objective
Your goal is to **write a professional follow-up email** that:
- Recaps the key context from the conversation (without re-summarizing the full transcript).
- Acknowledges the client’s pain points and goals in a natural tone.
- Addresses any objections or risks if present.
- Reinforces the value of the solution without being pushy.
- Confirms or initiates the next steps suggested during the call.
- Maintains a friendly, confident, and helpful tone.

---

## 🧠 Input You Will Receive
You will be given insights object that will conatain the following fields:
- `pain_points`: The specific problems the client is facing.
- `intents`: What the client is trying to achieve or improve.
- `objections`: Any concerns they expressed about budget, integration, or risk.
- `risks`: Potential blockers or hesitations.
- `integrations`: Platforms or tools they use or want to integrate.
- `sales_stage`: Their current stage in the decision process.
- `next_steps`: Concrete follow-up actions discussed in the call.
- `sentiment`: The emotional tone (e.g., positive, neutral, skeptical).
You will also receive Customer Email , Customer Name as well so that you can personalize the email.

---

## 📝 How to Write the Message
1. Open with a warm greeting and mention appreciation for the call.
2. Acknowledge one or two relevant pain points and goals.
3. If `objections` or `risks` exist, address them empathetically and professionally.
4. Mention helpful features aligned with their `intents` or `integrations`.
5. Clearly confirm the `next_steps` in your message.
6. Close with a friendly, helpful tone — never overly formal or overly casual.

---

## 📌 Guidelines
- Be specific: Reference their situation using available inputs.
- Be natural: Write like a professional sales rep who just had a real conversation.
- Be concise: Keep the message to 1–3 short paragraphs.
- Avoid over-selling: Let the value speak through alignment, not pressure.
- Always respect objections and risks — don’t dismiss them.

---

## 🧪 Example (for reference only)
> Hi Jordan,  
> Thanks again for the engaging discussion today. I really appreciate your transparency about the challenges with instructor onboarding and your goal to centralize operations.  
>  
> I understand your concerns about relying on a contractor — and we’ll make sure any solution we propose fits smoothly with your existing tools like Canvas, Slack, and Airtable.  
>  
> As discussed, I’ll send over a detailed pricing breakdown and schedule a technical deep dive with your lead developer and data engineer. Let me know if there’s anything else I can prep in advance.  
>  
> Looking forward to next steps!  
>  
> Best,  
> A2D Media

---
These are the insights we have received:{insights}
Customer Email : {email_address}
Customer Name : {customer_name}
use this email address {email_address} in the output as receiver email 
Remember: This message will be sent directly to the client and may influence their decision. Think like a sales advisor, act like a trusted partner, and write like a human.


 '''
def crm_agent_instructions(ctx: RunContextWrapper[CallContext], agent: Agent[CallContext]) -> str:
    customer = ctx.context.customer_profile
    insights = ctx.context.insights

    return f"""
You are a CRM Agent. Your job is to populate the CRM system with structured sales data from a customer call.

The data you need comes from two sources:
1. `customer` — containing personal details like name and email.
2. `insights` — containing sales insights like pain points, intent, risks, and more.

Use the `save_to_sheet` tool to push this data to the CRM.

Here’s the data to pass:
- name = {customer.name or ""}
- email = {customer.email or ""}
- sentiment = {insights.sentiment or ""}
- pain_points = {insights.pain_points or []}
- intents = {insights.intents or []}
- objections = {insights.objections or []}
- risks = {insights.risks or []}
- integrations = {insights.integrations or []}
- sales_stage = {insights.sales_stage or ""}
- next_steps = {insights.next_steps or []}

✅ Call the tool directly with these arguments.
✅ Leave fields blank if the data is missing — do not skip or raise errors.
✅ Your only responsibility is to structure and send the data to the CRM tool.
"""
def Supervisor_Agent_instructions(ctx: RunContextWrapper[CallContext], agent: Agent[CallContext]) -> str:
    transcript = ctx.context.transcript
    customer_details = ctx.context.customer_profile.name
    customer_email = ctx.context.customer_profile.email
    customer_company = ctx.context.customer_profile.company
    return f'''You are Auralis Supervisor, an autonomous and reliable AI orchestrator designed to analyze sales or discovery calls and guide downstream processes with precision.

## 🎯 Objective
Your role is to coordinate a specialized team of intelligent agents that each perform a step in a structured pipeline to process a sales call — from raw transcript to CRM integration. You ensure the correct **sequence**, **data flow**, and **tool usage**.

Your primary goal is to extract business-critical data from a call transcript and deliver a fully processed, actionable set of outputs including:
- A structured call summary
- Actionable business insights
- A personalized follow-up email
- CRM update record

## 🧑‍💼 Persona
You act as a senior operations manager with a deep understanding of AI agents and structured automation workflows. You do not perform any domain-specific analysis yourself — instead, you delegate those tasks to your agents.

You are thoughtful, logical, and task-driven.

## 🛠️ Your Team of Tools (Specialized Agents)

You have access to the following tools, which must be used in **exact sequence**:

1. **SummarizerAgent**  
   - Transforms raw transcript into structured summary & keypoints
   

2. **InsightAgent**  
   - Extracts detailed business insights (pain points, goals, risks, etc.) from summary/keypoints
   

3. **FollowUpAgent**  
   - Writes a professional follow-up email based on summary & insights
   

4. **CRMFormatterAgent**  
   - Updates the CRM with the useful insights to be needed by the sales team
   

## 📋 Workflow Rules

You must always:
1. Begin by calling the **SummarizerAgent** with the transcript from context.
2. Once the summary is returned, call the **InsightAgent**.
3. With both summary and insights in context, call the **FollowUpAgent** to generate the email.
4. Lastly, call the **CRMFormatterAgent** to create and store the CRM record.

Each agent depends on the output of the previous one. Wait for each tool's response before continuing.

Do not perform tasks manually. Always use the correct tool agent.

## 🧠 Thinking Guidelines

- Be disciplined in following the correct agent sequence.
- Never skip or combine agent steps.
- Rely on the context — do not hallucinate any input.
- If a tool fails, retry once. If it fails again, halt and report.

Here is the transcript to summarize : {transcript}
and here is the customer details you will need in a tool call  : name = {customer_details}, email = {customer_email}, company = {customer_company}
 '''
@function_tool(name_override='Send_Followup_Email')
def send_followup_email(to: str, subject: str, body: str) -> str:
    """
    Simulates sending a follow-up email.

    Args:
        to (str): Recipient's email address.
        subject (str): Email subject.
        body (str): Email body.

    Returns:
        str: Confirmation message.
    """
    print("📤 Simulating sending email...")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    return f"✅ Dummy email sent to {to} with subject: {subject}"
# Defining Agent LifeCycle Hooks
class Custom_agent_hooks(AgentHooks):
    async def on_start(self, context:RunContextWrapper[CallContext], agent:Agent[CallContext]):
        print('\n \n [DEBUG] -----------------------SUPERVISOR_AGENT STARTED-----------------------')
    async def on_tool_start(self , context: RunContextWrapper[CallContext],agent: Agent[CallContext] , tool: Tool):
        print(f'\n \n [DEBUG] -----------------------{tool.name} TOOL STARTED-----------------------')
    async def on_tool_end(self, context: RunContextWrapper[CallContext],agent: Agent[CallContext] , tool: Tool , result:str):
        print(f'\n \n [DEBUG] -----------------------{tool.name} TOOL ENDED-----------------------')
        print(f'\n \n[DEBUG] TOOL RESULT : {result}')
        print(f'\n \n[DEBUG] RESULT TYPE : {type(result)}')
        if tool.name == 'SummarizerAgent':
            print('SUMMARY UPDATED')
            summary = json.loads(result)
            email_obj = Summary(**summary)
            context.context.summary = email_obj
            print(type(email_obj))
        elif tool.name == 'InsightAgent':
            print('INSIGHTS UPDATED')
            insight = json.loads(result)
            insights_obj = Insights(**insight)
            context.context.insights = insights_obj
        elif tool.name == 'FollowUpAgent':
            print('EMAIL UPDATED')
            email = json.loads(result)
            email_obj = FollowUp_Email(**email)
            context.context.follow_up = email_obj
        elif tool.name == 'CRMFormatterAgent':
            print('CRM UPDATED')
    async def on_end(self, context: RunContextWrapper[CallContext], agent: Agent[CallContext]):
        print('\n \n [DEBUG] -----------------------SUPERVISOR_AGENT ENDED-----------------------')        

            
    async def on_end(self, context: RunContextWrapper[CallContext], agent: Agent[CallContext], output : Any):
        print('\n \n [DEBUG] -----------------------SUPERVISOR_AGENT ENDED-----------------------')

agent_hooks = Custom_agent_hooks()        
summarizer_Agent = Agent(
    name = 'Transcript_Summarizer',
    instructions = summarizer_instructions,
    output_type=Summary,
    model = model
)

insight_specialist = Agent(
    name = 'Insight_Specialist',
    instructions = insight_instructions,
    output_type=Insights,
    model = model
)

followup_specialist = Agent(
    name = 'FollowUp_Specialist',
    instructions = followup_instructions,
    output_type=FollowUp_Email,
    model = model
)
CRM_Agent = Agent(
    name = 'CRM_Agent',
    instructions = crm_agent_instructions,
    tools = [save_to_sheet],
    model_settings=ModelSettings(
        tool_choice="required" # Always call the tool
    ),
    model = model,
    hooks=agent_hooks
)

user1 = CustomerProfile(
    name = 'Alex Gomez',
    company = 'FooBar',
    role = 'Team Lead',
    email = 'Alex@FooBar.com'
)



Sales_Supervisor = Agent(
   name = 'Sales_Supervisor',
   instructions = Supervisor_Agent_instructions,
   tools = [
       summarizer_Agent.as_tool(
           tool_name = 'SummarizerAgent',
           tool_description='Summarizes a sales call transcript into a structured summary and keypoints'
       ),
       insight_specialist.as_tool(
           tool_name = 'InsightAgent',
           tool_description='Extracts detailed business insights from a sales call summary'
       ),
       followup_specialist.as_tool(
           tool_name = 'FollowUpAgent',
           tool_description='Writes a professional follow-up email based on summary & insights'
       ),
       CRM_Agent.as_tool(
           tool_name = 'CRMFormatterAgent',
           tool_description='Updates the CRM with the useful insights to be needed by the sales team'
       )
   ] ,
   hooks=agent_hooks

)           
    


async def run_agent():
    ctx = CallContext(
        transcript=test_transcript,
        customer_profile=user1
    )
    result = await Runner.run(starting_agent=Sales_Supervisor , input='Please analyze the new call transcript, generate a structured summary, extract actionable business insights, write a follow-up email for the client, and prepare the CRM record for storage.Begin by summarizing the transcript.' , run_config= config , context = ctx)
    print(result.final_output)
    print('\n \n-----------------------SUMMARY-----------------------')
    print(ctx.summary)
    print('\n \n-----------------------INSIGHTS-----------------------')
    print(ctx.insights)
    print('\n \n-----------------------EMAIL-----------------------')
    print(ctx.follow_up)

asyncio.run(run_agent())