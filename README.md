# outreach-pipeline (my branch scope)

AgentHack — NexaFlow AI sales agent. This branch owns everything downstream of
qualification: email generation, sending, reply classification, follow-ups,
meeting handling, memory, pipeline stage tracking, and the dashboard.

## Status legend
- done: built and tested against stub Leads (real `shared/schema.py`)
- todo: not started / nice-to-have

## Folder structure

```
outreach-pipeline/
├── shared/
│   └── schema.py               [done] verbatim copy of the team's shared schema
├── outreach/
│   ├── email_generator.py      [done] LLM-grounded draft, deterministic offline fallback
│   ├── email_sender.py         [done] Resend send + status/stage update + memory log
│   ├── response_classifier.py  [done] LLM classify, keyword fallback (6/6 tests pass)
│   ├── follow_up_scheduler.py  [done] Day-0 -> +3d logic, wired to real Lead
│   └── meeting.py              [done] meeting link + admin briefing generation/send
├── pipeline/
│   ├── stage_tracker.py        [done] validated PipelineStage transition graph
│   ├── memory.py               [done] short-term (in-proc) + long-term (SQLite) log
│   ├── lead_store.py           [done] Lead persistence (SQLite, JSON blob per lead)
│   └── stubs/
│       └── mock_leads.py       [done] 6 realistic fake leads across every stage
├── api/
│   └── routes.py               [done] FastAPI router — mount into the team's main app
├── dashboard/
│   └── app.py                  [done] Streamlit pipeline kanban + per-lead actions
├── main.py                     [done] standalone dev server (uvicorn main:app --reload)
├── config.py                   [done] env/config (Resend key, follow-up delay, etc.)
├── requirements.txt            [done]
└── tests/                      [done] 18 passing (scheduler, stage tracker, classifier)
```

## How to run it
```bash
pip install -r requirements.txt
# Set RESEND_API_KEY / ANTHROPIC_API_KEY as env vars when ready.
# Everything works without them too, via deterministic fallbacks.

pytest tests/ -q

# API:
uvicorn main:app --reload
curl -X POST localhost:8000/outreach/debug/seed-mock-leads
curl localhost:8000/outreach/leads

# Dashboard:
streamlit run dashboard/app.py
```

## Design notes / things to sanity-check with the team
- **No API keys needed to demo.** Both `email_generator` and
  `response_classifier` fall back to deterministic, non-LLM logic when
  `ANTHROPIC_API_KEY` isn't set (or if the API call throws mid-demo). Add the
  key to get much better-quality drafts/classification — everything else
  behaves identically either way.
- **`OutreachMessage` models one send + its reply on the same object**, not
  separate inbound/outbound messages. `follow_up_scheduler.state_from_lead()`
  and the reply/classify flow both lean on that — worth confirming this
  matches how your teammates' code writes to `Lead.outreach` too, since a
  second outbound message before a reply would currently look like a second
  "thread" rather than a follow-up on the first.
- **`pipeline/stage_tracker.py` owns the full `PipelineStage` graph**,
  including the `Discovered -> Researching -> Qualified` edges that are
  really your teammates' territory. I only *consume* those stages, but
  someone should eyeball the transition rules (`_VALID_TRANSITIONS`) so we're
  not enforcing a graph that contradicts how research/qualification actually
  moves leads.
- **`shared/schema.py` uses naive `datetime.utcnow()`** (deprecated in
  newer Python). Not touching it solo per the "ping the team first" rule at
  the top of that file, but flagging it — the deprecation warning shows up
  in every test run.
- **`recommended_service` is free text**: I added a `NEXAFLOW_SERVICES` list
  in `mock_leads.py` for consistent stub data, but the schema itself doesn't
  constrain it to an enum. Fine for a hackathon; flag if your qualification
  code and my email generator need to agree on exact service names.

## Scope reminder (not touching)
RAG, lead discovery, research, qualification — teammates' code. I only consume
a finished `Lead` object.
