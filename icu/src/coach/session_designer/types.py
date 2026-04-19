"""Phase 2 session designer data models."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


class DayPlanV2(BaseModel):
    """A single day in a weekly plan."""
    date: str
    day_of_week: str
    training_type: Literal[
        "Rest", "Recovery", "Aerobic", "Tempo",
        "Threshold", "VO2max", "Neuromuscular", "Race"
    ]
    icu_type: Literal["Ride", "WeightTraining", "Walk", "Run", "Rest"]
    name: str
    description: str
    duration_min: int
    target_tss: int
    power_range_w: Optional[str] = None
    hr_range_bpm: Optional[str] = None


class WeeklyPlan(BaseModel):
    """A complete weekly training plan."""
    week_start: str
    week_end: str
    focus_theme: str
    weekly_tss_target: int
    coaching_summary: Optional[str] = None
    days: list[DayPlanV2]
