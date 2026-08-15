"""
Meeting handling: link generation + a short admin briefing sent
BRIEFING_LEAD_TIME_MIN (default 30) minutes before a scheduled meeting.

Link generation: for the hackathon, we generate a deterministic booking-style
link rather than integrating a real calendar API (Cal.com/Calendly) under
time pressure — swap `generate_meeting_link` for a real API call later
without touching anything else in this module.

Briefing: pulls only from the Lead — recommended_service, qualification
reasoning, and any objections/replies recorded on outreach messages. Same
no-invented-facts rule as email_generator.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from config import settings
from pipeline.memory import MemoryEntry, long_term
from shared.schema import Lead, Meeting, OutreachStatus, ResponseClassification

_OBJECTION_TYPES = {ResponseClassification.PRICING_OBJECTION, ResponseClassification.TECHNICAL_OBJECTION}


def generate_meeting_link(lead: Lead) -> str:
    """Deterministic placeholder booking link. Swap for real Cal.com/Calendly API later."""
    slug = lead.company_name.lower().replace(" ", "-")
    token = uuid.uuid4().hex[:8]
    return f"https://meet.nexaflow.ai/{slug}-{token}"


def _collect_objections(lead: Lead) -> list[str]:
    objections = []
    for msg in lead.outreach:
        if msg.reply_classification in _OBJECTION_TYPES and msg.reply_text:
            objections.append(f"[{msg.reply_classification.value}] {msg.reply_text}")
    return objections


def _collect_key_points(lead: Lead) -> list[str]:
    points = []
    if lead.qualification:
        points.extend(lead.qualification.factors)
    points.extend(lead.research.buying_signals)
    return points


def build_briefing_text(lead: Lead) -> str:
    """
    Short admin briefing: problem, recommended service, objections, key points.
    Built entirely from data already on the Lead — no LLM call needed, which
    also means it's instant and free to regenerate.
    """
    problem = lead.qualification.reasoning if lead.qualification else "No qualification summary on file."
    service = lead.recommended_service or "Not yet determined"
    objections = _collect_objections(lead)
    key_points = _collect_key_points(lead)

    lines = [
        f"MEETING BRIEFING — {lead.company_name}",
        "",
        "Problem / opportunity:",
        f"  {problem}",
        "",
        f"Recommended service: {service}",
        "",
        "Objections raised so far:",
    ]
    lines += [f"  - {o}" for o in objections] if objections else ["  (none recorded)"]
    lines += ["", "Key points to reference:"]
    lines += [f"  - {p}" for p in key_points] if key_points else ["  (none recorded)"]

    if lead.decision_makers:
        lines += ["", "Attendee(s):"]
        lines += [f"  - {dm.name or 'Unknown'} ({dm.role})" for dm in lead.decision_makers]

    return "\n".join(lines)


def schedule_meeting(lead: Lead, scheduled_time: datetime) -> Meeting:
    """Create/update lead.meeting with a link, time, and briefing; advance pipeline stage."""
    from shared.schema import PipelineStage  # local import avoids a circular import at module load

    meeting = lead.meeting or Meeting()
    meeting.scheduled_time = scheduled_time
    meeting.meeting_link = generate_meeting_link(lead)
    meeting.briefing = build_briefing_text(lead)
    meeting.admin_reminder_sent = False

    lead.meeting = meeting
    lead.pipeline_stage = PipelineStage.MEETING_SCHEDULED
    lead.log(f"Meeting scheduled for {scheduled_time.isoformat()}.")

    long_term.append(MemoryEntry(
        lead_id=lead.id,
        entry_type="meeting_scheduled",
        payload={"scheduled_time": scheduled_time.isoformat(), "meeting_link": meeting.meeting_link},
    ))
    return meeting


def is_briefing_due(lead: Lead, now: datetime | None = None) -> bool:
    """True if it's within BRIEFING_LEAD_TIME_MIN of the meeting and the reminder hasn't gone out."""
    now = now or datetime.now(timezone.utc)
    if not lead.meeting or not lead.meeting.scheduled_time or lead.meeting.admin_reminder_sent:
        return False
    lead_time = timedelta(minutes=settings.BRIEFING_LEAD_TIME_MIN)
    return now >= (lead.meeting.scheduled_time - lead_time)


def send_admin_briefing(lead: Lead, dry_run: bool = False) -> str:
    """
    Send the pre-meeting briefing to the internal sales admin. Reuses the
    Resend sender for simplicity (an internal notification email) rather
    than standing up a separate Slack integration under time pressure.
    """
    if not lead.meeting:
        raise ValueError(f"Lead {lead.id} has no scheduled meeting to brief.")

    briefing_text = lead.meeting.briefing or build_briefing_text(lead)
    admin_email = settings.EMAIL_REPLY_TO or settings.EMAIL_FROM

    if not dry_run and settings.RESEND_API_KEY:
        # pyrefly: ignore [missing-import]
        import resend
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [admin_email],
            "subject": f"[Briefing] Meeting with {lead.company_name} in {settings.BRIEFING_LEAD_TIME_MIN} min",
            "text": briefing_text,
        })

    lead.meeting.admin_reminder_sent = True
    lead.log("Admin pre-meeting briefing sent.")
    long_term.append(MemoryEntry(lead_id=lead.id, entry_type="briefing_sent", payload={"text": briefing_text}))
    return briefing_text
