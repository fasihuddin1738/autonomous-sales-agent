"""
discovery/filter.py

Cheap filtering pass: takes raw discovered Leads (many of which are noise —
directories, listicles, blog posts, unrelated pages) and uses a lightweight
LLM call to keep only genuine candidate companies matching the ICP.

This runs BEFORE expensive deep research, so it should be fast and cheap.
Includes retry/backoff since the free-tier model shares a rate-limited pool.

filter_leads() now runs candidates through a thread pool instead of one
at a time with a fixed sleep between each — much faster, still respects
Groq's rate limit by capping concurrency (not by sleeping sequentially).
"""

import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead, PipelineStage
from discovery.rate_limiter import groq_rate_limiter
from discovery.rate_limiter import groq_rate_limiter
from discovery.groq_client import call_groq_with_fallback

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

FILTER_MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5      # seconds — grows with each retry, only used on actual failures

# How many filter calls run at once. Groq's free tier is generous enough
# that this is safe — if you start seeing a lot of 429s in the terminal,
# lower this to 3-5 rather than reintroducing a per-call sleep.
MAX_WORKERS = 3


def is_genuine_company(lead: Lead, icp: ICP) -> tuple[bool, str]:
    """
    Asks the LLM: is this a real, named company matching the ICP, or noise?
    Returns (keep: bool, reason: str). Retries on rate limits / connection errors.
    """
    website_line = f"URL: {lead.research.website}" if lead.research.website else "URL: not available (name extracted from a directory/listicle page)"

    prompt = f"""You are filtering candidates to find genuine companies for sales outreach.

ICP: industry="{icp.target_industry}", location="{icp.target_location}", special_focus="{icp.special_focus or 'none'}"

Candidate:
Title/Name: {lead.company_name}
{website_line}

Is this the name of an ACTUAL, NAMED COMPANY that could be a sales prospect matching the ICP?
If no URL is available, judge based on whether the NAME itself looks like a real, specific company
(not a generic category, not a listicle title, not a person's name alone).

Reject: directories, "Top N" listicles, blog posts, job listings, social media posts, YouTube videos,
unrelated content, and digital marketing/SEO/advertising agencies that serve the target industry
(they are vendors TO the industry, not companies IN it — reject these even if their name mentions
the industry, e.g. "SEO for Real Estate" or "Real Estate Marketing Agency" are NOT real estate companies).

Accept: a specific, real-sounding company that actually operates in the target industry.

Respond ONLY with valid JSON, no other text:
{{"keep": true or false, "reason": "one short sentence"}}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            groq_rate_limiter.acquire()
            response = call_groq_with_fallback(
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
    Runs the cheap filter over all discovered leads CONCURRENTLY
    (up to MAX_WORKERS at a time) instead of one at a time with a
    fixed delay. Returns only the ones that pass, updated to
    PipelineStage.POTENTIAL.

    Order of `kept` is not guaranteed to match input order, since
    calls complete out of order — dedup/downstream steps don't care
    about ordering, but flag it if something later assumes it does.
    """
    kept: list[Lead] = []
    filtered_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_lead = {
            executor.submit(is_genuine_company, lead, icp): lead
            for lead in leads
        }

        for future in as_completed(future_to_lead):
            lead = future_to_lead[future]
            try:
                keep, reason = future.result()
            except Exception as e:
                # Shouldn't normally happen since is_genuine_company
                # already catches its own errors, but stay safe.
                print(f"Unexpected error filtering '{lead.company_name}': {e}")
                keep, reason = True, "unexpected error — kept by default"

            if keep:
                lead.pipeline_stage = PipelineStage.POTENTIAL
                lead.log(f"Passed cheap filter: {reason}")
                kept.append(lead)
            else:
                filtered_count += 1
                print(f"Filtered out: {lead.company_name} — {reason}")

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
