from agents import OpenAIChatCompletionsModel, RunConfig, Runner, set_trace_processors , Agent , function_tool , RunContextWrapper
from openai import AsyncOpenAI
import weave
from weave.integrations.openai_agents.openai_agents import WeaveTracingProcessor
from dotenv import load_dotenv
from auralis.models.models import CallContext , Summary , Insights
load_dotenv()
import os
import asyncio
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
transcript = f'''[00:00] Sales Rep: Hey Jordan, thanks for joining the call. Hope your week’s going well.

[00:04] Jordan (Client): Thanks! It’s been a bit hectic — we’re closing Q2 targets and juggling a couple of tech vendor decisions.

[00:10] Sales Rep: Makes sense. Well, I’d love to understand what you’re evaluating and see if we can be a fit.

[00:16] Jordan: Sure. I lead IT ops at Onyx Learning. We run a hybrid education platform for enterprise clients — about 120 instructors, 10K learners per year. Our operations rely heavily on scheduling, virtual classrooms, and engagement analytics.

[00:33] Sales Rep: Awesome. What are you currently using to manage all of that?

[00:36] Jordan: A mix. For scheduling we use Calendly + Airtable, Zoom for virtual classes, and a custom analytics dashboard built by a contractor. But it’s fragile. Syncing between tools often breaks. No central control panel, and onboarding new instructors is slow.

[00:53] Sales Rep: Sounds like a lot of moving parts. What’s the biggest friction point?

[00:57] Jordan: Honestly — instructor onboarding and class monitoring. We can’t track real-time engagement unless they manually upload attendance. Also, support escalations aren’t centralized — instructors email different teams.

[01:10] Sales Rep: Got it. And is it fair to say your goals are: simplify operations, improve onboarding, and boost visibility?

[01:18] Jordan: Yep. Also, I’d love to reduce dependency on our in-house contractor — he’s been freelancing, and we had an outage last month that took hours to diagnose.

[01:28] Sales Rep: Ouch. Totally understand. Our platform centralizes scheduling, video, onboarding, and analytics — and we’ve built-in real-time instructor dashboards and automated attendance capture.

[01:42] Jordan: That’s interesting. Does it integrate with our internal Slack channels and Canvas LMS?

[01:47] Sales Rep: We have native Canvas LMS integration and Slack workflows via webhook. I can walk you through that.

[01:55] Jordan: Nice. Also, do you support data export to our data lake?

[01:59] Sales Rep: Yes — we support nightly syncs via secure S3 delivery or REST API pulls.

[02:04] Jordan: Great. And in terms of user management, how do you handle access roles for instructors vs. admins?

[02:11] Sales Rep: Role-based permissions are baked in — fully customizable. We also support SCIM for identity syncing with Okta or Azure AD.

[02:20] Jordan: Solid. Can you send me a breakdown of all modules and the pricing tiers?

[02:25] Sales Rep: Absolutely. Also — we’re doing early adopter onboarding for Q3 with extended support. You’d qualify based on your size.

[02:32] Jordan: Sounds good. Can we also schedule a technical deep dive next week? I’d like to include our lead dev and data engineer.

[02:38] Sales Rep: Yes, I’ll send a few time slots. Thanks, Jordan!


 '''
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
summarizer_Agent = Agent(
    name = 'Transcript_Summarizer',
    instructions = summarizer_instructions,
    output_type=Summary
)

insight_specialist = Agent(
    name = 'Insight_Specialist',
    instructions = insight_instructions,
    # output_type=Insights
)

async def run_agent():
    ctx = CallContext(
        transcript=transcript,
        summary = Summary(summary='Jordan from Onyx Learning is seeking to consolidate their fragmented education platform. They are specifically struggling with instructor onboarding, class monitoring, and contractor dependency, and are interested in integrations, data export, and user management.', keypoints=['Jordan from Onyx Learning is evaluating solutions to centralize their hybrid education platform, which currently uses a mix of tools like Calendly, Airtable, and Zoom.', 'Their main pain points are instructor onboarding, class monitoring, and reliance on a contractor for a custom analytics dashboard.', "Jordan's goals include simplifying operations, improving onboarding, boosting visibility, and reducing dependency on their in-house contractor.", "Onyx Learning is interested in the platform's integrations with Canvas LMS and Slack, data export capabilities, and user management features.", 'Jordan requested a breakdown of modules and pricing tiers and wants to schedule a technical deep dive with their lead developer and data engineer.'])
    )
    result = await Runner.run(starting_agent=insight_specialist , input='Gather insights from the provided summary ' , run_config= config , context = ctx)
    print(result.final_output)

asyncio.run(run_agent())