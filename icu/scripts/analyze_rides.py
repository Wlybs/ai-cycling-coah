"""CLI for deep analyzer — single activity, dry-run, replay, or backfill.

API-free: produces `<id>.prompt.md` + `<id>.trace.json` + `summary_latest.json`
under `coach_memory/deep_analysis/`. The user pastes `<id>.prompt.md` into
Gemini CLI / Claude Code coach mode to obtain the narrative report.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.common.icu_loader import load_activity_doc
from src.coach.deep_analyzer.feature_detector import detect_features
from src.coach.deep_analyzer.router import route
from src.coach.deep_analyzer.orchestrator import analyze_one


def _wbal_payload_from_streams(streams, physiology_bundle):
    """Wrap streams['w_bal'] into the dict shape sub-analyzers expect.
    Returns None if no w_bal available."""
    if not streams:
        return None
    series = streams.get("w_bal") or []
    if not series:
        return None
    wp = None
    cp_w = physiology_bundle.get("cp_w") if physiology_bundle else None
    if isinstance(cp_w, dict):
        wp = cp_w.get("w_prime_joules")
    out = {"series": list(series)}
    if wp:
        try:
            out["min_w_bal_pct"] = min(series) / float(wp) * 100.0
        except Exception:
            pass
    return out


def _load_physiology(memory: Path):
    pd = memory / "physiology"
    bundle = {"cp_w": None, "durability": None, "response": None}
    for k, name in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = pd / name
        if p.exists():
            bundle[k] = json.loads(p.read_text())
    return bundle


def main():
    parser = argparse.ArgumentParser(description="Deep analyzer CLI (API-free)")
    parser.add_argument("--activity", help="single activity id")
    parser.add_argument("--dry-run", action="store_true", help="print features + relevance + activated to stdout without writing files")
    parser.add_argument("--replay", action="store_true", help="re-analyze and overwrite")
    parser.add_argument("--backfill", action="store_true", help="run on all interval/race/climb activities")
    parser.add_argument("--since", help="ISO date for --backfill filter")
    args = parser.parse_args()

    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    output = memory / "deep_analysis"
    output.mkdir(parents=True, exist_ok=True)

    if not args.activity and not args.backfill:
        parser.error("one of --activity or --backfill is required")

    physiology = _load_physiology(memory)
    athlete_path = warehouse / "1_Profile" / "athlete_profile.json"
    if not athlete_path.exists():
        athlete_path = warehouse / "1_Profile" / "athlete.json"
    athlete = json.loads(athlete_path.read_text()) if athlete_path.exists() else {}

    if args.dry_run and args.activity:
        activity, streams = load_activity_doc(warehouse, args.activity)
        phys_flat = dict((physiology.get("cp_w") or {}))
        features = detect_features(activity, streams, phys_flat, athlete)
        rel = route(features)
        print(json.dumps({
            "features": features.model_dump(),
            "relevance": rel,
            "activated": [k for k, v in rel.items() if v >= 0.5],
        }, ensure_ascii=False, indent=2))
        return

    if args.activity:
        activity, streams = load_activity_doc(warehouse, args.activity)
        wbal = _wbal_payload_from_streams(streams, physiology)
        result = analyze_one(
            activity=activity, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # backfill: iterate activity list; load details via adapter
    list_path = warehouse / "4_Activities_List" / "activities.json"
    activities_raw = json.loads(list_path.read_text()) if list_path.exists() else []
    if args.since:
        activities_raw = [a for a in activities_raw if (a.get("start_date_local") or a.get("date") or "") >= args.since]
    for raw in activities_raw:
        aid = raw.get("id")
        if not aid:
            continue
        try:
            activity, streams = load_activity_doc(warehouse, aid)
        except FileNotFoundError:
            continue
        features = detect_features(activity, streams, dict(physiology.get("cp_w") or {}), athlete)
        if not (features.has_intervals or features.is_race or features.has_climbing):
            continue
        wbal = _wbal_payload_from_streams(streams, physiology)
        analyze_one(
            activity=activity, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output,
        )


if __name__ == "__main__":
    main()
