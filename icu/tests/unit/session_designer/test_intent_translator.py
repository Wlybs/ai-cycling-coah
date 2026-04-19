from src.coach.session_designer.intent_translator import (
    translate_intent,
)
from src.coach.periodization.types import IntensityTier


def test_rest_always_rest_day():
    name = translate_intent(
        tier=IntensityTier.REST, hint="rest",
        tolerance_classes={},
    )
    assert name == "rest_day"


def test_keyword_vo2_matches_vo2_template():
    name = translate_intent(
        tier=IntensityTier.HARD,
        hint="VO2max 5x4' @ 110-115% CP",
        tolerance_classes={"VO2max": "medium"},
    )
    assert name == "vo2max_short_5x4"


def test_keyword_threshold_matches_threshold_template():
    name = translate_intent(
        tier=IntensityTier.HARD, hint="threshold 2x20' @ 97-102% CP",
        tolerance_classes={},
    )
    assert name == "threshold_2x20"


def test_keyword_long_matches_endurance_long_z2():
    name = translate_intent(
        tier=IntensityTier.EASY, hint="long Z2 3h+",
        tolerance_classes={},
    )
    assert name == "endurance_long_z2"


def test_keyword_tempo_matches_tempo_or_ss_for_medium():
    name = translate_intent(
        tier=IntensityTier.MEDIUM, hint="tempo 60min continuous",
        tolerance_classes={},
    )
    assert name == "tempo_continuous_60"


def test_low_tolerance_downgrades_vo2_to_threshold():
    name = translate_intent(
        tier=IntensityTier.HARD, hint="VO2max 5x4'",
        tolerance_classes={"VO2max": "low"},
    )
    assert name == "threshold_2x20"


def test_default_falls_back_to_tier_default():
    name = translate_intent(
        tier=IntensityTier.MEDIUM, hint="something unclear",
        tolerance_classes={},
    )
    assert name == "sweet_spot_3x15"


def test_race_sim_for_race_tier():
    name = translate_intent(
        tier=IntensityTier.RACE_SIM, hint="RACE",
        tolerance_classes={},
    )
    assert name == "race_sim_course"


def test_openers_keyword_matches():
    name = translate_intent(
        tier=IntensityTier.EASY, hint="short openers 3x30''",
        tolerance_classes={},
    )
    assert name == "openers_short"


def test_recovery_rule_does_not_match_bare_spin():
    # Before hardening: "spindown calibration" matched "spin" → recovery_spin. No more.
    name = translate_intent(
        tier=IntensityTier.HARD, hint="spindown calibration",
        tolerance_classes={},
    )
    # Falls through to HARD tier default
    assert name == "threshold_2x20"


def test_high_tolerance_promotes_vo2_5x4_to_6x3():
    # Generic "vo2" hint, HARD tier, high tolerance → upgrade to 6x3
    name = translate_intent(
        tier=IntensityTier.HARD, hint="VO2max intervals",
        tolerance_classes={"VO2max": "high"},
    )
    assert name == "vo2max_short_6x3"


def test_tolerance_lookup_is_case_insensitive():
    # Upstream might emit different casing for the tolerance key
    name = translate_intent(
        tier=IntensityTier.HARD, hint="VO2max 5x4'",
        tolerance_classes={"VO2MAX": "low"},
    )
    assert name == "threshold_2x20"
