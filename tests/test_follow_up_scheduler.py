import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from outreach.follow_up_scheduler import FollowUpState, decide_follow_up, FollowUpScheduler


def _dt(days_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def test_no_outbound_yet_no_follow_up():
    state = FollowUpState("lead1", None, False, 0, False)
    decision = decide_follow_up(state)
    assert decision.should_send is False


def test_follow_up_due_after_3_days():
    state = FollowUpState("lead1", _dt(3.01), False, 0, False)
    decision = decide_follow_up(state)
    assert decision.should_send is True


def test_follow_up_not_due_before_3_days():
    state = FollowUpState("lead1", _dt(1.5), False, 0, False)
    decision = decide_follow_up(state)
    assert decision.should_send is False


def test_no_follow_up_if_replied():
    state = FollowUpState("lead1", _dt(5), True, 0, False)
    decision = decide_follow_up(state)
    assert decision.should_send is False
    assert "replied" in decision.reason


def test_no_follow_up_if_terminal_stage():
    state = FollowUpState("lead1", _dt(5), False, 0, True)
    decision = decide_follow_up(state)
    assert decision.should_send is False
    assert "terminal" in decision.reason


def test_no_double_follow_up():
    state = FollowUpState("lead1", _dt(5), False, 1, False)  # already sent max
    decision = decide_follow_up(state)
    assert decision.should_send is False


def test_scheduler_scan_picks_up_due_leads():
    scheduler = FollowUpScheduler()
    states = [
        FollowUpState("due", _dt(4), False, 0, False),
        FollowUpState("not_due", _dt(1), False, 0, False),
        FollowUpState("replied", _dt(4), True, 0, False),
    ]
    due = scheduler.scan_and_get_due(states)
    assert [s.lead_id for s in due] == ["due"]
