"""
FastAPI router for the outreach-pipeline module. Mount this in the team's
main FastAPI app, e.g.:

    from api.routes import router as outreach_router
    app.include_router(outreach_router, prefix="/outreach", tags=["outreach"])

Only exposes endpoints for what THIS branch owns — no RAG/discovery/research
endpoints here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
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
