"""HistoryInjector — 把 ledger 中相似 context 的历史压成 ≤8 条三元组。

调用入口：compress_history(reader, athlete_state, *, limit=8)
返回：list[HistoryTriplet]，按 ledger entry_id 降序（最新在前）。

约束：
- 不 import google.genai；不做任何 LLM/heuristic 数值估算。
- outcome 缺失即写 "outcome_pending"；后续 deep_analysis stimulus_score 入库后
  T65/T66 的渲染层可重读 ledger 升级该字段（不在本文件职责内）。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef, DecisionEntry

_log = get_logger("consensus")

OUTCOME_PENDING = "outcome_pending"
DEFAULT_CTL_TOLERANCE = 5.0


class HistoryTriplet(BaseModel):
    """One row of Section C — context-verdict-outcome triplet."""

    model_config = {"frozen": True}

    plan_entry_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    verdict: str = Field(default="")
    outcome: str = Field(default=OUTCOME_PENDING)


def compress_history(
    reader: LedgerReader,
    athlete_state: AthleteStateRef,
    *,
    limit: int = 8,
    ctl_tolerance: float = DEFAULT_CTL_TOLERANCE,
) -> list[HistoryTriplet]:
    """Return ≤limit most-recent triplets for similar BUILD-week contexts.

    `verdict` field is currently always empty string — it captures any
    *plan-time* verdict embedded in the weekly_plan_assembled payload itself,
    which Phase 2 ingester does not yet emit. Kept on the model for future
    use; do not synthesize.
    """
    plans = reader.query_similar(
        athlete_state=athlete_state,
        decision_type="weekly_plan_assembled",
        ctl_tolerance=ctl_tolerance,
        phase_match=True,
        limit=limit,
    )
    if not plans:
        return []

    # Scoop the entire ledger once; we'll filter out follow-on entries by
    # `payload.supersedes_plan_entry_id == plan.entry_id` (preferred) or by
    # falling back to "any later entry of consensus_verdict / adaptation_verdict
    # whose timestamp is within 28 days of plan.timestamp".
    all_entries = reader.query()
    follow_on_index: dict[str, list[DecisionEntry]] = {}
    for e in all_entries:
        if e.decision_type not in ("consensus_verdict", "adaptation_verdict"):
            continue
        link = e.payload.get("supersedes_plan_entry_id")
        if link:
            follow_on_index.setdefault(link, []).append(e)

    triplets: list[HistoryTriplet] = []
    for plan in plans:
        outcome = _resolve_outcome(plan, follow_on_index, all_entries)
        ctx = {
            "plan_period": plan.payload.get("plan_period", ""),
            "total_tss": plan.payload.get("total_tss"),
            "ctl": plan.athlete_state_ref.ctl,
            "phase": plan.athlete_state_ref.phase,
            "week_of_year": plan.athlete_state_ref.week_of_year,
        }
        triplets.append(HistoryTriplet(
            plan_entry_id=plan.entry_id,
            context=ctx,
            verdict=plan.payload.get("plan_time_verdict", ""),
            outcome=outcome,
        ))

    _log.event("consensus_history_compressed",
               n_plans=len(plans), n_triplets=len(triplets),
               n_outcome_pending=sum(1 for t in triplets
                                     if t.outcome == OUTCOME_PENDING))
    return triplets


def _resolve_outcome(plan: DecisionEntry,
                     follow_on_index: dict[str, list[DecisionEntry]],
                     all_entries: list[DecisionEntry]) -> str:
    linked = follow_on_index.get(plan.entry_id)
    if linked:
        # Prefer consensus_verdict over adaptation_verdict; take latest of each.
        consensus = [e for e in linked if e.decision_type == "consensus_verdict"]
        if consensus:
            latest = max(consensus, key=lambda e: e.entry_id)
            v = latest.payload.get("verdict", "?")
            c = latest.payload.get("confidence")
            return f"consensus.{v}@{c:.2f}" if isinstance(c, (int, float)) \
                else f"consensus.{v}"
        adaptation = [e for e in linked
                      if e.decision_type == "adaptation_verdict"]
        if adaptation:
            latest = max(adaptation, key=lambda e: e.entry_id)
            return f"adapter.{latest.payload.get('verdict', '?')}"
    return OUTCOME_PENDING
