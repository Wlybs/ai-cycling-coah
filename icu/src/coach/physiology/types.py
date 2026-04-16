from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CPWModel(BaseModel):
    generated_at: str
    window_days: int
    cp_watts: int
    w_prime_joules: int
    t_k_seconds: float
    model: Literal["3-param-hyperbolic", "2-param-hyperbolic"]
    fit_r_squared: float
    data_points_used: List[List[float]]
    athlete_ftp_set: int
    cp_vs_ftp_delta_w: int
    stale: bool = False


class LapWBal(BaseModel):
    lap_index: int
    type: Literal["work", "recovery", "steady"]
    w_bal_start_j: int
    w_bal_end_j: int
    depletion_pct: float


class WBalanceSeries(BaseModel):
    activity_id: str
    cp_used_w: int
    w_prime_used_j: int
    tau_s: float
    min_w_bal_j: int
    min_w_bal_pct: float
    min_w_bal_timestamp_s: int
    seconds_below_15pct: int
    laps: List[LapWBal]
    w_bal_series_1hz: List[int]


class DurabilityCurve(BaseModel):
    generated_at: str
    sample_size_rides: int
    fresh_mmp_w: dict
    fatigued_mmp_w: dict
    decay_rate_pct_per_1000kj: dict
    percentile_vs_class_estimate: Optional[str] = None


class ResponseTypeStats(BaseModel):
    sessions_n: int
    avg_tss: int
    next_day_hrv_delta_pct: float
    next_day_rhr_delta_bpm: float
    avg_target_adherence: float
    tolerance_class: Literal["low", "moderate", "high"]
    recommended_min_interval_hours: int


class KneeLoading(BaseModel):
    standing_climb_minutes_90d: int
    avg_hr_drift_bpm_standing: float
    flag: Optional[Literal["watch", "caution"]] = None


class ResponseProfile(BaseModel):
    generated_at: str
    window_days: int
    types: dict[str, ResponseTypeStats]
    knee_loading: KneeLoading


class PhysiologyBundle(BaseModel):
    cp_w: Optional[CPWModel] = None
    durability: Optional[DurabilityCurve] = None
    response: Optional[ResponseProfile] = None
