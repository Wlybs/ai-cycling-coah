"""红灯降载映射：把今日原始 SessionType 转成低强度替代 DesignedSession。

是 adapter 层最薄的一片：
- 输入：原始 SessionType + 日期 + 生理 / 耐久 / 响应轮廓三个 dict（与 Phase 2 compose_session 一致）。
- 输出：合法 DesignedSession 或 None（None ⇔ Rest，调用方跳过 proposed_session 落盘）。

降载表见 docs/superpowers/plans/phase-3/04-adapter-session-revisor.md §Mapping table。
本文件 0 文件 IO，0 网络调用，纯函数 — 写盘由 scripts/daily_adapt.py 负责。
"""
from __future__ import annotations

from datetime import date as DateT
from typing import Any

from src.coach.common.logging import get_logger
from src.coach.periodization.types import IntensityTier, SessionType
from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import DesignedSession, SessionIntent

_log = get_logger("adapter")

# 三字母 day_of_week，索引 = date.weekday()（0=Mon）。硬编码避免 locale 漂移。
_DOW_NAMES: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# SessionType → (template_name | None, fallback_tier, fallback_tss, session_hint)
# None template_name = 直接返回 None（Rest）。
_BUCKET: dict[SessionType, tuple[str | None, IntensityTier, int, str]] = {
    SessionType.THRESHOLD:     ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.VO2MAX:        ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.NEUROMUSCULAR: ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.RACE:          ("recovery_spin",     IntensityTier.EASY, 30, "recovery spin"),
    SessionType.TEMPO:         ("endurance_long_z2", IntensityTier.EASY, 70, "long z2"),
    SessionType.AEROBIC:       (None,                IntensityTier.REST,  0, ""),
    SessionType.RECOVERY:      (None,                IntensityTier.REST,  0, ""),
    SessionType.REST:          (None,                IntensityTier.REST,  0, ""),
}


def revise_session(
    *,
    original_type: SessionType,
    original_date: DateT,
    physiology: dict[str, Any],
    durability: dict[str, Any],
    response_profile: dict[str, Any],
) -> DesignedSession | None:
    """红灯降载：返回低强度替代 DesignedSession，或 None（= Rest）。

    All-keyword-only signature 防误调。
    """
    bucket = _BUCKET.get(original_type)
    if bucket is None:
        # SessionType 枚举闭合，理论上不可达；防御性返回 None。
        _log.event(
            "session_revised",
            date=original_date.isoformat(),
            original_type=original_type.value,
            revised_to=None,
            recommended_action="rest_passthrough_unknown_type",
        )
        return None

    template_name, fallback_tier, fallback_tss, session_hint = bucket

    if template_name is None:
        _log.event(
            "session_revised",
            date=original_date.isoformat(),
            original_type=original_type.value,
            revised_to=None,
            recommended_action="rest_passthrough",
        )
        return None

    intent = SessionIntent(
        day_of_week=_DOW_NAMES[original_date.weekday()],
        tier=fallback_tier,
        target_tss=fallback_tss,
        session_hint=session_hint,
    )

    revised = compose_session(
        intent=intent,
        date=original_date,
        template_name=template_name,
        physiology=physiology,
        durability=durability,
        response_profile=response_profile,
    )

    _log.event(
        "session_revised",
        date=original_date.isoformat(),
        original_type=original_type.value,
        revised_to=revised.session_type.value,
        recommended_action="propose_replacement",
    )
    return revised
