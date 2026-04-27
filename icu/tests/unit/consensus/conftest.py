"""Shared fixtures for consensus unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "phase3" / "consensus"


@pytest.fixture
def fixture_dir() -> Path:
    assert FIXTURES.is_dir(), f"missing fixture dir: {FIXTURES}"
    return FIXTURES


def _read(fixture_dir: Path, name: str) -> str:
    return (fixture_dir / name).read_text(encoding="utf-8")


@pytest.fixture
def happy_response(fixture_dir):
    return _read(fixture_dir, "happy.md")


@pytest.fixture
def reject_responses(fixture_dir):
    """Map fixture-name → file content for the 6 rejection fixtures."""
    names = [
        "reject_no_critic.md",
        "reject_critic_2_points.md",
        "reject_critic_no_data.md",
        "reject_phys_2_keywords.md",
        "reject_bad_verdict.md",
        "reject_no_summary_json.md",
    ]
    return {n: _read(fixture_dir, n) for n in names}
