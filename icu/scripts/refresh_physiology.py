"""Standalone physiology refresher. Called by sync_data.py or directly for debugging."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.physiology.refresher import refresh_all


def _load_activities(warehouse):
    out = []
    detail_dir = warehouse / "5_Activities_Detail"
    if not detail_dir.exists():
        return out
    for f in sorted(detail_dir.glob("*/activity.json")):
        try:
            doc = json.loads(f.read_text())
            streams_file = f.parent / "streams.json"
            if streams_file.exists():
                streams = json.loads(streams_file.read_text())
                doc["power_stream"] = streams.get("watts") or streams.get("power") or []
            out.append(doc)
        except Exception as exc:
            print(f"skip {f}: {exc}", file=sys.stderr)
    return out


def _load_wellness(warehouse):
    out = {}
    w = warehouse / "2_Wellness"
    if not w.exists():
        return out
    for f in w.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict) and "date" in d:
                out[d["date"]] = d
            elif isinstance(d, list):
                for rec in d:
                    out[rec.get("id") or rec.get("date")] = rec
        except Exception:
            pass
    return out


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    activities = _load_activities(warehouse)
    wellness = _load_wellness(warehouse)
    result = refresh_all(warehouse, memory, activities, wellness)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
