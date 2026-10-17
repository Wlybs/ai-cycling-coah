"""Absolute power-band time and sustained-effort count, peak (2026 spring) vs now.

No FTP value is used anywhere (no ftp_set, no ICU eFTP / icu_rolling_ftp).
Inputs (read-only):
  - icu/analysis/2026-10-16-training-history-context.json  (activity list)
  - icu_data_warehouse/5_Activities_Detail/*.json           (local 1 Hz streams + FIT laps)
  - --cache DIR: streams / FIT laps fetched by ICU API GET for activities without local streams
Outputs: 2026-10-18-absolute-power-bands.{json,md} next to this script.

Usage:
  python 2026-10-18-absolute-power-bands.py --icu D:/Cycling/icu --cache <dir>
"""
import argparse
import bisect
import datetime as dt
import glob
import json
import os
import statistics

BANDS = [280, 300, 320, 340]
SUSTAIN_W = 280
SUSTAIN_MIN_S = 480
LONGJING_KEYS = ["🐲", "龙一", "龙半", "半打", "龙井"]
# Work-lap rule for counting reps (my rule, not the athlete's label): 4-10 min and stream mean >= 280 W
WORK_LAP_MIN_S, WORK_LAP_MAX_S, WORK_LAP_W = 240, 600, 280

PERIODS = {
    "peak_2026-04-01_06-09": ("2026-04-01", "2026-06-09"),
    "now_2026-09-01_10-17": ("2026-09-01", "2026-10-17"),
}
MONTHS = [f"2026-{m:02d}" for m in range(1, 7)]
SCOPES = [("2026-01-01", "2026-06-30"), ("2026-09-01", "2026-10-17")]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_STEM = os.path.join(HERE, "2026-10-18-absolute-power-bands")


# ── loading ────────────────────────────────────────────────────────────────

def in_scope(day):
    return any(a <= day <= b for a, b in SCOPES)


def load_activities(icu, cache):
    ctx = json.load(open(os.path.join(icu, "analysis/2026-10-16-training-history-context.json"), encoding="utf-8"))
    acts = {a["id"]: a for a in ctx["activities"]}
    extra = os.path.join(cache, "activities_2026-10-16_17.json")
    if os.path.exists(extra):
        for a in json.load(open(extra, encoding="utf-8")):
            acts.setdefault(a["id"], a)
    rides = [a for a in acts.values() if "Ride" in (a.get("type") or "") and in_scope(a["start_date_local"][:10])]
    return sorted(rides, key=lambda a: a["start_date_local"])


def load_local_details(icu):
    out = {}
    for f in glob.glob(os.path.join(icu, "icu_data_warehouse/5_Activities_Detail/*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if "streams" in d:
            out[d["summary"].get("id")] = (os.path.basename(f), d)
    return out


def streams_to_dict(s):
    if isinstance(s, list):
        return {x["type"]: x.get("data") for x in s}
    return s or {}


def get_streams_and_laps(aid, local, cache):
    """Return (time, watts, laps, source) — any may be None when absent."""
    laps, st, src = None, {}, "icu_api_get"
    if aid in local:
        fname, d = local[aid]
        st = streams_to_dict(d["streams"])
        laps = d.get("laps") or None
        src = f"local:{fname}"
    if not st.get("watts"):  # absent locally, or the local file holds empty streams
        p = os.path.join(cache, f"{aid}_streams.json")
        if not os.path.exists(p):
            return None, None, None, src + " (no stream file)"
        st = streams_to_dict(json.load(open(p, encoding="utf-8")))
        src = "icu_api_get" if aid not in local else src + " empty -> icu_api_get"
    lp = os.path.join(cache, f"{aid}_laps.json")
    if not laps and os.path.exists(lp):
        laps = json.load(open(lp, encoding="utf-8")) or None
    return st.get("time"), st.get("watts"), laps, src


# ── per-activity metrics ───────────────────────────────────────────────────

def contiguous_runs(time, watts):
    """Split into runs of consecutive 1 Hz samples (dt == 1) with non-null watts. Zero watts stay in."""
    runs, cur = [], []
    for i, w in enumerate(watts):
        if w is None:
            if cur:
                runs.append(cur)
            cur = []
            continue
        if cur and time[i] - time[cur[-1]] != 1:
            runs.append(cur)
            cur = []
        cur.append(i)
    if cur:
        runs.append(cur)
    return runs


def sustained_segments(time, watts, runs):
    """Greedy, non-overlapping: start at a sample >= 280 W, extend to the furthest end
    keeping mean >= 280 W, trim trailing samples < 280 W, keep if >= 480 s."""
    segs = []
    for run in runs:
        w = [watts[i] for i in run]
        n = len(w)
        if n < SUSTAIN_MIN_S:
            continue
        q = [0.0] * (n + 1)  # q[k] = sum(w[:k]) - 280*k ; mean(w[i:j]) >= 280  <=>  q[j] >= q[i]
        for k in range(n):
            q[k + 1] = q[k] + w[k] - SUSTAIN_W
        neg_suffix_max = [0.0] * (n + 1)  # non-decreasing after negation, for bisect
        m = float("-inf")
        for k in range(n, -1, -1):
            m = max(m, q[k])
            neg_suffix_max[k] = -m
        i = 0
        while i <= n - SUSTAIN_MIN_S:
            if w[i] < SUSTAIN_W:
                i += 1
                continue
            j = bisect.bisect_right(neg_suffix_max, -q[i]) - 1  # largest j with suffix_max[j] >= q[i]
            while j > i and w[j - 1] < SUSTAIN_W:
                j -= 1
            if j - i >= SUSTAIN_MIN_S:
                seg = w[i:j]
                segs.append({
                    "start_s": time[run[i]],
                    "duration_s": j - i,
                    "mean_w": round(sum(seg) / len(seg), 1),
                })
                i = j
            else:
                i += 1
    return segs


def recompute_laps(laps, time, watts, start_utc):
    t0 = dt.datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    out = []
    for lap in laps:
        ts = lap.get("timestamp_iso")
        dur = lap.get("duration_sec")
        row = {"lap": lap.get("lap_number"), "fit_duration_s": round(dur, 1) if dur is not None else None,
               "fit_avg_w": lap.get("avg_watts")}
        if not ts or dur is None:
            row["error"] = "lap lacks start time or duration"
            out.append(row)
            continue
        off = (dt.datetime.fromisoformat(ts) - t0).total_seconds()
        lo = bisect.bisect_left(time, off)
        hi = bisect.bisect_left(time, off + dur)
        vals = [watts[k] for k in range(lo, hi) if watts[k] is not None]
        row.update({
            "start_offset_s": round(off),
            "stream_samples": hi - lo,
            "null_watts": (hi - lo) - len(vals),
            "stream_mean_w": round(sum(vals) / len(vals), 1) if vals else None,
        })
        out.append(row)
    return out


def analyse_activity(a, local, cache):
    aid = a["id"]
    day = a["start_date_local"][:10]
    iso = dt.date.fromisoformat(day).isocalendar()
    rec = {
        "id": aid, "date": day, "iso_week": f"{iso[0]}-W{iso[1]:02d}", "type": a.get("type"),
        "name": a.get("name"), "device_watts": a.get("device_watts"),
        "icu_training_load": a.get("icu_training_load"),
        "longjing_candidate": any(k in (a.get("name") or "") for k in LONGJING_KEYS),
    }
    time, watts, laps, src = get_streams_and_laps(aid, local, cache)
    rec["source"] = src
    if not time or not watts or all(w is None for w in watts):
        rec["missing"] = "no power stream" if time else "no stream"
        if rec["longjing_candidate"]:
            rec["laps_raw_count"] = len(laps) if laps else 0
        return rec
    if len(time) != len(watts):
        raise ValueError(f"{aid}: time/watts length mismatch {len(time)} vs {len(watts)}")
    nonnull = [w for w in watts if w is not None]
    diffs = [time[i + 1] - time[i] for i in range(len(time) - 1)]
    rec.update({
        "samples": len(watts),
        "null_watts": len(watts) - len(nonnull),
        "time_gaps_dt_gt_1": sum(1 for d in diffs if d > 1),
        "dropout_s_in_gaps_le_5s": sum(d - 1 for d in diffs if 1 < d <= 5),
        "median_dt_s": statistics.median(diffs) if diffs else None,
        "sec_ge": {str(b): sum(1 for w in nonnull if w >= b) for b in BANDS},
    })
    runs = contiguous_runs(time, watts)
    rec["sustained_ge280_8min"] = sustained_segments(time, watts, runs)
    if rec["longjing_candidate"]:
        rec["laps_raw_count"] = len(laps) if laps else 0
        if laps:
            rec["laps"] = recompute_laps(laps, time, watts, a["start_date"])
    return rec


# ── aggregation (only from per-activity records) ───────────────────────────

def agg(records, lo, hi):
    sel = [r for r in records if lo <= r["date"] <= hi]
    ok = [r for r in sel if "missing" not in r]
    days = (dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days + 1
    out = {"from": lo, "to": hi, "days": days, "rides": len(sel), "rides_with_power": len(ok),
           "rides_missing_power": [r["id"] for r in sel if "missing" in r]}
    for b in BANDS:
        out[f"min_ge_{b}"] = round(sum(r["sec_ge"][str(b)] for r in ok) / 60, 1)
    segs = [s for r in ok for s in r["sustained_ge280_8min"]]
    out["sustained_count"] = len(segs)
    out["sustained_min"] = round(sum(s["duration_s"] for s in segs) / 60, 1)
    out["time_gaps_dt_gt_1"] = sum(r["time_gaps_dt_gt_1"] for r in ok)
    out["dropout_s_in_gaps_le_5s"] = sum(r["dropout_s_in_gaps_le_5s"] for r in ok)
    out["samples"] = sum(r["samples"] for r in ok)
    for k in [f"min_ge_{b}" for b in BANDS] + ["sustained_count", "sustained_min"]:
        out[k + "_per7d"] = round(out[k] * 7 / days, 1)
    return out


def weekly(records, lo, hi):
    d0, d1 = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
    mon = d0 - dt.timedelta(days=d0.weekday())
    rows = []
    while mon <= d1:
        a, b = max(mon, d0), min(mon + dt.timedelta(days=6), d1)
        r = agg(records, a.isoformat(), b.isoformat())
        iso = mon.isocalendar()
        r["iso_week"] = f"{iso[0]}-W{iso[1]:02d}"
        rows.append(r)
        mon += dt.timedelta(days=7)
    return rows


def build_aggregates(records):
    out = {"periods": {}, "weekly": {}, "monthly": {}}
    for key, (lo, hi) in PERIODS.items():
        out["periods"][key] = agg(records, lo, hi)
        out["weekly"][key] = weekly(records, lo, hi)
    for m in MONTHS:
        y, mm = map(int, m.split("-"))
        last = (dt.date(y + (mm == 12), mm % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()
        out["monthly"][m] = agg(records, f"{m}-01", last)
    return out


# ── markdown ───────────────────────────────────────────────────────────────

def band_row(label, r, per7=False):
    sfx = "_per7d" if per7 else ""
    cells = [f"{r[f'min_ge_{b}{sfx}']}" for b in BANDS]
    return (f"| {label} | {r['days']} | {r['rides']} | {len(r['rides_missing_power'])} | " + " | ".join(cells)
            + f" | {r['sustained_count' + sfx]} | {r['sustained_min' + sfx]} |")


HDR = ("| {} | 天数 | 骑行 | 缺功率 | ≥280W 分 | ≥300W 分 | ≥320W 分 | ≥340W 分 | ≥8min@≥280W 段数 | 段总分钟 |\n"
       "|---|---|---|---|---|---|---|---|---|---|")


def fmt_mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def render_md(data):
    A = data["aggregates"]
    recs = data["activities"]
    P = A["periods"]
    pk, nw = P["peak_2026-04-01_06-09"], P["now_2026-09-01_10-17"]
    L = []
    L.append("# 绝对功率带时间：巅峰期 vs 现在（2026-10-18）\n")
    L.append("不用任何 FTP 值。所有数字由本目录同名 `.json` 的 `activities[]` 逐活动明细重算，"
             "聚合口径见 JSON `method`。生成脚本：同名 `.py`。\n")
    L.append("## 1. 两期对照（按 7 天折算）\n")
    L.append("折算 = 期内总量 × 7 / 期内天数。巅峰窗 70 天、现在窗 47 天。\n")
    L.append(HDR.format("时期"))
    L.append(band_row("巅峰 04-01–06-09 每7天", pk, True))
    L.append(band_row("现在 09-01–10-17 每7天", nw, True))
    L.append("")
    L.append("期内总量（未折算）：\n")
    L.append(HDR.format("时期"))
    L.append(band_row("巅峰 04-01–06-09 合计", pk))
    L.append(band_row("现在 09-01–10-17 合计", nw))
    L.append("")
    for key, title in [("peak_2026-04-01_06-09", "巅峰窗逐周（ISO 周，首尾周不完整）"),
                       ("now_2026-09-01_10-17", "现在窗逐周（ISO 周，首尾周不完整）")]:
        L.append(f"### {title}\n")
        L.append(HDR.format("周 (起止)"))
        for r in A["weekly"][key]:
            L.append(band_row(f"{r['iso_week']} ({r['from'][5:]}–{r['to'][5:]})", r))
        L.append("")
    L.append("### 2026-01 至 06 逐月\n")
    L.append(HDR.format("月"))
    for m, r in A["monthly"].items():
        L.append(band_row(m, r))
    L.append("")
    L.append("## 2. 持续段明细（连续 ≥8 分钟且均功率 ≥280W）\n")
    L.append("口径：只在真实连续 1Hz 样本内找（相邻 time 差 = 1 s，watts 非空；零功率照计，缺测处断开）；"
             "起点须 ≥280W，向后取均值仍 ≥280W 的最远终点，再剪掉末尾 <280W 的秒，剩余 ≥480 s 才算；段与段不重叠。\n")
    for key, title in [("peak_2026-04-01_06-09", "巅峰窗"), ("now_2026-09-01_10-17", "现在窗")]:
        lo, hi = PERIODS[key]
        L.append(f"### {title}\n")
        L.append("| 日期 | 活动 id | 名称 | 起点 (骑行内 时:分) | 时长 | 均功率 W |\n|---|---|---|---|---|---|")
        n = 0
        for r in recs:
            if lo <= r["date"] <= hi and "missing" not in r:
                for s in r["sustained_ge280_8min"]:
                    n += 1
                    L.append(f"| {r['date']} | {r['id']} | {(r['name'] or '').splitlines()[0][:24]} | "
                             f"{s['start_s'] // 3600}:{(s['start_s'] % 3600) // 60:02d} | {fmt_mmss(s['duration_s'])} | {s['mean_w']} |")
        if n == 0:
            L.append("| — | — | 无 | — | — | — |")
        L.append("")
    L.append("## 3. 龙井 VO2 课候选（名称含 🐲/龙一/龙半/半打/龙井 且有 laps）\n")
    L.append(f"按本人习惯视为 VO2 训练候选，不按名称里的“阈值/vo2”字面分类。lap 均功率用逐秒流按 FIT lap 起止时间重算。"
             f"“趟数”是我定的计数规则：lap 时长 {WORK_LAP_MIN_S // 60}–{WORK_LAP_MAX_S // 60} 分钟且重算均功率 ≥{WORK_LAP_W}W "
             f"记一趟〔推断规则，非本人标注〕；全部 lap 见 JSON `activities[].laps`。TSS 为 ICU `icu_training_load`（ICU 用其当时 FTP 设置算出，仅作参考）。\n")
    L.append("| 日期 | 活动 id | 名称 | lap 数 | 趟数 | 计入趟的 lap（时长@重算均功率） | TSS |\n|---|---|---|---|---|---|---|")
    for r in recs:
        if not r["longjing_candidate"]:
            continue
        nm = (r["name"] or "").splitlines()[0][:24]
        if "missing" in r:
            L.append(f"| {r['date']} | {r['id']} | {nm} | {r.get('laps_raw_count', 0)} | — | 缺功率流：{r['missing']} | {r['icu_training_load']} |")
            continue
        if not r.get("laps"):
            L.append(f"| {r['date']} | {r['id']} | {nm} | 0 | — | 无 laps，不列为候选 | {r['icu_training_load']} |")
            continue
        work = [x for x in r["laps"] if is_work_lap(x)]
        cells = "; ".join(f"L{x['lap']} {fmt_mmss(x['stream_samples'])}@{x['stream_mean_w']}" for x in work) or "无符合规则的 lap"
        L.append(f"| {r['date']} | {r['id']} | {nm} | {len(r['laps'])} | {len(work)} | {cells} | {r['icu_training_load']} |")
    L.append("")
    L.append("## 4. 缺测清单（逐条，不插补）\n")
    L.append("| 日期 | 活动 id | 类型 | 名称 | 原因 |\n|---|---|---|---|---|")
    miss = [r for r in recs if "missing" in r]
    for r in miss:
        L.append(f"| {r['date']} | {r['id']} | {r['type']} | {(r['name'] or '').splitlines()[0][:24]} | {r['missing']}（{r['source']}；device_watts={r['device_watts']}） |")
    if not miss:
        L.append("| — | — | — | 无 | — |")
    L.append("\n两窗的断档汇总（只计有功率流的骑行）：\n")
    L.append("| 时期 | 样本数 | time 断档(Δt>1s)处数 | 每小时断档处数 | ≤5s 小断档丢失秒数 |\n|---|---|---|---|---|")
    for lab, r in [("巅峰 04-01–06-09", pk), ("现在 09-01–10-17", nw)]:
        L.append(f"| {lab} | {r['samples']} | {r['time_gaps_dt_gt_1']} | {gaps_per_hour(r)} | {r['dropout_s_in_gaps_le_5s']} |")
    gaps = [r for r in recs if "missing" not in r and (r["null_watts"] or r["time_gaps_dt_gt_1"])]
    L.append("\n有功率流但含空值或时间断档的活动（功率带计时只数实有样本；持续段在断点处断开）：\n")
    L.append("| 日期 | 活动 id | 样本数 | watts 空值数 | time 断档(Δt>1s)处数 | ≤5s 小断档丢失秒数 | 中位 Δt |\n|---|---|---|---|---|---|---|")
    for r in gaps:
        L.append(f"| {r['date']} | {r['id']} | {r['samples']} | {r['null_watts']} | {r['time_gaps_dt_gt_1']} | "
                 f"{r['dropout_s_in_gaps_le_5s']} | {r['median_dt_s']} |")
    L.append("")
    L.append("## 5. 读数注意\n")
    L.append("- 持续段取“均值仍 ≥280W 的最远终点”，所以不少段均功率只有 280.0–280.9W：这些段把强段之后较低的一截也并了进来，"
             "段长偏长、段数偏少。段数/段长对口径敏感，≥X W 分钟数不受这个影响。")
    hp, hn = gaps_per_hour(pk), gaps_per_hour(nw)
    side = "巅峰窗" if hp > hn else "现在窗"
    L.append(f"- 持续段遇到任何断档（含 1–4 s 掉点）都断开，不拼接。每小时断档处数：巅峰窗 {hp}、现在窗 {hn}，"
             f"{side}的持续段被切断的机会更多，这个偏差方向是低估{side}的持续段。")
    L.append("- 骑行含 VirtualRide（Zwift 等骑行台），功率来自骑行台/功率计，与户外同样计入。")
    L.append("")
    return "\n".join(L)


def gaps_per_hour(r):
    return round(r["time_gaps_dt_gt_1"] / (r["samples"] / 3600), 1) if r["samples"] else None


def is_work_lap(x):
    return (x.get("stream_mean_w") is not None and WORK_LAP_MIN_S <= x["stream_samples"] <= WORK_LAP_MAX_S
            and x["stream_mean_w"] >= WORK_LAP_W)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--icu", default="D:/Cycling/icu")
    ap.add_argument("--cache", required=True)
    args = ap.parse_args()
    local = load_local_details(args.icu)
    records = [analyse_activity(a, local, args.cache) for a in load_activities(args.icu, args.cache)]
    data = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "method": {
            "ftp_used": False,
            "bands_w": BANDS,
            "band_time": "count of 1 Hz samples with non-null watts >= band; minutes = count/60",
            "sustained": (f"within contiguous runs (time step == 1 s, watts non-null, zeros kept): greedy non-overlapping; "
                          f"start sample >= {SUSTAIN_W} W; furthest end with mean >= {SUSTAIN_W} W; trailing samples < {SUSTAIN_W} W trimmed; "
                          f"keep if duration >= {SUSTAIN_MIN_S} s"),
            "per7d": "period total * 7 / days in period",
            "weeks": "ISO weeks (Mon-Sun), clipped to the period window",
            "lap_recompute": "lap window = [FIT lap start_time - activity start_date, + FIT total_elapsed_time), stream mean over non-null watts",
            "work_lap_rule": f"{WORK_LAP_MIN_S}-{WORK_LAP_MAX_S} s and stream mean >= {WORK_LAP_W} W (analyst rule)",
            "scope": SCOPES,
            "ride_types": "type contains 'Ride'",
        },
        "activities": records,
    }
    data["aggregates"] = build_aggregates(records)
    json.dump(data, open(OUT_STEM + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(OUT_STEM + ".md", "w", encoding="utf-8").write(render_md(data))
    print("activities", len(records), "missing", sum(1 for r in records if "missing" in r))


if __name__ == "__main__":
    main()
