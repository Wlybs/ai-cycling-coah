from typing import Any, Literal

from pydantic import BaseModel


class Features(BaseModel):
    has_intervals: bool = False
    is_race: bool = False
    has_climbing: bool = False
    is_endurance_long: bool = False
    has_anomaly: bool = False
    target_type_claimed: str | None = None
    w_prime_depleted: bool = False
    heat_stress: bool = False
    duration_seconds: int
    total_kj: int


class Findings(BaseModel):
    analyzer: str
    metrics: dict[str, Any]
    verdict: str
    evidence: list[tuple[str, str]]
    error: str | None = None


class SummaryLatest(BaseModel):
    activity_id: str
    analyzed_at: str
    sub_analyzers_run: list[str]
    headline_verdict: str
    stimulus_score: float
    progression_flag: Literal["progression", "flat", "regression_mild", "regression_severe"]
    next_plan_hints: list[str]
    knee_flag: Literal["watch", "caution"] | None = None


class StateFile(BaseModel):
    last_analyzed_activity_id: str | None = None
    last_analyzed_at: str | None = None
    errors: list[dict] = []
