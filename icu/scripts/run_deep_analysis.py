"""Runs deep analysis for newly synced activities. Called by sync_data.py."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.deep_analyzer.orchestrator import analyze_new


def _load_activity_list(warehouse):
    path = warehouse / "4_Activities_List" / "activities.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _load_streams_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / activity_id / "streams.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
    return loader


def _load_wbal_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / f"{activity_id}_wbalance.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
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
        load_streams=_load_streams_for(warehouse),
        load_wbal=_load_wbal_for(warehouse),
        history_for=lambda act: [a for a in activities if a.get("id") != act["id"]][:20],
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
