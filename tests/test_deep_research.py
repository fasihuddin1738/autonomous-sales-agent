"""
Quick standalone check -- not a full pytest suite, just fast feedback.
Run from the research-qualify/ root:

    python -m tests.test_deep_research
"""

from shared.schema import ICP
from research.deep_research import run_deep_research


def main():
    icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="E-commerce",
        company_size="50-300 employees",
        special_focus="high WhatsApp inquiry volume",
    )

    for name in ["MetroCart", "HarborHomes", "VectorWorks", "TinyCo", "SomeUnknownCo"]:
        findings = run_deep_research(name, icp)
        print(f"\n=== {name} ===")
        print(findings.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
