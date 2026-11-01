"""列出一次骑行原始功率流里的全部发力（冲刺 / 加速）。教练做骑行分析时先跑它。

用法（从 icu/ 目录运行）:
  .venv/bin/python scripts/list_efforts.py i203196687            # 在 icu_data_warehouse/5_Activities_Detail/ 里按活动 ID 找
  .venv/bin/python scripts/list_efforts.py <详情文件.json>         # 直接给详情文件
  .venv/bin/python scripts/list_efforts.py i203196687 --json     # 机器可读

发力的次数、时长、功率只引用这里的输出：全程滚动最佳（"最好 20 秒"）和 ICU 记圈最大值都不是某一次具体发力。
判据和依据见 src/analyzer/effort_detection.py。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analyzer.effort_detection import (  # noqa: E402
    ACCELERATION,
    MAX_DIP_S,
    OFFSET_FTP_RATIO,
    ONSET_FTP_RATIOS,
    SPRINT,
    SPRINT_MIN_DURATION_S,
    SPRINT_PEAK_FTP_RATIO,
    detect_efforts,
)
from src.utils.common import setup_encoding  # noqa: E402

NOTE = "时长是整段发力，含同一段里冲刺前后的高功率，不等于本人体感的冲刺时长；冲刺最猛处看 1s 峰时刻。"


def find_detail_file(activity: str, detail_dir: Path) -> Path:
    """activity 可以是详情文件路径，也可以是活动 ID：先按文件名 *_<ID>.json 找，再按 summary.id 找旧文件。"""
    path = Path(activity)
    if path.suffix == ".json" and path.is_file():
        return path
    detail_dir = Path(detail_dir)
    named = sorted(detail_dir.glob(f"*_{activity}.json"))
    if named:
        return named[-1]
    for candidate in sorted(detail_dir.glob("*.json")):
        try:
            doc = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and (doc.get("summary") or {}).get("id") == activity:
            return candidate
    raise FileNotFoundError(f"{detail_dir} 里找不到活动 {activity} 的详情文件")


def _streams(doc: dict) -> dict:
    streams = doc.get("streams") or {}
    if isinstance(streams, list):
        streams = {s["type"]: s.get("data") for s in streams if isinstance(s, dict) and "type" in s}
    return streams


def ride_distance(streams: dict, summary: dict) -> tuple:
    """返回 (累计距离米, 来源)。没有 distance 流时用车速逐秒积分（暂停不计），再按 summary 总距离缩放。"""
    if streams.get("distance"):
        return streams["distance"], "distance 流"
    speed, time = streams.get("velocity_smooth"), streams.get("time")
    if not speed or not time or len(speed) != len(time):
        return None, None
    distance = [0.0]
    for i in range(1, len(time)):
        step = (speed[i] or 0) if time[i] - time[i - 1] == 1 else 0
        distance.append(distance[-1] + step)
    total = summary.get("distance") or summary.get("icu_distance")
    if total and distance[-1] > 0:
        distance = [d * total / distance[-1] for d in distance]
    return distance, "车速积分估算"


def _clock(start_local):
    if not start_local:
        return lambda t: None
    start = datetime.fromisoformat(start_local)
    return lambda t: (start + timedelta(seconds=t)).strftime("%H:%M:%S")


def _row(no, effort, clock) -> dict:
    return {
        "no": no,
        "kind": effort.kind,
        "start_s": effort.start_s,
        "end_s": effort.end_s,
        "start_clock": clock(effort.start_s),
        "end_clock": clock(effort.end_s),
        "duration_s": effort.duration_s,
        "avg_w": round(effort.avg_w),
        "peak_1s_w": round(effort.peak_1s_w),
        "peak_1s_clock": clock(effort.peak_1s_s),
        "peak_5s_w": None if effort.peak_5s_w is None else round(effort.peak_5s_w),
        "start_km": None if effort.start_m is None else round(effort.start_m / 1000, 2),
    }


def analyze_file(path) -> dict:
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    summary = doc.get("summary") or {}
    streams = _streams(doc)
    if not streams.get("watts"):
        raise ValueError(f"{path.name} 没有 watts 流，无法识别发力")
    ftp = summary.get("icu_ftp")
    distance, distance_source = ride_distance(streams, summary)
    efforts = detect_efforts(streams.get("time") or [], streams["watts"], ftp, distance=distance)
    clock = _clock(summary.get("start_date_local"))
    kinds = [e.kind for e in efforts]
    return {
        "activity_id": summary.get("id"),
        "file": path.name,
        "start_date_local": summary.get("start_date_local"),
        "ftp_set": ftp,
        "thresholds_w": {
            "onset": [round(r * ftp) for r in ONSET_FTP_RATIOS],
            "offset": round(OFFSET_FTP_RATIO * ftp),
            "sprint_peak": round(SPRINT_PEAK_FTP_RATIO * ftp),
        },
        "durations_s": {"max_dip": MAX_DIP_S, "sprint_min": SPRINT_MIN_DURATION_S},
        "distance_source": distance_source,
        "counts": {SPRINT: kinds.count(SPRINT), ACCELERATION: kinds.count(ACCELERATION)},
        "note": NOTE,
        "efforts": [_row(no, e, clock) for no, e in enumerate(efforts, 1)],
    }


def format_report(report: dict) -> str:
    th, du, counts = report["thresholds_w"], report["durations_s"], report["counts"]
    lines = [
        f"活动 {report['activity_id']}（{report['file']}），出发 {report['start_date_local']}，"
        f"ftp_set {report['ftp_set']}W（summary.icu_ftp）",
        f"判据：起爆连续 3 秒 ≥{'/'.join(map(str, th['onset']))}W；低于 {th['offset']}W 超过 {du['max_dip']} 秒"
        f"或记录暂停即结束；冲刺 = 1s 峰 ≥{th['sprint_peak']}W 且 ≥{du['sprint_min']} 秒，其余为加速",
        f"共 {len(report['efforts'])} 次发力：冲刺 {counts[SPRINT]} 次，加速 {counts[ACCELERATION]} 次；"
        f"起点距离：{report['distance_source'] or '无'}",
        report["note"],
        "",
        "  #  类别  开始      结束      第几分钟   时长  均功率  1s峰@时刻         5s峰   起点km",
    ]
    for r in report["efforts"]:
        p5 = "-" if r["peak_5s_w"] is None else f"{r['peak_5s_w']}W"
        km = "-" if r["start_km"] is None else f"{r['start_km']:.2f}"
        lines.append(
            f"{r['no']:>3}  {r['kind']}  {r['start_clock'] or '-':<8}  {r['end_clock'] or '-':<8}  "
            f"{r['start_s'] / 60:8.1f}  {r['duration_s']:4d}s  {r['avg_w']:5d}W  "
            f"{r['peak_1s_w']:4d}W@{r['peak_1s_clock'] or '-':<8}  {p5:>5}  {km:>6}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="列出一次骑行原始功率流里的全部发力（冲刺 / 加速）")
    parser.add_argument("activity", help="活动 ID（如 i203196687）或详情文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--detail-dir", help="详情目录，默认 <warehouse>/5_Activities_Detail")
    args = parser.parse_args(argv)

    warehouse = Path(os.getenv("OUTPUT_WAREHOUSE_DIR") or REPO / "icu_data_warehouse")
    detail_dir = Path(args.detail_dir) if args.detail_dir else warehouse / "5_Activities_Detail"
    try:
        report = analyze_file(find_detail_file(args.activity, detail_dir))
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    setup_encoding()
    sys.exit(main())
