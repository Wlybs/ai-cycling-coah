"""Tests for the ICU warehouse adapter layer.

Written against the real ICU shapes discovered in icu_data_warehouse/.
"""
import json
from pathlib import Path

import pytest

from src.coach.common import icu_loader


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def _minimal_profile(tmp_path: Path, ftp: int = 300, weight: float = 62.0) -> None:
    _write(
        tmp_path / "1_Profile" / "athlete_profile.json",
        {"icu_ftp": ftp, "icu_weight": weight, "weight": weight},
    )


def test_normalize_summary_maps_key_renames():
    summary = {
        "id": "iTEST",
        "start_date_local": "2026-04-12T08:00:00",
        "moving_time": 3600,
        "icu_weighted_avg_watts": 250,
        "icu_training_load": 90,
        "icu_intensity": 85.0,
        "icu_joules": 900000,
        "max_heartrate": 180,
        "total_elevation_gain": 500.0,
        "decoupling": 3.5,
        "average_temp": 20.0,
        "icu_intervals_type": "vo2max",
    }
    out = icu_loader.normalize_summary(summary, athlete_ftp=300, athlete_weight_kg=62)
    assert out["id"] == "iTEST"
    assert out["duration_s"] == 3600
    assert out["np_watts"] == 250
    assert out["tss"] == 90
    assert out["if"] == pytest.approx(0.85, rel=1e-3)
    assert out["total_kj"] == 900
    assert out["max_hr"] == 180
    assert out["elevation_gain_m"] == 500.0
    assert out["decoupling_pct"] == 3.5
    assert out["avg_temperature_c"] == 20.0
    assert out["date"] == "2026-04-12"
    assert out["type"] == "vo2max"
    assert out["weight_kg"] == 62


def test_normalize_summary_defaults_when_missing():
    summary = {"id": "iX", "start_date_local": "2026-04-01T07:00:00"}
    out = icu_loader.normalize_summary(summary, athlete_ftp=300, athlete_weight_kg=62)
    assert out["type"] == "ride"
    assert out["planned_type"] is None
    assert out["hr_drift_z2_bpm"] is None
    assert out["id"] == "iX"


def test_normalize_summary_if_divides_by_100():
    summary = {
        "id": "iY",
        "start_date_local": "2026-04-02T07:00:00",
        "icu_intensity": 80.666664,
    }
    out = icu_loader.normalize_summary(summary, athlete_ftp=300, athlete_weight_kg=62)
    assert out["if"] == pytest.approx(0.807, rel=1e-3)


def test_normalize_streams_renames_keys():
    streams = {
        "watts": [100, 200],
        "heartrate": [120, 130],
        "altitude": [10, 11],
        "cadence": [80, 85],
        "time": [0, 1],
        "velocity_smooth": [5, 6],
    }
    out = icu_loader.normalize_streams(streams)
    assert out["power"] == [100, 200]
    assert out["hr"] == [120, 130]
    assert out["cadence"] == [80, 85]
    assert out["altitude"] == [10, 11]
    assert out["time"] == [0, 1]
    assert "gradient" in out
    assert len(out["gradient"]) == 2
    assert out["gradient"][0] == 0


def test_normalize_laps_prefers_icu_intervals():
    icu_intervals = [
        {
            "type": "WORK",
            "moving_time": 240,
            "average_watts": 320,
            "weighted_average_watts": 325,
            "number": 1,
        }
    ]
    fit_laps = [
        {"lap_number": 0, "duration_sec": 999, "avg_watts": 999}
    ]
    out = icu_loader.normalize_laps(icu_intervals, fit_laps, ftp=300)
    assert len(out) == 1
    lap = out[0]
    assert lap["type"] == "work"
    assert lap["duration_s"] == 240
    assert lap["avg_power"] == 320
    assert lap["lap_index"] == 1
    assert lap["if"] == pytest.approx(320 / 300, rel=1e-3)


def test_normalize_laps_falls_back_to_fit_laps():
    out = icu_loader.normalize_laps(
        [],
        [{"lap_number": 0, "duration_sec": 300, "avg_watts": 200}],
        ftp=300,
    )
    assert len(out) == 1
    assert out[0]["type"] == "ride"
    assert out[0]["duration_s"] == 300
    assert out[0]["avg_power"] == 200


def test_load_activity_doc_nested_file(tmp_path: Path):
    _minimal_profile(tmp_path)
    nested = {
        "summary": {
            "id": "iX",
            "start_date_local": "2026-04-12T08:00:00",
            "icu_ftp": 300,
        },
        "streams": {"watts": [100], "heartrate": [120], "altitude": [0],
                    "cadence": [80], "time": [0], "velocity_smooth": [5]},
        "laps": [],
        "icu_intervals": [],
    }
    _write(tmp_path / "5_Activities_Detail" / "2026-04-12_iX.json", nested)
    activity, streams = icu_loader.load_activity_doc(tmp_path, "iX")
    assert activity["id"] == "iX"
    assert streams is not None
    assert streams["power"] == [100]


def test_load_activity_doc_flat_file_returns_none_streams(tmp_path: Path):
    _minimal_profile(tmp_path)
    flat = {"id": "iFLAT", "start_date_local": "2026-01-01T08:00:00", "icu_pm_cp": 270}
    _write(tmp_path / "5_Activities_Detail" / "2026-01-01_iFLAT.json", flat)
    activity, streams = icu_loader.load_activity_doc(tmp_path, "iFLAT")
    assert activity["id"] == "iFLAT"
    assert streams is None


def test_load_activity_doc_matches_by_id_substring(tmp_path: Path):
    _minimal_profile(tmp_path)
    nested = {
        "summary": {"id": "i117802086", "start_date_local": "2026-01-14T08:00:00"},
        "streams": {"watts": [100], "heartrate": [120], "altitude": [0],
                    "cadence": [80], "time": [0], "velocity_smooth": [5]},
        "laps": [], "icu_intervals": [],
    }
    path = tmp_path / "5_Activities_Detail" / "2026-01-14_和俩武功尽失的康复骑_FULL.json"
    _write(path, nested)
    activity, streams = icu_loader.load_activity_doc(tmp_path, "i117802086")
    assert activity["id"] == "i117802086"
    assert streams is not None


def test_iter_activity_docs_skips_flat(tmp_path: Path):
    _minimal_profile(tmp_path)
    for i in (1, 2):
        _write(
            tmp_path / "5_Activities_Detail" / f"2026-04-0{i}_iN{i}.json",
            {
                "summary": {"id": f"iN{i}", "start_date_local": f"2026-04-0{i}T08:00:00"},
                "streams": {"watts": [i], "heartrate": [i], "altitude": [0],
                            "cadence": [0], "time": [0], "velocity_smooth": [1]},
                "laps": [], "icu_intervals": [],
            },
        )
    _write(
        tmp_path / "5_Activities_Detail" / "2026-03-01_iFLAT.json",
        {"id": "iFLAT", "start_date_local": "2026-03-01T08:00:00", "icu_pm_cp": 270},
    )
    yielded = list(icu_loader.iter_activity_docs(tmp_path))
    assert len(yielded) == 2
    ids = sorted(a["id"] for a, _ in yielded)
    assert ids == ["iN1", "iN2"]


def test_load_events_by_date_empty_ok(tmp_path: Path):
    out = icu_loader.load_events_by_date(tmp_path)
    assert out == {}
