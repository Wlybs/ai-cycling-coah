"""DayIntent → WorkoutTemplate name."""
from __future__ import annotations

from ..periodization.types import IntensityTier

_TIER_DEFAULTS = {
    IntensityTier.REST: "rest_day",
    IntensityTier.EASY: "recovery_spin",
    IntensityTier.MEDIUM: "sweet_spot_3x15",
    IntensityTier.HARD: "threshold_2x20",
    IntensityTier.RACE_SIM: "race_sim_course",
}

# 顺序重要：更具体的关键词先匹配
_KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    (("5x4", "5 x 4"), "vo2max_short_5x4"),
    (("6x3", "6 x 3"), "vo2max_short_6x3"),
    (("vo2",), "vo2max_short_5x4"),
    (("threshold",), "threshold_2x20"),
    (("sweet-spot", "sweet spot"), "sweet_spot_3x15"),
    (("tempo continuous", "continuous tempo"), "tempo_continuous_60"),
    (("long z2", "long endurance", "long ride"), "endurance_long_z2"),
    (("tempo inside", "with tempo", "long with"), "endurance_long_with_tempo"),
    (("opener",), "openers_short"),
    (("race",), "race_sim_course"),
    (("recovery spin", "recovery ride", "easy spin"), "recovery_spin"),
    (("tempo",), "tempo_continuous_60"),
    (("long",), "endurance_long_z2"),
]


def _match_keyword(hint: str) -> str | None:
    h = hint.lower()
    for keywords, template in _KEYWORD_RULES:
        if any(k in h for k in keywords):
            return template
    return None


def translate_intent(
    tier: IntensityTier,
    hint: str,
    tolerance_classes: dict[str, str],
) -> str:
    if tier is IntensityTier.REST:
        return "rest_day"

    name = _match_keyword(hint) or _TIER_DEFAULTS[tier]

    # tolerance downgrade: 低耐受 VO2 → threshold
    if name.startswith("vo2max"):
        tc = next(
            (v for k, v in tolerance_classes.items() if k.lower() == "vo2max"),
            None,
        )
        if tc == "low":
            return "threshold_2x20"
        if tc == "high" and name == "vo2max_short_5x4":
            # High-responder + generic VO2 intent → prefer higher-density 6x3 variant.
            return "vo2max_short_6x3"

    return name
