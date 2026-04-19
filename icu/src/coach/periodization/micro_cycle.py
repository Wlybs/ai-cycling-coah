"""Micro cycle builder: 把 PhaseIntent × MesoBlock × week_idx 落地成 7 日 DayIntent 序列。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Final

from .types import (
    DayIntent, IntensityTier, MesoBlock, MicroCycle, Phase, PhaseIntent,
)

DOW: Final = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 每 Phase 的 7 日 tier+hint 模板
_TEMPLATES: Final = {
    Phase.BASE: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.MEDIUM, "tempo endurance 60-75min"),
        (IntensityTier.EASY,   "Z2 recovery spin"),
        (IntensityTier.EASY,   "Z2 endurance 75-90min"),
        (IntensityTier.REST,   "rest or short Z1"),
        (IntensityTier.MEDIUM, "endurance 90min with short sweet-spot burst"),
        (IntensityTier.EASY,   "long Z2 3h+"),
    ],
    Phase.BUILD: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "VO2max 5x4' @ 110-115% CP"),
        (IntensityTier.EASY,   "Z2 recovery 45min"),
        (IntensityTier.MEDIUM, "sweet-spot 3x12' @ 88-93% CP"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "threshold 2x20' @ 97-102% CP"),
        (IntensityTier.MEDIUM, "endurance 2.5-3h with 2x10' tempo"),
    ],
    Phase.PEAK: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "VO2max short 6x3' @ 115-120% CP"),
        (IntensityTier.EASY,   "Z2 recovery 45min"),
        (IntensityTier.MEDIUM, "tempo 60-75min"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "race-sim intervals (course-specific)"),
        (IntensityTier.EASY,   "endurance 90-120min"),
    ],
    Phase.TAPER: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "short openers 3x3' @ 110% CP"),
        (IntensityTier.EASY,   "Z2 30-45min"),
        (IntensityTier.MEDIUM, "short tempo 30min"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "short Z2 45min + 3x30'' openers"),
        (IntensityTier.REST,   "rest (day before race area)"),
    ],
    Phase.RACE: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "30min Z2 + 4x30'' openers"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "20min activation + 3x30'' openers"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.RACE_SIM,"RACE"),
        (IntensityTier.REST,   "rest + recovery"),
    ],
    Phase.TRANSITION: [
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z1/Z2 outdoor unstructured"),
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z2 easy 60min"),
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z2 outdoor 90min"),
        (IntensityTier.EASY,  "Z2 easy 60min"),
    ],
}

# 每 tier 的相对 TSS 权重（按 1 周 7 日汇总归一到 weekly_tss_target）
_TIER_TSS_WEIGHT: Final = {
    IntensityTier.REST: 0.0,
    IntensityTier.EASY: 0.5,
    IntensityTier.MEDIUM: 1.0,
    IntensityTier.HARD: 1.4,
    IntensityTier.RACE_SIM: 2.0,
}


def _apply_extra_rest(
    days: list[tuple[IntensityTier, str]],
    rest_days_required: int,
) -> list[tuple[IntensityTier, str]]:
    """如果 intent 要 ≥2 rest 但模板只有 1 个，把 Fri 改成 REST。"""
    current_rests = sum(1 for t, _ in days if t is IntensityTier.REST)
    if current_rests >= rest_days_required:
        return days
    out = list(days)
    # 4 号位（周五）若非 REST，改成 REST
    if out[4][0] is not IntensityTier.REST:
        out[4] = (IntensityTier.REST, "rest (additional per intent)")
    return out


def _distribute_tss(
    week_tss: int,
    tiers: list[IntensityTier],
) -> list[int]:
    """按 tier 权重分配周 TSS 到每日，并校正四舍五入误差。"""
    weights = [_TIER_TSS_WEIGHT[t] for t in tiers]
    total_w = sum(weights) or 1.0
    raw = [week_tss * w / total_w for w in weights]
    ints = [int(round(v)) for v in raw]
    # 校正四舍五入误差，让总和等于 week_tss
    delta = week_tss - sum(ints)
    if ints:
        # 把 delta 加在第一个非零项上
        for i in range(len(ints)):
            if weights[i] > 0:
                ints[i] += delta
                break
    return ints


def build_micro_cycle(
    week_start: date,
    meso: MesoBlock,
    intent: PhaseIntent,
    week_idx: int,
) -> MicroCycle:
    """构造一周微循环。

    Args:
        week_start: Monday of the week.
        meso: MesoBlock containing the weekly load multipliers and phase.
        intent: PhaseIntent with weekly TSS target and rest days requirement.
        week_idx: 0-indexed week within the meso block (0, 1, 2, ...).
                 Clamped to the range [0, len(weekly_load_multipliers)-1].

    Returns:
        MicroCycle: A 7-day workout sequence with computed TSS per day.

    Notes:
        - weekly_tss_target = round(intent.weekly_tss_target * multiplier)
        - Extra-rest rule: if intent.rest_days_per_week >= 2 and template has
          only 1 REST, Friday (index 4) is replaced with REST.
        - Per-day TSS is distributed by tier weights and rounded to int.
          Rounding errors are corrected by adjusting the first non-zero day.
    """
    template = _TEMPLATES[meso.phase]
    template = _apply_extra_rest(template, intent.rest_days_per_week)

    # Clamp week_idx to valid range
    clamped_idx = min(max(0, week_idx), len(meso.weekly_load_multipliers) - 1)
    multiplier = meso.weekly_load_multipliers[clamped_idx]
    week_tss = int(round(intent.weekly_tss_target * multiplier))

    tiers = [t for t, _ in template]
    tss_per_day = _distribute_tss(week_tss, tiers)

    days: list[DayIntent] = []
    for i, (tier, hint) in enumerate(template):
        days.append(DayIntent(
            day_of_week=DOW[i], tier=tier,
            target_tss=max(0, tss_per_day[i]),
            session_hint=hint,
        ))

    return MicroCycle(
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        phase=meso.phase,
        intent=intent,
        days=days,
        weekly_tss_target=week_tss,
    )
