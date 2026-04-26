"""Shared fixtures for adapter unit tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.coach.ledger.types import AthleteStateRef


@pytest.fixture
def fixed_utc_now() -> datetime:
    return datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)


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
