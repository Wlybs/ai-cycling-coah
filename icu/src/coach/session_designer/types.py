"""Phase 2 session designer data models.

STUB: created out-of-order by File 09 delivery (T43) to lock the interface
File 06 (session-designer-infra) must build toward. File 06 may extend this
module with new fields, new SessionType entries, or additional models — it
MUST NOT rename or re-type the fields used below, as prose_io and plan_writer
already depend on them.
"""
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
    # STUB Literal: File 06 (assembler) must extend when new icu_type values
    # are needed (e.g. VirtualRide, Swim). Adding a value without updating this
    # Literal produces a silent Pydantic validation error at runtime.
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
