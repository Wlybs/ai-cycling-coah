"""
只读核对：按新规则（FIT lap 起始时间 → streams.time）重算仓库里已有活动的 lap 均功率，
与 FIT avg_watts 及文件里旧的 stream_start_index 结果对比（bd Cycling-vje）。不改任何文件。

用法:
  python scripts/verify_lap_alignment.py
  python scripts/verify_lap_alignment.py --detail-dir D:/Cycling/icu/icu_data_warehouse/5_Activities_Detail
  python scripts/verify_lap_alignment.py --min-lap-sec 120 --threshold 15 --out result.json
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.analyzer.lap_alignment import lap_stream_window

DEFAULT_DETAIL_DIR = os.path.join(
    os.getenv("OUTPUT_WAREHOUSE_DIR", "./icu_data_warehouse"), "5_Activities_Detail"
)


def normalize_streams(streams):
    if isinstance(streams, list):
        return {s.get('type'): s.get('data') for s in streams if isinstance(s, dict)}
    return streams or {}


def mean_watts(watts, start, end):
    if start is None or end is None:
        return None
    vals = [w for w in watts[start:end] if w is not None]
    return sum(vals) / len(vals) if vals else None


def check_file(path, min_lap_sec):
    with open(path, encoding='utf-8') as f:
        doc = json.load(f)
    streams = normalize_streams(doc.get('streams'))
    time, watts = streams.get('time') or [], streams.get('watts') or []
    start_utc = (doc.get('summary') or {}).get('start_date')
    rows = []
    if not time or not watts or len(time) != len(watts):
        return rows, "no usable time/watts stream"
    for lap in doc.get('laps') or []:
        dur, fit_w = lap.get('duration_sec'), lap.get('avg_watts')
        if dur is None or dur < min_lap_sec or fit_w is None:
            continue
        window = lap_stream_window(lap.get('timestamp_iso'), dur, start_utc, time)
        old = mean_watts(watts, lap.get('stream_start_index'), lap.get('stream_end_index'))
        new = mean_watts(watts, *window) if window else None
        rows.append({
            "file": os.path.basename(path),
            "lap": lap.get('lap_number'),
            "duration_sec": dur,
            "fit_avg_w": fit_w,
            "old_mean_w": round(old, 1) if old is not None else None,
            "new_mean_w": round(new, 1) if new is not None else None,
            "old_diff_w": round(old - fit_w, 1) if old is not None else None,
            "new_diff_w": round(new - fit_w, 1) if new is not None else None,
        })
    return rows, None


def summarize(rows, threshold):
    def bad(key):
        return sum(1 for r in rows if r[key] is None or abs(r[key]) > threshold)

    new_abs = sorted(abs(r['new_diff_w']) for r in rows if r['new_diff_w'] is not None)
    return {
        "laps_checked": len(rows),
        "files_with_laps": len({r['file'] for r in rows}),
        f"old_rule_off_gt_{threshold}w_or_empty": bad('old_diff_w'),
        f"new_rule_off_gt_{threshold}w_or_empty": bad('new_diff_w'),
        "new_rule_empty_window": sum(1 for r in rows if r['new_diff_w'] is None),
        "new_rule_median_abs_diff_w": new_abs[len(new_abs) // 2] if new_abs else None,
        "new_rule_max_abs_diff_w": new_abs[-1] if new_abs else None,
    }


def main():
    parser = argparse.ArgumentParser(description="只读核对 lap 与 streams 的对齐")
    parser.add_argument('--detail-dir', default=DEFAULT_DETAIL_DIR)
    parser.add_argument('--min-lap-sec', type=float, default=120)
    parser.add_argument('--threshold', type=float, default=15)
    parser.add_argument('--out', help="把逐 lap 结果写成 JSON（可选）")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.detail_dir, '*.json')))
    if not files:
        print(f"❌ 没找到详情文件: {args.detail_dir}")
        sys.exit(1)

    rows, skipped = [], {}
    for path in files:
        file_rows, reason = check_file(path, args.min_lap_sec)
        if reason:
            skipped[os.path.basename(path)] = reason
        rows.extend(file_rows)

    summary = summarize(rows, args.threshold)
    summary["files_total"] = len(files)
    summary["files_skipped"] = len(skipped)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    worst = sorted((r for r in rows if r['new_diff_w'] is None or abs(r['new_diff_w']) > args.threshold),
                   key=lambda r: -abs(r['new_diff_w'] or 1e9))
    for r in worst[:20]:
        print(f"  新规则仍偏差: {r['file']} lap{r['lap']} {r['duration_sec']}s "
              f"FIT {r['fit_avg_w']}W / 新 {r['new_mean_w']}W / 旧 {r['old_mean_w']}W")

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({"summary": summary, "skipped": skipped, "laps": rows}, f, ensure_ascii=False, indent=2)
        print(f"✅ 逐 lap 结果: {args.out}")


if __name__ == "__main__":
    main()
