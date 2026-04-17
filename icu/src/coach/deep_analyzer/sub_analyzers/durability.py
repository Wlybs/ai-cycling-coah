from ..types import Findings

CHECKPOINTS = ["1500kj", "2000kj", "2500kj"]


def analyze(ride: dict, personal_curve: dict | None) -> Findings:
    if ride.get("total_kj", 0) < 1500:
        return Findings(
            analyzer="durability",
            metrics={"reason": "ride shorter than 1500 kJ"},
            verdict="数据不足",
            evidence=[],
        )
    if not personal_curve or not personal_curve.get("fresh_mmp_w"):
        return Findings(
            analyzer="durability",
            metrics={"reason": "no personal curve"},
            verdict="数据不足",
            evidence=[],
        )

    ride_fat = ride.get("fatigued_mmp_w") or {}
    best_delta_pct = None
    best_checkpoint = None
    for cp in CHECKPOINTS:
        if cp not in ride_fat:
            continue
        for dur in ("300s",):
            ride_w = ride_fat[cp].get(dur)
            base_w = personal_curve["fatigued_mmp_w"].get(cp, {}).get(dur)
            if ride_w and base_w:
                delta_pct = (ride_w - base_w) / base_w * 100
                if best_delta_pct is None or abs(delta_pct) > abs(best_delta_pct):
                    best_delta_pct = delta_pct
                    best_checkpoint = cp

    if best_delta_pct is None:
        return Findings(
            analyzer="durability",
            metrics={"reason": "no overlapping checkpoints"},
            verdict="数据不足",
            evidence=[],
        )

    if best_delta_pct >= 3:
        verdict = "爬坡表现超预期"
    elif best_delta_pct <= -5:
        verdict = "疲劳衰退显著"
    else:
        verdict = "持平"

    metrics = {
        "best_checkpoint": best_checkpoint,
        "durability_bonus_pct_300s": round(best_delta_pct, 1) if best_delta_pct > 0 else 0.0,
        "durability_deficit_pct_300s": round(-best_delta_pct, 1) if best_delta_pct < 0 else 0.0,
    }
    return Findings(
        analyzer="durability",
        metrics=metrics,
        verdict=verdict,
        evidence=[
            (
                f"在 {best_checkpoint} 检查点，5min MMP 相对个人基线 {best_delta_pct:+.1f}%",
                f"ride.fatigued_mmp_w[{best_checkpoint}]",
            ),
        ],
    )
