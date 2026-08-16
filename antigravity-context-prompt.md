# Project context — AgentHack: NexaFlow AI Sales Agent

Paste this whole thing at the start of a fresh Antigravity session before asking it to build
anything. Fill in the "Right now" line at the bottom each time — everything above it stays
the same across sessions.

## What this is

A 24-hour hackathon project (AgentHack — Autonomous AI Sales Agent Challenge). The deliverable
is an AI system that takes a company's info, finds matching leads, researches them, and runs a
full sales pipeline end to end: qualify -> recommend a service -> personalized outreach ->
classify replies -> follow up -> schedule meetings -> track pipeline stage. Judging weighs
whether the required pipeline actually works (70%), extra features (15%), and frontend (15%) —
extras only count if the core pipeline is solid.

## The company we're building for (RAG ground truth)

NexaFlow AI — a fictional Karachi-based AI automation agency (WhatsApp assistants, web
chatbots, workflow automation, voice agents, knowledge assistants, sales automation). This
company's dossier is the authoritative knowledge base: every recommended service, price range,
and capability claim the system makes must trace back to that dossier. It contains deliberate
guardrails — no autonomous refunds, no unrestricted bulk WhatsApp messaging, no "we replace
your whole support team" claims, no invented pricing. It also contains intentionally outdated
info the system should recognize as stale rather than repeat as current.

## Required pipeline

RAG -> ICP -> Lead Discovery -> Cheap Filtering -> Deep Research -> Qualification -> Service
Matching -> Decision-Maker ID -> Personalized Outreach -> Response Classification -> Follow-Up
-> Meeting Scheduling. Short-term + long-term memory and a persistent pipeline-stage tracker
(Discovered -> Potential -> Qualified -> Contacted -> Interested -> Meeting Scheduled ->
Converted, plus negative states like Not Qualified / Not Interested / Do Not Contact) run
underneath every stage.

## Team and branches

Three-person team. I own `feature/research-qualify`:
- Deep research per lead (website, employees/departments, news, funding, tech stack, buying
  signals)
- Qualification scoring (0-100 confidence + human-readable reasoning; must be able to
  conclude NOT qualified)
- Service matching (grounded in the RAG layer, never invented capabilities)
- Decision-maker identification (prioritized by relevance to the recommended service)

Teammates own RAG/discovery and outreach/pipeline on separate branches. `shared/schema.py` is
team-owned — never edit it without explicit consent, even for something small like adding
`__init__.py`.

## Repo structure (current)

```
autonomous-sales-agent/                 <- repo root, where main.py lives
├── shared/                             EXISTING, team-owned — do not touch solo
│   ├── __init__.py
│   └── schema.py                       Lead, ICP, ResearchFindings, Qualification,
│                                        DecisionMaker, OutreachMessage, Meeting,
│                                        PipelineStage, ResponseClassification, OutreachStatus
├── research/                           MINE — built and smoke-tested
│   ├── config.py                       RESEARCH_MODE=mock|live toggle, reads .env
│   ├── search_client.py                Tavily/Serper wrapper (live mode only)
│   ├── llm_extract.py                  search snippets -> structured findings (live mode only)
│   ├── mock_data.py                    canned ResearchFindings: MetroCart, HarborHomes,
│                                        VectorWorks, TinyCo (deliberately weak-fit)
│   └── deep_research.py                run_deep_research(company_name, icp) -> ResearchFindings
├── qualification/                      MINE — scaffolded, NOT built yet
│   └── qualification.py                run_qualification / match_service /
│                                        identify_decision_makers — signatures only right now
├── tests/
│   └── test_deep_research.py
├── main.py                             EXISTING — not mine
├── .env.example                        EXISTING — shared, only ever append to it
└── requirements.txt
```

## Stack

Python + FastAPI backend, Pydantic v2 schemas (see shared/schema.py above — always populate
these exact types, never redefine local shapes). LLM calls via Anthropic or OpenAI (provider
swappable through one function). Web search via Tavily or Serper. Everything in `research/`
and `qualification/` runs in `RESEARCH_MODE=mock` by default against canned company data, so
it's testable with zero live API keys — flip one env var for real search + LLM calls later.

## Status right now

- `research/` — built, tested, working against mock data (MetroCart, HarborHomes,
  VectorWorks, TinyCo all return valid `ResearchFindings`)
- `qualification/` — scaffolded only, not implemented
- Frontend — not started

## Ground rules for you

- Stay inside `research/` and `qualification/` unless I explicitly ask you to touch something
  else.
- Never modify `shared/schema.py` or `main.py`.
- Never invent a NexaFlow capability, price, or guarantee that isn't grounded in the dossier
  facts described above.
- Default to `RESEARCH_MODE=mock` for anything you build or test — don't assume live API keys
  are available.
- Populate the shared Pydantic types exactly as defined; don't create parallel data shapes.

## Right now, I'm working on:

<< fill this in each session — e.g. "building run_qualification() in qualification.py,
scoring against the four mock companies" or "building the pipeline dashboard frontend" >>
