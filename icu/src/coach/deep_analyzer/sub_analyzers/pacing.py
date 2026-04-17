from ..types import Findings


def _vi(lap):
    ap = lap.get("avg_power") or 0
    np = lap.get("np_power") or ap
    return round(np / ap, 3) if ap else 1.0


def analyze(activity: dict, physiology: dict | None = None) -> Findings:
    laps = [l for l in activity.get("laps", []) if l.get("type") == "work"]
    if len(laps) < 2:
        return Findings(
            analyzer="pacing",
            metrics={"reason": "insufficient work laps"},
            verdict="数据不足",
            evidence=[],
        )

    vis = [_vi(l) for l in laps]
    vi_mean = round(sum(vis) / len(vis), 3)
    rest = vis[1:]
    rest_mean = sum(rest) / len(rest) if rest else vi_mean
    break_idx = next((i + 1 for i, v in enumerate(vis[1:]) if v > rest_mean + 0.10), None)

    n = len(laps)
    third = max(1, n // 3)
    avg_first = sum(l["avg_power"] for l in laps[:third]) / third
    avg_last = sum(l["avg_power"] for l in laps[-third:]) / third
    delta_pct = (avg_first - avg_last) / avg_first * 100 if avg_first else 0

    if delta_pct > 10:
        verdict = "起步冒进"
    elif delta_pct < -10:
        verdict = "后段崩盘"
    elif abs(delta_pct) <= 3:
        verdict = "节奏平稳"
    else:
        verdict = "均衡分布"

    return Findings(
        analyzer="pacing",
        metrics={
            "vi_mean": vi_mean,
            "first_third_avg_w": int(round(avg_first)),
            "last_third_avg_w": int(round(avg_last)),
            "front_to_back_delta_pct": round(delta_pct, 1),
            "pacing_break_lap_index": break_idx,
        },
        verdict=verdict,
        evidence=[
            (f"前1/3平均 {int(avg_first)}W 对比后1/3 {int(avg_last)}W，差值 {delta_pct:+.1f}%", f"laps[0..{third-1}] vs laps[-{third}:]"),
            (f"整体 VI 均值 {vi_mean}", "per-lap NP/AP"),
        ],
    )
