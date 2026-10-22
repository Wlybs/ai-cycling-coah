"""
Plan Adherence Evaluator
========================

Compares the most-recent generated weekly plan (reports/plan_YYYYMMDD.json)
against completed rides from the warehouse and produces
coach_memory/plan_adherence.json so the next plan can learn from execution.

Output schema (coach_memory/plan_adherence.json):
{
  "generated_at": ISO,
  "plan_file": str,
  "week_start": "YYYY-MM-DD",
  "week_end":   "YYYY-MM-DD",
  "days": [
      {
        "date": "YYYY-MM-DD",
        "day_of_week": "周一",
        "planned": {training_type, name, target_tss, power_range_w, ...},
        "actual":  {name, tss, np_watts, avg_hr, duration_min, if} or null,
        "status": "completed" | "skipped" | "over" | "under" | "substituted" | "future",
        "tss_delta": int or null,
        "if_delta":  float or null,
        "note": str,
      }
  ],
  "summary": {
      "planned_days": N,
      "completed_days": M,
      "tss_target": int,
      "tss_actual": int,
      "tss_ratio":  float,
      "compliance_pct": float,   # completed / planned (excluding Rest)
      "bias": "over" | "under" | "balanced",
      "missed_types": ["VO2max", ...],
  }
}
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.common import get_warehouse_dir, load_json, save_json, setup_encoding

setup_encoding()

WAREHOUSE = get_warehouse_dir()
ROOT = os.path.dirname(WAREHOUSE)
MEMORY_DIR = os.path.join(ROOT, "coach_memory")
REPORTS_DIR = os.path.join(ROOT, "reports")


STALE_AFTER_DAYS = 7  # 计划周结束超过 7 天就不再当作"上周计划"评估


def _find_latest_plan(today: str | None = None) -> str | None:
    """Return the newest plan that has started and ended no more than STALE_AFTER_DAYS ago.

    Old plans (e.g. a May race-week plan read in October) are ignored, so a
    long break in planning never resurfaces as "last week's adherence".
    """
    if not os.path.isdir(REPORTS_DIR):
        return None
    today_d = date.fromisoformat(today) if today else date.today()
    cutoff = (today_d - timedelta(days=STALE_AFTER_DAYS)).isoformat()
    for path in sorted(glob.glob(os.path.join(REPORTS_DIR, "plan_*.json")), reverse=True):
        plan = load_json(path) or {}
        week_start, week_end = plan.get("week_start"), plan.get("week_end")
        if week_start and week_end and week_start <= today_d.isoformat() and week_end >= cutoff:
            return path
    return None


def _classify_actual_if(if_val: float | None) -> str:
    if if_val is None:
        return "Unknown"
    if if_val < 0.60:
        return "Recovery"
    if if_val < 0.75:
        return "Aerobic"
    if if_val < 0.85:
        return "Tempo"
    if if_val < 0.95:
        return "Threshold"
    if if_val < 1.05:
        return "VO2max"
    return "Neuromuscular"


def _match_rides_by_date(activities: list[dict], week_start: str, week_end: str) -> dict[str, dict]:
    """Group rides by YYYY-MM-DD for the plan week; keep the highest-TSS ride per day."""
    by_date: dict[str, dict] = {}
    for act in activities:
        date_str = (act.get('start_date_local') or '')[:10]
        if not (week_start <= date_str <= week_end):
            continue
        ftp = act.get('icu_ftp') or 300
        np = act.get('icu_weighted_avg_watts')
        if_val = round(np / ftp, 3) if (np and ftp) else None
        ride = {
            "name": act.get('name', ''),
            "tss": act.get('icu_training_load'),
            "np_watts": np,
            "avg_hr": act.get('average_heartrate'),
            "duration_min": round((act.get('moving_time') or 0) / 60),
            "if": if_val,
            "classified_type": _classify_actual_if(if_val),
        }
        prev = by_date.get(date_str)
        if not prev or (ride.get('tss') or 0) > (prev.get('tss') or 0):
            by_date[date_str] = ride
    return by_date


def _compare_day(planned: dict, actual: dict | None, today: str) -> dict:
    day = {
        "date": planned["date"],
        "day_of_week": planned.get("day_of_week", ""),
        "planned": {
            "training_type": planned.get("training_type"),
            "name": planned.get("name"),
            "target_tss": planned.get("target_tss"),
            "duration_min": planned.get("duration_min"),
            "power_range_w": planned.get("power_range_w"),
        },
        "actual": actual,
        "tss_delta": None,
        "if_delta": None,
        "status": "future",
        "note": "",
    }

    if planned["date"] > today:
        day["status"] = "future"
        return day

    is_rest = planned.get("training_type") == "Rest"
    if not actual:
        day["status"] = "skipped" if not is_rest else "completed"
        day["note"] = "Rest honoured" if is_rest else "No ride recorded."
        return day

    if is_rest:
        day["status"] = "substituted"
        day["note"] = f"Athlete rode on scheduled rest day (TSS {actual.get('tss')})."
        return day

    target_tss = planned.get("target_tss") or 0
    actual_tss = actual.get("tss") or 0
    day["tss_delta"] = int(round(actual_tss - target_tss))

    if target_tss > 0 and abs(day["tss_delta"]) / target_tss <= 0.15:
        day["status"] = "completed"
    elif day["tss_delta"] > 0:
        day["status"] = "over"
        day["note"] = f"+{day['tss_delta']} TSS over target."
    else:
        day["status"] = "under"
        day["note"] = f"{day['tss_delta']} TSS below target."

    # Type drift: planned VO2max but actual Aerobic = red flag
    planned_type = planned.get("training_type")
    actual_type = actual.get("classified_type")
    if planned_type and actual_type and planned_type != actual_type:
        day["note"] += f" Planned {planned_type} → classified {actual_type}."

    return day


def evaluate_plan(plan_path: str | None = None, verbose: bool = True) -> dict | None:
    if plan_path is None:
        plan_path = _find_latest_plan()
        if plan_path is None:
            # 覆盖旧报告：不写 summary，下游（plan_generator）就不会再引用过期的执行情况
            save_json({
                "generated_at": datetime.now().isoformat(),
                "status": "no_recent_plan",
                "note": f"reports/ 中没有 {STALE_AFTER_DAYS} 天内结束的周计划，未评估执行情况",
            }, MEMORY_DIR, "plan_adherence.json")
            if verbose:
                print(f"   ⚠️ 没有 {STALE_AFTER_DAYS} 天内的周计划，跳过 adherence 评估（已标记 no_recent_plan）。")
            return None
    if not os.path.exists(plan_path):
        if verbose:
            print(f"   ⚠️ 计划文件不存在: {plan_path}，跳过 adherence 评估。")
        return None

    with open(plan_path, encoding='utf-8') as f:
        plan = json.load(f)

    week_start = plan.get("week_start")
    week_end = plan.get("week_end")
    if not week_start or not week_end:
        if verbose:
            print(f"   ⚠️ 计划文件缺少 week_start/week_end: {plan_path}")
        return None

    activities = load_json(os.path.join(WAREHOUSE, "4_Activities_List", "activity_list_clean.json")) or []
    by_date = _match_rides_by_date(activities, week_start, week_end)

    today = datetime.now().strftime("%Y-%m-%d")
    day_reports = []
    for planned in plan.get("days", []):
        actual = by_date.get(planned["date"])
        day_reports.append(_compare_day(planned, actual, today))

    non_rest = [d for d in day_reports if d["planned"]["training_type"] != "Rest"]
    past = [d for d in non_rest if d["status"] != "future"]
    completed = [d for d in past if d["status"] in ("completed", "over")]
    skipped = [d for d in past if d["status"] == "skipped"]

    tss_target = sum((d["planned"].get("target_tss") or 0) for d in past)
    tss_actual = sum((d["actual"].get("tss") or 0) for d in past if d["actual"])
    missed_types = sorted({
        d["planned"]["training_type"]
        for d in skipped
        if d["planned"]["training_type"]
    })

    bias = "balanced"
    if tss_target > 0:
        ratio = tss_actual / tss_target
        if ratio > 1.15:
            bias = "over"
        elif ratio < 0.85:
            bias = "under"
    else:
        ratio = None

    report = {
        "generated_at": datetime.now().isoformat(),
        "plan_file": os.path.basename(plan_path),
        "week_start": week_start,
        "week_end": week_end,
        "days": day_reports,
        "summary": {
            "planned_days": len(non_rest),
            "completed_days": len(completed),
            "skipped_days": len(skipped),
            "tss_target": tss_target,
            "tss_actual": int(round(tss_actual)),
            "tss_ratio": round(ratio, 2) if ratio else None,
            "compliance_pct": round(len(completed) / len(non_rest) * 100, 1) if non_rest else None,
            "bias": bias,
            "missed_types": missed_types,
        },
    }

    path = save_json(report, MEMORY_DIR, "plan_adherence.json")
    if verbose:
        s = report["summary"]
        compliance = s.get("compliance_pct")
        compliance_str = f"{compliance}%" if compliance is not None else "—"
        print(
            f"   ✅ 计划执行: 完成 {s['completed_days']}/{s['planned_days']} "
            f"| TSS {s['tss_actual']}/{s['tss_target']} ({s['bias']}) "
            f"| 合规率 {compliance_str} → {path}"
        )
        if missed_types:
            print(f"      跳过类型: {', '.join(missed_types)}  (下周应补偿)")
    return report


if __name__ == "__main__":
    os.chdir(ROOT)
    evaluate_plan()
