from src.coach.session_designer.safety_guards import (
    check_weekly_plan, SafetyViolation,
)


def _day(i, tss, hint, tier="HARD"):
    return {
        "day_of_week": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][i],
        "tier": tier, "target_tss": tss, "session_hint": hint,
    }


def test_back_to_back_hard_flagged():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 110, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=465, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "hard_back_to_back" for v in violations)


def test_knee_back_to_back_standing_violation():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 90, "standing climb intervals 5x5", "HARD"),
        _day(2, 95, "standing climb attacks", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=470,
        response_profile={"knee_loading": {"flag": "caution"}},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "knee_back_to_back_stand" for v in violations)


def test_tss_overflow_flagged():
    days = [_day(i, 120, "x", "HARD") for i in range(7)]
    violations = check_weekly_plan(
        days, weekly_tss_target=500, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "tss_budget_overflow" for v in violations)


def test_missing_rest_day_flagged():
    days = [_day(i, 60, "tempo", "EASY") for i in range(7)]
    violations = check_weekly_plan(
        days, weekly_tss_target=420, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "missing_rest_day" for v in violations)


def test_high_tolerance_allows_back_to_back_hard():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=465,
        response_profile={
            "types": {"Threshold": {"tolerance_class": "high"},
                      "VO2max": {"tolerance_class": "high"}}
        }, durability={}, w_prime_joules=22000,
    )
    assert not any(v.rule == "hard_back_to_back" for v in violations)


def test_no_violations_on_clean_plan():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 40, "recovery", "EASY"),
        _day(3, 75, "sweet-spot 3x15", "MEDIUM"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=440, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert len(violations) == 0


def test_three_hard_days_does_not_trigger_w_prime_rule():
    """標準 BUILD 週 2-3 次 HARD 是常態，不應報警。"""
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 40, "recovery", "EASY"),
        _day(3, 90, "VO2max 5x4", "HARD"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=455,
        response_profile={"types": {
            "Threshold": {"tolerance_class": "high"},
            "VO2max": {"tolerance_class": "high"}}},
        durability={}, w_prime_joules=22000,
    )
    assert not any(v.rule == "w_prime_weekly_overdraw" for v in violations)


def test_four_hard_days_triggers_w_prime_rule():
    """≥ 4 次 HARD 觸發累積疲勞警告（用戶決策 2026-04-18）。"""
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 85, "threshold 2x15", "HARD"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=500,
        response_profile={"types": {
            "Threshold": {"tolerance_class": "high"},
            "VO2max": {"tolerance_class": "high"}}},
        durability={}, w_prime_joules=22000,
    )
    w_p = [v for v in violations if v.rule == "w_prime_weekly_overdraw"]
    assert len(w_p) == 1
    assert w_p[0].day_index == 5
