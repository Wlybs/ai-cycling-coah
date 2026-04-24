"""Periodization 层的类型定义。所有对外暴露的数据结构都是 Pydantic 模型。"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Phase(str, Enum):
    """周期化阶段。取值与 Scheme 4 蓝图一致。"""
    BASE = "BASE"
    BUILD = "BUILD"
    PEAK = "PEAK"
    TAPER = "TAPER"
    RACE = "RACE"
    TRANSITION = "TRANSITION"


class IntensityTier(str, Enum):
    """当日强度等级。用于 MicroCycle 的 7 日序列。"""
    REST = "REST"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    RACE_SIM = "RACE_SIM"

    @property
    def ordinal(self) -> int:
        """相对顺序值，仅用于排序比较，不代表训练负荷（TSS/W 等）。"""
        return {
            "REST": 0,
            "EASY": 1,
            "MEDIUM": 2,
            "HARD": 3,
            "RACE_SIM": 4,
        }[self.value]


class SessionType(str, Enum):
    """与旧 plan_generator.DayPlan.training_type Literal 严格一致。

    任何值改动都会破坏 ICU 日历同步兼容性 — 务必保持。"""
    REST = "Rest"
    RECOVERY = "Recovery"
    AEROBIC = "Aerobic"
    TEMPO = "Tempo"
    THRESHOLD = "Threshold"
    VO2MAX = "VO2max"
    NEUROMUSCULAR = "Neuromuscular"
    RACE = "Race"


class PhaseIntent(BaseModel):
    """单个阶段的生理学意图。周期化引擎的对外主数据结构。"""
    phase: Phase
    primary_adaptation: str = Field(
        ...,
        description="本阶段主要想追的适应，如 'aerobic_base' / 'threshold_capacity' "
                    "/ 'vo2_power' / 'freshness_preservation'。",
    )
    weekly_tss_target: int = Field(..., ge=0, le=1200)
    intensity_distribution_pct: dict[str, int] = Field(
        ...,
        description="低/中/高强度占比，必须 sum=100。key 固定为 'low' | 'mid' | 'high'。",
    )
    rest_days_per_week: int = Field(..., ge=0, le=7)
    rationale: str = Field(..., description="给 LLM 看的决策理由，可含文献引用。")

    @model_validator(mode="after")
    def _check_distribution_sum(self):
        if set(self.intensity_distribution_pct.keys()) != {"low", "mid", "high"}:
            raise ValueError("intensity_distribution_pct keys must be {'low','mid','high'}")
        if sum(self.intensity_distribution_pct.values()) != 100:
            raise ValueError("intensity_distribution_pct must sum to 100")
        if any(v < 0 or v > 100 for v in self.intensity_distribution_pct.values()):
            raise ValueError("intensity_distribution_pct values must each be in [0, 100]")
        return self


class MacroWindow(BaseModel):
    """宏观阶段窗口（一段 Base / Build / Peak / Taper / Race / Transition 连续区间）。"""
    phase: Phase
    start_date: date
    end_date: date
    intent: PhaseIntent

    @model_validator(mode="after")
    def _check_order(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class MacroPlan(BaseModel):
    """整个赛季的阶段布局。"""
    generated_at: str
    season_end_date: date
    windows: list[MacroWindow] = Field(..., min_length=1)


class MesoBlock(BaseModel):
    """中观训练块 (通常 3–6 周)。"""
    pattern: Literal["3:1", "2:1", "polarized", "linear"] = Field(
        ..., description="'3:1' | '2:1' | 'polarized' | 'linear'"
    )
    block_start: date
    block_end: date
    weekly_load_multipliers: list[float] = Field(..., min_length=3, max_length=6)
    phase: Phase


class DayIntent(BaseModel):
    """当周单日意图。"""
    day_of_week: str = Field(..., pattern="^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    tier: IntensityTier
    target_tss: int = Field(..., ge=0, le=400)
    session_hint: str = Field(
        ..., description="给 Session Designer 的提示：期望哪种 session_type 或结构。"
    )


class MicroCycle(BaseModel):
    """当前一周的 7 日意图序列。"""
    week_start: date
    week_end: date
    phase: Phase
    intent: PhaseIntent
    days: list[DayIntent] = Field(..., min_length=7, max_length=7)
    weekly_tss_target: int = Field(..., ge=0, le=1200)


class NextRace(BaseModel):
    name: str
    race_date: date
    priority: str = Field(..., pattern="^(A|B|C)$")
    course_hint: Optional[str] = None


class PeriodizationSnapshot(BaseModel):
    """汇总快照。写入 coach_memory/periodization/periodization_current.json。"""
    generated_at: str
    current_phase: Phase
    macro: MacroPlan
    meso: MesoBlock
    micro: MicroCycle
    next_race: Optional[NextRace] = None
