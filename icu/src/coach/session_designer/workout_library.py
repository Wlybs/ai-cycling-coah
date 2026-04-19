"""可复用训练模板。steps 只记录\"强度占比\"，composer 在 T39 把占比代入 CP 转成瓦特。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..periodization.types import IntensityTier, SessionType


class WorkoutTemplateStep(BaseModel):
    label: str
    duration_s: int = Field(..., ge=5)
    target_w_low: Optional[int] = None
    target_w_high: Optional[int] = None
    pct_of_cp_low: Optional[float] = None
    pct_of_cp_high: Optional[float] = None
    w_prime_deplete_pct_max: Optional[float] = None
    zone: str = Field(..., pattern=r"^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")
    rep_count: int = 1


class WorkoutTemplate(BaseModel):
    name: str
    session_type: SessionType
    tier: IntensityTier
    steps: list[WorkoutTemplateStep]
    total_duration_s_range: tuple[int, int]
    notes: str


def _step(label: str, duration_s: int, pct_low: Optional[float],
          pct_high: Optional[float], zone: str,
          w_prime_max: Optional[float] = None) -> WorkoutTemplateStep:
    return WorkoutTemplateStep(
        label=label, duration_s=duration_s,
        pct_of_cp_low=pct_low, pct_of_cp_high=pct_high,
        zone=zone, w_prime_deplete_pct_max=w_prime_max,
    )


def _wu(dur_s=900) -> WorkoutTemplateStep:
    return _step("WU", dur_s, 0.40, 0.70, "Z1")


def _cd(dur_s=600) -> WorkoutTemplateStep:
    return _step("CD", dur_s, 0.40, 0.60, "Z1")


def _rest_interval(dur_s=180) -> WorkoutTemplateStep:
    return _step("rest", dur_s, 0.40, 0.55, "Z1")


def _build_intervals(label_fmt: str, rep: int, work_s: int,
                     rest_s: int, pct_low: float, pct_high: float,
                     zone: str, w_prime_max: Optional[float]
                     ) -> list[WorkoutTemplateStep]:
    steps: list[WorkoutTemplateStep] = []
    for i in range(rep):
        steps.append(_step(label_fmt.format(i=i+1, total=rep),
                           work_s, pct_low, pct_high, zone, w_prime_max))
        if i < rep - 1:
            steps.append(_rest_interval(rest_s))
    return steps


WORKOUT_TEMPLATES: list[WorkoutTemplate] = [
    WorkoutTemplate(
        name="vo2max_short_5x4",
        session_type=SessionType.VO2MAX, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("VO2 {i}/{total} 4'", 5, 240, 180,
                                  1.10, 1.15, "Z5", 0.25)
               + [_cd()]),
        total_duration_s_range=(2700, 3300),
        notes="经典 5x4' VO2max @ 110-115% CP，r3' active rest。W' 单次消耗上限 25% 以留余量。",
    ),
    WorkoutTemplate(
        name="vo2max_short_6x3",
        session_type=SessionType.VO2MAX, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("VO2 {i}/{total} 3'", 6, 180, 180,
                                  1.15, 1.20, "Z5", 0.20)
               + [_cd()]),
        total_duration_s_range=(2700, 3300),
        notes="6x3' VO2max 高刺激密度，PEAK 阶段使用。",
    ),
    WorkoutTemplate(
        name="threshold_2x20",
        session_type=SessionType.THRESHOLD, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("TH {i}/{total} 20'", 2, 1200, 480,
                                  0.97, 1.02, "Z4", None)
               + [_cd()]),
        total_duration_s_range=(4500, 5400),
        notes="Threshold 2x20 @ 97-102% CP，提高乳酸清除。",
    ),
    WorkoutTemplate(
        name="sweet_spot_3x15",
        session_type=SessionType.TEMPO, tier=IntensityTier.MEDIUM,
        steps=([_wu()]
               + _build_intervals("SS {i}/{total} 15'", 3, 900, 300,
                                  0.88, 0.93, "Z3", None)
               + [_cd()]),
        total_duration_s_range=(4200, 5100),
        notes="Sweet-spot 3x15 @ 88-93% CP，高性价比的有氧+力量区刺激。",
    ),
    WorkoutTemplate(
        name="tempo_continuous_60",
        session_type=SessionType.TEMPO, tier=IntensityTier.MEDIUM,
        steps=[_wu(600), _step("tempo 60'", 3600, 0.80, 0.85, "Z3"),
               _cd(600)],
        total_duration_s_range=(4200, 4800),
        notes="稳态 tempo 60min @ 80-85% CP。",
    ),
    WorkoutTemplate(
        name="endurance_long_z2",
        session_type=SessionType.AEROBIC, tier=IntensityTier.EASY,
        steps=[_wu(600),
               _step("long Z2", 9000, 0.65, 0.75, "Z2"),
               _cd(600)],
        total_duration_s_range=(7200, 14400),
        notes="长距离 Z2。时长按当日 target_tss 动态调整。",
    ),
    WorkoutTemplate(
        name="endurance_long_with_tempo",
        session_type=SessionType.AEROBIC, tier=IntensityTier.MEDIUM,
        steps=[_wu(600),
               _step("Z2 leg1", 3600, 0.65, 0.75, "Z2"),
               _step("tempo 1/2 10'", 600, 0.82, 0.88, "Z3"),
               _rest_interval(600),
               _step("tempo 2/2 10'", 600, 0.82, 0.88, "Z3"),
               _step("Z2 leg2", 3600, 0.65, 0.75, "Z2"),
               _cd(600)],
        total_duration_s_range=(8400, 12600),
        notes="长骑中段插 2x10' tempo。",
    ),
    WorkoutTemplate(
        name="recovery_spin",
        session_type=SessionType.RECOVERY, tier=IntensityTier.EASY,
        steps=[_step("recovery", 2400, 0.45, 0.55, "Z1")],
        total_duration_s_range=(1800, 3600),
        notes="主动恢复，心率不超过 65% HRmax。",
    ),
    WorkoutTemplate(
        name="openers_short",
        session_type=SessionType.NEUROMUSCULAR, tier=IntensityTier.EASY,
        steps=([_wu()]
               + _build_intervals("opener {i}/{total} 30\"", 4, 30, 180,
                                  1.05, 1.15, "Z5", 0.05)
               + [_cd(600)]),
        total_duration_s_range=(1800, 2700),
        notes="神经肌肉唤醒：短冲 + 长 rest，不产生疲劳。",
    ),
    WorkoutTemplate(
        name="race_sim_course",
        session_type=SessionType.RACE, tier=IntensityTier.RACE_SIM,
        steps=([_wu()]
               + _build_intervals("race-sim 15'", 3, 900, 360,
                                  0.95, 1.05, "Z4", None)
               + [_cd()]),
        total_duration_s_range=(3600, 5400),
        notes="Race-sim 模板骨架；composer 根据 course_hint 替换强度段时长/RPM。",
    ),
    WorkoutTemplate(
        name="rest_day",
        session_type=SessionType.REST, tier=IntensityTier.REST,
        steps=[],
        total_duration_s_range=(0, 0),
        notes="完全休息日。",
    ),
]


def get_template(name: str) -> WorkoutTemplate:
    for t in WORKOUT_TEMPLATES:
        if t.name == name:
            return t
    raise KeyError(f"unknown workout template: {name}")


def list_templates_for_tier(tier: IntensityTier) -> list[WorkoutTemplate]:
    return [t for t in WORKOUT_TEMPLATES if t.tier is tier]
