"""
scripts/test_integration.py

First full end-to-end wiring test: ICP -> discovery -> deep research ->
qualification -> service matching (grounded via RAG) -> decision-makers ->
persisted to lead_store.

Run from project root:
    python scripts/test_integration.py

Limits to a handful of leads (LEAD_LIMIT) to keep this fast and cheap while
proving the pipeline connects end to end -- bump it up once this runs clean.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.schema import ICP
from discovery.pipeline import run_discovery
from research.deep_research import run_deep_research
from qualification.qualification import (
    run_qualification,
    match_service,
    identify_decision_makers,
)
from rag.retrieve import retrieve_context, answer_from_context
from pipeline.lead_store import lead_store

LEAD_LIMIT = 3  # keep small for a fast, cheap first integration run


def main():
    icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="real estate",
        special_focus="high inbound lead volume",
    )

    print(f"=== Step 1: Discovery ===")
    leads = run_discovery(icp, max_results_per_query=3)
    print(f"Discovered {len(leads)} potential leads. Testing first {LEAD_LIMIT}.\n")

    test_leads = leads[:LEAD_LIMIT]

    for lead in test_leads:
        print(f"--- {lead.company_name} ---")

        print("Step 2: Deep research...")
        lead.research = run_deep_research(lead.company_name, icp)
        lead.log("Deep research completed")

        print("Step 3: Qualification...")
        lead.qualification = run_qualification(lead, icp)
        lead.log(f"Qualification: {lead.qualification.score}/100")
        print(f"  Score: {lead.qualification.score}/100 — {'QUALIFIED' if lead.qualification.is_qualified else 'NOT QUALIFIED'}")

        print("Step 4: Service matching (grounded via RAG)...")
        lead.recommended_service = match_service(lead, rag_lookup=answer_from_context)
        lead.log(f"Recommended service: {lead.recommended_service}")
        print(f"  Recommended: {lead.recommended_service}")

        print("Step 5: Decision-maker identification...")
        lead.decision_makers = identify_decision_makers(lead)
        print(f"  Targets: {[dm.role for dm in lead.decision_makers]}")

        print("Step 6: Persisting to lead_store...")
        lead_store.save(lead)

        print(f"Done with {lead.company_name}.\n")

    print("=== Integration test complete ===")
    print(f"Saved leads in store: {len(lead_store.all())}")


if __name__ == "__main__":
    main()
