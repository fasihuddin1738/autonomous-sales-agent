"""
qualification/qualification.py

Scaffolded, NOT yet implemented. Deep research (research/deep_research.py) is
built and testable against mock data -- this is next.

Planned surface, all against the shared schema:

    run_qualification(lead, icp) -> Qualification
        Score 0-100 + human-readable reasoning + is_qualified bool.
        Must be able to return is_qualified=False -- don't force a match.
        research/mock_data.py already has a deliberately weak-fit company
        ("tinyco") to exercise that path.

    match_service(lead, rag_lookup) -> str
        rag_lookup will come from the RAG teammate -- takes a query, returns
        grounded snippets from the NexaFlow service catalog. Recommended
        service must come from those snippets, never invented.

    identify_decision_makers(lead) -> list[DecisionMaker]
        Prioritized by relevance to the recommended service, not just
        "always contact the CEO."

Left unbuilt on purpose -- ping the team before starting so we don't
duplicate design work on the RAG hookup.
"""

from __future__ import annotations
from typing import Callable

from shared.schema import Lead, ICP, Qualification, DecisionMaker


def run_qualification(lead: Lead, icp: ICP) -> Qualification:
    raise NotImplementedError("Not built yet -- see module docstring.")


def match_service(lead: Lead, rag_lookup: Callable[[str], str]) -> str:
    raise NotImplementedError("Not built yet -- see module docstring.")


def identify_decision_makers(lead: Lead) -> list[DecisionMaker]:
    raise NotImplementedError("Not built yet -- see module docstring.")
