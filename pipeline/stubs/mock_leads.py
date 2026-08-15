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


def make_qualified_lead_thin_evidence() -> Lead:
    """
    Second Qualified lead, deliberately sparse research — tests that
    email_generator produces a shorter, more general email instead of
    padding with invented specifics when evidence is thin.
    """
    lead = Lead(
        company_name="Brightline Dental Group",
        source="ICP search: healthcare services, US, 20-50 employees",
        icp_fit_notes="Matches target industry band; limited public info available.",
        research=ResearchFindings(
            website="https://brightlinedental.example.com",
            employees_estimate="20-50",
            key_departments=["Front Desk / Patient Coordination"],
            recent_news=[],
            funding_signal=None,
            tech_stack=[],
            buying_signals=[],
            raw_notes="Small multi-location practice; little public signal beyond ICP fit.",
        ),
        qualification=Qualification(
            score=58,
            reasoning=(
                "Fits ICP on industry and size, but no strong buying signal found yet. "
                "Worth a light-touch outreach to gauge interest rather than a heavily "
                "personalized pitch."
            ),
            factors=["ICP fit: healthcare services, 20-50 employees"],
            is_qualified=True,
        ),
        recommended_service=NEXAFLOW_SERVICES[2],  # Internal Workflow Automation
        decision_makers=[
            DecisionMaker(
                name="Dana Kim",
                role="Practice Manager",
                email="dana.kim@brightlinedental.example.com",
                priority=1,
            ),
        ],
        pipeline_stage=PipelineStage.QUALIFIED,
    )
    lead.log("Qualified by research/qualification pipeline (score 58, thin evidence).")
    return lead


def make_qualified_lead_no_contact_email() -> Lead:
    """
    Third Qualified lead, decision maker has no email on file — tests that
    email_sender.send_email raises a clean EmailSendError instead of
    crashing or silently failing.
    """
    lead = Lead(
        company_name="Ironclad Manufacturing Co.",
        source="ICP search: manufacturing, US, growing ops team",
        icp_fit_notes="Strong ICP fit; contact found via LinkedIn only, no email yet.",
        research=ResearchFindings(
            website="https://ironcladmfg.example.com",
            employees_estimate="150-200",
            key_departments=["Operations", "Quality Control"],
            recent_news=["Announced a new production line opening next quarter"],
            funding_signal=None,
            tech_stack=["SAP"],
            buying_signals=["Posted 3 open roles for manual QC data entry in the last month"],
            raw_notes="Contact identified via LinkedIn; email not yet found by discovery.",
        ),
        qualification=Qualification(
            score=71,
            reasoning=(
                "Manufacturing company with manual QC data entry roles opening — strong "
                "fit for document/data-entry automation. Missing verified contact email."
            ),
            factors=["ICP fit: manufacturing", "buying signal: manual QC data entry hiring"],
            is_qualified=True,
        ),
        recommended_service=NEXAFLOW_SERVICES[4],  # AI-Powered Data Entry & Document Processing
        decision_makers=[
            DecisionMaker(
                name="Marcus Webb",
                role="VP of Operations",
                email=None,  # deliberately missing — tests the error path
                linkedin="https://linkedin.com/in/marcuswebb-example",
                priority=1,
            ),
        ],
        pipeline_stage=PipelineStage.QUALIFIED,
    )
    lead.log("Qualified by research/qualification pipeline (score 71, no email on file yet).")
    return lead


def make_qualified_lead_multiple_contacts() -> Lead:
    """
    Fourth Qualified lead, three decision makers with different priorities —
    tests that generate_email() picks the priority-1 contact by default, and
    gives the dashboard something to exercise the contact-selection path with.
    """
    lead = Lead(
        company_name="Solstice Retail Group",
        source="ICP search: multi-location retail, US, customer service scaling",
        icp_fit_notes="Strong ICP fit; multiple relevant stakeholders identified.",
        research=ResearchFindings(
            website="https://solsticeretail.example.com",
            employees_estimate="300-400",
            key_departments=["Customer Service", "E-commerce Ops", "IT"],
            recent_news=["Launched online ordering across all 40 store locations"],
            funding_signal=None,
            tech_stack=["Zendesk", "Shopify"],
            buying_signals=[
                "Customer service response times increased 3x since online ordering launched",
                "Hiring for 'Customer Experience Automation Lead'",
            ],
            raw_notes="Rapid e-commerce growth is straining the support org.",
        ),
        qualification=Qualification(
            score=85,
            reasoning=(
                "Excellent ICP fit: fast-growing retail e-commerce operation with a clear, "
                "recent spike in support response times and an open role explicitly about "
                "automating customer experience."
            ),
            factors=[
                "ICP fit: retail, 300-400 employees",
                "buying signal: response times tripled post-launch",
                "buying signal: hiring a role literally titled Customer Experience Automation Lead",
            ],
            is_qualified=True,
        ),
        recommended_service=NEXAFLOW_SERVICES[0],  # AI Customer Support Automation
        decision_makers=[
            DecisionMaker(
                name="Alicia Ferreira",
                role="Director of Customer Experience",
                email="alicia.ferreira@solsticeretail.example.com",
                priority=1,
            ),
            DecisionMaker(
                name="Ben Osei",
                role="VP of E-commerce",
                email="ben.osei@solsticeretail.example.com",
                priority=2,
            ),
            DecisionMaker(
                name="Rachel Tan",
                role="IT Director",
                email="rachel.tan@solsticeretail.example.com",
                priority=3,
            ),
        ],
        pipeline_stage=PipelineStage.QUALIFIED,
    )
    lead.log("Qualified by research/qualification pipeline (score 85).")
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
        make_qualified_lead_thin_evidence(),
        make_qualified_lead_no_contact_email(),
        make_qualified_lead_multiple_contacts(),
        make_contacted_lead_awaiting_reply(),
        make_lead_due_for_follow_up(),
        make_lead_with_positive_reply(),
        make_lead_with_pricing_objection(),
        make_lead_with_meeting_scheduled(),
    ]