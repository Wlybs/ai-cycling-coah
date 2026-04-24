"""Phase 2 File 09 — prose prompt rendering + user response merge.

No LLM API call. `render_prose_prompt` builds the text the user pastes into
Claude Code / Gemini CLI. `apply_prose_response` merges the user's pasted
JSON back into the WeeklyPlan with a two-layer numeric-field guard:

1. `_ProseResponse` / `_ProseDay` ignore any field other than
   `coaching_summary` and `days[*].{date, description}`, so malicious numeric
   fields are dropped at parse time.
2. The merge itself uses `model_copy(update={...})` on only those two text
   fields, so no numeric field is structurally reachable from the merge path.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .plan_writer import save_weekly_plan
from .types import WeeklyPlan

PROMPT_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "prompts" / "session_designer" / "prose_prompt.md"
)


class _ProseDay(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    description: str


class _ProseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    coaching_summary: str
    days: list[_ProseDay]


def _load_prompt_template() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"prose prompt template not found: {PROMPT_FILE}"
        ) from None


def render_prose_prompt(
    plan: WeeklyPlan,
    phase_rationale: str,
    phase_value: str,
    physiology_summary: dict[str, object],
    violations: list[dict],
) -> str:
    base = _load_prompt_template()
    physio_line = (
        f"CP={physiology_summary.get('cp')}W / "
        f"W'={physiology_summary.get('w_prime')}J / "
        f"durability decay 60s={physiology_summary.get('durability_60s_pct')}%/1000kJ / "
        f"knee_flag={physiology_summary.get('knee_flag')}"
    )
    return (
        base
        + "\n\n# 实际输入\n"
        + f"Phase: {phase_value}\n"
        + f"PhaseIntent rationale: {phase_rationale}\n"
        + f"WeeklyPlan (JSON): {json.dumps(plan.model_dump(), ensure_ascii=False)}\n"
        + f"Violations remaining (JSON): {json.dumps(violations, ensure_ascii=False)}\n"
        + f"Physiology: {physio_line}\n"
    )


def apply_prose_response(
    plan: WeeklyPlan,
    response: dict,
) -> WeeklyPlan:
    env = _ProseResponse.model_validate(response)
    if len(env.days) != 7:
        raise ValueError(
            f"prose response must have exactly 7 days, got {len(env.days)}"
        )
    plan_dates = {d.date for d in plan.days}
    response_dates = {d.date for d in env.days}
    if plan_dates != response_dates:
        missing = sorted(plan_dates - response_dates)
        extra = sorted(response_dates - plan_dates)
        raise ValueError(
            f"prose response date set mismatch. "
            f"missing={missing} extra={extra}"
        )
    by_date = {d.date: d for d in env.days}
    new_days = [
        day.model_copy(update={"description": by_date[day.date].description})
        for day in plan.days
    ]
    return plan.model_copy(update={
        "coaching_summary": env.coaching_summary,
        "days": new_days,
    })


def load_and_apply_prose(
    plan_path: Path,
    response_path: Path,
    out_dir: Path,
) -> dict[str, Path]:
    """Read plan.json + response.json, merge prose into plan, and overwrite
    plan_YYYYMMDD.{json,md} only. The `.trace.json` and `.prose_prompt.md`
    from the initial save are intentionally left untouched — they represent
    pre-enrichment artifacts whose content does not change with prose merge.
    """
    plan = WeeklyPlan.model_validate_json(
        plan_path.read_text(encoding="utf-8")
    )
    response_doc = json.loads(response_path.read_text(encoding="utf-8"))
    enriched = apply_prose_response(plan, response_doc)
    return save_weekly_plan(
        plan=enriched,
        out_dir=out_dir,
        # prose_prompt=None, trace=None → only .json + .md get rewritten
    )
