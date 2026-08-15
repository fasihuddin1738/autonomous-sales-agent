"""
research/deep_research.py

Public entry point for this module's first job:

    run_deep_research(company_name, icp) -> ResearchFindings

In mock mode (default, RESEARCH_MODE=mock) this returns canned data from
mock_data.py so the rest of the pipeline -- and your own qualification work --
can be built and demoed without live API keys or the RAG/discovery branch
being ready.

In live mode (RESEARCH_MODE=live) it runs real search queries, hands the
snippets to the LLM for extraction, and validates the result into a
ResearchFindings object.
"""

from __future__ import annotations

from shared.schema import ICP, ResearchFindings
from . import config
from .mock_data import get_mock_research
from .search_client import get_search_client
from .llm_extract import extract_research_findings


def _build_queries(company_name: str) -> list[str]:
    return [
        f"{company_name} company overview website",
        f"{company_name} employees size departments",
        f"{company_name} recent news",
        f"{company_name} funding OR investment",
        f"{company_name} technology stack tools",
        f"{company_name} customer support OR WhatsApp OR chatbot",
    ]


def _icp_summary(icp: ICP) -> str:
    parts = [f"location={icp.target_location}", f"industry={icp.target_industry}"]
    if icp.company_size:
        parts.append(f"company_size={icp.company_size}")
    if icp.special_focus:
        parts.append(f"special_focus={icp.special_focus}")
    return ", ".join(parts)


def run_deep_research(company_name: str, icp: ICP) -> ResearchFindings:
    if config.RESEARCH_MODE == "mock":
        mocked = get_mock_research(company_name)
        if mocked is not None:
            return mocked
        # Unknown company in mock mode -> return an empty-but-valid object
        # rather than raising, so callers can keep testing their flow.
        return ResearchFindings(
            raw_notes=(
                f"No mock data for '{company_name}'. Add it to research/mock_data.py, "
                f"or set RESEARCH_MODE=live in .env to run a real search."
            )
        )

    config.require_live_keys()
    client = get_search_client()

    raw_chunks: list[str] = []
    for query in _build_queries(company_name):
        for result in client.search(query, max_results=5):
            raw_chunks.append(f"- {result.title}: {result.snippet} ({result.url})")

    raw_search_text = "\n".join(raw_chunks) if raw_chunks else "No search results returned."

    extracted = extract_research_findings(
        company_name=company_name,
        icp_summary=_icp_summary(icp),
        raw_search_text=raw_search_text,
    )

    return ResearchFindings.model_validate(extracted)
