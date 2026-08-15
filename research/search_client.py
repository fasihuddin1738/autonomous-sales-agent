"""
research/search_client.py

Thin abstraction over the web-search provider so deep_research.py doesn't
care whether we're using Tavily or Serper. Only exercised when
RESEARCH_MODE=live -- mock mode never imports httpx at call time.
"""

from __future__ import annotations
from dataclasses import dataclass
import httpx

from . import config


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        raise NotImplementedError


class TavilyClient(SearchClient):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
            )
            for r in data.get("results", [])
        ]


class SerperClient(SearchClient):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
            )
            for r in data.get("organic", [])[:max_results]
        ]


def get_search_client() -> SearchClient:
    if config.SEARCH_PROVIDER == "serper":
        return SerperClient()
    return TavilyClient()
