"""
research/llm_extract.py

Turns raw search snippets into a structured ResearchFindings-shaped dict via
an LLM call. Only exercised when RESEARCH_MODE=live -- the anthropic/openai
SDKs are imported lazily inside call_llm() so mock mode never needs them
installed.
"""

from __future__ import annotations
import json
from . import config

EXTRACTION_SYSTEM_PROMPT = """You are a B2B research analyst. You will be given raw web \
search snippets about a company, plus that company's ICP context. Extract only what is \
actually supported by the snippets into the following JSON shape. Never invent facts \
that aren't in the snippets -- omit a field (use null or an empty list) rather than guess.

{
  "website": "string or null",
  "employees_estimate": "string or null, e.g. '40-60 employees'",
  "key_departments": ["list of strings"],
  "recent_news": ["list of short strings, one per notable item"],
  "funding_signal": "string or null",
  "tech_stack": ["list of strings"],
  "buying_signals": ["list of short strings describing evidence of a business problem NexaFlow's services could address"],
  "raw_notes": "string or null -- anything relevant that doesn't fit the fields above"
}

Return ONLY the JSON object. No prose, no markdown fences."""


def call_llm(prompt: str) -> str:
    """Single provider-agnostic entry point. Default: Anthropic.
    Swap the body of this function if the team standardizes on OpenAI later --
    nothing else in the module needs to change."""
    if config.LLM_PROVIDER == "openai":
        # pyrefly: ignore [missing-import]
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    # pyrefly: ignore [missing-import]
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=1000,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def extract_research_findings(company_name: str, icp_summary: str, raw_search_text: str) -> dict:
    prompt = (
        f"Company: {company_name}\n"
        f"ICP context: {icp_summary}\n\n"
        f"Raw search snippets:\n{raw_search_text}\n\n"
        f"Extract the JSON now."
    )
    raw = call_llm(prompt).strip()

    # Defensive parse -- LLMs occasionally wrap JSON in fences despite instructions.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fail soft: downstream code still gets a valid dict, just parked in
        # raw_notes instead of losing the research entirely.
        return {"raw_notes": raw}
