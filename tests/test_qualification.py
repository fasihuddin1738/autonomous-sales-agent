"""
tests/test_qualification.py

Standalone smoke test for the qualification module.
Run from the repo root (no live API keys required):

    python -m tests.test_qualification
"""

from __future__ import annotations

from shared.schema import ICP, Lead
from research.deep_research import run_deep_research
from qualification.qualification import (
    run_qualification,
    match_service,
    identify_decision_makers,
)


# ---------------------------------------------------------------------------
# Shared ICP — same as test_deep_research for consistency
# ---------------------------------------------------------------------------

ICP_FIXTURE = ICP(
    target_location="Karachi, Pakistan",
    target_industry="E-commerce",
    company_size="50-300 employees",
    special_focus="high WhatsApp inquiry volume",
)


def _make_lead(company_name: str) -> Lead:
    """Build a Lead by running deep research in mock mode."""
    findings = run_deep_research(company_name, ICP_FIXTURE)
    return Lead(company_name=company_name, research=findings)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_qualified_lead_metrocart() -> None:
    """MetroCart is a strong ICP fit — must be qualified with high score."""
    lead = _make_lead("MetroCart")
    result = run_qualification(lead, ICP_FIXTURE)

    print(f"\n[MetroCart] score={result.score}, is_qualified={result.is_qualified}")
    print(f"  reasoning: {result.reasoning}")
    for f in result.factors:
        print(f"  - {f}")

    assert result.score >= 60, f"Expected MetroCart score >= 60, got {result.score}"
    assert result.is_qualified is True, "Expected MetroCart to be qualified"
    print("  [PASS]")


def test_not_qualified_lead_tinyco() -> None:
    """TinyCo is deliberately weak-fit — must NOT be qualified."""
    lead = _make_lead("TinyCo")
    result = run_qualification(lead, ICP_FIXTURE)

    print(f"\n[TinyCo] score={result.score}, is_qualified={result.is_qualified}")
    print(f"  reasoning: {result.reasoning}")
    for f in result.factors:
        print(f"  - {f}")

    assert result.score < 60, f"Expected TinyCo score < 60, got {result.score}"
    assert result.is_qualified is False, "Expected TinyCo to NOT be qualified"
    print("  [PASS]")


def test_service_matching_keyword_fallback() -> None:
    """match_service with no rag_lookup should return a valid catalog service."""
    from qualification.qualification import _NEXAFLOW_CATALOG

    for company_name in ["MetroCart", "HarborHomes", "VectorWorks"]:
        lead = _make_lead(company_name)
        service = match_service(lead, rag_lookup=None)

        print(f"\n[{company_name}] recommended_service='{service}'")
        assert service in _NEXAFLOW_CATALOG, (
            f"match_service returned '{service}' which is NOT in the NexaFlow catalog"
        )
        print(f"  [PASS]")


def test_service_matching_with_rag_lookup() -> None:
    """match_service with a mock rag_lookup that names a known service."""
    from qualification.qualification import _NEXAFLOW_CATALOG

    def mock_rag_lookup(query: str) -> str:
        return "NexaFlow recommends the WhatsApp AI Assistant for high-volume support automation."

    lead = _make_lead("MetroCart")
    service = match_service(lead, rag_lookup=mock_rag_lookup)

    print(f"\n[MetroCart + mock RAG] recommended_service='{service}'")
    assert service in _NEXAFLOW_CATALOG, f"'{service}' not in catalog"
    print(f"  [PASS]")


def test_identify_decision_makers() -> None:
    """identify_decision_makers should return 3 prioritized roles."""
    lead = _make_lead("MetroCart")
    # Pre-set recommended_service to anchor DM selection
    lead.recommended_service = "WhatsApp AI Assistant"

    dms = identify_decision_makers(lead)

    print(f"\n[MetroCart] Decision Makers ({len(dms)}):")
    for dm in dms:
        print(f"  priority={dm.priority}  role='{dm.role}'")

    priorities = [dm.priority for dm in dms]
    assert 1 in priorities, "Expected at least one priority=1 decision maker"
    assert len(dms) >= 2, "Expected at least 2 decision maker roles"
    print("  [PASS]")


def test_full_qualification_pipeline() -> None:
    """End-to-end: research -> qualify -> match_service -> identify_decision_makers."""
    print("\n--- Full Pipeline: HarborHomes ---")
    lead = _make_lead("HarborHomes")

    # Step 1: qualify
    q = run_qualification(lead, ICP_FIXTURE)
    lead.qualification = q
    print(f"  Qualification: score={q.score}, is_qualified={q.is_qualified}")

    # Step 2: only proceed if qualified
    if q.is_qualified:
        # Step 3: match service
        service = match_service(lead)
        lead.recommended_service = service
        print(f"  Recommended service: {service}")

        # Step 4: identify decision makers
        dms = identify_decision_makers(lead)
        lead.decision_makers = dms
        print(f"  Decision makers: {[dm.role for dm in dms]}")

    assert lead.qualification is not None
    print("  [PASS]")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        test_qualified_lead_metrocart,
        test_not_qualified_lead_tinyco,
        test_service_matching_keyword_fallback,
        test_service_matching_with_rag_lookup,
        test_identify_decision_makers,
        test_full_qualification_pipeline,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test_fn.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed == 0:
        print("ALL QUALIFICATION TESTS PASSED!")
    else:
        print("SOME TESTS FAILED — check output above.")


if __name__ == "__main__":
    main()
