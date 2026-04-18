from ..types import Findings

CLIMB_GRADE_PCT = 3.0
MIN_CLIMB_S = 180


def _segment_climbs(gradient, power, altitude):
    climbs = []
    start = None
    for i, g in enumerate(gradient):
        if g is not None and g >= CLIMB_GRADE_PCT:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= MIN_CLIMB_S:
                climbs.append((start, i))
            start = None
    if start is not None and len(gradient) - start >= MIN_CLIMB_S:
        climbs.append((start, len(gradient)))
    return climbs


def analyze(activity: dict, streams: dict, physiology: dict | None) -> Findings:
    if not streams or "gradient" not in streams:
        return Findings(analyzer="climbing", metrics={"reason": "no gradient stream"}, verdict="数据不足", evidence=[])

    gradient = streams["gradient"]
    power = streams.get("power") or []
    cadence = streams.get("cadence") or []
    hr = streams.get("hr") or []
    altitude = streams.get("altitude") or []
    weight = float(activity.get("weight_kg") or 62)
    cp = (physiology or {}).get("cp_watts", 280)

    climb_rows = []
    standing_seconds = 0
    for start, end in _segment_climbs(gradient, power, altitude):
        dur = end - start
        seg_power = [p for p in power[start:end] if p is not None]
        seg_cadence = [c for c in cadence[start:end] if c is not None]
        seg_hr = [h for h in hr[start:end] if h is not None]
        avg_power = sum(seg_power) / len(seg_power) if seg_power else 0.0
        avg_hr = sum(seg_hr) / len(seg_hr) if seg_hr else 0.0
        avg_wkg = round(avg_power / weight, 2)
        d_alt = (altitude[end - 1] - altitude[start]) if len(altitude) >= end else 0
        vam = (d_alt / dur) * 3600 if dur > 0 else 0
        standing = sum(
            1 for p, c in zip(seg_power, seg_cadence)
            if p is not None and c is not None and c < 75 and p > cp * 1.1
        )
        standing_seconds += standing
        climb_rows.append({
            "duration_s": dur,
            "avg_power_w": round(avg_power, 1),
            "avg_hr_bpm": round(avg_hr, 1),
            "avg_wkg": avg_wkg,
            "vam_mh": int(round(vam)),
            "standing_seconds": standing,
        })

    if not climb_rows:
        return Findings(analyzer="climbing", metrics={"reason": "no sustained climb"}, verdict="数据不足", evidence=[])

    first_wkg = climb_rows[0]["avg_wkg"]
    last_wkg = climb_rows[-1]["avg_wkg"]
    if last_wkg >= first_wkg * 0.98:
        verdict = "爬坡表现超预期" if len(climb_rows) > 1 and last_wkg > first_wkg else "持平"
    elif last_wkg >= first_wkg * 0.92:
        verdict = "持平"
    else:
        verdict = "疲劳衰退显著"

    return Findings(
        analyzer="climbing",
        metrics={
            "climbs": climb_rows,
            "standing_minutes": round(standing_seconds / 60, 1),
            "first_climb_wkg": first_wkg,
            "last_climb_wkg": last_wkg,
        },
        verdict=verdict,
        evidence=[
            (f"{len(climb_rows)} 段持续爬坡，首段 {first_wkg} W/kg，末段 {last_wkg} W/kg", "climbs[]"),
            (f"摇车累计 {round(standing_seconds / 60, 1)} 分钟", "cadence<75 & power>1.1·CP"),
        ],
    )
