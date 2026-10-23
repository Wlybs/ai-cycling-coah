"""
从活动详情 JSON 中提取结构化骑行摘要，供教练分析使用。

用法:
  python extract_ride_summary.py              # 最新一条活动
  python extract_ride_summary.py 3            # 最新 3 条活动
  python extract_ride_summary.py <activity_id> # 指定活动 ID
"""
import sys
import os
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.common import setup_encoding

setup_encoding()

DIR_DETAIL = os.path.join(os.path.dirname(__file__), '..', 'icu_data_warehouse', '5_Activities_Detail')


def fmt_time(secs):
    """秒数 → h:mm:ss 或 m:ss 格式。"""
    if secs is None:
        return "N/A"
    secs = int(secs)
    if secs >= 3600:
        return f"{secs // 3600}:{(secs % 3600) // 60:02d}:{secs % 60:02d}"
    return f"{secs // 60}:{secs % 60:02d}"


def fmt_timestamp(iso_str, start_iso):
    """将绝对 ISO 时间戳转换为相对于骑行开始的 elapsed 时间字符串。"""
    if not iso_str or not start_iso:
        return ""
    try:
        # 处理不同格式
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                t = datetime.strptime(iso_str, fmt)
                break
            except ValueError:
                continue
        else:
            return ""
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                s = datetime.strptime(start_iso, fmt)
                break
            except ValueError:
                continue
        else:
            return ""
        # 去掉 tzinfo 做差
        t_naive = t.replace(tzinfo=None)
        s_naive = s.replace(tzinfo=None)
        delta = int((t_naive - s_naive).total_seconds())
        if delta < 0:
            return ""
        return fmt_time(delta)
    except Exception:
        return ""


def classify_session(summary, zone_pcts, work_intervals, ftp):
    """基于功率区间分布和间歇结构自动分类训练类型。

    返回 dict:
      type:        主分类标签
      sub_type:    细分标签
      description: 一句话描述实际训练内容
    """
    # zone_pcts: {"Z1": 41.7, "Z2": 21.2, ...} 百分比浮点数
    z1 = zone_pcts.get('Z1', 0)
    z2 = zone_pcts.get('Z2', 0)
    z3 = zone_pcts.get('Z3', 0)
    z4 = zone_pcts.get('Z4', 0)
    z5 = zone_pcts.get('Z5', 0)
    z6 = zone_pcts.get('Z6', 0)
    z7 = zone_pcts.get('Z7', 0)

    high_z = z5 + z6 + z7          # VO2max + Anaerobic + Neuromuscular
    threshold_z = z4                # Threshold
    ss_z = z3                       # Tempo / Sweet Spot
    low_z = z1 + z2                 # Recovery + Endurance

    # 分析工作间歇的结构
    n_work = len(work_intervals)
    work_durations = []
    work_powers = []
    for w in work_intervals:
        dur = w.get('avg_watts', 0)  # just for counting
        elapsed = w.get('duration', '0:00')
        # 解析 m:ss 或 h:mm:ss
        parts = elapsed.split(':')
        try:
            if len(parts) == 3:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                secs = int(parts[0]) * 60 + int(parts[1])
            else:
                secs = 0
        except ValueError:
            secs = 0
        work_durations.append(secs)
        work_powers.append(w.get('avg_watts', 0))

    # 短间歇 (<60s), 中间歇 (60-300s), 长间歇 (>300s)
    short_count = sum(1 for d in work_durations if 0 < d < 60)
    mid_count = sum(1 for d in work_durations if 60 <= d <= 300)
    long_count = sum(1 for d in work_durations if d > 300)

    avg_work_power = sum(work_powers) / len(work_powers) if work_powers else 0
    if_work = round(avg_work_power / ftp * 100) if ftp and avg_work_power else 0

    moving_time = summary.get('moving_time', 0) or 0

    tss = summary.get('icu_training_load', 0) or 0

    # ── 分类逻辑 ──
    # Recovery (must be short + low TSS)
    if low_z >= 85 and high_z < 3 and threshold_z < 5 and tss < 80 and moving_time < 5400:
        return {"type": "Recovery", "sub_type": "Active Recovery",
                "description": f"Z1+Z2 占 {low_z:.0f}%，TSS {tss}，纯恢复骑"}

    # Endurance / LSD (long Z1+Z2 dominant)
    if low_z >= 75 and high_z < 10 and threshold_z < 10 and moving_time >= 3600:
        return {"type": "Endurance", "sub_type": "LSD / Aerobic Base",
                "description": f"Z1+Z2 占 {low_z:.0f}%，{fmt_time(moving_time)} 有氧长距离，TSS {tss}"}

    # Endurance (long Z2)
    if z2 >= 50 and high_z < 10 and threshold_z < 10 and moving_time >= 3600:
        return {"type": "Endurance", "sub_type": "Aerobic Base",
                "description": f"Z2 占 {z2:.0f}%，{fmt_time(moving_time)} 有氧基础"}

    # Endurance (shorter)
    if low_z >= 65 and high_z < 10 and threshold_z < 10:
        return {"type": "Endurance", "sub_type": "Easy Ride",
                "description": f"Z1+Z2 占 {low_z:.0f}%，轻松骑"}

    # Neuromuscular / Sprint
    if z7 >= 5 or (short_count >= 5 and avg_work_power > ftp * 1.5):
        return {"type": "Neuromuscular", "sub_type": "Sprint / Max Power",
                "description": f"{short_count} 个短冲刺，均功 {avg_work_power:.0f}W ({if_work}% FTP)"}

    # VO2max intervals (short/mid with high power)
    if high_z >= 20 and short_count >= 10:
        return {"type": "VO2max", "sub_type": "Short Intervals",
                "description": f"{short_count} 个短间歇 (<60s)，Z5+Z6+Z7 占 {high_z:.0f}%，均功 {avg_work_power:.0f}W"}

    if high_z >= 15 and mid_count >= 3:
        return {"type": "VO2max", "sub_type": "Long VO2max Intervals",
                "description": f"{mid_count} 个中间歇 (1-5min)，Z5+Z6 占 {z5 + z6:.0f}%，均功 {avg_work_power:.0f}W"}

    # Threshold (structured intervals)
    if threshold_z >= 20 or (mid_count >= 2 and 95 <= if_work <= 110):
        return {"type": "Threshold", "sub_type": "FTP Intervals",
                "description": f"Z4 占 {threshold_z:.0f}%，{mid_count + long_count} 个阈值间歇，均功 {avg_work_power:.0f}W ({if_work}% FTP)"}

    if long_count >= 1 and 88 <= if_work <= 105:
        return {"type": "Threshold", "sub_type": "Sustained Threshold",
                "description": f"{long_count} 个长间歇 (>5min)，均功 {avg_work_power:.0f}W ({if_work}% FTP)"}

    # Threshold (by zone distribution — covers rides without ICU interval markers)
    np_ = summary.get('icu_weighted_avg_watts', 0) or 0
    if_overall = round(np_ / ftp * 100) if ftp and np_ else 0
    if threshold_z >= 15 and if_overall >= 78:
        return {"type": "Threshold", "sub_type": "Threshold Ride",
                "description": f"Z4 占 {threshold_z:.0f}%，整体 IF {if_overall}%，NP {np_}W"}

    # Sweet Spot / Tempo
    if ss_z >= 15 or (85 <= if_work <= 95 and (mid_count + long_count) >= 2):
        return {"type": "Sweet Spot", "sub_type": "Tempo / SS",
                "description": f"Z3 占 {ss_z:.0f}%，均功 {avg_work_power:.0f}W ({if_work}% FTP)"}

    # Mixed / Race Simulation (polarized: lots of Z1 + lots of high Z)
    if low_z >= 30 and high_z >= 20:
        return {"type": "Polarized", "sub_type": "Mixed / Race Sim",
                "description": f"极化分布：Z1+Z2 {low_z:.0f}% + Z5-Z7 {high_z:.0f}%，{n_work} 个工作段"}

    # High-intensity mixed
    if high_z >= 15:
        return {"type": "High Intensity", "sub_type": "Mixed Intervals",
                "description": f"Z5+ 占 {high_z:.0f}%，{n_work} 个工作段，均功 {avg_work_power:.0f}W"}

    # Outdoor ride / unstructured
    np_ = summary.get('icu_weighted_avg_watts', 0) or 0
    if_overall = round(np_ / ftp * 100) if ftp and np_ else 0

    # 如果没有间歇数据，根据整体 IF 和区间分布推断
    if n_work == 0:
        if if_overall >= 88:
            return {"type": "Threshold", "sub_type": "Sustained Effort",
                    "description": f"无间歇标记，整体 IF {if_overall}%，NP {np_}W，Z4 占 {threshold_z:.0f}%，推断为阈值/竞速骑行"}
        if if_overall >= 75 and ss_z + threshold_z >= 15:
            return {"type": "Sweet Spot", "sub_type": "Sustained Tempo",
                    "description": f"无间歇标记，整体 IF {if_overall}%，NP {np_}W，Z3+Z4 占 {ss_z + threshold_z:.0f}%"}

    return {"type": "Unstructured", "sub_type": "General Ride",
            "description": f"无明确间歇结构，NP {np_}W，IF {if_overall}%，TSS {tss}"}


def extract_summary(filepath):
    """从单个活动详情 JSON 提取结构化摘要。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    s = data.get('summary', {})
    start_time = s.get('start_date') or s.get('start_date_local', '')

    # ── 基础信息 ──
    header = {
        "activity_id": s.get('id'),
        "name": s.get('name', '').split('\n')[0],  # 只取第一行
        "date": s.get('start_date_local', '')[:10],
        "start_time_local": s.get('start_date_local', '')[11:19],
        "type": s.get('type'),
        "duration": fmt_time(s.get('moving_time')),
        "distance_km": round(s.get('distance', 0) / 1000, 1),
        "elevation_m": s.get('total_elevation_gain'),
    }

    # ── 核心指标 ──
    ftp = s.get('icu_ftp', 288)
    np_watts = s.get('icu_weighted_avg_watts')
    avg_watts = s.get('icu_average_watts')
    intensity = round(np_watts / ftp * 100, 1) if np_watts and ftp else None

    metrics = {
        "TSS": s.get('icu_training_load'),
        "NP": np_watts,
        "AP": avg_watts,
        "IF": f"{intensity}%" if intensity else None,
        "VI": s.get('icu_variability_index'),
        "avg_hr": s.get('average_heartrate'),
        "max_hr": s.get('max_heartrate'),
        "avg_cadence": round(s.get('average_cadence', 0)),
        "calories": s.get('calories'),
        "decoupling": s.get('decoupling'),
        "EF": s.get('icu_efficiency_factor'),
        "FTP_set": ftp,
    }

    # ── 训练负荷状态 ──
    form = {
        "CTL": round(s.get('icu_ctl', 0), 1),
        "ATL": round(s.get('icu_atl', 0), 1),
        "TSB": round((s.get('icu_ctl', 0) or 0) - (s.get('icu_atl', 0) or 0), 1),
    }

    # ── 功率区间分布 ──
    zone_times = s.get('icu_zone_times', [])
    total_secs = sum(z.get('secs', 0) for z in zone_times if z.get('id') != 'SS')
    zones = []
    for z in zone_times:
        if z.get('id') == 'SS':
            continue
        secs = z.get('secs', 0)
        pct = round(secs / total_secs * 100, 1) if total_secs > 0 else 0
        zones.append({"zone": z['id'], "time": fmt_time(secs), "pct": f"{pct}%"})

    # ── ICU 间歇段 ──
    intervals = []
    for iv in data.get('icu_intervals', []):
        intervals.append({
            "type": iv.get('type'),
            "group": iv.get('group_id', ''),
            "elapsed": fmt_time(iv.get('elapsed_time')),
            "start_elapsed": fmt_time(iv.get('start_time')),
            "end_elapsed": fmt_time(iv.get('end_time')),
            "avg_watts": iv.get('average_watts'),
            "NP": iv.get('weighted_average_watts'),
            "avg_hr": iv.get('average_heartrate'),
            "max_hr": iv.get('max_heartrate'),
            "avg_cadence": iv.get('average_cadence'),
            "zone": iv.get('zone'),
        })

    # ── FIT 计圈（Garmin 手动计圈） ──
    laps = []
    for lap in data.get('laps', []):
        lap_entry = {
            "lap": lap.get('lap_number'),
            "duration": fmt_time(lap.get('duration_sec')),
            "avg_watts": lap.get('avg_watts'),
            "avg_hr": lap.get('avg_hr'),
            "avg_cadence": lap.get('avg_cadence'),
            "max_watts": lap.get('max_watts'),
        }
        # 计算相对开始时间
        ts = lap.get('timestamp_iso', '')
        elapsed = fmt_timestamp(ts, start_time)
        if elapsed:
            lap_entry["start_elapsed"] = elapsed
        laps.append(lap_entry)

    # ── 间歇段摘要（一行式） ──
    interval_summary = s.get('interval_summary', [])

    # ── 工作间歇段按组汇总（方便教练看组间衰减） ──
    work_sets = []
    rest_intervals = []
    for iv in data.get('icu_intervals', []):
        if iv.get('type') == 'WORK':
            work_sets.append({
                "time_range": f"{fmt_time(iv.get('start_time'))}–{fmt_time(iv.get('end_time'))}",
                "duration": fmt_time(iv.get('elapsed_time')),
                "avg_watts": iv.get('average_watts'),
                "avg_hr": iv.get('average_heartrate'),
                "max_hr": iv.get('max_heartrate'),
                "avg_cadence": round(iv.get('average_cadence', 0), 1),
            })
        elif iv.get('type') == 'REST':
            rest_intervals.append({
                "time_range": f"{fmt_time(iv.get('start_time'))}–{fmt_time(iv.get('end_time'))}",
                "duration": fmt_time(iv.get('elapsed_time')),
                "avg_hr": iv.get('average_heartrate'),
                "min_hr": iv.get('min_heartrate'),
            })

    # ── 自动训练分类 ──
    zone_pcts = {}
    for z in zones:
        try:
            zone_pcts[z['zone']] = float(z['pct'].rstrip('%'))
        except (ValueError, KeyError):
            pass
    classification = classify_session(s, zone_pcts, work_sets, ftp)

    result = {
        "header": header,
        "training_classification": classification,
        "metrics": metrics,
        "form": form,
        "power_zones": zones,
        "interval_summary": interval_summary,
        "work_intervals": work_sets,
        "rest_intervals": rest_intervals,
        "icu_intervals": intervals,
        "laps": laps,
    }
    return result


def find_activity_files(query=None, count=1):
    """查找活动详情文件。query 可以是活动 ID 或数量。"""
    pattern = os.path.join(DIR_DETAIL, '*.json')
    files = sorted(glob.glob(pattern))

    if query and not query.isdigit():
        # 按 activity ID 查找
        matched = [f for f in files if query in os.path.basename(f)]
        return matched[:1]

    if query and query.isdigit():
        count = int(query)

    # 按文件名排序取最新
    return files[-count:]


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else None
    count = 1
    if query and query.isdigit():
        count = int(query)
        query = None

    files = find_activity_files(query, count)
    if not files:
        print("❌ 未找到活动详情文件。")
        return

    results = []
    for f in files:
        try:
            summary = extract_summary(f)
            results.append(summary)
        except Exception as e:
            print(f"⚠️ 处理 {os.path.basename(f)} 失败: {e}", file=sys.stderr)

    # 输出 JSON（供 Gemini 读取）
    print(json.dumps(results if len(results) > 1 else results[0],
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
