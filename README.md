# research-qualify module

Owns: deep research, qualification scoring, service matching, decision-maker ID.
Does not touch RAG/discovery or outreach/pipeline — those are teammates' branches.

## Quick start

```
pip install -r requirements.txt
cp .env.example .env          # defaults to RESEARCH_MODE=mock, works with zero API keys
python -m tests.test_deep_research
```

## Mock vs live

`RESEARCH_MODE=mock` (default) returns canned `ResearchFindings` for a handful of
companies pulled from the NexaFlow dossier's own case studies, so this module —
and anything built on top of it — can be tested independently before the
RAG/discovery branch or real API keys are ready.

Add more companies any time in `research/mock_data.py` (just add a lowercase key).

Flip to `RESEARCH_MODE=live` in `.env` once Tavily/Serper + an LLM key are in hand.
Nothing else changes — `run_deep_research()` has the same signature either way.

## Folder map

- `shared/schema.py` — team-owned, don't edit solo
- `research/` — deep research (built, mock-tested)
  - `deep_research.py` — `run_deep_research(company_name, icp) -> ResearchFindings`
  - `mock_data.py` — canned findings, mock mode
  - `search_client.py` — Tavily/Serper abstraction, live mode only
  - `llm_extract.py` — search snippets -> structured findings, live mode only
  - `config.py` — env var handling, mock/live toggle
- `qualification/` — scaffolded, **not built yet** (scoring, service match, decision-makers)
- `tests/test_deep_research.py` — quick manual smoke test, not pytest
