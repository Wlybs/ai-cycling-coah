from datetime import date, timedelta
from src.coach.periodization.macro_planner import plan_macro
from src.coach.periodization.race_calendar import RaceEntry
from src.coach.periodization.types import Phase


def test_single_race_builds_six_windows_backwards():
    race = RaceEntry(name="Goal HC", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18),
        baseline_ctl=90,
        races=[race],
        generated_at="2026-04-18T00:00:00Z",
    )
    phases = [w.phase for w in plan.windows]
    # 必须包含逆推出的完整链
    assert Phase.TAPER in phases
    assert Phase.PEAK in phases
    assert Phase.BUILD in phases
    assert Phase.BASE in phases
    # 最后一个窗口的 end >= race_date - 1
    last = [w for w in plan.windows if w.phase is Phase.TAPER][-1]
    assert race.race_date - last.end_date <= timedelta(days=1)


def test_no_races_defaults_to_rolling_build_with_transition():
    plan = plan_macro(
        reference_date=date(2026, 1, 5),
        baseline_ctl=80,
        races=[],
        generated_at="2026-01-05T00:00:00Z",
    )
    phases = [w.phase for w in plan.windows]
    assert Phase.BUILD in phases
    # 应该插入至少一次 Transition 微恢复
    assert Phase.TRANSITION in phases


def test_no_races_low_ctl_rolls_out_as_base():
    """底盘保护：baseline_ctl < 75 且无赛 → 全 12 周 BASE。"""
    plan = plan_macro(
        reference_date=date(2026, 1, 5),
        baseline_ctl=68,
        races=[],
        generated_at="2026-01-05T00:00:00Z",
    )
    phases = {w.phase for w in plan.windows}
    assert Phase.BASE in phases
    assert Phase.BUILD not in phases


def test_two_close_races_no_gap_becomes_maintain():
    r1 = RaceEntry(name="Race1", race_date=date(2026, 5, 3), priority="A")
    r2 = RaceEntry(name="Race2", race_date=date(2026, 5, 24), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 1), baseline_ctl=88,
        races=[r1, r2],
        generated_at="2026-04-01T00:00:00Z",
    )
    # 两赛间隔 21 天 < 56 天 → 不再走完整 Base→Build→Peak→Taper；
    # 第二场赛前有一次小 Taper/Peak
    r2_taper = [w for w in plan.windows
                if w.phase is Phase.TAPER and w.end_date <= r2.race_date]
    assert len(r2_taper) >= 1


def test_generated_windows_are_sorted_and_non_overlapping():
    race = RaceEntry(name="A", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18), baseline_ctl=90,
        races=[race], generated_at="2026-04-18T00:00:00Z",
    )
    starts = [w.start_date for w in plan.windows]
    ends = [w.end_date for w in plan.windows]
    assert starts == sorted(starts)
    # 相邻窗口不重叠（允许 end_n == start_{n+1}）
    for i in range(len(plan.windows) - 1):
        assert plan.windows[i].end_date <= plan.windows[i+1].start_date


def test_every_window_has_intent_with_matching_phase():
    race = RaceEntry(name="A", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18), baseline_ctl=90,
        races=[race], generated_at="2026-04-18T00:00:00Z",
    )
    for w in plan.windows:
        assert w.intent.phase is w.phase
