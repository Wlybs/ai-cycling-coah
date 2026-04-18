from ..types import Findings


def _similar(current, candidate, tol=0.20):
    if candidate.get("type") != current.get("type"):
        return False
    d1 = current.get("duration_s", 0)
    d2 = candidate.get("duration_s", 0)
    if d1 == 0:
        return False
    return abs(d1 - d2) / d1 <= tol


def analyze(current: dict, history: list) -> Findings:
    comps = [h for h in (history or []) if _similar(current, h)]
    n = len(comps)
    if n == 0:
        return Findings(analyzer="historical_cmp", metrics={"reason": "no comparables"}, verdict="数据不足", evidence=[])

    conf = "low" if n < 3 else "moderate"
    if n >= 5:
        conf = "high"

    avg_np = sum(c.get("np_watts") or 0 for c in comps) / n
    avg_dec = sum(c.get("decoupling_pct") or 0 for c in comps) / n
    cur_np = current.get("np_watts") or 0
    cur_dec = current.get("decoupling_pct") or 0
    np_delta_pct = (cur_np - avg_np) / avg_np * 100 if avg_np else 0

    if np_delta_pct >= 3 and cur_dec <= avg_dec:
        verdict = "进步"
    elif np_delta_pct <= -3 or cur_dec > avg_dec + 2:
        verdict = "退步"
    else:
        verdict = "持平"

    return Findings(
        analyzer="historical_cmp",
        metrics={
            "comparables_n": n,
            "avg_np_w": int(round(avg_np)),
            "cur_np_w": cur_np,
            "np_delta_pct": round(np_delta_pct, 1),
            "avg_decoupling_pct": round(avg_dec, 2),
            "cur_decoupling_pct": cur_dec,
            "confidence": conf,
        },
        verdict=verdict,
        evidence=[
            (f"与近 90 天 {n} 次相似 {current.get('type')} 对比，NP 变化 {np_delta_pct:+.1f}%", "history filtered by type+duration±20%"),
            (f"解耦 {cur_dec:.1f}% vs 历史均值 {avg_dec:.1f}%", "current.decoupling_pct"),
        ],
    )
