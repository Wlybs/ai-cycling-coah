"""Independent check: (1) recount band seconds + segment means from raw streams,
(2) recompute every aggregate from activities[], (3) every aggregate row appears in the md."""
import json, os, glob, datetime as dt
OUT = "D:/Cycling/.claude/worktrees/laughing-euler-a4dbd1/icu/analysis/2026-10-18-absolute-power-bands"
CACHE = "D:/Cycling/icu/icu_data_warehouse/9_Coach_Raw/2026-10-18-absolute-power-bands"
J = json.load(open(OUT + ".json", encoding="utf-8"))
md = open(OUT + ".md", encoding="utf-8").read()

def sd(s):
    return {x["type"]: x["data"] for x in s} if isinstance(s, list) else s

local = {}
for f in glob.glob("D:/Cycling/icu/icu_data_warehouse/5_Activities_Detail/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "streams" in d and sd(d["streams"]).get("watts"):
        local[d["summary"]["id"]] = sd(d["streams"])
errs = 0
for r in J["activities"]:
    if "missing" in r:
        continue
    st = local.get(r["id"]) or sd(json.load(open(os.path.join(CACHE, r["id"] + "_streams.json"), encoding="utf-8")))
    t, w = st["time"], st["watts"]
    for b in (280, 300, 320, 340):
        n = sum(1 for x in w if x is not None and x >= b)
        if n != r["sec_ge"][str(b)]:
            errs += 1; print("band mismatch", r["id"], b, n, r["sec_ge"][str(b)])
    pos = {tt: i for i, tt in enumerate(t)}
    for s in r["sustained_ge280_8min"]:
        i = pos[s["start_s"]]
        seg = w[i:i + s["duration_s"]]
        cont = all(t[i + k + 1] - t[i + k] == 1 for k in range(s["duration_s"] - 1)) and None not in seg
        m = sum(seg) / len(seg)
        if not cont or m < 280 or s["duration_s"] < 480 or abs(round(m, 1) - s["mean_w"]) > 0.05:
            errs += 1; print("segment bad", r["id"], s, cont, m)

def agg(lo, hi):
    sel = [r for r in J["activities"] if lo <= r["date"] <= hi]
    ok = [r for r in sel if "missing" not in r]
    days = (dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days + 1
    o = {"days": days, "rides": len(sel), "miss": len(sel) - len(ok)}
    for b in (280, 300, 320, 340):
        o[b] = round(sum(r["sec_ge"][str(b)] for r in ok) / 60, 1)
    segs = [s for r in ok for s in r["sustained_ge280_8min"]]
    o["n"] = len(segs); o["m"] = round(sum(s["duration_s"] for s in segs) / 60, 1)
    return o

def check(a, ref, label):
    global errs
    pairs = [(a["days"], ref["days"]), (a["rides"], ref["rides"]), (a["miss"], len(ref["rides_missing_power"])),
             (a[280], ref["min_ge_280"]), (a[300], ref["min_ge_300"]), (a[320], ref["min_ge_320"]), (a[340], ref["min_ge_340"]),
             (a["n"], ref["sustained_count"]), (a["m"], ref["sustained_min"])]
    if any(x != y for x, y in pairs):
        errs += 1; print("agg mismatch", label, pairs)
    row = f"| {a['days']} | {a['rides']} | {a['miss']} | {a[280]} | {a[300]} | {a[320]} | {a[340]} | {a['n']} | {a['m']} |"
    if row not in md:
        errs += 1; print("row not in md", label, row)
    p7 = lambda v: round(v * 7 / a["days"], 1)
    row7 = f"| {a['days']} | {a['rides']} | {a['miss']} | {p7(a[280])} | {p7(a[300])} | {p7(a[320])} | {p7(a[340])} | {p7(a['n'])} | {p7(a['m'])} |"
    return row7

A = J["aggregates"]
for key, ref in A["periods"].items():
    row7 = check(agg(ref["from"], ref["to"]), ref, key)
    if row7 not in md:
        errs += 1; print("per7 row not in md", key, row7)
    for wk in A["weekly"][key]:
        check(agg(wk["from"], wk["to"]), wk, wk["iso_week"])
for m, ref in A["monthly"].items():
    check(agg(ref["from"], ref["to"]), ref, m)
print("activities", len(J["activities"]), "errors", errs)
