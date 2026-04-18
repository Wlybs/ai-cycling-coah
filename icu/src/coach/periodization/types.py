"""Periodization 层的类型定义。所有对外暴露的数据结构都是 Pydantic 模型。"""
from __future__ import annotations

from enum import Enum


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
