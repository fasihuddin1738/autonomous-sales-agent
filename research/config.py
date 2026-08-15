"""
research/config.py

Centralized config for the research module. Reads from environment variables
(loaded via python-dotenv if a .env file is present) so nothing sensitive is
hardcoded and the module runs the same locally and once real keys land.

RESEARCH_MODE:
  - "mock"  (default) -> use canned data from mock_data.py, no network/API calls.
             Lets you build and test qualification + everything downstream
             before the RAG/discovery branch or real API keys are ready.
  - "live"  -> call the real search API + LLM.
"""

from __future__ import annotations
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

RESEARCH_MODE = os.getenv("RESEARCH_MODE", "mock").lower()  # "mock" | "live"

SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "tavily").lower()  # "tavily" | "serper"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()  # "anthropic" | "openai"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "claude-sonnet-4-6" if LLM_PROVIDER == "anthropic" else "gpt-4o-mini",
)


def require_live_keys() -> None:
    """Call before any real API call so missing keys fail loud and early,
    instead of surfacing as a confusing error three layers down."""
    if RESEARCH_MODE != "live":
        return
    if SEARCH_PROVIDER == "tavily" and not TAVILY_API_KEY:
        raise RuntimeError("RESEARCH_MODE=live but TAVILY_API_KEY is not set.")
    if SEARCH_PROVIDER == "serper" and not SERPER_API_KEY:
        raise RuntimeError("RESEARCH_MODE=live but SERPER_API_KEY is not set.")
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        raise RuntimeError("RESEARCH_MODE=live but ANTHROPIC_API_KEY is not set.")
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        raise RuntimeError("RESEARCH_MODE=live but OPENAI_API_KEY is not set.")
