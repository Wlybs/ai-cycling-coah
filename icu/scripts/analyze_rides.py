"""CLI for deep analyzer — single activity, dry-run, replay, or backfill."""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.deep_analyzer.feature_detector import detect_features
from src.coach.deep_analyzer.router import route
from src.coach.deep_analyzer.orchestrator import analyze_one


def _load_activity(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / activity_id / "activity.json"
    if not f.exists():
        raise FileNotFoundError(f)
    return json.loads(f.read_text())


def _load_streams(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / activity_id / "streams.json"
    return json.loads(f.read_text()) if f.exists() else None


def _load_wbal(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / f"{activity_id}_wbalance.json"
    return json.loads(f.read_text()) if f.exists() else None


def _load_physiology(memory: Path):
    pd = memory / "physiology"
    bundle = {"cp_w": None, "durability": None, "response": None}
    for k, name in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = pd / name
        if p.exists():
            bundle[k] = json.loads(p.read_text())
    return bundle


def _make_client():
    load_dotenv(REPO / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def main():
    parser = argparse.ArgumentParser(description="Deep analyzer CLI")
    parser.add_argument("--activity", help="single activity id")
    parser.add_argument("--dry-run", action="store_true", help="skip Gemini; print features + relevance + findings")
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
    athlete_path = warehouse / "1_Profile" / "athlete.json"
    athlete = json.loads(athlete_path.read_text()) if athlete_path.exists() else {}

    if args.dry_run and args.activity:
        activity = _load_activity(warehouse, args.activity)
        streams = _load_streams(warehouse, args.activity)
        phys_flat = dict((physiology.get("cp_w") or {}))
        features = detect_features(activity, streams, phys_flat, athlete)
        rel = route(features)
        print(json.dumps({
            "features": features.model_dump(),
            "relevance": rel,
            "activated": [k for k, v in rel.items() if v >= 0.5],
        }, ensure_ascii=False, indent=2))
        return

    client = _make_client()
    if args.activity:
        activity = _load_activity(warehouse, args.activity)
        streams = _load_streams(warehouse, args.activity)
        wbal = _load_wbal(warehouse, args.activity)
        result = analyze_one(
            activity=activity, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output, client=client,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    list_path = warehouse / "4_Activities_List" / "activities.json"
    activities = json.loads(list_path.read_text()) if list_path.exists() else []
    if args.since:
        activities = [a for a in activities if (a.get("date") or "") >= args.since]
    for a in activities:
        features = detect_features(a, None, dict(physiology.get("cp_w") or {}), athlete)
        if not (features.has_intervals or features.is_race or features.has_climbing):
            continue
        streams = _load_streams(warehouse, a["id"])
        wbal = _load_wbal(warehouse, a["id"])
        analyze_one(
            activity=a, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output, client=client,
        )


if __name__ == "__main__":
    main()
