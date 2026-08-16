"""
FastAPI router for the outreach-pipeline module. Mount this in the team's
main FastAPI app, e.g.:

    from api.routes import router as outreach_router
    app.include_router(outreach_router, prefix="/outreach", tags=["outreach"])

Only exposes endpoints for what THIS branch owns — no RAG/discovery/research
endpoints here.
"""
from __future__ import annotations

import asyncio
import ctypes
import threading
from datetime import datetime
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from outreach.email_generator import generate_email
from outreach.email_sender import send_email
from outreach.follow_up_scheduler import (
    FollowUpState,
    run_follow_up_for_lead,
    state_from_lead,
)
from outreach.meeting import build_briefing_text, schedule_meeting, send_admin_briefing
from outreach.response_classifier import classify_and_record
from pipeline.lead_store import lead_store
from pipeline.stage_tracker import InvalidStageTransition, advance_stage
from shared.schema import Lead, PipelineStage

router = APIRouter()

# ---------- Pipeline cancellation state ----------
# _cancel_event: set by cancel-pipeline, cleared by reset-pipeline.
# _discovery_state: holds a reference to the active discovery thread so
#   cancel_pipeline() can inject SystemExit into it via ctypes, stopping
#   retry loops and sleep delays as soon as Python re-enters the GIL.
_cancel_event = threading.Event()
_discovery_state: dict = {"thread": None}
_thread_lock = threading.Lock()


def _kill_thread(t: threading.Thread) -> None:
    """
    Best-effort forceful thread termination via async exception injection.
    Raises SystemExit inside the target thread at the next Python bytecode
    boundary. Interrupts time.sleep() delays immediately; HTTP calls finish
    their current response before the exception fires (~1-5 s).
    """
    try:
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(t.ident),
            ctypes.py_object(SystemExit),
        )
        if res > 1:
            # Affected too many threads — undo
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(t.ident), None
            )
    except Exception:
        pass


def pipeline_cancelled() -> bool:
    return _cancel_event.is_set()


@router.post("/cancel-pipeline")
def cancel_pipeline():
    """
    Stop the running pipeline. Sets the cancel flag AND injects SystemExit
    into the active discovery thread (if any), terminating retry loops and
    sleep delays immediately without restarting the uvicorn process.
    """
    _cancel_event.set()
    with _thread_lock:
        t = _discovery_state.get("thread")
        if t and t.is_alive():
            _kill_thread(t)
    return {"cancelled": True}


@router.post("/reset-pipeline")
def reset_pipeline():
    """Clear the cancellation flag before starting a new pipeline run."""
    _cancel_event.clear()
    return {"reset": True}


# ---------- Discovery proxy (cancellable) ----------

class ProxyDiscoverRequest(BaseModel):
    target_location: str
    target_industry: str
    company_size: str | None = None
    special_focus: str | None = None
    max_results_per_query: int = 5


@router.post("/proxy-discover")
async def proxy_discover(body: ProxyDiscoverRequest, request: Request):
    """
    Runs run_discovery() in a tracked daemon thread. When the user clicks Stop:
      1. cancel-pipeline sets _cancel_event AND injects SystemExit into the thread
      2. This endpoint detects _cancel_event within 0.5 s and returns cancelled
      3. The thread receives SystemExit at the next Python bytecode boundary,
         stopping retry delays (time.sleep) immediately and Groq calls after
         the current HTTP response completes (~1-5 s).
    """
    from discovery.pipeline import run_discovery
    from shared.schema import ICP as ICPSchema

    icp = ICPSchema(
        target_location=body.target_location,
        target_industry=body.target_industry,
        company_size=body.company_size,
        special_focus=body.special_focus,
    )

    result_box: list = []
    err_box: list = []

    def _worker() -> None:
        # Register this thread so cancel_pipeline() can kill it
        with _thread_lock:
            _discovery_state["thread"] = threading.current_thread()
        try:
            leads = run_discovery(icp, max_results_per_query=body.max_results_per_query)
            result_box.append(leads)
        except SystemExit:
            pass  # Killed by cancel_pipeline() — clean exit
        except Exception as e:
            err_box.append(e)
        finally:
            with _thread_lock:
                _discovery_state["thread"] = None

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    # Poll every 0.5 s: return early if cancelled, otherwise wait for completion
    while t.is_alive():
        if _cancel_event.is_set():
            _kill_thread(t)          # belt-and-suspenders in case cancel arrived
            return {"count": 0, "leads": [], "cancelled": True}  # before kill_thread call
        await asyncio.sleep(0.5)

    if err_box:
        raise HTTPException(status_code=500, detail=str(err_box[0]))

    leads = result_box[0] if result_box else []
    return {"count": len(leads), "leads": [lead.model_dump() for lead in leads]}


# ---------- Leads ----------

@router.get("/leads", response_model=list[Lead])
def list_leads(stage: Optional[PipelineStage] = None):
    return lead_store.by_stage(stage) if stage else lead_store.all()


@router.get("/leads/{lead_id}", response_model=Lead)
def get_lead(lead_id: str):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    return lead


@router.post("/leads/{lead_id}/stage", response_model=Lead)
def set_stage(lead_id: str, target: PipelineStage, reason: Optional[str] = None):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    try:
        advance_stage(lead, target, reason=reason)
    except InvalidStageTransition as e:
        raise HTTPException(400, str(e))
    lead_store.save(lead)
    return lead


# ---------- Outreach ----------

@router.post("/leads/{lead_id}/draft-email", response_model=Lead)
def draft_email(lead_id: str, contact_email: Optional[str] = None):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    contact = None
    if contact_email:
        contact = next((dm for dm in lead.decision_makers if dm.email == contact_email), None)
        if not contact:
            raise HTTPException(404, f"No decision maker with email {contact_email} on this lead")
    message = generate_email(lead, contact)
    lead.outreach.append(message)
    lead_store.save(lead)
    return lead


class SendEmailRequest(BaseModel):
    outreach_message_id: str
    dry_run: bool = False


@router.post("/leads/{lead_id}/send-email", response_model=Lead)
def send_drafted_email(lead_id: str, body: SendEmailRequest):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    message = next((m for m in lead.outreach if m.id == body.outreach_message_id), None)
    if not message:
        raise HTTPException(404, "OutreachMessage not found on this lead")
    send_email(lead, message, dry_run=body.dry_run)
    lead_store.save(lead)
    return lead


class ReplyRequest(BaseModel):
    outreach_message_id: str
    reply_text: str


@router.post("/leads/{lead_id}/reply", response_model=Lead)
def receive_reply(lead_id: str, body: ReplyRequest):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    message = next((m for m in lead.outreach if m.id == body.outreach_message_id), None)
    if not message:
        raise HTTPException(404, "OutreachMessage not found on this lead")
    classify_and_record(lead, message, body.reply_text)
    lead_store.save(lead)
    return lead


@router.post("/leads/{lead_id}/run-follow-up", response_model=Lead)
def trigger_follow_up(lead_id: str, dry_run: bool = True):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    run_follow_up_for_lead(lead, dry_run=dry_run)
    lead_store.save(lead)
    return lead


@router.post("/follow-ups/scan")
def scan_follow_ups(dry_run: bool = True):
    """Cron-style endpoint: call on a timer to fire all due follow-ups."""
    sent = []
    for lead in lead_store.all():
        result = run_follow_up_for_lead(lead, dry_run=dry_run)
        if result:
            lead_store.save(lead)
            sent.append({"lead_id": lead.id, "company_name": lead.company_name})
    return {"follow_ups_sent": sent}


# ---------- Meetings ----------

class ScheduleMeetingRequest(BaseModel):
    scheduled_time: datetime


@router.post("/leads/{lead_id}/schedule-meeting", response_model=Lead)
def schedule_meeting_endpoint(lead_id: str, body: ScheduleMeetingRequest):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    schedule_meeting(lead, body.scheduled_time)
    lead_store.save(lead)
    return lead


@router.post("/leads/{lead_id}/send-briefing", response_model=Lead)
def send_briefing_endpoint(lead_id: str, dry_run: bool = True):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    if not lead.meeting:
        raise HTTPException(400, "Lead has no scheduled meeting")
    send_admin_briefing(lead, dry_run=dry_run)
    lead_store.save(lead)
    return lead


# ---------- Debug / seed (dev only — remove before final demo if desired) ----------

@router.post("/debug/seed-mock-leads")
def seed_mock_leads():
    from pipeline.stubs.mock_leads import all_mock_leads
    leads = all_mock_leads()
    for lead in leads:
        lead_store.save(lead)
    return {"seeded": len(leads)}
