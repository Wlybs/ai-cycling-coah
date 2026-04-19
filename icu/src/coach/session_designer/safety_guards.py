"""周计划安全护栏。给 assembler 在 T42 用。"""
from __future__ import annotations

from pydantic import BaseModel

STAND_KEYWORDS = ("standing climb", "standing attack", "摇车", "climb attack")
HARD_DAYS_WEEKLY_LIMIT = 4  # 一周 HARD 日数阈值（用户决策 2026-04-18）


class SafetyViolation(BaseModel):
    rule: str
    day_index: int | None = None
    message: str
    suggested_action: str


def _is_hard(day: dict) -> bool:
    return str(day.get("tier", "")).upper() == "HARD"


def _has_stand_keyword(hint: str) -> bool:
    h = hint.lower()
    return any(k in h for k in STAND_KEYWORDS)


def _tolerance_for(response_profile: dict, type_key: str) -> str | None:
    """Case-insensitive lookup of response_profile['types'][type_key]['tolerance_class']."""
    types = (response_profile or {}).get("types") or {}
    needle = type_key.lower()
    for k, v in types.items():
        if isinstance(k, str) and k.lower() == needle:
            return (v or {}).get("tolerance_class")
    return None


def _infer_type_key(hint: str) -> str | None:
    h = hint.lower()
    if "vo2" in h:
        return "VO2max"
    if "threshold" in h:
        return "Threshold"
    if "sweet" in h:
        return "Tempo"
    return None


def _tolerance_allows_hard_back_to_back(
    response_profile: dict, day1: dict, day2: dict
) -> bool:
    for day in (day1, day2):
        key = _infer_type_key(day.get("session_hint", ""))
        if key is None:
            return False
        tc = _tolerance_for(response_profile, key)
        if tc != "high":
            return False
    return True


def check_weekly_plan(
    days: list[dict],
    weekly_tss_target: int,
    response_profile: dict,
    durability: dict,
    w_prime_joules: int,
) -> list[SafetyViolation]:
    out: list[SafetyViolation] = []

    # Rule: missing rest day
    if not any(str(d.get("tier", "")).upper() == "REST" for d in days):
        out.append(SafetyViolation(
            rule="missing_rest_day",
            message="本周无 REST 日",
            suggested_action="把周五或周一改 REST",
        ))

    # Rule: hard back-to-back
    for i in range(len(days) - 1):
        if _is_hard(days[i]) and _is_hard(days[i+1]):
            if not _tolerance_allows_hard_back_to_back(
                response_profile, days[i], days[i+1]
            ):
                out.append(SafetyViolation(
                    rule="hard_back_to_back",
                    day_index=i+1,
                    message=f"连续 HARD：{days[i]['day_of_week']} & "
                            f"{days[i+1]['day_of_week']}",
                    suggested_action="把第二天降级为 MEDIUM 或 EASY",
                ))

    # Rule: knee back-to-back standing
    knee_flag = (response_profile or {}).get("knee_loading", {}).get("flag")
    if knee_flag in ("watch", "caution"):
        for i in range(len(days) - 1):
            if (_has_stand_keyword(days[i].get("session_hint", ""))
                    and _has_stand_keyword(days[i+1].get("session_hint", ""))):
                out.append(SafetyViolation(
                    rule="knee_back_to_back_stand",
                    day_index=i+1,
                    message=f"连续 2 天出现站骑/摇车动作，knee_flag={knee_flag}",
                    suggested_action="把第二天改为 rest 或 recovery_spin",
                ))

    # Rule: TSS budget overflow
    total_tss = sum(int(d.get("target_tss", 0)) for d in days)
    if total_tss > weekly_tss_target * 1.15:
        out.append(SafetyViolation(
            rule="tss_budget_overflow",
            message=f"周 TSS {total_tss} > target {weekly_tss_target} * 1.15",
            suggested_action="把最后一个 EASY 日的 target_tss 下调",
        ))

    # Rule: W' weekly overdraw — 一周 HARD 日数 ≥ HARD_DAYS_WEEKLY_LIMIT
    hard_indices = [i for i, d in enumerate(days) if _is_hard(d)]
    if len(hard_indices) >= HARD_DAYS_WEEKLY_LIMIT:
        fourth_hard = hard_indices[HARD_DAYS_WEEKLY_LIMIT - 1]
        out.append(SafetyViolation(
            rule="w_prime_weekly_overdraw",
            day_index=fourth_hard,
            message=f"本周 HARD 日 {len(hard_indices)} 次 "
                    f"(阈值 {HARD_DAYS_WEEKLY_LIMIT})，累积疲劳风险",
            suggested_action=f"把第 {HARD_DAYS_WEEKLY_LIMIT} 次起的 HARD 日降级为 MEDIUM",
        ))

    return out
