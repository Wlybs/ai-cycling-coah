"""两张必要图：原始 P/HR 时间曲线（4 条代表 ride）+ 早段匹配窗口散点与同带漂移。

    python plots.py   # 读 analyze.py 写出的 JSON 与原始 streams
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from io_streams import load_activity_list, load_ride  # noqa: E402
from segments import STILL_GAP, STILL_REC, timeline  # noqa: E402
from windows import _rolling_mean  # noqa: E402

ANALYSIS = Path(__file__).resolve().parents[1]
JSON_PATH = ANALYSIS / "2026-10-20-lsd-indoor-outdoor-hr-review.json"
COLORS = {"indoor": "#2a78d6", "outdoor_island_lsd": "#eb6834", "outdoor_continuous_loop": "#1baf7a"}
MARKERS = {"indoor": "o", "outdoor_island_lsd": "s", "outdoor_continuous_loop": "^"}
LABELS = {"indoor": "室内 Zwift", "outdoor_island_lsd": "户外跨岛LSD", "outdoor_continuous_loop": "户外绕圈(LCK/西北)"}
INK, MUTED, GRID = "#2b2b2b", "#6b6b6b", "#e4e3df"
TIME_RIDES = ["i184773300", "i194515784", "i192260588", "i198249990"]

plt.rcParams.update({"font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "font.size": 9})


def gkey(group: str) -> str:
    return "indoor" if group.startswith("indoor") else group


def time_curves(R: dict) -> Path:
    acts = {a["id"]: a for a in load_activity_list()}
    rides = {r["id"]: r for r in R["rides"]}
    fig, axes = plt.subplots(len(TIME_RIDES) * 2, 1, figsize=(11, 14), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1] * len(TIME_RIDES), "hspace": 0.38})
    for k, aid in enumerate(TIME_RIDES):
        r = load_ride(acts[aid])
        tl = timeline(r)
        n = len(tl)
        p = np.full(n, np.nan)
        p[r.t] = r.p
        hr = np.full(n, np.nan)
        hr[r.t] = r.hr
        x = np.arange(n) / 3600
        col = COLORS[gkey(rides[aid]["group"])]
        axp, axh = axes[2 * k], axes[2 * k + 1]
        axp.plot(x, _rolling_mean(p, 60), color=col, lw=1.0)
        axh.plot(x, hr, color=col, lw=1.0)
        still = (tl == STILL_REC) | (tl == STILL_GAP)
        for ax in (axp, axh):
            ax.fill_between(x, 0, 1, where=still, transform=ax.get_xaxis_transform(), color=MUTED, alpha=0.25, lw=0)
            for w in rides[aid]["windows"]["medium"]:
                if w["end_elapsed_s"] <= 3600 and w["start_elapsed_s"] >= 1200:
                    ax.axvspan(w["start_elapsed_s"] / 3600, w["end_elapsed_s"] / 3600, color=col, alpha=0.12, lw=0)
        axp.set_ylim(0, 400)
        axh.set_ylim(90, 180)
        axp.set_ylabel("功率 W\n(60s均)")
        axh.set_ylabel("心率 bpm")
        title = f'{rides[aid]["date"]} {aid} · {LABELS[gkey(rides[aid]["group"])]} · 经过{r.t[-1] / 3600:.2f}h'
        axp.set_title(title, loc="left", fontsize=9, color=INK)
    axes[-1].set_xlabel("经过时间 h（灰底=静止，含自动暂停gap；浅色底=20–60min medium 稳态窗口）")
    fig.suptitle("原始功率/心率时间曲线（gap 不补零、不插值）", x=0.01, y=0.915, ha="left", fontsize=11, color=INK)
    out = ANALYSIS / "2026-10-20-lsd-indoor-outdoor-hr-review-timecurves.png"
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def matched_and_drift(R: dict) -> Path:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
    seen = set()
    for r in R["rides"]:
        g = gkey(r["group"])
        ws = [w for w in r["windows"]["medium"] if w["start_elapsed_s"] >= 1200 and w["end_elapsed_s"] <= 3600]
        if not ws:
            continue
        a1.scatter([w["P"] for w in ws], [w["HR_settled"] for w in ws], s=36, color=COLORS[g], marker=MARKERS[g],
                   edgecolor="white", linewidth=1.0, label=None if g in seen else LABELS[g], zorder=3)
        seen.add(g)
    a1.set_xlabel("窗口均功率 W（5min，medium 档）")
    a1.set_ylabel("窗口心率 bpm（第60s起均值）")
    a1.set_title("早段 20–60min 稳态窗口：同功率下心率", loc="left", fontsize=10, color=INK)
    a1.legend(frameon=False, loc="upper left")
    for aid in ["i184773300", "i194515784", "i192592799", "i197223842", "i192260588", "i198249990"]:
        r = next(x for x in R["rides"] if x["id"] == aid)
        d = R["drift"][aid]["medium"]
        if not d.get("usable"):
            continue
        g = gkey(r["group"])
        band = [w for w in r["windows"]["medium"] if abs(w["P"] - d["ref_P"]) <= 12 and w["start_elapsed_s"] >= 1200
                and w["end_elapsed_s"] <= r["elapsed_s"] - 600]
        xs = [w["start_elapsed_s"] / 3600 for w in band]
        ys = [w["HR_settled"] for w in band]
        a2.plot(xs, ys, color=COLORS[g], marker=MARKERS[g], ms=4, lw=1.2)
        a2.annotate(f'{r["date"][5:]} {d["ref_P"]:.0f}W', (xs[-1], ys[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=8, color=MUTED, va="center")
    a2.set_xlabel("经过时间 h（不含最后10min整理）")
    a2.set_ylabel("参考功率带±12W 内窗口心率 bpm")
    a2.set_title("同 ride 同功率带的心率随时间", loc="left", fontsize=10, color=INK)
    for g in ("indoor", "outdoor_island_lsd"):
        a2.plot([], [], color=COLORS[g], marker=MARKERS[g], label=LABELS[g])
    a2.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    out = ANALYSIS / "2026-10-20-lsd-indoor-outdoor-hr-review-matched.png"
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    R = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    print(time_curves(R))
    print(matched_and_drift(R))


if __name__ == "__main__":
    main()
