"""Adapter 类型定义：SignalSnapshot / AdaptationVerdict + 枚举常量。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- 锁定枚举 ----------

Verdict = Literal["green", "yellow", "red"]
VERDICT_VALUES: tuple[str, ...] = get_args(Verdict)

RecommendedAction = Literal[
    "none",                   # green: 无动作
    "nudge_only",             # yellow: 写 markdown nudge，不触 ICU
    "propose_replacement",    # red: 合成替代 session，等用户 --confirm
    "rest_48h",               # red + 连红护栏: 强制 48h 完全休息
]
RECOMMENDED_ACTIONS: tuple[str, ...] = get_args(RecommendedAction)

# 4 个被监控的信号 key —— 必须与 rules.py 内部一致。
SIGNAL_KEYS: tuple[str, ...] = ("hrv", "resting_hr", "sleep", "soreness")


# ---------- SignalSnapshot ----------

class SignalSnapshot(BaseModel):
    """单日 4 信号 + UTC 采集时间。字段语义对齐 wellness_history.json。"""

    model_config = {"frozen": True}

    captured_at: datetime = Field(..., description="UTC tz-aware timestamp")
    hrv_ms: float = Field(..., ge=0.0, description="今日 HRV (rMSSD ms)")
    resting_hr_bpm: int = Field(..., ge=0, description="今日 resting HR (bpm)")
    sleep_hours: float = Field(..., ge=0.0, description="昨夜睡眠时长 (hours)")
    soreness_score: int = Field(
        ..., ge=1, le=4,
        description="主观酸痛 1=worst..4=best (Intervals.icu 约定)",
    )

    @field_validator("captured_at")
    @classmethod
    def _require_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware (UTC)")
        return v


# ---------- AdaptationVerdict ----------

class AdaptationVerdict(BaseModel):
    """rules.evaluate_signals 的输出 —— 不含任何 IO 副作用。"""

    verdict: Verdict
    signal_summary: dict[str, Verdict] = Field(
        ...,
        description="逐信号红黄绿，key ∈ SIGNAL_KEYS（4 项必填）",
    )
    severity_score: float = Field(..., ge=0.0, le=1.0,
                                  description="0=全绿；1=全红+护栏触发")
    recommended_action: RecommendedAction
    triggered_rules: list[str] = Field(default_factory=list)
    guardrails_hit: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _check_signal_summary_keys(self) -> "AdaptationVerdict":
        missing = set(SIGNAL_KEYS) - set(self.signal_summary)
        if missing:
            raise ValueError(
                f"signal_summary missing required keys: {sorted(missing)}"
            )
        return self
