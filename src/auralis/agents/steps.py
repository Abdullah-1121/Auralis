"""
The three LLM steps of the pipeline, each a plain async function:
transcript -> Summary -> Insights -> FollowUpEmail.

Design notes (deliberate, and worth defending):
- No supervisor agent. The sequence is fixed, so plain code orchestrates it
  (see pipeline/runner.py). LLMs are used only where judgment is needed.
- The v0 CRM "agent" is gone entirely — writing structured data to a CRM is
  deterministic work, so it's now ordinary code in the CRM adapter.
- Clients are created lazily, never at import time.
"""

from functools import lru_cache

from agents import Agent, OpenAIChatCompletionsModel, RunConfig, Runner
from openai import AsyncOpenAI

from auralis.agents.prompts import (
    FOLLOWUP_INSTRUCTIONS,
    GROUNDING_INSTRUCTIONS,
    INSIGHT_INSTRUCTIONS,
    SCORECARD_INSTRUCTIONS,
    SUMMARIZER_INSTRUCTIONS,
)
from auralis.config import get_settings
from auralis.models import (
    CallScorecard,
    CustomerProfile,
    FollowUpEmail,
    GroundingReport,
    Insights,
    Summary,
)


class LLMNotConfiguredError(RuntimeError):
    """Raised when a step runs without an API key configured."""


@lru_cache()
def _run_config() -> RunConfig:
    s = get_settings()
    if not s.llm_api_key:
        raise LLMNotConfiguredError(
            "LLM_API_KEY is not set - add it to .env before processing calls."
        )
    client = AsyncOpenAI(api_key=s.llm_api_key, base_url=s.llm_base_url)
    model = OpenAIChatCompletionsModel(model=s.llm_model, openai_client=client)
    return RunConfig(model=model, model_provider=client, tracing_disabled=True)


def _agent(name: str, instructions: str, output_type: type) -> Agent:
    return Agent(name=name, instructions=instructions, output_type=output_type)


async def summarize(transcript: str) -> Summary:
    result = await Runner.run(
        _agent("Summarizer", SUMMARIZER_INSTRUCTIONS, Summary),
        input=f"Summarize this sales call transcript:\n\n{transcript}",
        run_config=_run_config(),
    )
    return result.final_output


async def extract_insights(summary: Summary) -> Insights:
    result = await Runner.run(
        _agent("InsightAnalyst", INSIGHT_INSTRUCTIONS, Insights),
        input=(
            "Analyze this call summary and keypoints.\n\n"
            f"Summary: {summary.summary}\n\nKeypoints:\n"
            + "\n".join(f"- {k}" for k in summary.keypoints)
        ),
        run_config=_run_config(),
    )
    return result.final_output


async def verify_grounding(transcript: str, insights: Insights) -> GroundingReport:
    result = await Runner.run(
        _agent("GroundingVerifier", GROUNDING_INSTRUCTIONS, GroundingReport),
        input=(
            "Verify each extracted claim against the transcript.\n\n"
            f"TRANSCRIPT:\n{transcript}\n\n"
            f"EXTRACTED INSIGHTS (JSON):\n{insights.model_dump_json(indent=2)}"
        ),
        run_config=_run_config(),
    )
    return result.final_output


async def score_call(transcript: str) -> CallScorecard:
    result = await Runner.run(
        _agent("SalesCoach", SCORECARD_INSTRUCTIONS, CallScorecard),
        input=f"Score this sales call:\n\n{transcript}",
        run_config=_run_config(),
    )
    return result.final_output


async def draft_followup(
    summary: Summary, insights: Insights, customer: CustomerProfile
) -> FollowUpEmail:
    result = await Runner.run(
        _agent("FollowUpSpecialist", FOLLOWUP_INSTRUCTIONS, FollowUpEmail),
        input=(
            f"Customer name: {customer.name}\n"
            f"Customer email: {customer.email}\n"
            f"Customer company: {customer.company}\n\n"
            f"Call summary: {summary.summary}\n\n"
            f"Insights (JSON): {insights.model_dump_json(indent=2)}\n\n"
            "Write the follow-up email now."
        ),
        run_config=_run_config(),
    )
    return result.final_output
