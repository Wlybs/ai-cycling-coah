# Phase 3 — Consensus council prompt + CLI (Tasks T65–T66)

> **Path note:** The plan files for Phase 3 live at
> `/mnt/d/Cycling-phase3/docs/superpowers/plans/phase-3/` (NOT under `icu/docs/`).
> Source code, tests and scripts referenced below live under
> `/mnt/d/Cycling-phase3/icu/`. Code-block paths are written **relative to**
> `/mnt/d/Cycling-phase3/icu/` (so `src/coach/consensus/...` means
> `/mnt/d/Cycling-phase3/icu/src/coach/consensus/...`).

## Mission

Build the **council prompt assembler** (T65) and the **finalize ledger**
CLI (T66) on top of the FROZEN File 06 consensus infrastructure
(`types.py`, `response_parser.py`, `history_injector.py`).

After this file:

- A user can run `scripts/run_consensus.py --verdict-request ... --history ...
  --out council.prompt.md` to materialise a 4-section markdown prompt that
  embeds (a) the current weekly plan + athlete state + injected ledger history,
  (b) optional **UNDER-DOSED** trigger annotations from the 6-item
  Critic checklist, (c) hard rules + output schema for the 4 expert roles.
- The user pastes that prompt into Gemini CLI / Claude Code, saves the
  response as `council.response.md`, and runs
  `scripts/finalize_consensus.py --response ./council.response.md
  --ledger coach_memory/ledger/decisions.jsonl` (default = dry-run print).
  With `--confirm`, the response is parsed via File 06's
  `consensus.response_parser.parse`, validated against the 6 hard rules, and
  appended to the ledger as a `consensus_verdict` entry — atomic, with
  per-content idempotency.

API_FREE remains a hard invariant: **neither script imports any LLM SDK**
nor opens any network socket. They only do file IO, regex, JSON, and
ledger writes.

## Out of scope

- `strict_prompt.py` (4-step strict-mode prompt assembly) — File 08 (T67–T70).
- Phase 1/2 internals — fully off-limits (see 00-index.md "Out of scope").
- Adapter (Files 03–05) and Ledger (Files 01–02) modules are FROZEN; this
  file imports them but does not modify them.
- Updating `scripts/sync_data.py` to auto-trigger consensus — File 09 (T71+).
- Any Pydantic / Phase-2 model changes.

## Inputs (read-only contracts)

These files exist before you start; touching them is a hard violation.

| Path | What you use from it |
|---|---|
| `src/coach/consensus/types.py` | `CouncilVerdict`, `ExpertTurn`, `ConsensusValidationError`, `EXPERT_ROLES`, `VERDICTS`, `MODES` literals |
| `src/coach/consensus/response_parser.py` | `parse(response_md, *, mode="council")` — raises `ConsensusValidationError(violations: list[str])` on any of 6 hard-rule failures |
| `src/coach/consensus/history_injector.py` | `compress_history(reader, athlete_state, *, limit=8, ctl_tolerance=5.0)` → `list[HistoryTriplet]`; constant `OUTCOME_PENDING = "outcome_pending"` |
| `src/coach/ledger/types.py` | `DecisionEntry`, `AthleteStateRef`, `DecisionType`, `generate_ulid`, `is_valid_ulid`. `"consensus_verdict"` is in the whitelist (verified 2026-04-27). |
| `src/coach/ledger/writer.py` | `LedgerWriter(path).record(decision_type=..., source=..., athlete_state=..., payload=..., evidence_refs=..., confidence=..., superseded_by=...)` returns the ULID `entry_id`. |
| `src/coach/ledger/reader.py` | `LedgerReader(path)` with `.query(...)`, `.query_similar(...)` |
| `src/coach/common/logging.py` | `get_logger(module: str) -> JSONLLogger` with `.event(action, **extra)`. |

## Outputs (what gets created)

```
icu/src/coach/consensus/
├── council_prompt.py      ← T65.1+T65.2+T65.3 (NEW)
└── (nothing else changed; File 06 modules are FROZEN)

icu/scripts/
├── run_consensus.py       ← T65.4 (NEW)
└── finalize_consensus.py  ← T66.1+T66.2+T66.3 (NEW)

icu/tests/unit/consensus/
└── test_council_prompt.py ← T65.1+T65.2+T65.3 (NEW)

icu/tests/unit/scripts/
├── test_run_consensus.py       ← T65.4 (NEW)
└── test_finalize_consensus.py  ← T66.1+T66.2+T66.3 (NEW)

icu/tests/fixtures/phase3/consensus/
└── (REUSE existing fixtures created by File 06; this file adds
   `council_response_happy.md` if not already present — see T66.2)
```

## Decision-type contract

Hardcoded throughout T66:

- `decision_type = "consensus_verdict"`
- `source = "consensus.council"` (lowercase, dot-separated; matches existing
  ledger convention from File 06's history_injector outcome-resolver).
- `payload = verdict.model_dump()` — i.e. the full `CouncilVerdict` Pydantic
  dump, no second-pass packing. This includes `mode`, `verdict`,
  `confidence`, `justification`, `expert_turns` (list of dicts), and
  `summary_json` (dict).
- `evidence_refs = ["consensus/<timestamp>/council.response.md"]` (caller
  passes the response path; finalize stores it as a single-element list so
  the ledger entry can be reproduced.)
- `confidence = verdict.confidence` (the float from the parser, already
  validated to `[0.0, 1.0]`).
- `superseded_by = None` (consensus verdicts never supersede in this CLI;
  corrections are a follow-up entry, out of scope here).

## Touch list (do not exceed)

```
icu/src/coach/consensus/council_prompt.py     (CREATE)
icu/scripts/run_consensus.py                  (CREATE)
icu/scripts/finalize_consensus.py             (CREATE)
icu/tests/unit/consensus/test_council_prompt.py     (CREATE)
icu/tests/unit/scripts/test_run_consensus.py        (CREATE)
icu/tests/unit/scripts/test_finalize_consensus.py   (CREATE)
icu/tests/fixtures/phase3/consensus/council_response_happy.md   (CREATE if absent)
```

Anything else (especially `src/coach/consensus/types.py`, `response_parser.py`,
`history_injector.py`, anything under `src/coach/ledger/`, anything under
`src/coach/adapter/`, `src/coach/deep_analyzer/`) is OFF LIMITS.

## Pre-flight Pydantic+IO checklist

Paste this checklist into the implementer subagent brief verbatim. Each item
is a fail-fast quality gate: if any item is unverifiable in your code,
**stop and re-read** the relevant file before continuing.

1. **Frozen Pydantic models.** Every Pydantic model added in this file uses
   `model_config = {"frozen": True}`. New `VerdictRequest` model in T65.1 is
   frozen. `HistoryTriplet` (already frozen in `history_injector.py`) — do not
   re-define it.
2. **Explicit field types.** Every `Field(...)` has a fully-spelled type
   annotation; never bare `Any`. If you genuinely need `Any`, annotate
   `dict[str, Any]` and document why.
3. **`Optional[T]` is forbidden.** Use `T | None` and require an explicit
   `default=None` on the `Field(...)`. Never use `from typing import Optional`.
4. **UTF-8 explicit on every file IO.** `path.read_text(encoding="utf-8")`,
   `path.write_text(text, encoding="utf-8")`, `open(..., encoding="utf-8")`.
   Never rely on platform default.
5. **`pathlib.Path` over `os.path`.** `from pathlib import Path`. The only
   `os` calls allowed are inside the FROZEN `LedgerWriter` (which we don't
   touch) — your new modules use `Path` everywhere.
6. **Stable JSON dumps.** `json.dumps(obj, indent=2, sort_keys=True,
   ensure_ascii=False)` for any human-readable JSON output. For ledger
   entries we delegate to `LedgerWriter` (which uses `model_dump_json()`,
   already stable).
7. **Timezone-aware timestamps.** `datetime.now(timezone.utc)`. Never use
   `datetime.utcnow()` (it returns naive). Pydantic field with
   `_require_utc` validator will reject naive datetimes — this is enforced
   transitively when we hand off to `LedgerWriter.record`.
8. **Immutable defaults.** `Field(default_factory=list)` /
   `Field(default_factory=dict)` — never `default=[]` / `default={}`
   (mutable shared instance trap).
9. **Explicit exit codes in CLIs.** `0` = success (including dry-run), `2` =
   user/input error (missing file, malformed JSON, parser rejection), `3` =
   internal/IO error during ledger write. Never let an unhandled exception
   bubble (catch at `main()` boundary; print to stderr; return code).

# Task 65 — Council prompt builder + run_consensus CLI

T65 builds the assembler that takes a `VerdictRequest` (the input "what is
the council reviewing?" bundle) and returns a multi-section markdown prompt
the user pastes into Gemini. It also wires the optional
`HistoryInjector.compress_history` output into Section C, and applies the
6 UNDER-DOSED trigger detector when a plan is dosed too softly. Finally
T65.4 packages the assembler in a CLI script.

T65 does NOT call any LLM. The CLI's only side-effect is writing one
markdown file.

T65 splits into 4 RED → GREEN cycles:

- **T65.1** — `VerdictRequest` Pydantic model + `build_council_prompt`
  base 4-section template
- **T65.2** — `detect_under_dosed_triggers(plan, athlete_state)` function:
  6 trigger labels matching blueprint §4.6 / §4.7 (Critic role's
  6-item UNDER-DOSED checklist)
- **T65.3** — wire the optional `history` argument: when non-empty, call
  `inject_history_triplets` (re-export of `compress_history` semantics) and
  embed in Section C; preserve `outcome_pending` sentinel verbatim.
- **T65.4** — `scripts/run_consensus.py` CLI

## T65.1 — VerdictRequest model + 4-section template

**Goal.** Stand up `src/coach/consensus/council_prompt.py` with a frozen
Pydantic `VerdictRequest` model (defined here because File 06's `types.py`
deliberately omitted it — see naming-convention "all input wrappers live in
the module that owns the assembler"), and a `build_council_prompt(request,
history=None)` function that returns a markdown string with **all four
required sections** in the exact order Section A → Section B → Section C →
Section D, lifted verbatim from blueprint §4.6.

The four section headers (lifted from blueprint §4.6, locked):

1. **Section A — Roles & Hard Rules** (planner / critic / physiologist / arbiter)
2. **Section B — Input Data** (WeeklyPlan JSON + Periodization snapshot
   summary + physiology summary + 28-day wellness trend)
3. **Section C — Active Ledger History** (3–8 context-verdict-outcome
   triplets, may be empty)
4. **Section D — Output Schema** (4 role tag blocks + `<summary_json>` JSON)

T65.1 only delivers Sections A, B (with raw inputs echoed back), and D — and
a stub Section C that says `(no historical context)` when `history` is
None / empty. T65.3 wires the actual triplets into C.

### - [ ] **Step 1: Write RED test**

Create `icu/tests/unit/consensus/test_council_prompt.py`:

```python
"""Unit tests for src.coach.consensus.council_prompt."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.coach.consensus.council_prompt import (
    VerdictRequest,
    build_council_prompt,
    detect_under_dosed_triggers,
)
from src.coach.ledger.types import AthleteStateRef


# ---------- helpers ----------

def _state(**over) -> AthleteStateRef:
    base = dict(ctl=70.0, atl=68.0, tsb=2.0, w_prime=14_500,
                phase="BUILD", week_of_year=17)
    base.update(over)
    return AthleteStateRef(**base)


def _plan(**over) -> dict:
    """Minimal WeeklyPlan-ish payload for prompt assembly tests."""
    base = {
        "week_start": "2026-04-20",
        "week_end": "2026-04-26",
        "focus_theme": "BUILD",
        "weekly_tss_target": 525,
        "days": [
            {"day_of_week": "Mon", "training_type": "Recovery",
             "name": "Easy Z2", "duration_min": 60, "target_tss": 45,
             "power_range_w": "120-160W", "tier": "EASY"},
            {"day_of_week": "Tue", "training_type": "VO2max",
             "name": "5x4min @CP", "duration_min": 75, "target_tss": 90,
             "power_range_w": "260-280W", "tier": "HIGH"},
            {"day_of_week": "Wed", "training_type": "Endurance",
             "name": "Z2 base", "duration_min": 90, "target_tss": 70,
             "power_range_w": "150-180W", "tier": "MID"},
            {"day_of_week": "Thu", "training_type": "Rest",
             "name": "Rest", "duration_min": 0, "target_tss": 0,
             "power_range_w": None, "tier": "REST"},
            {"day_of_week": "Fri", "training_type": "Threshold",
             "name": "2x20min", "duration_min": 80, "target_tss": 110,
             "power_range_w": "240-260W", "tier": "HIGH"},
            {"day_of_week": "Sat", "training_type": "Endurance",
             "name": "Long Z2", "duration_min": 180, "target_tss": 140,
             "power_range_w": "150-180W", "tier": "MID"},
            {"day_of_week": "Sun", "training_type": "Recovery",
             "name": "Easy spin", "duration_min": 60, "target_tss": 40,
             "power_range_w": "120-150W", "tier": "EASY"},
        ],
    }
    base.update(over)
    return base


def _physiology() -> dict:
    return {
        "cp_w": 285,
        "w_prime_j": 14_500,
        "durability_index": 0.74,
        "response_profile": {
            "types": {
                "vo2max": {"tolerance_class": "high"},
                "threshold": {"tolerance_class": "high"},
            }
        },
        "knee_flag": "OK",
    }


def _wellness_trend() -> list[dict]:
    return [
        {"date": "2026-04-19", "hrv": 62, "rhr": 51, "sleep_h": 7.6},
        {"date": "2026-04-20", "hrv": 65, "rhr": 50, "sleep_h": 7.4},
    ]


def _request(**over) -> "VerdictRequest":
    base = dict(
        plan=_plan(),
        athlete_state=_state(),
        physiology=_physiology(),
        wellness_trend=_wellness_trend(),
        periodization_summary={"phase": "BUILD",
                               "weekly_tss_target": 525,
                               "weeks_to_race": 8},
    )
    base.update(over)
    return VerdictRequest(**base)


# ---------- VerdictRequest schema tests ----------

class TestVerdictRequest:

    def test_required_fields_round_trip(self):
        r = _request()
        # Frozen — assignment must raise.
        with pytest.raises(ValidationError):
            r.plan = {}  # type: ignore[misc]

    def test_missing_plan_raises(self):
        with pytest.raises(ValidationError):
            VerdictRequest(  # type: ignore[call-arg]
                athlete_state=_state(),
                physiology=_physiology(),
                wellness_trend=[],
                periodization_summary={},
            )

    def test_missing_athlete_state_raises(self):
        with pytest.raises(ValidationError):
            VerdictRequest(  # type: ignore[call-arg]
                plan=_plan(),
                physiology=_physiology(),
                wellness_trend=[],
                periodization_summary={},
            )

    def test_wellness_trend_default_empty(self):
        # wellness_trend is optional with default_factory=list
        r = VerdictRequest(
            plan=_plan(),
            athlete_state=_state(),
            physiology=_physiology(),
            periodization_summary={},
        )
        assert r.wellness_trend == []


# ---------- build_council_prompt structural tests ----------

class TestBuildCouncilPromptStructure:

    def test_returns_str(self):
        out = build_council_prompt(_request())
        assert isinstance(out, str)
        assert len(out) > 100

    def test_contains_four_sections_in_order(self):
        out = build_council_prompt(_request())
        idx_a = out.find("## Section A")
        idx_b = out.find("## Section B")
        idx_c = out.find("## Section C")
        idx_d = out.find("## Section D")
        assert idx_a >= 0, "Section A header missing"
        assert idx_b > idx_a, "Section B must follow A"
        assert idx_c > idx_b, "Section C must follow B"
        assert idx_d > idx_c, "Section D must follow C"

    def test_section_a_lists_all_four_roles(self):
        out = build_council_prompt(_request())
        for role in ("Planner", "Critic", "Physiologist", "Arbiter"):
            assert role in out, f"role {role!r} missing from Section A"

    def test_section_a_mentions_under_dosed_check(self):
        out = build_council_prompt(_request())
        # Critic mandate must reference UNDER-DOSED 6-item check (label only;
        # actual triggers fire conditionally — see T65.2).
        assert "UNDER-DOSED" in out

    def test_section_b_includes_plan_summary(self):
        out = build_council_prompt(_request())
        assert "weekly_tss_target" in out or "Weekly TSS" in out
        # Each day-of-week label appears at least once in the plan dump.
        for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            assert d in out, f"day {d!r} missing from Section B plan dump"

    def test_section_b_includes_physiology(self):
        out = build_council_prompt(_request())
        assert "cp_w" in out or "CP" in out
        assert "w_prime" in out or "W'" in out

    def test_section_b_includes_wellness_trend(self):
        out = build_council_prompt(_request())
        assert "hrv" in out.lower() or "HRV" in out

    def test_section_c_empty_when_no_history(self):
        out = build_council_prompt(_request(), history=None)
        # Sentinel string the parser DOES NOT treat as a triplet
        assert "(no historical context)" in out

    def test_section_c_empty_for_empty_list(self):
        out = build_council_prompt(_request(), history=[])
        assert "(no historical context)" in out

    def test_section_d_specifies_summary_json_block(self):
        out = build_council_prompt(_request())
        assert "<summary_json>" in out
        # Schema must reference the three accept tags.
        assert "ACCEPT" in out and "REVISE" in out and "REJECT" in out

    def test_section_d_specifies_role_tag_blocks(self):
        out = build_council_prompt(_request())
        # Output schema reference must show <planner> / <critic> /
        # <physiologist> / <arbiter> tags so the LLM emits parseable bodies.
        for tag in ("<planner>", "<critic>",
                    "<physiologist>", "<arbiter>"):
            assert tag in out, f"output-schema tag {tag!r} missing"


# ---------- detect_under_dosed_triggers stub for T65.1 ----------

class TestDetectUnderDosedStub:
    """detect_under_dosed_triggers exists and returns []. T65.2 fills it."""

    def test_function_exists(self):
        assert callable(detect_under_dosed_triggers)

    def test_returns_list(self):
        out = detect_under_dosed_triggers(_plan(), _state().model_dump())
        assert isinstance(out, list)
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py -v
```

Expected error fragment:

```
ModuleNotFoundError: No module named 'src.coach.consensus.council_prompt'
```

### - [ ] **Step 3: Minimal implementation**

Create `icu/src/coach/consensus/council_prompt.py`:

```python
"""Council prompt assembler — 4 段 markdown 拼装 + UNDER-DOSED 触发器.

输入：VerdictRequest（plan + athlete_state + physiology + wellness_trend +
periodization_summary）+ 可选 history triplets。

输出：纯 markdown 字符串。本模块不做 LLM call、不做网络请求；调用方
（scripts/run_consensus.py）负责落盘并提示用户粘贴到 Gemini。

API_FREE：仅做字符串拼装与字典查找。不 import google.genai。
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from src.coach.common.logging import get_logger
from src.coach.consensus.history_injector import (
    OUTCOME_PENDING,
    HistoryTriplet,
)
from src.coach.ledger.types import AthleteStateRef

_log = get_logger("consensus")


# ---------- VerdictRequest ----------

class VerdictRequest(BaseModel):
    """Inputs the council needs to produce a verdict.

    `plan` is the WeeklyPlan dict (Phase 2 produces this; we accept dict to
    avoid coupling to Phase 2 types). `physiology` and `periodization_summary`
    are also dicts for the same reason — Phase 1/2 schemas must remain
    untouched.
    """

    model_config = {"frozen": True}

    plan: dict[str, Any]
    athlete_state: AthleteStateRef
    physiology: dict[str, Any]
    wellness_trend: list[dict[str, Any]] = Field(default_factory=list)
    periodization_summary: dict[str, Any] = Field(default_factory=dict)


# ---------- public entry ----------

def build_council_prompt(
    request: VerdictRequest,
    history: list[HistoryTriplet] | None = None,
) -> str:
    """Return a 4-section markdown prompt body.

    `history` is optional. When None or empty, Section C reads
    `(no historical context)`. T65.3 wires real triplets in.
    `detect_under_dosed_triggers` is invoked here so the prompt can hint
    the Critic at any conditions it MUST scrutinise.
    """
    triggers = detect_under_dosed_triggers(
        request.plan,
        request.athlete_state.model_dump(),
    )
    parts = [
        _section_a(triggers),
        _section_b(request),
        _section_c(history or []),
        _section_d(),
    ]
    body = "\n\n".join(parts).strip() + "\n"
    _log.event(
        "council_prompt_built",
        n_under_dosed_triggers=len(triggers),
        n_history_triplets=len(history or []),
    )
    return body


# ---------- section builders ----------

def _section_a(triggers: list[str]) -> str:
    """Roles & hard rules. Triggers list is informational — see T65.2."""
    base = (
        "## Section A — Roles & Hard Rules\n"
        "\n"
        "You are a 4-role expert council reviewing a cyclist's weekly plan.\n"
        "Emit ALL FOUR role bodies in order. Each role must be wrapped in\n"
        "the named tag (see Section D output schema).\n"
        "\n"
        "### Planner (`<planner>`)\n"
        "- Restate the weekly plan day-by-day with the prescribed power, "
        "duration, and intent for each session.\n"
        "- Cite at least 2 numerical justifications drawn from Section B.\n"
        "\n"
        "### Critic (`<critic>`)\n"
        "- Produce at LEAST 3 independent objection points the Planner did "
        "NOT raise.\n"
        "- Every point must include a numeric data citation (W, bpm, min, "
        "%, kJ/J or `field=value`).\n"
        "- Run the 6-item UNDER-DOSED checklist; report each item OK / "
        "UNDER-DOSED with reasoning.\n"
        "\n"
        "### Physiologist (`<physiologist>`)\n"
        "- Cite ≥3 of {CP, W', durability, response_profile} in your body.\n"
        "- Provide a quantitative end-of-week W' balance estimate.\n"
        "- Call out knee_flag status explicitly.\n"
        "\n"
        "### Arbiter (`<arbiter>`)\n"
        "- First line: ACCEPT / REVISE / REJECT.\n"
        "- Then a one-sentence justification.\n"
        "- For REVISE: enumerate every change as `(day, from, to)` triples.\n"
        "- The `<summary_json>` block must echo `verdict` + "
        "`confidence ∈ [0.0, 1.0]` consistent with this first line.\n"
    )
    if triggers:
        bullet_list = "\n".join(f"- {t}" for t in triggers)
        base += (
            "\n"
            "### UNDER-DOSED HYPOTHESIS — auto-fired triggers\n"
            "The deterministic pre-flight detector flagged these "
            "candidate UNDER-DOSED conditions. The Critic MUST examine each "
            "and either confirm or refute with data:\n"
            f"{bullet_list}\n"
        )
    return base


def _section_b(request: VerdictRequest) -> str:
    state = request.athlete_state
    plan_dump = json.dumps(
        request.plan, indent=2, ensure_ascii=False, sort_keys=True)
    state_dump = json.dumps(
        state.model_dump(), indent=2,
        ensure_ascii=False, sort_keys=True)
    phys_dump = json.dumps(
        request.physiology, indent=2,
        ensure_ascii=False, sort_keys=True)
    period_dump = json.dumps(
        request.periodization_summary, indent=2,
        ensure_ascii=False, sort_keys=True)
    wellness_dump = json.dumps(
        request.wellness_trend, indent=2,
        ensure_ascii=False, sort_keys=True)
    return (
        "## Section B — Input Data\n"
        "\n"
        "### Weekly plan (Phase 2 output)\n"
        "```json\n"
        f"{plan_dump}\n"
        "```\n"
        "\n"
        "### Athlete state snapshot\n"
        "```json\n"
        f"{state_dump}\n"
        "```\n"
        "\n"
        "### Physiology summary (Phase 1)\n"
        "```json\n"
        f"{phys_dump}\n"
        "```\n"
        "\n"
        "### Periodization summary\n"
        "```json\n"
        f"{period_dump}\n"
        "```\n"
        "\n"
        "### Wellness trend (recent days)\n"
        "```json\n"
        f"{wellness_dump}\n"
        "```\n"
    )


def _section_c(history: list[HistoryTriplet]) -> str:
    if not history:
        return (
            "## Section C — Active Ledger History\n"
            "\n"
            "(no historical context)\n"
        )
    rows: list[str] = []
    for t in history:
        ctx_dump = json.dumps(
            t.context, ensure_ascii=False, sort_keys=True)
        verdict_label = t.verdict or "(none)"
        pending_hint = (
            "(awaiting follow-on entry)"
            if t.outcome == OUTCOME_PENDING else ""
        )
        rows.append(
            f"- **plan_entry_id**: `{t.plan_entry_id}`  \n"
            f"  **context**: {ctx_dump}  \n"
            f"  **verdict**: `{verdict_label}`  \n"
            f"  **outcome**: `{t.outcome}`  {pending_hint}"
        )
    return (
        "## Section C — Active Ledger History\n"
        "\n"
        f"{len(history)} similar context-verdict-outcome triplet(s):\n"
        "\n"
        + "\n".join(rows)
        + "\n"
    )


def _section_d() -> str:
    return (
        "## Section D — Output Schema\n"
        "\n"
        "Emit, in this exact order:\n"
        "\n"
        "```\n"
        "<planner>\n"
        "...your planner body...\n"
        "</planner>\n"
        "\n"
        "<critic>\n"
        "...your critic body...\n"
        "</critic>\n"
        "\n"
        "<physiologist>\n"
        "...your physiologist body...\n"
        "</physiologist>\n"
        "\n"
        "<arbiter>\n"
        "ACCEPT|REVISE|REJECT\n"
        "...one-line justification...\n"
        "</arbiter>\n"
        "\n"
        "<summary_json>\n"
        '{"verdict": "ACCEPT|REVISE|REJECT", "confidence": 0.0}\n'
        "</summary_json>\n"
        "```\n"
        "\n"
        "Hard rules enforced by the parser:\n"
        "- All four role tags must appear, non-empty.\n"
        "- The `<summary_json>` block must be valid JSON, an object.\n"
        "- `verdict` must be one of ACCEPT / REVISE / REJECT.\n"
        "- `confidence` must be a float in [0.0, 1.0].\n"
        "- Critic body must contain ≥3 numbered or bulleted points, each "
        "carrying a numeric citation.\n"
        "- Physiologist body must mention ≥3 of {CP, W', durability, "
        "response_profile}.\n"
        "- The verdict in the first line of the Arbiter body must match "
        "the verdict in summary_json.\n"
    )


# ---------- detect_under_dosed_triggers stub for T65.1 ----------

def detect_under_dosed_triggers(
    plan: dict[str, Any],
    athlete_state: dict[str, Any],
) -> list[str]:
    """Return zero or more UNDER-DOSED trigger labels.

    T65.1 ships a stub that always returns []. T65.2 fills in the 6 rules
    drawn from blueprint §4.6 / Critic UNDER-DOSED checklist.
    """
    _ = plan, athlete_state
    return []
```

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py -v
```

Expected: ~14 tests pass.

### - [ ] **Step 5: Commit**

```bash
git add icu/src/coach/consensus/council_prompt.py \
        icu/tests/unit/consensus/test_council_prompt.py
git commit -m "feat(coach-phase3): consensus council_prompt 4-section assembler + VerdictRequest (T65.1)"
```

## T65.2 — UNDER-DOSED 6-trigger detector

**Goal.** Flesh out `detect_under_dosed_triggers(plan, athlete_state)` so that
each of the 6 conditions from blueprint §4.6 ("6 条 UNDER-DOSED 检查清单"),
when it fires, produces a stable, human-readable label that gets injected
into Section A's "UNDER-DOSED HYPOTHESIS" sub-section.

The 6 conditions, lifted verbatim from the blueprint:

1. 本周 HARD 日数 vs Meso 阶段应配额（BUILD: 2–3 次底线；≤1 即 UNDER-DOSED）
2. VO2max/Threshold session 工作间总时长 vs `response_profile.types[<type>].tolerance_class`（high tolerance = 18–24min work 底线）
3. 周总 TSS vs CTL 对应 acceptable load band（低于下界 = UNDER-DOSED）
4. Race 前 6 周是否至少 1 次 race-sim session（PEAK phase 必做）
5. 过去 3 周 stimulus_score 均值 < 0.45 → UNDER-DOSED
6. 过去 3 周是否至少 2 次 session 使 W' balance < −50%（无 = 缺高强度）

**Implementation note — out-of-scope inputs.** Triggers 5 and 6 require
inputs (`stimulus_score`, `w_prime_balance`) that the deterministic
pre-flight does not have access to from `plan + athlete_state` alone.
For those two we **only** check whether the input bundle includes the
optional keys `recent_stimulus_scores` (list of floats) and
`recent_w_prime_negatives` (list of ints — count of qualifying sessions
per recent week). When the keys are absent, the detector emits the trigger
as `"…: insufficient data — Critic must verify"` so the LLM is informed
that automatic checking failed and must run it manually.

This is consistent with blueprint §4.6's intent: the deterministic
pre-flight is a HINT, not a replacement for the LLM-side audit. The
ground truth always sits with the Critic role.

The 6 trigger labels (constants — used both in implementation and tests):

```
T1: under_dosed.hard_day_quota
T2: under_dosed.hi_intensity_work_minutes
T3: under_dosed.weekly_tss_below_band
T4: under_dosed.peak_no_race_sim
T5: under_dosed.stimulus_3w_mean
T6: under_dosed.w_prime_negatives_3w
```

(all snake_case, dotted, prefixed `under_dosed.` for grep-ability)

### - [ ] **Step 1: Write RED test**

Append to `icu/tests/unit/consensus/test_council_prompt.py`:

```python
# ---------- T65.2: detect_under_dosed_triggers ----------

class TestDetectUnderDosedTriggers:

    # ---- Trigger 1: hard-day quota ----

    def test_t1_fires_when_zero_hard_days_in_BUILD(self):
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"  # no hard days
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" in triggers

    def test_t1_fires_when_one_hard_day_in_BUILD(self):
        plan = _plan()
        # exactly 1 HIGH-tier day in BUILD = UNDER-DOSED
        hi = [d for d in plan["days"] if d["tier"] == "HIGH"]
        # default _plan() has 2 HIGH days; collapse one to MID.
        hi[0]["tier"] = "MID"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" in triggers

    def test_t1_does_not_fire_with_two_hard_days_in_BUILD(self):
        # default _plan() has 2 HIGH days
        triggers = detect_under_dosed_triggers(
            _plan(), _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" not in triggers

    def test_t1_skipped_outside_BUILD(self):
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="RECOVERY").model_dump())
        # T1 only checks BUILD specifically; outside BUILD no fire
        assert "under_dosed.hard_day_quota" not in triggers

    # ---- Trigger 2: hi-intensity work minutes ----

    def test_t2_fires_when_total_hi_work_below_18min(self):
        plan = _plan()
        for d in plan["days"]:
            if d["training_type"] in ("VO2max", "Threshold"):
                d["duration_min"] = 10  # well below 18min floor
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.hi_intensity_work_minutes" in triggers

    def test_t2_does_not_fire_when_total_hi_work_above_18min(self):
        # default _plan() has 75+80=155min hi (uses duration as proxy)
        triggers = detect_under_dosed_triggers(
            _plan(), _state().model_dump())
        assert "under_dosed.hi_intensity_work_minutes" not in triggers

    # ---- Trigger 3: weekly TSS below band ----

    def test_t3_fires_when_tss_below_load_band(self):
        plan = _plan(weekly_tss_target=300)  # CTL=70 → band lower bound ~5*CTL=350
        triggers = detect_under_dosed_triggers(
            plan, _state(ctl=70.0).model_dump())
        assert "under_dosed.weekly_tss_below_band" in triggers

    def test_t3_does_not_fire_when_tss_in_band(self):
        plan = _plan(weekly_tss_target=525)  # well within band
        triggers = detect_under_dosed_triggers(
            plan, _state(ctl=70.0).model_dump())
        assert "under_dosed.weekly_tss_below_band" not in triggers

    # ---- Trigger 4: PEAK phase race-sim ----

    def test_t4_fires_in_PEAK_with_no_race_sim(self):
        plan = _plan()
        # default plan has no day named "Race-Sim"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="PEAK").model_dump())
        assert "under_dosed.peak_no_race_sim" in triggers

    def test_t4_does_not_fire_in_PEAK_with_race_sim(self):
        plan = _plan()
        plan["days"][5]["name"] = "Race-Sim 90min"
        plan["days"][5]["training_type"] = "RaceSim"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="PEAK").model_dump())
        assert "under_dosed.peak_no_race_sim" not in triggers

    def test_t4_skipped_outside_PEAK(self):
        # in BUILD, T4 must not fire even with no race-sim
        triggers = detect_under_dosed_triggers(
            _plan(), _state(phase="BUILD").model_dump())
        assert "under_dosed.peak_no_race_sim" not in triggers

    # ---- Trigger 5: stimulus_score 3-week mean ----

    def test_t5_fires_when_3w_mean_below_0_45(self):
        plan = _plan()
        plan["recent_stimulus_scores"] = [0.4, 0.42, 0.38]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.stimulus_3w_mean" in triggers

    def test_t5_does_not_fire_when_mean_above_threshold(self):
        plan = _plan()
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.50]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.stimulus_3w_mean" not in triggers

    def test_t5_emits_insufficient_data_label_when_key_absent(self):
        plan = _plan()
        plan.pop("recent_stimulus_scores", None)
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert any(t.startswith("under_dosed.stimulus_3w_mean")
                   and "insufficient data" in t for t in triggers)

    # ---- Trigger 6: W' negatives 3-week count ----

    def test_t6_fires_when_three_week_negatives_below_two(self):
        plan = _plan()
        plan["recent_w_prime_negatives"] = [0, 1, 1]  # all under 2
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.w_prime_negatives_3w" in triggers

    def test_t6_does_not_fire_with_two_or_more_negatives(self):
        plan = _plan()
        plan["recent_w_prime_negatives"] = [3, 2, 4]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.w_prime_negatives_3w" not in triggers

    def test_t6_emits_insufficient_data_label_when_key_absent(self):
        plan = _plan()
        plan.pop("recent_w_prime_negatives", None)
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert any(t.startswith("under_dosed.w_prime_negatives_3w")
                   and "insufficient data" in t for t in triggers)

    # ---- happy path: no triggers ----

    def test_no_triggers_for_well_dosed_plan(self):
        plan = _plan(weekly_tss_target=525)
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.55]
        plan["recent_w_prime_negatives"] = [3, 2, 3]
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert triggers == []

    # ---- prompt wiring: triggers appear in Section A ----

    def test_triggers_render_in_prompt_section_a_when_present(self):
        # request whose plan triggers T1
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"
        req = _request(plan=plan)
        out = build_council_prompt(req)
        assert "UNDER-DOSED HYPOTHESIS" in out
        assert "under_dosed.hard_day_quota" in out

    def test_no_under_dosed_section_when_no_triggers(self):
        plan = _plan(weekly_tss_target=525)
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.55]
        plan["recent_w_prime_negatives"] = [3, 2, 3]
        req = _request(plan=plan)
        out = build_council_prompt(req)
        # When no triggers, the optional sub-section is omitted entirely.
        assert "UNDER-DOSED HYPOTHESIS" not in out
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py::TestDetectUnderDosedTriggers -v
```

Expected: roughly 19 new tests fail with assertion errors (no triggers
returned by the stub). The `test_no_triggers_for_well_dosed_plan` may pass
incidentally; that's fine.

### - [ ] **Step 3: Minimal implementation**

Replace the `detect_under_dosed_triggers` stub at the bottom of
`icu/src/coach/consensus/council_prompt.py` with the following full
implementation:

```python
# ---------- UNDER-DOSED 6-trigger detector ----------

# Tunable thresholds (lifted from blueprint §4.6 + reasonable defaults):
_BUILD_HARD_DAYS_FLOOR = 2          # T1: BUILD needs ≥2 HIGH-tier days
_HI_TOLERANCE_FLOOR_MIN = 18        # T2: high-tolerance class baseline
_TSS_BAND_LOWER_MULT = 5.0          # T3: lower edge of "acceptable load
                                    #     band" ≈ 5 × CTL (TSS/week)
_STIM_3W_MEAN_FLOOR = 0.45          # T5
_W_NEG_PER_WEEK_FLOOR = 2           # T6 — sessions per week with W' < -50%


def detect_under_dosed_triggers(
    plan: dict[str, Any],
    athlete_state: dict[str, Any],
) -> list[str]:
    """Run the 6-item UNDER-DOSED checklist (blueprint §4.6).

    Returns 0–6 stable labels. Labels are PREFIX-stable (`under_dosed.<id>`)
    so the prompt + tests can grep them. Where the deterministic check
    cannot run (missing input keys), emits an `insufficient data` variant
    that tells the Critic role to verify manually.

    The detector is INTENTIONALLY conservative: it errs on the side of
    "fire the trigger" so the Critic gets nudged. False positives are
    harmless (the Critic dismisses with data); false negatives are not
    (the user keeps getting under-prescribed plans).
    """
    triggers: list[str] = []
    phase = (athlete_state.get("phase") or "").upper()
    ctl = float(athlete_state.get("ctl") or 0.0)
    days = list(plan.get("days") or [])

    # -- T1: BUILD hard-day quota --
    if phase == "BUILD":
        hard_days = sum(1 for d in days
                        if str(d.get("tier", "")).upper() == "HIGH")
        if hard_days < _BUILD_HARD_DAYS_FLOOR:
            triggers.append("under_dosed.hard_day_quota")

    # -- T2: hi-intensity work minutes --
    hi_min = 0
    for d in days:
        if d.get("training_type") in ("VO2max", "Threshold"):
            try:
                hi_min += int(d.get("duration_min") or 0)
            except (TypeError, ValueError):
                continue
    # Use duration_min as a coarse proxy for "work-interval minutes" when
    # the plan does not break down work vs rest within the session.
    # Threshold 18min floor matches the "high tolerance" band baseline
    # in blueprint §4.6.
    if 0 < hi_min < _HI_TOLERANCE_FLOOR_MIN:
        triggers.append("under_dosed.hi_intensity_work_minutes")
    elif hi_min == 0:
        # No hi-intensity prescribed at all is a strict UNDER-DOSED.
        triggers.append("under_dosed.hi_intensity_work_minutes")

    # -- T3: weekly TSS below band --
    try:
        weekly_tss = int(plan.get("weekly_tss_target") or 0)
    except (TypeError, ValueError):
        weekly_tss = 0
    band_lower = _TSS_BAND_LOWER_MULT * ctl  # heuristic acceptable lower edge
    if ctl > 0 and weekly_tss > 0 and weekly_tss < band_lower:
        triggers.append("under_dosed.weekly_tss_below_band")

    # -- T4: PEAK without race-sim --
    if phase == "PEAK":
        has_race_sim = any(
            "race-sim" in str(d.get("name", "")).lower()
            or str(d.get("training_type", "")).lower() == "racesim"
            for d in days
        )
        if not has_race_sim:
            triggers.append("under_dosed.peak_no_race_sim")

    # -- T5: stimulus 3-week mean --
    stim = plan.get("recent_stimulus_scores")
    if isinstance(stim, list) and stim:
        try:
            mean_stim = sum(float(x) for x in stim) / len(stim)
        except (TypeError, ValueError):
            mean_stim = None
        if mean_stim is not None and mean_stim < _STIM_3W_MEAN_FLOOR:
            triggers.append("under_dosed.stimulus_3w_mean")
    else:
        triggers.append(
            "under_dosed.stimulus_3w_mean: insufficient data — "
            "Critic must verify"
        )

    # -- T6: W' negatives per week 3-week --
    negs = plan.get("recent_w_prime_negatives")
    if isinstance(negs, list) and negs:
        try:
            below = sum(1 for n in negs if int(n) < _W_NEG_PER_WEEK_FLOOR)
        except (TypeError, ValueError):
            below = len(negs)  # fail closed: count as all-below
        if below > 0:
            triggers.append("under_dosed.w_prime_negatives_3w")
    else:
        triggers.append(
            "under_dosed.w_prime_negatives_3w: insufficient data — "
            "Critic must verify"
        )

    return triggers
```

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py -v
```

Expected: all tests pass (T65.1 + T65.2 = roughly 33 tests).

### - [ ] **Step 5: Commit**

```bash
git add icu/src/coach/consensus/council_prompt.py \
        icu/tests/unit/consensus/test_council_prompt.py
git commit -m "feat(coach-phase3): consensus 6 UNDER-DOSED trigger detector wired into Section A (T65.2)"
```

## T65.3 — History triplet wiring (Section C)

**Goal.** When the caller passes a non-empty `history` list, render each
`HistoryTriplet` as a markdown bullet inside Section C. Preserve the
`outcome_pending` sentinel verbatim with a parenthetical hint
(`(awaiting follow-on entry)`) so the LLM can distinguish "no outcome
recorded yet" from "outcome was bad/good/neutral".

We deliberately do NOT call `LedgerReader` from here — `build_council_prompt`
remains pure (no IO). The CLI in T65.4 wires the reader → injector →
prompt-builder pipeline.

This task adds **3 tests** for the rendering and **does not modify
implementation** — the renderer was already written in T65.1 and is
exercised here with realistic triplets to lock the contract.

### - [ ] **Step 1: Write RED test**

Append to `icu/tests/unit/consensus/test_council_prompt.py`:

```python
# ---------- T65.3: history triplet rendering ----------

from src.coach.consensus.history_injector import HistoryTriplet, OUTCOME_PENDING


def _triplet(**over) -> HistoryTriplet:
    base = dict(
        plan_entry_id="01HZZZ" + "0" * 20,
        context={"phase": "BUILD", "total_tss": 520,
                 "ctl": 70.0, "week_of_year": 14,
                 "plan_period": "2026-04-06_2026-04-12"},
        verdict="ACCEPT",
        outcome="consensus.ACCEPT@0.82",
    )
    base.update(over)
    return HistoryTriplet(**base)


class TestSectionCRendering:

    def test_renders_each_triplet_as_bullet(self):
        triplets = [_triplet(),
                    _triplet(plan_entry_id="01ZZZB" + "1" * 20,
                             outcome=OUTCOME_PENDING)]
        out = build_council_prompt(_request(), history=triplets)
        # Both plan_entry_ids appear as backticked code spans.
        assert "01HZZZ" in out
        assert "01ZZZB" in out

    def test_outcome_pending_marked_with_hint(self):
        triplets = [_triplet(outcome=OUTCOME_PENDING)]
        out = build_council_prompt(_request(), history=triplets)
        assert OUTCOME_PENDING in out
        # Hint string the prompt builder adds beside outcome_pending.
        assert "awaiting follow-on entry" in out

    def test_section_c_summary_count_matches_input(self):
        triplets = [_triplet(plan_entry_id="01A" + "0" * 23),
                    _triplet(plan_entry_id="01B" + "1" * 23),
                    _triplet(plan_entry_id="01C" + "2" * 23)]
        out = build_council_prompt(_request(), history=triplets)
        # The Section C header line should report the triplet count.
        assert "3 similar context-verdict-outcome triplet(s)" in out

    def test_no_history_renders_empty_sentinel(self):
        out_none = build_council_prompt(_request(), history=None)
        out_empty = build_council_prompt(_request(), history=[])
        for out in (out_none, out_empty):
            assert "(no historical context)" in out
            assert "context-verdict-outcome triplet(s)" not in out

    def test_verdict_field_renders_safely_when_blank(self):
        # File 06 history_injector currently always sets verdict="" (the
        # plan-time verdict isn't emitted by Phase 2). Assert we don't crash
        # and we render `(none)` so the LLM doesn't see an empty backtick.
        triplets = [_triplet(verdict="")]
        out = build_council_prompt(_request(), history=triplets)
        assert "**verdict**: `(none)`" in out
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py::TestSectionCRendering -v
```

Expected: tests pass IF the T65.1 renderer is intact. If a test fails it
points at a missed contract — fix the renderer (do not weaken the test).

### - [ ] **Step 3: Minimal implementation**

No new code if T65.1 already renders triplets correctly. If any of the 5
tests above fail in Step 2, the most common fix is one of:

- The `outcome_pending` hint string changed: confirm
  `'(awaiting follow-on entry)'` appears next to outcome_pending in
  `_section_c`.
- The blank-verdict path falls through: confirm `t.verdict or '(none)'` in
  the bullet template.
- The summary count line is missing: confirm
  `f"{len(history)} similar context-verdict-outcome triplet(s):"`.

If T65.1 is correct, leave the implementation file untouched and just
re-run.

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/consensus/test_council_prompt.py -v
```

Expected: all consensus prompt tests pass (T65.1 + T65.2 + T65.3 ≈ 38).

### - [ ] **Step 5: Commit**

```bash
git add icu/tests/unit/consensus/test_council_prompt.py
git commit -m "test(coach-phase3): pin Section C history-triplet rendering contract (T65.3)"
```

(If you had to fix the renderer in Step 3, also stage
`icu/src/coach/consensus/council_prompt.py` and update the commit message
to `feat(coach-phase3): ...`.)

## T65.4 — `scripts/run_consensus.py` CLI

**Goal.** A standalone Python script that:

1. Reads a `VerdictRequest` from a JSON file (`--verdict-request`).
2. Optionally reads a list of `HistoryTriplet`s from a JSON file
   (`--history`); if absent, emits `(no historical context)`.
3. Calls `build_council_prompt(request, history)`.
4. Writes the resulting markdown to `--out` (default
   `./council.prompt.md` in the current working directory).
5. Prints to stdout the next-step instructions:

   ```
   Wrote council prompt → ./council.prompt.md
   Next steps:
     1. Open the file, copy its contents.
     2. Paste into Gemini CLI / Claude Code coach mode.
     3. Save the LLM response as council.response.md.
     4. Run: scripts/finalize_consensus.py --response council.response.md \
            --ledger coach_memory/ledger/decisions.jsonl
   ```

6. Exit 0 on success, 2 on input file errors, 3 on output write errors.

**Hard rule.** This script must NOT import `google.genai` or any LLM SDK.
It must NOT open a network socket. Verify with
`grep -R 'google\.genai\|requests\|urllib\|httpx' icu/scripts/run_consensus.py`
returning empty.

### - [ ] **Step 1: Write RED test**

Create `icu/tests/unit/scripts/test_run_consensus.py`:

```python
"""Unit tests for scripts.run_consensus."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_consensus import main as run_main


def _verdict_request_payload() -> dict:
    return {
        "plan": {
            "week_start": "2026-04-20",
            "week_end": "2026-04-26",
            "focus_theme": "BUILD",
            "weekly_tss_target": 525,
            "days": [
                {"day_of_week": d, "training_type": "Endurance",
                 "name": "Z2", "duration_min": 60, "target_tss": 50,
                 "power_range_w": "150-180W", "tier": "MID"}
                for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            ],
            "recent_stimulus_scores": [0.55, 0.55, 0.55],
            "recent_w_prime_negatives": [3, 3, 3],
        },
        "athlete_state": {
            "ctl": 70.0, "atl": 68.0, "tsb": 2.0,
            "w_prime": 14_500,
            "phase": "BUILD", "week_of_year": 17,
        },
        "physiology": {"cp_w": 285, "w_prime_j": 14_500,
                       "durability_index": 0.74,
                       "response_profile": {"types": {}},
                       "knee_flag": "OK"},
        "wellness_trend": [],
        "periodization_summary": {"phase": "BUILD",
                                  "weekly_tss_target": 525},
    }


def _history_payload() -> list[dict]:
    return [
        {
            "plan_entry_id": "01HZZZ" + "0" * 20,
            "context": {"phase": "BUILD", "total_tss": 520, "ctl": 70.0,
                        "week_of_year": 14,
                        "plan_period": "2026-04-06_2026-04-12"},
            "verdict": "ACCEPT",
            "outcome": "consensus.ACCEPT@0.82",
        },
    ]


# ---------- happy path ----------

class TestRunConsensusHappyPath:

    def test_writes_prompt_with_no_history(self, tmp_path, capsys):
        req_path = tmp_path / "req.json"
        out_path = tmp_path / "council.prompt.md"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")

        rc = run_main([
            "--verdict-request", str(req_path),
            "--out", str(out_path),
        ])

        assert rc == 0
        body = out_path.read_text(encoding="utf-8")
        assert "## Section A" in body
        assert "## Section D" in body
        assert "(no historical context)" in body
        assert "<summary_json>" in body
        out = capsys.readouterr().out
        assert "council.prompt.md" in out
        assert "finalize_consensus" in out

    def test_writes_prompt_with_history(self, tmp_path):
        req_path = tmp_path / "req.json"
        hist_path = tmp_path / "hist.json"
        out_path = tmp_path / "council.prompt.md"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        hist_path.write_text(json.dumps(_history_payload()),
                             encoding="utf-8")

        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(hist_path),
            "--out", str(out_path),
        ])
        assert rc == 0
        body = out_path.read_text(encoding="utf-8")
        assert "01HZZZ" in body
        assert "(no historical context)" not in body

    def test_default_out_is_council_prompt_md(self, tmp_path,
                                              monkeypatch):
        req_path = tmp_path / "req.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = run_main([
            "--verdict-request", str(req_path),
        ])
        assert rc == 0
        assert (tmp_path / "council.prompt.md").exists()


# ---------- error paths ----------

class TestRunConsensusErrors:

    def test_missing_verdict_request_file_exit_2(self, tmp_path, capsys):
        rc = run_main([
            "--verdict-request", str(tmp_path / "absent.json"),
            "--out", str(tmp_path / "out.md"),
        ])
        assert rc == 2
        err = capsys.readouterr().err
        assert "verdict-request" in err.lower() or "absent.json" in err

    def test_malformed_verdict_request_exit_2(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        rc = run_main([
            "--verdict-request", str(bad),
            "--out", str(tmp_path / "out.md"),
        ])
        assert rc == 2

    def test_missing_history_file_exit_2(self, tmp_path):
        req_path = tmp_path / "req.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(tmp_path / "absent_history.json"),
            "--out", str(tmp_path / "out.md"),
        ])
        assert rc == 2

    def test_history_payload_must_be_list(self, tmp_path):
        req_path = tmp_path / "req.json"
        hist_path = tmp_path / "hist.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        hist_path.write_text(json.dumps({"not": "a list"}),
                             encoding="utf-8")
        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(hist_path),
            "--out", str(tmp_path / "out.md"),
        ])
        assert rc == 2


# ---------- API_FREE invariant ----------

class TestApiFreeInvariant:

    def test_no_llm_sdk_imported(self):
        from pathlib import Path
        text = Path("scripts/run_consensus.py").read_text(encoding="utf-8")
        forbidden = ("google.genai", "from google import genai",
                     "import requests", "import urllib", "import httpx")
        for needle in forbidden:
            assert needle not in text, (
                f"run_consensus.py must remain API_FREE; found {needle!r}")
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_run_consensus.py -v
```

Expected error fragment:

```
ModuleNotFoundError: No module named 'scripts.run_consensus'
```

### - [ ] **Step 3: Minimal implementation**

Create `icu/scripts/run_consensus.py`:

```python
"""Phase 3 — assemble a council prompt for the user to paste into Gemini.

Reads:
  --verdict-request <path>   JSON of VerdictRequest fields
  [--history <path>]         JSON of list[HistoryTriplet]
  [--out <path>]             default ./council.prompt.md

Writes:
  one markdown file at --out

Exit codes:
  0 — success
  2 — input file error (missing, unreadable, bad JSON, wrong shape)
  3 — output write error

API_FREE: no LLM SDK, no network.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# Allow `python scripts/run_consensus.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.consensus.council_prompt import (  # noqa: E402
    VerdictRequest,
    build_council_prompt,
)
from src.coach.consensus.history_injector import HistoryTriplet  # noqa: E402


_NEXT_STEPS = (
    "Next steps:\n"
    "  1. Open the file, copy its contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save the LLM response as council.response.md.\n"
    "  4. Run: scripts/finalize_consensus.py --response council.response.md "
    "\\\n"
    "         --ledger coach_memory/ledger/decisions.jsonl"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 — assemble a 4-section council prompt from a "
            "VerdictRequest JSON. API-free; emits a markdown file the "
            "user pastes into Gemini."
        ),
    )
    p.add_argument("--verdict-request", required=True, type=Path,
                   help="Path to VerdictRequest JSON.")
    p.add_argument("--history", type=Path, default=None,
                   help="Optional: path to JSON list of HistoryTriplet.")
    p.add_argument("--out", type=Path,
                   default=Path("council.prompt.md"),
                   help="Output markdown path (default ./council.prompt.md)")
    return p.parse_args(argv)


def _load_json_or_die(path: Path, label: str) -> object:
    if not path.exists():
        print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {label} JSON is malformed at {path}: {exc}",
              file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"ERROR: cannot read {label} file {path}: {exc}",
              file=sys.stderr)
        raise SystemExit(2)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        # argparse exits with 2 on parse errors — pass through.
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        req_payload = _load_json_or_die(args.verdict_request,
                                        "verdict-request")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        request = VerdictRequest.model_validate(req_payload)
    except Exception as exc:  # pydantic.ValidationError or similar
        print(f"ERROR: verdict-request schema validation failed: {exc}",
              file=sys.stderr)
        return 2

    history: list[HistoryTriplet] | None = None
    if args.history is not None:
        try:
            hist_payload = _load_json_or_die(args.history, "history")
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        if not isinstance(hist_payload, list):
            print(
                f"ERROR: history JSON must be a list, got "
                f"{type(hist_payload).__name__}",
                file=sys.stderr,
            )
            return 2
        try:
            history = [HistoryTriplet.model_validate(t)
                       for t in hist_payload]
        except Exception as exc:
            print(f"ERROR: history triplet schema validation failed: {exc}",
                  file=sys.stderr)
            return 2

    body = build_council_prompt(request, history=history)

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write output {args.out}: {exc}",
              file=sys.stderr)
        return 3

    print(f"Wrote council prompt -> {args.out}")
    print(_NEXT_STEPS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_run_consensus.py -v
```

Expected: all ~9 tests pass.

Manual smoke from `icu/`:

```
.venv/bin/python scripts/run_consensus.py \
    --verdict-request tests/fixtures/phase3/consensus/verdict_request_sample.json \
    --out /tmp/cc.md
```

(The fixture is created in the smoke-test section at the bottom of this
file. If the fixture does not exist yet, skip the smoke command — pytest
already covers the contract.)

### - [ ] **Step 5: Commit**

```bash
git add icu/scripts/run_consensus.py \
        icu/tests/unit/scripts/test_run_consensus.py
git commit -m "feat(coach-phase3): run_consensus.py CLI emits council prompt md (T65.4, API-free)"
```

# Task 66 — `finalize_consensus.py` CLI

T66 builds the human-gate "I have the LLM's response, write it to the
ledger" CLI. The flow is:

1. User runs `scripts/run_consensus.py` (T65.4) → gets `council.prompt.md`.
2. User pastes into Gemini, saves the response as `council.response.md`.
3. User runs `scripts/finalize_consensus.py --response council.response.md
   --ledger coach_memory/ledger/decisions.jsonl` (default = dry-run).
4. `finalize_consensus`:
   - reads response file (UTF-8)
   - parses + validates via `consensus.response_parser.parse(...)` —
     raises `ConsensusValidationError` with a list of violations on any of
     6 hard-rule failures
   - reads athlete state from a `--athlete-state` JSON path (required;
     used to populate the ledger entry's `athlete_state_ref` field)
   - constructs the ledger payload
   - if `--dry-run` (default): pretty-prints the full would-be entry and
     exits 0 — ledger file untouched.
   - if `--confirm`: opens `LedgerWriter`, computes content-hash,
     checks for prior ledger entry with same content-hash; if found,
     prints `Already finalized: <hash>` and exits 0; otherwise calls
     `writer.record(...)`, prints the new `entry_id`, exits 0.
5. Failure rollback: any exception that can be raised by file IO,
   `json.loads`, or `parse(...)` MUST occur **BEFORE** any
   `writer.record(...)` invocation. The implementation enforces this with
   strict ordering — see T66.2.

T66 splits into 3 RED → GREEN cycles:

- **T66.1** — argparse skeleton + dry-run print + happy path
- **T66.2** — parse + validate + ledger append, with failure-before-write
  ordering
- **T66.3** — content-hash idempotency + duplicate detection

## T66.1 — argparse skeleton + dry-run default

**Goal.** Build the CLI shell that:

- Requires `--response <path>` (markdown), `--ledger <path>` (jsonl),
  `--athlete-state <path>` (json).
- Has mutually exclusive `--dry-run` (default) and `--confirm`.
- In dry-run: parses, prints would-be entry, exits 0.
- In confirm: same parse step then calls a stub
  `_append_to_ledger(...)` that we will implement in T66.2 (T66.1 leaves
  it as a `NotImplementedError`-raising placeholder so the test can lock
  the dry-run/confirm split).

### - [ ] **Step 1: Write RED test**

Create `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
"""Unit tests for scripts.finalize_consensus."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.finalize_consensus import main as finalize_main


# ---------- canned valid council response ----------

_HAPPY_RESPONSE = """\
<planner>
This week 525 TSS targets the BUILD phase. Tuesday 5x4min @CP at 270W
is the keystone session per the threshold response_profile. Saturday
180min Z2 builds durability at 165W average; total 615 minutes work,
matched to CP=285W and W'=14500J.
</planner>

<critic>
1. The Tuesday VO2max session is only 20min work; CP=285W tolerance band
   demands 22-24min for high-tolerance class — UNDER-DOSED by 2-4 min.
2. Friday threshold 2x20min total = 40min, but recent stimulus_score
   mean = 0.42 < 0.45 floor; need a third interval.
3. Saturday's long Z2 lacks a sustained sweet-spot block; durability
   index = 0.74 suggests 2x10min @ 230W could nudge it up.
</critic>

<physiologist>
CP=285W and W'=14500J anchor this athlete in mid-pack response_profile.
With the prescribed plan, end-of-week W' balance estimate is -42% on
Saturday. durability index = 0.74 is intact. knee_flag = OK.
</physiologist>

<arbiter>
REVISE
Plan needs one more threshold interval and 2 extra VO2 minutes.
- (Tue, 5x4min @270W, 6x4min @270W)
- (Fri, 2x20min @250W, 3x20min @250W)
</arbiter>

<summary_json>
{"verdict": "REVISE", "confidence": 0.78}
</summary_json>
"""


_ATHLETE_STATE = {
    "ctl": 70.0, "atl": 68.0, "tsb": 2.0, "w_prime": 14_500,
    "phase": "BUILD", "week_of_year": 17,
}


def _write_response(path: Path, body: str = _HAPPY_RESPONSE) -> None:
    path.write_text(body, encoding="utf-8")


def _write_state(path: Path, payload: dict | None = None) -> None:
    path.write_text(json.dumps(payload or _ATHLETE_STATE),
                    encoding="utf-8")


# ---------- argparse skeleton tests ----------

class TestArgparseSkeleton:

    def test_required_flags_missing_exit_2(self, tmp_path, capsys):
        rc = finalize_main([])
        # argparse exits 2 on missing required args
        assert rc == 2

    def test_dry_run_is_default(self, tmp_path, capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        # dry-run → exit 0 even though ledger doesn't exist
        assert rc == 0
        # ledger file must remain untouched
        assert not ledger.exists()
        out = capsys.readouterr().out
        assert "DRY-RUN" in out or "dry-run" in out

    def test_dry_run_prints_would_be_entry(self, tmp_path, capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        # Verdict + confidence pulled from <summary_json>
        assert "REVISE" in out
        assert "0.78" in out
        # Decision type literal
        assert "consensus_verdict" in out
        # Source literal
        assert "consensus.council" in out

    def test_dry_run_and_confirm_mutually_exclusive(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--dry-run",
            "--confirm",
        ])
        # argparse mutex group rejects with exit 2
        assert rc == 2


# ---------- API_FREE invariant ----------

class TestApiFreeInvariantFinalize:

    def test_no_llm_sdk_imported(self):
        text = Path("scripts/finalize_consensus.py").read_text(
            encoding="utf-8")
        for needle in ("google.genai", "from google import genai",
                       "import requests", "import urllib", "import httpx"):
            assert needle not in text, (
                f"finalize_consensus.py must remain API_FREE; "
                f"found {needle!r}"
            )
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py -v
```

Expected error fragment:

```
ModuleNotFoundError: No module named 'scripts.finalize_consensus'
```

### - [ ] **Step 3: Minimal implementation**

Create `icu/scripts/finalize_consensus.py`:

```python
"""Phase 3 — finalize a Gemini council response into the decision ledger.

Default behaviour is DRY-RUN: print the would-be ledger entry and exit 0.
With --confirm, validate + append the entry; respect content-hash
idempotency (T66.3) so a re-run on the same response file is a no-op.

Reads:
  --response       path to council.response.md (the user's pasted Gemini reply)
  --ledger         path to decisions.jsonl
  --athlete-state  path to JSON file matching AthleteStateRef shape

Writes (only when --confirm):
  one append line in the ledger JSONL via LedgerWriter.record(...)

Exit codes:
  0 — success (dry-run, applied, or duplicate-skipped)
  2 — input error (missing file, malformed JSON, parser violations,
                   schema validation failure)
  3 — internal/IO error during ledger write

API_FREE: no LLM SDK, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

# Allow `python scripts/finalize_consensus.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.consensus.response_parser import parse as parse_council  # noqa: E402
from src.coach.consensus.types import (  # noqa: E402
    ConsensusValidationError,
    CouncilVerdict,
)
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.types import AthleteStateRef  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


# ---------- argparse ----------

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 — finalize a 4-role council response into the ledger. "
            "Default = dry-run print; pass --confirm to actually append."
        ),
    )
    p.add_argument("--response", required=True, type=Path,
                   help="Path to council.response.md (Gemini reply).")
    p.add_argument("--ledger", required=True, type=Path,
                   help="Path to ledger JSONL (decisions.jsonl).")
    p.add_argument("--athlete-state", required=True, type=Path,
                   help="Path to AthleteStateRef JSON.")
    gate = p.add_mutually_exclusive_group()
    gate.add_argument("--confirm", action="store_true",
                      help="Actually append to the ledger. "
                           "Default = dry-run.")
    gate.add_argument("--dry-run", action="store_true",
                      help="Explicit dry-run (default behavior).")
    return p.parse_args(argv)


# ---------- entry helpers ----------

def _content_hash(verdict: CouncilVerdict) -> str:
    """Stable content-hash for idempotency (T66.3).

    Hash domain: mode + verdict + confidence + justification +
    summary_json (sorted) + concatenated expert role bodies.
    Deterministic across re-runs because we sort dict keys + use UTF-8.
    """
    blob = json.dumps(
        {
            "mode": verdict.mode,
            "verdict": verdict.verdict,
            "confidence": round(verdict.confidence, 6),
            "justification": verdict.justification,
            "summary_json": verdict.summary_json,
            "turns": [
                {"role": t.role, "body_md": t.body_md}
                for t in verdict.expert_turns
            ],
        },
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _print_dry_run(verdict: CouncilVerdict,
                   athlete_state: AthleteStateRef,
                   evidence_path: Path,
                   content_hash: str) -> None:
    payload = verdict.model_dump()
    entry_preview = {
        "decision_type": "consensus_verdict",
        "source": "consensus.council",
        "athlete_state_ref": athlete_state.model_dump(),
        "confidence": verdict.confidence,
        "evidence_refs": [str(evidence_path)],
        "payload": payload,
        "content_hash": content_hash,
    }
    print("[DRY-RUN] would append the following ledger entry:")
    print(json.dumps(entry_preview, indent=2,
                     sort_keys=True, ensure_ascii=False))
    print("\nRe-run with --confirm to actually append.")


# ---------- main ----------

def _read_response(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: response file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read response file: {exc}", file=sys.stderr)
        raise SystemExit(2)


def _read_athlete_state(path: Path) -> AthleteStateRef:
    if not path.exists():
        print(f"ERROR: athlete-state file not found: {path}",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: athlete-state JSON malformed: {exc}",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        return AthleteStateRef.model_validate(raw)
    except Exception as exc:
        print(f"ERROR: athlete-state schema validation failed: {exc}",
              file=sys.stderr)
        raise SystemExit(2)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    # ---- Phase 1: read + parse + validate (BEFORE any ledger touch) ----
    try:
        response_md = _read_response(args.response)
        athlete_state = _read_athlete_state(args.athlete_state)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        verdict = parse_council(response_md, mode="council")
    except ConsensusValidationError as exc:
        print("ERROR: council response failed parser validation:",
              file=sys.stderr)
        for v in exc.violations:
            print(f"  - {v}", file=sys.stderr)
        return 2

    content_hash = _content_hash(verdict)

    # ---- Phase 2: dry-run vs confirm ----
    if not args.confirm:
        _print_dry_run(verdict, athlete_state, args.response, content_hash)
        return 0

    # T66.3 will fill in idempotency here; for T66.1 leave a marker that
    # the next task replaces.
    return _append_to_ledger(verdict, athlete_state, args.response,
                             args.ledger, content_hash)


def _append_to_ledger(
    verdict: CouncilVerdict,
    athlete_state: AthleteStateRef,
    evidence_path: Path,
    ledger_path: Path,
    content_hash: str,
) -> int:
    raise NotImplementedError(
        "T66.2 will implement ledger append; T66.1 only ships dry-run.")


if __name__ == "__main__":
    raise SystemExit(main())
```

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py::TestArgparseSkeleton -v
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py::TestApiFreeInvariantFinalize -v
```

Expected: ~5 tests pass.

### - [ ] **Step 5: Commit**

```bash
git add icu/scripts/finalize_consensus.py \
        icu/tests/unit/scripts/test_finalize_consensus.py
git commit -m "feat(coach-phase3): finalize_consensus.py argparse skeleton + dry-run default (T66.1)"
```

## T66.2 — Parse + validate + ledger append (rollback ordering)

**Goal.** Replace the `_append_to_ledger` `NotImplementedError` stub with a
real implementation that uses `LedgerWriter.record(...)` to append a single
`consensus_verdict` entry. Maintain the contract that **every step that
can raise must run BEFORE the writer is invoked**.

The hard rule: if any of `_read_response`, `_read_athlete_state`,
`json.loads`, `parse_council`, or `AthleteStateRef.model_validate` raises,
the ledger file must remain byte-identical to what it was before the
process started.

We test this by:

- pointing `--ledger` at a path with pre-seeded contents;
- running `finalize_main` with `--confirm` against a malformed response;
- asserting (a) the exit code is 2 and (b) `ledger_path.read_text()`
  equals the original byte-for-byte.

### - [ ] **Step 1: Write RED test**

Append to `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
# ---------- T66.2: parse + validate + append ----------

class TestParseValidateAppend:

    def test_confirm_appends_one_ledger_line(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        assert ledger.exists()
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["decision_type"] == "consensus_verdict"
        assert entry["source"] == "consensus.council"
        assert entry["payload"]["verdict"] == "REVISE"
        assert entry["payload"]["confidence"] == pytest.approx(0.78)
        # athlete_state_ref echoed back
        assert entry["athlete_state_ref"]["phase"] == "BUILD"
        assert entry["athlete_state_ref"]["ctl"] == pytest.approx(70.0)
        # evidence_refs hold the response path string
        assert any(str(resp) in r for r in entry["evidence_refs"])
        # confidence at top level matches verdict.confidence
        assert entry["confidence"] == pytest.approx(0.78)

    def test_malformed_response_does_not_touch_ledger(self, tmp_path,
                                                      capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"

        # malformed: only 2 sections, no <summary_json>
        resp.write_text(
            "<planner>p</planner>\n<critic>c</critic>\n",
            encoding="utf-8",
        )
        _write_state(state)
        # pre-seed the ledger with one prior entry
        prior_line = (
            '{"schema_version":1,"entry_id":"01HZZZ' + "0" * 20
            + '","timestamp":"2026-01-01T00:00:00+00:00","decision_type":'
            '"weekly_plan_assembled","source":"phase2","athlete_state_ref":'
            '{"ctl":50.0,"atl":50.0,"tsb":0.0,"w_prime":12000,'
            '"phase":"BUILD","week_of_year":1},"confidence":null,'
            '"payload":{},"evidence_refs":[],"superseded_by":null}\n'
        )
        ledger.write_text(prior_line, encoding="utf-8")
        before = ledger.read_text(encoding="utf-8")

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])

        assert rc == 2
        # rollback contract: file is byte-identical
        after = ledger.read_text(encoding="utf-8")
        assert after == before, (
            "Ledger file mutated despite parser violation — "
            "T66.2 rollback contract is broken"
        )
        err = capsys.readouterr().err
        assert "violation" in err.lower() or "missing" in err.lower()

    def test_invalid_json_summary_does_not_touch_ledger(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        # Replace the well-formed summary_json with broken JSON.
        bad = _HAPPY_RESPONSE.replace(
            '{"verdict": "REVISE", "confidence": 0.78}',
            '{"verdict": "REVISE", "confidence": ',
        )
        resp.write_text(bad, encoding="utf-8")
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists() or \
               ledger.read_text(encoding="utf-8") == ""

    def test_missing_athlete_state_file_exit_2(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        _write_response(resp)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(tmp_path / "absent.json"),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists()

    def test_athlete_state_schema_violation_exit_2(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        # bad shape: missing required fields
        state.write_text(json.dumps({"ctl": 70.0}), encoding="utf-8")
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists()

    def test_entry_id_is_valid_ulid(self, tmp_path):
        from src.coach.ledger.types import is_valid_ulid
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        entry = json.loads(ledger.read_text(encoding="utf-8").strip())
        assert is_valid_ulid(entry["entry_id"])

    def test_evidence_refs_contains_response_path(self, tmp_path):
        resp = tmp_path / "council.response.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        entry = json.loads(ledger.read_text(encoding="utf-8").strip())
        assert any("council.response.md" in r
                   for r in entry["evidence_refs"])
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py::TestParseValidateAppend -v
```

Expected error fragments:

```
NotImplementedError: T66.2 will implement ledger append; T66.1 only ships dry-run.
```

(for the happy-path test) and assertion failures on rollback tests
because Step 3 hasn't run yet.

### - [ ] **Step 3: Minimal implementation**

Replace the `_append_to_ledger` stub in
`icu/scripts/finalize_consensus.py` with the real body. Note: the read /
parse / validate phases already happen BEFORE this function in `main()`,
so by the time we get here every fallible step that touches user input is
already complete — the function only does (a) idempotency probe (T66.3
adds this; T66.2 leaves a placeholder pass-through) and (b)
`writer.record(...)`.

```python
def _append_to_ledger(
    verdict: CouncilVerdict,
    athlete_state: AthleteStateRef,
    evidence_path: Path,
    ledger_path: Path,
    content_hash: str,
) -> int:
    """Append one consensus_verdict entry to the ledger.

    Pre-conditions (must all be true before this function is reached):
      - response file was read successfully
      - athlete-state JSON parsed AND schema-validated
      - council response parsed via response_parser.parse — no violations

    On success: prints the new entry_id; returns 0.
    On IO failure during the actual write: prints to stderr, returns 3.
    """
    # T66.3 fills in: probe LedgerReader for content_hash, skip if dup.

    payload = verdict.model_dump()
    payload["content_hash"] = content_hash

    try:
        writer = LedgerWriter(ledger_path)
        entry_id = writer.record(
            decision_type="consensus_verdict",
            source="consensus.council",
            athlete_state=athlete_state,
            payload=payload,
            evidence_refs=[str(evidence_path)],
            confidence=verdict.confidence,
        )
    except Exception as exc:  # IO / fcntl / fsync failure
        print(f"ERROR: ledger write failed: {exc}", file=sys.stderr)
        return 3

    print(f"Appended consensus_verdict entry_id={entry_id} "
          f"(content_hash={content_hash[:12]}...)")
    return 0
```

Notes for the implementer:

- We embed `content_hash` inside `payload` so a future T66.3 LedgerReader
  scan can look for it without needing a separate field. The blueprint's
  `DecisionEntry` schema is open-ended on `payload: dict`, so this is
  schema-safe.
- `writer.record` itself uses `tempfile`/`os.replace` semantics via
  `fcntl.flock` (see File 01's `LedgerWriter` impl); a write failure will
  raise (IOError / OSError / fcntl error) — we catch broadly and exit 3.

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py -v
```

Expected: all T66.1 + T66.2 tests green.

### - [ ] **Step 5: Commit**

```bash
git add icu/scripts/finalize_consensus.py \
        icu/tests/unit/scripts/test_finalize_consensus.py
git commit -m "feat(coach-phase3): finalize_consensus parse+validate+append with rollback ordering (T66.2)"
```

## T66.3 — Idempotency (content-hash duplicate skip)

**Goal.** When the same response file is re-finalized (intentionally or
accidentally), the second invocation must be a NO-OP. We compute a
deterministic SHA-256 hash of the verdict's content (mode + verdict +
confidence + justification + summary_json + concatenated role bodies) and
embed it in `payload["content_hash"]`. Before each new append, scan the
ledger via `LedgerReader.query(decision_type="consensus_verdict")` and
look for any prior entry with the same `content_hash`. If found:

- Print `Already finalized: <hash>` and `existing entry_id=<...>`.
- Exit 0 without writing.

This matches the pattern File 02 (`ledger_ingester`) established for
weekly_plan_assembled: idempotency through content-hash inside `payload`.
We deliberately do NOT use a sidecar marker file; the ledger is the
single source of truth.

### - [ ] **Step 1: Write RED test**

Append to `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
# ---------- T66.3: idempotency ----------

class TestIdempotency:

    def test_second_confirm_does_not_double_append(self, tmp_path,
                                                    capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0

        # Second invocation — same content
        capsys.readouterr()  # drain
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        out = capsys.readouterr().out
        assert "Already finalized" in out
        # Ledger still has exactly one consensus_verdict line
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        cv_lines = [l for l in lines
                    if json.loads(l)["decision_type"] == "consensus_verdict"]
        assert len(cv_lines) == 1, (
            f"expected 1 consensus_verdict entry, got {len(cv_lines)}: "
            f"{cv_lines}"
        )

    def test_different_response_appends_new_entry(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_state(state)

        # First response: REVISE @0.78
        resp1 = tmp_path / "r1.md"
        _write_response(resp1, _HAPPY_RESPONSE)
        rc1 = finalize_main([
            "--response", str(resp1),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0

        # Second response: ACCEPT @0.92 (different summary_json)
        resp2 = tmp_path / "r2.md"
        body2 = _HAPPY_RESPONSE.replace(
            '{"verdict": "REVISE", "confidence": 0.78}',
            '{"verdict": "ACCEPT", "confidence": 0.92}',
        ).replace(
            "REVISE\nPlan needs",
            "ACCEPT\nPlan looks",
        )
        _write_response(resp2, body2)
        rc2 = finalize_main([
            "--response", str(resp2),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0

        # Two distinct consensus_verdict lines
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        cv_lines = [l for l in lines
                    if json.loads(l)["decision_type"] == "consensus_verdict"]
        assert len(cv_lines) == 2

    def test_dry_run_then_confirm_appends_once(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        # Dry-run first
        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        assert rc1 == 0
        assert not ledger.exists()

        # Confirm second
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_content_hash_is_stable(self, tmp_path):
        """Two CouncilVerdicts with identical content yield same hash."""
        from scripts.finalize_consensus import _content_hash
        from src.coach.consensus.response_parser import parse as parse_council

        v1 = parse_council(_HAPPY_RESPONSE, mode="council")
        v2 = parse_council(_HAPPY_RESPONSE, mode="council")
        assert _content_hash(v1) == _content_hash(v2)
        assert len(_content_hash(v1)) == 64  # sha256 hex
```

### - [ ] **Step 2: Run — fail**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py::TestIdempotency -v
```

Expected: `test_second_confirm_does_not_double_append` fails with the
ledger having 2 lines (because T66.2's `_append_to_ledger` doesn't yet
probe for duplicates). Other tests may pass incidentally.

### - [ ] **Step 3: Minimal implementation**

Replace `_append_to_ledger` in `icu/scripts/finalize_consensus.py` again
with this idempotent version:

```python
def _append_to_ledger(
    verdict: CouncilVerdict,
    athlete_state: AthleteStateRef,
    evidence_path: Path,
    ledger_path: Path,
    content_hash: str,
) -> int:
    """Append one consensus_verdict entry to the ledger (idempotent).

    Probes the existing ledger for a prior consensus_verdict entry with
    the same payload.content_hash. On hit: print + return 0 without
    writing. Otherwise: append normally.
    """
    # ---- idempotency probe ----
    if ledger_path.exists():
        try:
            reader = LedgerReader(ledger_path)
            existing = reader.query(
                decision_type="consensus_verdict",
                limit=None,
            )
        except Exception as exc:
            print(f"ERROR: ledger read for idempotency probe failed: {exc}",
                  file=sys.stderr)
            return 3
        for prior in existing:
            if prior.payload.get("content_hash") == content_hash:
                print(
                    f"Already finalized: content_hash={content_hash[:12]}... "
                    f"existing entry_id={prior.entry_id}"
                )
                return 0

    # ---- new append ----
    payload = verdict.model_dump()
    payload["content_hash"] = content_hash

    try:
        writer = LedgerWriter(ledger_path)
        entry_id = writer.record(
            decision_type="consensus_verdict",
            source="consensus.council",
            athlete_state=athlete_state,
            payload=payload,
            evidence_refs=[str(evidence_path)],
            confidence=verdict.confidence,
        )
    except Exception as exc:
        print(f"ERROR: ledger write failed: {exc}", file=sys.stderr)
        return 3

    print(f"Appended consensus_verdict entry_id={entry_id} "
          f"(content_hash={content_hash[:12]}...)")
    return 0
```

Note on `LedgerReader.query` semantics — confirmed with File 06 caller in
`history_injector.py`: `query()` returns a list (not iterator), accepts
`decision_type=...` kwarg, sorts ascending by `entry_id`, and `limit=None`
means "no cap". This matches `src/coach/ledger/reader.py` (verified
2026-04-27 against the FROZEN module).

### - [ ] **Step 4: Run — pass**

Run:

```
cd icu && .venv/bin/pytest tests/unit/scripts/test_finalize_consensus.py -v
cd icu && .venv/bin/pytest tests/unit/consensus/ -v
cd icu && .venv/bin/pytest tests/unit/scripts/test_run_consensus.py -v
```

Expected: all three runs green. Total new tests: ~50 (test_council_prompt
~38 + test_run_consensus ~9 + test_finalize_consensus ~17).

### - [ ] **Step 5: Commit**

```bash
git add icu/scripts/finalize_consensus.py \
        icu/tests/unit/scripts/test_finalize_consensus.py
git commit -m "feat(coach-phase3): finalize_consensus content-hash idempotency (T66.3)"
```

# Acceptance / smoke / rollback / open questions

## Acceptance criteria

A reviewer may close T65/T66 only when ALL of the following are true:

1. `cd icu && .venv/bin/pytest tests/unit/consensus/ tests/unit/scripts/
   -v` runs green. Each individual file:
   - `tests/unit/consensus/test_council_prompt.py` — ~38 tests
   - `tests/unit/scripts/test_run_consensus.py` — ~9 tests
   - `tests/unit/scripts/test_finalize_consensus.py` — ~17 tests
2. The 5 commits land in order:
   - T65.1: `feat(coach-phase3): consensus council_prompt 4-section assembler + VerdictRequest (T65.1)`
   - T65.2: `feat(coach-phase3): consensus 6 UNDER-DOSED trigger detector wired into Section A (T65.2)`
   - T65.3: `test(coach-phase3): pin Section C history-triplet rendering contract (T65.3)`
   - T65.4: `feat(coach-phase3): run_consensus.py CLI emits council prompt md (T65.4, API-free)`
   - T66.1: `feat(coach-phase3): finalize_consensus.py argparse skeleton + dry-run default (T66.1)`
   - T66.2: `feat(coach-phase3): finalize_consensus parse+validate+append with rollback ordering (T66.2)`
   - T66.3: `feat(coach-phase3): finalize_consensus content-hash idempotency (T66.3)`
3. No file outside the touch list (above) changed:
   - `git diff --stat master...ai-coach-phase-3 -- 'icu/src/coach/' 'icu/scripts/' 'icu/tests/'`
     shows only the 6 files in the touch list.
4. API-free invariant verified by grep:
   ```
   grep -R "google\.genai\|from google import genai\|import requests\|import urllib\|import httpx" \
       icu/src/coach/consensus/council_prompt.py \
       icu/scripts/run_consensus.py \
       icu/scripts/finalize_consensus.py
   ```
   returns empty.
5. `consensus_verdict` decision-type literal appears in
   `icu/src/coach/ledger/types.py` (lift-and-paste regression — must
   match File 06's existing whitelist).

## Smoke test (manual, optional)

After all 7 commits land, in `icu/`:

```bash
mkdir -p tests/fixtures/phase3/consensus

# 1. Generate a verdict-request JSON inline
.venv/bin/python - <<'PY'
import json, pathlib
req = {
  "plan": {
    "week_start": "2026-04-27","week_end": "2026-05-03",
    "focus_theme": "BUILD","weekly_tss_target": 525,
    "days": [
      {"day_of_week": d, "training_type": "Endurance",
       "name": "Z2","duration_min": 60, "target_tss": 50,
       "power_range_w": "150-180W", "tier": "MID"}
      for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    ],
    "recent_stimulus_scores": [0.55,0.55,0.55],
    "recent_w_prime_negatives": [3,3,3],
  },
  "athlete_state": {
    "ctl": 70.0, "atl": 68.0, "tsb": 2.0,
    "w_prime": 14500, "phase": "BUILD", "week_of_year": 17,
  },
  "physiology": {
    "cp_w": 285, "w_prime_j": 14500,
    "durability_index": 0.74,
    "response_profile": {"types": {}}, "knee_flag": "OK",
  },
  "wellness_trend": [],
  "periodization_summary": {"phase": "BUILD","weekly_tss_target": 525},
}
pathlib.Path("tests/fixtures/phase3/consensus/verdict_request_sample.json").write_text(
  json.dumps(req, indent=2), encoding="utf-8"
)
PY

# 2. Build the prompt
.venv/bin/python scripts/run_consensus.py \
    --verdict-request tests/fixtures/phase3/consensus/verdict_request_sample.json \
    --out /tmp/council.prompt.md
cat /tmp/council.prompt.md | head -60

# 3. Paste into Gemini, save reply to /tmp/council.response.md (manual)

# 4. Athlete state JSON
.venv/bin/python - <<'PY'
import json, pathlib
pathlib.Path("/tmp/state.json").write_text(json.dumps({
  "ctl": 70.0, "atl": 68.0, "tsb": 2.0,
  "w_prime": 14500, "phase": "BUILD", "week_of_year": 17,
}), encoding="utf-8")
PY

# 5. Dry-run
.venv/bin/python scripts/finalize_consensus.py \
    --response /tmp/council.response.md \
    --ledger /tmp/ledger.jsonl \
    --athlete-state /tmp/state.json

# 6. Confirm
.venv/bin/python scripts/finalize_consensus.py \
    --response /tmp/council.response.md \
    --ledger /tmp/ledger.jsonl \
    --athlete-state /tmp/state.json \
    --confirm

# 7. Re-run confirm — should print "Already finalized"
.venv/bin/python scripts/finalize_consensus.py \
    --response /tmp/council.response.md \
    --ledger /tmp/ledger.jsonl \
    --athlete-state /tmp/state.json \
    --confirm
```

## Rollback (if a step has to be undone)

To roll back T65/T66 cleanly without disturbing File 06:

```bash
# Identify the 7 commits
git log --oneline ai-coach-phase-3 -- \
    icu/src/coach/consensus/council_prompt.py \
    icu/scripts/run_consensus.py \
    icu/scripts/finalize_consensus.py \
    icu/tests/unit/consensus/test_council_prompt.py \
    icu/tests/unit/scripts/test_run_consensus.py \
    icu/tests/unit/scripts/test_finalize_consensus.py

# Revert in reverse order (T66.3 → T66.2 → T66.1 → T65.4 → T65.3 → T65.2 → T65.1)
git revert --no-edit <T66.3_sha>
git revert --no-edit <T66.2_sha>
git revert --no-edit <T66.1_sha>
git revert --no-edit <T65.4_sha>
git revert --no-edit <T65.3_sha>
git revert --no-edit <T65.2_sha>
git revert --no-edit <T65.1_sha>

# Verify File 06 modules are still intact
.venv/bin/pytest tests/unit/consensus/test_types.py \
                 tests/unit/consensus/test_response_parser.py \
                 tests/unit/consensus/test_history_injector.py
```

## Open questions / blueprint resolutions

The implementer may revisit these mid-task; otherwise treat them as locked.

1. **VerdictRequest lives where?** Blueprint §4.6 doesn't explicitly assign
   it. File 06's `types.py` deliberately covers only outputs of consensus
   (CouncilVerdict, ExpertTurn). The naming convention in 00-index.md says
   "all Pydantic models in `types.py`", but that rule has been bent
   already (`HistoryTriplet` lives in `history_injector.py`). For
   simplicity and because `VerdictRequest` is solely an input wrapper for
   the assembler, we colocate it in `council_prompt.py`. **Decision:
   locked.**
2. **TSS lower-band heuristic for T3.** Blueprint says "CTL 对应
   acceptable load band (低于下界 = UNDER-DOSED)" without numeric
   formula. We use `5.0 × CTL` as a Banister-derived rule of thumb (CTL is
   chronic load measured as 42-day exponentially-weighted TSS/day, so
   weekly TSS ≈ 7 × CTL is "perfect ramp"; 5 × CTL is the conservative
   floor). **Flagged: review against athlete profile in /mnt/d/Cycling
   Phase 1 once a real dataset arrives. May tune to 4.5 × CTL or 5.5 ×
   CTL based on observed under-trigger rate.**
3. **T2 work-minute proxy.** Blueprint specifies "VO2max/Threshold session
   工作间总时长 vs response_profile.types[<type>].tolerance_class". The
   detector uses `duration_min` from each `day` entry as a coarse proxy
   for "work-interval minutes" because the WeeklyPlan dict does NOT
   expose work/rest split. Conservative: this counts the whole session
   (warm-up + work + cool-down), so an 18-minute work block inside a
   75-minute session passes the trigger. **This is intentional —
   trigger 2 is a HINT, not a hard rule; the Critic role does the
   detailed audit on the LLM side.**
4. **`phase_match=True` default for history.** File 06's
   `history_injector.compress_history` uses `phase_match=True` and
   `ctl_tolerance=5.0` by default. T65.3 inherits these via the wired CLI
   step in T65.4 (the script doesn't expose flags for them; they hang off
   the underlying call's defaults). If a user later wants to bypass
   phase-match, they edit the CLI directly — out of scope for File 07.
5. **`--athlete-state` rather than re-reading from ledger.** We require
   the user pass the current snapshot file because `finalize_consensus`
   does not yet have a stable contract on "what's the latest snapshot".
   The Phase 2 snapshot lives at `coach_memory/physiology/snapshot.json`
   but isn't shaped as `AthleteStateRef`. T71 (File 09) will add a
   `_resolve_athlete_state(memory_dir)` helper that synthesises one — at
   that point this argument can become optional. **Locked for File 07.**
6. **Confidence cross-check vs verdict.** The parser already enforces
   confidence ∈ [0.0, 1.0]. We pass `confidence=verdict.confidence` at
   the top level of the ledger entry (matching the `DecisionEntry`
   schema's `confidence: float | None` field) AND retain it inside
   `payload["confidence"]` (because `payload = verdict.model_dump()`
   includes it). This is intentional duplication for two reasons: (a)
   downstream `query_similar` may filter on `confidence`; (b) historical
   payloads from `weekly_plan_assembled` lack a top-level confidence, so
   keeping payload self-contained makes JSON-only consumers work. **Not
   a contract-breaker.**

## End-of-file checkpoint

- [ ] All 7 commits landed (T65.1 → T66.3)
- [ ] `cd icu && .venv/bin/pytest tests/unit/consensus/
        tests/unit/scripts/ -v` is green
- [ ] `grep -R "google.genai" icu/src/coach/consensus/ icu/scripts/`
      returns empty
- [ ] No files modified outside the 6-item touch list
- [ ] `save-progress` updates bd + MEMORY
- [ ] End session. Next session opens
      [`08-strict-prompt.md`](./08-strict-prompt.md) (T67–T70:
      strict_prompt 4-step pipeline + integration with finalize_consensus
      `--mode strict`).

## Worktree bootstrap reminder (executor reads before Step 1 of T65.1)

This file lives on `/mnt/d/Cycling-phase3` (branch `ai-coach-phase-3`).
If executor is on a fresh worktree, copy `.venv` + `src/analyzer` +
`src/utils` + `src/fetcher` per the bootstrap step at the bottom of
`01-ledger-infrastructure.md`. `tests/fixtures/phase3/consensus/` was
created in File 06 — do not re-create. New fixtures (just
`verdict_request_sample.json`) are added optionally via the smoke section
above.

Subagent brief for File 07 (paste into the implementer agent's first
turn):

> Use `/mnt/d/Cycling-phase3/docs/superpowers/plans/phase-3/07-consensus-council.md`.
> Follow `superpowers:subagent-driven-development`. Execute T65.1 →
> T65.2 → T65.3 → T65.4 → T66.1 → T66.2 → T66.3 in strict order. For
> each task: (a) write the RED test, (b) run pytest from `icu/` and
> confirm it fails with the expected error fragment, (c) write the
> minimal implementation, (d) run pytest again and confirm green, (e)
> commit with the exact message in Step 5.
>
> **HARD constraints:**
> - No imports of `google.genai`, `requests`, `urllib`, `httpx`,
>   `aiohttp` anywhere in this file's deliverables.
> - Touch list (`docs/superpowers/plans/phase-3/07-consensus-council.md`
>   §"Touch list") is exhaustive — any file outside it that changes is a
>   bug.
> - File 06 modules (`src/coach/consensus/{types,response_parser,
>   history_injector}.py`) are FROZEN — IMPORT only.
> - Adapter, ledger writer/reader, deep_analyzer, periodization,
>   session_designer, physiology — all OFF LIMITS.
>
> **Pre-flight Pydantic+IO checklist** (also in the spec): re-read
> §"Pre-flight Pydantic+IO checklist" before any Pydantic model.
>
> Report back with: (a) commit SHAs of all 7 commits, (b) `pytest -v`
> tail, (c) any deviation from the spec and reason.
