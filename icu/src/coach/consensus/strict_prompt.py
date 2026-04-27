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
