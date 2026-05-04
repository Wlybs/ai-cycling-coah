"""LedgerWriter — 原子 append JSONL 的单一入口。

不变量（见 plans/phase-3/00-index.md HARD 约束 APPEND_ONLY_LEDGER）：
- 只追加，不修改已写入的行。
- 纠错走 DecisionEntry.superseded_by 指向更早被修正的 entry。
- 写入前 Pydantic 校验；校验失败 → ValidationError 抛出，文件零变动。
"""
from __future__ import annotations

import fcntl
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.coach.common.logging import get_logger

from .types import (
    AthleteStateRef,
    DecisionEntry,
    DecisionType,
    generate_ulid,
)

_log = get_logger("ledger")


def _now_utc() -> datetime:
    """UTC now, with ICU_FORCED_NOW_ISO env override for date-coupled tests."""
    forced = os.environ.get("ICU_FORCED_NOW_ISO")
    if forced:
        dt = datetime.fromisoformat(forced)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return datetime.now(timezone.utc)


class LedgerWriter:
    """Append-only writer for a single JSONL file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        decision_type: DecisionType | str,
        source: str,
        athlete_state: AthleteStateRef,
        payload: dict[str, Any],
        evidence_refs: list[str] | None = None,
        confidence: float | None = None,
        superseded_by: str | None = None,
    ) -> str:
        """Validate + append one entry; return its entry_id (ULID).

        Raises pydantic.ValidationError on schema violation (file untouched).
        """
        entry = DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=_now_utc(),
            decision_type=decision_type,  # type: ignore[arg-type]
            source=source,
            athlete_state_ref=athlete_state,
            confidence=confidence,
            payload=payload,
            evidence_refs=evidence_refs or [],
            superseded_by=superseded_by,
        )

        line = entry.model_dump_json() + "\n"
        data = line.encode("utf-8")

        fd = os.open(
            self.path,
            os.O_RDWR | os.O_APPEND | os.O_CREAT,
            0o644,
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                size = os.fstat(fd).st_size
                if size > 0:
                    os.lseek(fd, -1, os.SEEK_END)
                    tail = os.read(fd, 1)
                    if tail != b"\n":
                        os.write(fd, b"\n")
                    os.lseek(fd, 0, os.SEEK_END)
                os.write(fd, data)
                os.fsync(fd)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

        _log.event(
            "ledger_entry_appended",
            entry_id=entry.entry_id,
            decision_type=entry.decision_type,
            source=source,
            path=str(self.path),
        )
        return entry.entry_id
