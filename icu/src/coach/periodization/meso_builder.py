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


def build_meso_block(*args, **kwargs):
    """Placeholder — implemented in Task T33."""
    raise NotImplementedError("build_meso_block implemented in T33")
