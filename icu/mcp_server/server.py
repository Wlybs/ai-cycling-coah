"""ICU Cycling MCP Server — exposes Intervals.icu athlete data as MCP tools.

Designed for the cycling-coach skill — every tool returns evidence with
provenance (file path + timestamp) to satisfy the "no hardcoded FTP" hard rule.

All numeric values (FTP, CP, W', PBs, HRV) come from the live data sources:
  - coach_memory/athlete_snapshot.json (refreshed by sync_data.py)
  - icu_data_warehouse/2_Wellness/wellness_history.json
  - icu_data_warehouse/3_PowerData/, 4_Activities_List/, 5_Activities_Detail/, 8_Events/

Run via:
  /mnt/d/Cycling/icu/.venv/bin/python /mnt/d/Cycling/icu/mcp_server/server.py
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

ICU_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICU_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402

WAREHOUSE = ICU_DIR / "icu_data_warehouse"
MEMORY = ICU_DIR / "coach_memory"

mcp = FastMCP("icu-cycling")


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"parse failed: {type(e).__name__}: {e}", "_path": str(path)}


def _file_age_hours(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    return round((datetime.now().timestamp() - path.stat().st_mtime) / 3600, 1)


@mcp.tool()
def icu_athlete_snapshot() -> dict:
    """读取当前运动员画像：FTP、体重、最近 90d 滚动 PBs、CP/W' 估计。

    这是 FTP / CP / W' 等核心数值的 single source of truth。
    永远不要在 reasoning 里 hardcode FTP — 调用这个 tool。

    Returns:
        {ftp_set, weight_kg, updated_at, age_hours_since_sync,
         recent_pbs: {5min, 10min, 20min, 60min}, source}
    """
    p = MEMORY / "athlete_snapshot.json"
    snap = _read_json(p)
    if not snap or snap.get("_error"):
        return {"error": "athlete_snapshot.json not readable", "path": str(p)}

    updated = snap.get("updated_at") or snap.get("snapshot_date")
    age_hours = None
    if updated:
        try:
            dt = datetime.fromisoformat(str(updated).replace("Z", ""))
            age_hours = round((datetime.now() - dt).total_seconds() / 3600, 1)
        except Exception:
            pass

    pbs = snap.get("recent_pbs") or {}
    return {
        "ftp_set": snap.get("ftp_set"),
        "weight_kg": snap.get("weight") or (snap.get("summary") or {}).get("icu_weight"),
        "updated_at": updated,
        "age_hours_since_sync": age_hours,
        "recent_pbs_90d_rolling": {
            d: (pbs.get(d) or {}).get("watts_90d")
            for d in ("5min", "10min", "20min", "60min")
        },
        "pb_warning": "PBs are 90d rolling-window peaks, NOT verified all-out tests. Confirm anchor with user before CP/FTP calculation.",
        "source": str(p),
    }


@mcp.tool()
def icu_wellness_today() -> dict:
    """读取最新一天 wellness（HRV/RHR/sleep）+ 7 天 baseline 对照。

    cycling-coach HRV 闸门评估的输入。

    Returns:
        {date, hrv, rhr, sleep_h, soreness, fatigue, ctl, atl, tsb,
         hrv_baseline_7d, rhr_baseline_7d, hrv_dev_pct, source}
    """
    p = WAREHOUSE / "2_Wellness" / "wellness_history.json"
    arr = _read_json(p)
    if not arr or not isinstance(arr, list):
        return {"error": "wellness_history.json not readable", "path": str(p)}

    last = arr[-1]
    last7 = arr[-7:]

    def _avg(key):
        vals = [e.get(key) for e in last7 if e.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    hrv_baseline = _avg("hrv")
    rhr_baseline = _avg("restingHR")

    today_hrv = last.get("hrv")
    today_rhr = last.get("restingHR")
    ctl = last.get("ctl")
    atl = last.get("atl")

    return {
        "date": last.get("id") or last.get("date"),
        "hrv": today_hrv,
        "rhr": today_rhr,
        "sleep_h": round(last.get("sleepSecs", 0) / 3600, 1) if last.get("sleepSecs") else None,
        "soreness": last.get("soreness"),
        "fatigue": last.get("fatigue"),
        "stress": last.get("stress"),
        "motivation": last.get("motivation"),
        "ctl": round(ctl, 1) if ctl is not None else None,
        "atl": round(atl, 1) if atl is not None else None,
        "tsb": round((ctl or 0) - (atl or 0), 1) if (ctl is not None and atl is not None) else None,
        "hrv_baseline_7d": hrv_baseline,
        "rhr_baseline_7d": rhr_baseline,
        "hrv_dev_pct": (
            round((today_hrv - hrv_baseline) / hrv_baseline * 100, 1)
            if (today_hrv is not None and hrv_baseline)
            else None
        ),
        "source": str(p),
        "age_hours": _file_age_hours(p),
    }


@mcp.tool()
def icu_wellness_history(days: int = 14) -> list:
    """读取最近 N 天 wellness 完整序列。

    Args:
        days: 回溯天数（最大 60）
    """
    days = min(max(days, 1), 60)
    p = WAREHOUSE / "2_Wellness" / "wellness_history.json"
    arr = _read_json(p) or []
    if not isinstance(arr, list):
        return []
    out = []
    for e in arr[-days:]:
        ctl = e.get("ctl")
        atl = e.get("atl")
        out.append({
            "date": e.get("id") or e.get("date"),
            "hrv": e.get("hrv"),
            "rhr": e.get("restingHR"),
            "sleep_h": round(e.get("sleepSecs", 0) / 3600, 1) if e.get("sleepSecs") else None,
            "soreness": e.get("soreness"),
            "fatigue": e.get("fatigue"),
            "ctl": round(ctl, 1) if ctl is not None else None,
            "atl": round(atl, 1) if atl is not None else None,
            "tsb": round((ctl or 0) - (atl or 0), 1) if (ctl is not None and atl is not None) else None,
        })
    return out


@mcp.tool()
def icu_recent_activities(days: int = 14, limit: int = 20) -> list:
    """读取最近 N 天活动列表（不含 streams）。

    Args:
        days: 回溯窗口
        limit: 最多返回条数
    """
    p = WAREHOUSE / "4_Activities_List" / "activity_list_clean.json"
    arr = _read_json(p) or []
    if not isinstance(arr, list):
        return []
    since = (date.today() - timedelta(days=days)).isoformat()
    filtered = [a for a in arr if (a.get("start_date_local") or "")[:10] >= since]
    filtered.sort(key=lambda x: x.get("start_date_local") or "", reverse=True)
    out = []
    for a in filtered[:limit]:
        out.append({
            "id": a.get("id"),
            "date": (a.get("start_date_local") or "")[:10],
            "name": (a.get("name") or "")[:80],
            "type": a.get("type"),
            "duration_min": round((a.get("moving_time") or 0) / 60),
            "distance_km": round((a.get("distance") or 0) / 1000, 1),
            "tss": a.get("icu_training_load"),
            "np_w": a.get("icu_weighted_avg_watts"),
            "if": a.get("icu_intensity"),
            "avg_w": a.get("icu_average_watts"),
            "avg_hr": a.get("average_heartrate"),
            "max_hr": a.get("max_heartrate"),
        })
    return out


@mcp.tool()
def icu_activity_detail(activity_id: str) -> dict:
    """读取单个活动详情：summary + laps + 间歇段统计（不含原始 streams 避免 token 爆）。

    Args:
        activity_id: 活动 ID（例如 "i133847457"）
    """
    base = WAREHOUSE / "5_Activities_Detail" / activity_id
    if not base.exists():
        return {"error": f"activity {activity_id} not synced locally; run sync_data.py"}

    activity = _read_json(base / "activity.json") or {}
    laps = _read_json(base / "laps.json") or []
    icu_intervals_doc = _read_json(base / "icu_intervals.json") or {}
    icu_intervals = (
        icu_intervals_doc.get("icu_intervals")
        if isinstance(icu_intervals_doc, dict) else None
    ) or []

    if not isinstance(laps, list):
        laps = []

    return {
        "id": activity_id,
        "date": (activity.get("start_date_local") or "")[:10],
        "name": activity.get("name"),
        "type": activity.get("type"),
        "duration_min": round((activity.get("moving_time") or 0) / 60),
        "distance_km": round((activity.get("distance") or 0) / 1000, 1),
        "elevation_m": activity.get("total_elevation_gain"),
        "tss": activity.get("icu_training_load"),
        "np_w": activity.get("icu_weighted_avg_watts"),
        "if": activity.get("icu_intensity"),
        "avg_w": activity.get("icu_average_watts"),
        "max_w": activity.get("max_watts"),
        "avg_hr": activity.get("average_heartrate"),
        "max_hr": activity.get("max_heartrate"),
        "kj": activity.get("kj"),
        "w_prime_depleted_kj": activity.get("icu_w_prime_depleted"),
        "lap_count": len(laps),
        "laps": [
            {
                "n": i + 1,
                "type": l.get("type"),
                "duration_s": l.get("moving_time"),
                "avg_w": l.get("average_watts"),
                "max_w": l.get("max_watts"),
                "avg_hr": l.get("average_heartrate"),
                "distance_km": round((l.get("distance") or 0) / 1000, 2),
            }
            for i, l in enumerate(laps[:40])
        ],
        "icu_intervals_count": len(icu_intervals) if isinstance(icu_intervals, list) else 0,
    }


@mcp.tool()
def icu_power_curve_90d() -> dict:
    """读取 90 天 rolling power curve（关键时长 PB）。

    HARD RULE: rolling-window PBs ≠ all-out 测试，使用前必须确认锚点。
    """
    p = WAREHOUSE / "3_PowerData" / "power_curves_90d.json"
    pc = _read_json(p)
    if not pc:
        return {"error": "power_curves_90d.json not readable", "path": str(p)}

    entries = pc.get("list") if isinstance(pc, dict) else pc
    if not isinstance(entries, list) or not entries:
        return {"error": "power_curves_90d.json has no list entries"}

    targets = [5, 10, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600, 5400]
    out_by_window = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        secs = entry.get("secs") or []
        watts = entry.get("watts") or entry.get("values") or []
        if not (isinstance(secs, list) and isinstance(watts, list)):
            continue
        sec_to_watt = dict(zip(secs, watts))
        pbs = {f"{t}s": sec_to_watt.get(t) for t in targets if t in sec_to_watt}
        models = entry.get("powerModels") or []
        out_by_window.append({
            "label": entry.get("label"),
            "id": entry.get("id"),
            "days": entry.get("days"),
            "weight_kg": entry.get("weight"),
            "rolling_pbs_w": pbs,
            "power_models": [
                {
                    "type": m.get("type"),
                    "cp_w": m.get("criticalPower"),
                    "w_prime_j": m.get("wPrime"),
                    "ftp_w": m.get("ftp"),
                    "p_max_w": m.get("pMax"),
                }
                for m in models if isinstance(m, dict)
            ],
        })

    return {
        "windows": out_by_window,
        "warning": "PBs are rolling-window peaks, NOT verified all-out tests. CP/W' from MS_2P/MORTON_3P/ECP/FFT are model estimates with 12-42 kJ W' spread — confirm anchor with user.",
        "source": str(p),
        "age_hours": _file_age_hours(p),
    }


@mcp.tool()
def icu_calendar_events(start_date: str, end_date: str) -> list:
    """读取 ICU 日历事件（计划训练 + 完成训练，按日期升序）。

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
    """
    p = WAREHOUSE / "8_Events" / "events.json"
    arr = _read_json(p) or []
    if not isinstance(arr, list):
        return []
    out = []
    for e in arr:
        d = (e.get("start_date_local") or "")[:10]
        if start_date <= d <= end_date:
            out.append({
                "id": e.get("id"),
                "date": d,
                "time": (e.get("start_date_local") or "")[11:16],
                "name": (e.get("name") or "")[:80],
                "category": e.get("category"),
                "type": e.get("type"),
                "tss_planned": e.get("icu_training_load"),
                "duration_min": (
                    round((e.get("moving_time") or 0) / 60)
                    if e.get("moving_time") else None
                ),
            })
    return sorted(out, key=lambda x: (x["date"], x["time"] or ""))


@mcp.tool()
def icu_fitness_trend(days: int = 30) -> dict:
    """读取 fitness 曲线轨迹（CTL/ATL/TSB），从 wellness 推导。

    Args:
        days: 回溯天数
    """
    days = min(max(days, 1), 90)
    wp = WAREHOUSE / "2_Wellness" / "wellness_history.json"
    arr = _read_json(wp) or []
    if not isinstance(arr, list):
        return {"error": "wellness not readable"}
    recent = arr[-days:]
    trajectory = [
        {
            "date": e.get("id"),
            "ctl": round(e.get("ctl") or 0, 1),
            "atl": round(e.get("atl") or 0, 1),
            "tsb": round((e.get("ctl") or 0) - (e.get("atl") or 0), 1),
        }
        for e in recent
    ]
    ctls = [t["ctl"] for t in trajectory if t["ctl"]]
    atls = [t["atl"] for t in trajectory if t["atl"]]
    tsbs = [t["tsb"] for t in trajectory]
    return {
        "trajectory": trajectory,
        "current": trajectory[-1] if trajectory else None,
        "ctl_max_window": max(ctls) if ctls else None,
        "ctl_min_window": min(ctls) if ctls else None,
        "atl_max_window": max(atls) if atls else None,
        "tsb_max_window": max(tsbs) if tsbs else None,
        "tsb_min_window": min(tsbs) if tsbs else None,
        "source": str(wp),
    }


@mcp.tool()
def icu_sync_status() -> dict:
    """检查本地缓存数据新鲜度（mtime only，不触发 sync）。

    cycling-coach 在做分析前调用这个；age >24h 应提示用户 sync。
    """
    files = {
        "athlete_snapshot": MEMORY / "athlete_snapshot.json",
        "wellness_history": WAREHOUSE / "2_Wellness" / "wellness_history.json",
        "activities_list": WAREHOUSE / "4_Activities_List" / "activity_list_clean.json",
        "power_curves_90d": WAREHOUSE / "3_PowerData" / "power_curves_90d.json",
        "events": WAREHOUSE / "8_Events" / "events.json",
        "fitness_trend": MEMORY / "fitness_trend.json",
    }
    out = {}
    for name, p in files.items():
        if p.exists():
            age_h = _file_age_hours(p)
            out[name] = {
                "age_hours": age_h,
                "stale": age_h is not None and age_h > 24,
                "path": str(p),
            }
        else:
            out[name] = {"missing": True, "path": str(p)}
    out["_advice"] = (
        "If any stale=True or missing=True, run: "
        "cd /mnt/d/Cycling/icu && .venv/bin/python scripts/sync_data.py"
    )
    return out


if __name__ == "__main__":
    mcp.run()
