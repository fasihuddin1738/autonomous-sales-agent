"""
Follow-up scheduler.

Design note: this module is deliberately schema-agnostic. Instead of taking
the full `Lead` object (whose exact field names I don't have yet), the core
logic works off plain primitives (`FollowUpState`). Once shared/schema.py is
pasted, `state_from_lead()` becomes a one-line adapter that pulls the right
fields off `Lead.outreach` / `Lead.pipeline_stage` — the decision logic below
won't need to change.

Spec: Day 0 email -> if no reply after FOLLOW_UP_DELAY_DAYS (default 3) ->
send one follow-up. Stops following up if a reply was received or the lead
was moved to a terminal stage (Converted, Not Interested, Do Not Contact,
Not Qualified).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from config import settings
from shared.schema import Lead, OutreachStatus


class TerminalStageReason(str, Enum):
    REPLIED = "replied"
    STAGE_TERMINAL = "stage_terminal"


@dataclass(frozen=True)
class FollowUpState:
    """Minimal, schema-agnostic view of a lead needed to decide on follow-up."""
    lead_id: str
    last_outbound_sent_at: Optional[datetime]   # timestamp of most recent outbound email
    has_replied: bool                            # any inbound reply recorded since last outbound
    follow_ups_sent: int                          # how many follow-ups already sent
    is_terminal_stage: bool                       # e.g. Converted / Not Interested / Do Not Contact / Not Qualified


@dataclass(frozen=True)
class FollowUpDecision:
    should_send: bool
    reason: str
    due_at: Optional[datetime] = None  # when it *will* be due, if not yet


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_follow_up_due_at(last_outbound_sent_at: datetime, delay_days: int = None) -> datetime:
    delay = delay_days if delay_days is not None else settings.FOLLOW_UP_DELAY_DAYS
    return last_outbound_sent_at + timedelta(days=delay)


def decide_follow_up(state: FollowUpState, now: Optional[datetime] = None) -> FollowUpDecision:
    """Pure function: given current state, decide whether a follow-up should fire now."""
    now = now or _now()

    if state.is_terminal_stage:
        return FollowUpDecision(False, "lead is in a terminal pipeline stage")

    if state.has_replied:
        return FollowUpDecision(False, "lead has already replied; no follow-up needed")

    if state.last_outbound_sent_at is None:
        return FollowUpDecision(False, "no outbound email sent yet; nothing to follow up on")

    if state.follow_ups_sent >= settings.MAX_FOLLOW_UPS:
        return FollowUpDecision(False, "max follow-ups already sent")

    due_at = next_follow_up_due_at(state.last_outbound_sent_at)
    if now >= due_at:
        return FollowUpDecision(True, "follow-up window elapsed with no reply", due_at=due_at)

    return FollowUpDecision(False, "follow-up not yet due", due_at=due_at)


class FollowUpScheduler:
    """
    Simple poll-based scheduler suitable for a hackathon demo: call
    `scan_and_get_due(leads_state)` on a timer (e.g. APScheduler every few
    minutes, or a button in the Streamlit dashboard) rather than running a
    persistent background daemon per-lead.
    """

    def __init__(self):
        self._sent_log: dict[str, int] = {}  # lead_id -> follow_ups_sent (in-memory demo cache)

    def scan_and_get_due(self, states: list[FollowUpState], now: Optional[datetime] = None) -> list[FollowUpState]:
        """Return the subset of leads whose follow-up is due right now."""
        due = []
        for state in states:
            decision = decide_follow_up(state, now=now)
            if decision.should_send:
                due.append(state)
        return due

    def mark_follow_up_sent(self, lead_id: str) -> None:
        self._sent_log[lead_id] = self._sent_log.get(lead_id, 0) + 1


def run_follow_up_for_lead(lead: Lead, dry_run: bool = False):
    """
    Convenience wrapper: check if `lead` is due for a follow-up, and if so,
    draft + send it. Returns the new OutreachMessage, or None if not due.
    """
    from outreach.email_generator import generate_follow_up  # local import avoids a circular import
    from outreach.email_sender import send_email

    state = state_from_lead(lead)
    decision = decide_follow_up(state)
    if not decision.should_send:
        return None

    original = max(
        (m for m in lead.outreach if m.sent_at is not None),
        key=lambda m: m.sent_at,
    )
    follow_up = generate_follow_up(lead, original)
    send_email(lead, follow_up, dry_run=dry_run)
    lead.log(f"Follow-up sent ({decision.reason}).")
    return follow_up


# --- Adapter: real Lead -> FollowUpState ---
def state_from_lead(lead: Lead) -> FollowUpState:
    """
    shared/schema.py doesn't model outbound/inbound as separate messages —
    each OutreachMessage is a single outbound send that may later carry a
    reply (reply_text / reply_classification) on the same object. So "has
    replied" and "follow-ups sent" are both read off the most recent
    OutreachMessage rather than counted across a message list.
    """
    from pipeline.stage_tracker import TERMINAL_STAGES  # local import avoids a circular import

    if not lead.outreach:
        return FollowUpState(
            lead_id=lead.id,
            last_outbound_sent_at=None,
            has_replied=False,
            follow_ups_sent=0,
            is_terminal_stage=lead.pipeline_stage in TERMINAL_STAGES,
        )

    latest = max(
        (m for m in lead.outreach if m.sent_at is not None),
        key=lambda m: m.sent_at,
        default=lead.outreach[-1],
    )
    return FollowUpState(
        lead_id=lead.id,
        last_outbound_sent_at=latest.sent_at,
        has_replied=latest.status == OutreachStatus.REPLIED or latest.reply_text is not None,
        follow_ups_sent=latest.follow_up_count,
        is_terminal_stage=lead.pipeline_stage in TERMINAL_STAGES,
    )
