import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from pipeline.stage_tracker import InvalidStageTransition, advance_stage, can_transition, is_terminal
from pipeline.stubs.mock_leads import make_qualified_lead_no_outreach
from shared.schema import PipelineStage


def test_valid_transition_qualified_to_contacted():
    lead = make_qualified_lead_no_outreach()
    advance_stage(lead, PipelineStage.CONTACTED)
    assert lead.pipeline_stage == PipelineStage.CONTACTED


def test_invalid_transition_raises():
    lead = make_qualified_lead_no_outreach()
    with pytest.raises(InvalidStageTransition):
        advance_stage(lead, PipelineStage.CONVERTED)  # can't skip straight there


def test_do_not_contact_always_allowed():
    lead = make_qualified_lead_no_outreach()
    assert can_transition(PipelineStage.QUALIFIED, PipelineStage.DO_NOT_CONTACT)
    advance_stage(lead, PipelineStage.DO_NOT_CONTACT)
    assert lead.pipeline_stage == PipelineStage.DO_NOT_CONTACT


def test_terminal_stage_detection():
    lead = make_qualified_lead_no_outreach()
    assert not is_terminal(lead)
    advance_stage(lead, PipelineStage.NOT_QUALIFIED)
    assert is_terminal(lead)


def test_stage_change_logged():
    lead = make_qualified_lead_no_outreach()
    log_len_before = len(lead.memory_log)
    advance_stage(lead, PipelineStage.CONTACTED, reason="test")
    assert len(lead.memory_log) == log_len_before + 1
    assert "Contacted" in lead.memory_log[-1]
