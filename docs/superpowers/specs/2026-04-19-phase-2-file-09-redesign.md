# Phase 2 File 09 Redesign — API-Free Prose Pipeline

> Status: design approved 2026-04-19, pending spec review before `writing-plans`
> Scope: replace `docs/superpowers/plans/phase-2/09-prose-generator.md` and patch `10-integration.md` T45–T46
> Driver: user hard constraint — scripts must never call an LLM API; Phase 2 must follow the existing `scripts/push_plan.py` prompt-file → paste → JSON-file → `--push` pattern.

## Context

The original `09-prose-generator.md` (committed `4fa3f14`) assumes a live `google.genai` client: `enrich_with_prose(plan, ..., client, model="gemini-2.5-flash")` calls `client.models.generate_content(...)`. This conflicts with the project's API-free workflow, which the legacy `scripts/push_plan.py` already implements:

1. Script emits a prompt file (no network call).
2. User pastes into Gemini CLI / Claude Code coach mode.
3. User saves the structured JSON reply locally.
4. `--push --plan-file <path>` syncs to ICU calendar.

Phase 2's composer + assembler already produce a fully numeric `WeeklyPlan` before any LLM involvement. The LLM's only remaining job is prose enrichment (`coaching_summary` + per-day `description` text). Redesigning File 09 around the existing API-free pattern eliminates the conflict and simplifies the tests (no mocked Gemini client needed).

## Design decisions (locked)

1. **Mode A — Optional polish.** Skeleton plan is always pushable to ICU calendar. Prose enrichment is a separate manual step; skipping it never blocks `--push`.
2. **No `google.genai` import** anywhere in `session_designer/`.
3. **Four-artifact output** from `save_weekly_plan`: `.json`, `.md`, `.trace.json`, `.prose_prompt.md` — the prose prompt is always emitted (near-zero cost; makes the optional path discoverable).
4. **Two-layer numeric safety.** (a) `_ProseResponse` Pydantic model only exposes `coaching_summary` and `days[*].{date,description}` — other fields in the user's pasted JSON are dropped by the parser. (b) `apply_prose_response` uses `model_copy(update={...})` on only the two text fields, so numeric fields are physically unreachable from the merge path.
5. **Strict day-set validation.** Pasted response must have exactly 7 days with dates matching `plan.days`. Mismatch raises `ValueError` before any mutation.
6. **File split: 1 → 2.** `plan_writer.py` owns filesystem IO; `prose_io.py` owns prompt text + response merging. Keeps each file < 200 lines.

## File structure

```
icu/src/coach/session_designer/
├── plan_writer.py         # NEW — T43 (save_weekly_plan)
├── prose_io.py            # NEW — T44 (render_prose_prompt, apply_prose_response, load_and_apply_prose)
└── (prose_generator.py intentionally not created)

icu/prompts/session_designer/
└── prose_prompt.md        # NEW — prompt template (identical to original plan)

icu/tests/unit/session_designer/
├── test_plan_writer.py    # NEW
└── test_prose_io.py       # NEW
```

## API contracts

### `plan_writer.save_weekly_plan`

```python
def save_weekly_plan(
    plan: WeeklyPlan,
    out_dir: Path,
    week_start: date,
    prose_prompt: str,
    trace: dict,
) -> dict[str, Path]:
    """Emit plan_YYYYMMDD.{json,md,trace.json,prose_prompt.md}.

    Returns {"json": ..., "md": ..., "trace": ..., "prose_prompt": ...}.
    All files are UTF-8 encoded. Markdown uses the skeleton descriptions
    already on plan.days[*].description (no LLM step required).
    """
```

Re-write semantics: `save_weekly_plan` always overwrites. Used on both the initial generation path and the post-`apply-prose` rewrite path.

### `prose_io.render_prose_prompt`

```python
def render_prose_prompt(
    plan: WeeklyPlan,
    phase_rationale: str,
    phase_value: str,           # Phase.value — "BUILD", "BASE", ...
    physiology_summary: dict,   # {"cp", "w_prime", "durability_60s_pct", "knee_flag"}
    violations: list,
) -> str:
    """Pure function. No network. Loads prose_prompt.md template and
    appends the concrete payload (plan JSON, physiology line, violations).
    """
```

### `prose_io._ProseResponse` and `apply_prose_response`

```python
class _ProseDay(BaseModel):
    date: str
    description: str
    model_config = ConfigDict(extra="ignore")   # drop duration_min etc.

class _ProseResponse(BaseModel):
    coaching_summary: str
    days: list[_ProseDay]
    model_config = ConfigDict(extra="ignore")

def apply_prose_response(
    plan: WeeklyPlan,
    response: dict,
) -> WeeklyPlan:
    """Parse response (dropping extra fields), validate day count / date
    set matches plan.days, merge coaching_summary + per-day description.

    Raises ValueError if:
      - days count != 7
      - any response date not in plan.days dates
      - any plan date missing from response
    """
```

### `prose_io.load_and_apply_prose`

```python
def load_and_apply_prose(
    plan_path: Path,
    response_path: Path,
    out_dir: Path,
    week_start: date,
) -> dict[str, Path]:
    """CLI glue: read plan.json + response.json, call apply_prose_response,
    re-render prompt for trace parity, and call save_weekly_plan to
    overwrite .json + .md + .trace.json + .prose_prompt.md in place.
    """
```

## End-to-end flow

```
                     [mandatory]
assembler.WeeklyPlan ──► save_weekly_plan ──► 4 files on disk
                                              │
                                              ├── plan_YYYYMMDD.json   ← push source
                                              ├── plan_YYYYMMDD.md     ← skeleton readable
                                              ├── plan_YYYYMMDD.trace.json
                                              └── plan_YYYYMMDD.prose_prompt.md

                     [optional — any time before --push]
user pastes prose_prompt.md into Claude Code
user saves reply as prose_response.json
                                              │
load_and_apply_prose(plan, response, ...) ────┤
                                              ├── plan_YYYYMMDD.json   ← overwritten with coaching_summary + descriptions
                                              └── plan_YYYYMMDD.md     ← overwritten

                     [push at any time]
push_plan.py --push --plan-file plan_YYYYMMDD.json   ← unchanged; reads whatever .json is on disk
```

## Test plan

### `test_plan_writer.py`

- `test_save_weekly_plan_emits_all_four_artifacts` — files exist on disk, `.json` round-trips through Pydantic, `.md` contains plan table (≥ 9 `|`-lines), `.prose_prompt.md` contains `"BUILD"` and `"CP="`.
- `test_save_weekly_plan_is_utf8_and_idempotent_on_rewrite` — second call with updated coaching_summary produces a byte-different `.md` that contains the new string.
- `test_markdown_table_includes_power_or_hr_range` — Rest day shows `-`, Ride days show a power/HR range.

### `test_prose_io.py`

- `test_render_prose_prompt_mentions_all_required_context` — prompt contains phase value, phase rationale, `CP=`, `threshold_capacity` (or equivalent focus_theme token), and `禁止修改`.
- `test_apply_prose_response_fills_summary_and_descriptions` — happy path; both fields updated on the returned plan; plan identity of Rest day description preserved only if LLM returned it.
- `test_apply_prose_response_does_not_mutate_numeric_fields` — pasted response includes `"duration_min": 9999, "power_range_w": "999-9999W"` on a ride day; returned plan still has the original 75 / `"308-322W"`. `description` accepted as `"custom"`.
- `test_apply_prose_response_rejects_day_count_mismatch` — 6 or 8 days in response → `ValueError`.
- `test_apply_prose_response_rejects_date_mismatch` — response date `2026-04-27` (one day past the week) → `ValueError`.
- `test_load_and_apply_prose_rewrites_json_and_md_in_place` — given a freshly-saved plan + a response fixture, after `load_and_apply_prose` the on-disk `.json` has non-empty `coaching_summary` and the `.md` contains the enriched text.

### Dropped from the original plan

- `test_enrich_with_prose_fills_summary_and_descriptions` (relied on mocked `client.models.generate_content`) — superseded by `test_apply_prose_response_fills_summary_and_descriptions`.
- `test_enrich_falls_back_when_api_fails` — no API, no fallback semantics.

## File 10 patch (inlined in this spec; no separate document)

`10-integration.md` T45–T46 currently calls `enrich_with_prose(client=gemini_client, ...)`. Replace with:

```python
# in scripts/push_plan.py, --engine v2 branch

def generate_plan_v2(week_start: date, week_end: date) -> dict[str, Path]:
    snapshot = load_periodization_snapshot(...)
    plan = assemble_weekly(snapshot, ...)
    prompt = render_prose_prompt(
        plan,
        phase_rationale=snapshot.micro.phase_rationale,
        phase_value=snapshot.micro.phase.value,
        physiology_summary=_summarize_physiology(),
        violations=plan.violations_remaining,
    )
    trace = build_trace(plan, snapshot)   # existing helper
    paths = save_weekly_plan(
        plan=plan, out_dir=Path("reports"),
        week_start=week_start,
        prose_prompt=prompt, trace=trace,
    )
    print(f"✅ 骨架计划已写入 {paths['json']}")
    print(f"📝 如需教练叙述：复制 {paths['prose_prompt']} 到 Claude Code，")
    print(f"    保存返回 JSON 后运行 --apply-prose --plan-file {paths['json']} --prose-response <path>")
    return paths


def apply_prose_to_existing(plan_path: Path, response_path: Path) -> dict[str, Path]:
    week_start_iso = json.loads(plan_path.read_text(encoding="utf-8"))["week_start"]
    week_start = date.fromisoformat(week_start_iso)
    return load_and_apply_prose(
        plan_path=plan_path,
        response_path=response_path,
        out_dir=plan_path.parent,
        week_start=week_start,
    )
```

New CLI flags on `push_plan.py`:

| Flag | Purpose |
|---|---|
| `--engine v2` | Run new pipeline (generate_plan_v2). Default remains legacy until Phase 3. |
| `--apply-prose` + `--plan-file X` + `--prose-response Y` | Merge user-pasted prose into existing plan. |
| `--push --plan-file X` | Unchanged (reads any valid WeeklyPlan JSON; works on both skeleton and enriched). |

Fallback guardrail (unchanged from original plan): any exception inside `generate_plan_v2` is caught and the code falls back to legacy `generate_plan(...)`, preserving production use.

## Acceptance criteria for File 09 delivery

- `pytest icu/tests/unit/session_designer/test_plan_writer.py icu/tests/unit/session_designer/test_prose_io.py -v` → all green.
- No import of `google.genai` in `icu/src/coach/session_designer/*`.
- Grepping `icu/src/coach/session_designer/` for `generate_content(` returns nothing.
- `reports/plan_20260420.{json,md,trace.json,prose_prompt.md}` materialize on a dry-run of the v2 pipeline.
- A round-trip test (save → hand-edit response fixture → apply → re-save) preserves every numeric field on every day.

## Out of scope

- Modifying `plan_generator.py` or any Phase 1 file (legacy stays intact per File 00-index rule #7).
- Automatic LLM invocation of any kind (no subprocess to `claude`, no shell-out to Gemini CLI).
- Validating the **content quality** of user-pasted descriptions (e.g., language, tone). Phase 2 only validates schema + numeric non-mutation.
- CLI argument parsing refactor in `push_plan.py` beyond the two new flags. `parse_args` extension stays minimal.

## Migration from existing committed plan

- `09-prose-generator.md` will be rewritten by `writing-plans` (not patched in place) because the task scope, file list, and test set all change.
- Old commit `4fa3f14` stays in history; new plan replaces it under the same filename. Memory entry `coach_phase2_plan.md` is updated to point at the new plan.
- `10-integration.md` receives an in-place patch (section marked "Revised 2026-04-19 — API-free prose flow") preserving T45–T46 numbering.
