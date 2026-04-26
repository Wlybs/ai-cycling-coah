"""Shared fixtures for adapter unit tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.coach.ledger.types import AthleteStateRef


@pytest.fixture
def fixed_utc_now() -> datetime:
    return datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def freeze_now(monkeypatch, fixed_utc_now):
    """Freeze datetime.now() inside src.coach.adapter.rules to fixed_utc_now."""
    import src.coach.adapter.rules as rules_mod

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is None:
                return fixed_utc_now.replace(tzinfo=None)
            return fixed_utc_now.astimezone(tz)

    monkeypatch.setattr(rules_mod, "datetime", _Frozen)
    return fixed_utc_now


@pytest.fixture
def baseline_state() -> AthleteStateRef:
    """Healthy mid-BUILD state — TSB only mildly negative."""
    return AthleteStateRef(
        ctl=72.3, atl=78.0, tsb=-5.7,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


@pytest.fixture
def stressed_state() -> AthleteStateRef:
    """TSB anomaly: deeply negative — should trigger guardrail."""
    return AthleteStateRef(
        ctl=72.3, atl=110.0, tsb=-37.7,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )
