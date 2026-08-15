"""
Classifies an inbound reply into shared.schema.ResponseClassification.

Two paths, same pattern as email_generator.py:
- classify_llm(): Claude call constrained to return one of the exact enum values.
- classify_keyword(): dependency-free fallback so classification still works
  offline/without a key (and gives tests something deterministic to assert on).
"""
from __future__ import annotations

import json
import re

from config import settings
from pipeline.memory import MemoryEntry, long_term
from shared.schema import Lead, OutreachMessage, ResponseClassification

_VALID_VALUES = [c.value for c in ResponseClassification]

SYSTEM_PROMPT = f"""You classify inbound sales email replies into exactly one of these \
categories: {json.dumps(_VALID_VALUES)}.

Guidance:
- "Positive / Interested" - general enthusiasm, no explicit meeting ask yet.
- "Meeting Requested" - explicitly asks to schedule a call/meeting, or proposes a time.
- "Question" - asks for more info without objecting or committing.
- "Pricing Objection" - pushes back specifically on cost/budget.
- "Technical Objection" - pushes back on integration, security, technical fit.
- "Not Interested" - explicit decline.
- "Not Now" - interested in principle but bad timing (e.g. "check back next quarter").
- "Wrong Person / Referral" - says they're not the right contact, may point elsewhere.
- "Other" - anything that doesn't clearly fit above (auto-replies, out-of-office, spam).

Return ONLY valid JSON, no markdown fences: {{"classification": "<one of the exact values above>"}}"""


# Ordered keyword fallback — order matters, first match wins.
_KEYWORD_RULES: list[tuple[ResponseClassification, list[str]]] = [
    (ResponseClassification.WRONG_PERSON, ["wrong person", "not the right contact", "forward this to", "reach out to"]),
    (ResponseClassification.MEETING_REQUESTED, ["schedule a call", "set up a call", "book a time", "calendar link", "let's meet", "available to talk", "can we set up"]),
    (ResponseClassification.PRICING_OBJECTION, ["too expensive", "budget", "pricing", "cost", "price"]),
    (ResponseClassification.TECHNICAL_OBJECTION, ["security concern", "integrat", "doesn't support", "compliance", "infosec"]),
    (ResponseClassification.NOT_NOW, ["not right now", "check back", "next quarter", "revisit later", "bad timing"]),
    (ResponseClassification.NOT_INTERESTED, ["not interested", "no thanks", "please remove", "unsubscribe", "stop contacting"]),
    (ResponseClassification.QUESTION, ["how does", "what is", "can you explain", "?"]),
    (ResponseClassification.POSITIVE, ["interesting", "sounds great", "love this", "tell me more", "keen"]),
]


def classify_keyword(reply_text: str) -> ResponseClassification:
    text = reply_text.lower()
    for classification, keywords in _KEYWORD_RULES:
        if any(kw in text for kw in keywords):
            return classification
    return ResponseClassification.OTHER


def classify_llm(reply_text: str) -> ResponseClassification:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Reply to classify:\n\n{reply_text}"}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)
    value = data["classification"]
    return ResponseClassification(value)  # raises ValueError if not an exact match


def classify_reply(reply_text: str) -> ResponseClassification:
    if settings.ANTHROPIC_API_KEY:
        try:
            return classify_llm(reply_text)
        except Exception:
            return classify_keyword(reply_text)
    return classify_keyword(reply_text)


def classify_and_record(lead: Lead, message: OutreachMessage, reply_text: str) -> ResponseClassification:
    """Classify a reply and write the result back onto the message + memory log."""
    classification = classify_reply(reply_text)
    message.reply_text = reply_text
    message.reply_classification = classification

    lead.log(f"Reply classified as '{classification.value}'.")
    long_term.append(MemoryEntry(
        lead_id=lead.id,
        entry_type="classification",
        payload={"outreach_message_id": message.id, "classification": classification.value},
    ))
    return classification
