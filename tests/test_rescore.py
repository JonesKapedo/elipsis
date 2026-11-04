"""Re-score reminder scheduling rules."""

from datetime import UTC, datetime, timedelta

from elipsis_api.services_reengage import FIRST_DUE_DAY, _due_cycle, _parse


def test_nothing_due_before_day_75():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    assert _due_cycle(created, created + timedelta(days=FIRST_DUE_DAY - 1)) is None


def test_first_cycle_on_day_75():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    assert _due_cycle(created, created + timedelta(days=75)) == 1


def test_second_cycle_after_ninety_days():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    assert _due_cycle(created, created + timedelta(days=75)) == 1
    assert _due_cycle(created, created + timedelta(days=164)) == 1
    assert _due_cycle(created, created + timedelta(days=165)) == 2


def test_stored_timestamps_are_treated_as_utc():
    parsed = _parse("2026-10-31 12:00:00")
    assert parsed is not None and parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    assert _parse("not-a-date") is None
    assert _parse(None) is None
