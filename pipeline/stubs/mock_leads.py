"""
Factory for fake, schema-valid Lead objects, so outreach/pipeline code can be
built and tested without waiting on the real RAG/discovery/research/
qualification pipeline. Each mock lead is fully populated (research findings,
qualification, decision makers) so downstream modules have real evidence to
ground against — never empty stubs that would force invented facts.

NexaFlow AI's service catalog (fictional agency) — recommended_service must
always be one of these, since email_generator will refuse to draft around an
unrecognized service.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from shared.schema import (
    DecisionMaker,
    Lead,
    Meeting,
    OutreachMessage,
    OutreachStatus,
    PipelineStage,
    Qualification,
    ResearchFindings,
    ResponseClassification,
)

NEXAFLOW_SERVICES = [
    "AI Customer Support Automation",
    "Sales Outreach & Lead Qualification Automation",
    "Internal Workflow Automation (Ops/Finance)",
    "Custom RAG Knowledge Assistant",
    "AI-Powered Data Entry & Document Processing",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_qualified_lead_no_outreach() -> Lead:
    """A freshly qualified lead, nothing sent yet — the common starting point."""
    lead = Lead(
        company_name="Fernwood Logistics",
        source="ICP search: mid-market logistics, US, high support ticket volume",
        icp_fit_notes="Matches target industry (logistics) and company size band.",
        research=ResearchFindings(
            website="https://fernwoodlogistics.example.com",
            employees_estimate="80-120",
            key_departments=["Customer Support", "Dispatch Ops"],
            recent_news=["Opened a second regional distribution hub in Q2"],
            funding_signal=None,
            tech_stack=["Zendesk", "Salesforce"],
            buying_signals=[
                "Job posting for 'Customer Support Team Lead' mentions 'reduce ticket backlog'",
                "Support team grew from 4 to 9 reps in the last year",
            ],
            raw_notes="Support team appears stretched thin post-expansion.",
        ),
        qualification=Qualification(
            score=78,
            reasoning=(
                "Strong ICP fit: mid-market logistics company scaling support headcount "
                "quickly, with an explicit hiring signal around ticket backlog. High "
                "likelihood of interest in support automation."
            ),
            factors=[
                "ICP fit: logistics, 80-120 employees",
                "buying signal: hiring for backlog reduction",
                "existing tooling (Zendesk) is easy to integrate with",
            ],
            is_qualified=True,
        ),
        recommended_service=NEXAFLOW_SERVICES[0],  # AI Customer Support Automation
        decision_makers=[
            DecisionMaker(
                name="Priya Nandan",
                role="Head of Customer Support",
                email="priya.nandan@fernwoodlogistics.example.com",
                linkedin="https://linkedin.com/in/priyanandan-example",
                priority=1,
            ),
            DecisionMaker(
                name="Tom Alvarez",
                role="COO",
                email="tom.alvarez@fernwoodlogistics.example.com",
                priority=2,
            ),
        ],
        pipeline_stage=PipelineStage.QUALIFIED,
    )
    lead.log("Qualified by research/qualification pipeline (score 78).")
    return lead


def make_contacted_lead_awaiting_reply(days_since_sent: float = 1.5) -> Lead:
    """A lead that received Day-0 outreach and hasn't replied yet — not due for follow-up."""
    lead = make_qualified_lead_no_outreach()
    contact = lead.decision_makers[0]
    msg = OutreachMessage(
        contact=contact,
        subject="Cutting Fernwood's support backlog without new hires",
        body=(
            f"Hi {contact.name.split()[0]},\n\n"
            "Saw that Fernwood's support team has grown fast alongside the new "
            "distribution hub — and that you're hiring a Team Lead partly to tackle "
            "the ticket backlog. We help logistics teams like yours automate the "
            "repetitive tier-1 tickets in Zendesk so reps can focus on the ones that "
            "actually need a human.\n\n"
            "Worth a quick call this week?\n\nBest,\nNexaFlow AI"
        ),
        evidence_used=[
            "Job posting for Customer Support Team Lead mentions reducing ticket backlog",
            "Support team grew from 4 to 9 reps in the last year",
            "Uses Zendesk",
        ],
        status=OutreachStatus.SENT,
        sent_at=_now() - timedelta(days=days_since_sent),
    )
    lead.outreach.append(msg)
    lead.pipeline_stage = PipelineStage.CONTACTED
    lead.log(f"Day-0 outreach email sent to {contact.name} ({contact.role}).")
    return lead


def make_lead_due_for_follow_up() -> Lead:
    """Sent 4 days ago, no reply — should trigger the follow-up scheduler."""
    return make_contacted_lead_awaiting_reply(days_since_sent=4.0)


def make_lead_with_positive_reply() -> Lead:
    """A lead that replied positively — ready to move to Interested / schedule a meeting."""
    lead = make_contacted_lead_awaiting_reply(days_since_sent=1.0)
    msg = lead.outreach[0]
    msg.status = OutreachStatus.REPLIED
    msg.reply_text = "This looks interesting, can we set up a call next week?"
    msg.reply_classification = ResponseClassification.MEETING_REQUESTED
    lead.pipeline_stage = PipelineStage.INTERESTED
    lead.log("Reply received: Meeting Requested.")
    return lead


def make_lead_with_pricing_objection() -> Lead:
    lead = make_contacted_lead_awaiting_reply(days_since_sent=2.0)
    msg = lead.outreach[0]
    msg.status = OutreachStatus.REPLIED
    msg.reply_text = "Not sure this fits our budget right now, what's the pricing like?"
    msg.reply_classification = ResponseClassification.PRICING_OBJECTION
    lead.log("Reply received: Pricing Objection.")
    return lead


def make_lead_with_meeting_scheduled() -> Lead:
    lead = make_lead_with_positive_reply()
    lead.meeting = Meeting(
        scheduled_time=_now() + timedelta(hours=2),
        meeting_link=None,  # filled in by outreach/meeting.py
        briefing=None,
        admin_reminder_sent=False,
    )
    lead.pipeline_stage = PipelineStage.MEETING_SCHEDULED
    lead.log("Meeting scheduled.")
    return lead


def all_mock_leads() -> list[Lead]:
    return [
        make_qualified_lead_no_outreach(),
        make_contacted_lead_awaiting_reply(),
        make_lead_due_for_follow_up(),
        make_lead_with_positive_reply(),
        make_lead_with_pricing_objection(),
        make_lead_with_meeting_scheduled(),
    ]
