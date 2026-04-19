import pytest

from src.coach.session_designer.workout_library import (
    WORKOUT_TEMPLATES, get_template, list_templates_for_tier,
)
from src.coach.periodization.types import IntensityTier, SessionType


def test_required_templates_present():
    names = {t.name for t in WORKOUT_TEMPLATES}
    assert "vo2max_short_5x4" in names
    assert "threshold_2x20" in names
    assert "sweet_spot_3x15" in names
    assert "endurance_long_z2" in names
    assert "recovery_spin" in names
    assert "rest_day" in names


def test_every_template_has_session_type_and_tier():
    for t in WORKOUT_TEMPLATES:
        assert isinstance(t.session_type, SessionType)
        assert isinstance(t.tier, IntensityTier)
        assert t.total_duration_s_range[0] <= t.total_duration_s_range[1]


def test_get_template_lookup():
    t = get_template("threshold_2x20")
    assert t.name == "threshold_2x20"
    assert t.session_type is SessionType.THRESHOLD


def test_get_template_missing_raises():
    with pytest.raises(KeyError):
        get_template("does_not_exist")


def test_list_templates_for_tier_filters_correctly():
    hard = list_templates_for_tier(IntensityTier.HARD)
    assert all(t.tier is IntensityTier.HARD for t in hard)
    easy = list_templates_for_tier(IntensityTier.EASY)
    assert any(t.name == "recovery_spin" for t in easy)


def test_template_steps_use_symbolic_targets_not_absolute_watts():
    t = get_template("threshold_2x20")
    for step in t.steps:
        assert step.target_w_low is None
        assert step.target_w_high is None
    assert any(s.pct_of_cp_low is not None for s in t.steps)
