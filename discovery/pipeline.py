"""
discovery/pipeline.py
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead
from discovery.search import discover_leads_with_raw
from discovery.filter import filter_leads
from discovery.extract_from_listings import expand_directory_leads


def run_discovery(icp: ICP, max_results_per_query: int = 8) -> list[Lead]:
    print(f"Discovering leads for ICP: {icp.target_industry} in {icp.target_location}...")
    raw_leads, raw_results = discover_leads_with_raw(icp, max_results_per_query=max_results_per_query)
    print(f"Found {len(raw_leads)} raw candidates. Running cheap filter...")

    potential_leads = filter_leads(raw_leads, icp)

    # Mine directory/listicle pages for additional company names
    print("Mining directory/listicle pages for additional leads...")
    directory_results = [r for r in raw_results if is_likely_directory(r)]
    extra_leads = expand_directory_leads(directory_results, icp)
    print(f"Extracted {len(extra_leads)} additional candidates from listings.")

    # Dedupe against what we already have
    existing_names = {lead.company_name.lower() for lead in potential_leads}
    new_unique = [l for l in extra_leads if l.company_name.lower() not in existing_names]

    # Filter the newly extracted ones too, since some may still be noise
    extra_potential = filter_leads(new_unique, icp) if new_unique else []

    all_potential = potential_leads + extra_potential
    return all_potential


def is_likely_directory(result: dict) -> bool:
    """Cheap heuristic (no LLM call) to flag likely listicle/directory pages worth mining."""
    title = result.get("title", "").lower()
    signals = ["top ", "best ", "directory", "list of", "browse", " agents in", " companies in"]
    return any(s in title for s in signals)


if __name__ == "__main__":
    test_icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="real estate",
        special_focus="high inbound lead volume",
    )

    results = run_discovery(test_icp)

    print(f"\nFinal potential leads ({len(results)}):")
    for lead in results:
        print(f"- {lead.company_name} | stage={lead.pipeline_stage} | source={lead.source}")