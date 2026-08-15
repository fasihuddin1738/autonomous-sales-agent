"""
discovery/filter.py

Cheap filtering pass: takes raw discovered Leads (many of which are noise —
directories, listicles, blog posts, unrelated pages) and uses a lightweight
LLM call to keep only genuine candidate companies matching the ICP.

This runs BEFORE expensive deep research, so it should be fast and cheap.
Includes retry/backoff since the free-tier model shares a rate-limited pool.
"""

import os
import sys
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead, PipelineStage

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

FILTER_MODEL = "openai/gpt-oss-20b:free"
MAX_RETRIES = 3
DELAY_BETWEEN_CALLS = 2.5   # seconds — keeps us under the free-tier rate limit
RETRY_BACKOFF_BASE = 5      # seconds — grows with each retry


def is_genuine_company(lead: Lead, icp: ICP) -> tuple[bool, str]:
    """
    Asks the LLM: is this a real, named company matching the ICP, or noise?
    Returns (keep: bool, reason: str). Retries on rate limits / connection errors.
    """
    prompt = f"""You are filtering search results to find genuine companies for sales outreach.

ICP: industry="{icp.target_industry}", location="{icp.target_location}", special_focus="{icp.special_focus or 'none'}"

Candidate:
Title/Name: {lead.company_name}
URL: {lead.research.website}

Is this the website of an ACTUAL, NAMED COMPANY that could be a sales prospect matching the ICP?
Reject: directories, "Top N" listicles, blog posts, job listings, social media posts, marketing agencies
(unless the agency itself matches the ICP), YouTube videos, unrelated content.
Accept: a real company's own website/page.

Respond ONLY with valid JSON, no other text:
{{"keep": true or false, "reason": "one short sentence"}}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=FILTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                timeout=30,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            return result.get("keep", False), result.get("reason", "")

        except Exception as e:
            wait = RETRY_BACKOFF_BASE * attempt
            print(f"Attempt {attempt}/{MAX_RETRIES} failed for '{lead.company_name}': {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"Giving up on '{lead.company_name}' — keeping by default (fail open).")
                return True, "filter error after retries — kept by default"


def filter_leads(leads: list[Lead], icp: ICP) -> list[Lead]:
    """
    Runs the cheap filter over all discovered leads, with a small delay
    between calls to stay under the free-tier rate limit.
    Returns only the ones that pass, updated to PipelineStage.POTENTIAL.
    """
    kept: list[Lead] = []

    for i, lead in enumerate(leads):
        keep, reason = is_genuine_company(lead, icp)
        if keep:
            lead.pipeline_stage = PipelineStage.POTENTIAL
            lead.log(f"Passed cheap filter: {reason}")
            kept.append(lead)
        else:
            print(f"Filtered out: {lead.company_name} — {reason}")

        if i < len(leads) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\n{len(kept)}/{len(leads)} leads passed the cheap filter.")
    return kept


if __name__ == "__main__":
    from discovery.search import discover_leads

    test_icp = ICP(
        target_location="Karachi, Pakistan",
        target_industry="real estate",
        special_focus="high inbound lead volume",
    )
    raw_leads = discover_leads(test_icp)
    potential_leads = filter_leads(raw_leads, test_icp)

    print("\nPotential leads:")
    for lead in potential_leads:
        print(f"- {lead.company_name} ({lead.research.website})")