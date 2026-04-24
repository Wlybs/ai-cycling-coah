"""宏观规划：赛历 → 一串 MacroWindow。倒推算法，详见 03-macro-planner.md T31。"""
from __future__ import annotations

from datetime import date, timedelta

from .intent_library import build_intent_for_phase
from .race_calendar import RaceEntry
from .types import MacroPlan, MacroWindow, Phase

TAPER_DAYS = 10
PEAK_DAYS = 14
BUILD_DAYS = 28
BASE_DAYS = 42
MAINTAIN_MIN_GAP_DAYS = 56
DEFAULT_HORIZON_WEEKS = 12
TRANSITION_EVERY_WEEKS = 4
TRANSITION_LEN_DAYS = 7
CTL_BASE_PROTECT = 75.0  # 与 phase_detector 一致（用户决策 2026-04-18）


def _backwards_from_race(
    race: RaceEntry, baseline_ctl: float
) -> list[MacroWindow]:
    """从一场 A 级赛倒推 Taper → Peak → Build → Base。"""
    r = race.race_date
    taper_start = r - timedelta(days=TAPER_DAYS)
    peak_start = taper_start - timedelta(days=PEAK_DAYS)
    build_start = peak_start - timedelta(days=BUILD_DAYS)
    base_start = build_start - timedelta(days=BASE_DAYS)
    return [
        MacroWindow(phase=Phase.BASE, start_date=base_start,
                    end_date=build_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.BASE, baseline_ctl)),
        MacroWindow(phase=Phase.BUILD, start_date=build_start,
                    end_date=peak_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.BUILD, baseline_ctl)),
        MacroWindow(phase=Phase.PEAK, start_date=peak_start,
                    end_date=taper_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.PEAK, baseline_ctl)),
        MacroWindow(phase=Phase.TAPER, start_date=taper_start,
                    end_date=r - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.TAPER, baseline_ctl)),
    ]


def _maintain_between(
    prev_race: RaceEntry, next_race: RaceEntry, baseline_ctl: float
) -> list[MacroWindow]:
    """两赛间隔短的情况：仅 Peak(缩) + Taper。"""
    gap_days = (next_race.race_date - prev_race.race_date).days
    # 保留前赛后 3 天的微恢复 → 然后 Peak → Taper
    peak_start = prev_race.race_date + timedelta(days=3)
    taper_start = next_race.race_date - timedelta(days=TAPER_DAYS)
    if peak_start >= taper_start:
        # 实在太挤，合并成短 Taper
        return [MacroWindow(
            phase=Phase.TAPER, start_date=peak_start,
            end_date=next_race.race_date - timedelta(days=1),
            intent=build_intent_for_phase(Phase.TAPER, baseline_ctl),
        )]
    return [
        MacroWindow(phase=Phase.PEAK, start_date=peak_start,
                    end_date=taper_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.PEAK, baseline_ctl)),
        MacroWindow(phase=Phase.TAPER, start_date=taper_start,
                    end_date=next_race.race_date - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.TAPER, baseline_ctl)),
    ]


def _default_rolling_build(
    reference_date: date, baseline_ctl: float, horizon_weeks: int
) -> list[MacroWindow]:
    """无赛历：根据 baseline_ctl 决定走 BASE 还是 BUILD 循环。

    - CTL < CTL_BASE_PROTECT (75)：整个 horizon 全 BASE（底盘保护）。
    - 否则：每 4 周 BUILD + 1 周 TRANSITION 循环。
    """
    end = reference_date + timedelta(weeks=horizon_weeks)

    if baseline_ctl < CTL_BASE_PROTECT:
        return [MacroWindow(
            phase=Phase.BASE,
            start_date=reference_date,
            end_date=end - timedelta(days=1),
            intent=build_intent_for_phase(Phase.BASE, baseline_ctl),
        )]

    out: list[MacroWindow] = []
    cur = reference_date
    while cur < end:
        b_end = min(cur + timedelta(weeks=TRANSITION_EVERY_WEEKS) - timedelta(days=1),
                    end - timedelta(days=1))
        out.append(MacroWindow(
            phase=Phase.BUILD, start_date=cur, end_date=b_end,
            intent=build_intent_for_phase(Phase.BUILD, baseline_ctl),
        ))
        cur = b_end + timedelta(days=1)
        if cur >= end:
            break
        t_end = min(cur + timedelta(days=TRANSITION_LEN_DAYS - 1),
                    end - timedelta(days=1))
        out.append(MacroWindow(
            phase=Phase.TRANSITION, start_date=cur, end_date=t_end,
            intent=build_intent_for_phase(Phase.TRANSITION, baseline_ctl),
        ))
        cur = t_end + timedelta(days=1)
    return out


def _merge_and_trim(windows: list[MacroWindow]) -> list[MacroWindow]:
    """按 start_date 排序，后者覆盖前者的尾部，保证不重叠。"""
    if not windows:
        return []
    sorted_w = sorted(windows, key=lambda w: w.start_date)
    out: list[MacroWindow] = [sorted_w[0]]
    for w in sorted_w[1:]:
        prev = out[-1]
        if w.start_date <= prev.end_date:
            # model_copy skips validators in Pydantic v2; manually check end >= start below.
            out[-1] = prev.model_copy(
                update={"end_date": w.start_date - timedelta(days=1)}
            )
            if out[-1].end_date < out[-1].start_date:
                out.pop()
        out.append(w)
    # 丢弃非法窗口
    return [w for w in out if w.end_date >= w.start_date]


def plan_macro(
    reference_date: date,
    baseline_ctl: float,
    races: list[RaceEntry],
    generated_at: str,
) -> MacroPlan:
    """根据参考日期、baseline CTL 和赛历生成宏观训练计划。

    - 每场 A 级赛倒推 BASE→BUILD→PEAK→TAPER；两赛间隔 < 56 天走 maintain 分支。
    - 无 A 级赛：baseline_ctl < 75 全走 BASE（底盘保护），否则 BUILD + TRANSITION 循环。
    """
    a_races = sorted(
        [r for r in races if r.priority.upper() == "A"
         and r.race_date >= reference_date],
        key=lambda r: r.race_date,
    )
    if not a_races:
        windows = _default_rolling_build(
            reference_date, baseline_ctl, DEFAULT_HORIZON_WEEKS
        )
        season_end = (reference_date
                      + timedelta(weeks=DEFAULT_HORIZON_WEEKS))
    else:
        windows: list[MacroWindow] = []
        for idx, race in enumerate(a_races):
            if idx == 0:
                windows.extend(_backwards_from_race(race, baseline_ctl))
            else:
                prev = a_races[idx - 1]
                gap = (race.race_date - prev.race_date).days
                if gap < MAINTAIN_MIN_GAP_DAYS:
                    windows.extend(_maintain_between(prev, race, baseline_ctl))
                else:
                    windows.extend(_backwards_from_race(race, baseline_ctl))
        season_end = a_races[-1].race_date + timedelta(days=7)

    windows = _merge_and_trim([w for w in windows
                               if w.end_date >= reference_date])
    return MacroPlan(
        generated_at=generated_at,
        season_end_date=season_end,
        windows=windows,
    )
