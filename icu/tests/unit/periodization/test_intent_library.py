from src.coach.periodization.intent_library import (
    build_intent_for_phase, INTENT_TEMPLATES,
)
from src.coach.periodization.types import Phase


def test_all_phases_have_template():
    for p in Phase:
        assert p in INTENT_TEMPLATES


def test_build_intent_scales_tss_with_ctl():
    intent_lo = build_intent_for_phase(Phase.BUILD, baseline_ctl=60)
    intent_hi = build_intent_for_phase(Phase.BUILD, baseline_ctl=110)
    assert intent_lo.weekly_tss_target < intent_hi.weekly_tss_target
    # 分配比例应该保持一致
    assert intent_lo.intensity_distribution_pct == intent_hi.intensity_distribution_pct


def test_taper_has_high_intensity_preserved():
    intent = build_intent_for_phase(Phase.TAPER, baseline_ctl=90)
    assert intent.intensity_distribution_pct["high"] >= 25
    # vol: TSS target 应 << BUILD
    build = build_intent_for_phase(Phase.BUILD, baseline_ctl=90)
    assert intent.weekly_tss_target < build.weekly_tss_target * 0.6


def test_base_polarized_distribution():
    intent = build_intent_for_phase(Phase.BASE, baseline_ctl=90)
    assert intent.intensity_distribution_pct["low"] >= 80


def test_rationale_cites_source():
    intent = build_intent_for_phase(Phase.TAPER, baseline_ctl=90)
    assert "Mujika" in intent.rationale or "taper" in intent.rationale.lower()


def test_distribution_always_sums_to_100():
    for p in Phase:
        intent = build_intent_for_phase(p, baseline_ctl=85)
        assert sum(intent.intensity_distribution_pct.values()) == 100


def test_build_intent_respects_minimum_ctl_guard():
    # 极低 CTL 时仍有合理下限
    intent = build_intent_for_phase(Phase.BUILD, baseline_ctl=20)
    assert intent.weekly_tss_target >= 150
