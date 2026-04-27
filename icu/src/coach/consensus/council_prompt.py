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
