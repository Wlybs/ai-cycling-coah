"""Runs deep analysis for newly synced activities. Called by sync_data.py."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.common.icu_loader import load_activity_doc
from src.coach.deep_analyzer.orchestrator import analyze_new


def _load_activity_list(warehouse):
    path = warehouse / "4_Activities_List" / "activities.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _wbal_from_streams(streams, physiology_bundle):
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


def _streams_loader(warehouse):
    def loader(activity_id):
        try:
            _, streams = load_activity_doc(warehouse, activity_id)
            return streams
        except FileNotFoundError:
            return None
    return loader


def _wbal_loader(warehouse, physiology_bundle):
    def loader(activity_id):
        try:
            _, streams = load_activity_doc(warehouse, activity_id)
        except FileNotFoundError:
            return None
        return _wbal_from_streams(streams, physiology_bundle)
    return loader


def _load_physiology(memory):
    phys_dir = memory / "physiology"
    bundle = {"cp_w": None, "durability": None, "response": None}
    for key, fname in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = phys_dir / fname
        if p.exists():
            bundle[key] = json.loads(p.read_text())
    return bundle


def _make_client():
    load_dotenv(REPO / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    output_dir = memory / "deep_analysis"
    client = _make_client()
    athlete_path = warehouse / "1_Profile" / "athlete_profile.json"
    if not athlete_path.exists():
        athlete_path = warehouse / "1_Profile" / "athlete.json"
    athlete = json.loads(athlete_path.read_text()) if athlete_path.exists() else {}
    activities = _load_activity_list(warehouse)
    physiology = _load_physiology(memory)

    results = analyze_new(
        activities_iter=activities,
        physiology_bundle=physiology,
        athlete=athlete,
        output_dir=output_dir,
        client=client,
        load_streams=_streams_loader(warehouse),
        load_wbal=_wbal_loader(warehouse, physiology),
        history_for=lambda act: [a for a in activities if a.get("id") != act["id"]][:20],
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
