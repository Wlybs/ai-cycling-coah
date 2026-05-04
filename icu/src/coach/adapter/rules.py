"""Deterministic threshold rules for the Adaptation Engine.

判定流程（pure function chain）:
    snapshot + history + state →
        4 个 _classify_<signal>() → signal_summary →
        worst-of-four → base verdict →
        guardrails (TSB anomaly / consecutive red) → final verdict + action
    → AdaptationVerdict

所有阈值常量在文件顶部，每条注解写**为什么是这个数字**（避免调参失忆，
见 specs/2026-04-19-phase-3-blueprint.md §Component 5 规则引擎表格）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from src.coach.common.logging import get_logger
from src.coach.ledger.types import AthleteStateRef, DecisionEntry

from .types import (
    SIGNAL_KEYS,
    AdaptationVerdict,
    RecommendedAction,
    SignalSnapshot,
    Verdict,
)

_log = get_logger("adapter")


# ---------- 阈值常量（每条带 Why） ----------

# HRV 偏离 % vs 28d rolling mean
HRV_DEVIATION_YELLOW_PCT: float = -5.0
"""≤ -5% 进入 yellow。Why: 蓝图 §Component 5 表格"≥ −5% / −5~−10% / <−10%"。"""
HRV_DEVIATION_RED_PCT: float = -10.0
"""≤ -10% 进入 red。Why: 同上。"""

# Resting HR 偏离基线 (bpm)，正值=升高=应激
RESTING_HR_YELLOW_DELTA_BPM: int = 4
"""+4..+6 bpm 进入 yellow。Why: HRV4Training 文献 +5bpm 对应 ANS 失衡早期信号。"""
RESTING_HR_RED_DELTA_BPM: int = 7
"""≥ +7 bpm 进入 red。Why: 同源；与 HRV red 阈值同步触发概率 > 0.6。"""

# 睡眠时长 (hours)
SLEEP_YELLOW_HOURS: float = 7.0
"""< 7h 进入 yellow。Why: 蓝图阈值表"≥7h / 5.5~7h / <5.5h"。"""
SLEEP_RED_HOURS: float = 5.5
"""< 5.5h 进入 red。Why: 同上；连续夜短睡眠 < 5.5h 与训练适应受损强相关。"""

# Soreness 评分（Intervals.icu 1=worst..4=best）
SORENESS_YELLOW_SCORE: int = 2
"""=2 进入 yellow。Why: 与蓝图"任一=2"对齐（只跟踪 soreness 单维度）。"""
SORENESS_RED_SCORE: int = 1
"""=1 进入 red。Why: 与蓝图"任一=1"对齐。"""

# 加权严重度
_WEIGHTS: dict[str, float] = {
    "hrv": 0.30,         # ANS 状态 —— 最敏感的应激指标
    "resting_hr": 0.20,  # ANS 副指标 —— 与 HRV 部分共线，权重略低
    "sleep": 0.30,       # 恢复底盘 —— 与 HRV 同等关键
    "soreness": 0.20,    # 主观、噪声大；权重偏低但保留 veto 能力
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"
_SCORE_OF: dict[str, float] = {"green": 0.0, "yellow": 0.5, "red": 1.0}

# 护栏
TSB_ANOMALY_THRESHOLD: float = -30.0
"""TSB < -30 触发。Why: ATL/CTL 模型经验值 —— TSB < -30 对应非常高的过载风险。"""
CONSECUTIVE_RED_LIMIT: int = 3
"""过去 4 天内已 ≥3 红 + 今日红 → 升级 rest_48h。Why: 蓝图"过去 3 天已有 3 次红 + 今天又判红"。"""
_RED_LOOKBACK_DAYS: int = 4
"""扫描窗口（含今天前一天起 4 天）。"""

_HRV_BASELINE_FIELD = "hrv_ms_28d_mean"
_HR_BASELINE_FIELD = "resting_hr_28d_mean"


# ---------- 信号分类 ----------

def _classify_hrv(*, deviation_pct: float) -> Verdict:
    """deviation_pct = (today - 28d_mean) / 28d_mean × 100. 负值 = 偏低 = 应激。"""
    if deviation_pct <= HRV_DEVIATION_RED_PCT:
        return "red"
    if deviation_pct <= HRV_DEVIATION_YELLOW_PCT:
        return "yellow"
    return "green"


def _classify_resting_hr(*, delta_bpm: int) -> Verdict:
    """delta_bpm = today - 28d_mean (bpm). 正值 = 升高 = 应激。"""
    if delta_bpm >= RESTING_HR_RED_DELTA_BPM:
        return "red"
    if delta_bpm >= RESTING_HR_YELLOW_DELTA_BPM:
        return "yellow"
    return "green"


def _classify_sleep(*, sleep_hours: float) -> Verdict:
    if sleep_hours < SLEEP_RED_HOURS:
        return "red"
    if sleep_hours < SLEEP_YELLOW_HOURS:
        return "yellow"
    return "green"


def _classify_soreness(*, score: int | None) -> Verdict:
    if score is None:
        return "green"
    if score <= SORENESS_RED_SCORE:
        return "red"
    if score <= SORENESS_YELLOW_SCORE:
        return "yellow"
    return "green"


def _severity_score(summary: dict[str, str]) -> float:
    return sum(_WEIGHTS[k] * _SCORE_OF[summary[k]] for k in SIGNAL_KEYS)


# ---------- 护栏 ----------

def _tsb_anomaly_hit(state: AthleteStateRef) -> bool:
    return state.tsb < TSB_ANOMALY_THRESHOLD


def _consecutive_red_count(history: Iterable[DecisionEntry]) -> int:
    """Count `adaptation_verdict` entries with verdict='red' in the last
    `_RED_LOOKBACK_DAYS` days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RED_LOOKBACK_DAYS)
    count = 0
    for entry in history:
        if entry.decision_type != "adaptation_verdict":
            continue
        if entry.timestamp < cutoff:
            continue
        if str(entry.payload.get("verdict", "")).lower() == "red":
            count += 1
    return count


# ---------- 主入口 ----------

_WORST: dict[str, int] = {"green": 0, "yellow": 1, "red": 2}
_INVERSE: dict[int, Verdict] = {0: "green", 1: "yellow", 2: "red"}


def evaluate_signals(
    snapshot: SignalSnapshot,
    *,
    state: AthleteStateRef,
    history: Iterable[DecisionEntry] = (),
    hrv_28d_mean_ms: float | None = None,
    resting_hr_28d_mean_bpm: float | None = None,
) -> AdaptationVerdict:
    """Pure judge: snapshot + state + history → AdaptationVerdict.

    `hrv_28d_mean_ms` / `resting_hr_28d_mean_bpm` 由调用方（T60 daily_adapt）
    从 wellness_history 预计算并传入；缺失时该信号判 green（保守 fallback）。
    """
    # 1. 4 信号分类
    if hrv_28d_mean_ms and hrv_28d_mean_ms > 0:
        hrv_dev = (snapshot.hrv_ms - hrv_28d_mean_ms) / hrv_28d_mean_ms * 100.0
        hrv_v = _classify_hrv(deviation_pct=hrv_dev)
    else:
        hrv_v = "green"

    if resting_hr_28d_mean_bpm and resting_hr_28d_mean_bpm > 0:
        hr_delta = int(round(snapshot.resting_hr_bpm - resting_hr_28d_mean_bpm))
        hr_v = _classify_resting_hr(delta_bpm=hr_delta)
    else:
        hr_v = "green"

    sleep_v = _classify_sleep(sleep_hours=snapshot.sleep_hours)
    sore_v = _classify_soreness(score=snapshot.soreness_score)

    summary: dict[str, Verdict] = {
        "hrv": hrv_v, "resting_hr": hr_v,
        "sleep": sleep_v, "soreness": sore_v,
    }

    triggered: list[str] = []
    if hrv_v == "red":
        triggered.append("hrv_red_threshold")
    if hr_v == "red":
        triggered.append("resting_hr_red_threshold")
    if sleep_v == "red":
        triggered.append("sleep_debt_acute")
    if sore_v == "red":
        triggered.append("soreness_red")

    # 2. base verdict = worst-of-four
    base_idx = max(_WORST[v] for v in summary.values())
    verdict: Verdict = _INVERSE[base_idx]

    severity = _severity_score(summary)

    # 3. 护栏
    guardrails: list[str] = []
    if _tsb_anomaly_hit(state):
        guardrails.append("tsb_anomaly")
        verdict = "red"
        severity = min(1.0, severity + 0.1)

    action: RecommendedAction
    if verdict == "green":
        action = "none"
    elif verdict == "yellow":
        action = "nudge_only"
    else:
        action = "propose_replacement"

    if verdict == "red" and _consecutive_red_count(history) >= CONSECUTIVE_RED_LIMIT - 1:
        # Today's red would make it the CONSECUTIVE_RED_LIMIT-th.
        guardrails.append("consecutive_red_escalation")
        action = "rest_48h"

    notes = None
    if hrv_28d_mean_ms:
        notes = f"hrv_dev={hrv_dev:+.1f}% vs 28d mean"

    verdict_obj = AdaptationVerdict(
        verdict=verdict,
        signal_summary=summary,
        severity_score=severity,
        recommended_action=action,
        triggered_rules=triggered,
        guardrails_hit=guardrails,
        notes=notes,
    )
    _log.event(
        "adapter_verdict_evaluated",
        verdict=verdict,
        severity=round(severity, 3),
        triggered=triggered,
        guardrails=guardrails,
        recommended_action=action,
    )
    return verdict_obj
