from ..types import Findings

ZONES = {
    "vo2max": (1.06, 1.20, 12 * 60),
    "threshold": (0.95, 1.05, 20 * 60),
    "sweet-spot": (0.88, 0.94, 40 * 60),
    "tempo": (0.76, 0.88, 30 * 60),
    "aerobic": (0.56, 0.75, 45 * 60),
    "neuromuscular": (1.50, 3.00, 30),
}


def default_range(target_type: str, cp: int) -> tuple[float, float]:
    lo, hi, _ = ZONES.get(target_type, (0.95, 1.05, 20 * 60))
    return round(cp * lo), round(cp * hi)


def analyze(activity: dict, physiology: dict | None, recent_misses: list | None = None) -> Findings:
    target = activity.get("planned_type")
    if not target or target not in ZONES:
        return Findings(analyzer="target_align", metrics={"reason": "no planned target"}, verdict="目标缺失", evidence=[])

    cp = (physiology or {}).get("cp_watts") or 0
    if not cp:
        return Findings(analyzer="target_align", metrics={"reason": "no CP"}, verdict="数据不足", evidence=[])

    lo, hi = default_range(target, cp)
    _, _, min_in_zone = ZONES[target]

    seconds_in_zone = 0
    for lap in activity.get("laps", []):
        if lap.get("type") != "work":
            continue
        p = lap.get("avg_power") or 0
        if lo <= p <= hi:
            seconds_in_zone += lap.get("duration_s") or 0

    hit = seconds_in_zone >= min_in_zone
    ratio = seconds_in_zone / min_in_zone if min_in_zone else 1.0

    if hit:
        verdict = "命中"
    elif ratio >= 0.5:
        verdict = "部分命中"
    else:
        verdict = "刺激错配"

    misses_prev = sum(1 for m in (recent_misses or []) if m.get("type") == target and m.get("missed"))
    under_flag = (not hit) and misses_prev >= 2

    return Findings(
        analyzer="target_align",
        metrics={
            "target_type": target,
            "target_range_w": [int(round(lo)), int(round(hi))],
            "seconds_in_zone": seconds_in_zone,
            "min_required_seconds": min_in_zone,
            "ratio_to_required": round(ratio, 2),
            "under_prescription_flag": under_flag,
        },
        verdict=verdict,
        evidence=[
            (f"目标类型 {target}；需求最少 {min_in_zone//60} 分钟在 {int(lo)}–{int(hi)} W", "ZONES table"),
            (f"实际累计 {seconds_in_zone//60} 分钟在区间内 (达成率 {ratio:.0%})", "laps[].avg_power 聚合"),
        ],
    )
