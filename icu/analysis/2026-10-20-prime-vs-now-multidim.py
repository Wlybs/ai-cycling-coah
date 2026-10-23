"""Multi-dimensional prime vs now comparison from 1 Hz streams. No FTP values used."""
import json, os, statistics as st, math, glob

S = os.path.dirname(os.path.abspath(__file__))
# git-ignored raw ICU streams (GET 2026-10-20), kept permanently
RAW = r"D:/Cycling/icu/icu_data_warehouse/9_Coach_Raw/2026-10-20-prime-vs-now-multidim"
WELL_CTX = r"D:/Cycling/icu/analysis/2026-10-16-training-history-context.json"
WELL_LIVE = r"D:/Cycling/icu/icu_data_warehouse/2_Wellness/wellness_history.json"
PEAK = ("2026-04-01", "2026-06-09")
NOW = ("2026-09-01", "2026-10-20")
BANDS = [(160, 180), (180, 200), (200, 220), (220, 240), (240, 260), (260, 280), (280, 300), (300, 320)]


def period(d):
    if PEAK[0] <= d <= PEAK[1]:
        return "peak"
    if NOW[0] <= d <= NOW[1]:
        return "now"
    return None


def streams(aid):
    p = os.path.join(RAW, f"{aid}_streams.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return {x["type"]: x.get("data") for x in d} if isinstance(d, list) else {}


def contiguous(time):
    """index runs where consecutive time diff == 1"""
    runs, start = [], 0
    for i in range(1, len(time)):
        if time[i] - time[i - 1] != 1:
            runs.append((start, i)); start = i
    runs.append((start, len(time)))
    return runs


def rolling(vals, w):
    out, s, q = [None] * len(vals), 0.0, []
    for i, v in enumerate(vals):
        v = v or 0
        q.append(v); s += v
        if len(q) > w:
            s -= q.pop(0)
        if len(q) == w:
            out[i] = s / w
    return out


def best_window(watts, time, w, start_idx=0):
    best = None
    for a, b in contiguous(time):
        a = max(a, start_idx)
        if b - a < w:
            continue
        s = sum((x or 0) for x in watts[a:a + w])
        m = s
        for i in range(a + w, b):
            s += (watts[i] or 0) - (watts[i - w] or 0)
            m = max(m, s)
        best = max(best or 0, m / w)
    return best


def analyse(a):
    st_ = streams(a["id"])
    t, w = st_.get("time") or [], st_.get("watts") or []
    hr, cad, alt, temp = st_.get("heartrate"), st_.get("cadence"), st_.get("altitude"), st_.get("temp")
    name = (a.get("name") or "")
    indoor = a.get("type") == "VirtualRide" or "zwift" in name.lower() or "室内" in name or a.get("trainer") is True
    rec = {"id": a["id"], "date": a["start_date_local"][:10], "name": name[:30], "indoor": bool(indoor)}
    if not t or not w or not any(w):
        rec["missing"] = "no power"; return rec
    n = len(t)
    pedal = [i for i in range(n) if (w[i] or 0) > 0]
    rec["secs"] = n
    rec["kj"] = round(sum((x or 0) for x in w) / 1000, 1)
    rec["band_s"] = {k: sum(1 for x in w if (x or 0) >= k) for k in (280, 300, 320, 340)}
    rec["z_s"] = {"lt200": sum(1 for x in w if 0 < (x or 0) < 200), "200_280": sum(1 for x in w if 200 <= (x or 0) < 280)}
    if alt and any(alt):
        sm = rolling(alt, 10); g = 0
        for i in range(1, n):
            if sm[i] is not None and sm[i - 1] is not None and sm[i] > sm[i - 1]:
                g += sm[i] - sm[i - 1]
        rec["elev_m"] = round(g)
    if temp and any(x is not None for x in temp):
        tv = [x for x in temp if x is not None]
        rec["temp_med"] = round(st.median(tv), 1)
    if cad and any(cad):
        c1 = [cad[i] for i in pedal if (cad[i] or 0) > 0 and (w[i] or 0) > 100]
        rec["cad_med"] = round(st.median(c1)) if c1 else None
        p60 = rolling(w, 60)
        c2 = [cad[i] for i in range(n) if p60[i] and p60[i] >= 280 and (cad[i] or 0) > 0]
        rec["cad_med_ge280"] = round(st.median(c2)) if len(c2) >= 120 else None
    rec["best300"] = best_window(w, t, 300)
    rec["best1200"] = best_window(w, t, 1200)
    # durability: best 5 min after 2000 kJ / after 3000 kJ cumulative
    cum, i2000, i3000 = 0, None, None
    for i, x in enumerate(w):
        cum += (x or 0)
        if i2000 is None and cum >= 2_000_000:
            i2000 = i
        if i3000 is None and cum >= 3_000_000:
            i3000 = i; break
    rec["best300_after2000kj"] = best_window(w, t, 300, i2000) if i2000 is not None else None
    rec["best300_after3000kj"] = best_window(w, t, 300, i3000) if i3000 is not None else None
    if hr and sum(1 for x in hr if x) > 0.8 * n:
        p60, h60 = rolling(w, 60), rolling(hr, 60)
        bands = {}
        for i in range(600, n, 10):
            if p60[i] is None or not h60[i] or h60[i] < 80:
                continue
            for lo, hi in BANDS:
                if lo <= p60[i] < hi:
                    bands.setdefault(f"{lo}-{hi}", []).append(h60[i])
        rec["hr_band"] = {k: (round(st.median(v), 1), len(v)) for k, v in bands.items() if len(v) >= 12}
        h60max = max(x for x in h60 if x is not None)
        rec["hr60_max"] = round(h60max)
        # EF + decoupling on pedaling samples after first 10 min
        idx = [i for i in range(600, n) if (w[i] or 0) > 0 and hr[i]]
        if len(idx) >= 3600:
            p30 = rolling(w, 30)
            npw = (st.mean([(p30[i] or 0) ** 4 for i in idx])) ** 0.25
            rec["np_pedal"] = round(npw)
            rec["avg_p_pedal"] = round(st.mean(w[i] for i in idx))
            rec["avg_hr_pedal"] = round(st.mean(hr[i] for i in idx), 1)
            rec["ef"] = round(npw / rec["avg_hr_pedal"], 3)
            h = len(idx) // 2
            e1 = st.mean(w[i] for i in idx[:h]) / st.mean(hr[i] for i in idx[:h])
            e2 = st.mean(w[i] for i in idx[h:]) / st.mean(hr[i] for i in idx[h:])
            rec["decouple_pct"] = round((e1 - e2) / e1 * 100, 1)
            rec["vi"] = round(npw / max(rec["avg_p_pedal"], 1), 3)
    else:
        rec["hr_missing"] = True
    return rec


def wellness():
    w = {r["id"]: r for r in json.load(open(WELL_CTX, encoding="utf-8"))["wellness_selected"]}
    for r in json.load(open(WELL_LIVE, encoding="utf-8")):
        w[r["id"]] = {**w.get(r["id"], {}), **r}
    return w


def main():
    acts = json.load(open(os.path.join(RAW, "activities.json"), encoding="utf-8"))
    recs = [analyse(a) for a in acts if period(a["start_date_local"][:10])]
    for r in recs:
        r["period"] = period(r["date"])
    json.dump(recs, open(os.path.join(S, "2026-10-20-prime-vs-now-multidim-records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    well = wellness()
    out = {}
    for P, (lo, hi) in (("peak", PEAK), ("now", NOW)):
        rs = [r for r in recs if r["period"] == P and "missing" not in r]
        days = sum(1 for k in well if lo <= k <= hi) or 1
        wk = days / 7
        o = {"days": days, "rides": len(rs), "indoor_rides": sum(r["indoor"] for r in rs),
             "missing_power": sum(1 for r in recs if r["period"] == P and "missing" in r),
             "hr_missing": sum(1 for r in rs if r.get("hr_missing"))}
        o["hours_wk"] = round(sum(r["secs"] for r in rs) / 3600 / wk, 1)
        o["kj_wk"] = round(sum(r["kj"] for r in rs) / wk)
        o["rides_ge3h_wk"] = round(sum(1 for r in rs if r["secs"] >= 3 * 3600) / wk, 2)
        o["elev_m_wk"] = round(sum(r.get("elev_m", 0) for r in rs if not r["indoor"]) / wk)
        o["share_lt200_200_280_ge280"] = [round(sum(r["z_s"]["lt200"] for r in rs) / sum(r["secs"] for r in rs) * 100, 1),
                                          round(sum(r["z_s"]["200_280"] for r in rs) / sum(r["secs"] for r in rs) * 100, 1),
                                          round(sum(r["band_s"][280] for r in rs) / sum(r["secs"] for r in rs) * 100, 1)]
        out_rs = [r for r in rs if not r["indoor"]]
        o["temp_med_outdoor"] = round(st.median([r["temp_med"] for r in out_rs if r.get("temp_med") is not None]), 1) if any(r.get("temp_med") for r in out_rs) else None
        for env, sub in (("outdoor", out_rs), ("indoor", [r for r in rs if r["indoor"]])):
            hb = {}
            for r in sub:
                for k, (m, cnt) in (r.get("hr_band") or {}).items():
                    hb.setdefault(k, []).append(m)
            o[f"hr_at_power_{env}"] = {k: [round(st.median(v), 1), len(v)] for k, v in sorted(hb.items())}
        steady = [r for r in out_rs if r.get("ef") and r["secs"] >= 2 * 3600 and r.get("vi", 9) <= 1.25]
        o["ef_outdoor_2h_med"] = [round(st.median([r["ef"] for r in steady]), 3), len(steady)] if steady else None
        o["decouple_outdoor_2h_med"] = [round(st.median([r["decouple_pct"] for r in steady]), 1), len(steady)] if steady else None
        o["cad_med"] = round(st.median([r["cad_med"] for r in rs if r.get("cad_med")]))
        c2 = [r["cad_med_ge280"] for r in rs if r.get("cad_med_ge280")]
        o["cad_med_ge280"] = [round(st.median(c2)), len(c2)] if c2 else None
        o["hr60_max_top3"] = sorted([r["hr60_max"] for r in rs if r.get("hr60_max")], reverse=True)[:3]
        o["best300_top"] = round(max(r["best300"] or 0 for r in rs))
        o["best1200_top"] = round(max(r["best1200"] or 0 for r in rs))
        d2 = [(r["best300_after2000kj"], r["date"]) for r in rs if r.get("best300_after2000kj")]
        d3 = [(r["best300_after3000kj"], r["date"]) for r in rs if r.get("best300_after3000kj")]
        o["rides_over2000kj"] = len(d2)
        o["best300_after2000kj_top3"] = [(round(x), d) for x, d in sorted(d2, reverse=True)[:3]]
        o["rides_over3000kj"] = len(d3)
        o["best300_after3000kj_top3"] = [(round(x), d) for x, d in sorted(d3, reverse=True)[:3]]
        ws = [well[k] for k in sorted(well) if lo <= k <= hi]
        f = lambda key: round(st.mean([x[key] for x in ws if x.get(key)]), 1)
        o["hrv_mean"], o["rhr_mean"] = f("hrv"), f("restingHR")
        o["sleep_h_mean"] = round(st.mean([x["sleepSecs"] / 3600 for x in ws if x.get("sleepSecs")]), 2)
        out[P] = o
    json.dump(out, open(os.path.join(S, "2026-10-20-prime-vs-now-multidim-summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
