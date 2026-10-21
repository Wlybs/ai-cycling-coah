"""
Coach 记忆构建器：从数据仓库提炼训练上下文，写入 coach_memory/。

自动生成（每次 build_memory.py 运行时覆盖）：
  coach_memory/athlete_snapshot.json  — 运动员当前画像
  coach_memory/training_history.json  — 近期训练历史摘要
  coach_memory/fitness_trend.json     — 体能趋势（CTL/ATL/TSB）

手动维护（由教练/用户编辑，不会被覆盖）：
  coach_memory/body_status.md         — 伤病与身体状况
  coach_memory/race_calendar.md       — 赛事日历
  coach_memory/nutrition_strategy.md  — 补给策略
  coach_memory/coach_log.md           — 教练日志
"""
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.common import get_warehouse_dir, load_json, save_json, setup_encoding

setup_encoding()

WAREHOUSE = get_warehouse_dir()
MEMORY_DIR = os.path.join(os.path.dirname(WAREHOUSE), "coach_memory")


# ─── 辅助函数 ─────────────────────────────────────────────────────────────────

def _load(relative_path):
    return load_json(os.path.join(WAREHOUSE, relative_path))


def _fmt_duration(seconds):
    if not seconds:
        return "0min"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    return f"{h}h{m}min" if h else f"{m}min"


# ─── 1. 运动员画像 ────────────────────────────────────────────────────────────

def _compute_power_zones(ftp, zone_pcts, zone_names):
    """Convert zone upper-bound percentages into watts, labeling each range."""
    if not ftp or not zone_pcts:
        return []
    zones = []
    prev_watts = 0
    for i, upper_pct in enumerate(zone_pcts):
        name = zone_names[i] if i < len(zone_names) else f"Z{i + 1}"
        upper_watts = round(ftp * upper_pct / 100) if upper_pct < 900 else None
        zones.append({
            "zone": i + 1,
            "name": name,
            "lower_pct": round(prev_watts / ftp * 100, 1) if ftp else None,
            "upper_pct": upper_pct,
            "lower_watts": prev_watts,
            "upper_watts": upper_watts,
        })
        prev_watts = (upper_watts + 1) if upper_watts else prev_watts
    return zones


def _compute_hr_zones(hr_boundaries, zone_names, lthr=None):
    """hr_zones in sport_settings is a list of upper bounds in BPM."""
    if not hr_boundaries:
        return []
    zones = []
    prev_bpm = 0
    for i, upper_bpm in enumerate(hr_boundaries):
        name = zone_names[i] if i < len(zone_names) else f"Z{i + 1}"
        zones.append({
            "zone": i + 1,
            "name": name,
            "lower_bpm": prev_bpm,
            "upper_bpm": upper_bpm,
            "pct_of_lthr": round(upper_bpm / lthr * 100, 1) if lthr else None,
        })
        prev_bpm = upper_bpm + 1
    return zones


def build_athlete_snapshot():
    profile = _load("1_Profile/athlete_profile.json") or {}
    settings_list = _load("6_SportSettings/sport_settings.json") or []
    wellness = _load("2_Wellness/wellness_history.json") or []

    # 从 sport_settings 找骑行的 FTP
    ftp = None
    lthr = None
    pz_pcts, pz_names = [], []
    hz_boundaries, hz_names = [], []
    for s in (settings_list if isinstance(settings_list, list) else [settings_list]):
        if s.get('ftp'):
            ftp = s['ftp']
            lthr = s.get('lthr') or s.get('thresholdHR')
            pz_pcts = s.get('power_zones') or s.get('powerZones') or s.get('zones') or []
            pz_names = s.get('power_zone_names') or []
            hz_boundaries = s.get('hr_zones') or s.get('hrZones') or []
            hz_names = s.get('hr_zone_names') or []
            break

    power_zones = _compute_power_zones(ftp, pz_pcts, pz_names)
    hr_zones = _compute_hr_zones(hz_boundaries, hz_names, lthr)

    # W' 从最近 wellness 读取
    w_prime = None
    for w in reversed(wellness):
        sport_info = w.get('sportInfo') or []
        for si in sport_info:
            if si.get('type') == 'Ride' and si.get('wPrime'):
                w_prime = si['wPrime']
                break
        if w_prime:
            break

    # 最新体重
    weight = None
    for w in reversed(wellness):
        if w.get('weight'):
            weight = w['weight']
            break

    recovery_signals = _build_recovery_signals(wellness, profile.get('icu_resting_hr'))
    recent_pbs = _build_recent_pbs()

    snapshot = {
        "updated_at": datetime.now().isoformat(),
        "name": profile.get('name', 'Unknown'),
        "athlete_id": profile.get('id'),
        "ftp_set": ftp,           # ICU 设定 FTP
        "lthr": lthr,
        "w_prime": w_prime,
        "weight_kg": weight,
        "w_per_kg_ftp": round(ftp / weight, 2) if (ftp and weight) else None,
        "power_zones": power_zones,
        "hr_zones": hr_zones,
        "recovery_signals": recovery_signals,
        "recent_pbs": recent_pbs,
        "profile_raw": {
            k: profile.get(k)
            for k in ['icu_vo2max', 'icu_resting_hr', 'sex', 'dob']
            if profile.get(k)
        },
    }

    path = save_json(snapshot, MEMORY_DIR, "athlete_snapshot.json")
    zone_preview = f"{len(power_zones)}区" if power_zones else "(空)"
    print(f"   ✅ 运动员画像: FTP={ftp}W / LTHR={lthr}bpm / 体重={weight}kg / 区间={zone_preview} → {path}")
    return snapshot


def _build_recovery_signals(wellness, baseline_rhr=None):
    """
    Compute HRV / RHR 7-day rolling avg and compare to 30-day baseline.
    Emits alert records when body_status.md thresholds are breached.
    """
    if not wellness:
        return None

    sorted_w = sorted(wellness, key=lambda x: x.get('id', ''))
    today_cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    today_cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    def _stat(records, field):
        vals = [r.get(field) for r in records if r.get(field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    recent_7 = [w for w in sorted_w if w.get('id', '') >= today_cutoff_7]
    recent_30 = [w for w in sorted_w if w.get('id', '') >= today_cutoff_30]

    hrv_7 = _stat(recent_7, 'hrvSDNN')
    hrv_30 = _stat(recent_30, 'hrvSDNN')
    rhr_7 = _stat(recent_7, 'restingHR')
    rhr_30 = _stat(recent_30, 'restingHR')

    alerts = []
    if hrv_7 and hrv_30 and hrv_7 < hrv_30 * 0.85:
        alerts.append(f"HRV 7d avg {hrv_7} dropped >15% below 30d baseline {hrv_30}")
    rhr_base = baseline_rhr or rhr_30
    if rhr_7 and rhr_base and rhr_7 >= rhr_base + 5:
        alerts.append(f"RHR 7d avg {rhr_7} ≥ baseline {rhr_base} + 5 bpm")

    # 2-day consecutive checks on raw latest entries
    last_two = sorted_w[-2:] if len(sorted_w) >= 2 else []
    fatigue_hits = sum(1 for w in last_two if (w.get('fatigue') or 0) >= 4)
    motivation_hits = sum(1 for w in last_two if (w.get('motivation') or 5) <= 2)
    if fatigue_hits == 2:
        alerts.append("Self-reported fatigue ≥4 on 2 consecutive days")
    if motivation_hits == 2:
        alerts.append("Self-reported motivation ≤2 on 2 consecutive days")

    return {
        "hrv_7d_avg": hrv_7,
        "hrv_30d_baseline": hrv_30,
        "rhr_7d_avg": rhr_7,
        "rhr_30d_baseline": rhr_30,
        "rhr_configured_baseline": baseline_rhr,
        "alerts": alerts,
        "alert_level": "red" if len(alerts) >= 2 else ("yellow" if alerts else "green"),
    }


def _build_recent_pbs():
    """
    Extract key-duration PBs from 90d and all-time power curves if available.
    """
    curves_90d = _load("3_PowerData/power_curves_90d.json") or {}
    curves_all = _load("3_PowerData/power_curves_all_time.json") or {}

    key_durations = {
        "5s": 5, "30s": 30, "1min": 60, "5min": 300,
        "10min": 600, "20min": 1200, "60min": 3600,
    }

    def _extract(curve):
        item = (curve.get('list') or [{}])[0]
        secs = item.get('secs') or []
        vals = item.get('values') or []
        return dict(zip(secs, vals))

    m90 = _extract(curves_90d)
    m_all = _extract(curves_all)
    return {
        label: {
            "watts_90d": m90.get(secs),
            "watts_all_time": m_all.get(secs),
        }
        for label, secs in key_durations.items()
    }


# ─── 2. 训练历史摘要 ──────────────────────────────────────────────────────────

def build_training_history(weeks=12):
    activities = _load("4_Activities_List/activity_list_clean.json") or []
    if not activities:
        print("   ⚠️ 未找到活动列表。")
        return {}

    cutoff = datetime.now() - timedelta(weeks=weeks)

    # 按周聚合
    weekly = defaultdict(lambda: {
        "tss": 0, "duration_sec": 0, "distance_m": 0,
        "rides": 0, "elevation_m": 0, "avg_power_list": [], "avg_hr_list": []
    })

    all_activities = []
    for act in activities:
        try:
            dt = datetime.fromisoformat(act['start_date_local'])
        except Exception:
            continue
        if dt < cutoff:
            continue

        # ISO 周标签
        week_key = dt.strftime("%Y-W%W")
        w = weekly[week_key]
        w["tss"] += act.get('icu_training_load') or 0
        w["duration_sec"] += act.get('moving_time') or 0
        w["distance_m"] += act.get('distance') or 0
        w["rides"] += 1
        w["elevation_m"] += act.get('total_elevation_gain') or 0
        if act.get('icu_weighted_avg_watts'):
            w["avg_power_list"].append(act['icu_weighted_avg_watts'])
        if act.get('average_heartrate'):
            w["avg_hr_list"].append(act['average_heartrate'])

        all_activities.append({
            "date": act['start_date_local'][:10],
            "name": act.get('name', ''),
            "type": act.get('type', ''),
            "tss": act.get('icu_training_load'),
            "duration": _fmt_duration(act.get('moving_time')),
            "distance_km": round((act.get('distance') or 0) / 1000, 1),
            "np_watts": act.get('icu_weighted_avg_watts'),
            "avg_hr": act.get('average_heartrate'),
            "ctl": round(act.get('icu_ctl') or 0, 1),
            "atl": round(act.get('icu_atl') or 0, 1),
            "ftp_at_time": act.get('icu_ftp'),
            "rolling_ftp": act.get('icu_rolling_ftp'),
        })

    # 整理周汇总
    weekly_summary = []
    for week_key in sorted(weekly.keys()):
        w = weekly[week_key]
        avg_p = round(sum(w['avg_power_list']) / len(w['avg_power_list']), 1) if w['avg_power_list'] else None
        avg_hr = round(sum(w['avg_hr_list']) / len(w['avg_hr_list']), 1) if w['avg_hr_list'] else None
        weekly_summary.append({
            "week": week_key,
            "rides": w["rides"],
            "tss": round(w["tss"], 1),
            "duration": _fmt_duration(w["duration_sec"]),
            "distance_km": round(w["distance_m"] / 1000, 1),
            "elevation_m": round(w["elevation_m"]),
            "avg_np_watts": avg_p,
            "avg_hr": avg_hr,
        })

    # 最近4周平均周TSS
    recent_weeks = weekly_summary[-4:] if len(weekly_summary) >= 4 else weekly_summary
    avg_weekly_tss = round(sum(w["tss"] for w in recent_weeks) / len(recent_weeks), 1) if recent_weeks else 0

    history = {
        "updated_at": datetime.now().isoformat(),
        "period_weeks": weeks,
        "total_rides": len(all_activities),
        "avg_weekly_tss": avg_weekly_tss,
        "weekly_summary": weekly_summary,
        "recent_activities": sorted(all_activities, key=lambda x: x["date"], reverse=True)[:30],
    }

    path = save_json(history, MEMORY_DIR, "training_history.json")
    print(f"   ✅ 训练历史: {len(all_activities)} 次活动 / 近4周均TSS={avg_weekly_tss} → {path}")
    return history


# ─── 3. 体能趋势 ─────────────────────────────────────────────────────────────

def build_fitness_trend(days=90):
    wellness = _load("2_Wellness/wellness_history.json") or []
    if not wellness:
        print("   ⚠️ 未找到健康数据。")
        return {}

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    trend = []
    for w in wellness:
        if w.get('id', '') < cutoff:
            continue
        ctl = w.get('ctl')
        atl = w.get('atl')
        trend.append({
            "date": w['id'],
            "ctl": round(ctl, 1) if ctl else None,
            "atl": round(atl, 1) if atl else None,
            "tsb": round(ctl - atl, 1) if (ctl and atl) else None,
            "ramp_rate": round(w.get('rampRate') or 0, 2),
            "hrv": w.get('hrvSDNN'),
            "rhr": w.get('restingHR'),
            "weight": w.get('weight'),
            "sleep_score": w.get('sleepScore'),
            "fatigue": w.get('fatigue'),
            "motivation": w.get('motivation'),
        })

    # 当前状态
    latest = trend[-1] if trend else {}
    peak_ctl = max((t['ctl'] for t in trend if t['ctl']), default=None)

    fitness_data = {
        "updated_at": datetime.now().isoformat(),
        "period_days": days,
        "current": {
            "date": latest.get('date'),
            "ctl": latest.get('ctl'),
            "atl": latest.get('atl'),
            "tsb": latest.get('tsb'),
            "ramp_rate": latest.get('ramp_rate'),
        },
        "peak_ctl_in_period": round(peak_ctl, 1) if peak_ctl else None,
        "trend": trend,
    }

    path = save_json(fitness_data, MEMORY_DIR, "fitness_trend.json")
    ctl = latest.get('ctl', '-')
    atl = latest.get('atl', '-')
    tsb = latest.get('tsb', '-')
    print(f"   ✅ 体能趋势: 当前 CTL={ctl} / ATL={atl} / TSB={tsb} / 峰值CTL={peak_ctl} → {path}")
    return fitness_data


# ─── 4. 检查手动维护记忆文件 ────────────────────────────────────────────────

def check_manual_memory_files():
    manual_files = [
        ("body_status.md",        "身体状况"),
        ("race_calendar.md",      "赛事日历"),
        ("nutrition_strategy.md", "补给策略"),
        ("coach_log.md",          "教练日志"),
    ]
    for fname, label in manual_files:
        fpath = os.path.join(MEMORY_DIR, fname)
        status = "✅ 存在" if os.path.exists(fpath) else "⚠️  缺失"
        print(f"   {status} — {fname} ({label})")


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def build_all():
    print("🧠 构建 Coach 记忆...")
    os.makedirs(MEMORY_DIR, exist_ok=True)

    print("\n[1/4] 运动员画像")
    build_athlete_snapshot()

    print("\n[2/4] 训练历史（近12周）")
    build_training_history(weeks=12)

    print("\n[3/4] 体能趋势（近90天）")
    build_fitness_trend(days=90)

    print("\n[4/4] 手动记忆文件")
    check_manual_memory_files()

    print(f"\n✅ 记忆构建完成，文件位于: {MEMORY_DIR}/")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), '../..'))
    build_all()
