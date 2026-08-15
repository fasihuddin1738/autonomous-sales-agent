"""
shared/schema.py

Single source of truth for data structures used across the pipeline:
RAG/ICP -> Discovery -> Research -> Qualification -> Outreach -> Memory -> Pipeline.

Rule: don't edit this file solo. If you need a new field, ping the team first.
Everyone imports from here instead of redefining these shapes locally.
"""

from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    DISCOVERED = "Discovered"
    POTENTIAL = "Potential"
    RESEARCHING = "Researching"
    QUALIFIED = "Qualified"
    CONTACTED = "Contacted"
    INTERESTED = "Interested"
    MEETING_SCHEDULED = "Meeting Scheduled"
    CONVERTED = "Converted"
    NOT_QUALIFIED = "Not Qualified"
    NOT_INTERESTED = "Not Interested"
    DO_NOT_CONTACT = "Do Not Contact"


class ResponseClassification(str, Enum):
    POSITIVE = "Positive / Interested"
    MEETING_REQUESTED = "Meeting Requested"
    QUESTION = "Question"
    PRICING_OBJECTION = "Pricing Objection"
    TECHNICAL_OBJECTION = "Technical Objection"
    NOT_INTERESTED = "Not Interested"
    NOT_NOW = "Not Now"
    WRONG_PERSON = "Wrong Person / Referral"
    OTHER = "Other"


class OutreachStatus(str, Enum):
    DRAFTED = "Drafted"
    SENT = "Sent"
    REPLIED = "Replied"
    BOUNCED = "Bounced"
    FOLLOWED_UP = "Followed Up"


# ---------------------------------------------------------------------------
# ICP (Ideal Customer Profile) — captured once per session/user
# ---------------------------------------------------------------------------

class ICP(BaseModel):
    target_location: str
    target_industry: str
    company_size: Optional[str] = None          # e.g. "10-50 employees"
    special_focus: Optional[str] = None          # e.g. "high WhatsApp inquiry volume"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Research sub-structures
# ---------------------------------------------------------------------------

class ResearchFindings(BaseModel):
    website: Optional[str] = None
    employees_estimate: Optional[str] = None
    key_departments: list[str] = Field(default_factory=list)
    recent_news: list[str] = Field(default_factory=list)
    funding_signal: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    raw_notes: Optional[str] = None               # free-text fallback for anything unstructured


class Qualification(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str                                 # human-readable explanation for the score
    factors: list[str] = Field(default_factory=list)  # e.g. ["ICP fit", "buying signal: hiring support"]
    is_qualified: bool


class DecisionMaker(BaseModel):
    name: Optional[str] = None
    role: str                                       # e.g. "Head of Sales", "CTO"
    email: Optional[str] = None
    linkedin: Optional[str] = None
    priority: int = 1                                # 1 = most relevant to the recommended service


class OutreachMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contact: DecisionMaker
    subject: str
    body: str
    evidence_used: list[str] = Field(default_factory=list)   # what facts grounded the personalization
    status: OutreachStatus = OutreachStatus.DRAFTED
    sent_at: Optional[datetime] = None
    reply_text: Optional[str] = None
    reply_classification: Optional[ResponseClassification] = None
    follow_up_count: int = 0
    next_follow_up_at: Optional[datetime] = None


class Meeting(BaseModel):
    scheduled_time: Optional[datetime] = None
    meeting_link: Optional[str] = None
    briefing: Optional[str] = None                   # short summary: problem, service, objections, key points
    admin_reminder_sent: bool = False


# ---------------------------------------------------------------------------
# The core Lead object — the backbone every module reads/writes
# ---------------------------------------------------------------------------

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    source: Optional[str] = None                     # where it was discovered (search query, etc.)
    icp_fit_notes: Optional[str] = None

    research: ResearchFindings = Field(default_factory=ResearchFindings)
    qualification: Optional[Qualification] = None
    recommended_service: Optional[str] = None         # must map to a real NexaFlow offering
    decision_makers: list[DecisionMaker] = Field(default_factory=list)

    outreach: list[OutreachMessage] = Field(default_factory=list)
    meeting: Optional[Meeting] = None

    pipeline_stage: PipelineStage = PipelineStage.DISCOVERED
    memory_log: list[str] = Field(default_factory=list)   # timestamped short notes of what happened

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def log(self, note: str) -> None:
        """Helper: append a timestamped entry to memory_log and bump updated_at."""
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        self.memory_log.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.utcnow()
