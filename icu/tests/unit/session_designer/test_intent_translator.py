from src.coach.session_designer.intent_translator import (
    translate_intent,
)
from src.coach.periodization.types import IntensityTier


def _intent(tier, hint):
    return {"tier": tier, "hint": hint}


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
