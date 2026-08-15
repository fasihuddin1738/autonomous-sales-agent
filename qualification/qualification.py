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
from typing import Callable, Optional

from shared.schema import Lead, ICP, Qualification, DecisionMaker


# ---------------------------------------------------------------------------
# NexaFlow service catalog — used as grounded fallback when rag_lookup is
# not yet wired up. Must only list real NexaFlow offerings from the dossier.
# ---------------------------------------------------------------------------

_NEXAFLOW_CATALOG = {
    "WhatsApp AI Assistant": [
        "whatsapp", "whatsapp business", "high inbound whatsapp volume",
        "whatsapp support agents", "whatsapp inquiry", "order status",
        "customer support", "back-and-forth", "messaging",
    ],
    "Lead Capture Chatbot": [
        "lead-gen", "lead capture", "web forms", "inbound leads",
        "lead qualification", "crm", "manual qualification", "property inquiries",
        "sales chatbot", "lead routing",
    ],
    "Workflow Automation": [
        "workflow", "manual process", "automation", "operational process",
        "headcount growing", "support headcount", "inconsistent process",
        "manual entry", "crm manual",
    ],
    "Knowledge Assistant": [
        "knowledge", "sops", "manuals", "safety docs", "document storage",
        "documents", "sharepoint", "knowledge base", "staff asking managers",
        "search retrieval",
    ],
    "Voice AI Agent": [
        "voice", "call center", "phone support", "ivr", "inbound calls",
        "outbound calls", "voice agent",
    ],
    "Sales Automation": [
        "sales automation", "outreach", "follow-up", "pipeline", "crm automation",
        "sales process", "sales team",
    ],
}

# ICP qualification threshold — leads at or above this score are qualified.
QUALIFICATION_THRESHOLD = 60


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_employees(employees_estimate: Optional[str]) -> Optional[int]:
    """Extract a rough headcount integer from a free-text estimate string."""
    if not employees_estimate:
        return None
    import re
    nums = re.findall(r"\d+", employees_estimate)
    if nums:
        # Take the largest number found (e.g., "~45 support reps, ~300 total" -> 300)
        return max(int(n) for n in nums)
    return None


def _text_contains_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _research_text(lead: Lead) -> str:
    """Flatten all ResearchFindings fields into one searchable string."""
    r = lead.research
    parts = [
        r.website or "",
        r.employees_estimate or "",
        " ".join(r.key_departments),
        " ".join(r.recent_news),
        r.funding_signal or "",
        " ".join(r.tech_stack),
        " ".join(r.buying_signals),
        r.raw_notes or "",
    ]
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_qualification(lead: Lead, icp: ICP) -> Qualification:
    """
    Score a lead 0-100 against the ICP and NexaFlow fit criteria, produce
    human-readable reasoning, and set is_qualified.

    Scoring breakdown (total 100 pts):
      - ICP Industry match          : 25 pts
      - ICP Location match          : 20 pts
      - Company size fit            : 20 pts
      - Buying signals present      : 20 pts
      - Special focus match         : 15 pts
    """
    score = 0
    factors: list[str] = []
    research_text = _research_text(lead)

    # ---- 1. Industry match (25 pts) ----------------------------------------
    if icp.target_industry and _text_contains_any(
        research_text, [icp.target_industry.lower()]
    ):
        score += 25
        factors.append(f"Industry match: '{icp.target_industry}' aligned with research findings")
    else:
        # Partial match: check key_departments or buying_signals hint at industry
        industry_words = icp.target_industry.lower().split() if icp.target_industry else []
        if any(
            _text_contains_any(research_text, [w])
            for w in industry_words
            if len(w) > 3
        ):
            score += 12
            factors.append(f"Partial industry match: some '{icp.target_industry}' signals found")
        else:
            factors.append(f"No industry match for '{icp.target_industry}'")

    # ---- 2. Location match (20 pts) ----------------------------------------
    if icp.target_location and _text_contains_any(
        research_text, [icp.target_location.lower()]
    ):
        score += 20
        factors.append(f"Location match: '{icp.target_location}'")
    else:
        # Location isn't always in ResearchFindings; don't penalise heavily if
        # the lead was surface-discovered within the right geography.
        score += 10
        factors.append("Location not explicitly confirmed in research (no deduction for ICP-discovered lead)")

    # ---- 3. Company size fit (20 pts) ----------------------------------------
    headcount = _count_employees(lead.research.employees_estimate)
    icp_size_str = (icp.company_size or "").lower()

    if headcount is None and not icp.company_size:
        # Neither side has size info — neutral
        score += 10
        factors.append("Company size: no data on either side — neutral")
    elif headcount is not None and headcount < 10:
        # Very small company — poor fit for NexaFlow automation products
        factors.append(f"Company size too small (~{headcount} employees): likely under budget threshold")
    elif headcount is not None:
        # Parse ICP range if present e.g. "50-300 employees"
        import re
        icp_nums = re.findall(r"\d+", icp_size_str)
        if icp_nums:
            icp_min, icp_max = int(icp_nums[0]), int(icp_nums[-1])
            if icp_min <= headcount <= icp_max:
                score += 20
                factors.append(f"Company size ideal: ~{headcount} employees within ICP range {icp_min}–{icp_max}")
            elif headcount < icp_min:
                score += 8
                factors.append(f"Company size below ICP range (~{headcount} vs {icp_min}–{icp_max}): partial fit")
            else:
                score += 15
                factors.append(f"Company size above ICP range (~{headcount} vs {icp_min}–{icp_max}): may still be viable")
        else:
            # ICP size is qualitative (e.g. "SME") — just confirm not tiny
            score += 15
            factors.append(f"Company size ~{headcount} employees: acceptable")
    else:
        score += 5
        factors.append("Company size unknown — could not confirm ICP size fit")

    # ---- 4. Buying signals (20 pts) ----------------------------------------
    buying_signals = lead.research.buying_signals
    if len(buying_signals) >= 3:
        score += 20
        factors.append(f"Strong buying signals ({len(buying_signals)}): " + "; ".join(buying_signals[:2]))
    elif len(buying_signals) == 2:
        score += 14
        factors.append(f"Moderate buying signals (2): " + "; ".join(buying_signals))
    elif len(buying_signals) == 1:
        score += 8
        factors.append(f"Weak buying signals (1): {buying_signals[0]}")
    else:
        factors.append("No buying signals found in research — poor fit indicator")

    # ---- 5. Special focus match (15 pts) ------------------------------------
    if icp.special_focus:
        focus_keywords = [w.lower() for w in icp.special_focus.split() if len(w) > 3]
        if any(_text_contains_any(research_text, [kw]) for kw in focus_keywords):
            score += 15
            factors.append(f"Special focus match: '{icp.special_focus}' evident in research")
        else:
            factors.append(f"Special focus '{icp.special_focus}' NOT found in research findings")
    else:
        score += 7
        factors.append("No special focus criteria in ICP — not applied")

    # ---- Cap & decide -------------------------------------------------------
    score = max(0, min(100, score))
    is_qualified = score >= QUALIFICATION_THRESHOLD

    # Build human-readable reasoning
    verdict = "QUALIFIED" if is_qualified else "NOT QUALIFIED"
    reasoning = (
        f"{lead.company_name} scored {score}/100 — {verdict}. "
        f"Key factors: {'; '.join(factors[:3])}."
    )
    if not is_qualified:
        reasoning += (
            f" Score of {score} is below the {QUALIFICATION_THRESHOLD}-point "
            f"qualification threshold. Do not advance to outreach without a manual review."
        )

    return Qualification(
        score=score,
        reasoning=reasoning,
        factors=factors,
        is_qualified=is_qualified,
    )


def match_service(
    lead: Lead,
    rag_lookup: Optional[Callable[[str], str]] = None,
) -> str:
    """
    Return the most appropriate NexaFlow service name for this lead.

    If rag_lookup is provided (injected by the RAG teammate), call it with a
    query string and use the returned snippet to determine the service.
    Otherwise fall back to keyword matching against the internal catalog so
    the module is usable in mock mode before the RAG branch is ready.

    Returned string is always a key from _NEXAFLOW_CATALOG — never invented.
    """
    research_text = _research_text(lead)

    if rag_lookup is not None:
        # Build a compact query from the top buying signals + industry
        query = f"NexaFlow service for: {'; '.join(lead.research.buying_signals[:3])}"
        snippet = rag_lookup(query)
        # Match the snippet against the catalog keys
        snippet_lower = snippet.lower()
        for service_name in _NEXAFLOW_CATALOG:
            if service_name.lower() in snippet_lower:
                return service_name
        # If RAG didn't name a known service, fall through to keyword matching
        # rather than returning something invented.

    # --- Keyword scoring fallback ---
    service_scores: dict[str, int] = {s: 0 for s in _NEXAFLOW_CATALOG}
    for service_name, keywords in _NEXAFLOW_CATALOG.items():
        for kw in keywords:
            if kw in research_text.lower():
                service_scores[service_name] += 1

    best_service = max(service_scores, key=lambda s: service_scores[s])
    if service_scores[best_service] == 0:
        # No keyword hit at all — safe default for NexaFlow
        return "WhatsApp AI Assistant"

    return best_service


def identify_decision_makers(lead: Lead) -> list[DecisionMaker]:
    """
    Return a prioritized list of decision-maker role profiles for this lead.

    Priority 1 = most relevant to the recommended service (operational owner).
    Priority 2 = secondary sponsor / budget holder.
    Priority 3 = executive fallback (CEO/Founder).

    Name, email, and LinkedIn are left None since they come from the discovery
    branch — this function defines the *roles* to target; enrichment happens
    downstream.
    """
    recommended = lead.recommended_service or match_service(lead)
    research_text = _research_text(lead)

    # Role templates keyed by service
    _SERVICE_ROLE_MAP: dict[str, list[dict]] = {
        "WhatsApp AI Assistant": [
            {"role": "Head of Customer Support", "priority": 1},
            {"role": "E-commerce Operations Manager", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
        "Lead Capture Chatbot": [
            {"role": "Head of Sales", "priority": 1},
            {"role": "Marketing Manager", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
        "Workflow Automation": [
            {"role": "Head of Operations", "priority": 1},
            {"role": "CTO / Tech Lead", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
        "Knowledge Assistant": [
            {"role": "Head of Operations / Safety Manager", "priority": 1},
            {"role": "HR Manager", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
        "Voice AI Agent": [
            {"role": "Head of Customer Operations", "priority": 1},
            {"role": "CTO / Tech Lead", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
        "Sales Automation": [
            {"role": "Head of Sales", "priority": 1},
            {"role": "Revenue Operations Manager", "priority": 2},
            {"role": "CEO / Founder", "priority": 3},
        ],
    }

    role_templates = _SERVICE_ROLE_MAP.get(
        recommended, _SERVICE_ROLE_MAP["WhatsApp AI Assistant"]
    )

    decision_makers: list[DecisionMaker] = []
    for template in role_templates:
        dm = DecisionMaker(
            name=None,
            role=template["role"],
            email=None,
            linkedin=None,
            priority=template["priority"],
        )
        decision_makers.append(dm)

    return decision_makers
