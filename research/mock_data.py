"""
research/mock_data.py

Canned ResearchFindings payloads for fictional companies -- some pulled from
the NexaFlow dossier's case studies (MetroCart, HarborHomes, VectorWorks),
plus one deliberately weak-fit example (TinyCo) so you can also exercise the
"not qualified" path once qualification scoring is built.

Used whenever RESEARCH_MODE=mock (the default), so research, qualification,
and everything downstream can be built and demoed before the RAG/discovery
branch or real API keys are ready.

Add more companies here any time -- just add a new lowercase key.
"""

from __future__ import annotations
from shared.schema import ResearchFindings

MOCK_COMPANIES: dict[str, ResearchFindings] = {
    "metrocart": ResearchFindings(
        website="metrocart.example.com",
        employees_estimate="~45 support reps, ~300 total",
        key_departments=["Customer Support", "Logistics", "E-commerce Ops"],
        recent_news=[
            "Expanded delivery coverage to two new regions this quarter",
            "Support team hiring push posted for 'WhatsApp support agents'",
        ],
        funding_signal=None,
        tech_stack=["Shopify-style storefront", "WhatsApp Business", "Zendesk-style ticketing"],
        buying_signals=[
            "High inbound WhatsApp volume about order status and returns",
            "Customers frequently send incomplete order info, causing back-and-forth",
            "Support headcount growing faster than automation",
        ],
        raw_notes="Public-facing support channels are WhatsApp-heavy; no visible chatbot/automation today.",
    ),
    "harborhomes": ResearchFindings(
        website="harborhomes.example.com",
        employees_estimate="~20 agents across 3 offices",
        key_departments=["Sales", "Property Management"],
        recent_news=[
            "Opened a third regional office",
            "Running paid lead-gen campaigns for property inquiries",
        ],
        funding_signal=None,
        tech_stack=["Web lead-capture forms", "Basic CRM (manual entry)"],
        buying_signals=[
            "Inbound leads from web forms and WhatsApp are manually qualified today",
            "Sales managers report inconsistent lead qualification across agents",
            "No automated routing of high-intent leads to the right agent",
        ],
        raw_notes="Lead volume looks healthy but conversion process is manual and inconsistent.",
    ),
    "vectorworks": ResearchFindings(
        website="vectorworks.example.com",
        employees_estimate="~400 across manufacturing sites",
        key_departments=["Operations", "Safety & Compliance", "HR"],
        recent_news=["Rolled out a new safety compliance initiative plant-wide"],
        funding_signal=None,
        tech_stack=["SharePoint-style document storage", "No search/retrieval layer evident"],
        buying_signals=[
            "Large body of SOPs, manuals and safety docs scattered across drives",
            "Staff repeatedly ask managers questions already answered in existing docs",
        ],
        raw_notes="Good fit signal for a knowledge assistant, not primarily a chat/WhatsApp play.",
    ),
    "tinyco": ResearchFindings(
        website="tinyco.example.com",
        employees_estimate="~4 employees",
        key_departments=["Founder-run"],
        recent_news=[],
        funding_signal=None,
        tech_stack=["Instagram DMs as primary customer channel"],
        buying_signals=[],
        raw_notes=(
            "No repeatable operational process yet, no clear owner for automation, "
            "budget unconfirmed. Deliberately weak-fit -- useful for testing the "
            "'not qualified' path once scoring is built."
        ),
    ),
}


def get_mock_research(company_name: str) -> ResearchFindings | None:
    return MOCK_COMPANIES.get(company_name.strip().lower())
