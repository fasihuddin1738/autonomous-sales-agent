"""
discovery/extract_from_listings.py

Instead of discarding directory/listicle pages during filtering, this
extracts the individual company names mentioned inside them — turning
one "Top 9 Companies" page into up to 9 real candidate leads.

expand_directory_leads() now runs extraction calls concurrently via a
thread pool instead of one page at a time. Dedup happens AFTER all
threads finish, not during — mutating a shared set() from multiple
threads at once is a race condition, so each thread returns its own
list of names and the main thread does the deduping serially.
"""

import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead, PipelineStage
from discovery.rate_limiter import groq_rate_limiter
from discovery.rate_limiter import groq_rate_limiter
from discovery.groq_client import call_groq_with_fallback

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


EXTRACT_MODEL = "llama-3.1-8b-instant"

# Same reasoning as filter.py — cap concurrency instead of running
# sequentially. Lower this if you start seeing 429s from Groq.
MAX_WORKERS = 8


def extract_companies_from_content(title: str, content: str, icp: ICP) -> list[str]:
    """
    Given a directory/listicle page's title + content snippet, asks the LLM
    to pull out real company names mentioned, matching the ICP.
    Returns a list of company name strings (may be empty).
    """
    prompt = f"""This is a directory or listicle page about {icp.target_industry} in {icp.target_location}.

Title: {title}
Content: {content[:2000]}

Extract a list of REAL, NAMED companies mentioned in this content that operate in
{icp.target_industry}. Do not include generic terms, categories, or the page's own title.
If no specific company names are mentioned, return an empty list.

Respond ONLY with valid JSON, no other text:
{{"companies": ["Company Name 1", "Company Name 2", ...]}}"""

    try:
        groq_rate_limiter.acquire()
        response = call_groq_with_fallback(
                model=EXTRACT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                timeout=30,
            )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("companies", [])
    except Exception as e:
        print(f"Extraction failed for '{title}': {e}")
        return []


def expand_directory_leads(rejected_results: list[dict], icp: ICP) -> list[Lead]:
    """
    Takes raw Tavily results that were classified as directories/listicles
    (i.e. would otherwise be thrown away) and extracts individual companies
    from their content CONCURRENTLY, producing new candidate Leads.

    rejected_results: list of dicts with 'title', 'content', 'url' keys
    (the raw Tavily result, not a Lead — call this BEFORE building Lead objects,
    or pass through the original search result alongside the Lead).
    """
    # Filter out pages with no content up front — no point spinning up a
    # thread for something we'd skip anyway.
    valid_results = []
    for result in rejected_results:
        content = result.get("content", "") or result.get("raw_content", "") or ""
        if content:
            valid_results.append((result, content))

    new_leads: list[Lead] = []
    seen_names: set[str] = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_result = {
            executor.submit(
                extract_companies_from_content, result.get("title", ""), content, icp
            ): result
            for result, content in valid_results
        }

        for future in as_completed(future_to_result):
            result = future_to_result[future]
            title = result.get("title", "")

            try:
                company_names = future.result()
            except Exception as e:
                print(f"Unexpected error extracting from '{title}': {e}")
                continue

            # Dedup happens here, in the main thread, after each future
            # resolves — safe because only one thread (this one) ever
            # touches seen_names.
            for name in company_names:
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())

                lead = Lead(
                    company_name=name,
                    source=f"extracted from directory: {title}",
                    pipeline_stage=PipelineStage.DISCOVERED,
                )
                lead.log(f"Extracted from listing page: '{title}'")
                new_leads.append(lead)

    return new_leads
