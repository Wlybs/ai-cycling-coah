from ..types import Findings


def analyze(activity: dict, physiology: dict | None, wbal_series: dict | None) -> Findings:
    if wbal_series is None:
        return Findings(
            analyzer="w_balance",
            metrics={"reason": "no W' balance series available"},
            verdict="数据不足",
            evidence=[],
        )

    work_laps = [l for l in wbal_series["laps"] if l["type"] == "work"]
    recov_laps = [l for l in wbal_series["laps"] if l["type"] == "recovery"]
    max_dep = max((l["depletion_pct"] for l in work_laps), default=0.0)
    avg_recov_pct = (
        sum(abs(l["depletion_pct"]) for l in recov_laps) / len(recov_laps)
        if recov_laps else 0.0
    )
    min_pct = wbal_series.get("min_w_bal_pct", 100)
    sec_below_15 = wbal_series.get("seconds_below_15pct", 0)

    if min_pct < 15 or sec_below_15 > 60:
        verdict = "过度依赖 W' 债务"
    elif max_dep > 60 and avg_recov_pct < 50:
        verdict = "W' 管理失衡"
    else:
        verdict = "W' 管理得当"

    return Findings(
        analyzer="w_balance",
        metrics={
            "max_lap_depletion_pct": round(max_dep, 1),
            "avg_recovery_restore_pct": round(avg_recov_pct, 1),
            "min_w_bal_pct": round(min_pct, 1),
            "seconds_below_15pct": sec_below_15,
        },
        verdict=verdict,
        evidence=[
            (f"最低 W'bal {min_pct:.1f}% ；低于15%累计 {sec_below_15}s", "w_balance_model output"),
            (f"最大区间消耗 {max_dep:.1f}% ；平均恢复回升 {avg_recov_pct:.1f}%", "laps[].depletion_pct"),
        ],
    )
