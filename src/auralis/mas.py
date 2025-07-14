from agents import OpenAIChatCompletionsModel, RunConfig, Runner, set_trace_processors , Agent , function_tool , RunContextWrapper
from openai import AsyncOpenAI
import weave
from weave.integrations.openai_agents.openai_agents import WeaveTracingProcessor
from dotenv import load_dotenv
from auralis.models.models import CallContext , Summary
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
summarizer_instructions = Agent(
    name = 'Transcript_Summarizer',
    instructions = summarizer_instructions,
    output_type=Summary
)

transcript = f'''[00:00] Sales Rep: Hi Sarah, thanks for joining today. Can you hear me okay?

[00:04] Client (Sarah): Yes, I can hear you just fine. Thanks for having me.

[00:08] Sales Rep: Great. So just to get us started — could you tell me a bit about your team and what you're looking to achieve?

[00:15] Sarah: Sure. I manage the operations team at Brightline Logistics. We have about 25 field agents and 5 dispatchers. We're currently using spreadsheets and some old legacy software to track delivery routes, but it's not scalable.

[00:32] Sales Rep: Got it. And what are some of the biggest pain points you're facing with your current setup?

[00:37] Sarah: Honestly, visibility. I can’t track agent location in real time, and we often get delays or missed deliveries because of outdated info. Also, reporting is a nightmare — I spend hours each week pulling data manually.

[00:52] Sales Rep: That definitely makes sense. So you're looking for something with real-time tracking, better reporting, and I assume mobile access?

[01:00] Sarah: Exactly. Our field agents need to be able to update status from their phones, and dispatchers need to reroute quickly.

[01:10] Sales Rep: Got it. I think our platform could be a good fit. It includes GPS-based live tracking, mobile updates, and auto-generated weekly reports. Does that sound like what you're looking for?

[01:22] Sarah: Yes, that’s very aligned with what we need. I’d love to see how your reporting dashboard looks.

[01:28] Sales Rep: I’ll show you that in a moment. One quick thing — do you have a budget range in mind?

[01:35] Sarah: We’re in early research, but ideally under $5,000 annually.

[01:40] Sales Rep: Totally reasonable. Our mid-tier plan should fall well under that. I’ll include pricing in the follow-up email.

[01:48] Sarah: Perfect.

[01:50] Sales Rep: Okay, let me share my screen and show you the dashboard…
 '''
async def run_agent():
    ctx = CallContext(
        transcript=transcript
    )
    result = await Runner.run(starting_agent=summarizer_instructions , input='Summarize the transcript call and provide a summary' , run_config= config , context = ctx)
    print(result.final_output)

asyncio.run(run_agent())