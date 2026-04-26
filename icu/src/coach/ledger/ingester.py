"""LedgerIngester — 扫 Phase 2 产物回补 ledger entries。

为什么需要 Ingester：Phase 3 的硬约束 PHASE_1_2_IMMUTABILITY 禁止改 Phase 2
代码。理想做法是 Phase 2 各组件在写完产物时自己往 ledger 追加 entry，但那样
要改 Phase 2 源码。Ingester 是妥协：扫文件系统产物 → 推断决策 → 回补 entry。

5 种 decision_type 的 unique key（用于幂等）：
- phase_transition: 与 ledger 中最新 phase_transition entry 的 to_phase 对比
- macro_plan_generated: payload.generated_at（macro_plan.json 顶层字段）
- meso_block_created: payload.block_start
- micro_cycle_generated: payload.week_start
- weekly_plan_assembled: payload.plan_date

单一 entry-point: LedgerIngester(...).ingest_all() 返回 {decision_type: count_new}。
"""
from __future__ import annotations

import json
from pathlib import Path

from .reader import LedgerReader
from .types import AthleteStateRef
from .writer import LedgerWriter


class LedgerIngester:
    def __init__(
        self,
        memory_dir: Path | str,
        ledger_writer: LedgerWriter,
        ledger_reader: LedgerReader,
        default_state: AthleteStateRef,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.writer = ledger_writer
        self.reader = ledger_reader
        self.default_state = default_state

    # ---------- public ----------

    def ingest_all(self) -> dict[str, int]:
        return {
            "phase_transition": self._ingest_phase_current(),
            "macro_plan_generated": self._ingest_macro_plan(),
            "meso_block_created": self._ingest_meso_block(),
            "micro_cycle_generated": self._ingest_micro_cycles(),
            "weekly_plan_assembled": self._ingest_weekly_plans(),
        }

    # ---------- helpers ----------

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ---------- phase_transition ----------

    def _ingest_phase_current(self) -> int:
        doc = self._read_json(self.memory_dir / "periodization" / "phase_current.json")
        if doc is None:
            return 0
        new_phase = doc.get("current_phase")
        if not new_phase:
            return 0

        prior = self.reader.query(decision_type="phase_transition")
        prior_phase = prior[-1].payload.get("to_phase") if prior else None
        if prior_phase == new_phase:
            return 0

        self.writer.record(
            decision_type="phase_transition",
            source="ingester.phase_current",
            athlete_state=self.default_state,
            payload={
                "from_phase": prior_phase,
                "to_phase": new_phase,
                "reasons": doc.get("reasons", []),
                "generated_at": doc.get("generated_at"),
            },
            evidence_refs=["periodization/phase_current.json"],
            confidence=1.0,
        )
        return 1

    # ---------- macro_plan_generated ----------

    def _ingest_macro_plan(self) -> int:
        doc = self._read_json(self.memory_dir / "periodization" / "macro_plan.json")
        if doc is None:
            return 0
        gen_at = doc.get("generated_at")
        if not gen_at:
            return 0

        prior = self.reader.query(decision_type="macro_plan_generated")
        if any(e.payload.get("generated_at") == gen_at for e in prior):
            return 0

        windows = doc.get("windows", [])
        self.writer.record(
            decision_type="macro_plan_generated",
            source="ingester.macro_plan",
            athlete_state=self.default_state,
            payload={
                "generated_at": gen_at,
                "season_end_date": doc.get("season_end_date"),
                "windows_count": len(windows),
                "phase_sequence": [w.get("phase") for w in windows],
            },
            evidence_refs=["periodization/macro_plan.json"],
            confidence=1.0,
        )
        return 1

    # ---------- meso_block_created ----------

    def _ingest_meso_block(self) -> int:
        doc = self._read_json(self.memory_dir / "periodization" / "meso_block.json")
        if doc is None:
            return 0
        block_start = doc.get("block_start")
        if not block_start:
            return 0

        prior = self.reader.query(decision_type="meso_block_created")
        if any(e.payload.get("block_start") == block_start for e in prior):
            return 0

        self.writer.record(
            decision_type="meso_block_created",
            source="ingester.meso_block",
            athlete_state=self.default_state,
            payload={
                "pattern": doc.get("pattern"),
                "block_start": block_start,
                "block_end": doc.get("block_end"),
                "weeks": len(doc.get("weekly_load_multipliers", [])),
                "phase": doc.get("phase"),
            },
            evidence_refs=["periodization/meso_block.json"],
            confidence=1.0,
        )
        return 1

    # ---------- micro_cycle_generated ----------

    def _ingest_micro_cycles(self) -> int:
        per_dir = self.memory_dir / "periodization"
        if not per_dir.exists():
            return 0

        prior = self.reader.query(decision_type="micro_cycle_generated")
        seen_weeks = {e.payload.get("week_start") for e in prior}

        n_new = 0
        for path in sorted(per_dir.glob("micro_cycle_*.json")):
            doc = self._read_json(path)
            if doc is None:
                continue
            week_start = doc.get("week_start")
            if not week_start or week_start in seen_weeks:
                continue
            hard_days = sum(1 for d in doc.get("days", []) if d.get("tier") == "HARD")
            self.writer.record(
                decision_type="micro_cycle_generated",
                source="ingester.micro_cycle",
                athlete_state=self.default_state,
                payload={
                    "week_start": week_start,
                    "week_end": doc.get("week_end"),
                    "phase": doc.get("phase"),
                    "hard_days": hard_days,
                    "weekly_tss_target": doc.get("weekly_tss_target"),
                },
                evidence_refs=[f"periodization/{path.name}"],
                confidence=1.0,
            )
            seen_weeks.add(week_start)
            n_new += 1
        return n_new

    # ---------- weekly_plan_assembled ----------

    def _ingest_weekly_plans(self) -> int:
        rep_dir = self.memory_dir / "reports"
        if not rep_dir.exists():
            return 0

        prior = self.reader.query(decision_type="weekly_plan_assembled")
        seen_dates = {e.payload.get("plan_date") for e in prior}

        n_new = 0
        for path in sorted(rep_dir.glob("plan_*.json")):
            # skip trace.json siblings (they end in .trace.json)
            if path.name.endswith(".trace.json"):
                continue
            doc = self._read_json(path)
            if doc is None:
                continue
            plan_date = doc.get("week_start")
            if not plan_date or plan_date in seen_dates:
                continue

            trace_path = path.with_suffix(".trace.json")
            evidence = [f"reports/{path.name}"]
            trace_summary: dict | None = None
            if trace_path.exists():
                trace_doc = self._read_json(trace_path)
                if trace_doc is not None:
                    evidence.append(f"reports/{trace_path.name}")
                    trace_summary = {
                        "composer_version": trace_doc.get("composer_version"),
                        "session_count": len(trace_doc.get("sessions", [])),
                    }

            sessions_by_type: dict[str, int] = {}
            for d in doc.get("days", []):
                t = d.get("training_type", "unknown")
                sessions_by_type[t] = sessions_by_type.get(t, 0) + 1

            self.writer.record(
                decision_type="weekly_plan_assembled",
                source="ingester.weekly_plan",
                athlete_state=self.default_state,
                payload={
                    "plan_date": plan_date,
                    "total_tss": doc.get("weekly_tss_target"),
                    "focus_theme": doc.get("focus_theme"),
                    "sessions_by_type": sessions_by_type,
                    "trace_summary": trace_summary,
                },
                evidence_refs=evidence,
                confidence=1.0,
            )
            seen_dates.add(plan_date)
            n_new += 1
        return n_new
