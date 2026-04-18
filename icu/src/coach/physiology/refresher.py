import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..common.logging import get_logger
from . import cp_w_fitter, durability_model, response_profile

LOG = get_logger("physiology_refresher")


def _load_athlete(warehouse_dir: Path) -> dict:
    """Load athlete profile, tolerating either real (athlete_profile.json) or
    legacy-synthetic (athlete.json) filename, and ICU-style key names."""
    defaults = {"ftp": 288, "hr_max": 195, "weight": 62}
    for name in ("athlete_profile.json", "athlete.json"):
        path = warehouse_dir / "1_Profile" / name
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        return {
            "ftp": int(raw.get("ftp") or raw.get("icu_ftp") or defaults["ftp"]),
            "hr_max": int(raw.get("hr_max") or raw.get("icu_hr_max") or defaults["hr_max"]),
            "weight": float(raw.get("weight") or raw.get("icu_weight") or defaults["weight"]),
        }
    return defaults


def _safe(name: str, fn):
    t0 = time.monotonic()
    try:
        fn()
        LOG.event(
            action=f"refresh_{name}",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="ok",
        )
        return {"status": "ok"}
    except Exception as e:
        LOG.event(
            action=f"refresh_{name}",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="error",
            error=str(e),
        )
        return {"status": "error", "error": str(e)}


def refresh_all(
    warehouse_dir: Path,
    memory_dir: Path,
    activities: Iterable[dict],
    wellness_by_date: dict,
) -> dict:
    warehouse_dir = Path(warehouse_dir)
    memory_dir = Path(memory_dir)
    physiology_dir = memory_dir / "physiology"
    physiology_dir.mkdir(parents=True, exist_ok=True)
    athlete = _load_athlete(warehouse_dir)
    ftp = int(athlete.get("ftp") or 288)

    # Materialise once so multiple consumers can iterate
    activities_list = list(activities)

    result: dict = {}

    def fit_cp():
        mmp = cp_w_fitter.load_mmp_from_warehouse(warehouse_dir)
        if not mmp:
            raise RuntimeError("no MMP data available")
        model = cp_w_fitter.fit_cp_w(mmp, athlete_ftp=ftp, window_days=90)
        cp_w_fitter.write_snapshot(
            model, physiology_dir, now_iso=datetime.now(timezone.utc).isoformat()
        )

    result["cp_w"] = _safe("cp_w", fit_cp)

    def fit_dur():
        rides = [a for a in activities_list if "power_stream" in a]
        curve = durability_model.fit_durability(rides)
        (physiology_dir / "durability.json").write_text(
            curve.model_dump_json(indent=2)
        )

    result["durability"] = _safe("durability", fit_dur)
    if not activities_list:
        result["durability"] = {"status": "empty"}

    def fit_resp():
        prof = response_profile.build_profile(
            sessions=activities_list,
            wellness_by_date=wellness_by_date,
            window_days=60,
        )
        (physiology_dir / "response_profile.json").write_text(
            prof.model_dump_json(indent=2)
        )

    result["response"] = _safe("response_profile", fit_resp)
    return result
