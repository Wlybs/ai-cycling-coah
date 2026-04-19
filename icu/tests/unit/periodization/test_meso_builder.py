from datetime import date
import pytest

from src.coach.periodization.meso_builder import (
    select_meso_pattern, MESO_PATTERNS, build_meso_block,
)
from src.coach.periodization.types import Phase


def test_base_phase_uses_polarized():
    p = select_meso_pattern(
        phase=Phase.BASE, knee_flag=None, recent_atl_delta=0.0)
    assert p == "polarized"


def test_build_default_three_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None, recent_atl_delta=2.0)
    assert p == "3:1"


def test_build_high_responder_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None,
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "2:1"


def test_knee_caution_forces_three_one_over_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag="caution",
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "3:1"


def test_taper_uses_linear():
    p = select_meso_pattern(
        phase=Phase.TAPER, knee_flag=None, recent_atl_delta=-3.0)
    assert p == "linear"


def test_all_patterns_defined():
    assert set(MESO_PATTERNS.keys()) == {"3:1", "2:1", "polarized", "linear"}
    for multipliers in MESO_PATTERNS.values():
        assert 3 <= len(multipliers) <= 6
        assert min(multipliers) < 1.0
        assert max(multipliers) >= 1.0
