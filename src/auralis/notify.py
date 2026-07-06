"""
Slack notification — fired when a call finishes processing.

Design rules:
- Not configured (empty SLACK_WEBHOOK_URL) -> silently skipped. Slack is a
  convenience channel, not a pipeline step.
- A Slack failure must NEVER fail the call: the analysis is already done
  and persisted. The caller wraps this in try/except and logs.
"""

import logging

import httpx

from auralis.config import get_settings
from auralis.models import CallRecord

logger = logging.getLogger(__name__)


def _build_message(record: CallRecord) -> dict:
    s = get_settings()
    customer = record.customer
    title = f"📞 Call analyzed: {customer.name}"
    if customer.company:
        title += f" ({customer.company})"

    lines = []
    if record.scorecard:
        lines.append(f"*Call score:* {record.scorecard.overall_score}/10")
    if record.grounding:
        flagged = len(record.grounding.flagged)
        confidence = record.grounding.overall_confidence
        check = "all claims verified" if flagged == 0 else f"{flagged} claim(s) flagged for review"
        lines.append(f"*Grounding:* {confidence} confidence — {check}")
    if record.insights:
        lines.append(f"*Sentiment:* {record.insights.sentiment}")
        if record.insights.sales_stage:
            lines.append(f"*Stage:* {record.insights.sales_stage}")
    if record.followup:
        lines.append(f"*Follow-up draft:* “{record.followup.email_subject}”")

    review_url = f"{s.public_base_url.rstrip('/')}/ui?call={record.call_id}"

    return {
        "text": f"{title} — review and approve: {review_url}",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) or "Processed."}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{review_url}|Review the draft and approve the send →>",
                },
            },
        ],
    }


async def notify_call_done(record: CallRecord) -> bool:
    """Post the call summary to Slack. Returns True if a message was sent,
    False if notifications are not configured."""
    s = get_settings()
    if not s.slack_webhook_url:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(s.slack_webhook_url, json=_build_message(record))
        resp.raise_for_status()
    logger.info("Call %s: Slack notification sent", record.call_id)
    return True
