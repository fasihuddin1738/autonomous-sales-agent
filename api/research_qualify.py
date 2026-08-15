"""
api/research_qualify.py

FastAPI router for the research-qualify module. Mount in main.py:

    from api.research_qualify import router as research_router
    app.include_router(research_router, prefix="/research", tags=["Research & Qualification"])

Only exposes endpoints for what this module owns: deep research, qualification
scoring, service matching (grounded via RAG), and decision-maker identification.
No discovery or outreach endpoints here.

Design note: discovery's /discovery/discover endpoint returns Lead objects but
does NOT persist them to lead_store. This router accepts leads directly in the
request body (as returned by /discovery/discover) rather than requiring they
already exist in the store — this keeps the discovery router untouched and
avoids two people editing the same file. Every endpoint here PERSISTS its
result to lead_store, so once a lead has been processed here, it shows up in
/outreach/leads for the pipeline view.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.schema import ICP, Lead
from research.deep_research import run_deep_research
from qualification.qualification import (
    run_qualification,
    match_service,
    identify_decision_makers,
)
from rag.retrieve import retrieve_context
from pipeline.lead_store import lead_store

router = APIRouter()


def _rag_lookup(query: str) -> str:
    """Adapts retrieve_context (list[str]) into the single-string shape
    match_service expects for its rag_lookup callable."""
    return "\n".join(retrieve_context(query, top_k=3))


def _process_lead(lead: Lead, icp: ICP) -> Lead:
    """Runs the full research -> qualify -> match service -> decision-makers
    chain on one lead in place, then returns it. Does not persist —
    callers are responsible for saving to lead_store."""
    lead.research = run_deep_research(lead.company_name, icp)
    lead.log("Deep research completed")

    lead.qualification = run_qualification(lead, icp)
    lead.log(f"Qualification: {lead.qualification.score}/100 ({'qualified' if lead.qualification.is_qualified else 'not qualified'})")

    lead.recommended_service = match_service(lead, rag_lookup=_rag_lookup)
    lead.log(f"Recommended service: {lead.recommended_service}")

    lead.decision_makers = identify_decision_makers(lead)
    lead.log(f"Identified {len(lead.decision_makers)} decision-maker targets")

    return lead


# ---------- Single lead ----------

class ProcessLeadRequest(BaseModel):
    lead: Lead
    icp: ICP


@router.post("/process", response_model=Lead)
def process_lead(body: ProcessLeadRequest):
    """
    Runs research + qualification + service matching + decision-maker ID
    on a single lead (e.g. one item from /discovery/discover's response),
    persists it to lead_store, and returns the fully populated Lead.
    """
    lead = _process_lead(body.lead, body.icp)
    lead_store.save(lead)
    return lead


# ---------- Batch ----------

class ProcessBatchRequest(BaseModel):
    leads: list[Lead]
    icp: ICP
    limit: int | None = None  # cap how many leads to process; None = process all


class ProcessBatchResponse(BaseModel):
    processed: int
    qualified: int
    skipped: int
    leads: list[Lead]


@router.post("/process-batch", response_model=ProcessBatchResponse)
def process_batch(body: ProcessBatchRequest):
    """
    Runs the full research/qualify/match/decision-maker chain over a list
    of leads (typically the output of POST /discovery/discover), persists
    each to lead_store, and returns them all with a qualified-count summary.

    This is the endpoint the frontend should call right after discovery to
    move leads from Discovered/Potential into a fully qualified state.

    Pass `limit` to cap how many leads get processed (useful for fast test
    runs / demos instead of always processing every discovered lead) — the
    rest are returned in `skipped` count and left untouched/unpersisted.
    """
    leads_to_process = body.leads[: body.limit] if body.limit is not None else body.leads
    skipped_count = len(body.leads) - len(leads_to_process)

    processed_leads: list[Lead] = []
    for lead in leads_to_process:
        try:
            processed = _process_lead(lead, body.icp)
            lead_store.save(processed)
            processed_leads.append(processed)
        except Exception as e:
            lead.log(f"Processing failed: {e}")
            lead_store.save(lead)
            processed_leads.append(lead)

    qualified_count = sum(1 for l in processed_leads if l.qualification and l.qualification.is_qualified)

    return ProcessBatchResponse(
        processed=len(processed_leads),
        qualified=qualified_count,
        skipped=skipped_count,
        leads=processed_leads,
    )


# ---------- Re-run a single step (useful for demo / debugging) ----------

@router.get("/leads/{lead_id}", response_model=Lead)
def get_processed_lead(lead_id: str):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    return lead
