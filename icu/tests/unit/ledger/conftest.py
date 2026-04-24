"""Shared fixtures for ledger unit tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.coach.ledger.types import AthleteStateRef


@pytest.fixture
def sample_state() -> AthleteStateRef:
    return AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


@pytest.fixture
def ledger_path(tmp_path):
    """Empty path; writer creates the file on first record."""
    return tmp_path / "decisions.jsonl"


@pytest.fixture
def fixed_utc_now():
    return datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)
