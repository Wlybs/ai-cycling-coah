# Phase 3 — Ledger infrastructure (Tasks T50–T52)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 交付 `icu/src/coach/ledger/` 的骨架（types / writer / reader），这是 Phase 3 其他所有组件的依赖根。此文件与 Phase 1/2 代码完全解耦，只依赖 Python stdlib + Pydantic v2，可与 Phase 2 主线并行开发。

**Files covered:**
- `icu/src/coach/ledger/__init__.py`
- `icu/src/coach/ledger/types.py`
- `icu/src/coach/ledger/writer.py`
- `icu/src/coach/ledger/reader.py`
- `icu/tests/unit/ledger/__init__.py`
- `icu/tests/unit/ledger/conftest.py`
- `icu/tests/unit/ledger/test_types.py`
- `icu/tests/unit/ledger/test_writer.py`
- `icu/tests/unit/ledger/test_reader.py`

**Hard constraints (from 00-index.md):**
- `NO_NEW_DEPS`: ULID 用 stdlib 搓（`time_ns` + `secrets` + Crockford base32），禁止引入第三方 ulid 包。
- `APPEND_ONLY_LEDGER`: writer 绝不覆写已有 entry；纠错走 `superseded_by` 字段。
- `PHASE_1_2_IMMUTABILITY`: 本文件涉及的所有代码都在 `icu/src/coach/ledger/` 和 `icu/tests/unit/ledger/` 下，不触 Phase 1/2。

---

## Task 50: Package scaffold + types (AthleteStateRef, DecisionEntry, ULID helper)

**Files:**
- Create: `icu/src/coach/ledger/__init__.py`
- Create: `icu/src/coach/ledger/types.py`
- Create: `icu/tests/unit/ledger/__init__.py`
- Create: `icu/tests/unit/ledger/test_types.py`

- [ ] **Step 1: Write failing tests — types + ULID helper**

Write `icu/tests/unit/ledger/test_types.py`:
```python
"""Unit tests for ledger types: AthleteStateRef, DecisionEntry, ULID helper."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.coach.ledger.types import (
    AthleteStateRef,
    DecisionEntry,
    DECISION_TYPES,
    generate_ulid,
    is_valid_ulid,
)


# ---------- AthleteStateRef ----------

def test_athlete_state_ref_roundtrip():
    ref = AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )
    js = ref.model_dump_json()
    loaded = AthleteStateRef.model_validate_json(js)
    assert loaded == ref


def test_athlete_state_ref_rejects_negative_w_prime():
    with pytest.raises(ValidationError):
        AthleteStateRef(
            ctl=72.3, atl=85.1, tsb=-12.8,
            w_prime=-100, phase="BUILD", week_of_year=16,
        )


def test_athlete_state_ref_week_of_year_range():
    # ISO weeks are 1–53
    AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                    w_prime=18000, phase="BASE", week_of_year=1)
    AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                    w_prime=18000, phase="BASE", week_of_year=53)
    with pytest.raises(ValidationError):
        AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                        w_prime=18000, phase="BASE", week_of_year=0)
    with pytest.raises(ValidationError):
        AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                        w_prime=18000, phase="BASE", week_of_year=54)


# ---------- DecisionEntry ----------

def _sample_state() -> AthleteStateRef:
    return AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


def test_decision_entry_minimal_fields():
    entry = DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state_ref=_sample_state(),
        payload={"verdict": "green"},
    )
    assert entry.schema_version == 1
    assert entry.evidence_refs == []
    assert entry.superseded_by is None
    assert entry.confidence is None


def test_decision_entry_roundtrip_all_decision_types():
    # Must roundtrip for every decision_type we use.
    for dt in DECISION_TYPES:
        entry = DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime.now(timezone.utc),
            decision_type=dt,
            source=f"test.{dt}",
            athlete_state_ref=_sample_state(),
            payload={"_fixture": dt},
            confidence=0.5,
            evidence_refs=["physiology/cp_w_current.json"],
        )
        js = entry.model_dump_json()
        loaded = DecisionEntry.model_validate_json(js)
        assert loaded.decision_type == dt
        assert loaded.payload == {"_fixture": dt}


def test_decision_entry_rejects_unknown_decision_type():
    with pytest.raises(ValidationError):
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime.now(timezone.utc),
            decision_type="made_up_type",
            source="test",
            athlete_state_ref=_sample_state(),
            payload={},
        )


def test_decision_entry_rejects_naive_timestamp():
    # UTC required — naive datetime should be rejected.
    with pytest.raises(ValidationError):
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime(2026, 4, 19, 10, 0, 0),  # no tzinfo
            decision_type="adaptation_verdict",
            source="test",
            athlete_state_ref=_sample_state(),
            payload={},
        )


def test_decision_entry_confidence_range():
    base = dict(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="consensus_verdict",
        source="test",
        athlete_state_ref=_sample_state(),
        payload={},
    )
    DecisionEntry(**base, confidence=0.0)
    DecisionEntry(**base, confidence=1.0)
    with pytest.raises(ValidationError):
        DecisionEntry(**base, confidence=-0.01)
    with pytest.raises(ValidationError):
        DecisionEntry(**base, confidence=1.01)


def test_decision_entry_superseded_by_accepts_ulid():
    other = generate_ulid()
    entry = DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="phase_transition",
        source="test",
        athlete_state_ref=_sample_state(),
        payload={},
        superseded_by=other,
    )
    assert entry.superseded_by == other


# ---------- ULID helper ----------

def test_ulid_is_26_char_crockford_base32():
    ulid = generate_ulid()
    assert len(ulid) == 26
    alphabet = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert set(ulid) <= alphabet


def test_ulid_uniqueness_within_burst():
    # 10k ULIDs generated in the same ms should still be unique
    ulids = [generate_ulid() for _ in range(10_000)]
    assert len(set(ulids)) == 10_000


def test_ulid_monotonic_across_ms():
    import time
    a = generate_ulid()
    time.sleep(0.002)  # ensure ms advances
    b = generate_ulid()
    # First 10 chars encode 48-bit ms timestamp; later ms → lexicographically greater
    assert b[:10] > a[:10]


def test_is_valid_ulid():
    assert is_valid_ulid(generate_ulid()) is True
    assert is_valid_ulid("TOO_SHORT") is False
    assert is_valid_ulid("I" * 26) is False  # 'I' not in Crockford base32
    assert is_valid_ulid("L" * 26) is False  # 'L' not in Crockford base32


def test_decision_types_matches_blueprint():
    # 00-index.md locks these 8 values; adding a 9th requires an ADR.
    expected = {
        "phase_transition", "macro_plan_generated", "meso_block_created",
        "micro_cycle_generated", "weekly_plan_assembled",
        "consensus_verdict", "adaptation_verdict", "adaptation_applied",
    }
    assert set(DECISION_TYPES) == expected
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.ledger'`.

- [ ] **Step 3: Implement package + types**

Write `icu/src/coach/ledger/__init__.py`:
```python
"""Decision Ledger — Phase 3 的 append-only 决策账本。

公开入口：
- LedgerWriter: 原子 append JSONL（见 writer.py）
- LedgerReader: 查询 / 相似 context 检索 / 决策链追溯（见 reader.py）
- DecisionEntry / AthleteStateRef / DECISION_TYPES: 类型和常量（见 types.py）

所有持久化通过单文件 `coach_memory/ledger/decisions.jsonl` 完成。
Schema / 约束见 docs/superpowers/specs/2026-04-19-phase-3-blueprint.md。
"""
```

Write `icu/src/coach/ledger/types.py`:
```python
"""Ledger 类型定义：AthleteStateRef / DecisionEntry + ULID helper。"""
from __future__ import annotations

import secrets
import time
from datetime import datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator


# ---------- decision_type 白名单 ----------

DecisionType = Literal[
    "phase_transition",
    "macro_plan_generated",
    "meso_block_created",
    "micro_cycle_generated",
    "weekly_plan_assembled",
    "consensus_verdict",
    "adaptation_verdict",
    "adaptation_applied",
]

DECISION_TYPES: tuple[str, ...] = get_args(DecisionType)


# ---------- ULID helper (stdlib-only, Crockford base32) ----------

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ALPHABET_SET = frozenset(_CROCKFORD)


def _encode_crockford(value: int, length: int) -> str:
    """Encode non-negative integer to Crockford base32, left-padded to `length`."""
    if value < 0:
        raise ValueError("value must be non-negative")
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def generate_ulid() -> str:
    """Return a 26-char ULID (48-bit ms timestamp + 80-bit randomness).

    ULID spec: https://github.com/ulid/spec.
    Time encoded in first 10 chars (lexicographically sortable by ms).
    Random encoded in last 16 chars (80 bits from secrets.randbits).
    """
    ms = time.time_ns() // 1_000_000  # 48 bits fits until year 10889
    rand = secrets.randbits(80)
    return _encode_crockford(ms, 10) + _encode_crockford(rand, 16)


def is_valid_ulid(candidate: str) -> bool:
    """True iff `candidate` is a 26-char Crockford-base32 string."""
    if not isinstance(candidate, str) or len(candidate) != 26:
        return False
    return set(candidate) <= _ALPHABET_SET


# ---------- AthleteStateRef ----------

class AthleteStateRef(BaseModel):
    """每条 ledger entry 附带的运动员状态快照。

    Phase/week_of_year 必填 → `query_similar` 按此索引。
    字段冻结；新增字段前请评估向后兼容（旧 entry 没有新字段时读取必须不崩）。
    """

    model_config = {"frozen": True}

    ctl: float = Field(..., description="Chronic Training Load (当天值)")
    atl: float = Field(..., description="Acute Training Load")
    tsb: float = Field(..., description="Training Stress Balance = CTL − ATL")
    w_prime: int = Field(..., ge=0, description="当前 W' 焦耳值（来自 CPWModel）")
    phase: str = Field(..., description="Periodization Phase enum value, e.g. 'BUILD'")
    week_of_year: int = Field(..., ge=1, le=53, description="ISO week number")


# ---------- DecisionEntry ----------

class DecisionEntry(BaseModel):
    """Ledger 的一条决策记录。append-only；纠错通过 superseded_by 指针。"""

    schema_version: int = 1
    entry_id: str = Field(..., description="26-char ULID, time-sortable")
    timestamp: datetime = Field(..., description="UTC timestamp (tzinfo required)")
    decision_type: DecisionType
    source: str = Field(..., description="模块标识，如 'adapter.daily' / 'consensus.council'")
    athlete_state_ref: AthleteStateRef
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    superseded_by: str | None = Field(
        default=None,
        description=(
            "ULID of an EARLIER entry that THIS entry supersedes/corrects. "
            "Set at write time of the newer correction entry. "
            "Append-only-safe: never mutates the older entry."
        ),
    )

    @field_validator("entry_id")
    @classmethod
    def _check_entry_id(cls, v: str) -> str:
        if not is_valid_ulid(v):
            raise ValueError(f"entry_id must be a valid ULID, got {v!r}")
        return v

    @field_validator("superseded_by")
    @classmethod
    def _check_superseded_by(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_ulid(v):
            raise ValueError(f"superseded_by must be a valid ULID, got {v!r}")
        return v

    @field_validator("timestamp")
    @classmethod
    def _require_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        return v
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_types.py -v`
Expected: PASS all ~14 tests.

- [ ] **Step 5: Commit**

Write `icu/tests/unit/ledger/__init__.py` (empty file, makes tests importable as package):
```python
```

```bash
git add icu/src/coach/ledger/__init__.py \
        icu/src/coach/ledger/types.py \
        icu/tests/unit/ledger/__init__.py \
        icu/tests/unit/ledger/test_types.py
git commit -m "feat(coach-phase3): ledger package scaffold + types (AthleteStateRef, DecisionEntry, ULID)"
```

---

## Task 51: LedgerWriter — atomic append JSONL

**Files:**
- Create: `icu/src/coach/ledger/writer.py`
- Create: `icu/tests/unit/ledger/conftest.py`
- Create: `icu/tests/unit/ledger/test_writer.py`

**Design notes:**
- JSONL 单文件；每条 entry 占一行（`model_dump_json()` + `"\n"`）。
- 原子性：用 `fcntl.flock(LOCK_EX)` 独占锁 + `os.O_APPEND` + `write()` 单次系统调用。典型 entry < 4KB，单次 `write()` 在 Linux 上对 pipe/regular file 是 atomic（< `PIPE_BUF` = 4096B）。对 > 4KB 的 entry，flock 仍保证跨进程独占。
- 写完 `os.fsync(fd)` 保证 crash 前落盘。
- 不读文件做 dedupe；依赖 ULID 时间排序。

- [ ] **Step 1: Write failing tests — record + atomic + concurrent**

Create `icu/tests/unit/ledger/conftest.py`:
```python
"""Shared fixtures for ledger unit tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.coach.ledger.types import AthleteStateRef


@pytest.fixture
def sample_state() -> AthleteStateRef:
    return AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


@pytest.fixture
def ledger_path(tmp_path):
    """Empty path; writer creates the file on first record."""
    return tmp_path / "decisions.jsonl"


@pytest.fixture
def fixed_utc_now():
    return datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)
```

Write `icu/tests/unit/ledger/test_writer.py`:
```python
"""Unit tests for LedgerWriter: atomic append, concurrent-safe, schema-strict."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path

import pytest

from src.coach.ledger.types import AthleteStateRef, is_valid_ulid
from src.coach.ledger.writer import LedgerWriter


def test_record_creates_file_and_appends_line(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    entry_id = w.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=sample_state,
        payload={"verdict": "green"},
        confidence=1.0,
    )
    assert is_valid_ulid(entry_id)
    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    doc = json.loads(lines[0])
    assert doc["entry_id"] == entry_id
    assert doc["decision_type"] == "adaptation_verdict"
    assert doc["payload"] == {"verdict": "green"}


def test_record_appends_without_rewriting(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(5):
        w.record(
            decision_type="phase_transition",
            source="test",
            athlete_state=sample_state,
            payload={"seq": i},
        )
    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    payloads = [json.loads(l)["payload"]["seq"] for l in lines]
    assert payloads == [0, 1, 2, 3, 4]


def test_record_returns_distinct_ulids(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    ids = [
        w.record(decision_type="consensus_verdict", source="test",
                 athlete_state=sample_state, payload={"i": i})
        for i in range(100)
    ]
    assert len(set(ids)) == 100


def test_record_evidence_refs_default_empty(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="micro_cycle_generated", source="test",
             athlete_state=sample_state, payload={})
    doc = json.loads(Path(ledger_path).read_text().splitlines()[0])
    assert doc["evidence_refs"] == []
    assert doc["superseded_by"] is None


def test_record_persists_optional_fields(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=sample_state,
        payload={"total_tss": 480},
        evidence_refs=["reports/plan_20260419.trace.json"],
        confidence=0.82,
    )
    doc = json.loads(Path(ledger_path).read_text().splitlines()[0])
    assert doc["evidence_refs"] == ["reports/plan_20260419.trace.json"]
    assert doc["confidence"] == 0.82


def test_record_rejects_invalid_decision_type(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    with pytest.raises(Exception):  # ValidationError from Pydantic
        w.record(decision_type="bogus", source="test",
                 athlete_state=sample_state, payload={})
    # File should still be empty-or-absent (no partial row)
    if Path(ledger_path).exists():
        assert Path(ledger_path).read_text() == ""


# ---------- Concurrency ----------

def _child_write(path: str, n: int, state_dict: dict):
    """Worker process: write N entries to the shared ledger."""
    from src.coach.ledger.writer import LedgerWriter
    from src.coach.ledger.types import AthleteStateRef
    state = AthleteStateRef(**state_dict)
    w = LedgerWriter(Path(path))
    for i in range(n):
        w.record(decision_type="adaptation_verdict", source=f"proc.{os.getpid()}",
                 athlete_state=state, payload={"i": i, "pid": os.getpid()})


def test_concurrent_writes_produce_valid_lines(ledger_path, sample_state):
    """Two processes each write 50 entries; total must be 100 valid lines."""
    state_dict = sample_state.model_dump()
    procs = [mp.Process(target=_child_write, args=(str(ledger_path), 50, state_dict))
             for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0

    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    # Every line must be valid JSON with a valid ULID
    for line in lines:
        doc = json.loads(line)
        assert is_valid_ulid(doc["entry_id"])
        assert doc["decision_type"] == "adaptation_verdict"


def test_append_mode_tolerates_corrupt_trailing_line(tmp_path, sample_state):
    """Pre-existing file with a half-written last line: new record still appends."""
    p = tmp_path / "decisions.jsonl"
    p.write_text('{"entry_id": "01HF0", "decision_type":', encoding="utf-8")  # truncated
    w = LedgerWriter(p)
    w.record(decision_type="phase_transition", source="test",
             athlete_state=sample_state, payload={"ok": True})
    text = p.read_text(encoding="utf-8")
    # Writer MUST append on a new line so the corrupt prefix stays on its own line
    assert text.count("\n") >= 1
    last_line = text.splitlines()[-1]
    doc = json.loads(last_line)
    assert doc["payload"] == {"ok": True}
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_writer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.ledger.writer'`.

- [ ] **Step 3: Implement LedgerWriter**

Write `icu/src/coach/ledger/writer.py`:
```python
"""LedgerWriter — 原子 append JSONL 的单一入口。

不变量（见 00-index.md HARD 约束 APPEND_ONLY_LEDGER）：
- 只追加，不修改已写入的行。
- 纠错走 DecisionEntry.superseded_by 指向后续 entry。
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


class LedgerWriter:
    """Append-only writer for a single JSONL file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        # Ensure parent dir exists; file itself is created lazily on first record
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
            timestamp=datetime.now(timezone.utc),
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

        # O_APPEND guarantees each write() is positioned at EOF atomically.
        # flock adds cross-process mutual exclusion — required for writes > PIPE_BUF
        # and for the "newline before append if file ends mid-line" safeguard below.
        fd = os.open(
            self.path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o644,
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                # If the existing tail is not newline-terminated (e.g. a prior
                # crash left a half-written line), prepend a newline so our
                # new entry lives on its own line.
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
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_writer.py -v`
Expected: PASS all 8 tests.

Note: `test_concurrent_writes_produce_valid_lines` spawns processes; if it hangs on Windows/WSL, confirm WSL build supports `fcntl.flock`.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/ledger/writer.py \
        icu/tests/unit/ledger/conftest.py \
        icu/tests/unit/ledger/test_writer.py
git commit -m "feat(coach-phase3): LedgerWriter with flock-based atomic append JSONL"
```

---

## Task 52: LedgerReader — query / query_similar / trace_chain

**Files:**
- Create: `icu/src/coach/ledger/reader.py`
- Create: `icu/tests/unit/ledger/test_reader.py`

**Design notes:**
- 全量扫描 + 内存过滤。对 < 5 MB JSONL（预计多年内的量级），线性扫描耗时 < 100ms，无需索引。
- Reader 每次调用都重新读文件：保证看到 Writer 最新 append，不缓存。
- 坏行（JSON 解析失败）→ 跳过并 log 警告，不抛异常。这样即使某条 entry 因 Pydantic 升级暂时不可反序列化，其他 entry 仍可读。
- `query_similar`：phase 完全相等 + `|ctl_diff| ≤ tolerance`。不上向量检索（YAGNI）。

- [ ] **Step 1: Write failing tests — query / query_similar / trace_chain**

Write `icu/tests/unit/ledger/test_reader.py`:
```python
"""Unit tests for LedgerReader: query, query_similar, trace_chain, corruption tolerance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


def _state(ctl: float = 72.0, phase: str = "BUILD", week: int = 16) -> AthleteStateRef:
    return AthleteStateRef(
        ctl=ctl, atl=ctl * 1.1, tsb=-ctl * 0.15,
        w_prime=18500, phase=phase, week_of_year=week,
    )


# ---------- query ----------

def test_query_returns_empty_on_missing_file(tmp_path):
    r = LedgerReader(tmp_path / "not_there.jsonl")
    assert r.query() == []


def test_query_returns_all_entries_default(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(3):
        w.record(decision_type="adaptation_verdict", source="test",
                 athlete_state=sample_state, payload={"i": i})
    r = LedgerReader(ledger_path)
    entries = r.query()
    assert len(entries) == 3
    # Sorted ascending by entry_id (== by timestamp)
    assert [e.payload["i"] for e in entries] == [0, 1, 2]


def test_query_filters_by_decision_type(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="adaptation_verdict", source="a",
             athlete_state=sample_state, payload={})
    w.record(decision_type="consensus_verdict", source="b",
             athlete_state=sample_state, payload={})
    w.record(decision_type="adaptation_verdict", source="c",
             athlete_state=sample_state, payload={})

    r = LedgerReader(ledger_path)
    got = r.query(decision_type="adaptation_verdict")
    assert len(got) == 2
    assert all(e.decision_type == "adaptation_verdict" for e in got)


def test_query_filters_by_time_window(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    # Record 3 entries (timestamps separated by sleeps)
    import time
    w.record(decision_type="phase_transition", source="x",
             athlete_state=sample_state, payload={"n": 1})
    time.sleep(0.005)
    middle_time = datetime.now(timezone.utc)
    time.sleep(0.005)
    w.record(decision_type="phase_transition", source="x",
             athlete_state=sample_state, payload={"n": 2})

    r = LedgerReader(ledger_path)
    after_middle = r.query(since=middle_time)
    assert len(after_middle) == 1
    assert after_middle[0].payload["n"] == 2


def test_query_limit_takes_most_recent(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(10):
        w.record(decision_type="adaptation_verdict", source="x",
                 athlete_state=sample_state, payload={"i": i})

    r = LedgerReader(ledger_path)
    last3 = r.query(limit=3)
    assert len(last3) == 3
    # Most recent 3 means i=7,8,9
    assert [e.payload["i"] for e in last3] == [7, 8, 9]


# ---------- query_similar ----------

def test_query_similar_matches_phase_and_ctl(ledger_path):
    w = LedgerWriter(ledger_path)
    # Mix of phases and CTLs
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"tag": "match_A"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=73.8, phase="BUILD"), payload={"tag": "match_B"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=85.0, phase="BUILD"), payload={"tag": "too_far"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=72.5, phase="PEAK"), payload={"tag": "wrong_phase"})

    r = LedgerReader(ledger_path)
    query_state = _state(ctl=72.0, phase="BUILD")
    hits = r.query_similar(
        athlete_state=query_state,
        decision_type="weekly_plan_assembled",
        ctl_tolerance=5.0,
        phase_match=True,
        limit=5,
    )
    tags = {e.payload["tag"] for e in hits}
    assert tags == {"match_A", "match_B"}


def test_query_similar_phase_match_false_allows_any_phase(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="consensus_verdict", source="t",
             athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"tag": "build"})
    w.record(decision_type="consensus_verdict", source="t",
             athlete_state=_state(ctl=72.5, phase="PEAK"), payload={"tag": "peak"})

    r = LedgerReader(ledger_path)
    hits = r.query_similar(
        athlete_state=_state(ctl=72.0, phase="BUILD"),
        decision_type="consensus_verdict",
        ctl_tolerance=5.0, phase_match=False, limit=5,
    )
    assert {e.payload["tag"] for e in hits} == {"build", "peak"}


def test_query_similar_returns_most_recent_first(ledger_path):
    w = LedgerWriter(ledger_path)
    for i in range(10):
        w.record(decision_type="weekly_plan_assembled", source="t",
                 athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"i": i})

    r = LedgerReader(ledger_path)
    hits = r.query_similar(
        athlete_state=_state(ctl=72.0, phase="BUILD"),
        decision_type="weekly_plan_assembled",
        ctl_tolerance=5.0, phase_match=True, limit=3,
    )
    # Most recent 3 (i=9,8,7) in descending order
    assert [e.payload["i"] for e in hits] == [9, 8, 7]


# ---------- trace_chain ----------

def test_trace_chain_follows_superseded_by(ledger_path, sample_state):
    """Correction chain: c corrects b; b stands on its own; trace from c yields [c, b]."""
    w = LedgerWriter(ledger_path)
    id_b = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": "original"})
    id_c = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": "corrected"},
                    superseded_by=id_b)

    r = LedgerReader(ledger_path)
    chain = r.trace_chain(id_c)
    # Start at id_c, follow its superseded_by to id_b, stop (id_b has no superseded_by).
    assert [e.entry_id for e in chain] == [id_c, id_b]


def test_trace_chain_unknown_entry_returns_empty(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="phase_transition", source="t",
             athlete_state=sample_state, payload={})
    r = LedgerReader(ledger_path)
    assert r.trace_chain("01ZZZZZZZZZZZZZZZZZZZZZZZZ") == []


def test_trace_chain_detects_cycle(ledger_path, sample_state):
    # Fabricate a corrupted chain A → B → A by writing hand-crafted lines
    w = LedgerWriter(ledger_path)
    id_a = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": 1})
    id_b = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": 2},
                    superseded_by=id_a)
    # Append a third entry that edits id_a's line in-place is forbidden, but
    # we can simulate a cycle by writing a new line with entry_id=id_a and
    # superseded_by=id_b — reader should detect the cycle and stop.
    # We can't reuse an entry_id via the Writer API (no such support by design),
    # so we directly append a crafted line.
    from pathlib import Path as _P
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    cycled = {
        "schema_version": 1,
        "entry_id": id_a,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "decision_type": "phase_transition",
        "source": "t",
        "athlete_state_ref": sample_state.model_dump(),
        "confidence": None,
        "payload": {"n": "cycled"},
        "evidence_refs": [],
        "superseded_by": id_b,
    }
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(_json.dumps(cycled) + "\n")

    r = LedgerReader(ledger_path)
    chain = r.trace_chain(id_a)
    # Must terminate (not infinite-loop) even if a cycle exists.
    # Exactly how many entries it visits is impl-defined; just bound it.
    assert 1 <= len(chain) <= 3


# ---------- Corruption tolerance ----------

def test_query_skips_corrupt_lines(tmp_path, sample_state):
    p = tmp_path / "decisions.jsonl"
    w = LedgerWriter(p)
    w.record(decision_type="adaptation_verdict", source="t",
             athlete_state=sample_state, payload={"ok": 1})
    # Append a malformed JSON line
    with open(p, "a", encoding="utf-8") as f:
        f.write("NOT_JSON_AT_ALL\n")
    w.record(decision_type="adaptation_verdict", source="t",
             athlete_state=sample_state, payload={"ok": 2})

    r = LedgerReader(p)
    entries = r.query()
    assert len(entries) == 2
    assert [e.payload["ok"] for e in entries] == [1, 2]
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.ledger.reader'`.

- [ ] **Step 3: Implement LedgerReader**

Write `icu/src/coach/ledger/reader.py`:
```python
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

        matched.sort(key=lambda e: e.entry_id)  # ULID sort == time sort
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

        matched.sort(key=lambda e: e.entry_id, reverse=True)  # newest first
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
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/ -v`
Expected: PASS all tests across `test_types.py`, `test_writer.py`, `test_reader.py` (~26 tests).

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/ledger/reader.py \
        icu/tests/unit/ledger/test_reader.py
git commit -m "feat(coach-phase3): LedgerReader with query / query_similar / trace_chain"
```

---

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/ledger/ -v` 全绿（~26 tests）
- [ ] 3 次提交完成（T50 / T51 / T52 各一次）
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`02-ledger-ingester.md`](./02-ledger-ingester.md) 开始（T53–T54）。

## Worktree bootstrap reminder (executor reads before Step 1 of T50)

This worktree (`/mnt/d/Cycling-phase3`) was created fresh from `master @ 892f791`. Per memory `worktree_setup_icu.md`, untracked paths (`.venv`, `src/analyzer/`, `src/utils/`, `src/fetcher/`) are not in the worktree. Bootstrap before running pytest:

```bash
# From /mnt/d/Cycling-phase3
cp -rf /mnt/d/Cycling/icu/.venv icu/.venv
cp -rf /mnt/d/Cycling/icu/src/analyzer icu/src/analyzer
cp -rf /mnt/d/Cycling/icu/src/utils icu/src/utils
cp -rf /mnt/d/Cycling/icu/src/fetcher icu/src/fetcher
# Copy .env if any test needs it (ledger T50–T52 do not)
```

Alternatively, symlink the `.venv` to save disk; the three `src/` folders must be real copies since `src/coach/` lives under the same tree.
