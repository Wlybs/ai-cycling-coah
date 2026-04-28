"""Phase 3 — heuristic advisory hook.

Pure function: reads ledger + deep_analysis snapshots, returns a list of
human-readable advisory strings. No side effects beyond a single JSONL log
event per detector. Never raises on missing inputs.

API_FREE: no LLM SDK import. NO_NEW_DEPS: stdlib + Phase 1 logger +
Phase 3 LedgerReader only.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader

CONSENSUS_OVERDUE_DAYS: int = 14
STIMULUS_DECLINE_WINDOW: int = 3


def suggest_actions(
    ledger_path: Path,
    periodization_dir: Path,
    deep_analysis_dir: Path,
    today: date | None = None,
) -> list[str]:
    """Return advisory lines based on 4 trigger conditions.

    Triggers (in stable order):
      1. phase_transition entry within last 7 days
      2. latest weekly_plan_assembled has non-empty payload.violations
      3. consensus_verdict absent OR older than CONSENSUS_OVERDUE_DAYS
      4. last STIMULUS_DECLINE_WINDOW dated deep_analysis summaries strictly
         monotonic non-increasing in stimulus_score

    Returns list[str] (possibly empty). Never raises on missing inputs.
    """
    if today is None:
        today = date.today()
    logger = get_logger("suggester")
    reader: LedgerReader | None
    if ledger_path.exists():
        reader = LedgerReader(ledger_path)
    else:
        reader = None

    out: list[str] = []
    for name, fn in (
        ("phase_transition_this_week",
         lambda: _trigger_phase_transition_this_week(reader, today)),
        ("safety_violation_in_latest_plan",
         lambda: _trigger_safety_violation_in_latest_plan(reader)),
        ("consensus_overdue",
         lambda: _trigger_consensus_overdue(reader, today)),
        ("stimulus_score_decline",
         lambda: _trigger_stimulus_score_decline(deep_analysis_dir)),
    ):
        line = fn()
        logger.event(action="suggest", trigger=name, fired=bool(line))
        if line is not None:
            out.append(line)
    return out


def _trigger_phase_transition_this_week(
    reader: LedgerReader | None, today: date,
) -> str | None:
    if reader is None:
        return None
    since = datetime.combine(today - timedelta(days=7), time.min,
                             tzinfo=timezone.utc)
    until = datetime.combine(today + timedelta(days=1), time.min,
                             tzinfo=timezone.utc)
    hits = reader.query(decision_type="phase_transition",
                        since=since, until=until)
    if not hits:
        return None
    return ("本周 Phase Detector 触发了阶段切换；"
            "建议跑 run_consensus.py 复核新阶段计划。")


def _trigger_safety_violation_in_latest_plan(
    reader: LedgerReader | None,
) -> str | None:
    if reader is None:
        return None
    hits = reader.query(decision_type="weekly_plan_assembled")
    if not hits:
        return None
    latest = hits[-1]
    violations = (latest.payload or {}).get("violations", [])
    if not isinstance(violations, list) or not violations:
        return None
    return (f"最近一次 weekly_plan_assembled 含 {len(violations)} 条 "
            f"safety guard violation；建议跑 run_consensus.py 让 Critic 审查。")


def _trigger_consensus_overdue(
    reader: LedgerReader | None, today: date,
) -> str | None:
    if reader is None:
        # No ledger ⇒ never run consensus ⇒ overdue.
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    hits = reader.query(decision_type="consensus_verdict")
    if not hits:
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    latest = hits[-1]
    age_days = (today - latest.timestamp.date()).days
    if age_days > CONSENSUS_OVERDUE_DAYS:
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    return None


def _trigger_stimulus_score_decline(deep_analysis_dir: Path) -> str | None:
    if not deep_analysis_dir.exists():
        return None
    dated = sorted(
        p for p in deep_analysis_dir.glob("summary_*.json")
        if p.name != "summary_latest.json"
    )
    if len(dated) < STIMULUS_DECLINE_WINDOW:
        return None
    window = dated[-STIMULUS_DECLINE_WINDOW:]
    scores: list[float] = []
    for p in window:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            scores.append(float(doc.get("stimulus_score")))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    monotonic_non_increasing = all(
        scores[i] >= scores[i + 1] for i in range(len(scores) - 1)
    )
    strictly_decreasing_overall = scores[0] > scores[-1]
    if monotonic_non_increasing and strictly_decreasing_overall:
        return (f"最近 {STIMULUS_DECLINE_WINDOW} 次 deep_analysis "
                f"stimulus_score 单调下滑；建议核查训练负荷或休息状态。")
    return None
