"""
Outbound email dispatch — runs only after a human approves the draft.

Design rules:
- No SMTP credentials configured -> the approval still succeeds; the record
  says email_status=skipped. Stated, never silent.
- Sync smtplib wrapped by the caller in asyncio.to_thread — the API event
  loop never blocks on an SMTP handshake.
"""

import logging
import smtplib
from email.message import EmailMessage

from auralis.config import get_settings
from auralis.models import FollowUpEmail

logger = logging.getLogger(__name__)


class MailerNotConfiguredError(RuntimeError):
    """Raised when dispatch is attempted without SMTP credentials."""


def is_configured() -> bool:
    s = get_settings()
    return bool(s.smtp_username and s.smtp_password)


def send_followup(followup: FollowUpEmail) -> None:
    """Send the approved follow-up email. Raises on any failure —
    the caller records email_status=failed and surfaces it."""
    s = get_settings()
    if not is_configured():
        raise MailerNotConfiguredError(
            "SMTP_USERNAME / SMTP_PASSWORD are not set - approval recorded, "
            "but no email can be dispatched."
        )
    if not followup.receiver_email:
        raise ValueError("Follow-up draft has no receiver_email.")

    msg = EmailMessage()
    msg["Subject"] = followup.email_subject
    msg["From"] = f"{s.smtp_from_name} <{s.smtp_username}>"
    msg["To"] = followup.receiver_email
    msg.set_content(followup.email_body)

    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(s.smtp_username, s.smtp_password)
        smtp.send_message(msg)
    logger.info("Follow-up email sent to %s", followup.receiver_email)
