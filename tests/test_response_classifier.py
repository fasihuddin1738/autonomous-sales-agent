import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from outreach.response_classifier import classify_keyword
from shared.schema import ResponseClassification


def test_meeting_requested():
    assert classify_keyword("Can we set up a call next week?") == ResponseClassification.MEETING_REQUESTED


def test_pricing_objection():
    assert classify_keyword("What's the pricing on this?") == ResponseClassification.PRICING_OBJECTION


def test_not_interested():
    assert classify_keyword("Please remove me from this list, not interested.") == ResponseClassification.NOT_INTERESTED


def test_technical_objection():
    assert classify_keyword("We have a security concern about integrating this.") == ResponseClassification.TECHNICAL_OBJECTION


def test_wrong_person():
    assert classify_keyword("I'm the wrong person for this, reach out to our IT lead.") == ResponseClassification.WRONG_PERSON


def test_fallback_other():
    assert classify_keyword("Out of office until Monday.") == ResponseClassification.OTHER
