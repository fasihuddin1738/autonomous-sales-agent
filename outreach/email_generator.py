"""
Personalized outreach email generation.

Rule: every email must be grounded in the Lead's research/qualification data.
Never invent facts, metrics, or claims not present on the Lead. Every
generated OutreachMessage carries `evidence_used`, a list of the exact facts
pulled from `lead.research` / `lead.qualification` that justify the
personalization — this makes grounding auditable, not just a prompt promise.

Two paths:
- generate_email_llm(): calls Claude to draft based on a strict, evidence-only
  prompt. Used when ANTHROPIC_API_KEY is set.
- generate_email_template(): a deterministic, no-network fallback so the
  pipeline still works offline / without a key (useful for hackathon demo
  reliability and for tests).

generate_email() picks whichever is available.
"""
from __future__ import annotations

import json
from typing import Optional

from config import settings
from shared.schema import DecisionMaker, Lead, OutreachMessage, OutreachStatus

SYSTEM_PROMPT = """You are drafting a cold outreach email on behalf of NexaFlow AI, \
an AI automation agency. You will be given structured evidence about a prospect \
company (research findings, a qualification summary, and a recommended NexaFlow \
service) and the specific decision-maker you're writing to.

Hard rules:
1. Use ONLY the facts given to you. Never invent statistics, news, job postings, \
   tools, or claims that are not present in the evidence provided.
2. If the evidence is thin, write a shorter, more general email rather than padding \
   it with invented specifics.
3. Address the recipient's role directly — tailor the angle to what a person in that \
   role would care about (e.g. a Head of Support cares about ticket volume/backlog; \
   a COO cares about cost and headcount efficiency).
4. Keep it short: 80-130 words. One clear call to action (a quick call).
5. No hype, no "revolutionize your business" language. Be specific and low-pressure.
6. Return ONLY valid JSON, no markdown fences, no preamble, in this exact shape:
{"subject": "...", "body": "...", "evidence_used": ["fact 1", "fact 2"]}
Where "evidence_used" lists the exact evidence-provided facts (verbatim or lightly \
reworded) that you actually used in the email body — omit anything you didn't use."""


def _build_user_prompt(lead: Lead, contact: DecisionMaker) -> str:
    evidence = {
        "company_name": lead.company_name,
        "recipient_role": contact.role,
        "recipient_name": contact.name,
        "recommended_service": lead.recommended_service,
        "qualification_reasoning": lead.qualification.reasoning if lead.qualification else None,
        "qualification_factors": lead.qualification.factors if lead.qualification else [],
        "recent_news": lead.research.recent_news,
        "buying_signals": lead.research.buying_signals,
        "tech_stack": lead.research.tech_stack,
        "key_departments": lead.research.key_departments,
        "employees_estimate": lead.research.employees_estimate,
        "raw_notes": lead.research.raw_notes,
    }
    return (
        "Evidence (use only what's here):\n"
        + json.dumps(evidence, indent=2)
        + "\n\nDraft the outreach email now."
    )


def generate_email_llm(lead: Lead, contact: DecisionMaker) -> OutreachMessage:
    # pyrefly: ignore [missing-import]
    import anthropic  # local import: only required on this code path

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(lead, contact)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)

    return OutreachMessage(
        contact=contact,
        subject=data["subject"],
        body=data["body"],
        evidence_used=data.get("evidence_used", []),
        status=OutreachStatus.DRAFTED,
    )


def generate_email_template(lead: Lead, contact: DecisionMaker) -> OutreachMessage:
    """Deterministic fallback — no LLM, no network. Grounded but formulaic."""
    first_name = (contact.name or "there").split()[0] if contact.name else "there"
    signals = lead.research.buying_signals[:1]
    news = lead.research.recent_news[:1]
    evidence_used: list[str] = []

    hook_parts = []
    if signals:
        hook_parts.append(signals[0])
        evidence_used.append(signals[0])
    if news:
        hook_parts.append(news[0])
        evidence_used.append(news[0])
    hook = " ".join(hook_parts) if hook_parts else f"{lead.company_name} is on our radar as a strong fit for teams like yours."

    service = lead.recommended_service or "an automation solution tailored to your workflow"

    body = (
        f"Hi {first_name},\n\n"
        f"{hook} We work with companies like {lead.company_name} on {service.lower()}, "
        f"and thought it might be worth a quick conversation given your role as {contact.role}.\n\n"
        "Open to a short call this week?\n\nBest,\nNexaFlow AI"
    )
    subject = f"Quick idea for {lead.company_name}'s {contact.role.lower()} workflow"

    return OutreachMessage(
        contact=contact,
        subject=subject,
        body=body,
        evidence_used=evidence_used,
        status=OutreachStatus.DRAFTED,
    )


def generate_email(lead: Lead, contact: Optional[DecisionMaker] = None) -> OutreachMessage:
    """
    Main entry point. Defaults to the highest-priority decision maker if none
    is specified. Uses the LLM path if ANTHROPIC_API_KEY is configured,
    otherwise falls back to the template path.
    """
    if contact is None:
        if not lead.decision_makers:
            raise ValueError(f"Lead {lead.id} ({lead.company_name}) has no decision makers to write to.")
        contact = min(lead.decision_makers, key=lambda dm: dm.priority)

    if settings.ANTHROPIC_API_KEY:
        try:
            return generate_email_llm(lead, contact)
        except Exception:
            # Don't let a flaky API call block the pipeline mid-demo; fall back.
            return generate_email_template(lead, contact)
    return generate_email_template(lead, contact)


def generate_follow_up(lead: Lead, original: OutreachMessage) -> OutreachMessage:
    """
    Draft a brief, non-pushy follow-up referencing the original email.
    Reuses the same evidence (already grounded) rather than re-deriving new
    claims, and keeps it short since it's a bump, not a full re-pitch.
    """
    first_name = (original.contact.name or "there").split()[0] if original.contact.name else "there"
    body = (
        f"Hi {first_name},\n\n"
        f"Following up on my note about {lead.recommended_service.lower() if lead.recommended_service else 'this'} "
        f"for {lead.company_name} — know things get busy, so just bumping this up. "
        "Happy to keep it to 15 minutes if useful, otherwise no worries at all.\n\n"
        "Best,\nNexaFlow AI"
    )
    subject = f"Re: {original.subject}"
    return OutreachMessage(
        contact=original.contact,
        subject=subject,
        body=body,
        evidence_used=original.evidence_used,
        status=OutreachStatus.DRAFTED,
        follow_up_count=original.follow_up_count + 1,
    )
