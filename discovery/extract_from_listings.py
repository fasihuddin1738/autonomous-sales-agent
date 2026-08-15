"""
discovery/extract_from_listings.py

Instead of discarding directory/listicle pages during filtering, this
extracts the individual company names mentioned inside them — turning
one "Top 9 Companies" page into up to 9 real candidate leads.
"""

import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.schema import ICP, Lead, PipelineStage

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

EXTRACT_MODEL = "llama-3.1-8b-instant"


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
        response = client.chat.completions.create(
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
    from their content, producing new candidate Leads.

    rejected_results: list of dicts with 'title', 'content', 'url' keys
    (the raw Tavily result, not a Lead — call this BEFORE building Lead objects,
    or pass through the original search result alongside the Lead).
    """
    new_leads: list[Lead] = []
    seen_names = set()

    for result in rejected_results:
        title = result.get("title", "")
        content = result.get("content", "") or result.get("raw_content", "") or ""
        if not content:
            continue

        company_names = extract_companies_from_content(title, content, icp)

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