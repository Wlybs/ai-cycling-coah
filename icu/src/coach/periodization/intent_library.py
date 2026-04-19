"""每个 Phase 的生理学意图模板。来源：Allen-Coggan、Seiler、Mujika 公开协议。"""
from __future__ import annotations

from .types import Phase, PhaseIntent

MIN_WEEKLY_TSS = 150


INTENT_TEMPLATES: dict[Phase, dict] = {
    Phase.BASE: {
        "primary_adaptation": "aerobic_base",
        "tss_per_ctl": 5.0,
        "distribution": {"low": 85, "mid": 10, "high": 5},
        "rest_days": 1,
        "rationale": (
            "Seiler 2010 polarized base: ≥80% low-intensity. 目标打底有氧、线粒体密度、"
            "脂肪氧化能力；不追强度。"
        ),
    },
    Phase.BUILD: {
        "primary_adaptation": "threshold_capacity",
        "tss_per_ctl": 5.8,
        "distribution": {"low": 75, "mid": 15, "high": 10},
        "rest_days": 1,
        "rationale": (
            "Allen-Coggan 2019 build block: sweet-spot + threshold 为主，周期性加入 "
            "VO2max 刺激。CTL ramp rate 目标 3–5/周。"
        ),
    },
    Phase.PEAK: {
        "primary_adaptation": "vo2_power_sharpening",
        "tss_per_ctl": 5.3,
        "distribution": {"low": 65, "mid": 15, "high": 20},
        "rest_days": 1,
        "rationale": (
            "Peak block 把高强度占比抬到 20%，短间歇 (3–5min) 反复出现，"
            "同时开始降低总量，为 Taper 铺路。"
        ),
    },
    Phase.TAPER: {
        "primary_adaptation": "freshness_preservation",
        "tss_per_ctl": 2.5,
        "distribution": {"low": 60, "mid": 10, "high": 30},
        "rest_days": 2,
        "rationale": (
            "Mujika 2009 taper meta-analysis: 总量 -41–60%，但保持强度；刺激短而尖。"
            "关键是让 ATL 快速下降、TSB 回到 +5~+15。"
        ),
    },
    Phase.RACE: {
        "primary_adaptation": "race_execution",
        "tss_per_ctl": 1.5,
        "distribution": {"low": 50, "mid": 10, "high": 40},
        "rest_days": 2,
        "rationale": (
            "Race week: openers only。目标是把神经和能量系统唤醒，不做任何产生显著 "
            "TSS 的动作。"
        ),
    },
    Phase.TRANSITION: {
        "primary_adaptation": "active_recovery",
        "tss_per_ctl": 2.8,
        "distribution": {"low": 95, "mid": 5, "high": 0},
        "rest_days": 3,
        "rationale": (
            "Off-season / transition: 2–4 周无结构化训练，降低 CTL、释放累积疲劳、"
            "处理伤病。没有强度，只做 Z1/Z2 户外骑行。"
        ),
    },
}


def build_intent_for_phase(phase: Phase, baseline_ctl: float) -> PhaseIntent:
    tpl = INTENT_TEMPLATES[phase]
    weekly_tss = max(MIN_WEEKLY_TSS, int(round(baseline_ctl * tpl["tss_per_ctl"])))
    return PhaseIntent(
        phase=phase,
        primary_adaptation=tpl["primary_adaptation"],
        weekly_tss_target=weekly_tss,
        intensity_distribution_pct=dict(tpl["distribution"]),
        rest_days_per_week=tpl["rest_days"],
        rationale=tpl["rationale"],
    )
