"""
增强趋势分析引擎：跨活动纵向分析，输出结构化 JSON 供 Coach 消费。

产出：coach_memory/training_analysis.json
"""
import glob
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.common import get_warehouse_dir, load_json, save_json, setup_encoding

setup_encoding()

WAREHOUSE = get_warehouse_dir()
MEMORY_DIR = os.path.join(os.path.dirname(WAREHOUSE), "coach_memory")


def _load(rel):
    return load_json(os.path.join(WAREHOUSE, rel))


def _pct(val, ftp):
    return round(val / ftp * 100, 1) if ftp and val else None


# ─── 1. 功率区间定义 ──────────────────────────────────────────────────────────

def get_zone_config():
    """从 sport_settings 读取功率和心率区间（百分比边界）。"""
    settings_list = _load("6_SportSettings/sport_settings.json") or []
    for s in (settings_list if isinstance(settings_list, list) else [settings_list]):
        if s.get('ftp') and s.get('power_zones'):
            ftp = s['ftp']
            pz = s['power_zones']   # 上界百分比列表
            pz_names = s.get('power_zone_names', [f"Z{i+1}" for i in range(len(pz))])
            hz = s.get('hr_zones', [])
            hz_names = s.get('hr_zone_names', [])
            return {
                "ftp": ftp,
                "lthr": s.get('lthr'),
                "power_zone_pcts": pz,
                "power_zone_names": pz_names,
                "hr_zone_boundaries": hz,
                "hr_zone_names": hz_names,
            }
    return {"ftp": 288, "power_zone_pcts": [55,75,90,105,120,150,999],
            "power_zone_names": ["Z1","Z2","Z3","Z4","Z5","Z6","Z7"],
            "hr_zone_boundaries": [], "hr_zone_names": [], "lthr": None}


def classify_power_zone(watts, ftp, zone_pcts):
    """返回 0-based 区间编号。"""
    if not watts or not ftp:
        return -1
    pct = watts / ftp * 100
    for i, upper in enumerate(zone_pcts):
        if pct <= upper:
            return i
    return len(zone_pcts) - 1


# ─── 2. 训练强度分布（极化分析）────────────────────────────────────────────────

def analyze_intensity_distribution(activities, zone_cfg, weeks=8):
    """
    按时间（秒）统计各功率区间分布，计算训练极化度。
    极化度 = (Z1+Z2时间) vs (Z4+Z5+Z6时间)，忽略 Z3。
    """
    cutoff = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    ftp = zone_cfg['ftp']
    zone_pcts = zone_cfg['power_zone_pcts']
    zone_names = zone_cfg['power_zone_names']

    # 从详情文件统计区间时间
    zone_secs = defaultdict(int)
    total_secs = 0
    acts_with_streams = 0

    detail_files = glob.glob(os.path.join(WAREHOUSE, "5_Activities_Detail", "*.json"))
    for fpath in detail_files:
        date_str = os.path.basename(fpath)[:10]
        if date_str < cutoff:
            continue
        data = load_json(fpath)
        if not data:
            continue
        streams = data.get('streams') or {}
        if isinstance(streams, list):  # 旧格式详情文件：[{type, data}, ...]
            streams = {s.get('type'): s.get('data') for s in streams if isinstance(s, dict)}
        watts_stream = streams.get('watts') or []
        if not watts_stream:
            continue
        acts_with_streams += 1
        for w in watts_stream:
            if w is None:
                continue
            z = classify_power_zone(w, ftp, zone_pcts)
            if z >= 0:
                zone_secs[z] += 1
                total_secs += 1

    if not total_secs:
        return None

    zone_dist = []
    for i, name in enumerate(zone_names):
        secs = zone_secs.get(i, 0)
        zone_dist.append({
            "zone": i + 1,
            "name": name,
            "seconds": secs,
            "percent": round(secs / total_secs * 100, 1),
        })

    # 极化度
    low_secs = zone_secs.get(0, 0) + zone_secs.get(1, 0)
    high_secs = sum(zone_secs.get(i, 0) for i in range(3, len(zone_names)))
    mid_secs = total_secs - low_secs - high_secs

    return {
        "period_weeks": weeks,
        "activities_analyzed": acts_with_streams,
        "total_hours": round(total_secs / 3600, 1),
        "zone_distribution": zone_dist,
        "polarization": {
            "low_intensity_pct": round(low_secs / total_secs * 100, 1),
            "medium_intensity_pct": round(mid_secs / total_secs * 100, 1),
            "high_intensity_pct": round(high_secs / total_secs * 100, 1),
            "polarization_index": round(high_secs / (low_secs + high_secs) * 100, 1) if (low_secs + high_secs) else 0,
        }
    }


# ─── 3. 有氧效率趋势（EF = NP / HR）────────────────────────────────────────────

def analyze_aerobic_efficiency(activities, weeks=12):
    """
    追踪有氧效率（EF = NP/avgHR）趋势，区分 LSD 和阈值类型。
    """
    cutoff = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")

    ef_trend = []
    for act in activities:
        date = act.get('start_date_local', '')[:10]
        if date < cutoff:
            continue
        np = act.get('icu_weighted_avg_watts')
        hr = act.get('average_heartrate')
        tss = act.get('icu_training_load', 0)
        duration = act.get('moving_time', 0)
        if not np or not hr or hr < 60:
            continue

        ef = round(np / hr, 3)
        ftp = act.get('icu_ftp', 288)
        if_val = round(np / ftp, 3) if ftp else None

        # 判断训练类型
        if if_val and if_val < 0.75:
            ride_type = "Endurance"
        elif if_val and if_val < 0.90:
            ride_type = "Tempo"
        else:
            ride_type = "Threshold+"

        ef_trend.append({
            "date": date,
            "name": act.get('name', ''),
            "ef": ef,
            "np": np,
            "avg_hr": hr,
            "if": if_val,
            "tss": tss,
            "duration_min": round(duration / 60),
            "ride_type": ride_type,
        })

    ef_trend.sort(key=lambda x: x['date'])

    # 按类型计算近4周 vs 近8周 EF 均值（趋势方向）
    cutoff_4w = (datetime.now() - timedelta(weeks=4)).strftime("%Y-%m-%d")

    def avg_ef(records):
        vals = [r['ef'] for r in records if r['ef']]
        return round(sum(vals) / len(vals), 3) if vals else None

    recent_4w = [r for r in ef_trend if r['date'] >= cutoff_4w]
    older = [r for r in ef_trend if r['date'] < cutoff_4w]

    return {
        "period_weeks": weeks,
        "ef_trend": ef_trend,
        "summary": {
            "recent_4w_avg_ef": avg_ef(recent_4w),
            "prior_avg_ef": avg_ef(older),
            "total_rides_analyzed": len(ef_trend),
            "endurance_rides": len([r for r in ef_trend if r['ride_type'] == 'Endurance']),
        }
    }


# ─── 4. FTP / eFTP 历史趋势 ───────────────────────────────────────────────────

def analyze_ftp_trend(activities):
    """提取 FTP 设定值和 eFTP 的历史变化。"""
    ftp_records = []
    seen_dates = set()

    for act in sorted(activities, key=lambda x: x.get('start_date_local', '')):
        date = act.get('start_date_local', '')[:10]
        if date in seen_dates:
            continue
        seen_dates.add(date)

        ftp = act.get('icu_ftp')
        eftp = act.get('icu_pm_ftp') or act.get('icu_rolling_ftp')
        if ftp:
            ftp_records.append({
                "date": date,
                "ftp_set": ftp,
                "eftp": round(eftp, 1) if eftp else None,
            })

    if not ftp_records:
        return None

    first = ftp_records[0]
    last = ftp_records[-1]
    peak_eftp = max((r['eftp'] for r in ftp_records if r['eftp']), default=None)

    return {
        "history": ftp_records,
        "summary": {
            "earliest_ftp": first['ftp_set'],
            "current_ftp": last['ftp_set'],
            "current_eftp": last['eftp'],
            "peak_eftp_in_history": round(peak_eftp, 1) if peak_eftp else None,
            "ftp_change": (last['ftp_set'] - first['ftp_set']) if first['ftp_set'] else None,
        }
    }


# ─── 5. 功率曲线对比 ─────────────────────────────────────────────────────────

def analyze_power_curve_comparison():
    """对比 90天 vs 全生涯最佳，提取关键时间节点 MMP。"""
    key_durations = {
        "1s": 1, "5s": 5, "30s": 30, "1min": 60, "5min": 300,
        "10min": 600, "20min": 1200, "30min": 1800, "60min": 3600
    }

    def extract_mmps(curve_data):
        if not curve_data:
            return {}
        item = curve_data.get('list', [{}])[0]
        secs_list = item.get('secs', [])
        values = item.get('values', [])
        secs_to_val = dict(zip(secs_list, values))
        result = {}
        for label, s in key_durations.items():
            result[label] = secs_to_val.get(s)
        return result

    curves_90d = _load("3_PowerData/power_curves_90d.json")
    curves_all = _load("3_PowerData/power_curves_all_time.json")

    mmp_90d = extract_mmps(curves_90d)
    mmp_all = extract_mmps(curves_all)

    comparison = {}
    for label in key_durations:
        v90 = mmp_90d.get(label)
        vall = mmp_all.get(label)
        comparison[label] = {
            "90d_watts": v90,
            "all_time_watts": vall,
            "pct_of_alltime": round(v90 / vall * 100, 1) if v90 and vall else None,
        }

    return {
        "mmp_90d": mmp_90d,
        "mmp_all_time": mmp_all,
        "comparison": comparison,
    }


# ─── 6. 疲劳与恢复模式 ───────────────────────────────────────────────────────

def analyze_recovery_patterns(activities):
    """
    分析 TSB 与训练表现的关联：
    - 高 TSB 时（>10）的功率表现是否更好？
    - 识别过度训练风险（CTL 快速上升 + TSB 持续负值）
    """
    records = []
    for act in activities:
        ctl = act.get('icu_ctl')
        atl = act.get('icu_atl')
        if not ctl or not atl:
            continue
        tsb = round(ctl - atl, 1)
        np = act.get('icu_weighted_avg_watts')
        ftp = act.get('icu_ftp', 288)
        records.append({
            "date": act.get('start_date_local', '')[:10],
            "tsb": tsb,
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "np": np,
            "if": round(np / ftp, 3) if np and ftp else None,
            "tss": act.get('icu_training_load'),
        })

    records.sort(key=lambda x: x['date'])

    # 高 TSB 组 vs 低 TSB 组的平均 IF
    high_tsb = [r for r in records if r['tsb'] > 5 and r['np']]
    low_tsb  = [r for r in records if r['tsb'] < -5 and r['np']]

    def avg_if(grp):
        vals = [r['if'] for r in grp if r['if']]
        return round(sum(vals) / len(vals), 3) if vals else None

    # 过度训练风险检测（近3周内 TSB 持续 < -10）
    cutoff_3w = (datetime.now() - timedelta(weeks=3)).strftime("%Y-%m-%d")
    recent = [r for r in records if r['date'] >= cutoff_3w]
    overtraining_risk = len([r for r in recent if r['tsb'] < -10]) >= 3

    # 这里的 TSB/CTL 取自最后一次骑行当天，不是"今天"——当前值以 fitness_trend.json 的 current 为准
    last = records[-1] if records else {}
    return {
        "records": records,
        "summary": {
            "high_tsb_avg_if": avg_if(high_tsb),
            "low_tsb_avg_if": avg_if(low_tsb),
            "overtraining_risk": overtraining_risk,
            "last_ride_date": last.get('date'),
            "last_ride_tsb": last.get('tsb'),
            "last_ride_ctl": last.get('ctl'),
        }
    }


# ─── 7. 恢复信号检测（HRV / RHR 趋势告警） ──────────────────────────────────

def detect_recovery_alerts(baseline_rhr=None, lookback_days=30):
    """
    Compare 7-day rolling HRV/RHR against 30-day baseline and raise alerts.
    Thresholds mirror body_status.md "Recovery Alert Thresholds":
      - HRV 7d avg < 85% of 30d baseline
      - 2 consecutive days each >10% below baseline
      - RHR 7d avg ≥ baseline + 5 bpm
      - fatigue ≥4 or motivation ≤2 for 2 consecutive days
    """
    wellness = _load("2_Wellness/wellness_history.json") or []
    if not wellness:
        return {"alerts": [], "alert_level": "green"}

    sorted_w = sorted(wellness, key=lambda x: x.get('id', ''))
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_30 = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    def _avg(records, key):
        vals = [r[key] for r in records if r.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    recent_7 = [w for w in sorted_w if w.get('id', '') >= cutoff_7]
    recent_30 = [w for w in sorted_w if w.get('id', '') >= cutoff_30]

    hrv_7 = _avg(recent_7, 'hrvSDNN')
    hrv_30 = _avg(recent_30, 'hrvSDNN')
    rhr_7 = _avg(recent_7, 'restingHR')
    rhr_30 = _avg(recent_30, 'restingHR')

    alerts = []
    if hrv_7 and hrv_30 and hrv_7 < hrv_30 * 0.85:
        alerts.append({
            "kind": "hrv_drop",
            "detail": f"HRV 7d avg {hrv_7} is {round((1 - hrv_7 / hrv_30) * 100, 1)}% below 30d baseline {hrv_30}",
        })

    # 2-day consecutive -10% check
    consecutive_hrv_dip = 0
    for w in sorted_w[-2:]:
        v = w.get('hrvSDNN')
        if v and hrv_30 and v < hrv_30 * 0.90:
            consecutive_hrv_dip += 1
    if consecutive_hrv_dip >= 2:
        alerts.append({"kind": "hrv_consecutive", "detail": "HRV >10% below baseline for 2 consecutive days"})

    rhr_base = baseline_rhr or rhr_30
    if rhr_7 and rhr_base and rhr_7 >= rhr_base + 5:
        alerts.append({
            "kind": "rhr_elevated",
            "detail": f"RHR 7d avg {rhr_7} ≥ baseline {rhr_base} + 5 bpm",
        })

    last_two = sorted_w[-2:] if len(sorted_w) >= 2 else []
    if len(last_two) == 2 and all((w.get('fatigue') or 0) >= 4 for w in last_two):
        alerts.append({"kind": "fatigue_self", "detail": "Subjective fatigue ≥4 for 2 days"})
    if len(last_two) == 2 and all((w.get('motivation') or 5) <= 2 for w in last_two):
        alerts.append({"kind": "motivation_self", "detail": "Subjective motivation ≤2 for 2 days"})

    return {
        "alerts": alerts,
        "alert_level": "red" if len(alerts) >= 2 else ("yellow" if alerts else "green"),
        "hrv_7d": hrv_7,
        "hrv_30d": hrv_30,
        "rhr_7d": rhr_7,
        "rhr_30d": rhr_30,
        "rhr_baseline": baseline_rhr,
    }


# ─── 8. 赛事准备度检测 ───────────────────────────────────────────────────────

def detect_race_readiness(days_ahead=10):
    """
    If a priority race falls within `days_ahead` days, compute TSB trajectory and
    emit taper recommendations consistent with the athlete's locked policy
    (target TSB 0 to +5, no full rest day before A races).
    """
    events = _load("8_Events/events.json") or []
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    upcoming = []
    for e in events:
        if e.get("category") not in ("RACE_A", "RACE_B", "RACE_C"):
            continue
        try:
            race_date = datetime.strptime(e.get("start_date_local", "")[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= race_date <= cutoff:
            upcoming.append({
                "date": race_date.isoformat(),
                "name": e.get("name", ""),
                "priority": e["category"],
                "days_away": (race_date - today).days,
            })
    upcoming.sort(key=lambda x: x["days_away"])

    # Current TSB from most recent wellness entry
    wellness = _load("2_Wellness/wellness_history.json") or []
    latest = wellness[-1] if wellness else {}
    ctl = latest.get('ctl')
    atl = latest.get('atl')
    tsb = round(ctl - atl, 1) if (ctl and atl) else None

    if not upcoming:
        return {"races_within_window": [], "current_tsb": tsb, "recommendation": None}

    next_race = upcoming[0]
    target_tsb = "0 to +5" if next_race["priority"] == "RACE_A" else "+5 to +10"
    recommendations = []

    if next_race["priority"] == "RACE_A":
        if next_race["days_away"] >= 7:
            recommendations.append("Last hard block permitted; begin taper 2026-04-24 style (2-day mini-taper) if within 3 days.")
        if next_race["days_away"] in (1, 2):
            recommendations.append("Openers day: 3×1 min @ 115% FTP + 2×10 sec MAX. NO pure Z1 day-before.")
        if tsb is not None and tsb > 10 and next_race["days_away"] <= 3:
            recommendations.append(f"⚠️ TSB {tsb} > +10: staleness risk (see 2026-04-01 log). Insert one 40-min Z3 ride to pull TSB into 0..+5.")
        if tsb is not None and tsb < -10 and next_race["days_away"] <= 3:
            recommendations.append(f"⚠️ TSB {tsb} too negative. Reduce next 2 days to Z1/Z2 short (≤45 min) + openers D-1.")
    else:
        recommendations.append("Priority B/C — keep normal training; add 15 min openers day-before.")

    return {
        "races_within_window": upcoming,
        "current_tsb": tsb,
        "target_tsb_for_next_race": target_tsb,
        "recommendation": recommendations,
    }


# ─── 主函数 ──────────────────────────────────────────────────────────────────

def run_analysis():
    print("📊 运行增强趋势分析...")
    os.makedirs(MEMORY_DIR, exist_ok=True)

    activities = _load("4_Activities_List/activity_list_clean.json") or []
    zone_cfg = get_zone_config()
    ftp = zone_cfg['ftp']
    print(f"   使用 FTP={ftp}W，功率区间: {zone_cfg['power_zone_names']}")

    print("\n[1/5] 训练强度分布（区间时间统计）...")
    intensity = analyze_intensity_distribution(activities, zone_cfg, weeks=8)
    if intensity:
        pol = intensity['polarization']
        print(f"   低强度 {pol['low_intensity_pct']}% | 中强度 {pol['medium_intensity_pct']}% | 高强度 {pol['high_intensity_pct']}%")
        print(f"   极化指数: {pol['polarization_index']}%（高强度占有效训练时间比）")

    print("\n[2/5] 有氧效率趋势（EF 趋势）...")
    ae = analyze_aerobic_efficiency(activities, weeks=12)
    if ae:
        s = ae['summary']
        print(f"   近4周均 EF={s['recent_4w_avg_ef']} | 之前均 EF={s['prior_avg_ef']} | 共 {s['total_rides_analyzed']} 次骑行")

    print("\n[3/5] FTP 历史趋势...")
    ftp_trend = analyze_ftp_trend(activities)
    if ftp_trend:
        s = ftp_trend['summary']
        print(f"   当前 FTP={s['current_ftp']}W | eFTP={s['current_eftp']}W | 历史峰值eFTP={s['peak_eftp_in_history']}W")

    print("\n[4/5] 功率曲线对比（90天 vs 全生涯）...")
    pc = analyze_power_curve_comparison()
    if pc:
        cmp = pc['comparison']
        print(f"   5min: {cmp['5min']['90d_watts']}W ({cmp['5min']['pct_of_alltime']}% of all-time)")
        print(f"   20min: {cmp['20min']['90d_watts']}W ({cmp['20min']['pct_of_alltime']}% of all-time)")

    print("\n[5/7] 疲劳恢复模式...")
    recovery = analyze_recovery_patterns(activities)
    s = recovery['summary']
    risk_str = "⚠️ 有过度训练风险" if s['overtraining_risk'] else "正常"
    print(f"   最后一次骑行 {s['last_ride_date']}: TSB={s['last_ride_tsb']} CTL={s['last_ride_ctl']} | 状态: {risk_str}")
    print(f"   高TSB时均IF={s['high_tsb_avg_if']} vs 低TSB时均IF={s['low_tsb_avg_if']}")

    print("\n[6/7] 恢复信号告警 (HRV / RHR)...")
    profile = _load("1_Profile/athlete_profile.json") or {}
    baseline_rhr = profile.get('icu_resting_hr')
    recovery_alerts = detect_recovery_alerts(baseline_rhr=baseline_rhr)
    print(f"   告警等级: {recovery_alerts['alert_level']}  ({len(recovery_alerts['alerts'])} 条)")
    for a in recovery_alerts['alerts']:
        print(f"   ⚠️  {a['detail']}")

    print("\n[7/7] 赛事准备度 (10 日窗口)...")
    race_readiness = detect_race_readiness(days_ahead=10)
    if race_readiness.get('races_within_window'):
        for r in race_readiness['races_within_window']:
            print(f"   {r['date']}  {r['name']}  ({r['priority']}, {r['days_away']}d away)")
        for rec in race_readiness.get('recommendation') or []:
            print(f"   → {rec}")
    else:
        print("   未来 10 天内无计划赛事。")

    # 整合输出
    analysis = {
        "generated_at": datetime.now().isoformat(),
        "zone_config": zone_cfg,
        "intensity_distribution": intensity,
        "aerobic_efficiency": ae,
        "ftp_trend": ftp_trend,
        "power_curve_comparison": pc,
        "recovery_patterns": recovery,
        "recovery_alerts": recovery_alerts,
        "race_readiness": race_readiness,
    }

    path = save_json(analysis, MEMORY_DIR, "training_analysis.json")
    _auto_append_alerts_to_log(recovery_alerts, race_readiness)
    print(f"\n✅ 分析完成 → {path}")
    return analysis


def _auto_append_alerts_to_log(recovery_alerts, race_readiness):
    """
    If fresh recovery alerts or race-week recommendations exist, append a dated
    entry to coach_log.md — but de-duplicate (do not append if identical
    content was added today).
    """
    log_path = os.path.join(MEMORY_DIR, "coach_log.md")
    if not os.path.exists(log_path):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    lines_to_add = []
    alerts = recovery_alerts.get('alerts') or []
    if alerts:
        details = "; ".join(a['detail'] for a in alerts)
        lines_to_add.append(f"## {today}: [Recovery Alert — {recovery_alerts['alert_level']}] {details}")

    races = race_readiness.get('races_within_window') or []
    recs = race_readiness.get('recommendation') or []
    if races and recs:
        next_race = races[0]
        rec_str = " | ".join(recs)
        lines_to_add.append(
            f"## {today}: [Race Readiness — {next_race['name']} in {next_race['days_away']}d] {rec_str}"
        )

    if not lines_to_add:
        return

    existing = open(log_path, encoding='utf-8').read()
    to_append = "\n\n".join(l for l in lines_to_add if l not in existing)
    if not to_append:
        return

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write("\n\n" + to_append + "\n")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), '../..'))
    run_analysis()
