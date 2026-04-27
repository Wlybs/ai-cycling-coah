"""Council prompt assembler — 4 段 markdown 拼装 + UNDER-DOSED 触发器.

输入：VerdictRequest（plan + athlete_state + physiology + wellness_trend +
periodization_summary）+ 可选 history triplets。

输出：纯 markdown 字符串。本模块不做 LLM call、不做网络请求；调用方
（scripts/run_consensus.py）负责落盘并提示用户粘贴到 Gemini。

API_FREE：仅做字符串拼装与字典查找；本模块不调用任何 LLM SDK。
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


# ---------- UNDER-DOSED 6-trigger detector ----------

# Tunable thresholds (lifted from blueprint §4.6 + reasonable defaults):
_BUILD_HARD_DAYS_FLOOR = 2          # T1: BUILD needs >=2 HIGH-tier days
_HI_TOLERANCE_FLOOR_MIN = 18        # T2: high-tolerance class baseline
_TSS_BAND_LOWER_MULT = 5.0          # T3: lower edge of "acceptable load
                                    #     band" ~= 5 * CTL (TSS/week)
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

    # -- T2: hi-intensity work minutes (per-session, see spec Open Q #3) --
    # `duration_min` is a coarse proxy for "work-interval minutes". The
    # 18min floor is the high-tolerance baseline (blueprint §4.6); a 75min
    # session with an 18min work-block passes; a 10min session does not.
    hi_sessions: list[int] = []
    for d in days:
        if d.get("training_type") in ("VO2max", "Threshold"):
            try:
                hi_sessions.append(int(d.get("duration_min") or 0))
            except (TypeError, ValueError):
                continue
    short_hi = any(0 < m < _HI_TOLERANCE_FLOOR_MIN for m in hi_sessions)
    no_hi = sum(hi_sessions) == 0
    if short_hi or no_hi:
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
