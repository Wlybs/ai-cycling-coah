"""LedgerReader — 读 / 过滤 / 相似 context 检索 / 决策链追溯。

全量扫描 + 内存过滤。对 < 5 MB JSONL 足够快（< 100ms）；体量再大时
再考虑分段 / 索引（目前 YAGNI）。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.coach.common.logging import get_logger

from .types import AthleteStateRef, DecisionEntry, DecisionType

_log = get_logger("ledger")


class LedgerReader:
    """Read-only view over a single JSONL ledger file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    # ------- raw iteration -------

    def _iter_entries(self) -> Iterator[DecisionEntry]:
        """Yield entries in file order; skip malformed lines with a warning."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line_num, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    yield DecisionEntry.model_validate_json(line)
                except Exception as exc:
                    _log.event(
                        "ledger_line_skipped",
                        path=str(self.path),
                        line_num=line_num,
                        reason=str(exc),
                    )
                    continue

    # ------- query -------

    def query(
        self,
        *,
        decision_type: DecisionType | str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[DecisionEntry]:
        """Return entries matching filters, sorted ascending by entry_id (time).

        `limit` caps the result after sorting; the **most recent N** are returned.
        """
        matched: list[DecisionEntry] = []
        for entry in self._iter_entries():
            if decision_type is not None and entry.decision_type != decision_type:
                continue
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp > until:
                continue
            matched.append(entry)

        matched.sort(key=lambda e: e.entry_id)
        if limit is not None and len(matched) > limit:
            matched = matched[-limit:]
        return matched

    # ------- query_similar -------

    def query_similar(
        self,
        *,
        athlete_state: AthleteStateRef,
        decision_type: DecisionType | str,
        ctl_tolerance: float = 5.0,
        phase_match: bool = True,
        limit: int = 5,
    ) -> list[DecisionEntry]:
        """Return most-recent `limit` entries whose state is 'similar' to input.

        Similar = decision_type matches AND (phase matches if phase_match) AND
        |entry.ctl - athlete_state.ctl| <= ctl_tolerance.
        """
        matched: list[DecisionEntry] = []
        for entry in self._iter_entries():
            if entry.decision_type != decision_type:
                continue
            if phase_match and entry.athlete_state_ref.phase != athlete_state.phase:
                continue
            if abs(entry.athlete_state_ref.ctl - athlete_state.ctl) > ctl_tolerance:
                continue
            matched.append(entry)

        matched.sort(key=lambda e: e.entry_id, reverse=True)
        return matched[:limit]

    # ------- trace_chain -------

    def trace_chain(self, entry_id: str) -> list[DecisionEntry]:
        """Follow superseded_by pointers starting from entry_id.

        Returns [entry_id's entry, ...successor entries] in order.
        Cycle-safe: bounded by number of distinct visits.
        Unknown entry_id → [].
        """
        by_id: dict[str, DecisionEntry] = {e.entry_id: e for e in self._iter_entries()}
        if entry_id not in by_id:
            return []
        chain: list[DecisionEntry] = []
        seen: set[str] = set()
        cursor: str | None = entry_id
        while cursor is not None and cursor in by_id and cursor not in seen:
            seen.add(cursor)
            entry = by_id[cursor]
            chain.append(entry)
            cursor = entry.superseded_by
        return chain
