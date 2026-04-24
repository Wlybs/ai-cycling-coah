"""Ledger 类型定义：AthleteStateRef / DecisionEntry + ULID helper。"""
from __future__ import annotations

import secrets
import time
from datetime import datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator


# ---------- decision_type 白名单 ----------

DecisionType = Literal[
    "phase_transition",
    "macro_plan_generated",
    "meso_block_created",
    "micro_cycle_generated",
    "weekly_plan_assembled",
    "consensus_verdict",
    "adaptation_verdict",
    "adaptation_applied",
]

DECISION_TYPES: tuple[str, ...] = get_args(DecisionType)


# ---------- ULID helper (stdlib-only, Crockford base32) ----------

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ALPHABET_SET = frozenset(_CROCKFORD)


def _encode_crockford(value: int, length: int) -> str:
    """Encode non-negative integer to Crockford base32, left-padded to `length`."""
    if value < 0:
        raise ValueError("value must be non-negative")
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def generate_ulid() -> str:
    """Return a 26-char ULID (48-bit ms timestamp + 80-bit randomness).

    Time encoded in first 10 chars (lexicographically sortable by ms).
    Random encoded in last 16 chars (80 bits from secrets.randbits).
    """
    ms = time.time_ns() // 1_000_000
    rand = secrets.randbits(80)
    return _encode_crockford(ms, 10) + _encode_crockford(rand, 16)


def is_valid_ulid(candidate: str) -> bool:
    """True iff `candidate` is a 26-char Crockford-base32 string."""
    if not isinstance(candidate, str) or len(candidate) != 26:
        return False
    return set(candidate) <= _ALPHABET_SET


# ---------- AthleteStateRef ----------

class AthleteStateRef(BaseModel):
    """每条 ledger entry 附带的运动员状态快照。

    Phase/week_of_year 必填 → `query_similar` 按此索引。
    字段冻结；新增字段前请评估向后兼容（旧 entry 没有新字段时读取必须不崩）。
    """

    model_config = {"frozen": True}

    ctl: float = Field(..., description="Chronic Training Load (当天值)")
    atl: float = Field(..., description="Acute Training Load")
    tsb: float = Field(..., description="Training Stress Balance = CTL − ATL")
    w_prime: int = Field(..., ge=0, description="当前 W' 焦耳值（来自 CPWModel）")
    phase: str = Field(..., description="Periodization Phase enum value, e.g. 'BUILD'")
    week_of_year: int = Field(..., ge=1, le=53, description="ISO week number")


# ---------- DecisionEntry ----------

class DecisionEntry(BaseModel):
    """Ledger 的一条决策记录。append-only；纠错通过 superseded_by 指针。"""

    schema_version: int = 1
    entry_id: str = Field(..., description="26-char ULID, time-sortable")
    timestamp: datetime = Field(..., description="UTC timestamp (tzinfo required)")
    decision_type: DecisionType
    source: str = Field(..., description="模块标识，如 'adapter.daily' / 'consensus.council'")
    athlete_state_ref: AthleteStateRef
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    superseded_by: str | None = Field(
        default=None,
        description=(
            "ULID of an EARLIER entry that THIS entry supersedes/corrects. "
            "Set at write time of the newer correction entry. "
            "Append-only-safe: never mutates the older entry."
        ),
    )

    @field_validator("entry_id")
    @classmethod
    def _check_entry_id(cls, v: str) -> str:
        if not is_valid_ulid(v):
            raise ValueError(f"entry_id must be a valid ULID, got {v!r}")
        return v

    @field_validator("superseded_by")
    @classmethod
    def _check_superseded_by(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_ulid(v):
            raise ValueError(f"superseded_by must be a valid ULID, got {v!r}")
        return v

    @field_validator("timestamp")
    @classmethod
    def _require_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        return v
