"""
Pipeline stage transitions. Encodes the valid stage graph so nothing can jump
from Discovered straight to Converted, etc., and logs every transition to
the lead's memory_log + long-term memory.

Note: Discovered -> Researching/Qualified/Not Qualified are owned by
teammates' research/qualification code, not this module — but the graph is
defined here (single source of truth for the whole team) so nobody encodes
conflicting rules in two places. Ping the team before changing edges, same
spirit as shared/schema.py.
"""
from __future__ import annotations

from pipeline.memory import MemoryEntry, long_term
from shared.schema import Lead, PipelineStage

TERMINAL_STAGES = {
    PipelineStage.CONVERTED,
    PipelineStage.NOT_QUALIFIED,
    PipelineStage.NOT_INTERESTED,
    PipelineStage.DO_NOT_CONTACT,
}

# Adjacency list: allowed forward/side transitions from each stage.
# Any stage can move to DO_NOT_CONTACT (opt-out/compliance override).
_VALID_TRANSITIONS: dict[PipelineStage, set[PipelineStage]] = {
    PipelineStage.DISCOVERED: {PipelineStage.POTENTIAL, PipelineStage.NOT_QUALIFIED},
    PipelineStage.POTENTIAL: {PipelineStage.RESEARCHING, PipelineStage.NOT_QUALIFIED},
    PipelineStage.RESEARCHING: {PipelineStage.QUALIFIED, PipelineStage.NOT_QUALIFIED},
    PipelineStage.QUALIFIED: {PipelineStage.CONTACTED, PipelineStage.NOT_QUALIFIED},
    PipelineStage.CONTACTED: {
        PipelineStage.INTERESTED,
        PipelineStage.NOT_INTERESTED,
        PipelineStage.CONTACTED,  # re-contacted / follow-up sent, stays Contacted
    },
    PipelineStage.INTERESTED: {
        PipelineStage.MEETING_SCHEDULED,
        PipelineStage.NOT_INTERESTED,
    },
    PipelineStage.MEETING_SCHEDULED: {
        PipelineStage.CONVERTED,
        PipelineStage.NOT_INTERESTED,
        PipelineStage.INTERESTED,  # meeting fell through, back to nurturing
    },
    PipelineStage.CONVERTED: set(),
    PipelineStage.NOT_QUALIFIED: set(),
    PipelineStage.NOT_INTERESTED: set(),
    PipelineStage.DO_NOT_CONTACT: set(),
}


class InvalidStageTransition(Exception):
    pass


def can_transition(current: PipelineStage, target: PipelineStage) -> bool:
    if target == PipelineStage.DO_NOT_CONTACT:
        return True  # always allowed — compliance/opt-out override
    if current == target:
        return True  # no-op is fine
    return target in _VALID_TRANSITIONS.get(current, set())


def advance_stage(lead: Lead, target: PipelineStage, reason: str | None = None) -> Lead:
    current = lead.pipeline_stage
    if not can_transition(current, target):
        raise InvalidStageTransition(
            f"Cannot move '{lead.company_name}' from {current.value} to {target.value}. "
            f"Valid next stages from {current.value}: "
            f"{sorted(s.value for s in _VALID_TRANSITIONS.get(current, set()))}"
        )

    lead.pipeline_stage = target
    note = f"Stage change: {current.value} -> {target.value}"
    if reason:
        note += f" ({reason})"
    lead.log(note)

    long_term.append(MemoryEntry(
        lead_id=lead.id,
        entry_type="stage_change",
        payload={"from": current.value, "to": target.value, "reason": reason},
    ))
    return lead


def is_terminal(lead: Lead) -> bool:
    return lead.pipeline_stage in TERMINAL_STAGES
