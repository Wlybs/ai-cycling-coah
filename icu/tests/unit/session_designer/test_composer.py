from datetime import date

from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import SessionIntent
from src.coach.periodization.types import IntensityTier, SessionType


def _physiology(cp=280, w_prime=22000):
    return {"cp_watts": cp, "w_prime_joules": w_prime, "fit_r_squared": 0.95,
            "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": -8}


def test_compose_threshold_session_produces_watts():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280),
        durability={}, response_profile={},
    )
    assert session.session_type is SessionType.THRESHOLD
    # 2x20 main 段的 watts 应该 ≈ 97-102% × 280
    main_steps = [s for s in session.structure.steps if "TH" in s.label]
    for step in main_steps:
        assert step.target_w_low is not None
        assert 270 <= step.target_w_low <= 275
        assert 285 <= step.target_w_high <= 290
    assert "W" in (session.power_range_w or "")


def test_compose_long_z2_stretches_duration_to_match_tss():
    intent = SessionIntent(
        day_of_week="Sun", tier=IntensityTier.EASY,
        target_tss=160, session_hint="long Z2 3h+",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 26),
        template_name="endurance_long_z2",
        physiology=_physiology(cp=280),
        durability={"decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0}},
        response_profile={},
    )
    assert session.duration_min >= 180
    assert session.target_tss == 160
    assert session.trace is not None
    assert "duration_stretched_pct" in session.trace


def test_compose_rest_day_returns_empty_structure():
    intent = SessionIntent(
        day_of_week="Mon", tier=IntensityTier.REST,
        target_tss=0, session_hint="rest",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 20),
        template_name="rest_day",
        physiology=_physiology(), durability={}, response_profile={},
    )
    assert session.session_type is SessionType.REST
    assert session.duration_min == 0
    assert len(session.structure.steps) == 0


def test_compose_uses_cp_not_ftp_when_different():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=90, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=265),
        durability={}, response_profile={},
    )
    main = [s for s in session.structure.steps if "TH" in s.label][0]
    assert main.target_w_low < 260


def test_compose_tss_within_15pct_of_target_for_intervals():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280),
        durability={}, response_profile={},
    )
    diff = abs(session.target_tss - 95)
    assert diff <= 95 * 0.15


def test_description_contains_schema():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(), durability={}, response_profile={},
    )
    desc = session.description.lower()
    assert "wu" in desc or "warmup" in desc or "热身" in desc
    assert "cd" in desc or "cooldown" in desc or "整理" in desc


def test_trace_records_cp_and_template_name():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280, w_prime=22000),
        durability={"decay_rate_pct_per_1000kj": {"60s": 3.0}},
        response_profile={"types": {"Threshold": {"tolerance_class": "medium"}}},
    )
    trace = session.trace
    assert trace["template_name"] == "threshold_2x20"
    assert trace["cp_watts"] == 280
    assert trace["w_prime_joules"] == 22000
    assert "tss_estimated" in trace


def test_tolerance_class_matched_case_insensitively():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    # response_profile keys may arrive lowercase (from physiology.response_profile)
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280),
        durability={},
        response_profile={"types": {"threshold": {"tolerance_class": "high"}}},
    )
    assert session.trace["tolerance_class"] == "high"
