"""Phase 2 session designer data models.

STUB created by File 09 delivery (T43): DayPlanV2, WeeklyPlan.
Extended by File 06 delivery (T36): WorkoutStep, SessionStructure, SessionIntent, DesignedSession.

File 09's prose_io and plan_writer depend on DayPlanV2 and WeeklyPlan's exact structure.
File 06 adds workout-design models without modifying the File 09 stubs.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from src.coach.periodization.types import IntensityTier, SessionType


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
    # NOTE: spec said `str` (required) but File 09 stub locked this as Optional.
    # Keeping Optional to preserve File 09's save_weekly_plan(coaching_summary=None) default.
    coaching_summary: Optional[str] = None
    days: list[DayPlanV2]


class WorkoutStep(BaseModel):
    """A single step within a structured workout."""
    label: str
    duration_s: int = Field(..., ge=5)
    target_w_low: Optional[int] = None
    target_w_high: Optional[int] = None
    target_hr_low: Optional[int] = None
    target_hr_high: Optional[int] = None
    target_rpm_low: Optional[int] = None
    target_rpm_high: Optional[int] = None
    zone: str = Field(..., pattern=r"^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")

    @model_validator(mode="after")
    def _check_ranges(self):
        if (self.target_w_low is not None and self.target_w_high is not None
                and self.target_w_low > self.target_w_high):
            raise ValueError("target_w_low must be <= target_w_high")
        if (self.target_hr_low is not None and self.target_hr_high is not None
                and self.target_hr_low > self.target_hr_high):
            raise ValueError("target_hr_low must be <= target_hr_high")
        if (self.target_rpm_low is not None and self.target_rpm_high is not None
                and self.target_rpm_low > self.target_rpm_high):
            raise ValueError("target_rpm_low must be <= target_rpm_high")
        return self


class SessionStructure(BaseModel):
    """Structured breakdown of a training session into phases."""
    steps: list[WorkoutStep]

    @property
    def total_duration_s(self) -> int:
        """Total duration across all steps, in seconds."""
        return sum(s.duration_s for s in self.steps)

    @property
    def main_duration_s(self) -> int:
        """Duration of main (non-warmup, non-cooldown) steps, in seconds."""
        inside = [s for s in self.steps if s.label.lower() not in ("wu", "cd")]
        if not inside:
            return 0
        return sum(s.duration_s for s in inside)


class SessionIntent(BaseModel):
    """High-level training intent for a single day.

    Derived from MicroCycle.DayIntent, consumed by workout composer.
    """
    day_of_week: str = Field(..., pattern=r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    tier: IntensityTier
    target_tss: int = Field(..., ge=0, le=400)
    session_hint: str


class DesignedSession(BaseModel):
    """Complete designed workout ready for athlete delivery."""
    day_of_week: str
    date: str
    session_type: SessionType
    name: str
    description: str
    duration_min: int = Field(..., ge=0, le=600)
    target_tss: int = Field(..., ge=0, le=400)
    structure: SessionStructure
    power_range_w: Optional[str] = None
    hr_range_bpm: Optional[str] = None
    trace: Optional[dict[str, Any]] = None
