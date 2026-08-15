import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP


def capture_icp_interactive() -> ICP:
    """
    Simple CLI capture for testing. Swap this for a form/API endpoint
    once the frontend is wired up (outreach-pipeline teammate's territory).
    """
    print("Let's define your Ideal Customer Profile.\n")

    target_location = input("Target location (e.g. 'Karachi, Pakistan'): ").strip()
    target_industry = input("Target industry (e.g. 'Real estate', 'E-commerce'): ").strip()
    company_size = input("Company size (optional, e.g. '10-50 employees', press Enter to skip): ").strip() or None
    special_focus = input("Special focus (optional, e.g. 'high WhatsApp inquiry volume', press Enter to skip): ").strip() or None

    icp = ICP(
        target_location=target_location,
        target_industry=target_industry,
        company_size=company_size,
        special_focus=special_focus,
    )

    print(f"\nICP captured: {icp.model_dump_json(indent=2)}")
    return icp


def build_icp(target_location: str, target_industry: str,
              company_size: str = None, special_focus: str = None) -> ICP:
    """
    Programmatic version — call this directly from an API endpoint
    once the frontend sends structured data instead of CLI input.
    """
    return ICP(
        target_location=target_location,
        target_industry=target_industry,
        company_size=company_size,
        special_focus=special_focus,
    )


if __name__ == "__main__":
    capture_icp_interactive()