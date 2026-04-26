# Phase 3 — Adapter session revisor + prompt builder (Tasks T58–T59)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 在 [03-adapter-infrastructure.md](./03-adapter-infrastructure.md) 已交付的判定基座之上，给 `icu/src/coach/adapter/` 加两层薄皮：
1. **`session_revisor.py`** — 红灯时把当日原始 `SessionType` 按降载映射喂给 Phase 2 `compose_session`，产出合法 `DesignedSession`（或 `None` 表示 Rest）。
2. **`prompt_builder.py`** — 把 `AdaptationVerdict` + `SignalSnapshot`（+ 可选原始/替代 session）渲染成给 athlete 看的 markdown：黄灯 nudge 短文案、红灯 override 完整说明 + 一键命令。

两个文件都只产出**纯字符串 / 纯数据结构**，0 文件 IO，0 网络调用。账本写入、文件落盘、ICU PATCH 全部留给 T60 `daily_adapt.py` 与 T61 `apply_adaptation.py`（File 05），保持本层无副作用。

**Files covered:**
- `icu/src/coach/adapter/__init__.py` (extend exports — re-export `revise_session` / `build_yellow_nudge` / `build_red_override`)
- `icu/src/coach/adapter/session_revisor.py` (new)
- `icu/src/coach/adapter/prompt_builder.py` (new)
- `icu/tests/unit/adapter/test_session_revisor.py` (new)
- `icu/tests/unit/adapter/test_prompt_builder.py` (new)

**Files NOT touched (HARD constraint):**
- `icu/src/coach/adapter/types.py` (T55 产物，read-only)
- `icu/src/coach/adapter/rules.py` (T56–T57 产物，read-only)
- `icu/src/coach/ledger/*` (File 01 产物，只 import types)
- `icu/src/coach/session_designer/*` (Phase 2 产物，只 import `compose_session` + `SessionIntent` + `DesignedSession`)
- `icu/src/coach/periodization/types.py` (Phase 2 产物，只 import `IntensityTier` / `SessionType`)

**Hard constraints (echoed from 00-index.md):**
- `NO_NEW_DEPS`: 只允许 stdlib + Pydantic v2。不引 jinja2 / 任何 templating 包；prompt_builder 用 f-string + `\n.join` 拼字符串。
- `API_FREE_WORKFLOW`: 绝不 import `google.genai` / `anthropic` / `openai` 或任何 LLM SDK；本文件产物全是离线纯函数。
- `PHASE_1_2_IMMUTABILITY`: session_revisor 调 Phase 2 `compose_session` 当**库**用，不改其源码。
- `HUMAN_GATE_ON_ICU_WRITE`: prompt_builder 产出的红灯 markdown **必须**包含 `apply_adaptation.py --confirm` 字串 — 这是用户介入的 single source of truth；没有这条命令字符串的 override 文案视为残品。
- `APPEND_ONLY_LEDGER`: 本文件不写 ledger（写盘是 T60）。
- `RED_NO_AUTO_ESCALATE`: prompt_builder 红灯文案**不得**提示"自动升级到 strict consensus"或类似自动化字样。

**Locked decisions echoed (from 00-index.md):**
- 第 3 条 `HUMAN_GATE_ON_ICU_WRITE`：`build_red_override` 必含一行 `icu/.venv/bin/python scripts/apply_adaptation.py --confirm --date <date>`，且不含 `auto`、`automatic`、`background` 等字样。
- 第 8 条 `NO_NEW_DEPS`：禁 jinja2 / mustache / chevron。

## Mapping table (canonical, used by both T58 implementation and T59 文案)

降载映射，由 `revise_session` 实现，并在 prompt_builder 红灯 override 文案里复述：

| 原 `SessionType` | 桶 (intent bucket) | template_name | 替代 `IntensityTier` | 替代 `target_tss` | 替代 session_type |
|---|---|---|---|---|---|
| `THRESHOLD` / `VO2MAX` / `NEUROMUSCULAR` / `RACE` | HARD | `recovery_spin` | `EASY` | `30` | `RECOVERY` |
| `TEMPO` | MEDIUM | `endurance_long_z2` | `EASY` | `70` | `AEROBIC` |
| `AEROBIC` | EASY | — (return `None`) | — | — | — |
| `RECOVERY` | EASY | — (return `None`) | — | — | — |
| `REST` | REST | — (return `None`) | — | — | — |

Notes:
- HARD 桶选 `recovery_spin`：`workout_library.py` 中唯一的"短主动恢复"模板（单段 30–60 min，0.45–0.55 × CP，Z1）。蓝图原文写"Recovery 45-60 min Z2"，因 `workout_library` 现有模板没有 Z2 短 recovery，本规范以 `recovery_spin` 替代（Z1 < Z2 强度，更安全；duration 40 min 落在 30-60 范围，符合"短"语义）。Phase 4 加新模板时可换。
- MEDIUM 桶选 `endurance_long_z2`：`workout_library` 中唯一的纯 Z2 endurance 模板。`compose_session` 会按 `intent.target_tss=70` 自动拉伸 main 段；模板 `total_duration_s_range=(7200, 14400)` 锁定下限 120 min（蓝图原文写"60-90 min"，但当前模板硬下限 120 min；下限会成为输出 duration）。这与"easy 长骑减少强度，时长可保留"的语义一致 — Phase 4 加 60-90 min Z2 模板时换。
- EASY / RECOVERY / REST：原本就低强度或不骑，红灯下进一步降载 = Rest 完全休息；返回 `None` 表示"no proposed session"，调用方据此跳过 `proposed_session_<date>.json` 落盘。

## Worktree bootstrap reminder (executor reads before Step 1 of T58)

如果你在新 git worktree（如 `git worktree add ../phase-3-adapter-revisor ai-coach-phase-3`）里执行本文件，主仓 `icu/` 的 untracked 资产不会带过来。最低限度需要：

```bash
# 在 worktree 根目录
cd icu
ln -s /mnt/d/Cycling-phase3/icu/.venv .venv      # 复用主仓的 venv
cp -r /mnt/d/Cycling-phase3/icu/src/analyzer .   # phase 1 的 analyzer 包仍未 commit
cp -r /mnt/d/Cycling-phase3/icu/src/utils .
cp -r /mnt/d/Cycling-phase3/icu/src/fetcher .
.venv/bin/pytest tests/unit/adapter/ -q          # 应见 52 passed (File 03 baseline)
```

`pytest` 跑 52 passed 之前**不要**进入 Step 1。

## Task 58: `session_revisor.py` — 降载映射 + Phase 2 compose_session 复用

**Files:**
- Create: `icu/src/coach/adapter/session_revisor.py`
- Create: `icu/tests/unit/adapter/test_session_revisor.py`
- Edit: `icu/src/coach/adapter/__init__.py` (only add re-exports — do not touch existing docstring)

**Design notes:**
- 函数签名（用户已审定）：`revise_session(*, original_type: SessionType, original_date: DateT, physiology: dict, durability: dict, response_profile: dict) -> DesignedSession | None`。所有参数 keyword-only，避免位置参数冲突。
- `original_date` 是 `datetime.date`（与 `compose_session(date=...)` 类型一致），不是 `datetime.datetime`。
- 内部用一个 `_BUCKET` dict 把 `SessionType` 映射到 `(template_name | None, fallback_tier, fallback_tss)`；`None` template_name = 返回 `None`。
- `day_of_week` 从 `original_date.strftime("%a")` 得 (返回如 "Mon")，但 `SessionIntent` 的 pattern 要求三字母首字母大写——`%a` 在 C locale 下就是 `"Mon"/"Tue"/...`，与 pattern 匹配。**为防 locale 漂移**，硬编码一张 `_DOW_NAMES = ("Mon","Tue","Wed","Thu","Fri","Sat","Sun")` 用 `original_date.weekday()` 索引。
- `session_hint` 传一个稳定字符串（如 `"recovery spin"` / `"long z2"`）让 `compose_session` 内部的 keyword 路由命中预期 template；但因为我们直接传 `template_name`，session_hint 仅作为 trace 标记，不影响选模板。
- `compose_session` 是纯函数：输入 dict + intent + template_name，输出 `DesignedSession`，无副作用 — 适合作为 revise_session 的子调用。
- 日志：用 `get_logger("adapter")._log.event("session_revised", date=..., original_type=..., revised_to=..., recommended_action=...)`。**禁止**把 kwarg 起名 `action`（与 `JSONLLogger.event(action: str, ...)` 位置参数冲突，File 03 已踩此坑）。

- [ ] **Step 1: Write failing tests**

Create `icu/tests/unit/adapter/test_session_revisor.py`:

```python
"""Unit tests for adapter.session_revisor — HARD/MEDIUM 降载 + EASY/REST passthrough."""
from __future__ import annotations

from datetime import date

import pytest

from src.coach.adapter.session_revisor import revise_session
from src.coach.periodization.types import IntensityTier, SessionType
from src.coach.session_designer.types import DesignedSession


# ---------- Shared fixtures ----------

@pytest.fixture
def physiology() -> dict:
    return {"cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288}


@pytest.fixture
def durability() -> dict:
    return {"decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1}, "sample_size_rides": 28}


@pytest.fixture
def response_profile() -> dict:
    return {"types": {"vo2max": {"tolerance_class": "mid"}, "threshold": {"tolerance_class": "high"}}}


@pytest.fixture
def fixed_date() -> date:
    return date(2026, 4, 19)  # Sunday


# ---------- HARD bucket → recovery_spin ----------

@pytest.mark.parametrize("hard_type", [
    SessionType.THRESHOLD,
    SessionType.VO2MAX,
    SessionType.NEUROMUSCULAR,
    SessionType.RACE,
])
def test_revise_hard_returns_recovery_spin(
    hard_type, fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=hard_type, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert isinstance(out, DesignedSession)
    assert out.session_type is SessionType.RECOVERY
    assert out.date == "2026-04-19"
    assert out.day_of_week == "Sun"
    # template_name leaks via trace (composer 写入)
    assert out.trace is not None
    assert out.trace["template_name"] == "recovery_spin"
    # duration 落在 recovery_spin 模板的 (1800, 3600)s = 30-60min 范围
    assert 30 <= out.duration_min <= 60


# ---------- MEDIUM bucket → endurance_long_z2 ----------

def test_revise_tempo_returns_endurance_long_z2(
    fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=SessionType.TEMPO, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert isinstance(out, DesignedSession)
    assert out.session_type is SessionType.AEROBIC
    assert out.trace is not None
    assert out.trace["template_name"] == "endurance_long_z2"
    # endurance_long_z2 总时长下限 7200s = 120min（即使 target_tss=70 也压不下来）
    assert out.duration_min >= 120


# ---------- EASY / RECOVERY / REST → None ----------

@pytest.mark.parametrize("low_type", [
    SessionType.AEROBIC,
    SessionType.RECOVERY,
    SessionType.REST,
])
def test_revise_low_intensity_returns_none(
    low_type, fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=low_type, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out is None


# ---------- Determinism / purity ----------

def test_revise_session_idempotent(
    fixed_date, physiology, durability, response_profile,
):
    """Same inputs → same outputs; no hidden state."""
    out1 = revise_session(
        original_type=SessionType.VO2MAX, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    out2 = revise_session(
        original_type=SessionType.VO2MAX, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out1 == out2


def test_revise_session_keyword_only():
    """All parameters must be keyword-only — positional call must fail."""
    with pytest.raises(TypeError):
        revise_session(  # type: ignore[misc]
            SessionType.THRESHOLD, date(2026, 4, 19), {}, {}, {},
        )


def test_revise_session_passes_date_through(
    physiology, durability, response_profile,
):
    """day_of_week computed deterministically from original_date.weekday()."""
    monday = date(2026, 4, 13)  # Monday
    out = revise_session(
        original_type=SessionType.THRESHOLD, original_date=monday,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out is not None
    assert out.day_of_week == "Mon"
    assert out.date == "2026-04-13"
```

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_session_revisor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter.session_revisor'`.

- [ ] **Step 2: Run RED**

Confirm fail message exact: `ModuleNotFoundError`. If you see any other error first, the test file itself has a typo — fix the test, not the source.

- [ ] **Step 3: Implement session_revisor**

Write `icu/src/coach/adapter/session_revisor.py`:

```python
"""红灯降载映射：把今日原始 SessionType 转成低强度替代 DesignedSession。

是 adapter 层最薄的一片：
- 输入：原始 SessionType + 日期 + 生理 / 耐久 / 响应轮廓三个 dict（与 Phase 2 compose_session 一致）。
- 输出：合法 DesignedSession 或 None（None ⇔ Rest，调用方跳过 proposed_session 落盘）。

降载表见 docs/superpowers/plans/phase-3/04-adapter-session-revisor.md §Mapping table。
本文件 0 文件 IO，0 网络调用，纯函数 — 写盘由 scripts/daily_adapt.py 负责。
"""
from __future__ import annotations

from datetime import date as DateT
from typing import Any

from src.coach.common.logging import get_logger
from src.coach.periodization.types import IntensityTier, SessionType
from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import DesignedSession, SessionIntent

_log = get_logger("adapter")

# 三字母 day_of_week，索引 = date.weekday()（0=Mon）。硬编码避免 locale 漂移。
_DOW_NAMES: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# SessionType → (template_name | None, fallback_tier, fallback_tss, session_hint)
# None template_name = 直接返回 None（Rest）。
_BUCKET: dict[SessionType, tuple[str | None, IntensityTier, int, str]] = {
    SessionType.THRESHOLD:     ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.VO2MAX:        ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.NEUROMUSCULAR: ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.RACE:          ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.TEMPO:         ("endurance_long_z2", IntensityTier.EASY, 70, "long z2"),
    SessionType.AEROBIC:       (None,                IntensityTier.REST,  0, ""),
    SessionType.RECOVERY:      (None,                IntensityTier.REST,  0, ""),
    SessionType.REST:          (None,                IntensityTier.REST,  0, ""),
}


def revise_session(
    *,
    original_type: SessionType,
    original_date: DateT,
    physiology: dict[str, Any],
    durability: dict[str, Any],
    response_profile: dict[str, Any],
) -> DesignedSession | None:
    """红灯降载：返回低强度替代 DesignedSession，或 None（= Rest）。

    All-keyword-only signature 防误调。
    """
    bucket = _BUCKET.get(original_type)
    if bucket is None:
        # SessionType 枚举闭合，理论上不可达；防御性返回 None。
        _log.event(
            "session_revised",
            date=original_date.isoformat(),
            original_type=original_type.value,
            revised_to=None,
            recommended_action="rest_passthrough_unknown_type",
        )
        return None

    template_name, fallback_tier, fallback_tss, session_hint = bucket

    if template_name is None:
        _log.event(
            "session_revised",
            date=original_date.isoformat(),
            original_type=original_type.value,
            revised_to=None,
            recommended_action="rest_passthrough",
        )
        return None

    intent = SessionIntent(
        day_of_week=_DOW_NAMES[original_date.weekday()],
        tier=fallback_tier,
        target_tss=fallback_tss,
        session_hint=session_hint,
    )

    revised = compose_session(
        intent=intent,
        date=original_date,
        template_name=template_name,
        physiology=physiology,
        durability=durability,
        response_profile=response_profile,
    )

    _log.event(
        "session_revised",
        date=original_date.isoformat(),
        original_type=original_type.value,
        revised_to=revised.session_type.value,
        recommended_action="propose_replacement",
    )
    return revised
```

Edit `icu/src/coach/adapter/__init__.py` — append re-exports below the existing docstring (do not touch the docstring):

```python
"""Adaptation Engine — Phase 3 每日再评估的判定层。

公开入口：
- SignalSnapshot / AdaptationVerdict: 类型（见 types.py）
- evaluate_signals(snapshot, history) → AdaptationVerdict: 主判定函数（见 rules.py）

本包是 **纯函数层**：输入 dataclass、输出 dataclass，0 文件 IO，0 LLM 调用。
持久化 / ICU PATCH 在 scripts/daily_adapt.py 与 scripts/apply_adaptation.py 完成。
判定规则与阈值见 docs/superpowers/specs/2026-04-19-phase-3-blueprint.md §Component 5。
"""
from .rules import evaluate_signals
from .session_revisor import revise_session
from .types import (
    RECOMMENDED_ACTIONS,
    SIGNAL_KEYS,
    VERDICT_VALUES,
    AdaptationVerdict,
    RecommendedAction,
    SignalSnapshot,
    Verdict,
)

__all__ = [
    "AdaptationVerdict",
    "RECOMMENDED_ACTIONS",
    "RecommendedAction",
    "SIGNAL_KEYS",
    "SignalSnapshot",
    "VERDICT_VALUES",
    "Verdict",
    "evaluate_signals",
    "revise_session",
]
```

(`build_yellow_nudge` / `build_red_override` 在 T59 添加；本步骤先只 export `revise_session`。)

- [ ] **Step 4: Run GREEN + regression**

```bash
cd icu && .venv/bin/pytest tests/unit/adapter/test_session_revisor.py -v
cd icu && .venv/bin/pytest tests/unit/adapter/ -v   # 应 ≥ 52 + 7 = 59 passed
cd icu && .venv/bin/pytest tests/unit/ -x           # 全套不挂（baseline ≥ 457，含 ledger 50 + adapter 52）
```

如全套测试某项之前就因 worktree 缺货失败，先按 §Worktree bootstrap reminder 补齐再判断。

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/adapter/session_revisor.py \
        icu/src/coach/adapter/__init__.py \
        icu/tests/unit/adapter/test_session_revisor.py
git commit -m "feat(coach-phase3): session_revisor — HARD/MEDIUM 降载映射 + EASY/REST passthrough"
```

## Task 59: `prompt_builder.py` — 黄灯 nudge + 红灯 override markdown

**Files:**
- Create: `icu/src/coach/adapter/prompt_builder.py`
- Create: `icu/tests/unit/adapter/test_prompt_builder.py`
- Edit: `icu/src/coach/adapter/__init__.py` (add `build_yellow_nudge` / `build_red_override` to re-exports)

**Design notes:**
- 两个函数，全 keyword-only，全返回 `str`，**禁止**任何 IO（不调 `Path.write_text` / `open(..., "w")`）。落盘由 T60 `daily_adapt.py` 干。
- 都接收 `verdict: AdaptationVerdict`、`snapshot: SignalSnapshot`；区别在 yellow 只多接 `today_session: DesignedSession | None`（用作上下文展示，可选），red 多接 `original` + `proposed: DesignedSession | None`。
- yellow 文案目标：让 athlete 一眼看到"今天偏黄但训练不变"，给一句轻量建议。≤ 8 行 markdown，4 个信号一行表格 + 1 句 advice。
- red 文案目标：让 athlete 一眼明白"今天必须改"+ 看到原始 vs 替代 + 一键确认命令。≥ 15 行 markdown，包含信号表 + 触发规则 + 护栏 + 原 vs 替代 session block + `apply_adaptation.py --confirm` 命令。
- 测试用关键字断言（substring/regex），不做整段字符串等价比对（脆）。
- emoji（🟡/🔴）允许使用以增强 athlete 可读性，不影响 ASCII 关键字断言。

- [ ] **Step 1: Write failing tests**

Create `icu/tests/unit/adapter/test_prompt_builder.py`:

```python
"""Unit tests for adapter.prompt_builder — yellow nudge + red override markdown."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.coach.adapter.prompt_builder import build_red_override, build_yellow_nudge
from src.coach.adapter.session_revisor import revise_session
from src.coach.adapter.types import AdaptationVerdict, SignalSnapshot
from src.coach.periodization.types import SessionType
from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import DesignedSession, SessionIntent


# ---------- Shared fixtures ----------

@pytest.fixture
def physiology() -> dict:
    return {"cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288}


@pytest.fixture
def durability() -> dict:
    return {"decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1}}


@pytest.fixture
def response_profile() -> dict:
    return {"types": {}}


@pytest.fixture
def signal_snapshot(fixed_utc_now) -> SignalSnapshot:
    return SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=44.0,
        resting_hr_bpm=58,
        sleep_hours=5.5,
        soreness_score=2,
    )


@pytest.fixture
def yellow_verdict() -> AdaptationVerdict:
    return AdaptationVerdict(
        verdict="yellow",
        signal_summary={"hrv": "yellow", "resting_hr": "green",
                        "sleep": "yellow", "soreness": "green"},
        severity_score=0.42,
        recommended_action="nudge_only",
        triggered_rules=["hrv_yellow_band", "sleep_yellow_band"],
        guardrails_hit=[],
        notes=None,
    )


@pytest.fixture
def red_verdict() -> AdaptationVerdict:
    return AdaptationVerdict(
        verdict="red",
        signal_summary={"hrv": "red", "resting_hr": "yellow",
                        "sleep": "red", "soreness": "yellow"},
        severity_score=0.81,
        recommended_action="propose_replacement",
        triggered_rules=["hrv_red_threshold", "sleep_red_threshold"],
        guardrails_hit=["consecutive_red_2_days"],
        notes=None,
    )


@pytest.fixture
def original_threshold_session(physiology, durability, response_profile) -> DesignedSession:
    intent = SessionIntent(
        day_of_week="Sun", tier=__import__("src.coach.periodization.types",
                                           fromlist=["IntensityTier"]).IntensityTier.HARD,
        target_tss=85, session_hint="threshold 2x20",
    )
    return compose_session(
        intent=intent, date=date(2026, 4, 19), template_name="threshold_2x20",
        physiology=physiology, durability=durability, response_profile=response_profile,
    )


@pytest.fixture
def proposed_recovery_session(physiology, durability, response_profile) -> DesignedSession | None:
    return revise_session(
        original_type=SessionType.THRESHOLD, original_date=date(2026, 4, 19),
        physiology=physiology, durability=durability, response_profile=response_profile,
    )


# ---------- build_yellow_nudge ----------

def test_yellow_nudge_contains_all_signal_keys(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    for key in ("hrv", "resting_hr", "sleep", "soreness"):
        assert key in md, f"yellow nudge missing signal key: {key}"


def test_yellow_nudge_contains_severity(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    assert "0.42" in md, "yellow nudge must show severity score"


def test_yellow_nudge_marks_yellow_status(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    # Either emoji or word
    assert ("🟡" in md) or ("yellow" in md.lower())


def test_yellow_nudge_keyword_only(yellow_verdict, signal_snapshot):
    with pytest.raises(TypeError):
        build_yellow_nudge(yellow_verdict, signal_snapshot, None)  # type: ignore[misc]


def test_yellow_nudge_returns_str(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    assert isinstance(md, str) and len(md) > 0


def test_yellow_nudge_accepts_today_session_optional(
    yellow_verdict, signal_snapshot, original_threshold_session,
):
    md_with = build_yellow_nudge(
        verdict=yellow_verdict, snapshot=signal_snapshot,
        today_session=original_threshold_session,
    )
    md_without = build_yellow_nudge(
        verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None,
    )
    # 两种都返回 str；带 session 的应包含 session.name
    assert original_threshold_session.name in md_with
    assert original_threshold_session.name not in md_without


# ---------- build_red_override ----------

def test_red_override_contains_apply_command(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert "apply_adaptation.py" in md
    assert "--confirm" in md
    assert "2026-04-19" in md  # date 出现在命令


def test_red_override_lists_original_and_proposed_names(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert original_threshold_session.name in md
    assert proposed_recovery_session is not None
    assert proposed_recovery_session.name in md


def test_red_override_with_proposed_none_shows_rest(
    red_verdict, signal_snapshot, original_threshold_session,
):
    """proposed=None ⇔ Rest 推荐：文案应明示完全休息且仍带 --confirm 命令。"""
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=None,
    )
    assert "Rest" in md or "rest" in md.lower()
    assert "apply_adaptation.py" in md
    assert "--confirm" in md


def test_red_override_lists_triggered_rules_and_guardrails(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    for rule in red_verdict.triggered_rules:
        assert rule in md
    for guard in red_verdict.guardrails_hit:
        assert guard in md


def test_red_override_marks_red_status(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert ("🔴" in md) or ("red" in md.lower())


def test_red_override_keyword_only(red_verdict, signal_snapshot, original_threshold_session):
    with pytest.raises(TypeError):
        build_red_override(  # type: ignore[misc]
            red_verdict, signal_snapshot, original_threshold_session, None,
        )


def test_red_override_no_auto_escalation_language(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    """RED_NO_AUTO_ESCALATE: 文案禁出现 'auto'/'automatic'/'background' 之类自动化字样。"""
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    ).lower()
    for forbidden in ("auto-escalate", "automatic", "auto_push", "background"):
        assert forbidden not in md, f"override 文案不得含自动化字样: {forbidden}"


# ---------- Purity ----------

def test_prompt_builders_no_file_io(
    yellow_verdict, red_verdict, signal_snapshot,
    original_threshold_session, proposed_recovery_session,
    monkeypatch,
):
    """两个函数都禁止任何文件写入：替换 Path.write_text / builtins.open(写) 触发即 FAIL。"""
    from pathlib import Path

    def _fail_write(*a, **kw):
        raise AssertionError("prompt_builder must not write to disk")

    monkeypatch.setattr(Path, "write_text", _fail_write)
    monkeypatch.setattr(Path, "write_bytes", _fail_write)

    real_open = open

    def _guard_open(file, mode="r", *a, **kw):
        if any(c in mode for c in ("w", "a", "x")):
            raise AssertionError(f"prompt_builder must not open() for write: mode={mode}")
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", _guard_open)

    build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot,
                      today_session=original_threshold_session)
    build_red_override(verdict=red_verdict, snapshot=signal_snapshot,
                      original=original_threshold_session, proposed=proposed_recovery_session)
```

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_prompt_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter.prompt_builder'`.

- [ ] **Step 2: Run RED**

Confirm `ModuleNotFoundError` (or `ImportError` for the two function names) is the first error. Anything else = test typo.

- [ ] **Step 3: Implement prompt_builder**

Write `icu/src/coach/adapter/prompt_builder.py`:

```python
"""把 AdaptationVerdict + SignalSnapshot 渲染成 athlete 可读 markdown。

两个公开函数：
- build_yellow_nudge: 短文案，今日不改训练，只挂提示
- build_red_override: 长文案，含原 vs 替代 session block + apply_adaptation 一键命令

两者都是纯字符串拼装；写盘由 scripts/daily_adapt.py 完成。
"""
from __future__ import annotations

from src.coach.adapter.types import AdaptationVerdict, SignalSnapshot
from src.coach.session_designer.types import DesignedSession

# --------- emoji & label helpers ---------

_VERDICT_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

_SIGNAL_LABELS = {
    "hrv": "HRV (ms)",
    "resting_hr": "Resting HR (bpm)",
    "sleep": "Sleep (h)",
    "soreness": "Soreness (1=worst..4=best)",
}


def _signal_value(snapshot: SignalSnapshot, key: str) -> str:
    if key == "hrv":
        return f"{snapshot.hrv_ms:.1f}"
    if key == "resting_hr":
        return f"{snapshot.resting_hr_bpm}"
    if key == "sleep":
        return f"{snapshot.sleep_hours:.1f}"
    if key == "soreness":
        return f"{snapshot.soreness_score}"
    return "?"


def _signal_table_md(verdict: AdaptationVerdict, snapshot: SignalSnapshot) -> str:
    """4 行 markdown 表：信号 / 值 / 状态。"""
    rows = ["| Signal | Value | Status |", "|---|---|---|"]
    for key in ("hrv", "resting_hr", "sleep", "soreness"):
        status = verdict.signal_summary.get(key, "?")
        emoji = _VERDICT_EMOJI.get(status, "")
        rows.append(
            f"| {_SIGNAL_LABELS[key]} | {_signal_value(snapshot, key)} "
            f"| {emoji} {status} ({key}) |"
        )
    return "\n".join(rows)


def _session_block_md(label: str, session: DesignedSession | None) -> str:
    """渲染单个 session 摘要，session=None ⇔ Rest。"""
    if session is None:
        return f"**{label}:** Rest（完全休息，不骑）"
    return (
        f"**{label}:** {session.name}\n"
        f"- type: {session.session_type.value}\n"
        f"- duration: {session.duration_min} min\n"
        f"- target TSS: {session.target_tss}\n"
        f"- description: {session.description}"
    )


# --------- public functions ---------


def build_yellow_nudge(
    *,
    verdict: AdaptationVerdict,
    snapshot: SignalSnapshot,
    today_session: DesignedSession | None,
) -> str:
    """黄灯 nudge：短文案，今日训练不变，只挂提示让 athlete 心里有数。"""
    emoji = _VERDICT_EMOJI[verdict.verdict]
    parts = [
        f"# {emoji} Yellow nudge — {verdict.verdict.upper()} / severity {verdict.severity_score:.2f}",
        "",
        _signal_table_md(verdict, snapshot),
        "",
        "**Action:** 今日训练**不变**；建议主观感受偏差大时酌情降一档强度（如把 sweet-spot 替成 tempo），"
        "warmup 多花 5 分钟评估身体。",
    ]
    if verdict.triggered_rules:
        parts.append("")
        parts.append(f"**Triggered:** {', '.join(verdict.triggered_rules)}")
    if today_session is not None:
        parts.append("")
        parts.append(_session_block_md("Today's session", today_session))
    return "\n".join(parts) + "\n"


def build_red_override(
    *,
    verdict: AdaptationVerdict,
    snapshot: SignalSnapshot,
    original: DesignedSession | None,
    proposed: DesignedSession | None,
) -> str:
    """红灯 override：长文案，含信号表 + 触发规则 + 护栏 + 原 vs 替代 session + 一键命令。"""
    emoji = _VERDICT_EMOJI[verdict.verdict]
    date_str = (
        original.date if original is not None
        else (proposed.date if proposed is not None else "<DATE>")
    )

    parts = [
        f"# {emoji} Red override — {verdict.verdict.upper()} / severity {verdict.severity_score:.2f}",
        "",
        _signal_table_md(verdict, snapshot),
        "",
        f"**Triggered rules:** {', '.join(verdict.triggered_rules) if verdict.triggered_rules else '(none)'}",
        f"**Guardrails hit:** {', '.join(verdict.guardrails_hit) if verdict.guardrails_hit else '(none)'}",
        "",
        _session_block_md("Original (planned)", original),
        "",
        _session_block_md("Proposed (downgraded)", proposed),
        "",
        "## Apply (human gate)",
        "",
        "运行下面的命令以把替代 session 写回 ICU；不运行 = 保持原计划：",
        "",
        "```",
        f"icu/.venv/bin/python scripts/apply_adaptation.py --confirm --date {date_str}",
        "```",
    ]
    if verdict.notes:
        parts.append("")
        parts.append(f"**Notes:** {verdict.notes}")
    return "\n".join(parts) + "\n"
```

Edit `icu/src/coach/adapter/__init__.py` — extend re-exports added in T58:

```python
from .prompt_builder import build_red_override, build_yellow_nudge
from .rules import evaluate_signals
from .session_revisor import revise_session
from .types import (
    RECOMMENDED_ACTIONS,
    SIGNAL_KEYS,
    VERDICT_VALUES,
    AdaptationVerdict,
    RecommendedAction,
    SignalSnapshot,
    Verdict,
)

__all__ = [
    "AdaptationVerdict",
    "RECOMMENDED_ACTIONS",
    "RecommendedAction",
    "SIGNAL_KEYS",
    "SignalSnapshot",
    "VERDICT_VALUES",
    "Verdict",
    "build_red_override",
    "build_yellow_nudge",
    "evaluate_signals",
    "revise_session",
]
```

(docstring 保持不动；只加底部 imports + `__all__` 扩列。)

- [ ] **Step 4: Run GREEN + regression**

```bash
cd icu && .venv/bin/pytest tests/unit/adapter/test_prompt_builder.py -v
cd icu && .venv/bin/pytest tests/unit/adapter/ -v   # 应 ≥ 52 + 7 (T58) + ~12 (T59) ≈ 71 passed
cd icu && .venv/bin/pytest tests/unit/ -x           # 全套不挂
```

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/adapter/prompt_builder.py \
        icu/src/coach/adapter/__init__.py \
        icu/tests/unit/adapter/test_prompt_builder.py
git commit -m "feat(coach-phase3): prompt_builder — yellow nudge + red override markdown"
```

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/adapter/ -v` 全绿 (≥ 71 tests)
- [ ] `cd icu && .venv/bin/pytest tests/unit/ledger/ tests/unit/adapter/ -v` 全绿 (ledger 50 + adapter ≥ 71)
- [ ] `cd icu && .venv/bin/pytest tests/unit/ -x` 全套不挂
- [ ] 2 次提交完成（T58 / T59 各一次）
- [ ] `git grep -n 'auto_push' icu/src/coach/adapter/` 无输出（HUMAN_GATE_ON_ICU_WRITE 守住）
- [ ] `git grep -nE 'google\.genai|anthropic|openai' icu/src/coach/adapter/` 无输出（API_FREE_WORKFLOW 守住）
- [ ] `git grep -n 'from src.coach.session_designer' icu/src/coach/adapter/session_revisor.py` 应输出 ≥ 2 行（允许的依赖）
- [ ] `git grep -nE 'open\(.+["\x27](w|a|x)' icu/src/coach/adapter/prompt_builder.py` 与 `git grep -n 'write_text\|write_bytes' icu/src/coach/adapter/prompt_builder.py` 都为空（prompt_builder 0 IO）
- [ ] `python -c "from src.coach.adapter import revise_session, build_yellow_nudge, build_red_override; print('ok')"` 在 `cd icu && .venv/bin/python -c "..."` 下输出 `ok`
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`05-adapter-integration.md`](./05-adapter-integration.md) 开始（T60–T61，scripts/daily_adapt.py 真正写 ledger + ICU PATCH）

## Known pitfalls (写在最前面给 implementer 看)

1. **`_log.event(action=...)` 冲突**：`JSONLLogger.event(action: str, *, ...)` 把 `action` 作为位置参数。任何 `_log.event("foo", action="...")` 会报 `TypeError: multiple values for argument 'action'`。本文件的 session_revisor 调 `_log.event("session_revised", date=..., recommended_action=...)`，避开冲突。**禁止**自己加 `action=` kwarg。File 03 已踩此坑。

2. **`IntensityTier` 是 enum，不是字符串字面量**：必须 `IntensityTier.EASY`，不能 `"EASY"`。Pydantic v2 会接受字符串 coerce，但 `_BUCKET` dict 里直接写 enum 值更显眼、更安全。

3. **`DateT` 是 `datetime.date`，不是 `datetime.datetime`**：`compose_session(date=...)` 签名锁死 `DateT`。`SessionIntent.day_of_week` pattern 要 `Mon/Tue/.../Sun`，不要传 `date.strftime("%A")` (那是 "Monday" 长格式)。本文件硬编码 `_DOW_NAMES` 用 `weekday()` 索引避免 locale 漂移。

4. **`recovery_spin` 不是真 Z2**：`workout_library.py` 中 `recovery_spin` 是单段 0.45-0.55 × CP / Z1（蓝图原文写"Recovery 45-60min Z2"，但模板没注册 Z2 短 recovery）。Spec 已锁定用 `recovery_spin` 当 HARD 桶降载目标 — 不要去改 `workout_library.py` 来"匹配蓝图"，那违反 PHASE_1_2_IMMUTABILITY。

5. **`endurance_long_z2` 时长不能 < 120 min**：模板 `total_duration_s_range=(7200, 14400)` 锁定。即使 `target_tss=70` 在 `_scale_long_ride_to_tss` 里也压不到 60-90 min（蓝图原文要 60-90 min Z2，但当前模板硬下限 120 min）。spec 已在 `test_revise_tempo_returns_endurance_long_z2` 用 `assert out.duration_min >= 120` 锁定预期。**不要**为了"满足蓝图 60-90"去改模板源码。

6. **`response_profile["types"]` 字典键大小写**：`compose_session` 内部用 `k.lower() == type_key.lower()` 不区分大小写匹配，所以测试 fixture 里随便起 `"vo2max"` 还是 `"VO2max"` 都行；不要写 case-sensitive 断言。

7. **`freeze_now` 不需要**：session_revisor 不调 `datetime.now()`（用户已审定），prompt_builder 也不调。`tests/unit/adapter/conftest.py` 的 `freeze_now` fixture 是 T56-T57 的 rules 模块用的，本文件测试**不要 request 它**（请求会触发对 rules 模块的 monkeypatch，但当前测试根本不进 rules 路径，无意义）。本文件测试只 request `fixed_utc_now`（T55 conftest fixture，纯 const）。

8. **`SessionIntent.target_tss` 上限 400**：`_BUCKET` 里写 30/70 是安全值；如果将来要加 `recovery_spin` target_tss=100 这种，要看清模板自身能不能达到 — recovery_spin 自然 TSS ≈ 17，target_tss=100 + diff_pct > 15% 会让 composer 把 final_tss 改回估算值（17）。当前 30/70 是手调过的不会触发该路径的安全值。

9. **测试不要用真 ICU client**：session_revisor 是纯函数，不调网络。`physiology / durability / response_profile` 全是测试 fixture dict，不要 mock 真 ICU 端点。

10. **prompt_builder 不要尝试 import jinja2**：`NO_NEW_DEPS`。f-string + `\n.join` 拼字符串足够。
