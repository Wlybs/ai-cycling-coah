"""Re-segment a lap's raw power stream into intensity-class sub-segments.

Use when the athlete reports a merged lap (forgot to press), a double-pressed
lap (traffic stop / red light), or a group-ride lap containing attack/draft
sub-phases. The aggregate lap metrics hide the real work; this tool slices
the stream so you can see what actually happened.

Usage:
  python scripts/segment_lap.py --activity i139065650 --lap 11
  python scripts/segment_lap.py --activity i139065650 --lap 14 --group
  python scripts/segment_lap.py --activity i139065650 --lap 10 --min-seg 20

--lap is 1-based (matches ICU UI / 码表 display; lap 1 = first interval).
--group uses attack-level thresholds (high ≥ 1.5×FTP, medium ≥ 1.0×FTP).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.common.lap_segmenter import segment_lap_by_power
from src.coach.common.icu_loader import _load_athlete


def _find_activity_file(warehouse: Path, activity_id: str) -> Path:
    for f in sorted((warehouse / "5_Activities_Detail").glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(doc, dict):
            sid = (doc.get("summary") or {}).get("id") or doc.get("id")
            if sid == activity_id:
                return f
    raise FileNotFoundError(f"No activity file found for id={activity_id}")


def main():
    p = argparse.ArgumentParser(description="Re-segment a lap by intensity class")
    p.add_argument("--activity", required=True, help="activity id, e.g. i139065650")
    p.add_argument("--lap", type=int, required=True,
                   help="1-based lap number (matches the display your athlete sees)")
    p.add_argument("--min-seg", type=int, default=10,
                   help="minimum segment length in seconds (default 10)")
    p.add_argument("--group", action="store_true",
                   help="use group-ride thresholds: high≥1.5×FTP, medium≥1.0×FTP")
    p.add_argument("--high-pct", type=float, default=None, help="override high threshold (fraction of FTP)")
    p.add_argument("--med-pct", type=float, default=None, help="override medium threshold (fraction of FTP)")
    args = p.parse_args()

    warehouse = REPO / "icu_data_warehouse"
    path = _find_activity_file(warehouse, args.activity)
    doc = json.loads(path.read_text(encoding="utf-8"))
    intervals = doc.get("icu_intervals") or []
    streams = doc.get("streams") or {}
    watts_full = streams.get("watts") or []

    idx0 = args.lap - 1
    if not (0 <= idx0 < len(intervals)):
        raise SystemExit(
            f"lap {args.lap} out of range; activity has {len(intervals)} intervals (1..{len(intervals)})"
        )
    iv = intervals[idx0]
    start = iv.get("start_index", 0) or 0
    end = iv.get("end_index", len(watts_full)) or len(watts_full)
    lap_watts = watts_full[start:end]

    ftp, _weight = _load_athlete(warehouse)

    if args.group:
        high_pct = 1.50
        med_pct = 1.00
    else:
        high_pct = 0.90
        med_pct = 0.60
    if args.high_pct is not None:
        high_pct = args.high_pct
    if args.med_pct is not None:
        med_pct = args.med_pct

    segments = segment_lap_by_power(
        lap_watts,
        ftp=ftp,
        min_segment_s=args.min_seg,
        high_pct=high_pct,
        med_pct=med_pct,
    )

    print(json.dumps({
        "activity": args.activity,
        "lap_number": args.lap,
        "lap_total_samples": len(lap_watts),
        "ftp": ftp,
        "thresholds": {"high_pct": high_pct, "med_pct": med_pct},
        "segments": segments,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
