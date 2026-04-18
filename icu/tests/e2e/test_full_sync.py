import json
from pathlib import Path

import pytest

from src.coach.physiology.refresher import refresh_all
from src.coach.deep_analyzer.orchestrator import analyze_new

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "rides"


def _seed_warehouse(base: Path):
    (base / "icu_data_warehouse" / "3_PowerData").mkdir(parents=True)
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_90d.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1200, 780, 560, 450, 340, 310, 290],
    }))
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_all_time.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1389, 850, 600, 480, 360, 320, 295],
    }))
    (base / "icu_data_warehouse" / "1_Profile").mkdir(parents=True)
    (base / "icu_data_warehouse" / "1_Profile" / "athlete.json").write_text(json.dumps({
        "weight": 62, "ftp": 288, "hr_max": 195,
    }))


@pytest.mark.e2e
def test_full_phase1_pipeline_api_free(tmp_path):
    """API-free pipeline: refresh physiology → analyze_new writes prompt+trace+summary.
    No GEMINI_API_KEY needed; no LLM client involved.
    """
    _seed_warehouse(tmp_path)
    activity = json.loads((FIXTURE_DIR / "interval_ride_synthetic.json").read_text())

    refresh_result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[{**activity, "power_stream": [300] * 3600}],
        wellness_by_date={},
    )
    assert refresh_result["cp_w"]["status"] == "ok"

    physiology_bundle = {
        "cp_w": json.loads((tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").read_text()),
        "durability": json.loads((tmp_path / "coach_memory" / "physiology" / "durability.json").read_text()),
        "response": None,
    }

    out_dir = tmp_path / "coach_memory" / "deep_analysis"
    results = analyze_new(
        activities_iter=[activity],
        physiology_bundle=physiology_bundle,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "ACL post-op"},
        output_dir=out_dir,
    )

    assert results[0]["status"] == "ok"
    # New contract (Phase 1.11): prompt file replaces Gemini-generated .md
    assert (out_dir / "iE2E1.prompt.md").exists()
    assert (out_dir / "iE2E1.trace.json").exists()
    assert (out_dir / "summary_latest.json").exists()
    assert (out_dir / "_state.json").exists()
    # Legacy artifact must NOT be produced
    assert not (out_dir / "iE2E1.md").exists()

    prompt_text = (out_dir / "iE2E1.prompt.md").read_text(encoding="utf-8")
    assert '"activity_id": "iE2E1"' in prompt_text
