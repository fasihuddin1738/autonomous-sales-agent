"""
Streamlit dashboard: pipeline kanban view + per-lead detail/actions.

Run with:
    streamlit run dashboard/app.py

Reads/writes directly through pipeline.lead_store (same SQLite file the API
uses), so this works standalone against mock leads, or against real leads
once the team's app is writing into the same store.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone

import streamlit as st

from outreach.email_generator import generate_email
from outreach.email_sender import send_email
from outreach.follow_up_scheduler import run_follow_up_for_lead, state_from_lead, decide_follow_up
from outreach.meeting import schedule_meeting, send_admin_briefing
from outreach.response_classifier import classify_and_record
from pipeline.lead_store import lead_store
from pipeline.stage_tracker import InvalidStageTransition, advance_stage
from pipeline.stubs.mock_leads import all_mock_leads
from shared.schema import PipelineStage

st.set_page_config(page_title="NexaFlow Outreach Pipeline", layout="wide")
st.title("🚀 NexaFlow AI — Outreach Pipeline")

with st.sidebar:
    st.header("Dev tools")
    if st.button("Seed mock leads"):
        for lead in all_mock_leads():
            lead_store.save(lead)
        st.success("Seeded 6 mock leads.")
        st.rerun()
    if st.button("Clear all leads", type="secondary"):
        lead_store.delete_all()
        st.warning("Cleared all leads.")
        st.rerun()
    dry_run = st.checkbox("Dry run (don't actually send emails)", value=True)

leads = lead_store.all()

if not leads:
    st.info("No leads yet — click **Seed mock leads** in the sidebar to get started.")
    st.stop()

# --- Kanban-style overview ---
stage_order = [
    PipelineStage.DISCOVERED, PipelineStage.POTENTIAL, PipelineStage.RESEARCHING,
    PipelineStage.QUALIFIED, PipelineStage.CONTACTED, PipelineStage.INTERESTED,
    PipelineStage.MEETING_SCHEDULED, PipelineStage.CONVERTED,
]
terminal_negative = [PipelineStage.NOT_QUALIFIED, PipelineStage.NOT_INTERESTED, PipelineStage.DO_NOT_CONTACT]

st.subheader("Pipeline overview")
cols = st.columns(len(stage_order))
for col, stage in zip(cols, stage_order):
    stage_leads = [l for l in leads if l.pipeline_stage == stage]
    with col:
        st.markdown(f"**{stage.value}**  \n({len(stage_leads)})")
        for lead in stage_leads:
            st.caption(f"• {lead.company_name}")

if any(l.pipeline_stage in terminal_negative for l in leads):
    with st.expander(f"Closed-out leads ({sum(l.pipeline_stage in terminal_negative for l in leads)})"):
        for l in leads:
            if l.pipeline_stage in terminal_negative:
                st.write(f"{l.company_name} — {l.pipeline_stage.value}")

st.divider()

# --- Lead detail / actions ---
st.subheader("Lead detail")
lead_names = {f"{l.company_name} ({l.pipeline_stage.value})": l.id for l in leads}
selected_label = st.selectbox("Select a lead", list(lead_names.keys()))
lead = lead_store.get(lead_names[selected_label])

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown(f"### {lead.company_name}")
    st.write(f"**Stage:** {lead.pipeline_stage.value}")
    if lead.qualification:
        st.write(f"**Qualification score:** {lead.qualification.score}/100")
        st.write(f"**Reasoning:** {lead.qualification.reasoning}")
    st.write(f"**Recommended service:** {lead.recommended_service or '—'}")

    if lead.research.buying_signals:
        st.write("**Buying signals:**")
        for s in lead.research.buying_signals:
            st.write(f"- {s}")

    st.write("**Outreach history:**")
    if not lead.outreach:
        st.caption("No outreach sent yet.")
    for msg in lead.outreach:
        with st.expander(f"{msg.subject} — {msg.status.value}"):
            st.text(msg.body)
            st.caption(f"Evidence used: {', '.join(msg.evidence_used) or 'none'}")
            if msg.reply_text:
                st.write(f"**Reply:** {msg.reply_text}")
                st.write(f"**Classified as:** {msg.reply_classification.value if msg.reply_classification else '—'}")

    if lead.meeting and lead.meeting.scheduled_time:
        st.write("**Meeting:**")
        st.write(f"- Time: {lead.meeting.scheduled_time}")
        st.write(f"- Link: {lead.meeting.meeting_link}")
        if lead.meeting.briefing:
            with st.expander("Admin briefing"):
                st.text(lead.meeting.briefing)

    if lead.memory_log:
        with st.expander("Memory log"):
            for entry in lead.memory_log:
                st.caption(entry)

with col_b:
    st.markdown("### Actions")

    if st.button("Draft email", key="draft"):
        contact = min(lead.decision_makers, key=lambda dm: dm.priority) if lead.decision_makers else None
        if contact:
            msg = generate_email(lead, contact)
            lead.outreach.append(msg)
            lead_store.save(lead)
            st.success(f"Drafted: {msg.subject}")
            st.rerun()
        else:
            st.error("No decision makers on this lead.")

    unsent = [m for m in lead.outreach if m.status.value == "Drafted"]
    if unsent:
        if st.button(f"Send latest draft ({unsent[-1].subject[:30]}...)", key="send"):
            send_email(lead, unsent[-1], dry_run=dry_run)
            lead_store.save(lead)
            st.success("Sent." if not dry_run else "Sent (dry run).")
            st.rerun()

    st.divider()
    reply_text = st.text_area("Simulate inbound reply", key="reply_box")
    if st.button("Submit reply", key="submit_reply") and reply_text and lead.outreach:
        classify_and_record(lead, lead.outreach[-1], reply_text)
        lead_store.save(lead)
        st.rerun()

    st.divider()
    state = state_from_lead(lead)
    decision = decide_follow_up(state)
    st.caption(f"Follow-up: {decision.reason}")
    if decision.should_send and st.button("Send follow-up now", key="followup"):
        run_follow_up_for_lead(lead, dry_run=dry_run)
        lead_store.save(lead)
        st.rerun()

    st.divider()
    meeting_time = st.time_input("Schedule meeting for (today, UTC)", key="meeting_time")
    if st.button("Schedule meeting", key="schedule"):
        dt = datetime.combine(datetime.now(timezone.utc).date(), meeting_time, tzinfo=timezone.utc)
        schedule_meeting(lead, dt)
        lead_store.save(lead)
        st.rerun()

    if lead.meeting and lead.meeting.scheduled_time and not lead.meeting.admin_reminder_sent:
        if st.button("Send admin briefing now", key="briefing"):
            send_admin_briefing(lead, dry_run=dry_run)
            lead_store.save(lead)
            st.rerun()

    st.divider()
    next_stages = sorted({s for s in PipelineStage} - {lead.pipeline_stage})
    target = st.selectbox("Move to stage", [s.value for s in next_stages], key="stage_select")
    if st.button("Apply stage change", key="apply_stage"):
        try:
            advance_stage(lead, PipelineStage(target), reason="manual override from dashboard")
            lead_store.save(lead)
            st.rerun()
        except InvalidStageTransition as e:
            st.error(str(e))
