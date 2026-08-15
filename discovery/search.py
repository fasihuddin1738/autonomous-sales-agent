import os
import sys
from tavily import TavilyClient
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead, PipelineStage

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def build_search_queries(icp: ICP) -> list[str]:
    """
    Turns an ICP into a handful of targeted search queries.
    Multiple angled queries find more diverse candidates than one broad query.
    """
    base = f"{icp.target_industry} companies in {icp.target_location}"
    queries = [base]

    if icp.special_focus:
        queries.append(f"{base} with {icp.special_focus}")
        queries.append(f"{icp.target_industry} businesses {icp.target_location} needing {icp.special_focus}")

    if icp.company_size:
        queries.append(f"{base} {icp.company_size}")

    return queries


def discover_leads(icp: ICP, max_results_per_query: int = 5) -> list[Lead]:
    """
    Runs Tavily searches based on the ICP and returns a deduplicated
    list of candidate Lead objects (company_name + source only).
    """
    queries = build_search_queries(icp)
    seen_names = set()
    leads: list[Lead] = []

    for query in queries:
        try:
            response = tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=max_results_per_query,
            )
        except Exception as e:
            print(f"Tavily search failed for query '{query}': {e}")
            continue

        for result in response.get("results", []):
            company_name = extract_company_name(result)
            if not company_name or company_name.lower() in seen_names:
                continue

            seen_names.add(company_name.lower())
            lead = Lead(
                company_name=company_name,
                source=f"search: {query}",
                pipeline_stage=PipelineStage.DISCOVERED,
            )
            lead.research.website = result.get("url")
            lead.log(f"Discovered via query: '{query}'")
            leads.append(lead)

    return leads


def extract_company_name(result: dict) -> str | None:
    """
    Best-effort company name extraction from a Tavily search result.
    Uses the page title, cleaned up. Good enough for a hackathon —
    refine with an LLM call later if extraction quality is poor.
    """
    title = result.get("title", "")
    if not title:
        return None

    # Strip common suffixes like " - Home" or " | Official Site"
    for separator in [" - ", " | ", ": "]:
        if separator in title:
            title = title.split(separator)[0]

    return title.strip()


if __name__ == "__main__":
    # Quick manual test
    test_icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="real estate",
        special_focus="high inbound lead volume",
    )
    results = discover_leads(test_icp)
    print(f"\nDiscovered {len(results)} candidate leads:\n")
    for lead in results:
        print(f"- {lead.company_name} ({lead.research.website})")