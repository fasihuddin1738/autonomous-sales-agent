import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead
from discovery.search import discover_leads
from discovery.filter import filter_leads


def run_discovery(icp: ICP, max_results_per_query: int = 5) -> list[Lead]:
    """
    Full discovery pipeline: given an ICP, returns a filtered list of
    Lead objects at PipelineStage.POTENTIAL, ready for deep research.
    """
    print(f"Discovering leads for ICP: {icp.target_industry} in {icp.target_location}...")
    raw_leads = discover_leads(icp, max_results_per_query=max_results_per_query)
    print(f"Found {len(raw_leads)} raw candidates. Running cheap filter...")

    potential_leads = filter_leads(raw_leads, icp)
    return potential_leads


if __name__ == "__main__":
    from shared.schema import ICP

    test_icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="real estate",
        special_focus="high inbound lead volume",
    )

    results = run_discovery(test_icp)

    print(f"\nFinal potential leads ({len(results)}):")
    for lead in results:
        print(f"- {lead.company_name} | stage={lead.pipeline_stage} | {lead.research.website}")