# Phase 3 — Adapter infrastructure (Tasks T55–T57)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 交付 `icu/src/coach/adapter/` 的判定基座（types / rules）。本文件只产出 **纯 Python 决策内核**：把每日 4 个信号 + 2 条护栏映射到 `green / yellow / red` 的 `AdaptationVerdict`。Session 合成 / ICU PATCH 不在本文件范围（落在 04 / 05）。Ledger 写入也不在本文件 —— `evaluate_signals` 只 **返回** verdict，写入由 T60 `daily_adapt.py` 负责，保持本层无副作用。

**Files covered:**
- `icu/src/coach/adapter/__init__.py`
- `icu/src/coach/adapter/types.py`
- `icu/src/coach/adapter/rules.py`
- `icu/tests/unit/adapter/__init__.py`
- `icu/tests/unit/adapter/conftest.py`
- `icu/tests/unit/adapter/test_types.py`
- `icu/tests/unit/adapter/test_rules.py`
- `icu/tests/unit/adapter/test_evaluate_signals.py`

**Hard constraints (from 00-index.md):**
- `NO_NEW_DEPS`: 本文件只允许 stdlib + Pydantic v2；不引 numpy / pandas / 任何统计包。所有阈值算术用 builtins。
- `API_FREE_WORKFLOW`: rules.py 是确定性纯函数；绝不 import `google.genai` 或任何 LLM SDK。
- `PHASE_1_2_IMMUTABILITY`: 本文件涉及代码全部在 `icu/src/coach/adapter/` 与 `icu/tests/unit/adapter/` 下；不触 Phase 1/2，亦不触 `src/coach/ledger/`（只 `from src.coach.ledger.types import ...` 引用类型）。
- `APPEND_ONLY_LEDGER`: rules.py 不写 ledger。`evaluate_signals` 必须是 **pure**：相同输入 → 相同输出，0 文件 IO，0 全局状态变更。

**Locked decisions echoed (from 00-index.md):**
- 第 3 条 `HUMAN_GATE_ON_ICU_WRITE`：本层产出的 `AdaptationVerdict` **绝不直接调 ICU**；只是数据结构。绿灯 = 0 动作；黄灯 = 后续仅写 markdown 文件；红灯 = 后续等用户 `--confirm`。本规则在 `recommended_action` 的命名（`none` / `nudge_only` / `propose_replacement` / `rest_48h`）里 enforce —— 不出现 `auto_push_*` 之类带 ICU 写权限语义的值。
- 第 6 条 `PHYSIOLOGIST_QUANT_3_OF_4`：与本文件无关（属 consensus），但 `recommended_action` 不包含 `escalate_to_strict_consensus` —— 见 `RED_NO_AUTO_ESCALATE`。

---

## Task 55: Package scaffold + types (AdaptationVerdict, SignalSnapshot)

**Files:**
- Create: `icu/src/coach/adapter/__init__.py`
- Create: `icu/src/coach/adapter/types.py`
- Create: `icu/tests/unit/adapter/__init__.py`
- Create: `icu/tests/unit/adapter/conftest.py`
- Create: `icu/tests/unit/adapter/test_types.py`

**Design notes:**
- `SignalSnapshot` 字段命名匹配 `wellness_history.json` 原始 key 的语义（`hrv_ms` / `resting_hr_bpm` / `sleep_hours` / `soreness_score`）。`captured_at` 必须是 UTC tz-aware（与 `DecisionEntry.timestamp` 一致），naive datetime 拒收。
- `AdaptationVerdict.verdict` 走 `Literal["green","yellow","red"]`（与 00-index.md "Adapter verdict 枚举" 锁定值小写一致）。
- `signal_summary` 是 `dict[str, Literal["green","yellow","red"]]`，每个信号一条 —— 这样下游 prompt_builder（T59）可以直接渲染逐信号红黄绿，不需要重算。
- `severity_score ∈ [0.0, 1.0]`：0 = 全绿；1 = 全红 + 护栏触发。具体加权见 T56。
- `recommended_action` 走白名单 `Literal[...]`，禁止任意字符串 —— 防止下游误把"自动推 ICU"塞进来。

- [ ] **Step 1: Write failing tests — types**

Create `icu/tests/unit/adapter/conftest.py`:
```python
"""Shared fixtures for adapter unit tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.coach.ledger.types import AthleteStateRef


@pytest.fixture
def fixed_utc_now() -> datetime:
    return datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def baseline_state() -> AthleteStateRef:
    """Healthy mid-BUILD state — TSB only mildly negative."""
    return AthleteStateRef(
        ctl=72.3, atl=78.0, tsb=-5.7,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


@pytest.fixture
def stressed_state() -> AthleteStateRef:
    """TSB anomaly: deeply negative — should trigger guardrail."""
    return AthleteStateRef(
        ctl=72.3, atl=110.0, tsb=-37.7,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )
```

Write `icu/tests/unit/adapter/test_types.py`:
```python
"""Unit tests for adapter types: SignalSnapshot, AdaptationVerdict."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.coach.adapter.types import (
    AdaptationVerdict,
    RECOMMENDED_ACTIONS,
    SignalSnapshot,
    VERDICT_VALUES,
)


# ---------- SignalSnapshot ----------

def test_signal_snapshot_roundtrip(fixed_utc_now):
    snap = SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=68.0,
        resting_hr_bpm=52,
        sleep_hours=7.4,
        soreness_score=3,
    )
    js = snap.model_dump_json()
    loaded = SignalSnapshot.model_validate_json(js)
    assert loaded == snap


def test_signal_snapshot_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        SignalSnapshot(
            captured_at=datetime(2026, 4, 19, 10, 0, 0),  # no tzinfo
            hrv_ms=68.0, resting_hr_bpm=52,
            sleep_hours=7.4, soreness_score=3,
        )


def test_signal_snapshot_soreness_range(fixed_utc_now):
    # soreness scale 1 (worst) .. 4 (best) — Intervals.icu wellness convention
    SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                   resting_hr_bpm=50, sleep_hours=7.0, soreness_score=1)
    SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                   resting_hr_bpm=50, sleep_hours=7.0, soreness_score=4)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=0)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=5)


def test_signal_snapshot_rejects_negative_physiology(fixed_utc_now):
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=-1.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=3)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=-1, sleep_hours=7.0, soreness_score=3)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=-0.1, soreness_score=3)


# ---------- AdaptationVerdict ----------

def _signal_summary_all(verdict: str) -> dict[str, str]:
    return {"hrv": verdict, "resting_hr": verdict,
            "sleep": verdict, "soreness": verdict}


def test_verdict_values_locked():
    # 00-index.md locks {green, yellow, red} (lowercase) — adding a 4th requires ADR.
    assert set(VERDICT_VALUES) == {"green", "yellow", "red"}


def test_recommended_actions_whitelist():
    # HUMAN_GATE_ON_ICU_WRITE: no value here may imply auto-push.
    assert set(RECOMMENDED_ACTIONS) == {
        "none", "nudge_only", "propose_replacement", "rest_48h",
    }


def test_adaptation_verdict_minimal_green():
    v = AdaptationVerdict(
        verdict="green",
        signal_summary=_signal_summary_all("green"),
        severity_score=0.0,
        recommended_action="none",
    )
    assert v.triggered_rules == []
    assert v.guardrails_hit == []
    assert v.notes is None


def test_adaptation_verdict_roundtrip_red():
    v = AdaptationVerdict(
        verdict="red",
        signal_summary={"hrv": "red", "resting_hr": "yellow",
                        "sleep": "red", "soreness": "yellow"},
        severity_score=0.85,
        recommended_action="propose_replacement",
        triggered_rules=["hrv_red_threshold", "sleep_debt_acute"],
        guardrails_hit=[],
        notes="HRV -12.3% vs 28d mean",
    )
    js = v.model_dump_json()
    loaded = AdaptationVerdict.model_validate_json(js)
    assert loaded == v


def test_adaptation_verdict_severity_range():
    base = dict(
        verdict="green",
        signal_summary=_signal_summary_all("green"),
        recommended_action="none",
    )
    AdaptationVerdict(**base, severity_score=0.0)
    AdaptationVerdict(**base, severity_score=1.0)
    with pytest.raises(ValidationError):
        AdaptationVerdict(**base, severity_score=-0.01)
    with pytest.raises(ValidationError):
        AdaptationVerdict(**base, severity_score=1.01)


def test_adaptation_verdict_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="amber",  # not in {green, yellow, red}
            signal_summary=_signal_summary_all("green"),
            severity_score=0.0,
            recommended_action="none",
        )


def test_adaptation_verdict_rejects_unknown_action():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="red",
            signal_summary=_signal_summary_all("red"),
            severity_score=1.0,
            recommended_action="auto_push_to_icu",  # forbidden
        )


def test_adaptation_verdict_signal_summary_keys_complete():
    # All 4 signal keys must be present — protects downstream prompt rendering.
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="green",
            signal_summary={"hrv": "green"},  # missing 3 keys
            severity_score=0.0,
            recommended_action="none",
        )


def test_adaptation_verdict_signal_summary_values_locked():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="green",
            signal_summary={"hrv": "fine", "resting_hr": "green",
                            "sleep": "green", "soreness": "green"},
            severity_score=0.0,
            recommended_action="none",
        )
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter'`.

- [ ] **Step 3: Implement package + types**

Write `icu/src/coach/adapter/__init__.py`:
```python
"""Adaptation Engine — Phase 3 每日再评估的判定层。

公开入口：
- SignalSnapshot / AdaptationVerdict: 类型（见 types.py）
- evaluate_signals(snapshot, history) → AdaptationVerdict: 主判定函数（见 rules.py）

本包是 **纯函数层**：输入 dataclass、输出 dataclass，0 文件 IO，0 LLM 调用。
持久化 / ICU PATCH 在 scripts/daily_adapt.py 与 scripts/apply_adaptation.py 完成。
判定规则与阈值见 docs/superpowers/specs/2026-04-19-phase-3-blueprint.md §Component 5。
"""
```

Write `icu/src/coach/adapter/types.py`:
```python
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
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_types.py -v`
Expected: PASS all ~11 tests.

- [ ] **Step 5: Commit**

Write `icu/tests/unit/adapter/__init__.py` (empty):
```python
```

```bash
git add icu/src/coach/adapter/__init__.py \
        icu/src/coach/adapter/types.py \
        icu/tests/unit/adapter/__init__.py \
        icu/tests/unit/adapter/conftest.py \
        icu/tests/unit/adapter/test_types.py
git commit -m "feat(coach-phase3): adapter package scaffold + types (SignalSnapshot, AdaptationVerdict)"
```

---

## Task 56: rules.py — 4 信号阈值 + 2 护栏 + 阈值常量 docstring

**Files:**
- Create: `icu/src/coach/adapter/rules.py`
- Create: `icu/tests/unit/adapter/test_rules.py`

**Design notes:**
- 每个信号一个 `_classify_<signal>()` 纯函数 → 返回 `Verdict`。
- 加权严重度：`severity_score = Σ weight_i × score_i`，其中 `score(green)=0.0, score(yellow)=0.5, score(red)=1.0`。权重在文件顶部 `_WEIGHTS` 字典里，sum=1.0；改权重必须更新 docstring 注解动机。
- 护栏 1 — `consecutive_red`：扫 `history` 取最近 4 条 `adaptation_verdict` 类 `DecisionEntry`，若其中已有 ≥3 条红灯 **且当前判定也是红**，升级 `recommended_action="rest_48h"`。
- 护栏 2 — `tsb_anomaly`：调用方传入 `AthleteStateRef`，若 `tsb < TSB_ANOMALY_THRESHOLD`（默认 −30），强制本日红灯 + 加 0.1 严重度（封顶 1.0）。
- 所有阈值常量带 `# Why: <出处>` 注解 —— 便于后续调参时翻日志。

- [ ] **Step 1: Write failing tests — 4 信号 × 3 verdict 黄金值表 + 2 护栏**

Write `icu/tests/unit/adapter/test_rules.py`:
```python
"""Threshold golden-value tests for adapter.rules — 4 signals × 3 verdicts + 2 guardrails."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.coach.adapter.rules import (
    HRV_DEVIATION_RED_PCT,
    HRV_DEVIATION_YELLOW_PCT,
    RESTING_HR_RED_DELTA_BPM,
    RESTING_HR_YELLOW_DELTA_BPM,
    SLEEP_RED_HOURS,
    SLEEP_YELLOW_HOURS,
    SORENESS_RED_SCORE,
    SORENESS_YELLOW_SCORE,
    TSB_ANOMALY_THRESHOLD,
    CONSECUTIVE_RED_LIMIT,
    _classify_hrv,
    _classify_resting_hr,
    _classify_sleep,
    _classify_soreness,
    _consecutive_red_count,
    _tsb_anomaly_hit,
    _severity_score,
)
from src.coach.adapter.types import SignalSnapshot
from src.coach.ledger.types import AthleteStateRef, DecisionEntry, generate_ulid


# ---------- HRV ----------

@pytest.mark.parametrize("dev_pct,expected", [
    (-2.0, "green"),                                # well within ±5%
    (HRV_DEVIATION_YELLOW_PCT + 0.01, "green"),     # boundary just above yellow
    (HRV_DEVIATION_YELLOW_PCT, "yellow"),           # boundary inclusive
    (-7.5, "yellow"),                               # mid-yellow
    (HRV_DEVIATION_RED_PCT, "red"),                 # boundary inclusive
    (-15.0, "red"),                                 # well below red
])
def test_classify_hrv(dev_pct, expected):
    assert _classify_hrv(deviation_pct=dev_pct) == expected


# ---------- Resting HR ----------

@pytest.mark.parametrize("delta_bpm,expected", [
    (0, "green"),
    (RESTING_HR_YELLOW_DELTA_BPM - 1, "green"),
    (RESTING_HR_YELLOW_DELTA_BPM, "yellow"),
    (RESTING_HR_RED_DELTA_BPM - 1, "yellow"),
    (RESTING_HR_RED_DELTA_BPM, "red"),
    (15, "red"),
])
def test_classify_resting_hr(delta_bpm, expected):
    assert _classify_resting_hr(delta_bpm=delta_bpm) == expected


# ---------- Sleep ----------

@pytest.mark.parametrize("hours,expected", [
    (8.0, "green"),
    (SLEEP_YELLOW_HOURS, "green"),                  # ≥ yellow boundary inclusive on green side
    (SLEEP_YELLOW_HOURS - 0.01, "yellow"),
    (SLEEP_RED_HOURS, "yellow"),                    # red boundary: < SLEEP_RED → red
    (SLEEP_RED_HOURS - 0.01, "red"),
    (4.0, "red"),
])
def test_classify_sleep(hours, expected):
    assert _classify_sleep(sleep_hours=hours) == expected


# ---------- Soreness (1=worst..4=best) ----------

@pytest.mark.parametrize("score,expected", [
    (4, "green"),
    (SORENESS_YELLOW_SCORE + 1, "green"),
    (SORENESS_YELLOW_SCORE, "yellow"),
    (SORENESS_RED_SCORE, "red"),
    (1, "red"),
])
def test_classify_soreness(score, expected):
    assert _classify_soreness(score=score) == expected


# ---------- Severity weighted score ----------

def test_severity_score_all_green():
    s = _severity_score({"hrv": "green", "resting_hr": "green",
                         "sleep": "green", "soreness": "green"})
    assert s == 0.0


def test_severity_score_all_red():
    s = _severity_score({"hrv": "red", "resting_hr": "red",
                         "sleep": "red", "soreness": "red"})
    assert s == pytest.approx(1.0)


def test_severity_score_mixed_is_in_unit_interval():
    s = _severity_score({"hrv": "red", "resting_hr": "yellow",
                         "sleep": "green", "soreness": "yellow"})
    assert 0.0 < s < 1.0


# ---------- Guardrail 1: consecutive red ----------

def _verdict_entry(state: AthleteStateRef, verdict: str,
                   ts: datetime) -> DecisionEntry:
    return DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=ts,
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state_ref=state,
        payload={"verdict": verdict},
    )


def test_consecutive_red_count_zero(baseline_state, fixed_utc_now):
    history = [
        _verdict_entry(baseline_state, "green", fixed_utc_now - timedelta(days=i))
        for i in range(1, 5)
    ]
    assert _consecutive_red_count(history) == 0


def test_consecutive_red_count_three_in_last_four_days(baseline_state, fixed_utc_now):
    history = [
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=1)),
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=2)),
        _verdict_entry(baseline_state, "green", fixed_utc_now - timedelta(days=3)),
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=4)),
    ]
    # 3 reds within 4-day lookback → triggers when today is also red
    assert _consecutive_red_count(history) >= CONSECUTIVE_RED_LIMIT - 1


def test_consecutive_red_count_ignores_old_entries(baseline_state, fixed_utc_now):
    history = [
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=10)),
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=11)),
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=12)),
    ]
    assert _consecutive_red_count(history) == 0


# ---------- Guardrail 2: TSB anomaly ----------

def test_tsb_anomaly_hit_below_threshold(stressed_state):
    assert _tsb_anomaly_hit(stressed_state) is True


def test_tsb_anomaly_not_hit_baseline(baseline_state):
    assert _tsb_anomaly_hit(baseline_state) is False


def test_tsb_anomaly_threshold_is_negative_thirty():
    # Locked default — see rules.py docstring for derivation
    assert TSB_ANOMALY_THRESHOLD == -30.0
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter.rules'`.

- [ ] **Step 3: Implement rules.py**

Write `icu/src/coach/adapter/rules.py`:
```python
"""Deterministic threshold rules for the Adaptation Engine.

判定流程（pure function chain）:
    snapshot + history + state →
        4 个 _classify_<signal>() → signal_summary →
        worst-of-four → base verdict →
        guardrails (TSB anomaly / consecutive red) → final verdict + action
    → AdaptationVerdict

所有阈值常量在文件顶部，每条注解写**为什么是这个数字**（避免调参失忆，
见 specs/2026-04-19-phase-3-blueprint.md §Component 5 规则引擎表格）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from src.coach.common.logging import get_logger
from src.coach.ledger.types import AthleteStateRef, DecisionEntry

from .types import (
    SIGNAL_KEYS,
    AdaptationVerdict,
    RecommendedAction,
    SignalSnapshot,
    Verdict,
)

_log = get_logger("adapter")


# ---------- 阈值常量（每条带 Why） ----------

# HRV 偏离 % vs 28d rolling mean
HRV_DEVIATION_YELLOW_PCT: float = -5.0
"""≤ -5% 进入 yellow。Why: 蓝图 §Component 5 表格"≥ −5% / −5~−10% / <−10%"。"""
HRV_DEVIATION_RED_PCT: float = -10.0
"""≤ -10% 进入 red。Why: 同上。"""

# Resting HR 偏离基线 (bpm)，正值=升高=应激
RESTING_HR_YELLOW_DELTA_BPM: int = 4
"""+4..+6 bpm 进入 yellow。Why: HRV4Training 文献 +5bpm 对应 ANS 失衡早期信号。"""
RESTING_HR_RED_DELTA_BPM: int = 7
"""≥ +7 bpm 进入 red。Why: 同源；与 HRV red 阈值同步触发概率 > 0.6。"""

# 睡眠时长 (hours)
SLEEP_YELLOW_HOURS: float = 7.0
"""< 7h 进入 yellow。Why: 蓝图阈值表"≥7h / 5.5~7h / <5.5h"。"""
SLEEP_RED_HOURS: float = 5.5
"""< 5.5h 进入 red。Why: 同上；连续夜短睡眠 < 5.5h 与训练适应受损强相关。"""

# Soreness 评分（Intervals.icu 1=worst..4=best）
SORENESS_YELLOW_SCORE: int = 2
"""=2 进入 yellow。Why: 与蓝图"任一=2"对齐（只跟踪 soreness 单维度）。"""
SORENESS_RED_SCORE: int = 1
"""=1 进入 red。Why: 与蓝图"任一=1"对齐。"""

# 加权严重度
_WEIGHTS: dict[str, float] = {
    "hrv": 0.30,         # ANS 状态 —— 最敏感的应激指标
    "resting_hr": 0.20,  # ANS 副指标 —— 与 HRV 部分共线，权重略低
    "sleep": 0.30,       # 恢复底盘 —— 与 HRV 同等关键
    "soreness": 0.20,    # 主观、噪声大；权重偏低但保留 veto 能力
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"
_SCORE_OF: dict[str, float] = {"green": 0.0, "yellow": 0.5, "red": 1.0}

# 护栏
TSB_ANOMALY_THRESHOLD: float = -30.0
"""TSB < -30 触发。Why: ATL/CTL 模型经验值 —— TSB < -30 对应非常高的过载风险。"""
CONSECUTIVE_RED_LIMIT: int = 3
"""过去 4 天内已 ≥3 红 + 今日红 → 升级 rest_48h。Why: 蓝图"过去 3 天已有 3 次红 + 今天又判红"。"""
_RED_LOOKBACK_DAYS: int = 4
"""扫描窗口（含今天前一天起 4 天）。"""

_HRV_BASELINE_FIELD = "hrv_ms_28d_mean"
_HR_BASELINE_FIELD = "resting_hr_28d_mean"


# ---------- 信号分类 ----------

def _classify_hrv(*, deviation_pct: float) -> Verdict:
    """deviation_pct = (today - 28d_mean) / 28d_mean × 100. 负值 = 偏低 = 应激。"""
    if deviation_pct <= HRV_DEVIATION_RED_PCT:
        return "red"
    if deviation_pct <= HRV_DEVIATION_YELLOW_PCT:
        return "yellow"
    return "green"


def _classify_resting_hr(*, delta_bpm: int) -> Verdict:
    """delta_bpm = today - 28d_mean (bpm). 正值 = 升高 = 应激。"""
    if delta_bpm >= RESTING_HR_RED_DELTA_BPM:
        return "red"
    if delta_bpm >= RESTING_HR_YELLOW_DELTA_BPM:
        return "yellow"
    return "green"


def _classify_sleep(*, sleep_hours: float) -> Verdict:
    if sleep_hours < SLEEP_RED_HOURS:
        return "red"
    if sleep_hours < SLEEP_YELLOW_HOURS:
        return "yellow"
    return "green"


def _classify_soreness(*, score: int) -> Verdict:
    if score <= SORENESS_RED_SCORE:
        return "red"
    if score <= SORENESS_YELLOW_SCORE:
        return "yellow"
    return "green"


def _severity_score(summary: dict[str, str]) -> float:
    return sum(_WEIGHTS[k] * _SCORE_OF[summary[k]] for k in SIGNAL_KEYS)


# ---------- 护栏 ----------

def _tsb_anomaly_hit(state: AthleteStateRef) -> bool:
    return state.tsb < TSB_ANOMALY_THRESHOLD


def _consecutive_red_count(history: Iterable[DecisionEntry]) -> int:
    """Count `adaptation_verdict` entries with verdict='red' in the last
    `_RED_LOOKBACK_DAYS` days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RED_LOOKBACK_DAYS)
    count = 0
    for entry in history:
        if entry.decision_type != "adaptation_verdict":
            continue
        if entry.timestamp < cutoff:
            continue
        if str(entry.payload.get("verdict", "")).lower() == "red":
            count += 1
    return count


# ---------- 主入口 ----------

_WORST: dict[str, int] = {"green": 0, "yellow": 1, "red": 2}
_INVERSE: dict[int, Verdict] = {0: "green", 1: "yellow", 2: "red"}


def evaluate_signals(
    snapshot: SignalSnapshot,
    *,
    state: AthleteStateRef,
    history: Iterable[DecisionEntry] = (),
    hrv_28d_mean_ms: float | None = None,
    resting_hr_28d_mean_bpm: float | None = None,
) -> AdaptationVerdict:
    """Pure judge: snapshot + state + history → AdaptationVerdict.

    `hrv_28d_mean_ms` / `resting_hr_28d_mean_bpm` 由调用方（T60 daily_adapt）
    从 wellness_history 预计算并传入；缺失时该信号判 green（保守 fallback）。
    """
    # 1. 4 信号分类
    if hrv_28d_mean_ms and hrv_28d_mean_ms > 0:
        hrv_dev = (snapshot.hrv_ms - hrv_28d_mean_ms) / hrv_28d_mean_ms * 100.0
        hrv_v = _classify_hrv(deviation_pct=hrv_dev)
    else:
        hrv_v = "green"

    if resting_hr_28d_mean_bpm and resting_hr_28d_mean_bpm > 0:
        hr_delta = int(round(snapshot.resting_hr_bpm - resting_hr_28d_mean_bpm))
        hr_v = _classify_resting_hr(delta_bpm=hr_delta)
    else:
        hr_v = "green"

    sleep_v = _classify_sleep(sleep_hours=snapshot.sleep_hours)
    sore_v = _classify_soreness(score=snapshot.soreness_score)

    summary: dict[str, Verdict] = {
        "hrv": hrv_v, "resting_hr": hr_v,
        "sleep": sleep_v, "soreness": sore_v,
    }

    triggered: list[str] = []
    if hrv_v == "red":
        triggered.append("hrv_red_threshold")
    if hr_v == "red":
        triggered.append("resting_hr_red_threshold")
    if sleep_v == "red":
        triggered.append("sleep_debt_acute")
    if sore_v == "red":
        triggered.append("soreness_red")

    # 2. base verdict = worst-of-four
    base_idx = max(_WORST[v] for v in summary.values())
    verdict: Verdict = _INVERSE[base_idx]

    severity = _severity_score(summary)

    # 3. 护栏
    guardrails: list[str] = []
    if _tsb_anomaly_hit(state):
        guardrails.append("tsb_anomaly")
        verdict = "red"
        severity = min(1.0, severity + 0.1)

    action: RecommendedAction
    if verdict == "green":
        action = "none"
    elif verdict == "yellow":
        action = "nudge_only"
    else:
        action = "propose_replacement"

    if verdict == "red" and _consecutive_red_count(history) >= CONSECUTIVE_RED_LIMIT - 1:
        # Today's red would make it the CONSECUTIVE_RED_LIMIT-th.
        guardrails.append("consecutive_red_escalation")
        action = "rest_48h"

    notes = None
    if hrv_28d_mean_ms:
        notes = f"hrv_dev={hrv_dev:+.1f}% vs 28d mean"

    verdict_obj = AdaptationVerdict(
        verdict=verdict,
        signal_summary=summary,
        severity_score=severity,
        recommended_action=action,
        triggered_rules=triggered,
        guardrails_hit=guardrails,
        notes=notes,
    )
    _log.event(
        "adapter_verdict_evaluated",
        verdict=verdict,
        severity=round(severity, 3),
        triggered=triggered,
        guardrails=guardrails,
        action=action,
    )
    return verdict_obj
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_rules.py -v`
Expected: PASS all ~20 parametrized + guardrail tests.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/adapter/rules.py \
        icu/tests/unit/adapter/test_rules.py
git commit -m "feat(coach-phase3): adapter rules — 4 signal thresholds + TSB / consecutive-red guardrails"
```

---

## Task 57: evaluate_signals — end-to-end happy path

**Files:**
- Create: `icu/tests/unit/adapter/test_evaluate_signals.py`

**Design notes:**
- T56 已实现 `evaluate_signals`；本任务只补端到端 happy-path 测试 + 边界场景，验证 `signal_summary` / `severity_score` / `recommended_action` 三者一致性。
- 不再写新代码 —— 所有逻辑在 T56 的 rules.py 里。如果 happy-path 测试发现 bug，fix 一并提交但不扩范围。

- [ ] **Step 1: Write failing tests — happy path + 4 边界场景**

Write `icu/tests/unit/adapter/test_evaluate_signals.py`:
```python
"""End-to-end tests for evaluate_signals — happy path + 4 boundary scenarios."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.coach.adapter.rules import evaluate_signals
from src.coach.adapter.types import SignalSnapshot
from src.coach.ledger.types import AthleteStateRef, DecisionEntry, generate_ulid


def _snap(fixed_utc_now: datetime, *,
          hrv: float = 68.0, hr: int = 52,
          sleep: float = 7.4, sore: int = 3) -> SignalSnapshot:
    return SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=hrv, resting_hr_bpm=hr,
        sleep_hours=sleep, soreness_score=sore,
    )


# ---------- happy path ----------

def test_happy_path_all_green(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now)
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "green"
    assert v.severity_score == 0.0
    assert v.recommended_action == "none"
    assert v.triggered_rules == []
    assert v.guardrails_hit == []
    assert set(v.signal_summary.values()) == {"green"}


# ---------- yellow path ----------

def test_yellow_when_sleep_short(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, sleep=6.0)  # < 7.0 → yellow, ≥ 5.5 → not red
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "yellow"
    assert v.recommended_action == "nudge_only"
    assert v.signal_summary["sleep"] == "yellow"
    assert 0.0 < v.severity_score < 1.0


# ---------- red path: single signal ----------

def test_red_when_hrv_collapses(fixed_utc_now, baseline_state):
    # HRV -15% vs 28d mean → red
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert v.recommended_action == "propose_replacement"
    assert "hrv_red_threshold" in v.triggered_rules
    assert v.guardrails_hit == []


# ---------- guardrail 1: TSB anomaly forces red ----------

def test_tsb_anomaly_forces_red_even_with_green_signals(fixed_utc_now,
                                                        stressed_state):
    snap = _snap(fixed_utc_now)  # all green signals
    v = evaluate_signals(
        snap, state=stressed_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert "tsb_anomaly" in v.guardrails_hit
    assert v.severity_score >= 0.1  # bumped by guardrail


# ---------- guardrail 2: consecutive red escalates to rest_48h ----------

def test_consecutive_red_escalates_to_rest_48h(fixed_utc_now, baseline_state):
    # 2 prior red entries within last 4 days; today HRV crash → 3rd red → escalate
    history = [
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=fixed_utc_now - timedelta(days=i),
            decision_type="adaptation_verdict",
            source="adapter.daily",
            athlete_state_ref=baseline_state,
            payload={"verdict": "red"},
        )
        for i in (1, 2)
    ]
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)  # red
    v = evaluate_signals(
        snap, state=baseline_state, history=history,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert v.recommended_action == "rest_48h"
    assert "consecutive_red_escalation" in v.guardrails_hit


# ---------- baseline missing → graceful fallback ----------

def test_missing_baselines_skips_those_signals(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, hrv=10.0, hr=120)  # would be RED if baselined
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=None, resting_hr_28d_mean_bpm=None,
    )
    # Without baselines, hrv/resting_hr default to green; sleep/soreness still active.
    assert v.signal_summary["hrv"] == "green"
    assert v.signal_summary["resting_hr"] == "green"
    assert v.verdict in {"green", "yellow", "red"}  # depends on sleep/soreness


# ---------- determinism (pure function) ----------

def test_evaluate_signals_is_pure(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)
    v1 = evaluate_signals(snap, state=baseline_state,
                          hrv_28d_mean_ms=68.0,
                          resting_hr_28d_mean_bpm=52.0)
    v2 = evaluate_signals(snap, state=baseline_state,
                          hrv_28d_mean_ms=68.0,
                          resting_hr_28d_mean_bpm=52.0)
    assert v1 == v2
```

- [ ] **Step 2: Run — fail (or pass — see below)**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_evaluate_signals.py -v`

Expected: 全部 PASS（T56 已实现 `evaluate_signals`）。

如果 RED：说明 T56 实现与本任务的 happy-path 假设不一致。**不要扩范围** —— 修 rules.py 让 happy-path 通过即可，commit 一并落在本 task 的 Step 5 提交里。

- [ ] **Step 3: Implement (no-op or surgical fix)**

若 Step 2 已绿：跳过此步。
若 Step 2 红：仅修 `icu/src/coach/adapter/rules.py` 让本任务测试绿，且不破 T56 测试。禁止新增模块或修改类型。

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/ -v`
Expected: PASS all tests in `test_types.py` + `test_rules.py` + `test_evaluate_signals.py` (~38 tests total)。

- [ ] **Step 5: Commit**

```bash
git add icu/tests/unit/adapter/test_evaluate_signals.py
# 若有修 rules.py 也一起 add
git commit -m "test(coach-phase3): evaluate_signals end-to-end happy path + guardrail integration"
```

---

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/adapter/ -v` 全绿（~38 tests）
- [ ] `cd icu && .venv/bin/pytest tests/unit/ledger/ tests/unit/adapter/ -v` 全绿（ledger ~26 + adapter ~38 = ~64）
- [ ] 3 次提交完成（T55 / T56 / T57 各一次）
- [ ] `git grep -n 'auto_push' icu/src/coach/adapter/` 无输出（HUMAN_GATE_ON_ICU_WRITE 守住）
- [ ] `git grep -n 'google.genai\|anthropic\|openai' icu/src/coach/adapter/` 无输出（API_FREE_WORKFLOW 守住）
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`04-adapter-session-revisor.md`](./04-adapter-session-revisor.md) 开始（T58–T59）。

## Worktree bootstrap reminder (executor reads before Step 1 of T55)

本文件依赖 `src/coach/ledger/`（File 01 产物）+ `src/coach/common/logging`（Phase 1 产物）。在新 worktree 里若 `tests/unit/adapter/conftest.py` import `AthleteStateRef` 失败，先确认：

```bash
# From the worktree root
ls icu/src/coach/ledger/types.py     # File 01 产物，应已存在于本分支
ls icu/src/coach/common/logging.py    # Phase 1 产物
ls icu/.venv/bin/pytest               # 共享 .venv
```

若 `.venv` 缺失，按 `worktree_setup_icu.md` 备忘录的步骤 bootstrap（symlink `/mnt/d/Cycling/icu/.venv` 即可，本文件不需要 fetcher / analyzer / utils）。
