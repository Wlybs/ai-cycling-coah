from typing import List, Literal, Optional, Tuple, Any
from pydantic import BaseModel


class Features(BaseModel):
    has_intervals: bool = False
    is_race: bool = False
    has_climbing: bool = False
    is_endurance_long: bool = False
    has_anomaly: bool = False
    target_type_claimed: Optional[str] = None
    w_prime_depleted: bool = False
    heat_stress: bool = False
    duration_seconds: int
    total_kj: int


class Findings(BaseModel):
    analyzer: str
    metrics: dict[str, Any]
    verdict: str
    evidence: List[Tuple[str, str]]
    error: Optional[str] = None


class SummaryLatest(BaseModel):
    activity_id: str
    analyzed_at: str
    sub_analyzers_run: List[str]
    headline_verdict: str
    stimulus_score: float
    progression_flag: Literal["progression", "flat", "regression_mild", "regression_severe"]
    next_plan_hints: List[str]
    knee_flag: Optional[Literal["watch", "caution"]] = None


class StateFile(BaseModel):
    last_analyzed_activity_id: Optional[str] = None
    last_analyzed_at: Optional[str] = None
    errors: List[dict] = []
