"""Shared pytest fixtures for periodization unit tests."""
from __future__ import annotations

import pytest

from src.coach.periodization.types import Phase, PhaseIntent


@pytest.fixture
def phase_intent_fixture():
    """Default PhaseIntent (BUILD phase) for MicroCycle/Snapshot construction."""
    def _build(phase: Phase = Phase.BUILD) -> PhaseIntent:
        return PhaseIntent(
            phase=phase, primary_adaptation="threshold_capacity",
            weekly_tss_target=500,
            intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
            rest_days_per_week=1, rationale="test",
        )
    return _build
