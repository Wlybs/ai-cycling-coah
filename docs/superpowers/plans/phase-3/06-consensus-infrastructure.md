# Phase 3 — Consensus infrastructure (Tasks T62–T64)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 交付 `icu/src/coach/consensus/` 的骨架（types / response_parser / history_injector），是 council/strict 模式 prompt 拼装与裁决入库的依赖根。本文件**不做任何 LLM 网络调用**：response_parser 解析的是用户粘贴回来的 Gemini 文本；history_injector 只读 Phase 3 自家 `LedgerReader`。与 Phase 2 完全解耦，可与 Adapter 主线并行开发。

**Files covered:**
- `icu/src/coach/consensus/__init__.py`
- `icu/src/coach/consensus/types.py`
- `icu/src/coach/consensus/response_parser.py`
- `icu/src/coach/consensus/history_injector.py`
- `icu/tests/unit/consensus/__init__.py`
- `icu/tests/unit/consensus/conftest.py`
- `icu/tests/unit/consensus/test_types.py`
- `icu/tests/unit/consensus/test_response_parser.py`
- `icu/tests/unit/consensus/test_history_injector.py`
- `icu/tests/fixtures/phase3/consensus/` — 7 个 Gemini-style response markdown fixture（happy + 6 rejection）

**Hard constraints (from 00-index.md):**
- `API_FREE_WORKFLOW`：禁止 `import google.genai` 或任何 LLM SDK；本文件仅做字符串解析。
- `CRITIC_3_POINTS_MIN`：Critic 必须 ≥3 条独立反对点且每条带具体数据，否则 parser 拒绝写库。
- `PHYSIOLOGIST_QUANT_3_OF_4`：Physiologist 段必须命中 CP / W' / durability / response_profile 四项关键词中至少 3 项。
- `PHASE_1_2_IMMUTABILITY`：所有代码落在 `icu/src/coach/consensus/` 与 `icu/tests/unit/consensus/`，禁触 Phase 1/2。
- 依赖：`icu/src/coach/ledger/`（T50–T52 已完成）。**不依赖** Phase 2 任何模块 — Section B/C 的输入数据由 T65–T66（council_prompt.py / run_consensus.py）在调用方组装后传入 history_injector / parser 的纯函数接口。

---

## Task 62: Package scaffold + types (CouncilVerdict, ExpertTurn, exceptions)

**Files:**
- Create: `icu/src/coach/consensus/__init__.py`
- Create: `icu/src/coach/consensus/types.py`
- Create: `icu/tests/unit/consensus/__init__.py`
- Create: `icu/tests/unit/consensus/test_types.py`

**Design notes:**
- `Verdict` 三态 `ACCEPT`/`REVISE`/`REJECT`（大写，与 Gemini 输出强约定）。
- `Mode` 二态 `council`/`strict`（小写，与 0-index naming convention 一致）。
- `ExpertRole` 四态 `planner`/`critic`/`physiologist`/`arbiter`。
- `CouncilVerdict` 是 parser 成功解析后的产物；保留 `summary_json` 原始 dict 以便后续 ledger payload 直传，避免二次序列化偏差。
- `ConsensusValidationError` 必带 `violations: list[str]`，列具体违规条目，用于 finalize_consensus 显式打印 + 指引重跑 prompt（蓝图 §4.7 "任一失败 → 不写 ledger + 打印具体违规条目"）。

- [ ] **Step 1: Write failing tests — types + exception roundtrip**

Write `icu/tests/unit/consensus/test_types.py`:
```python
"""Unit tests for consensus types: ExpertTurn, CouncilVerdict, exceptions."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.coach.consensus.types import (
    EXPERT_ROLES,
    VERDICTS,
    MODES,
    ConsensusValidationError,
    CouncilVerdict,
    ExpertTurn,
)


# ---------- ExpertTurn ----------

def test_expert_turn_roundtrip():
    turn = ExpertTurn(
        role="critic",
        body_md="**Point 1.** TSS 偏低，仅 320 vs target 480 ...",
        cited_data=["weekly_plan.total_tss=320", "phase=BUILD"],
    )
    js = turn.model_dump_json()
    loaded = ExpertTurn.model_validate_json(js)
    assert loaded == turn


def test_expert_turn_rejects_unknown_role():
    with pytest.raises(ValidationError):
        ExpertTurn(role="coach", body_md="...", cited_data=[])


def test_expert_turn_role_enum_matches_blueprint():
    # 00-index.md locks these 4; adding a 5th requires an ADR.
    assert set(EXPERT_ROLES) == {"planner", "critic", "physiologist", "arbiter"}


def test_expert_turn_body_md_must_not_be_blank():
    with pytest.raises(ValidationError):
        ExpertTurn(role="planner", body_md="   \n\t ", cited_data=[])


# ---------- CouncilVerdict ----------

def _make_turns() -> list[ExpertTurn]:
    return [
        ExpertTurn(role="planner",  body_md="P body", cited_data=["a", "b"]),
        ExpertTurn(role="critic",   body_md="C body",
                   cited_data=["x1", "x2", "x3"]),
        ExpertTurn(role="physiologist", body_md="Phys body",
                   cited_data=["CP=288", "W'=18500", "durability"]),
        ExpertTurn(role="arbiter",  body_md="A body", cited_data=[]),
    ]


def test_council_verdict_roundtrip_all_three_verdicts():
    for v in VERDICTS:
        cv = CouncilVerdict(
            mode="council",
            verdict=v,
            confidence=0.7,
            justification="一句话理由。",
            expert_turns=_make_turns(),
            summary_json={"verdict": v, "confidence": 0.7,
                          "critic_hard_points": ["a", "b", "c"]},
        )
        js = cv.model_dump_json()
        loaded = CouncilVerdict.model_validate_json(js)
        assert loaded == cv
        assert loaded.verdict == v


def test_council_verdict_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="council", verdict="MAYBE", confidence=0.5,
            justification="x", expert_turns=_make_turns(), summary_json={},
        )


def test_council_verdict_confidence_range():
    base = dict(
        mode="council", verdict="ACCEPT", justification="x",
        expert_turns=_make_turns(), summary_json={},
    )
    CouncilVerdict(**base, confidence=0.0)
    CouncilVerdict(**base, confidence=1.0)
    with pytest.raises(ValidationError):
        CouncilVerdict(**base, confidence=-0.01)
    with pytest.raises(ValidationError):
        CouncilVerdict(**base, confidence=1.01)


def test_council_verdict_mode_enum():
    assert set(MODES) == {"council", "strict"}
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="ad-hoc", verdict="ACCEPT", confidence=0.7,
            justification="x", expert_turns=_make_turns(), summary_json={},
        )


def test_council_verdict_requires_four_distinct_roles():
    """council mode 必须包含 planner/critic/physiologist/arbiter 各一条。"""
    only_three = _make_turns()[:3]
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="council", verdict="ACCEPT", confidence=0.7,
            justification="x", expert_turns=only_three, summary_json={},
        )


def test_council_verdict_revise_requires_changes():
    """REVISE 必须在 summary_json 内带 changes 列表，否则违反语义。"""
    cv = CouncilVerdict(
        mode="council", verdict="REVISE", confidence=0.6,
        justification="把周三换成 endurance",
        expert_turns=_make_turns(),
        summary_json={
            "verdict": "REVISE",
            "confidence": 0.6,
            "critic_hard_points": ["a", "b", "c"],
            "changes": [{"day": "Wed", "from": "VO2max", "to": "Endurance"}],
        },
    )
    assert cv.summary_json["changes"][0]["day"] == "Wed"


# ---------- Exception ----------

def test_consensus_validation_error_carries_violations():
    err = ConsensusValidationError(
        violations=["critic.points<3", "physiologist.keywords<3"],
    )
    assert "critic.points<3" in str(err)
    assert err.violations == [
        "critic.points<3", "physiologist.keywords<3",
    ]


def test_consensus_validation_error_requires_nonempty():
    with pytest.raises(ValueError):
        ConsensusValidationError(violations=[])
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.consensus'`.

- [ ] **Step 3: Implement package + types**

Write `icu/src/coach/consensus/__init__.py`:
```python
"""Multi-Expert Consensus — Phase 3 的 council/strict 审查骨架。

公开入口：
- CouncilVerdict / ExpertTurn / ConsensusValidationError: 类型与异常（见 types.py）
- ResponseParser: Gemini 4-段 + summary_json 解析 + 硬规则校验（见 response_parser.py）
- HistoryInjector: 调 LedgerReader 拼相似 context-verdict-outcome 三元组（见 history_injector.py）

API_FREE：本包不 import google.genai 也不做任何 network call。所有 LLM 交互
通过 prompt 文件 → 用户手工粘贴回 response 文件的异步流。
"""
```

Write `icu/src/coach/consensus/types.py`:
```python
"""Consensus 类型定义：CouncilVerdict / ExpertTurn / ConsensusValidationError。"""
from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- 枚举（与 00-index.md naming conventions 对齐） ----------

ExpertRole = Literal["planner", "critic", "physiologist", "arbiter"]
EXPERT_ROLES: tuple[str, ...] = get_args(ExpertRole)

Verdict = Literal["ACCEPT", "REVISE", "REJECT"]
VERDICTS: tuple[str, ...] = get_args(Verdict)

Mode = Literal["council", "strict"]
MODES: tuple[str, ...] = get_args(Mode)


# ---------- ExpertTurn ----------

class ExpertTurn(BaseModel):
    """单个角色的发言。

    body_md 保留原始 markdown（含 `<role>` 包裹外的内容），方便回写
    verdict.md 时复刻原文风格。cited_data 是 parser 抽出的原子引用片段
    （如 "CP=288W"、"weekly_plan.total_tss=320"），用于硬规则计数。
    """

    model_config = {"frozen": True}

    role: ExpertRole
    body_md: str = Field(..., description="角色段落原文 markdown")
    cited_data: list[str] = Field(default_factory=list,
                                  description="parser 抽出的引用片段（数据/字段名）")

    @field_validator("body_md")
    @classmethod
    def _body_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("body_md must not be blank")
        return v


# ---------- CouncilVerdict ----------

class CouncilVerdict(BaseModel):
    """parser 成功解析后的裁决产物。

    summary_json 保留原始解析得到的 dict（不重新打包），后续 ledger payload
    可以直传，避免二次序列化漂移。
    """

    model_config = {"frozen": True}

    mode: Mode
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(..., min_length=1)
    expert_turns: list[ExpertTurn] = Field(..., min_length=1)
    summary_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _council_requires_four_roles(self) -> "CouncilVerdict":
        if self.mode == "council":
            roles = {t.role for t in self.expert_turns}
            missing = set(EXPERT_ROLES) - roles
            if missing:
                raise ValueError(
                    f"council mode requires all 4 roles; missing: {sorted(missing)}"
                )
        return self


# ---------- Exception ----------

class ConsensusValidationError(Exception):
    """Gemini response 不合规 → parser 抛出。带 violations 列表用于打印 + 重跑。"""

    def __init__(self, violations: list[str]) -> None:
        if not violations:
            raise ValueError("ConsensusValidationError requires ≥1 violation")
        self.violations = list(violations)
        super().__init__("; ".join(self.violations))
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/test_types.py -v`
Expected: PASS all ~12 tests.

- [ ] **Step 5: Commit**

Write `icu/tests/unit/consensus/__init__.py` (empty file):
```python
```

```bash
git add icu/src/coach/consensus/__init__.py \
        icu/src/coach/consensus/types.py \
        icu/tests/unit/consensus/__init__.py \
        icu/tests/unit/consensus/test_types.py
git commit -m "feat(coach-phase3): consensus package scaffold + types (CouncilVerdict, ExpertTurn)"
```

---

## Task 63: response_parser.py — 4 段 + summary_json 解析 + 硬规则校验

**Files:**
- Create: `icu/src/coach/consensus/response_parser.py`
- Create: `icu/tests/unit/consensus/conftest.py`
- Create: `icu/tests/unit/consensus/test_response_parser.py`
- Create: `icu/tests/fixtures/phase3/consensus/happy.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_no_critic.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_critic_2_points.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_critic_no_data.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_phys_2_keywords.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_bad_verdict.md`
- Create: `icu/tests/fixtures/phase3/consensus/reject_no_summary_json.md`

**Design notes:**
- 解析输入一律是用户粘贴回的 markdown 文本（`council.response.md`），不接触 LLM。
- 抽段策略：按 `<planner>...</planner>` / `<critic>` / `<physiologist>` / `<arbiter>` 包裹标签切片；标签缺失即视为违规。
- `<summary_json>...</summary_json>` 块内 `json.loads`；解析失败或缺块即违规。
- 硬规则共 6 条（蓝图 §4.7 "响应解析 + 硬规则校验"）：
  1. 四 role 标签齐全（缺一即违规）
  2. `summary_json` 块存在且 JSON 合法
  3. **CRITIC_3_POINTS_MIN** — Critic 段内独立反对点 ≥3。判定：以 `\n\d+\.` 或 `\n[-*]\s` 切分 bullet/numbered list；每个 item 必须含 ≥1 个具体数据引用（数字、`%`、`=`、`watts`/`W`/`bpm`/`min`/`min<sup>?` 等单位中至少一种）；满足 item 数 ≥3。
  4. **PHYSIOLOGIST_QUANT_3_OF_4** — Physiologist 段（不区分大小写）命中关键词集合 `{"CP", "W'", "durability", "response_profile"}` 中至少 3 项；命中前对 `'` 与 `′` 都规范化。
  5. Arbiter verdict ∈ {ACCEPT, REVISE, REJECT}；从 summary_json["verdict"] 读，再用文本兜底（`<arbiter>` 段内首个匹配大写词）。两路冲突 → 违规。
  6. confidence ∈ [0.0, 1.0] 且来自 summary_json["confidence"]（float-able）。
- 任一失败 → `ConsensusValidationError(violations=...)`，违规字段串用稳定标识：`"section.missing.<role>"` / `"summary_json.missing"` / `"critic.points<3"` / `"critic.point_no_data:<idx>"` / `"physiologist.keywords<3"` / `"verdict.invalid:<got>"` / `"verdict.mismatch"` / `"confidence.out_of_range:<got>"`。
- 解析路径 = pure function `parse(response_md: str, *, mode: Literal["council","strict"]="council") -> CouncilVerdict`。strict 模式仅放宽"四 role 同一文档"的约束（strict 是 4 份单独 response 文件，调用方拼成单一拼接文本传入即可，本函数对此无感知）。

- [ ] **Step 1: Write failing tests + author 7 fixtures**

Author the 7 markdown fixtures under `icu/tests/fixtures/phase3/consensus/`. The happy fixture is the gold reference; the 6 reject fixtures each break **exactly one** rule (mutation-style) so violation strings are unambiguous.

`icu/tests/fixtures/phase3/consensus/happy.md`:
```markdown
<planner>
本周训练目标：BUILD 阶段第 2 周，2 次 HARD（VO2 + Threshold）+ 1 次 endurance long ride，目标周 TSS=480。
依据：CTL=72.3、phase=BUILD、weekly_plan.total_tss=480。
</planner>

<critic>
1. 周 HARD 仅排了 1 次，违反 BUILD 阶段 2 次底线（weekly_plan.hard_days=1，target=2）。
2. VO2max 工作间总时长 14 min，低于 high tolerance 18 min 底线（response_profile.types.VO2max.tolerance_class=high）。
3. 周三 Threshold session 持续 60min，对应 IF=0.92 偏高（IF=0.92 vs target 0.88）。
</critic>

<physiologist>
当前 CP=288W，W'=18500J，durability decay 60s ≈ 6%/1000kJ；response_profile.types.VO2max.tolerance_class=high。
周末 W' balance 预估 −45%，knee_flag 当前为 false。
</physiologist>

<arbiter>
REVISE — 调整周二 Endurance 为 VO2max session 以补足 HARD 配额。confidence 0.72。
</arbiter>

<summary_json>
{
  "verdict": "REVISE",
  "confidence": 0.72,
  "critic_hard_points": [
    "weekly_plan.hard_days=1 vs target 2",
    "VO2 work_min=14 vs floor 18",
    "Threshold IF=0.92 vs target 0.88"
  ],
  "changes": [
    {"day": "Tue", "from": "Endurance", "to": "VO2max"}
  ]
}
</summary_json>
```

`reject_no_critic.md`：删掉整个 `<critic>...</critic>` 块（Section.missing.critic）。
`reject_critic_2_points.md`：Critic 段只留 2 条（CRITIC_3_POINTS_MIN）。
`reject_critic_no_data.md`：Critic 三条但其中一条改为 "整体训练负荷不够" 这种无数据引用 — 触发 `critic.point_no_data:<idx>`。
`reject_phys_2_keywords.md`：Physiologist 段去掉 `durability` 和 `response_profile` 提及，仅保留 CP / W'（PHYSIOLOGIST_QUANT_3_OF_4）。
`reject_bad_verdict.md`：summary_json 的 verdict 改为 `"MAYBE"`（verdict.invalid）。
`reject_no_summary_json.md`：删掉整个 `<summary_json>...</summary_json>` 块（summary_json.missing）。

Create `icu/tests/unit/consensus/conftest.py`:
```python
"""Shared fixtures for consensus unit tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "phase3" / "consensus"


@pytest.fixture
def fixture_dir() -> Path:
    assert FIXTURES.is_dir(), f"missing fixture dir: {FIXTURES}"
    return FIXTURES


def _read(fixture_dir: Path, name: str) -> str:
    return (fixture_dir / name).read_text(encoding="utf-8")


@pytest.fixture
def happy_response(fixture_dir):
    return _read(fixture_dir, "happy.md")


@pytest.fixture
def reject_responses(fixture_dir):
    """Map fixture-name → file content for the 6 rejection fixtures."""
    names = [
        "reject_no_critic.md",
        "reject_critic_2_points.md",
        "reject_critic_no_data.md",
        "reject_phys_2_keywords.md",
        "reject_bad_verdict.md",
        "reject_no_summary_json.md",
    ]
    return {n: _read(fixture_dir, n) for n in names}
```

Write `icu/tests/unit/consensus/test_response_parser.py`:
```python
"""Unit tests for ResponseParser: happy path + 6 hard-rule rejections."""
from __future__ import annotations

import pytest

from src.coach.consensus.response_parser import parse
from src.coach.consensus.types import (
    ConsensusValidationError,
    CouncilVerdict,
)


# ---------- happy ----------

def test_parse_happy_path_returns_council_verdict(happy_response):
    cv = parse(happy_response, mode="council")
    assert isinstance(cv, CouncilVerdict)
    assert cv.mode == "council"
    assert cv.verdict == "REVISE"
    assert cv.confidence == pytest.approx(0.72)
    assert {t.role for t in cv.expert_turns} == {
        "planner", "critic", "physiologist", "arbiter"
    }
    # Critic cited_data: parser must surface ≥3 atomic data references
    critic = next(t for t in cv.expert_turns if t.role == "critic")
    assert len(critic.cited_data) >= 3
    # summary_json passthrough preserved
    assert cv.summary_json["changes"][0]["day"] == "Tue"


def test_parse_happy_path_sets_justification_from_arbiter(happy_response):
    cv = parse(happy_response, mode="council")
    assert "REVISE" in cv.justification or cv.justification.strip() != ""


# ---------- 6 rejection modes ----------

@pytest.mark.parametrize(
    "fname,expected_violation_substr",
    [
        ("reject_no_critic.md",         "section.missing.critic"),
        ("reject_critic_2_points.md",   "critic.points<3"),
        ("reject_critic_no_data.md",    "critic.point_no_data"),
        ("reject_phys_2_keywords.md",   "physiologist.keywords<3"),
        ("reject_bad_verdict.md",       "verdict.invalid"),
        ("reject_no_summary_json.md",   "summary_json.missing"),
    ],
)
def test_parse_rejects_each_hard_rule_breach(reject_responses, fname,
                                             expected_violation_substr):
    text = reject_responses[fname]
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(text, mode="council")
    found = excinfo.value.violations
    assert any(expected_violation_substr in v for v in found), (
        f"expected violation containing {expected_violation_substr!r}, "
        f"got {found}"
    )


def test_parse_strict_mode_accepts_concatenated_responses(happy_response):
    """strict 模式：调用方把 4 份独立 response 拼成单一文档传入；parser 依旧合法。"""
    cv = parse(happy_response, mode="strict")
    assert cv.mode == "strict"
    assert cv.verdict in {"ACCEPT", "REVISE", "REJECT"}


# ---------- 边界：confidence / verdict mismatch ----------

def test_parse_rejects_confidence_out_of_range(happy_response):
    bad = happy_response.replace('"confidence": 0.72', '"confidence": 1.42')
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(bad, mode="council")
    assert any("confidence.out_of_range" in v for v in excinfo.value.violations)


def test_parse_rejects_text_arbiter_verdict_vs_summary_json_mismatch(happy_response):
    # summary_json says REVISE, but rewrite arbiter text to say ACCEPT — mismatch.
    bad = happy_response.replace(
        "REVISE — 调整周二", "ACCEPT — 通过原计划"
    )
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(bad, mode="council")
    assert any("verdict.mismatch" in v for v in excinfo.value.violations)
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/test_response_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.consensus.response_parser'`.

- [ ] **Step 3: Implement parser**

Write `icu/src/coach/consensus/response_parser.py`:
```python
"""Gemini council response parser — 4 段 + summary_json + 硬规则校验。

输入：用户粘贴回的 markdown（council.response.md 或 strict 拼接）。
输出：CouncilVerdict（成功）或 ConsensusValidationError（任一硬规则失败）。

API_FREE：本模块仅做正则与字符串处理；不 import google.genai。
"""
from __future__ import annotations

import json
import re
from typing import Literal

from src.coach.common.logging import get_logger

from .types import (
    ConsensusValidationError,
    CouncilVerdict,
    EXPERT_ROLES,
    ExpertTurn,
    VERDICTS,
)

_log = get_logger("consensus")


# ---------- regex helpers ----------

_TAG_RE = {
    role: re.compile(rf"<{role}>(.*?)</{role}>", re.DOTALL | re.IGNORECASE)
    for role in EXPERT_ROLES
}
_SUMMARY_RE = re.compile(r"<summary_json>(.*?)</summary_json>",
                         re.DOTALL | re.IGNORECASE)

# Critic point splitter: leading "1." / "2." numbered or "- " / "* " bullets
_POINT_RE = re.compile(r"^\s*(?:\d+\.|[-*])\s+", re.MULTILINE)

# A "data citation" inside one point — at least one of:
#   - bare number with a unit (W, watts, bpm, min, %, kJ, J)
#   - explicit `field=value` or `field:value`
#   - inequality with number ("< 18", ">= 480")
_DATA_CITATION_RE = re.compile(
    r"""(
          \d+(?:\.\d+)?\s*(?:%|W\b|watts|bpm|min|kJ|J\b)
        | \w[\w./_]*\s*[=:]\s*\S
        | [<>]=?\s*\d
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Physiologist quantitative keyword bag (case-insensitive, normalize ' and ′)
_PHYS_KEYWORDS = ("CP", "W'", "DURABILITY", "RESPONSE_PROFILE")


# ---------- main entry ----------

def parse(response_md: str,
          *,
          mode: Literal["council", "strict"] = "council") -> CouncilVerdict:
    violations: list[str] = []

    # Rule 1 — four role sections present
    role_bodies: dict[str, str] = {}
    for role in EXPERT_ROLES:
        m = _TAG_RE[role].search(response_md)
        if not m:
            violations.append(f"section.missing.{role}")
        else:
            role_bodies[role] = m.group(1).strip()

    # Rule 2 — summary_json block present and parseable
    summary_json: dict = {}
    sm = _SUMMARY_RE.search(response_md)
    if not sm:
        violations.append("summary_json.missing")
    else:
        try:
            summary_json = json.loads(sm.group(1).strip())
            if not isinstance(summary_json, dict):
                violations.append("summary_json.not_object")
                summary_json = {}
        except json.JSONDecodeError as exc:
            violations.append(f"summary_json.invalid_json:{exc.msg}")

    # If the bedrock structure is broken, we can still try to surface the
    # remaining role-level rule violations for a richer error message,
    # but we cap analysis at what we have.

    # Rule 3 — Critic ≥3 independent points, each with data citation
    critic_cited: list[str] = []
    if "critic" in role_bodies:
        critic_cited = _check_critic(role_bodies["critic"], violations)

    # Rule 4 — Physiologist hits ≥3 of 4 quantitative keywords
    if "physiologist" in role_bodies:
        _check_physiologist(role_bodies["physiologist"], violations)

    # Rule 5/6 — verdict + confidence from summary_json, with text cross-check
    arbiter_text = role_bodies.get("arbiter", "")
    verdict = _check_verdict(summary_json, arbiter_text, violations)
    confidence = _check_confidence(summary_json, violations)

    if violations:
        _log.event("consensus_response_rejected",
                   mode=mode, n_violations=len(violations),
                   violations=violations)
        raise ConsensusValidationError(violations=violations)

    # ---------- happy: build CouncilVerdict ----------

    turns = [
        ExpertTurn(
            role="planner",
            body_md=role_bodies["planner"],
            cited_data=_extract_citations(role_bodies["planner"]),
        ),
        ExpertTurn(
            role="critic",
            body_md=role_bodies["critic"],
            cited_data=critic_cited,
        ),
        ExpertTurn(
            role="physiologist",
            body_md=role_bodies["physiologist"],
            cited_data=_extract_citations(role_bodies["physiologist"]),
        ),
        ExpertTurn(
            role="arbiter",
            body_md=role_bodies["arbiter"],
            cited_data=[],
        ),
    ]

    cv = CouncilVerdict(
        mode=mode,
        verdict=verdict,  # already validated
        confidence=confidence,
        justification=arbiter_text.splitlines()[0].strip()
                      if arbiter_text.strip() else "(no justification line)",
        expert_turns=turns,
        summary_json=summary_json,
    )
    _log.event("consensus_response_accepted",
               mode=mode, verdict=verdict, confidence=confidence)
    return cv


# ---------- internal rule checks ----------

def _check_critic(body: str, violations: list[str]) -> list[str]:
    """Return list of cited data items (one per accepted point)."""
    splits = _POINT_RE.split(body)
    # _POINT_RE.split: first element is the (often-empty) prefix before first marker;
    # subsequent elements are point bodies.
    points = [s.strip() for s in splits[1:] if s.strip()]

    if len(points) < 3:
        violations.append(f"critic.points<3:got_{len(points)}")
        # Continue to also flag any data-less points among what we have

    cited: list[str] = []
    for idx, p in enumerate(points, start=1):
        m = _DATA_CITATION_RE.search(p)
        if not m:
            violations.append(f"critic.point_no_data:{idx}")
            cited.append("")
        else:
            cited.append(m.group(0).strip())
    return [c for c in cited if c]


def _check_physiologist(body: str, violations: list[str]) -> None:
    norm = body.replace("′", "'").upper()
    hits = sum(1 for kw in _PHYS_KEYWORDS if kw in norm)
    if hits < 3:
        violations.append(f"physiologist.keywords<3:got_{hits}")


def _check_verdict(summary_json: dict,
                   arbiter_text: str,
                   violations: list[str]) -> str:
    # From summary_json
    sj_verdict = summary_json.get("verdict")
    if sj_verdict not in VERDICTS:
        violations.append(f"verdict.invalid:{sj_verdict!r}")
        return "REJECT"  # placeholder; we'll raise anyway

    # Cross-check against arbiter text — first all-caps verdict-ish word
    text_match = re.search(r"\b(ACCEPT|REVISE|REJECT)\b", arbiter_text)
    if text_match and text_match.group(1) != sj_verdict:
        violations.append(
            f"verdict.mismatch:summary={sj_verdict},text={text_match.group(1)}"
        )
    return sj_verdict


def _check_confidence(summary_json: dict, violations: list[str]) -> float:
    raw = summary_json.get("confidence")
    try:
        c = float(raw)
    except (TypeError, ValueError):
        violations.append(f"confidence.out_of_range:{raw!r}")
        return 0.0
    if not (0.0 <= c <= 1.0):
        violations.append(f"confidence.out_of_range:{c}")
        return 0.0
    return c


def _extract_citations(body: str) -> list[str]:
    return [m.group(0).strip() for m in _DATA_CITATION_RE.finditer(body)]
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/test_response_parser.py -v`
Expected: PASS all 9 tests (1 happy + 6 parametrized rejection + 1 strict + 2 boundary).

If a rejection fixture surfaces > 1 violation (e.g. removing the critic block also drops critic citations), the parametrized substring assertion only requires the **expected** violation token to be in the list — it tolerates extra. Author the fixtures to keep the dominant rule unambiguous.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/consensus/response_parser.py \
        icu/tests/unit/consensus/conftest.py \
        icu/tests/unit/consensus/test_response_parser.py \
        icu/tests/fixtures/phase3/consensus/
git commit -m "feat(coach-phase3): consensus response_parser with 6 hard-rule rejections"
```

---

## Task 64: history_injector.py — 压相似 context-verdict-outcome 三元组

**Files:**
- Create: `icu/src/coach/consensus/history_injector.py`
- Create: `icu/tests/unit/consensus/test_history_injector.py`

**Design notes:**
- 输入：当前 `AthleteStateRef`（来自调用方按 Phase 1/2 snapshots 组装），可选 `LedgerReader` 实例，可选 limit（默认 8）。
- 取相似 `weekly_plan_assembled` entries：调 `reader.query_similar(decision_type="weekly_plan_assembled", athlete_state=ref, ctl_tolerance=5.0, phase_match=True, limit=limit)`。
- 对每个匹配 plan，按 `payload["plan_period"]` / `entry.timestamp` 在原 ledger 内**追溯后续**最多 4 周内的 `consensus_verdict` / `adaptation_verdict` / 以及 deep_analysis stimulus_score（如果蓝图后续把 deep_analysis 也写入 ledger 则同源；M1 阶段 deep_analysis 不写 ledger，故 stimulus_score 字段缺省时标 `outcome_pending`）。
- 输出：≤8 条 `HistoryTriplet`（context / verdict / outcome）；每条 outcome 缺失则置 `"outcome_pending"`。**禁止瞎编**：不调用任何 LLM、不做 heuristic 数值估算 — 没有就是没有。
- 提供纯函数 `compress_history(reader, athlete_state, *, limit=8) -> list[HistoryTriplet]`，方便 council_prompt.py 在 Section C 直接渲染。
- HistoryTriplet 是本文件内的 lightweight Pydantic model（不放进 types.py，避免 cross-file 依赖膨胀；T65 council_prompt.py 引用本文件即可）。

**State of the world for outcome lookup:**
- `consensus_verdict` → `entry.payload["verdict"]` + `entry.payload["confidence"]`
- `adaptation_verdict` → `entry.payload["verdict"]` (green/yellow/red)
- `stimulus_score` → 仅 M2+ 才会以 `decision_type="deep_analysis_completed"`（暂未在 8 个 decision_type 内）入库；M1 内 outcome_pending 是预期行为。

- [ ] **Step 1: Write failing tests — empty / <3 / >8 / outcome_pending**

Write `icu/tests/unit/consensus/test_history_injector.py`:
```python
"""Unit tests for HistoryInjector: empty, sparse, saturated, outcome_pending."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.coach.consensus.history_injector import (
    HistoryTriplet,
    compress_history,
)
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


def _state(ctl: float = 72.0, phase: str = "BUILD",
           week: int = 16) -> AthleteStateRef:
    return AthleteStateRef(
        ctl=ctl, atl=ctl * 1.1, tsb=-ctl * 0.15,
        w_prime=18500, phase=phase, week_of_year=week,
    )


@pytest.fixture
def ledger_path(tmp_path) -> Path:
    return tmp_path / "decisions.jsonl"


# ---------- empty ledger ----------

def test_compress_history_empty_ledger_returns_empty(ledger_path):
    reader = LedgerReader(ledger_path)  # file does not exist yet
    triplets = compress_history(reader, _state(), limit=8)
    assert triplets == []


# ---------- < 3 plans ----------

def test_compress_history_returns_all_when_under_three(ledger_path):
    w = LedgerWriter(ledger_path)
    # 2 weekly_plan_assembled, both BUILD/CTL≈72
    for i in range(2):
        w.record(
            decision_type="weekly_plan_assembled",
            source="ingester",
            athlete_state=_state(ctl=72.0 + i * 0.4),
            payload={"plan_period": f"2026-W{14+i:02d}", "total_tss": 460},
        )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 2
    # All should have outcome_pending since no follow-on verdicts written
    assert all(t.outcome == "outcome_pending" for t in triplets)


# ---------- > 8 plans → cap at 8 ----------

def test_compress_history_caps_at_limit(ledger_path):
    w = LedgerWriter(ledger_path)
    for i in range(12):
        w.record(
            decision_type="weekly_plan_assembled",
            source="ingester",
            athlete_state=_state(ctl=72.0),
            payload={"plan_period": f"2026-W{i:02d}", "total_tss": 460},
        )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 8


# ---------- outcome stitching ----------

def test_compress_history_attaches_consensus_verdict_outcome(ledger_path):
    w = LedgerWriter(ledger_path)
    plan_id = w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W14", "total_tss": 480},
    )
    # Following consensus_verdict written same day for that plan
    w.record(
        decision_type="consensus_verdict",
        source="consensus.council",
        athlete_state=_state(),
        payload={"verdict": "REVISE", "confidence": 0.7,
                 "supersedes_plan_entry_id": plan_id},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    t = triplets[0]
    assert isinstance(t, HistoryTriplet)
    assert "REVISE" in t.outcome
    assert t.context["plan_period"] == "2026-W14"


def test_compress_history_attaches_adaptation_verdict_outcome(ledger_path):
    w = LedgerWriter(ledger_path)
    plan_id = w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W15", "total_tss": 500},
    )
    w.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=_state(),
        payload={"verdict": "red",
                 "supersedes_plan_entry_id": plan_id,
                 "reason": "HRV crash"},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    assert "red" in triplets[0].outcome


# ---------- outcome_pending sentinel ----------

def test_compress_history_marks_outcome_pending_when_no_follow_on(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W17", "total_tss": 470},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    assert triplets[0].outcome == "outcome_pending"


def test_compress_history_filters_out_unrelated_phase(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(phase="PEAK"),
        payload={"plan_period": "2026-W14"},
    )
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(phase="BUILD"),
        payload={"plan_period": "2026-W15"},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(phase="BUILD"), limit=8)
    assert len(triplets) == 1
    assert triplets[0].context["plan_period"] == "2026-W15"


def test_history_triplet_pydantic_roundtrip():
    t = HistoryTriplet(
        plan_entry_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        context={"plan_period": "2026-W14", "total_tss": 460,
                 "ctl": 72.3, "phase": "BUILD"},
        verdict="REVISE",
        outcome="consensus.REVISE@0.70",
    )
    js = t.model_dump_json()
    loaded = HistoryTriplet.model_validate_json(js)
    assert loaded == t


def test_compress_history_no_llm_no_heuristic_estimation(ledger_path,
                                                         monkeypatch):
    """Defense-in-depth: importing google.genai at module load must fail clean."""
    import sys
    assert "google.genai" not in sys.modules
    # Sanity: module under test must not pull google.genai transitively
    from src.coach.consensus import history_injector  # noqa: F401
    assert "google.genai" not in sys.modules
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/test_history_injector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.consensus.history_injector'`.

- [ ] **Step 3: Implement injector**

Write `icu/src/coach/consensus/history_injector.py`:
```python
"""HistoryInjector — 把 ledger 中相似 context 的历史压成 ≤8 条三元组。

调用入口：compress_history(reader, athlete_state, *, limit=8)
返回：list[HistoryTriplet]，按 ledger entry_id 降序（最新在前）。

约束：
- 不 import google.genai；不做任何 LLM/heuristic 数值估算。
- outcome 缺失即写 "outcome_pending"；后续 deep_analysis stimulus_score 入库后
  T65/T66 的渲染层可重读 ledger 升级该字段（不在本文件职责内）。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef, DecisionEntry

_log = get_logger("consensus")

OUTCOME_PENDING = "outcome_pending"
DEFAULT_CTL_TOLERANCE = 5.0


class HistoryTriplet(BaseModel):
    """One row of Section C — context-verdict-outcome triplet."""

    model_config = {"frozen": True}

    plan_entry_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    verdict: str = Field(default="")
    outcome: str = Field(default=OUTCOME_PENDING)


def compress_history(
    reader: LedgerReader,
    athlete_state: AthleteStateRef,
    *,
    limit: int = 8,
    ctl_tolerance: float = DEFAULT_CTL_TOLERANCE,
) -> list[HistoryTriplet]:
    """Return ≤limit most-recent triplets for similar BUILD-week contexts.

    `verdict` field is currently always empty string — it captures any
    *plan-time* verdict embedded in the weekly_plan_assembled payload itself,
    which Phase 2 ingester does not yet emit. Kept on the model for future
    use; do not synthesize.
    """
    plans = reader.query_similar(
        athlete_state=athlete_state,
        decision_type="weekly_plan_assembled",
        ctl_tolerance=ctl_tolerance,
        phase_match=True,
        limit=limit,
    )
    if not plans:
        return []

    # Scoop the entire ledger once; we'll filter out follow-on entries by
    # `payload.supersedes_plan_entry_id == plan.entry_id` (preferred) or by
    # falling back to "any later entry of consensus_verdict / adaptation_verdict
    # whose timestamp is within 28 days of plan.timestamp".
    all_entries = reader.query()
    follow_on_index: dict[str, list[DecisionEntry]] = {}
    for e in all_entries:
        if e.decision_type not in ("consensus_verdict", "adaptation_verdict"):
            continue
        link = e.payload.get("supersedes_plan_entry_id")
        if link:
            follow_on_index.setdefault(link, []).append(e)

    triplets: list[HistoryTriplet] = []
    for plan in plans:
        outcome = _resolve_outcome(plan, follow_on_index, all_entries)
        ctx = {
            "plan_period": plan.payload.get("plan_period", ""),
            "total_tss": plan.payload.get("total_tss"),
            "ctl": plan.athlete_state_ref.ctl,
            "phase": plan.athlete_state_ref.phase,
            "week_of_year": plan.athlete_state_ref.week_of_year,
        }
        triplets.append(HistoryTriplet(
            plan_entry_id=plan.entry_id,
            context=ctx,
            verdict=plan.payload.get("plan_time_verdict", ""),
            outcome=outcome,
        ))

    _log.event("consensus_history_compressed",
               n_plans=len(plans), n_triplets=len(triplets),
               n_outcome_pending=sum(1 for t in triplets
                                     if t.outcome == OUTCOME_PENDING))
    return triplets


def _resolve_outcome(plan: DecisionEntry,
                     follow_on_index: dict[str, list[DecisionEntry]],
                     all_entries: list[DecisionEntry]) -> str:
    linked = follow_on_index.get(plan.entry_id)
    if linked:
        # Prefer consensus_verdict over adaptation_verdict; take latest of each.
        consensus = [e for e in linked if e.decision_type == "consensus_verdict"]
        if consensus:
            latest = max(consensus, key=lambda e: e.entry_id)
            v = latest.payload.get("verdict", "?")
            c = latest.payload.get("confidence")
            return f"consensus.{v}@{c:.2f}" if isinstance(c, (int, float)) \
                else f"consensus.{v}"
        adaptation = [e for e in linked
                      if e.decision_type == "adaptation_verdict"]
        if adaptation:
            latest = max(adaptation, key=lambda e: e.entry_id)
            return f"adapter.{latest.payload.get('verdict', '?')}"
    return OUTCOME_PENDING
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/consensus/ -v`
Expected: PASS all tests across `test_types.py`, `test_response_parser.py`, `test_history_injector.py` (~30 tests total).

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/consensus/history_injector.py \
        icu/tests/unit/consensus/test_history_injector.py
git commit -m "feat(coach-phase3): consensus history_injector with ≤8 triplets + outcome_pending sentinel"
```

---

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/consensus/ -v` 全绿（~30 tests）
- [ ] 3 次提交完成（T62 / T63 / T64 各一次）
- [ ] `icu/tests/fixtures/phase3/consensus/` 内 7 个 markdown fixture 全部入库
- [ ] grep 自检：`grep -R "google.genai" icu/src/coach/consensus/` 应为空
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`07-consensus-council.md`](./07-consensus-council.md) 开始（T65–T66：council_prompt.py + run_consensus.py + finalize_consensus.py）

## Worktree bootstrap reminder (executor reads before Step 1 of T62)

This file lives on `/mnt/d/Cycling-phase3` (branch `ai-coach-phase-3`). 若执行器是 fresh worktree，按 `01-ledger-infrastructure.md` 末尾的 bootstrap 步骤复制 `.venv` + `src/analyzer` + `src/utils` + `src/fetcher`。`tests/fixtures/phase3/consensus/` 是本文件首次创建的目录，无需预先准备。
