import json
from pathlib import Path

from src.coach.physiology.refresher import refresh_all


def _seed_warehouse(base: Path):
    pd = base / "icu_data_warehouse" / "3_PowerData"
    pd.mkdir(parents=True)
    (pd / "power_curves_90d.json").write_text(json.dumps({
        "secs": [5, 30, 60, 300, 600, 1200],
        "watts": [1200, 780, 540, 340, 305, 290],
    }))
    (pd / "power_curves_all_time.json").write_text(json.dumps({
        "secs": [5, 30, 60, 300, 600, 1200],
        "watts": [1389, 850, 600, 360, 315, 295],
    }))
    profile = base / "icu_data_warehouse" / "1_Profile"
    profile.mkdir(parents=True)
    (profile / "athlete.json").write_text(json.dumps({
        "weight": 62, "ftp": 288, "hr_max": 195,
    }))


def test_refresh_all_writes_cp_w_snapshot_minimal(tmp_path):
    _seed_warehouse(tmp_path)
    result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[],
        wellness_by_date={},
    )
    assert result["cp_w"]["status"] == "ok"
    assert (tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").exists()


def test_refresh_all_partial_failure_continues(tmp_path):
    _seed_warehouse(tmp_path)

    # Break durability by passing ride with no power_stream key
    result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[{"id": "bad"}],  # missing power_stream -> skipped not crash
        wellness_by_date={},
    )
    # cp_w still OK even if durability is empty
    assert result["cp_w"]["status"] == "ok"
    assert result["durability"]["status"] in ("ok", "empty")
