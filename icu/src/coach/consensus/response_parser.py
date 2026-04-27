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
