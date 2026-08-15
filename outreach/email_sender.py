"""
Sends an OutreachMessage via Resend, updates its status/timestamp, and
records the send in long-term memory + the lead's memory_log.

This module mutates the Lead in place (appends/updates the OutreachMessage,
advances pipeline_stage on first send) and returns it — callers are
responsible for persisting the lead (see pipeline/lead_store.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from config import settings
from pipeline.memory import MemoryEntry, long_term
from shared.schema import Lead, OutreachMessage, OutreachStatus, PipelineStage


class EmailSendError(Exception):
    pass


def _send_via_resend(to_email: str, subject: str, body: str) -> str:
    """Returns the Resend message id. Raises EmailSendError on failure."""
    if not settings.RESEND_API_KEY:
        raise EmailSendError("RESEND_API_KEY is not set — cannot send real email.")

    import resend

    resend.api_key = settings.RESEND_API_KEY
    params = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if settings.EMAIL_REPLY_TO:
        params["reply_to"] = settings.EMAIL_REPLY_TO

    result = resend.Emails.send(params)
    return result.get("id", "") if isinstance(result, dict) else str(result)


def send_email(lead: Lead, message: OutreachMessage, dry_run: bool = False) -> OutreachMessage:
    """
    Send `message` (must already be attached to lead.outreach, or will be
    appended if not) via Resend. Set dry_run=True to skip the real API call
    and simulate a send — useful for demo/test runs without burning Resend
    quota or when RESEND_API_KEY isn't configured yet.
    """
    if message not in lead.outreach:
        lead.outreach.append(message)

    if not message.contact.email:
        raise EmailSendError(f"No email address on file for contact {message.contact.role}.")

    if dry_run or not settings.RESEND_API_KEY:
        message_id = "dry-run"
    else:
        message_id = _send_via_resend(message.contact.email, message.subject, message.body)

    message.status = OutreachStatus.SENT
    message.sent_at = datetime.now(timezone.utc)

    if lead.pipeline_stage in (PipelineStage.QUALIFIED,):
        lead.pipeline_stage = PipelineStage.CONTACTED

    lead.log(f"Email sent to {message.contact.name or message.contact.role} ({message.subject}).")
    long_term.append(MemoryEntry(
        lead_id=lead.id,
        entry_type="email_sent",
        payload={
            "outreach_message_id": message.id,
            "subject": message.subject,
            "to": message.contact.email,
            "resend_id": message_id,
            "is_follow_up": message.follow_up_count > 0,
        },
    ))
    return message


def record_reply(lead: Lead, message: OutreachMessage, reply_text: str) -> OutreachMessage:
    """
    Call this when an inbound reply comes in for a given outreach message
    (before classification — response_classifier.py fills in
    reply_classification separately).
    """
    message.status = OutreachStatus.REPLIED
    message.reply_text = reply_text
    lead.log(f"Reply received to '{message.subject}'.")
    long_term.append(MemoryEntry(
        lead_id=lead.id,
        entry_type="reply_received",
        payload={"outreach_message_id": message.id, "reply_text": reply_text},
    ))
    return message
