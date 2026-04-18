"""Periodization snapshot JSON 读写。所有路径都相对 base_dir。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .types import (
    MacroPlan, MesoBlock, MicroCycle, PeriodizationSnapshot, Phase,
)

PHASE_CURRENT = "phase_current.json"
MACRO_PLAN = "macro_plan.json"
MESO_BLOCK = "meso_block.json"
SNAPSHOT = "periodization_current.json"


def _ensure_dir(base_dir: Path) -> Path:
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def write_phase_current(
    base_dir: Path, phase: Phase, reasons: list[str], now_iso: str
) -> str:
    base = _ensure_dir(base_dir)
    doc = {
        "generated_at": now_iso,
        "current_phase": phase.value,
        "reasons": reasons,
    }
    path = base / PHASE_CURRENT
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return str(path)


def write_macro_plan(base_dir: Path, macro: MacroPlan) -> str:
    base = _ensure_dir(base_dir)
    path = base / MACRO_PLAN
    path.write_text(macro.model_dump_json(indent=2))
    return str(path)


def write_meso_block(base_dir: Path, meso: MesoBlock) -> str:
    base = _ensure_dir(base_dir)
    path = base / MESO_BLOCK
    path.write_text(meso.model_dump_json(indent=2))
    return str(path)


def _micro_filename(micro: MicroCycle) -> str:
    iso_year, iso_week, _ = micro.week_start.isocalendar()
    return f"micro_cycle_{iso_year}-W{iso_week:02d}.json"


def write_micro_cycle(base_dir: Path, micro: MicroCycle) -> str:
    base = _ensure_dir(base_dir)
    path = base / _micro_filename(micro)
    path.write_text(micro.model_dump_json(indent=2))
    return str(path)


def write_periodization_snapshot(
    base_dir: Path, snap: PeriodizationSnapshot
) -> str:
    """写入总快照 + 同步写入 phase_current / macro / meso / micro。"""
    base = _ensure_dir(base_dir)
    write_phase_current(
        base, snap.current_phase,
        reasons=[f"Snapshot regenerated at {snap.generated_at}"],
        now_iso=snap.generated_at,
    )
    write_macro_plan(base, snap.macro)
    write_meso_block(base, snap.meso)
    write_micro_cycle(base, snap.micro)
    path = base / SNAPSHOT
    path.write_text(snap.model_dump_json(indent=2))
    return str(path)


def load_periodization_snapshot(base_dir: Path) -> Optional[PeriodizationSnapshot]:
    path = Path(base_dir) / SNAPSHOT
    if not path.exists():
        return None
    try:
        return PeriodizationSnapshot.model_validate_json(path.read_text())
    except Exception:
        return None
