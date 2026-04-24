"""Meso 块构造器：pattern 选择 + 周负荷乘数 + 日期窗口。"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from types import MappingProxyType
from typing import Literal, Optional

from .types import Phase

KneeFlag = Literal["caution", "watch"]
MesoPatternName = Literal["3:1", "2:1", "polarized", "linear"]

MESO_PATTERNS: Mapping[str, tuple[float, ...]] = MappingProxyType({
    "3:1": (1.00, 1.05, 1.10, 0.70),
    "2:1": (1.00, 1.08, 0.65),
    "polarized": (1.00, 1.00, 1.00, 0.85),
    "linear": (1.00, 0.70, 0.40),
})


def select_meso_pattern(
    phase: Phase,
    knee_flag: Optional[KneeFlag] = None,
    recent_atl_delta: float = 0.0,
    response_high_responder: bool = False,
) -> MesoPatternName:
    """Select the meso pattern based on phase + knee-safety + responder profile.

    Rules (priority order):
    - BASE → 'polarized'
    - TAPER / RACE → 'linear'
    - BUILD / PEAK: knee_flag ∈ {'caution','watch'} forces '3:1' (safety override);
      else 'response_high_responder=True' → '2:1'; default '3:1'
    - TRANSITION → '3:1' (deload by itself)

    ``recent_atl_delta`` is reserved for future adaptive selection and currently unused.
    """
    if phase is Phase.BASE:
        return "polarized"
    if phase in (Phase.TAPER, Phase.RACE):
        return "linear"
    if phase in (Phase.BUILD, Phase.PEAK):
        if knee_flag in ("caution", "watch"):
            return "3:1"
        if response_high_responder:
            return "2:1"
        return "3:1"
    return "3:1"


def _monday_of(d: date) -> date:
    """Return the Monday of the ISO week containing ``d``."""
    return d - timedelta(days=d.weekday())


def build_meso_block(
    reference_date: date,
    macro: "MacroWindow",
    pattern: str,
) -> "MesoBlock":
    """Build the current meso block aligned to the Monday of ``reference_date``.

    - ``block_start``: the later of ``reference_date``'s Monday and ``macro.start_date``.
    - Natural ``block_end``: ``block_start`` + (7 × len(pattern multipliers) − 1) days.
    - If the macro window ends earlier, truncate ``block_end`` to ``macro.end_date``
      and clip the multiplier list to the remaining full weeks (ceiling).
    - Enforces ``len(multipliers) >= 3`` to satisfy ``MesoBlock.weekly_load_multipliers``
      Pydantic contract (File 01 ``types.py`` declares ``min_length=3``). When the
      usable macro window is shorter than 3 weeks, the multiplier count is floored
      at 3 even though ``block_end`` reflects the true macro boundary.

    Note: when the remaining macro window is shorter than 3 weeks, ``block_end``
    reflects the true macro boundary while ``len(weekly_load_multipliers)`` stays
    at 3 (the Pydantic floor from ``MesoBlock.weekly_load_multipliers``). Callers
    must use the multiplier list length — not ``block_end - block_start`` — to
    determine the effective number of loading weeks in such edge cases.
    """
    from .types import MacroWindow, MesoBlock
    if not isinstance(macro, MacroWindow):
        raise TypeError(f"expected MacroWindow, got {type(macro).__name__}")
    if pattern not in MESO_PATTERNS:
        raise KeyError(f"unknown meso pattern: {pattern}")
    multipliers = list(MESO_PATTERNS[pattern])

    block_start = max(_monday_of(reference_date), macro.start_date)
    natural_end = block_start + timedelta(days=7 * len(multipliers) - 1)
    if natural_end <= macro.end_date:
        block_end = natural_end
    else:
        block_end = macro.end_date
        available_days = (block_end - block_start).days + 1
        full_weeks = max(3, (available_days + 6) // 7)
        full_weeks = min(full_weeks, len(multipliers))
        multipliers = multipliers[:full_weeks]
    return MesoBlock(
        pattern=pattern,
        block_start=block_start,
        block_end=block_end,
        weekly_load_multipliers=multipliers,
        phase=macro.phase,
    )
