# Phase 3 — Consensus strict 4-step prompt + finalize state machine (Tasks T67–T68)

> **Path note:** Plan files at `/mnt/d/Cycling-phase3/docs/superpowers/plans/phase-3/`;
> source under `/mnt/d/Cycling-phase3/icu/`. Code-block paths are
> relative to `/mnt/d/Cycling-phase3/icu/`.

> **Milestone:** **M2** (per `00-index.md` line 36). File 08 does NOT
> block Phase 3 M1 release — M1 ships once Files 01–07 + File 09 are
> green. File 08 unlocks the strict 4-step council mode.

## Mission

Build the **strict-mode prompt assembler** (T67) and extend the
**finalize ledger CLI** with a 4-step state machine (T68) on top of
FROZEN File 06 infrastructure and FROZEN-for-M1 File 07 council mode.

- `run_consensus.py --mode strict [--reuse <dir>]` emits
  `1_planner.prompt.md`; `finalize_consensus.py --mode strict --step
  {2,3,4} --consensus-dir <dir>` emits each next role's prompt embedding
  prior replies. Step 4 with `--confirm` concats + parses (mode="strict")
  + appends ledger.
- Concat goes through File 06's `parse(response_md, mode="strict")`
  unchanged. `_council_requires_four_roles` only fires for
  `mode="council"`; concat has all 4 tags by construction, so behavior
  is consistent (regression-pinned in T68.3).
- Ledger: `decision_type="consensus_verdict"`,
  `source="consensus.strict"`, `payload.mode="strict"`,
  `payload.content_hash` over concat.

API_FREE invariant: no LLM SDK import, no network. File IO, regex,
JSON, ledger writes only.

## Out of scope

- Phase 1/2 internals (PHASE_1_2_IMMUTABILITY locked).
- File 06 modules (`types.py`, `response_parser.py`,
  `history_injector.py`) are FROZEN — File 08 imports only. Do NOT add
  a `mode` literal, do NOT change `_council_requires_four_roles`, do
  NOT add a strict branch to `parse(...)` — strict is first-class via
  the existing `mode="strict"` kwarg.
- File 07's `council_prompt.py` is FROZEN — re-import private
  `_section_b` / `_section_c` (OQ4 locked NO on promotion). File 08
  may extend `run_consensus.py` and `finalize_consensus.py` with new
  flags; council-mode regression must stay green.
- Adapter (03–05) / Ledger (01–02) modules: import only.
- Auto-trigger of strict mode (RED_NO_AUTO_ESCALATE locked).
- `ledger_digest.py` (also M2 but SEPARATE task).
- Any Pydantic / Phase-2 model changes.

## Inputs (read-only contracts)

These files exist before you start; touching them is a hard violation.

| Path | What you use from it |
|---|---|
| `src/coach/consensus/types.py` | `CouncilVerdict`, `ExpertTurn`, `ConsensusValidationError`, `EXPERT_ROLES` (`("planner", "critic", "physiologist", "arbiter")`), `VERDICTS`, `MODES` literals, `Mode` literal |
| `src/coach/consensus/response_parser.py` | `parse(response_md, *, mode="council"\|"strict")` — raises `ConsensusValidationError(violations: list[str])` on any of 6 hard-rule failures. **Used as-is** for the concatenated 4-step body. |
| `src/coach/consensus/history_injector.py` | `HistoryTriplet` model, `OUTCOME_PENDING` constant. (Strict mode does NOT need `compress_history` — history is read from disk verbatim if a `history.json` already exists in the reused consensus dir.) |
| `src/coach/consensus/council_prompt.py` | `VerdictRequest` (frozen Pydantic, holds `plan` / `athlete_state` / `physiology` / `wellness_trend` / `periodization_summary`); `build_council_prompt`; private builders `_section_b(request)`, `_section_c(history)`, `_section_d()`; `detect_under_dosed_triggers(plan, athlete_state)` — strict mode reuses the same trigger list, embedded only in Critic step (step 2). |
| `src/coach/ledger/types.py` | `DecisionEntry`, `AthleteStateRef`, `DecisionType`, `generate_ulid`, `is_valid_ulid`. `"consensus_verdict"` is in the whitelist (verified 2026-04-27). |
| `src/coach/ledger/writer.py` | `LedgerWriter(path).record(decision_type=..., source=..., athlete_state=..., payload=..., evidence_refs=..., confidence=..., superseded_by=...)` returns the ULID `entry_id`. |
| `src/coach/ledger/reader.py` | `LedgerReader(path)` with `.query(...)` — used only for the idempotency probe (re-uses File 07's `_append_to_ledger` helper). |
| `src/coach/common/logging.py` | `get_logger("consensus") -> JSONLLogger` with `.event(action, **extra)`. |

The File 07 scripts that File 08 EXTENDS:

| Path | What File 08 changes |
|---|---|
| `scripts/run_consensus.py` | T67.3 adds `--mode {council,strict}`, `--reuse <dir>`. Council-mode default unchanged. |
| `scripts/finalize_consensus.py` | T68.1–T68.3 add `--mode strict`, `--step {2,3,4}`, `--consensus-dir <dir>` and the strict state-machine helpers. Existing council-mode CLI surface unchanged. |

## Outputs (what gets created or extended)

```
icu/src/coach/consensus/
├── strict_prompt.py        ← T67.1 + T67.2 (NEW, ~310 lines impl)
└── (everything else FROZEN — File 06 + File 07's council_prompt.py)

icu/scripts/
├── run_consensus.py        ← T67.3 (EXTEND: ~80 added lines)
└── finalize_consensus.py   ← T68.1 + T68.2 + T68.3 (EXTEND: ~350 added lines)

icu/tests/unit/consensus/
└── test_strict_prompt.py   ← T67.1 + T67.2 (NEW, ~22 tests)

icu/tests/unit/scripts/
├── test_run_consensus.py        ← T67.3 (EXTEND: ~9 new tests)
└── test_finalize_consensus.py   ← T68.1 + T68.2 + T68.3 (EXTEND: ~34 new tests)

icu/tests/fixtures/phase3/consensus/
├── verdict_request.json    ← REUSE existing File 07 fixture if present;
│                             create if absent (see T67.3 step 1).
├── history.json            ← REUSE existing File 07 fixture (optional).
└── strict/                 ← NEW fixture sub-tree
    ├── 1_planner.response.md
    ├── 2_critic.response.md
    ├── 3_physiologist.response.md
    └── 4_arbiter.response.md
```

## Decision-type contract

Hardcoded throughout T68:

- `decision_type = "consensus_verdict"` — same literal as File 07. The
  ledger does **NOT** distinguish council vs strict at the
  `decision_type` level; the discriminator lives in `source` and
  `payload.mode`.
- `source = "consensus.strict"` (lowercase, dot-separated; symmetric with
  File 07's `consensus.council`).
- `payload = verdict.model_dump()` — i.e. the full `CouncilVerdict`
  Pydantic dump from `parse(..., mode="strict")`. Includes
  `mode == "strict"`, `verdict`, `confidence`, `justification`,
  `expert_turns` (list of dicts), `summary_json` (dict).
  `payload["content_hash"] = sha256(concatenated_body)` is appended after
  `model_dump()` — symmetric with File 07.
- `evidence_refs = [<all 4 response file paths as strings>]`. Path
  ordering: planner, critic, physiologist, arbiter (the natural step
  order). The concatenated synthetic file is **not** persisted to disk —
  it is built in memory during step-4 finalize and discarded after parser
  acceptance. See Open Question 5 (locked NO, no on-disk concat artefact).
- `confidence = verdict.confidence` (the float from the parser, already
  validated to `[0.0, 1.0]`).
- `superseded_by = None`.
- Idempotency: same `_content_hash(verdict)` helper as File 07 — but the
  hash domain naturally differs because `verdict.mode == "strict"` flips
  the first key. Re-running step-4 `--confirm` on the same response
  files hits the existing-entry branch and prints `"Already finalized"`.

## Touch list (do not exceed)

```
icu/src/coach/consensus/strict_prompt.py                (CREATE)
icu/scripts/run_consensus.py                            (EDIT — add flags)
icu/scripts/finalize_consensus.py                       (EDIT — add state machine)
icu/tests/unit/consensus/test_strict_prompt.py          (CREATE)
icu/tests/unit/scripts/test_run_consensus.py            (EDIT — add strict tests)
icu/tests/unit/scripts/test_finalize_consensus.py       (EDIT — add strict tests)
icu/tests/fixtures/phase3/consensus/strict/1_planner.response.md       (CREATE)
icu/tests/fixtures/phase3/consensus/strict/2_critic.response.md        (CREATE)
icu/tests/fixtures/phase3/consensus/strict/3_physiologist.response.md  (CREATE)
icu/tests/fixtures/phase3/consensus/strict/4_arbiter.response.md       (CREATE)
```

Anything else (especially `src/coach/consensus/types.py`,
`response_parser.py`, `history_injector.py`, `council_prompt.py`,
anything under `src/coach/ledger/`, anything under `src/coach/adapter/`,
`src/coach/deep_analyzer/`, `src/coach/physiology/`,
`src/coach/periodization/`, `src/coach/session_designer/`) is OFF LIMITS.

`git diff --stat` regression after the final commit must show **exactly**
the 10 paths above and no others.

## Pre-flight Pydantic+IO checklist

Lifted verbatim from File 07; same 9 items, paste into implementer
brief. Fail-fast quality gates.

1. **Frozen Pydantic models.** File 08 adds NONE — reuses frozen
   `VerdictRequest` (council_prompt.py) + `HistoryTriplet`
   (history_injector.py). Adding a new BaseModel in strict_prompt.py is
   almost certainly wrong; stop and ask.
2. **Explicit field types**, no bare `Any`; `dict[str, Any]` with a
   note when truly needed.
3. **No `Optional[T]`** — use `T | None` + explicit `default=None`.
   Never `from typing import Optional`.
4. **UTF-8 explicit** on every read/write/open.
5. **`pathlib.Path`** over `os.path`; compose with `dir / "name.md"`.
6. **Stable JSON** dumps: `indent=2, sort_keys=True, ensure_ascii=False`.
   Ledger entries via `LedgerWriter.model_dump_json()` (already stable).
7. **Timezone-aware timestamps**: `datetime.now(timezone.utc)`. Never
   `utcnow()`.
8. **Immutable defaults**: `default_factory=list/dict`. The
   `build_strict_prompt` signature uses `prior_responses=None` (not
   `{}`).
9. **Explicit CLI exit codes**: `0` success / `2` input error / `3`
   IO error. Catch at `main()` boundary; never let exceptions bubble.

## Architectural map

```
run_consensus.py --mode strict [--reuse <dir>]
  → 1_planner.prompt.md
  → user pastes 1_planner.response.md
finalize_consensus.py --mode strict --step 2 --consensus-dir X
  reads 1_planner.response.md
  build_strict_prompt(step=2, prior_responses={"planner": ...})
  → 2_critic.prompt.md
... (steps 3, 4-build same shape) ...
finalize_consensus.py --mode strict --step 4 --confirm
  --athlete-state ... --ledger ...
  reads all 4 *_<role>.response.md, concatenates
  parse_council(synth, mode="strict") → CouncilVerdict
  idempotency probe (content_hash); LedgerWriter.record(
    source="consensus.strict", payload.mode="strict")
  writes strict_verdict.md
```

# Task 67 — strict_prompt builder + run_consensus integration

T67 builds the strict prompt assembler that takes a step number, a
`VerdictRequest`, optional history, and any prior expert responses, and
returns a single-role markdown prompt the user pastes into Gemini. It
also extends `scripts/run_consensus.py` with `--mode strict` and
`--reuse <dir>`.

T67 does NOT call any LLM. The CLI's only side-effect is writing one or
more markdown files (the prompt for the current step + the persisted
inputs for `--reuse`).

T67 splits into 3 RED → GREEN cycles:

- **T67.1** — `STRICT_STEP_TO_ROLE` constant + `build_strict_prompt(step=1, ...)`
  for the Planner-only prompt (no priors).
- **T67.2** — `build_strict_prompt(step=2|3|4, ...)` — adds Critic,
  Physiologist, Arbiter steps with prior-response embedding.
- **T67.3** — extend `scripts/run_consensus.py` with `--mode strict` and
  `--reuse <dir>`; emit `1_planner.prompt.md`; persist `verdict_request.json`
  + optional `history.json` into the consensus dir (so a future
  `--reuse` invocation can find them).

## T67.1 — strict_prompt skeleton + Planner step

**Goal.** Stand up `src/coach/consensus/strict_prompt.py` with:

- `STRICT_STEP_TO_ROLE: dict[int, str] = {1: "planner", 2: "critic",
  3: "physiologist", 4: "arbiter"}` module-level constant.
- `build_strict_prompt(step: int, request: VerdictRequest,
  history: list[HistoryTriplet] | None = None,
  prior_responses: dict[str, str] | None = None) -> str` public entry.
- `_section_a_for_role(role: str, triggers: list[str]) -> str` —
  role-specific hard rules. Reuses the same hard-rule text from
  `council_prompt._section_a` but only for that one role; UNDER-DOSED
  triggers appear ONLY when `role == "critic"`.
- `_section_d_for_role(role: str) -> str` — single-role output schema;
  for `role == "arbiter"` includes the `<summary_json>` block; for the
  other 3 roles, only the role tag + free body.
- `_render_prior_responses(prior_responses: dict[str, str]) -> str` —
  formats embedded prior responses as fenced markdown.
- For step=1: assert `prior_responses is None or empty dict`; raise
  `ValueError("step=1 cannot accept prior_responses")` otherwise.

The four section ordering for strict step 1 (Planner) is:

1. Section A_step1 — Planner role + hard rules ONLY (no Critic /
   Physiologist / Arbiter rules; no UNDER-DOSED triggers).
2. (no prior responses block — step 1 has no priors)
3. Section B — `_section_b(request)` imported verbatim from
   `council_prompt`.
4. Section C — `_section_c(history or [])` imported verbatim from
   `council_prompt`.
5. Section D_step1 — single `<planner>...</planner>` schema only.

**Estimated impl size:** ~150 lines (including imports, constant,
docstrings, and three private builders).

### Step 1 — Write RED test

Create `icu/tests/unit/consensus/test_strict_prompt.py`:

```python
"""T67.1 RED — strict_prompt skeleton + step 1 (Planner-only)."""
from __future__ import annotations

import pytest

from src.coach.consensus.council_prompt import VerdictRequest
from src.coach.consensus.history_injector import HistoryTriplet
from src.coach.ledger.types import AthleteStateRef


def _make_request() -> VerdictRequest:
    return VerdictRequest(
        plan={"plan_period": "2026-W17", "weekly_tss_target": 380,
              "days": [
                  {"day": "Mon", "training_type": "Endurance",
                   "duration_min": 90, "tier": "MEDIUM"},
                  {"day": "Wed", "training_type": "VO2max",
                   "duration_min": 75, "tier": "HIGH"},
                  {"day": "Sat", "training_type": "Threshold",
                   "duration_min": 90, "tier": "HIGH"}]},
        athlete_state=AthleteStateRef(
            ctl=68.0, atl=72.0, tsb=-4.0,
            w_prime=18000, phase="BUILD", week_of_year=17),
        physiology={"cp_watts": 288, "w_prime_joules": 18000},
        wellness_trend=[{"date": "2026-04-26", "hrv": 72}],
        periodization_summary={"phase": "BUILD"},
    )


def test_strict_step_to_role_constant_locked() -> None:
    from src.coach.consensus.strict_prompt import STRICT_STEP_TO_ROLE
    assert STRICT_STEP_TO_ROLE == {
        1: "planner", 2: "critic",
        3: "physiologist", 4: "arbiter",
    }


def test_build_strict_prompt_is_callable() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert isinstance(out, str) and out.strip()


def test_step1_contains_planner_role_only_in_section_a() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "<planner>" in out
    assert "Critic (`<critic>`)" not in out
    assert "Physiologist (`<physiologist>`)" not in out
    assert "Arbiter (`<arbiter>`)" not in out


def test_step1_section_b_reused_from_council_prompt() -> None:
    """Section B identical to council mode (verbatim re-import)."""
    from src.coach.consensus import council_prompt as cp_mod
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert cp_mod._section_b(_make_request()) in out


def test_step1_section_c_empty_when_no_history() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "(no historical context)" in out


def test_step1_section_c_renders_history_when_provided() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    triplets = [HistoryTriplet(
        plan_entry_id="01HXYZABCD0123456789ABCDEF",
        context={"ctl": 65, "phase": "BUILD"},
        verdict="ACCEPT", outcome="consensus.ACCEPT@0.78")]
    out = build_strict_prompt(step=1, request=_make_request(),
                              history=triplets)
    assert "01HXYZABCD0123456789ABCDEF" in out


def test_step1_section_d_planner_schema_only() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "<planner>" in out and "</planner>" in out
    assert "<summary_json>" not in out
    assert "<arbiter>" not in out
    assert "<critic>" not in out
    assert "<physiologist>" not in out


def test_step1_no_under_dosed_triggers_in_planner() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "UNDER-DOSED" not in out
    assert "under_dosed" not in out


def test_invalid_step_rejected() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    for bad in (0, -1, 5, 99):
        with pytest.raises(ValueError) as exc:
            build_strict_prompt(step=bad, request=_make_request())
        assert "step" in str(exc.value).lower()


def test_step1_rejects_prior_responses() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    with pytest.raises(ValueError):
        build_strict_prompt(step=1, request=_make_request(),
                            prior_responses={"planner": "<planner>x</planner>"})


def test_step1_accepts_empty_prior_responses() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request(),
                              prior_responses={})
    assert "<planner>" in out
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/consensus/test_strict_prompt.py -v
```

Expected first failure (10 collected, 10 errors):
`ImportError: cannot import name 'STRICT_STEP_TO_ROLE' from 'src.coach.consensus.strict_prompt'`
or, depending on collection order:
`ModuleNotFoundError: No module named 'src.coach.consensus.strict_prompt'`

### Step 3 — Minimal implementation

Create `icu/src/coach/consensus/strict_prompt.py`:

```python
"""Strict-mode 4-step prompt assembler — one role per step.

Strict 模式 vs council：Section B/C 完全复用 council_prompt 的私有 builder；
只有 Section A（角色硬规则）和 Section D（输出 schema）按当前 step 拆成单一 role。
API_FREE：仅字符串拼装；不调用任何 LLM SDK。
"""
from __future__ import annotations

from src.coach.common.logging import get_logger
from src.coach.consensus.council_prompt import (
    VerdictRequest, _section_b, _section_c,
    detect_under_dosed_triggers,
)
from src.coach.consensus.history_injector import HistoryTriplet

_log = get_logger("consensus")

STRICT_STEP_TO_ROLE: dict[int, str] = {
    1: "planner", 2: "critic",
    3: "physiologist", 4: "arbiter",
}
_VALID_STEPS: frozenset[int] = frozenset(STRICT_STEP_TO_ROLE.keys())


def build_strict_prompt(
    step: int,
    request: VerdictRequest,
    history: list[HistoryTriplet] | None = None,
    prior_responses: dict[str, str] | None = None,
) -> str:
    """Return a single-role markdown prompt body for `step`."""
    if step not in _VALID_STEPS:
        raise ValueError(
            f"step must be one of {sorted(_VALID_STEPS)}, got {step!r}")
    if step == 1 and prior_responses:
        raise ValueError(
            "step=1 cannot accept prior_responses (Planner has no priors)")

    role = STRICT_STEP_TO_ROLE[step]
    triggers: list[str] = []
    if role == "critic":
        triggers = detect_under_dosed_triggers(
            request.plan, request.athlete_state.model_dump())

    parts: list[str] = [_section_a_for_role(role, triggers)]
    if step >= 2:
        parts.append(_render_prior_responses(prior_responses or {}))
    parts.append(_section_b(request))
    parts.append(_section_c(history or []))
    parts.append(_section_d_for_role(role))

    body = "\n\n".join(parts).strip() + "\n"
    _log.event("strict_prompt_built", step=step, role=role,
               n_under_dosed_triggers=len(triggers),
               n_history_triplets=len(history or []),
               n_prior_responses=len(prior_responses or {}))
    return body


# ---------- section builders ----------

# Per-role hard-rule text — keep BYTE-IDENTICAL to the role bullet
# blocks in council_prompt._section_a (lockstep wording).
_ROLE_RULES: dict[str, str] = {
    "planner": (
        "### Planner (`<planner>`)\n"
        "- Restate the weekly plan day-by-day with the prescribed "
        "power, duration, and intent for each session.\n"
        "- Cite at least 2 numerical justifications drawn from Section B.\n"
    ),
    "critic": (
        "### Critic (`<critic>`)\n"
        "- Produce at LEAST 3 independent objection points the Planner "
        "did NOT raise.\n"
        "- Every point must include a numeric data citation "
        "(W, bpm, min, %, kJ/J or `field=value`).\n"
        "- Run the 6-item UNDER-DOSED checklist; report each item "
        "OK / UNDER-DOSED with reasoning.\n"
    ),
    "physiologist": (
        "### Physiologist (`<physiologist>`)\n"
        "- Cite ≥3 of {CP, W', durability, response_profile} in your body.\n"
        "- Provide a quantitative end-of-week W' balance estimate.\n"
        "- Call out knee_flag status explicitly.\n"
    ),
    "arbiter": (
        "### Arbiter (`<arbiter>`)\n"
        "- First line: ACCEPT / REVISE / REJECT.\n"
        "- Then a one-sentence justification.\n"
        "- For REVISE: enumerate every change as `(day, from, to)` triples.\n"
        "- The `<summary_json>` block must echo `verdict` + "
        "`confidence ∈ [0.0, 1.0]` consistent with this first line.\n"
    ),
}


def _section_a_for_role(role: str, triggers: list[str]) -> str:
    base = (
        "## Section A — Role & Hard Rules (strict mode)\n\n"
        f"You are the **{role.upper()}** in a 4-step expert council. "
        "Other roles respond in subsequent steps. Stay strictly within "
        "your role's scope and rules below.\n\n"
        f"{_ROLE_RULES[role]}"
    )
    if role == "critic" and triggers:
        bullet_list = "\n".join(f"- {t}" for t in triggers)
        base += (
            "\n### UNDER-DOSED HYPOTHESIS — auto-fired triggers\n"
            "Examine each and either confirm or refute with data:\n"
            f"{bullet_list}\n"
        )
    return base


def _render_prior_responses(prior_responses: dict[str, str]) -> str:
    """T67.1 ships an empty stub; T67.2 fills it in."""
    if not prior_responses:
        return ""
    rows: list[str] = []
    for role in ("planner", "critic", "physiologist"):
        body = prior_responses.get(role)
        if not body:
            continue
        rows.append(
            f"### Prior {role.capitalize()} response (verbatim)\n\n"
            f"```markdown\n{body.strip()}\n```\n"
        )
    if not rows:
        return ""
    return (
        "## Prior Expert Responses\n\n"
        "Verbatim replies from earlier strict steps. Treat as "
        "authoritative inputs to your own role.\n\n"
        + "\n".join(rows)
    )


def _section_d_for_role(role: str) -> str:
    if role == "arbiter":
        return (
            "## Section D — Output Schema (Arbiter)\n\n"
            "Emit, in this exact order:\n\n"
            "```\n"
            "<arbiter>\n"
            "ACCEPT|REVISE|REJECT\n"
            "...one-line justification...\n"
            "</arbiter>\n\n"
            "<summary_json>\n"
            '{"verdict": "ACCEPT|REVISE|REJECT", "confidence": 0.0}\n'
            "</summary_json>\n"
            "```\n\n"
            "Hard rules at step-4 finalize:\n"
            "- `<summary_json>` valid JSON object.\n"
            "- `verdict` ∈ ACCEPT / REVISE / REJECT.\n"
            "- `confidence` ∈ [0.0, 1.0].\n"
            "- Arbiter body first line must match summary_json verdict.\n"
        )
    return (
        f"## Section D — Output Schema ({role.capitalize()})\n\n"
        "Emit, in this exact order:\n\n"
        f"```\n<{role}>\n...your {role} body...\n</{role}>\n```\n\n"
        "Hard rules:\n"
        f"- `<{role}>` tag exactly once, non-empty.\n"
        "- Stay within your role's scope (see Section A).\n"
    )
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/consensus/test_strict_prompt.py -v
```

Expected: `10 passed`.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/src/coach/consensus/strict_prompt.py \
          icu/tests/unit/consensus/test_strict_prompt.py && \
  git commit -m "feat(coach-phase3): T67.1 strict_prompt skeleton + step 1 (Planner)"
```

## T67.2 — Critic / Physiologist / Arbiter steps + prior-response embedding

**Goal.** Wire `build_strict_prompt(step=2|3|4, ...)`. The remaining
three steps share the same shape but differ in:

- which `_ROLE_RULES[role]` block goes into Section A_step;
- which prior responses must be present in `prior_responses`;
- whether UNDER-DOSED triggers fire (only step 2);
- whether `<summary_json>` schema appears in Section D_step (only step 4).

**Prior-response requirements** (validated explicitly):

- step=2: must include `"planner"`.
- step=3: must include `"planner"` and `"critic"`.
- step=4: must include `"planner"`, `"critic"`, and `"physiologist"`.

Missing required priors → `ValueError` with the missing role name.
Extra keys outside the {planner, critic, physiologist} set → `ValueError`
(no Arbiter prior in any step; that's a programmer bug).

**Estimated impl size:** ~150 added lines (validators + a small
dispatcher inside `build_strict_prompt`; the section builders themselves
are already in T67.1 and just need to be exercised for the new roles).

### Step 1 — Write RED test

Append to `icu/tests/unit/consensus/test_strict_prompt.py`:

```python
# ============================================================
# T67.2 — steps 2 / 3 / 4
# ============================================================

_PLANNER_BODY = "<planner>\n- Wed: VO2max 75min @ CP=288W\n</planner>\n"
_CRITIC_BODY = (
    "<critic>\n1. tss=380 < 5*ctl=340.\n"
    "2. work=20min < 25min.\n3. no race-sim.\n</critic>\n"
)
_PHYS_BODY = (
    "<physiologist>\nCP=288W, W'=18000J durability=0.92 "
    "response_profile OK; knee_flag=false.\n</physiologist>\n"
)


def _bsp(step: int, **kw):
    from src.coach.consensus.strict_prompt import build_strict_prompt
    return build_strict_prompt(step=step, request=_make_request(), **kw)


def test_step2_requires_planner_prior() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(2, prior_responses={})
    assert "planner" in str(exc.value).lower()


def test_step2_embeds_planner_response() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "Prior Planner response" in out
    assert "Wed: VO2max 75min" in out


def test_step2_section_a_critic_only() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "Critic (`<critic>`)" in out
    assert "Planner (`<planner>`)" not in out
    assert "Physiologist (`<physiologist>`)" not in out
    assert "Arbiter (`<arbiter>`)" not in out


def test_step2_under_dosed_triggers_present_for_critic() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "UNDER-DOSED HYPOTHESIS" in out


def test_step2_section_d_critic_only_no_summary_json() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "<critic>" in out
    assert "<summary_json>" not in out


def test_step3_requires_planner_and_critic() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(3, prior_responses={"planner": _PLANNER_BODY})
    assert "critic" in str(exc.value).lower()


def test_step3_embeds_planner_and_critic_priors() -> None:
    out = _bsp(3, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "Prior Planner response" in out
    assert "Prior Critic response" in out
    assert "tss=380" in out


def test_step3_no_under_dosed_triggers() -> None:
    out = _bsp(3, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "UNDER-DOSED HYPOTHESIS" not in out


def test_step4_requires_all_three_priors() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(4, prior_responses={
            "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "physiologist" in str(exc.value).lower()


def test_step4_embeds_all_three_priors() -> None:
    out = _bsp(4, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
        "physiologist": _PHYS_BODY})
    assert "Prior Planner response" in out
    assert "Prior Critic response" in out
    assert "Prior Physiologist response" in out


def test_step4_section_d_arbiter_with_summary_json() -> None:
    out = _bsp(4, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
        "physiologist": _PHYS_BODY})
    assert "<arbiter>" in out
    assert "<summary_json>" in out
    assert "ACCEPT|REVISE|REJECT" in out


def test_step4_rejects_arbiter_in_prior_responses() -> None:
    """Arbiter is the OUTPUT, never a prior input."""
    with pytest.raises(ValueError) as exc:
        _bsp(4, prior_responses={
            "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
            "physiologist": _PHYS_BODY,
            "arbiter": "<arbiter>oops</arbiter>"})
    assert "arbiter" in str(exc.value).lower()
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/consensus/test_strict_prompt.py -v
```

Expected first failure (10 prior tests still pass; 12 new tests fail):
`Failed: DID NOT RAISE <class 'ValueError'>`
(because `build_strict_prompt(step=2, ..., prior_responses={})` currently
proceeds without checking required priors).

### Step 3 — Minimal implementation

REPLACE the existing `build_strict_prompt` body in
`src/coach/consensus/strict_prompt.py` with the version below (adds
`_validate_prior_responses` call before `parts.append`):

```python
# ADD constants + _validate_prior_responses (after STRICT_STEP_TO_ROLE):

_STEP_REQUIRED_PRIORS: dict[int, frozenset[str]] = {
    1: frozenset(),
    2: frozenset({"planner"}),
    3: frozenset({"planner", "critic"}),
    4: frozenset({"planner", "critic", "physiologist"}),
}
# Arbiter is OUTPUT, never an input role.
_ALLOWED_PRIOR_KEYS: frozenset[str] = frozenset(
    {"planner", "critic", "physiologist"})


def _validate_prior_responses(
    step: int, prior_responses: dict[str, str] | None,
) -> dict[str, str]:
    pr = prior_responses or {}
    if step == 1:
        if pr:
            raise ValueError(
                "step=1 cannot accept prior_responses")
        return {}
    extra = set(pr) - _ALLOWED_PRIOR_KEYS
    if extra:
        raise ValueError(
            f"prior_responses disallowed keys: {sorted(extra)}; "
            f"only {sorted(_ALLOWED_PRIOR_KEYS)} valid")
    missing = _STEP_REQUIRED_PRIORS[step] - set(pr)
    if missing:
        raise ValueError(
            f"step={step} requires {sorted(_STEP_REQUIRED_PRIORS[step])}; "
            f"missing {sorted(missing)}")
    blanks = [k for k, v in pr.items() if not (v or "").strip()]
    if blanks:
        raise ValueError(f"prior_responses blank: {sorted(blanks)}")
    return dict(pr)


# REPLACE build_strict_prompt to call the validator:

def build_strict_prompt(
    step: int,
    request: VerdictRequest,
    history: list[HistoryTriplet] | None = None,
    prior_responses: dict[str, str] | None = None,
) -> str:
    if step not in _VALID_STEPS:
        raise ValueError(
            f"step must be one of {sorted(_VALID_STEPS)}, got {step!r}")
    priors = _validate_prior_responses(step, prior_responses)

    role = STRICT_STEP_TO_ROLE[step]
    triggers: list[str] = []
    if role == "critic":
        triggers = detect_under_dosed_triggers(
            request.plan, request.athlete_state.model_dump())

    parts: list[str] = [_section_a_for_role(role, triggers)]
    if step >= 2:
        parts.append(_render_prior_responses(priors))
    parts.append(_section_b(request))
    parts.append(_section_c(history or []))
    parts.append(_section_d_for_role(role))

    body = "\n\n".join(parts).strip() + "\n"
    _log.event("strict_prompt_built", step=step, role=role,
               n_under_dosed_triggers=len(triggers),
               n_history_triplets=len(history or []),
               n_prior_responses=len(priors))
    return body
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/consensus/test_strict_prompt.py -v
```

Expected: `22 passed`.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/src/coach/consensus/strict_prompt.py \
          icu/tests/unit/consensus/test_strict_prompt.py && \
  git commit -m "feat(coach-phase3): T67.2 strict steps 2-4 + prior-response embedding"
```

## T67.3 — extend run_consensus.py with `--mode strict` + `--reuse <dir>`

**Goal.** Extend `scripts/run_consensus.py` to:

- accept `--mode {council,strict}` (default `council`); preserves existing
  council behavior bit-for-bit.
- when `--mode strict --reuse <consensus_dir>` is given:
  - read `verdict_request.json` from `<dir>` (required); read
    `history.json` from `<dir>` (optional, missing → empty history);
  - emit `1_planner.prompt.md` into `<dir>` (NOT `--out`; ignore `--out`
    when `--reuse` is set, with a warning if conflict).
- when `--mode strict` WITHOUT `--reuse`:
  - require `--verdict-request` (same as council mode);
  - emit `1_planner.prompt.md` into `--out` (default
    `coach_memory/consensus/<YYYY-MM-DD_HHMM>/1_planner.prompt.md`);
  - **also** persist the verdict-request + history into the consensus
    dir as `verdict_request.json` + `history.json` so a future
    `--reuse <dir>` invocation can find them.
- when `--mode council` (default): EVERY existing behavior is preserved.
  Council mode also gains the "persist inputs" behavior (writes
  `verdict_request.json` + optional `history.json` next to
  `council.prompt.md`) so the user can later flip to strict mode via
  `--reuse <dir>` without re-fetching the inputs. See Open Question 1
  for the rationale.
- print updated NEXT_STEPS for strict mode pointing the user at
  `finalize_consensus.py --mode strict --step 2 --consensus-dir <dir>`.

**Estimated impl size:** ~80 added lines (new flags + a new helper
`_persist_inputs(dir, request, history)` + a small dispatcher in `main`).

### Step 1 — Write RED test

Append to `icu/tests/unit/scripts/test_run_consensus.py`:

```python
# ============================================================
# T67.3 — strict mode + --reuse
# ============================================================

import json
from pathlib import Path

import pytest


_BASE_REQUEST = {
    "plan": {
        "plan_period": "2026-W17",
        "weekly_tss_target": 380,
        "days": [
            {"day": "Mon", "training_type": "Endurance",
             "duration_min": 90, "tier": "MEDIUM"},
            {"day": "Wed", "training_type": "VO2max",
             "duration_min": 75, "tier": "HIGH"},
        ],
    },
    "athlete_state": {
        "ctl": 68.0, "atl": 72.0, "tsb": -4.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    },
    "physiology": {"cp_watts": 288, "w_prime_joules": 18000},
    "wellness_trend": [],
    "periodization_summary": {"phase": "BUILD"},
}


def _write_request(dir_: Path) -> Path:
    p = dir_ / "verdict_request.json"
    p.write_text(json.dumps(_BASE_REQUEST, indent=2,
                            sort_keys=True, ensure_ascii=False),
                 encoding="utf-8")
    return p


def test_strict_mode_emits_1_planner_prompt(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out_dir = tmp_path / "consensus_2026-04-27_1200"
    rc = main([
        "--mode", "strict",
        "--verdict-request", str(req),
        "--out", str(out_dir / "1_planner.prompt.md"),
    ])
    assert rc == 0
    written = out_dir / "1_planner.prompt.md"
    assert written.exists()
    body = written.read_text(encoding="utf-8")
    assert "<planner>" in body
    # Must NOT include other roles' Section A rules
    assert "Critic (`<critic>`)" not in body


def test_strict_mode_persists_inputs_for_reuse(tmp_path: Path) -> None:
    """Strict mode without --reuse must drop verdict_request.json next
    to the prompt for later --reuse."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out_dir = tmp_path / "consensus_X"
    rc = main(["--mode", "strict", "--verdict-request", str(req),
               "--out", str(out_dir / "1_planner.prompt.md")])
    assert rc == 0
    assert (out_dir / "verdict_request.json").exists()


def test_strict_reuse_reads_inputs_from_dir(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_T"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    body = (consensus_dir / "1_planner.prompt.md").read_text(encoding="utf-8")
    assert "<planner>" in body


def test_strict_reuse_missing_verdict_request_returns_2(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "empty_dir"
    consensus_dir.mkdir(parents=True)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 2


def test_strict_reuse_with_history_json(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_with_history"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    (consensus_dir / "history.json").write_text(json.dumps([{
        "plan_entry_id": "01HXYZABCD0123456789ABCDEF",
        "context": {"ctl": 65, "phase": "BUILD"},
        "verdict": "ACCEPT", "outcome": "consensus.ACCEPT@0.78",
    }]), encoding="utf-8")
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    body = (consensus_dir / "1_planner.prompt.md").read_text(encoding="utf-8")
    assert "01HXYZABCD0123456789ABCDEF" in body


def test_strict_without_reuse_requires_verdict_request(tmp_path: Path) -> None:
    """`--mode strict` without --reuse must require --verdict-request."""
    from scripts.run_consensus import main
    with pytest.raises(SystemExit):
        # argparse exits with 2 when a required flag is missing
        main(["--mode", "strict"])


def test_council_mode_default_unchanged(tmp_path: Path) -> None:
    """Regression: council mode (default) writes the original 4-role
    prompt and ignores any strict-only flags."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    rc = main([
        "--verdict-request", str(req),
        "--out", str(tmp_path / "council.prompt.md"),
    ])
    assert rc == 0
    body = (tmp_path / "council.prompt.md").read_text(encoding="utf-8")
    # Council mode emits all 4 roles in Section A
    assert "Critic (`<critic>`)" in body
    assert "Physiologist (`<physiologist>`)" in body
    assert "Arbiter (`<arbiter>`)" in body


def test_council_mode_also_persists_inputs(tmp_path: Path) -> None:
    """Council mode persists verdict_request.json next to the council
    prompt so a future strict --reuse invocation can pick it up."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out = tmp_path / "consensus_dir" / "council.prompt.md"
    rc = main([
        "--verdict-request", str(req),
        "--out", str(out),
    ])
    assert rc == 0
    assert (tmp_path / "consensus_dir" / "verdict_request.json").exists()


def test_strict_reuse_emits_strict_next_steps(tmp_path: Path,
                                              capsys) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_NEXT"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "--mode strict --step 2" in captured.out
    assert "1_planner.response.md" in captured.out
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_run_consensus.py -v
```

Expected first failure (existing council tests pass; 9 new tests fail):
`SystemExit: 2` (or `argparse.ArgumentError: unrecognized arguments: --mode`)

### Step 3 — Minimal implementation

REPLACE `_parse_args` and `main` in `icu/scripts/run_consensus.py` (also
ADD the helper `_persist_inputs` between them). Full revised file
follows. The diff is additive within the existing skeleton (imports +
the `_NEXT_STEPS` constant remain unchanged, but a strict variant is
added):

```python
# REPLACE the _NEXT_STEPS constant block:

_NEXT_STEPS_COUNCIL = (
    "Next steps (council mode):\n"
    "  1. Open the file, copy contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save reply as council.response.md.\n"
    "  4. Run: scripts/finalize_consensus.py --response council.response.md "
    "\\\n"
    "         --ledger coach_memory/ledger/decisions.jsonl"
)
_NEXT_STEPS_STRICT = (
    "Next steps (strict step 1 — Planner):\n"
    "  1. Open 1_planner.prompt.md, copy contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save reply as 1_planner.response.md (same dir).\n"
    "  4. Run: scripts/finalize_consensus.py --mode strict --step 2 \\\n"
    "         --consensus-dir <this_dir>"
)


# REPLACE _parse_args:

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 - assemble a council prompt; --mode strict "
                    "+ --reuse drive the strict 4-step variant.",
    )
    p.add_argument("--mode", choices=("council", "strict"),
                   default="council")
    p.add_argument("--verdict-request", type=Path, default=None,
                   help="Required unless --reuse.")
    p.add_argument("--history", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None,
                   help="Default: ./council.prompt.md (council) or "
                        "./coach_memory/consensus/1_planner.prompt.md "
                        "(strict). Ignored when --reuse is set.")
    p.add_argument("--reuse", type=Path, default=None,
                   help="Strict only: reuse an existing consensus dir.")
    return p.parse_args(argv)


# ADD helper _persist_inputs (above main):

def _persist_inputs(consensus_dir: Path,
                    request_payload: object,
                    history_payload: object | None) -> None:
    consensus_dir.mkdir(parents=True, exist_ok=True)
    (consensus_dir / "verdict_request.json").write_text(
        json.dumps(request_payload, indent=2,
                   sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    if history_payload is not None:
        (consensus_dir / "history.json").write_text(
            json.dumps(history_payload, indent=2,
                       sort_keys=True, ensure_ascii=False),
            encoding="utf-8")


# REPLACE main:

def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    # Resolve inputs based on mode + flags.
    if args.mode == "strict" and args.reuse is not None:
        request_path = args.reuse / "verdict_request.json"
        history_path = args.reuse / "history.json"
        if not history_path.exists():
            history_path = None
        out_path = args.reuse / "1_planner.prompt.md"
    else:
        if args.verdict_request is None:
            print("ERROR: --verdict-request required (or use --reuse "
                  "with --mode strict).", file=sys.stderr)
            return 2
        request_path = args.verdict_request
        history_path = args.history
        if args.out is not None:
            out_path = args.out
        elif args.mode == "strict":
            out_path = Path("coach_memory/consensus/1_planner.prompt.md")
        else:
            out_path = Path("council.prompt.md")

    try:
        req_payload = _load_json_or_die(request_path, "verdict-request")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        request = VerdictRequest.model_validate(req_payload)
    except Exception as exc:
        print(f"ERROR: verdict-request schema validation: {exc}",
              file=sys.stderr)
        return 2

    history: list[HistoryTriplet] | None = None
    history_payload_for_persist: object | None = None
    if history_path is not None:
        try:
            hist_payload = _load_json_or_die(history_path, "history")
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        if not isinstance(hist_payload, list):
            print(f"ERROR: history JSON must be a list, got "
                  f"{type(hist_payload).__name__}", file=sys.stderr)
            return 2
        try:
            history = [HistoryTriplet.model_validate(t)
                       for t in hist_payload]
            history_payload_for_persist = hist_payload
        except Exception as exc:
            print(f"ERROR: history schema: {exc}", file=sys.stderr)
            return 2

    if args.mode == "strict":
        from src.coach.consensus.strict_prompt import build_strict_prompt
        body = build_strict_prompt(step=1, request=request, history=history)
        next_steps = _NEXT_STEPS_STRICT
    else:
        body = build_council_prompt(request, history=history)
        next_steps = _NEXT_STEPS_COUNCIL

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write output {out_path}: {exc}",
              file=sys.stderr)
        return 3

    try:
        _persist_inputs(out_path.parent, req_payload,
                        history_payload_for_persist)
    except OSError as exc:
        print(f"ERROR: cannot persist inputs to {out_path.parent}: {exc}",
              file=sys.stderr)
        return 3

    print(f"Wrote {args.mode} prompt -> {out_path}")
    print(next_steps)
    return 0
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_run_consensus.py -v
```

Expected: existing council tests still pass + 9 new strict tests pass
(total green count depends on T65.4 baseline; assert delta-only).

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/run_consensus.py \
          icu/tests/unit/scripts/test_run_consensus.py && \
  git commit -m "feat(coach-phase3): T67.3 run_consensus.py --mode strict + --reuse"
```

# Task 68 — finalize_consensus.py strict state machine

T68 turns `scripts/finalize_consensus.py` into a small state machine for
strict mode:

- **step 2** : reads `1_planner.response.md` from `<consensus-dir>`,
  writes `2_critic.prompt.md` into the same dir.
- **step 3** : reads steps 1+2 responses, writes `3_physiologist.prompt.md`.
- **step 4** without `--confirm` : reads steps 1+2+3 responses + the
  step-4 Arbiter response (if it exists, dry-run-prints the would-be
  ledger entry; if it does not yet exist, writes `4_arbiter.prompt.md`
  instead — see Open Question 2 below; locked behavior is **two-phase**:
  step 4 has a "build prompt" sub-mode that fires when
  `4_arbiter.response.md` is missing, and a "finalize" sub-mode that
  fires when all 4 response files are present).
- **step 4** with `--confirm` : asserts all 4 response files exist;
  concatenates; calls `parse(synth, mode="strict")`; idempotency probes
  the ledger; on pass, appends with `source="consensus.strict"`,
  `payload.mode="strict"`, `payload.content_hash` over the concatenated
  body. Also writes `strict_verdict.md` (human-readable summary).

Existing council-mode CLI surface (`--response`, `--ledger`,
`--athlete-state`, `--confirm`/`--dry-run`) is unchanged.

T68 splits into 3 RED → GREEN cycles:

- **T68.1** — argparse extension: add `--mode {council,strict}`,
  `--step {2,3,4}`, `--consensus-dir <dir>`. Mutual-exclusion guards.
- **T68.2** — step 2 / 3 router: read prior responses, validate role
  tags, call `strict_prompt.build_strict_prompt`, write next prompt.
  Step 4 "build prompt" sub-mode (when `4_arbiter.response.md` is
  absent).
- **T68.3** — step 4 finalize: concatenate all 4 responses, parse,
  ledger append (idempotent), `strict_verdict.md` emission.

## T68.1 — argparse extension + mutual-exclusion guards

**Goal.** Extend the existing argparse in
`icu/scripts/finalize_consensus.py` with strict-mode flags, without
disturbing council-mode behavior. Add validation that:

- `--step` requires `--mode strict`;
- `--mode strict` requires `--consensus-dir <dir>` (when used at all —
  council mode never uses it);
- `--step` ∈ {2, 3, 4} (1 is run by `run_consensus.py`, not finalize);
- council mode (default) still requires `--response`, `--ledger`,
  `--athlete-state` as before;
- strict mode at step 2/3 does NOT require `--ledger` or
  `--athlete-state` (those are only needed at step 4 finalize);
- strict mode at step 4 with `--confirm` requires `--ledger` AND
  `--athlete-state`.

**Estimated impl size:** ~50 added lines (new argparse args + a
`_validate_args(args)` helper that returns int exit-code or `None`).

### Step 1 — Write RED test

Append to `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
# ============================================================
# T68.1 — argparse extension for strict mode
# ============================================================

import json
from pathlib import Path

import pytest


def test_step_without_mode_strict_rejected(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--step", "2", "--consensus-dir", str(tmp_path)]) == 2


def test_step_value_validated(tmp_path: Path) -> None:
    """Only 2/3/4 accepted (1 is run by run_consensus.py)."""
    from scripts.finalize_consensus import main
    d = tmp_path / "X"; d.mkdir()
    for bad in ("1", "5"):
        with pytest.raises(SystemExit):
            main(["--mode", "strict", "--step", bad,
                  "--consensus-dir", str(d)])


def test_strict_mode_requires_consensus_dir(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--mode", "strict", "--step", "2"]) == 2


def test_council_mode_default_unchanged(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    with pytest.raises(SystemExit):
        main([])


def test_strict_step4_confirm_requires_ledger_and_state(
    tmp_path: Path,
) -> None:
    from scripts.finalize_consensus import main
    d = tmp_path / "Y"; d.mkdir()
    for fname in ("1_planner.response.md", "2_critic.response.md",
                  "3_physiologist.response.md", "4_arbiter.response.md"):
        (d / fname).write_text(
            f"<{fname.split('_')[1]}>x</{fname.split('_')[1]}>",
            encoding="utf-8")
    rc = main(["--mode", "strict", "--step", "4", "--confirm",
               "--consensus-dir", str(d)])
    assert rc == 2


def test_strict_step2_does_not_require_ledger(tmp_path: Path) -> None:
    """T68.1 only validates argparse; step-2 routing arrives in T68.2."""
    from scripts.finalize_consensus import main
    d = tmp_path / "Z"; d.mkdir()
    (d / "verdict_request.json").write_text(json.dumps({
        "plan": {"plan_period": "W17", "weekly_tss_target": 380,
                 "days": []},
        "athlete_state": {"ctl": 68, "atl": 72, "tsb": -4,
                          "w_prime": 18000, "phase": "BUILD",
                          "week_of_year": 17},
        "physiology": {}, "wellness_trend": [],
        "periodization_summary": {},
    }), encoding="utf-8")
    (d / "1_planner.response.md").write_text(
        "<planner>OK</planner>", encoding="utf-8")
    rc = main(["--mode", "strict", "--step", "2",
               "--consensus-dir", str(d)])
    # argparse accepted (non-2 OR a non-argparse rc=2 input error).
    assert isinstance(rc, int)


def test_dry_run_and_confirm_mutually_exclusive(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    with pytest.raises(SystemExit):
        main(["--response", str(tmp_path / "x.md"),
              "--ledger", str(tmp_path / "l.jsonl"),
              "--athlete-state", str(tmp_path / "a.json"),
              "--confirm", "--dry-run"])


def test_strict_help_text_mentions_step_and_consensus_dir(capsys) -> None:
    from scripts.finalize_consensus import main
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--mode" in out and "--step" in out and "--consensus-dir" in out


def test_step3_argparse_accepted(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    d = tmp_path / "S3"; d.mkdir()
    rc = main(["--mode", "strict", "--step", "3",
               "--consensus-dir", str(d)])
    assert isinstance(rc, int)


def test_council_response_path_still_required(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    with pytest.raises(SystemExit):
        main(["--mode", "council",
              "--ledger", str(tmp_path / "l.jsonl"),
              "--athlete-state", str(tmp_path / "a.json")])
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected first failure (existing council tests still pass; 10 new tests
fail):
`SystemExit: 2` with stderr fragment
`unrecognized arguments: --mode strict --step 2 --consensus-dir ...`

### Step 3 — Minimal implementation

REPLACE `_parse_args` in `icu/scripts/finalize_consensus.py` and ADD a
new `_validate_args` helper. Existing council `main()` body stays
intact, just gated by an early `if args.mode == "strict": return
_strict_main(args)` dispatch:

```python
# REPLACE _parse_args:

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 - finalize a council response. Default = "
                    "dry-run; --confirm to append. --mode strict drives "
                    "the 4-step state machine via --step + --consensus-dir.",
    )
    p.add_argument("--mode", choices=("council", "strict"),
                   default="council")
    p.add_argument("--response", type=Path, default=None)
    p.add_argument("--ledger", type=Path, default=None)
    p.add_argument("--athlete-state", type=Path, default=None)
    p.add_argument("--step", type=int, choices=(2, 3, 4), default=None,
                   help="Strict mode only.")
    p.add_argument("--consensus-dir", type=Path, default=None,
                   help="Strict mode only.")
    gate = p.add_mutually_exclusive_group()
    gate.add_argument("--confirm", action="store_true")
    gate.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> int | None:
    if args.mode == "strict":
        if args.step is None:
            print("ERROR: --mode strict requires --step {2,3,4}.",
                  file=sys.stderr)
            return 2
        if args.consensus_dir is None:
            print("ERROR: --mode strict requires --consensus-dir <dir>.",
                  file=sys.stderr)
            return 2
        if (args.step == 4 and args.confirm
                and (args.ledger is None or args.athlete_state is None)):
            print("ERROR: strict step 4 --confirm requires --ledger "
                  "AND --athlete-state.", file=sys.stderr)
            return 2
        return None
    if args.step is not None:
        print("ERROR: --step requires --mode strict.", file=sys.stderr)
        return 2
    if (args.response is None or args.ledger is None
            or args.athlete_state is None):
        print("ERROR: council mode requires --response, --ledger, "
              "--athlete-state.", file=sys.stderr)
        return 2
    return None


# REPLACE the top of main() to insert _validate_args + strict dispatch:

def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    rc = _validate_args(args)
    if rc is not None:
        return rc

    if args.mode == "strict":
        return _strict_main(args)

    # ... existing council flow continues unchanged ...


def _strict_main(args: argparse.Namespace) -> int:
    """T68.1 stub; T68.2/T68.3 fill in."""
    print(f"[T68.1 stub] strict step={args.step}", file=sys.stderr)
    return 0
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected: existing council tests still pass + 10 new T68.1 tests pass.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/finalize_consensus.py \
          icu/tests/unit/scripts/test_finalize_consensus.py && \
  git commit -m "feat(coach-phase3): T68.1 finalize_consensus argparse for strict mode"
```

## T68.2 — step 2 / 3 router + step 4 prompt-build sub-mode

**Goal.** Replace the T68.1 stub `_strict_main` with a real router:

- **step 2**: read `1_planner.response.md` + `verdict_request.json` (+
  optional `history.json`) from `<consensus-dir>`; validate the planner
  role tag is well-formed (single non-empty `<planner>...</planner>`);
  call `strict_prompt.build_strict_prompt(step=2, request=...,
  history=..., prior_responses={"planner": <body>})`; write
  `2_critic.prompt.md` into `<consensus-dir>`. Print NEXT_STEPS for
  step 3.
- **step 3**: same shape, reads two priors (`1_planner` + `2_critic`),
  writes `3_physiologist.prompt.md`.
- **step 4 without `--confirm` AND without `4_arbiter.response.md`**:
  treat as "build prompt" sub-mode; reads three priors (`1_planner` +
  `2_critic` + `3_physiologist`), writes `4_arbiter.prompt.md`. Print
  NEXT_STEPS for the user to paste the Arbiter reply and re-run with
  `--confirm`.
- **step 4 with `--confirm`** OR **step 4 without `--confirm` but
  `4_arbiter.response.md` exists**: defer to T68.3's finalize path.

**Role-tag validator.** A helper `_extract_role_body(md, role)` returns
the role body or raises `ValueError("malformed role tag: ...")`. Rules:

- exactly one `<role>...</role>` pair (case-insensitive); zero or
  more-than-one is an error;
- body is non-empty after `.strip()`;
- the surrounding markdown is preserved verbatim (we re-inject the
  whole tag wrapper into `prior_responses[role]`).

**Estimated impl size:** ~120 added lines (router + 4 small helpers:
`_load_strict_inputs`, `_extract_role_body`, `_write_step_prompt`,
`_strict_main` body).

### Step 1 — Write RED test

Append to `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
# ============================================================
# T68.2 — step 2 / 3 router + step 4 prompt-build sub-mode
# ============================================================

_REQUEST_PAYLOAD = {
    "plan": {"plan_period": "2026-W17", "weekly_tss_target": 380,
             "days": [{"day": "Wed", "training_type": "VO2max",
                       "duration_min": 75, "tier": "HIGH"}]},
    "athlete_state": {"ctl": 68.0, "atl": 72.0, "tsb": -4.0,
                      "w_prime": 18000, "phase": "BUILD",
                      "week_of_year": 17},
    "physiology": {"cp_watts": 288, "w_prime_joules": 18000},
    "wellness_trend": [],
    "periodization_summary": {"phase": "BUILD"},
}


def _seed_dir(tmp_path: Path, *,
              with_planner=False, with_critic=False,
              with_phys=False, with_arbiter=False) -> Path:
    d = tmp_path / "session"
    d.mkdir(parents=True)
    (d / "verdict_request.json").write_text(
        json.dumps(_REQUEST_PAYLOAD), encoding="utf-8")
    if with_planner:
        (d / "1_planner.response.md").write_text(
            "<planner>\n- Wed VO2 @ CP=288W\n</planner>\n",
            encoding="utf-8")
    if with_critic:
        (d / "2_critic.response.md").write_text(
            "<critic>\n1. tss=380 < 340.\n2. work=20min < 25min.\n"
            "3. no race-sim.\n</critic>\n", encoding="utf-8")
    if with_phys:
        (d / "3_physiologist.response.md").write_text(
            "<physiologist>\nCP=288W W'=18000J durability=0.92 "
            "response_profile=high; knee_flag=false.\n"
            "</physiologist>\n", encoding="utf-8")
    if with_arbiter:
        (d / "4_arbiter.response.md").write_text(
            "<arbiter>\nREVISE\nLower Wed VO2 to 18min.\n</arbiter>\n"
            '<summary_json>\n{"verdict": "REVISE", "confidence": 0.74}\n'
            "</summary_json>\n", encoding="utf-8")
    return d


def _strict_call(consensus_dir: Path, step: int) -> int:
    from scripts.finalize_consensus import main
    return main(["--mode", "strict", "--step", str(step),
                 "--consensus-dir", str(consensus_dir)])


def test_step2_writes_critic_prompt(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True)
    assert _strict_call(consensus_dir, 2) == 0
    body = (consensus_dir / "2_critic.prompt.md").read_text(encoding="utf-8")
    assert "Prior Planner response" in body
    assert "Critic (`<critic>`)" in body


def test_step2_missing_planner_response_returns_2(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path)
    assert _strict_call(consensus_dir, 2) == 2


def test_step2_malformed_planner_tag_returns_2(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path)
    (consensus_dir / "1_planner.response.md").write_text(
        "<planner>no close", encoding="utf-8")
    assert _strict_call(consensus_dir, 2) == 2


def test_step2_blank_planner_body_returns_2(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path)
    (consensus_dir / "1_planner.response.md").write_text(
        "<planner>   </planner>", encoding="utf-8")
    assert _strict_call(consensus_dir, 2) == 2


def test_step3_writes_physiologist_prompt(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True, with_critic=True)
    assert _strict_call(consensus_dir, 3) == 0
    body = (consensus_dir / "3_physiologist.prompt.md").read_text(
        encoding="utf-8")
    assert "Prior Planner response" in body
    assert "Prior Critic response" in body


def test_step3_missing_critic_returns_2(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True)
    assert _strict_call(consensus_dir, 3) == 2


def test_step4_build_prompt_when_arbiter_response_absent(
    tmp_path: Path,
) -> None:
    """Step 4 without --confirm AND without 4_arbiter.response.md
    writes 4_arbiter.prompt.md (build sub-mode)."""
    consensus_dir = _seed_dir(tmp_path, with_planner=True,
                              with_critic=True, with_phys=True)
    assert _strict_call(consensus_dir, 4) == 0
    body = (consensus_dir / "4_arbiter.prompt.md").read_text(encoding="utf-8")
    assert "<arbiter>" in body and "<summary_json>" in body


def test_step4_build_prompt_missing_phys_returns_2(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True, with_critic=True)
    assert _strict_call(consensus_dir, 4) == 2


def test_step2_history_json_picked_up(tmp_path: Path) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True)
    (consensus_dir / "history.json").write_text(json.dumps([{
        "plan_entry_id": "01HABCDEFGHJKMNPQRSTVWXYZ0",
        "context": {"ctl": 65, "phase": "BUILD"},
        "verdict": "ACCEPT", "outcome": "consensus.ACCEPT@0.78",
    }]), encoding="utf-8")
    assert _strict_call(consensus_dir, 2) == 0
    body = (consensus_dir / "2_critic.prompt.md").read_text(encoding="utf-8")
    assert "01HABCDEFGHJKMNPQRSTVWXYZ0" in body


def test_step2_emits_strict_step3_next_steps(tmp_path: Path,
                                             capsys) -> None:
    consensus_dir = _seed_dir(tmp_path, with_planner=True)
    _strict_call(consensus_dir, 2)
    out = capsys.readouterr().out
    assert "--step 3" in out and "2_critic.response.md" in out
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected first failure: 10 new tests fail with the T68.1 stub
(`assert (consensus_dir/"2_critic.prompt.md").exists()` is False because
`_strict_main` only prints a stub message).

### Step 3 — Minimal implementation

REPLACE `_strict_main` and ADD helpers in
`icu/scripts/finalize_consensus.py`:

```python
# ADD imports near the top of the file:
import re
from datetime import datetime, timezone

from src.coach.consensus.council_prompt import VerdictRequest
from src.coach.consensus.history_injector import HistoryTriplet
from src.coach.consensus.strict_prompt import (
    STRICT_STEP_TO_ROLE,
    build_strict_prompt,
)


# ADD module-level constants:

_NEXT_STEPS_STRICT_TEMPLATE: dict[int, str] = {
    2: ("Next steps (strict step 2 — Critic):\n"
        "  1. Open 2_critic.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 2_critic.response.md.\n"
        "  3. Run: scripts/finalize_consensus.py --mode strict --step 3 "
        "--consensus-dir <this_dir>"),
    3: ("Next steps (strict step 3 — Physiologist):\n"
        "  1. Open 3_physiologist.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 3_physiologist.response.md.\n"
        "  3. Run: scripts/finalize_consensus.py --mode strict --step 4 "
        "--consensus-dir <this_dir>"),
    4: ("Next steps (strict step 4 — Arbiter):\n"
        "  1. Open 4_arbiter.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 4_arbiter.response.md.\n"
        "  3. Re-run step 4 (dry-run preview), then add --confirm + "
        "--athlete-state + --ledger to append."),
}


# ADD helper _extract_role_body:

_TAG_RE_CACHE: dict[str, re.Pattern] = {}


def _extract_role_body(md: str, role: str) -> str:
    """Body inside <role>...</role>; raise on missing/duplicate/blank."""
    pat = _TAG_RE_CACHE.get(role)
    if pat is None:
        pat = re.compile(rf"<{role}>(.*?)</{role}>",
                         re.DOTALL | re.IGNORECASE)
        _TAG_RE_CACHE[role] = pat
    matches = pat.findall(md)
    if len(matches) != 1:
        raise ValueError(f"malformed role tag: expected exactly one "
                         f"<{role}>...</{role}>, got {len(matches)}")
    body = matches[0].strip()
    if not body:
        raise ValueError(f"role tag <{role}> body is blank")
    return body


def _load_strict_inputs(
    consensus_dir: Path,
) -> tuple[VerdictRequest, list[HistoryTriplet] | None]:
    req_path = consensus_dir / "verdict_request.json"
    if not req_path.exists():
        raise FileNotFoundError(
            f"verdict_request.json not in {consensus_dir}")
    req_payload = json.loads(req_path.read_text(encoding="utf-8"))
    request = VerdictRequest.model_validate(req_payload)
    history: list[HistoryTriplet] | None = None
    hist_path = consensus_dir / "history.json"
    if hist_path.exists():
        hp = json.loads(hist_path.read_text(encoding="utf-8"))
        if not isinstance(hp, list):
            raise ValueError("history.json must be a JSON list")
        history = [HistoryTriplet.model_validate(t) for t in hp]
    return request, history


def _read_prior_responses(consensus_dir: Path, step: int) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in range(1, step):
        role = STRICT_STEP_TO_ROLE[s]
        path = consensus_dir / f"{s}_{role}.response.md"
        if not path.exists():
            raise FileNotFoundError(
                f"prior strict response missing: {path.name}")
        md = path.read_text(encoding="utf-8")
        body = _extract_role_body(md, role)
        out[role] = f"<{role}>\n{body}\n</{role}>"
    return out


# REPLACE _strict_main:

def _strict_main(args: argparse.Namespace) -> int:
    consensus_dir: Path = args.consensus_dir
    if not consensus_dir.is_dir():
        print(f"ERROR: --consensus-dir not a directory: {consensus_dir}",
              file=sys.stderr)
        return 2

    step: int = args.step
    arbiter_response = consensus_dir / "4_arbiter.response.md"
    if step == 4 and (args.confirm or arbiter_response.exists()):
        return _strict_finalize_step4(args, consensus_dir)

    try:
        request, history = _load_strict_inputs(consensus_dir)
        priors = _read_prior_responses(consensus_dir, step)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: strict step {step} input: {exc}",
              file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: strict step {step} validation: {exc}",
              file=sys.stderr)
        return 2

    try:
        body = build_strict_prompt(
            step=step, request=request,
            history=history, prior_responses=priors)
    except ValueError as exc:
        print(f"ERROR: build_strict_prompt step {step}: {exc}",
              file=sys.stderr)
        return 2

    role = STRICT_STEP_TO_ROLE[step]
    out_path = consensus_dir / f"{step}_{role}.prompt.md"
    try:
        out_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write {out_path}: {exc}", file=sys.stderr)
        return 3

    print(f"Wrote strict step-{step} prompt -> {out_path}")
    print(_NEXT_STEPS_STRICT_TEMPLATE[step])
    return 0


# ADD a stub for T68.3 (filled in next subtask):

def _strict_finalize_step4(args: argparse.Namespace,
                           consensus_dir: Path) -> int:
    print("[T68.2 stub] step 4 finalize not yet implemented",
          file=sys.stderr)
    return 0
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected: existing council tests + T68.1 tests still pass + 10 new
T68.2 tests pass.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/finalize_consensus.py \
          icu/tests/unit/scripts/test_finalize_consensus.py && \
  git commit -m "feat(coach-phase3): T68.2 finalize_consensus strict step 2/3/4-build router"
```

## T68.3 — step 4 finalize: concat + parse + ledger append + strict_verdict.md

**Goal.** Replace the T68.2 stub `_strict_finalize_step4` with the full
finalize logic:

1. Read all 4 response files (`1_planner` … `4_arbiter`); validate each
   role tag via `_extract_role_body`. Missing or malformed → exit 2.
2. **Concatenate** the four bodies into one synthetic markdown blob,
   preserving role tag wrappers, in the natural step order. Also include
   the Arbiter's `<summary_json>` block (extracted separately from
   `4_arbiter.response.md` since `_extract_role_body` only returns the
   `<arbiter>` body).
3. Call `parse_council(synth_md, mode="strict")`. On
   `ConsensusValidationError`, exit 2 with the violations list.
4. Compute `_content_hash(verdict)` (re-uses File 07 helper). Idempotency
   probe via `LedgerReader` over `decision_type="consensus_verdict"`.
   On hit → print `Already finalized: ...` and return 0 without writing.
5. **Dry-run** (default, no `--confirm`): print would-be ledger entry +
   write `strict_verdict.md` (human-readable). Return 0.
6. **`--confirm`**: append via `LedgerWriter.record(...,
   source="consensus.strict", payload=verdict.model_dump() | {"content_hash": h},
   evidence_refs=[<all 4 response paths>])`. Print
   `Appended consensus_verdict entry_id=<ULID> ...`. Also write
   `strict_verdict.md`. Return 0.
7. On IO failure during ledger write or `strict_verdict.md` write,
   return 3.

**`strict_verdict.md` format** (locked): see the
`_write_strict_verdict_md` impl below for the exact template — header
with timestamp + mode/verdict/confidence/justification, four `### Role`
sections (verbatim bodies), a `## summary_json` fenced JSON block, and
a `## Ledger entry` section with entry_id / evidence_refs / content_hash.

**Estimated impl size:** ~180 added lines (concat + parse + idempotency
+ ledger append + strict_verdict.md emission; reuses File 07's
`_content_hash` and `_append_to_ledger`-style logic, parameterised on
`source="consensus.strict"`).

### Step 1 — Write RED test

Append to `icu/tests/unit/scripts/test_finalize_consensus.py`:

```python
# ============================================================
# T68.3 — step 4 finalize (concat + parse + ledger + verdict.md)
# ============================================================

_HAPPY_PLANNER = (
    "<planner>\n- Wed: VO2max 75min @ CP=288W.\n"
    "- Sat: Threshold 90min @ 95% CP.\n</planner>"
)
_HAPPY_CRITIC = (
    "<critic>\n"
    "1. Wed VO2 work=20min < 25min (durability=0.92).\n"
    "2. weekly_tss=380 < 5*ctl=340.\n"
    "3. No race-sim, phase=BUILD ending 14 days.\n"
    "</critic>"
)
_HAPPY_PHYS = (
    "<physiologist>\nCP=288W W'=18000J durability decay 6%/1000kJ; "
    "response_profile.tolerance_class=high; end-of-week W' ≈ -2400J "
    "(knee_flag=false).\n</physiologist>"
)
_HAPPY_ARBITER = (
    "<arbiter>\nREVISE\nLower Wed VO2 work to 18min (durability=0.92).\n"
    "</arbiter>\n"
    '<summary_json>\n{"verdict": "REVISE", "confidence": 0.74}\n'
    "</summary_json>"
)


def _seed_full_strict(tmp_path: Path) -> Path:
    d = tmp_path / "session_full"
    d.mkdir(parents=True)
    (d / "verdict_request.json").write_text(
        json.dumps(_REQUEST_PAYLOAD), encoding="utf-8")
    (d / "1_planner.response.md").write_text(_HAPPY_PLANNER, encoding="utf-8")
    (d / "2_critic.response.md").write_text(_HAPPY_CRITIC, encoding="utf-8")
    (d / "3_physiologist.response.md").write_text(
        _HAPPY_PHYS, encoding="utf-8")
    (d / "4_arbiter.response.md").write_text(_HAPPY_ARBITER, encoding="utf-8")
    return d


def _make_athlete_state(tmp_path: Path) -> Path:
    p = tmp_path / "athlete_state.json"
    p.write_text(json.dumps({
        "ctl": 68.0, "atl": 72.0, "tsb": -4.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }), encoding="utf-8")
    return p


def _step4_dryrun_args(tmp_path: Path, consensus_dir: Path) -> list[str]:
    return ["--mode", "strict", "--step", "4",
            "--consensus-dir", str(consensus_dir),
            "--athlete-state", str(_make_athlete_state(tmp_path))]


def test_step4_dry_run_happy(tmp_path: Path, capsys) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    assert main(_step4_dryrun_args(tmp_path, consensus_dir)) == 0
    out = capsys.readouterr().out
    assert "[DRY-RUN]" in out
    assert '"mode": "strict"' in out
    assert '"source": "consensus.strict"' in out
    assert (consensus_dir / "strict_verdict.md").exists()


def test_step4_confirm_appends_to_ledger(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    ledger_path = tmp_path / "decisions.jsonl"
    rc = main(_step4_dryrun_args(tmp_path, consensus_dir)
              + ["--confirm", "--ledger", str(ledger_path)])
    assert rc == 0
    line = ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    entry = json.loads(line)
    assert entry["decision_type"] == "consensus_verdict"
    assert entry["source"] == "consensus.strict"
    assert entry["payload"]["mode"] == "strict"
    assert entry["payload"]["verdict"] == "REVISE"
    assert "content_hash" in entry["payload"]
    assert len(entry["evidence_refs"]) == 4


def test_step4_confirm_idempotent_on_rerun(tmp_path: Path,
                                           capsys) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    ledger_path = tmp_path / "decisions.jsonl"
    args = (_step4_dryrun_args(tmp_path, consensus_dir)
            + ["--confirm", "--ledger", str(ledger_path)])
    rc1 = main(args)
    capsys.readouterr()
    rc2 = main(args)
    assert rc1 == 0 and rc2 == 0
    assert "Already finalized" in capsys.readouterr().out
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    consensus_lines = [l for l in lines
                       if json.loads(l)["decision_type"]
                       == "consensus_verdict"]
    assert len(consensus_lines) == 1


def test_step4_concat_preserves_role_tag_order(tmp_path: Path) -> None:
    """Concat ordering planner→critic→physiologist→arbiter,
    verified via strict_verdict.md."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    main(_step4_dryrun_args(tmp_path, consensus_dir))
    md = (consensus_dir / "strict_verdict.md").read_text(encoding="utf-8")
    assert (md.index("### Planner") < md.index("### Critic")
            < md.index("### Physiologist") < md.index("### Arbiter"))


def test_step4_parser_failure_returns_2(tmp_path: Path) -> None:
    """text=ACCEPT vs summary_json=REVISE rejected by parse(mode='strict')."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    (consensus_dir / "4_arbiter.response.md").write_text(
        "<arbiter>\nACCEPT\nfine.\n</arbiter>\n"
        '<summary_json>\n{"verdict": "REVISE", "confidence": 0.5}\n'
        "</summary_json>", encoding="utf-8")
    rc = main(_step4_dryrun_args(tmp_path, consensus_dir) + [
        "--confirm", "--ledger", str(tmp_path / "decisions.jsonl")])
    assert rc == 2


def test_step4_missing_arbiter_response_falls_to_prompt_build(
    tmp_path: Path,
) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    (consensus_dir / "4_arbiter.response.md").unlink()
    assert main(_step4_dryrun_args(tmp_path, consensus_dir)) == 0
    assert (consensus_dir / "4_arbiter.prompt.md").exists()
    assert not (consensus_dir / "strict_verdict.md").exists()


def test_step4_strict_verdict_md_contents(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    main(_step4_dryrun_args(tmp_path, consensus_dir))
    md = (consensus_dir / "strict_verdict.md").read_text(encoding="utf-8")
    assert "**Mode**: strict" in md
    assert "**Verdict**: REVISE" in md
    assert "**Confidence**: 0.74" in md
    assert "## Expert turns" in md
    assert "## summary_json" in md


def test_step4_evidence_refs_paths_in_order(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    ledger_path = tmp_path / "decisions.jsonl"
    main([
        "--mode", "strict", "--step", "4", "--confirm",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(_make_athlete_state(tmp_path)),
        "--ledger", str(ledger_path),
    ])
    line = ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    refs = json.loads(line)["evidence_refs"]
    assert len(refs) == 4
    assert refs[0].endswith("1_planner.response.md")
    assert refs[3].endswith("4_arbiter.response.md")


def test_step4_confirm_missing_arbiter_response_returns_2(
    tmp_path: Path,
) -> None:
    """--confirm + missing 4_arbiter.response.md → exit 2 (no silent
    re-route to prompt-build)."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    (consensus_dir / "4_arbiter.response.md").unlink()
    rc = main([
        "--mode", "strict", "--step", "4", "--confirm",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(_make_athlete_state(tmp_path)),
        "--ledger", str(tmp_path / "decisions.jsonl"),
    ])
    assert rc == 2


def test_step4_council_validator_does_not_fire_in_strict_mode(
    tmp_path: Path,
) -> None:
    """Regression-pin Architectural decision #4."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    rc = main([
        "--mode", "strict", "--step", "4",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(_make_athlete_state(tmp_path)),
    ])
    assert rc == 0


def test_step4_confidence_out_of_range_rejected(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    (consensus_dir / "4_arbiter.response.md").write_text(
        '<arbiter>\nACCEPT\nfine.\n</arbiter>\n<summary_json>\n'
        '{"verdict": "ACCEPT", "confidence": 2.0}\n</summary_json>',
        encoding="utf-8",
    )
    rc = main([
        "--mode", "strict", "--step", "4", "--confirm",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(_make_athlete_state(tmp_path)),
        "--ledger", str(tmp_path / "decisions.jsonl"),
    ])
    assert rc == 2


def test_step4_critic_under_3_points_rejected(tmp_path: Path) -> None:
    """Parser rule 3 still fires: Critic <3 points → fail."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    (consensus_dir / "2_critic.response.md").write_text(
        "<critic>\n1. only one.\n</critic>", encoding="utf-8",
    )
    rc = main([
        "--mode", "strict", "--step", "4", "--confirm",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(_make_athlete_state(tmp_path)),
        "--ledger", str(tmp_path / "decisions.jsonl"),
    ])
    assert rc == 2


def test_step4_athlete_state_reused_for_ledger_record(
    tmp_path: Path,
) -> None:
    """The --athlete-state JSON is what's recorded (not VerdictRequest's
    embedded athlete_state)."""
    from scripts.finalize_consensus import main
    consensus_dir = _seed_full_strict(tmp_path)
    p = tmp_path / "newer_state.json"
    p.write_text(json.dumps({
        "ctl": 71.0, "atl": 75.0, "tsb": -4.0,
        "w_prime": 18500, "phase": "BUILD", "week_of_year": 18,
    }), encoding="utf-8")
    ledger_path = tmp_path / "decisions.jsonl"
    main([
        "--mode", "strict", "--step", "4", "--confirm",
        "--consensus-dir", str(consensus_dir),
        "--athlete-state", str(p),
        "--ledger", str(ledger_path),
    ])
    line = ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    entry = json.loads(line)
    assert entry["athlete_state_ref"]["week_of_year"] == 18
    assert entry["athlete_state_ref"]["w_prime"] == 18500
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected first failure: 14 new tests fail with stub message
`[T68.2 stub] step 4 finalize not yet implemented` (rc=0 but no
`[DRY-RUN]` printed, no `strict_verdict.md` created, no ledger entry).

### Step 3 — Minimal implementation

REPLACE `_strict_finalize_step4` and ADD helpers in
`icu/scripts/finalize_consensus.py`:

```python
# ADD helper _concat_strict_responses:

_SUMMARY_JSON_RE = re.compile(
    r"<summary_json>(.*?)</summary_json>",
    re.DOTALL | re.IGNORECASE)


def _concat_strict_responses(consensus_dir: Path) -> tuple[str, list[Path]]:
    """Concatenate 4 role bodies + arbiter's summary_json. Order:
    planner → critic → physiologist → arbiter."""
    paths: list[Path] = []
    bodies: list[str] = []
    summary_block = ""
    for step in (1, 2, 3, 4):
        role = STRICT_STEP_TO_ROLE[step]
        path = consensus_dir / f"{step}_{role}.response.md"
        if not path.exists():
            raise FileNotFoundError(
                f"strict response missing: {path.name}")
        md = path.read_text(encoding="utf-8")
        body = _extract_role_body(md, role)
        bodies.append(f"<{role}>\n{body}\n</{role}>")
        paths.append(path)
        if role == "arbiter":
            sm = _SUMMARY_JSON_RE.search(md)
            if not sm:
                raise ValueError(
                    "4_arbiter.response.md missing <summary_json>")
            summary_block = (f"<summary_json>\n{sm.group(1).strip()}\n"
                             "</summary_json>")
    return "\n\n".join(bodies + [summary_block]) + "\n", paths


# ADD helper _write_strict_verdict_md:

def _write_strict_verdict_md(consensus_dir: Path,
                             verdict: CouncilVerdict,
                             response_paths: list[Path],
                             content_hash: str,
                             entry_id: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    role_to_body = {t.role: t.body_md.strip()
                    for t in verdict.expert_turns}
    summary_dump = json.dumps(verdict.summary_json, indent=2,
                              sort_keys=True, ensure_ascii=False)
    refs_lines = "\n".join(f"  - {p}" for p in response_paths)
    body = (
        f"# Strict consensus verdict — {now}\n\n"
        f"**Mode**: {verdict.mode}\n"
        f"**Verdict**: {verdict.verdict}\n"
        f"**Confidence**: {verdict.confidence:.2f}\n"
        f"**Justification**: {verdict.justification}\n\n"
        "## Expert turns\n\n"
        f"### Planner\n{role_to_body.get('planner', '(missing)')}\n\n"
        f"### Critic\n{role_to_body.get('critic', '(missing)')}\n\n"
        f"### Physiologist\n"
        f"{role_to_body.get('physiologist', '(missing)')}\n\n"
        f"### Arbiter\n{role_to_body.get('arbiter', '(missing)')}\n\n"
        f"## summary_json\n\n```json\n{summary_dump}\n```\n\n"
        "## Ledger entry\n\n"
        f"- entry_id: {entry_id or '(DRY-RUN)'}\n"
        f"- evidence_refs:\n{refs_lines}\n"
        f"- content_hash: {content_hash}\n"
    )
    (consensus_dir / "strict_verdict.md").write_text(body, encoding="utf-8")


# REPLACE _strict_finalize_step4:

def _strict_finalize_step4(args: argparse.Namespace,
                           consensus_dir: Path) -> int:
    if args.athlete_state is None:
        print("ERROR: strict step 4 finalize requires --athlete-state.",
              file=sys.stderr)
        return 2

    try:
        synth, response_paths = _concat_strict_responses(consensus_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: strict step 4 input: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: cannot read strict response: {exc}",
              file=sys.stderr)
        return 2

    try:
        athlete_state = _read_athlete_state(args.athlete_state)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        verdict = parse_council(synth, mode="strict")
    except ConsensusValidationError as exc:
        print("ERROR: strict response failed parser validation:",
              file=sys.stderr)
        for v in exc.violations:
            print(f"  - {v}", file=sys.stderr)
        return 2

    content_hash = _content_hash(verdict)

    if args.confirm:
        if args.ledger is None:
            print("ERROR: strict step 4 --confirm requires --ledger.",
                  file=sys.stderr)
            return 2
        if args.ledger.exists():
            try:
                reader = LedgerReader(args.ledger)
                existing = reader.query(
                    decision_type="consensus_verdict", limit=None)
            except Exception as exc:
                print(f"ERROR: ledger read failed: {exc}",
                      file=sys.stderr)
                return 3
            for prior in existing:
                if prior.payload.get("content_hash") == content_hash:
                    print(f"Already finalized: "
                          f"content_hash={content_hash[:12]}... "
                          f"existing entry_id={prior.entry_id}")
                    try:
                        _write_strict_verdict_md(
                            consensus_dir, verdict, response_paths,
                            content_hash, prior.entry_id)
                    except OSError:
                        pass
                    return 0

    if not args.confirm:
        entry_preview = {
            "decision_type": "consensus_verdict",
            "source": "consensus.strict",
            "athlete_state_ref": athlete_state.model_dump(),
            "confidence": verdict.confidence,
            "evidence_refs": [str(p) for p in response_paths],
            "payload": verdict.model_dump(),
            "content_hash": content_hash,
        }
        print("[DRY-RUN] would append the following ledger entry:")
        print(json.dumps(entry_preview, indent=2,
                         sort_keys=True, ensure_ascii=False))
        print("\nRe-run with --confirm + --ledger to actually append.")
        try:
            _write_strict_verdict_md(
                consensus_dir, verdict, response_paths,
                content_hash, None)
        except OSError as exc:
            print(f"ERROR: cannot write strict_verdict.md: {exc}",
                  file=sys.stderr)
            return 3
        return 0

    payload = verdict.model_dump()
    payload["content_hash"] = content_hash
    try:
        writer = LedgerWriter(args.ledger)
        entry_id = writer.record(
            decision_type="consensus_verdict",
            source="consensus.strict",
            athlete_state=athlete_state,
            payload=payload,
            evidence_refs=[str(p) for p in response_paths],
            confidence=verdict.confidence,
            superseded_by=None,
        )
    except Exception as exc:
        print(f"ERROR: ledger write failed: {exc}", file=sys.stderr)
        return 3

    try:
        _write_strict_verdict_md(consensus_dir, verdict, response_paths,
                                 content_hash, entry_id)
    except OSError as exc:
        print(f"ERROR: cannot write strict_verdict.md: {exc}",
              file=sys.stderr)
        return 3

    print(f"Appended consensus_verdict entry_id={entry_id} "
          f"(source=consensus.strict, "
          f"content_hash={content_hash[:12]}...)")
    return 0
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_finalize_consensus.py -v
```

Expected: existing council tests + T68.1 + T68.2 tests + 14 new T68.3
tests pass. Total finalize_consensus suite green count rises by 34.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/finalize_consensus.py \
          icu/tests/unit/scripts/test_finalize_consensus.py \
          icu/tests/fixtures/phase3/consensus/strict/ && \
  git commit -m "feat(coach-phase3): T68.3 finalize_consensus strict step 4 finalize + ledger append"
```

## Acceptance criteria

1. **Pytest deltas:** test_strict_prompt.py = 22 passed (10+12);
   test_run_consensus.py = +9 on File 07 baseline; test_finalize_consensus.py
   = +34 (10+10+14). Net +65 tests; council regression unchanged.
2. **Commits (exact, in order):**
   1. `feat(coach-phase3): T67.1 strict_prompt skeleton + step 1 (Planner)`
   2. `feat(coach-phase3): T67.2 strict steps 2-4 + prior-response embedding`
   3. `feat(coach-phase3): T67.3 run_consensus.py --mode strict + --reuse`
   4. `feat(coach-phase3): T68.1 finalize_consensus argparse for strict mode`
   5. `feat(coach-phase3): T68.2 finalize_consensus strict step 2/3/4-build router`
   6. `feat(coach-phase3): T68.3 finalize_consensus strict step 4 finalize + ledger append`
3. **`git diff --stat`** = ONLY the 7 touch-list paths.
4. **API-free grep**: `! grep -rn "google\.genai\|^import requests\|^from requests\|^import httpx\|^from httpx\|^import aiohttp\|^from aiohttp\|^import urllib\|^from urllib" src/coach/consensus/ scripts/run_consensus.py scripts/finalize_consensus.py`
   must return exit 0.
5. **No new deps**: `icu/requirements.txt` unchanged.
6. **Council regression** stays green at every File 08 commit.
7. **PHASE_1_2_IMMUTABILITY**: zero edits under
   `icu/src/coach/{physiology,deep_analyzer,periodization,session_designer}/`.
8. **Branch `ai-coach-phase-3`** at every commit.

## Smoke test (manual, optional)

E2E sanity check on a fresh dir; automated tests cover the same paths.

```bash
cd /mnt/d/Cycling-phase3/icu
mkdir -p /tmp/strict_smoke
# Drop a verdict_request.json into /tmp/strict_smoke (use the test
# fixture under tests/fixtures/phase3/consensus/verdict_request.json).

# Step 1
.venv/bin/python scripts/run_consensus.py --mode strict \
    --verdict-request /tmp/strict_smoke/verdict_request.json \
    --out /tmp/strict_smoke/1_planner.prompt.md
# Paste reply -> 1_planner.response.md

# Steps 2, 3, 4-build
.venv/bin/python scripts/finalize_consensus.py --mode strict --step 2 \
    --consensus-dir /tmp/strict_smoke
# Paste reply -> 2_critic.response.md
.venv/bin/python scripts/finalize_consensus.py --mode strict --step 3 \
    --consensus-dir /tmp/strict_smoke
# Paste reply -> 3_physiologist.response.md
.venv/bin/python scripts/finalize_consensus.py --mode strict --step 4 \
    --consensus-dir /tmp/strict_smoke
# Paste reply -> 4_arbiter.response.md

# Step 4 dry-run + --confirm
.venv/bin/python scripts/finalize_consensus.py --mode strict --step 4 \
    --consensus-dir /tmp/strict_smoke \
    --athlete-state /tmp/strict_smoke/athlete_state.json
# Expect: [DRY-RUN] preview + strict_verdict.md.
.venv/bin/python scripts/finalize_consensus.py --mode strict --step 4 \
    --confirm --consensus-dir /tmp/strict_smoke \
    --athlete-state /tmp/strict_smoke/athlete_state.json \
    --ledger coach_memory/ledger/decisions.jsonl
# Expect: Appended consensus_verdict entry_id=01H...
# Idempotency: re-run same --confirm. Expect: Already finalized: ...
```

## Rollback

Revert in reverse order: T68.3 → T68.2 → T68.1 → T67.3 → T67.2 → T67.1.
After every revert, run pytest under `tests/unit/consensus/` +
`tests/unit/scripts/`. Council tests stay green. File 06/07 modules byte-
identical to pre-File-08 (verify with `git diff <pre-tag>..HEAD --
icu/src/coach/consensus/{types,response_parser,history_injector,council_prompt}.py`).

## Open questions / blueprint resolutions

These were raised during File 08 spec drafting; each has a locked
decision recorded here so implementers don't reopen them.

### OQ1 — Where does `--reuse <dir>` find verdict_request.json?

**Decision (locked).** Extend `run_consensus.py` to persist
`verdict_request.json` (+ optional `history.json`) into the consensus
dir alongside the prompt (both council and strict-no-reuse modes).
T67.3 implements this. `--mode strict --reuse <dir>` then reads inputs
from that dir without re-fetching from `coach_memory/`.

### OQ2 — Can step 4 be both "build prompt" and "finalize"?

**Decision (locked).** Auto-detect based on file presence:

- `4_arbiter.response.md` absent AND no `--confirm` → prompt-build.
- `4_arbiter.response.md` present OR `--confirm` set → finalize.
- `--confirm` set BUT `4_arbiter.response.md` absent → exit 2.

### OQ3 — Should each strict step's response validate as a partial CouncilVerdict?

**Decision (locked).** **NO.** Partial bodies can't satisfy parser
rules 3/4 (Critic ≥3 points, Physiologist 3-of-4 keywords). Defer full
validation to step-4 concat; steps 2/3 only do `_extract_role_body`
tag-presence + non-blank check.

### OQ4 — Promote `_section_b` / `_section_c` to public exports?

**Decision (locked).** **NO.** Cross-module private imports are
acceptable within the same package; promoting would be a contract
change to File 07.

### OQ5 — Persist the step-4 concatenated body to disk?

**Decision (locked).** **NO.** The 4 response files are the ground
truth; concat is a deterministic function. `evidence_refs` + payload
preserve full reproducibility. `strict_verdict.md` is the only
persisted human artefact.

### OQ6 — Strict-mode `source` field granularity?

**Decision (locked).** Single value `consensus.strict` (no step
suffix) — symmetric with File 07's `consensus.council`. Step 2/3/4-build
events stay in the JSONL logger only (no ledger entry).

## End-of-file checkpoint

- [ ] All 6 commits landed on `ai-coach-phase-3` in the locked order.
- [ ] `cd icu && .venv/bin/pytest tests/unit/consensus/ tests/unit/scripts/`
      green; T67/T68 delta = +65 tests.
- [ ] API-free grep returns exit 0 (no match).
- [ ] `git diff --stat` shows ONLY the 7 touch-list paths.
- [ ] `save-progress` run; MEMORY.md update deferred to parent session.
- [ ] Next session = NONE. Phase 3 M2 complete; release tag is parent
      session's responsibility.

## Worktree bootstrap reminder

In a fresh worktree, untracked `icu/src/{analyzer,utils,fetcher}` +
`icu/.venv/` are missing. Bootstrap with `cp -r /mnt/d/Cycling/icu/src/{analyzer,utils,fetcher} icu/src/`
then `ln -s /mnt/d/Cycling/icu/.venv icu/.venv`. Verify File 07 baseline
green before starting File 08. See user-memory `worktree_setup_icu.md`.

## Subagent brief

> Use `docs/superpowers/plans/phase-3/08-consensus-strict.md`. Apply
> `superpowers:subagent-driven-development`. Execute T67.1 → T67.2 →
> T67.3 → T68.1 → T68.2 → T68.3. Each: RED test + fail → minimal impl →
> pass → commit. Apply the 9-item Pre-flight checklist. Honour the touch
> list — no edits under `src/coach/{physiology,deep_analyzer,periodization,session_designer,ledger,adapter}/`
> nor File 06/07 modules; no new requirements.txt; no `import google.genai|requests|httpx|urllib|aiohttp`.
> Council regression stays green after every commit. Report: 6 task IDs,
> file paths, pytest delta, deviations.

## Glossary

- **strict mode**: 4-step single-role council variant.
- **consensus dir**: `coach_memory/consensus/<YYYY-MM-DD_HHMM>/`.
- **prior responses**: 1–3 earlier-step Gemini replies embedded verbatim.
- **prompt-build sub-mode** vs **finalize sub-mode**: step 4 branches —
  builds `4_arbiter.prompt.md` vs concats + parses + ledger.
- **content_hash**: sha256 over `CouncilVerdict` for idempotency.
- **synthetic concat**: in-memory `synth_md` from 4 responses; never
  persisted (OQ5).
