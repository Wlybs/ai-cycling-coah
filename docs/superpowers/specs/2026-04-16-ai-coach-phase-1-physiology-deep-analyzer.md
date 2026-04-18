# AI Coach — Phase 1: Physiology Model + Deep Analyzer

**Date**: 2026-04-16
**Phase**: 1 of 4
**Blueprint**: [2026-04-16-ai-coach-scheme-4-blueprint.md](./2026-04-16-ai-coach-scheme-4-blueprint.md)
**Status**: Design approved; pending implementation plan

## Goal

Build the personalized physiological foundation (components 1 and 4 of the Scheme 4 blueprint) on top of which all subsequent phases depend. On the day Phase 1 ships, the coach must already deliver materially better plan quality and analysis depth without waiting for Phase 2.

## Scope

In scope:
1. `icu/src/coach/physiology/` — CP/W' fitter, W' balance real-time model, durability curve, individual response profile
2. `icu/src/coach/deep_analyzer/` — feature detector, relevance router, six sub-analyzers, report composer
3. Integration hooks into `icu/scripts/sync_data.py`
4. Partial observability (JSONL logging, `--debug`, decision trace files)
5. Minimum-invasive injection of physiology + deep-analysis outputs into the existing `plan_generator.py` prompt (no refactor of plan_generator's core logic — that belongs to Phase 2)

Out of scope (deferred to later phases):
- Periodization engine
- Session designer rewrite
- Multi-expert consensus
- Adaptation engine, decision ledger
- Evidence RAG
- Race-specific module
- Unified persona merge

## Architecture

### Data Flow

```
icu_data_warehouse/ (raw sync data)
        │
        ├──► physiology/ ──► coach_memory/physiology/{cp_w, durability, response_profile}.json
        │                                │
        │                                ▼
        └──► deep_analyzer/ ──► coach_memory/deep_analysis/<activity_id>.md
                                         + summary_latest.json
                                                   │
                                                   ▼
                              (read by plan_generator.py prompt + Coach Brief)
```

All numeric reasoning lives in Python. Gemini is called exactly once per deep-analysis report, strictly for prose composition from pre-computed findings JSON.

### Module Boundaries

Each module is a **pure function** over known inputs with typed outputs. No hidden state.

```
icu/src/coach/
├── physiology/
│   ├── __init__.py
│   ├── cp_w_fitter.py          # fit_cp_w(mmp_history) -> CPWModel
│   ├── w_balance_model.py      # compute_w_balance(streams, cp_model) -> WBalanceSeries
│   ├── durability_model.py     # fit_durability(activities, cp_model) -> DurabilityCurve
│   ├── response_profile.py     # build_profile(sessions, wellness) -> ResponseProfile
│   └── refresher.py            # facade: refresh_all() orchestrates the four above
└── deep_analyzer/
    ├── __init__.py
    ├── feature_detector.py     # detect_features(activity, streams) -> Features
    ├── router.py               # route(features) -> Dict[SubAnalyzer, float] (relevance)
    ├── sub_analyzers/
    │   ├── pacing.py           # analyze(activity, physiology) -> Findings
    │   ├── w_balance.py
    │   ├── durability.py
    │   ├── climbing.py
    │   ├── target_align.py
    │   └── historical_cmp.py
    ├── report_composer.py      # compose(findings_set, athlete_profile) -> Markdown (Gemini)
    └── orchestrator.py         # facade: analyze_new() and analyze_one(activity_id)
```

## Component Detail

### 1. Physiology Model Layer

#### 1.1 CP/W' Fitter — `cp_w_fitter.py`
- **Model**: 3-parameter hyperbolic `P(t) = CP + W' / (t − t_k)` where `t_k` ∈ [−20, −5] seconds
- **Inputs**: All mean-max power data from `icu_data_warehouse/3_PowerData/` — 90-day window + career peak
- **Fitting range**: 120–1200 seconds (canonical CP band), with 5–60 s data constraining W' via anchor residuals
- **Method**: `scipy.optimize.curve_fit` with bounded parameters; report R² and residual distribution; fall back to 2-parameter model if 3-parameter R² < 0.90
- **Output file**: `coach_memory/physiology/cp_w_current.json`
  ```json
  {
    "generated_at": "ISO-8601",
    "window_days": 90,
    "cp_watts": <int>,
    "w_prime_joules": <int>,
    "t_k_seconds": <float>,
    "model": "3-param-hyperbolic" | "2-param-hyperbolic",
    "fit_r_squared": <float>,
    "data_points_used": [[duration_s, power_w], ...],
    "athlete_ftp_set": <int>,
    "cp_vs_ftp_delta_w": <int>
  }
  ```
- **Monthly snapshot**: Additional write to `coach_memory/physiology/history/cp_w_<YYYY-MM>.json` on the first refresh of each calendar month
- **Caching**: Skip refit if the data hash of the input MMP set is unchanged since last run
- **Update frequency**: Every `sync_data.py` run (cheap when cached)

#### 1.2 W' Balance Real-time Model — `w_balance_model.py`
- **Model**: Skiba-Clarke reversible integral
  - When `P(t) > CP`: `W'(t) = W'(t − 1) − (P(t) − CP) · Δt`
  - When `P(t) ≤ CP`: `W'(t) = W' − (W' − W'(t − 1)) · exp(−Δt / τ)`
- **τ (recovery time constant)**: Skiba 2012 personalized formula `τ = 546 · exp(−0.01 · D_CP) + 316`, where `D_CP = CP − mean_power_below_cp`
- **Inputs**: Activity streams (1 Hz power series) from `5_Activities_Detail/<id>/streams.json` + current CP/W' from the fitter
- **Output file**: `icu_data_warehouse/5_Activities_Detail/<activity_id>_wbalance.json`
  ```json
  {
    "activity_id": "i...",
    "cp_used_w": <int>,
    "w_prime_used_j": <int>,
    "tau_s": <float>,
    "min_w_bal_j": <int>,
    "min_w_bal_pct": <float>,
    "min_w_bal_timestamp_s": <int>,
    "seconds_below_15pct": <int>,
    "laps": [
      {
        "lap_index": <int>,
        "type": "work" | "recovery" | "steady",
        "w_bal_start_j": <int>,
        "w_bal_end_j": <int>,
        "depletion_pct": <float>
      }
    ],
    "w_bal_series_1hz": [<int>, ...]
  }
  ```
- **Update frequency**: Per new activity
- **Error policy**: Hard failure recorded in `deep_analysis/_state.json` errors; downstream `w_balance` sub-analyzer marked "insufficient data" and skipped for that activity only

#### 1.3 Durability Curve — `durability_model.py`
- **Inputs**: All activities ≥ 2 hours in the last 180 days with valid power streams
- **Method**: For each ride, compute MMP at [60, 300, 1200] seconds under four "fresh-state" conditions:
  - First 500 kJ (fresh baseline)
  - After cumulative 1500 kJ
  - After cumulative 2000 kJ
  - After cumulative 2500 kJ
- Aggregate across rides; fit a decay rate (exponential or power-law) for each duration bucket
- **Output file**: `coach_memory/physiology/durability.json`
  ```json
  {
    "generated_at": "...",
    "sample_size_rides": <int>,
    "fresh_mmp_w": {"60s": <int>, "300s": <int>, "1200s": <int>},
    "fatigued_mmp_w": {
      "1500kj": {"60s": <int>, "300s": <int>, "1200s": <int>},
      "2000kj": {...},
      "2500kj": {...}
    },
    "decay_rate_pct_per_1000kj": {"60s": <float>, "300s": <float>, "1200s": <float>},
    "percentile_vs_class_estimate": "top_25"  // optional; only if enough population data
  }
  ```
- **Update frequency**: Weekly (more expensive; not every sync)

#### 1.4 Individual Response Profile — `response_profile.py`
- **Inputs**: Last 60 days of completed sessions (from `4_Activities_List/` + `5_Activities_Detail/`) + wellness data (`2_Wellness/`)
- **Method**: For each canonical session type (Aerobic / Tempo / Threshold / VO2max / Neuromuscular / Race):
  - Count sessions in window
  - Average TSS absorbed
  - Average next-day HRV delta vs 30-day baseline
  - Average next-day RHR delta
  - Target adherence rate (actual IF within ±0.05 of planned IF where planned IF is recorded)
  - Assign tolerance class (`low` / `moderate` / `high`) by rule table on next-day recovery signals
- Also tracks "knee loading flag": cumulative standing-climb minutes (inferred from cadence + gradient joint distribution) and average HR drift during standing segments
- **Output file**: `coach_memory/physiology/response_profile.json`
  ```json
  {
    "generated_at": "...",
    "window_days": 60,
    "types": {
      "vo2max": {
        "sessions_n": <int>,
        "avg_tss": <int>,
        "next_day_hrv_delta_pct": <float>,
        "next_day_rhr_delta_bpm": <float>,
        "avg_target_adherence": <float>,
        "tolerance_class": "low" | "moderate" | "high",
        "recommended_min_interval_hours": <int>
      },
      ...
    },
    "knee_loading": {
      "standing_climb_minutes_90d": <int>,
      "avg_hr_drift_bpm_standing": <float>,
      "flag": null | "watch" | "caution"
    }
  }
  ```
- **Update frequency**: Weekly

#### 1.5 Facade — `refresher.py`
Single entry point `refresh_all()` that runs the four subroutines in order, catches per-subroutine exceptions, writes partial results, returns a status summary. Invoked from `sync_data.py` and from `scripts/refresh_physiology.py` (standalone debug).

### 2. Deep Analyzer

#### 2.1 Feature Detector — `feature_detector.py`
Pure function scanning activity metadata + streams. Output:
```json
{
  "has_intervals": <bool>,
  "is_race": <bool>,
  "has_climbing": <bool>,
  "is_endurance_long": <bool>,
  "has_anomaly": <bool>,
  "target_type_claimed": <str | null>,
  "w_prime_depleted": <bool>,
  "heat_stress": <bool>,
  "duration_seconds": <int>,
  "total_kj": <int>
}
```

Detection rules:
- `has_intervals`: exists lap with IF > 0.85 and 30 ≤ duration ≤ 600 s
- `is_race`: ICU type = "Race" OR (NP > 0.95 · CP AND max_HR > 0.95 · HR_max). `HR_max` sourced from `icu_data_warehouse/1_Profile/athlete.json`'s `hr_max` field; if absent, fall back to max observed HR across last 180 days.
- `has_climbing`: elevation_gain > 300 m OR sustained gradient > 5% for > 180 s
- `is_endurance_long`: duration > 7200 s
- `has_anomaly`: IF > 0.90 OR decoupling_pct > 8 OR HR drift > 10 bpm in Z2. `decoupling_pct` is read from the ICU-provided activity metric (field `decoupling` in `5_Activities_Detail/<id>/activity.json`); if absent, compute from power/HR streams (first-half vs second-half P:HR ratio delta).
- `target_type_claimed`: reads from the active plan's scheduled session type for that date first (if exists in `coach_memory/active_plan.md` or `plan_adherence.json`); falls back to ICU session `type` field.
- `w_prime_depleted`: min_w_bal_pct from physiology output < 20
- `heat_stress`: optional. Only evaluated if `avg_temperature_c` field is present in `5_Activities_Detail/<id>/activity.json`; value > 28 sets true; missing field → false (not unknown).

#### 2.2 Relevance Router — `router.py`
For each sub-analyzer, a relevance score in [0, 1]. Threshold: ≥ 0.5 runs it. `is_race` forces all six.

| Sub-analyzer | Relevance formula |
|---|---|
| `pacing` | 0.9 if has_intervals; else 0.8 if is_race; else 0.2 |
| `w_balance` | 0.95 if has_intervals; else 0.9 if w_prime_depleted; else 0.3 |
| `durability` | 0.9 if is_endurance_long; else 0.4 |
| `climbing` | 0.9 if has_climbing; else 0.1 |
| `target_align` | 0.85 if target_type_claimed; else 0.3 |
| `historical_cmp` | 0.6 always |

#### 2.3 Sub-Analyzers (each in `sub_analyzers/<name>.py`)

All share an interface:
```python
def analyze(activity: Activity, physiology: PhysiologyBundle) -> Findings
```

Each returns a structured `Findings` object (Pydantic) with:
- `metrics`: quantitative outputs (not restated raw ICU metrics — derived insights only)
- `verdict`: one-line categorical call
- `evidence`: list of `(statement, data_ref)` tuples tying each claim to a specific data point

##### 2.3.1 `pacing.py`
- Computes VI per lap (NP/AP ratio)
- Identifies first lap with VI > rest-mean + 0.10 (pacing break point)
- First-third vs last-third work power delta (front-loaded detection)
- Verdict categories: `起步冒进` | `节奏平稳` | `后段崩盘` | `均衡分布`

##### 2.3.2 `w_balance.py`
- Reads `<activity_id>_wbalance.json`
- Per-interval depletion percentage
- Recovery adequacy: W'bal return fraction during each rest period vs "sustainable" target (≥ 60%)
- Danger seconds below 15% threshold
- Theoretical hold-time extension per interval: based on CP model, estimates `Δt_additional` before W'bal depletes to 0
- Verdict categories: `W' 管理得当` | `W' 管理失衡` | `过度依赖 W' 债务` | `数据不足`

##### 2.3.3 `durability.py`
- Computes this-ride MMP at 1500 / 2000 / 2500 kJ fatigue checkpoints (if ride spans the checkpoint)
- Compares to personal durability curve
- Flags: `durability_bonus_pct` (positive if above baseline) or `durability_deficit_pct`
- Cross-references with nutrition flag if deficit observed: "possible fueling issue"

##### 2.3.4 `climbing.py`
- Segments climbs by sustained gradient > 3% for > 180 s
- Per-climb: avg power, avg HR, W/kg, VAM (vertical ascent meters per hour), cadence histogram
- Standing/seated inference: low cadence (< 75 rpm) + high power (> CP · 1.1) ≈ standing
- Writes cumulative standing minutes back to `response_profile` flag
- Verdict categories: `爬坡表现超预期` | `持平` | `疲劳衰退显著`

##### 2.3.5 `target_align.py`
- Reads planned type + planned power range from the same source `feature_detector` uses for `target_type_claimed` (active plan first, ICU session type second)
- When only a type is known but no explicit power range, derive the default range from personal CP (e.g., VO2max = [1.06·CP, 1.20·CP], Threshold = [0.95·CP, 1.05·CP])
- Computes accumulated time-in-target-zone (work segments only, not recoveries)
- Type-specific thresholds:
  - VO2max: ≥ 12 min in Z5 required for "hit"
  - Threshold: ≥ 20 min in Z4 required for "hit"
  - Sweet-spot: ≥ 40 min in Z3-high required for "hit"
  - Tempo: ≥ 30 min in Z3 required for "hit"
- On miss: computes the delta + flags "coach may be under-prescribing" if three consecutive misses in same type
- Verdict categories: `命中` | `部分命中` | `刺激错配` | `目标缺失`

##### 2.3.6 `historical_cmp.py`
- Queries last 90 days for same-type sessions within ±20% duration
- If ≥ 3 comparables: computes deltas on NP, HR, decoupling, W'bal depletion pattern, durability score
- Trend verdict: `进步` | `持平` | `退步` + confidence tier

#### 2.4 Report Composer — `report_composer.py`
Single Gemini call per activity. Prompt template binds:
- Athlete profile (static: 62 kg, Type II dominant, ACL post-op right knee)
- Personal physiology (dynamic: current CP, W', durability stats, response profile)
- Pre-computed findings JSON from activated sub-analyzers
- Session summary line (auto-generated: duration, NP, TSS, IF, kJ)

Output markdown structure (strictly enforced):
```markdown
# 活动 <id> 深度分析 — <YYYY-MM-DD> <type>

**Session 概要** · <auto-generated line>

## 今日结论
<1-2 sentence verdict>

## 关键发现

### 1. <theme>
> 证据: <specific data quote>
- 结论: <interpretation>
- 联系画像: <tie-in to athlete profile>

### 2. <theme>
...

## 下次怎么办
1. <actionable instruction>
2. <actionable instruction>

## 附:本次激活的分析维度
<checkbox summary>
```

Hard rules in prompt:
- No restating raw ICU-visible metrics (no "NP was X W, IF was Y")
- Every bullet in 关键发现 must have `> 证据:` line
- 下次怎么办 items must be actionable (valid input for next plan_generator run)
- Conclusions, not observations

#### 2.5 Orchestrator — `orchestrator.py`
- `analyze_new()`: reads `_state.json`, finds activities newer than `last_analyzed_activity_id`, invokes `analyze_one` on each (asyncio worker pool, max 4 parallel Gemini calls)
- `analyze_one(activity_id)`: feature_detector → router → parallel sub-analyzers (asyncio) → report_composer → writes outputs + trace file
- On completion: updates `_state.json`, updates `summary_latest.json` with the most recent report's headline

### 3. Outputs

#### 3.1 Physiology outputs
```
coach_memory/physiology/
├── cp_w_current.json
├── durability.json
├── response_profile.json
└── history/
    └── cp_w_<YYYY-MM>.json
```

Plus per-activity W' balance:
```
icu_data_warehouse/5_Activities_Detail/
├── <activity_id>_wbalance.json
└── ...
```

#### 3.2 Deep analysis outputs
```
coach_memory/deep_analysis/
├── _state.json                    # {last_analyzed_activity_id, last_analyzed_at, errors: [...]}
├── summary_latest.json            # headline + structured hints for plan_generator + Coach Brief
├── <activity_id>.md               # human-facing report
└── <activity_id>.trace.json       # features, relevance scores, activated set, raw findings
```

`summary_latest.json` schema:
```json
{
  "activity_id": "...",
  "analyzed_at": "...",
  "sub_analyzers_run": [...],
  "headline_verdict": "...",
  "stimulus_score": <float 0-1>,
  "progression_flag": "progression" | "flat" | "regression_mild" | "regression_severe",
  "next_plan_hints": [<str>, ...],
  "knee_flag": null | "watch" | "caution"
}
```

### 4. Integration

#### 4.1 `scripts/sync_data.py` tail
Append after existing `build_memory.py`:
```python
from icu.src.coach.physiology.refresher import refresh_all as refresh_physiology
from icu.src.coach.deep_analyzer.orchestrator import analyze_new
from icu.src.coach.brief_updater import update_coach_brief

refresh_physiology()        # soft-fail; logs error but sync continues
analyze_new()               # async internally; 4-worker pool for Gemini
update_coach_brief()        # refreshes GEMINI.md Coach Brief injection block
```

Each call wrapped in try/except that writes an error to its module log but does not halt `sync_data.py`.

#### 4.2 `plan_generator.py` minimum-invasive injection
Add a prompt-injection helper (do not rewrite plan_generator yet — Phase 2's job):
```python
def inject_phase1_context(base_prompt: str) -> str:
    physiology = load_if_exists("coach_memory/physiology/cp_w_current.json")
    durability = load_if_exists("coach_memory/physiology/durability.json")
    response   = load_if_exists("coach_memory/physiology/response_profile.json")
    summary    = load_if_exists("coach_memory/deep_analysis/summary_latest.json")
    recent_md  = tail_reports("coach_memory/deep_analysis/*.md", n=5)

    if not any([physiology, durability, response, summary]):
        return base_prompt  # graceful degradation if Phase 1 outputs missing

    return base_prompt + render_phase1_context_block(
        physiology, durability, response, summary, recent_md
    )
```

The injected block instructs Gemini: "use these personal CP/W' instead of set FTP", "respect tolerance classes", "honor hints from recent 下次怎么办 lines", "raise weekly TSS if recent stimulus scores indicate under-prescription".

This is intentionally ugly glue — Phase 2 will replace plan_generator wholesale. Phase 1's job is to make plan quality better *today* without refactoring.

#### 4.3 Coach Brief (GEMINI.md opening) enhancement
Extend existing Coach Brief generation to include:
- Most recent deep-analysis headline verdict
- Current stimulus score trend (3-session average)
- Active knee flag (if any)
- Consecutive regression count (if any)

#### 4.4 Backfill command
`scripts/analyze_rides.py --backfill --since <ISO_DATE>`
- Defaults to only interval sessions, races, long climbs (filters via feature_detector)
- User-initiated (not auto); keeps first-install cost controlled

## Error Handling

| Layer | Failure behavior | Rationale |
|---|---|---|
| CP/W' fitter | Soft fail — retain last snapshot, mark `stale: true` | Occasional fit failure must not break the pipeline |
| W' balance per-activity | Hard fail — record in `_state.json` errors; w_balance sub-analyzer skipped for that activity only | Data quality issues must surface |
| Feature detector | Conservative fallback — any throw → field is False, only routing narrows | Never let dirty data trigger analysis |
| Sub-analyzer | Isolated — one failure does not affect the other five | Parallel isolation |
| Report composer (Gemini) | 3 retries with exponential backoff; final failure saves raw findings to `<id>.raw.json`, marks report pending | Cloud APIs are unreliable |
| `sync_data.py` outer | Never blocks existing sync — each new call is try/except → log → continue | Protect the working pipeline |

**Invariant**: Nothing in Phase 1 can break the existing system. Disabling Phase 1 must be as simple as removing the three new calls from `sync_data.py`.

## Observability

### Structured logging
- Per-module JSONL logs in `icu/logs/<module>.log`
- Mandatory fields: `ts, module, activity_id, action, duration_ms, status, error`
- Gemini calls additionally log: `prompt_token_count, completion_token_count, response_snippet_200, parsed_ok`

### Trace files
Every deep-analysis report has a sibling `<id>.trace.json`:
- All feature values
- Relevance score for each sub-analyzer
- Activated set
- Raw findings JSON per sub-analyzer
- Enables "why did analyzer X not run?" audits

### CLI tools
- `python -m icu.scripts.analyze_rides --activity <id> --dry-run` — full pipeline minus Gemini; prints findings
- `python -m icu.scripts.analyze_rides --activity <id> --replay` — rerun and overwrite
- `python -m icu.scripts.physiology_audit` — prints current vs 30-day-ago CP / W' / durability / response profile

### `--debug` switch
- Log level DEBUG
- Gemini raw request/response saved to `icu/logs/gemini_raw/<ts>_<id>.json`
- Per-step timing printed

## Testing

### Unit tests (pure computation; coverage target ≥ 90%)
- `cp_w_fitter`: synthetic MMP → CP/W' within ±1%; noisy data → R² reported correctly
- `w_balance_model`: constant-power-above-CP scenario → exact W' depletion within ±2%
- `durability_model`: synthetic fatigue curve → fitted decay rate within ±5%
- `response_profile`: mock wellness series → correct tolerance-class classification
- `feature_detector`: fixture activities → correct feature vectors

### Integration tests (with real de-identified fixtures)
- 3–5 representative rides exported from user's warehouse (interval workout, race, long Z2, failed VO2, climbing ride)
- Each fixture has `<name>.expected.json` defining expected findings
- Sub-analyzer outputs compared against expected findings

### Report composer (structural assertions only)
- Fixed findings JSON input → assert output conforms to the Pydantic markdown schema
- Assert three top-level sections present; assert each 关键发现 bullet has `> 证据:` line; assert no raw-metric restatement heuristic violations
- No assertions on Chinese prose content (LLM output varies)

### End-to-end
- `tests/e2e/test_full_sync.py`: mocked ICU API; full `sync_data` → `refresh_physiology` → `analyze_new`; asserts `coach_memory/` output completeness

### Fixture strategy
- De-identified real-ride fixtures under `tests/fixtures/rides/` (git-ignored copies; user-local only)
- Synthetic fixtures committable for CI
- Each fixture includes `expected.json`

## Performance Budget

| Operation | Target |
|---|---|
| `refresh_physiology()` full run | < 30 s |
| Single activity deep analysis (pure Python) | < 5 s |
| Single activity report generation (Gemini) | < 15 s |
| `analyze_new()` with 4-worker pool, 10 new activities | < 60 s |
| `sync_data.py` full pipeline (current ~3 min → with Phase 1) | < 4 min |

## Dependencies

- `scipy` (curve fitting) — add to `requirements.txt`
- `numpy` (already present)
- `pandas` (already present)
- `pydantic` (already present)
- `asyncio` (stdlib)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| CP/W' fitting unstable on sparse data | 2-param fallback; report R²; skip downstream until confident |
| W' balance model sensitivity to τ formula | Log τ alongside every computation; allow per-athlete override via config |
| Gemini output drift breaks markdown schema | Pydantic validator; retry on schema failure; Phase 3 Critic model eventually adds extra quality gate |
| Backfill cost explosion | Default filter (interval/race/climb only); explicit `--backfill` opt-in |
| `plan_generator.py` prompt injection grows unwieldy | Accepted — Phase 2 will replace plan_generator; this is temporary glue |

## Success Criteria

Phase 1 is complete when:

1. `coach_memory/physiology/*.json` refreshes on every `sync_data.py` run with fit R² ≥ 0.90 on user's data
2. Deep analysis reports generated for all new interval / race / climbing activities with < 5% report-generation failure rate
3. Reports pass structural validation (three sections, every finding cites evidence, no raw-metric restatement)
4. `plan_generator.py` prompt now includes personalized CP/W', durability stats, response profile, and recent deep-analysis hints
5. All unit tests pass; integration tests pass on de-identified fixtures
6. Performance targets met
7. User confirms on at least one generated report: "this is a real coach-level analysis" (qualitative user acceptance)

## Rollback

Phase 1 is additive. Rollback = revert commits; the existing system returns unchanged. No irreversible data migrations.

## Next Phase

On Phase 1 completion, brainstorm Phase 2 (periodization engine + session designer rewrite) will begin — plan_generator's temporary injection glue is replaced with first-class architecture.

## Implementation Completed

Date: 2026-04-18
Real-warehouse CP fit R²: **0.916** (3-param hyperbolic, CP=306W, W'=20870J on 90-day MMP)
User acceptance: **yes** (v1 accepted after iterative refinement in 1.10–1.16; user quote: "现在第一版的这个报告我可以接受，如果之后在具体情况下出现其他问题的话，我们再进一步修改。")

Beyond the original T1–T24 plan, the following adjustments landed in this phase to make the pipeline work against the real warehouse and the user's actual workflow (no Gemini API key; coaches via Gemini CLI / Claude Code). Each is its own commit under `feat(coach-phase1): ... (Phase 1.N)`:

- **1.10 ICU schema adapter** (`src/coach/common/icu_loader.py`) — central adapter layer translating real ICU key names / file shapes / event structures to the Phase 1 internal schema; lets sub_analyzers stay untouched.
- **1.11 API-free pipeline** — no `GEMINI_API_KEY` anywhere; `report_composer.compose()` replaced by pure `build_prompt()`; orchestrator writes `<id>.prompt.md` for the athlete to paste into Gemini CLI / Claude Code coach mode.
- **1.12 Ask-first protocol + payload slim** — coach MUST ask 2–4 targeted questions before emitting a report; payload slimmed from 37KB to 6.8KB by dropping Run/Swim/Other sportSettings, physiology `data_points_used`, and `verdict='数据不足'` findings.
- **1.13 Intent routing in GEMINI.md** — Intent A/B/C forking so `分析我上次骑行` loads the right `.prompt.md` instead of running the legacy sync+brief pipeline.
- **1.13 ACL mention gate** — `ACL`/`右膝术后`/`半月板` forbidden unless `knee_loading.flag` non-null or user reports actual pain in Stage 1.
- **1.14 Per-interval payload + TSB-aware recovery** — zone-based `_classify_lap_type` (ICU's `type='WORK'` ignored); laps carry HR/cadence/W'bal_start_end/zone/label/strain; payload adds `form={ctl,atl,tsb}`/`feel`/`user_description`; system prompt mandates a Markdown interval-execution table + TSB-tiered recovery rules (no more "TSS>150 → recovery" reflex).
- **1.15 Raw-stream re-segmentation tool** (`src/coach/common/lap_segmenter.py` + `scripts/segment_lap.py`) — when user reports merged / double-pressed / group-ride laps, coach runs the segmenter to pull the real work segment out of the polluted aggregate. 1-based `lap_number` field added for display alignment with the ICU UI / 码表.
- **1.16 Segment HR/cadence + M:SS format + group-lap mandate** — segmenter emits per-sub-segment HR/cadence; durations ≥60s render as `M:SS min`; group-ride laps (user mentions 轮组/攻防/跟风) MUST emit full sub-segment Markdown table, no vague prose summaries.

Test suite baseline: **106 passed** (from 77 before T22).

Known follow-ups for Phase 2:
1. `8_Events/planned_type` lookup is best-effort (many ICU events carry generic categories like "WORKOUT"); `target_align` relevance stays low. Phase 2 session-designer should write structured event `sub_type` so this dimension activates reliably.
2. `hr_drift_z2_bpm` defaults to None (ICU doesn't expose this summary field). If Phase 2 wants the signal, compute from stream HR during z2 segments.
3. `--debug` + `icu/logs/gemini_raw/` raw-response capture was out-of-scope (pipeline is LLM-API-free, so the observability target shifted — save prompt.md + timestamp, which already happens).
4. Phase 2 `prose_generator` plan (`ai-coach-phase-2` branch, File 09) currently assumes a Gemini API client; must be re-planned under the "no API key" constraint — same API-free pattern as Phase 1.11 applies.
5. 16 of 55 legacy flat activity detail files (pre-2026-01-14) are silently skipped by `iter_activity_docs`. Phase 2 may want to re-sync those with `scripts/sync_activity_detail.py` if historical signal matters.
