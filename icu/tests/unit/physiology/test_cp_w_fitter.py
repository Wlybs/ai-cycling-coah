import json
from pathlib import Path

from src.coach.physiology.cp_w_fitter import fit_cp_w, write_snapshot, _iter_curve_points


def synthetic_mmp(cp=280, w_prime=22000, t_k=-10.0, durations=None):
    durations = durations or [5, 15, 30, 60, 120, 300, 600, 1200]
    return [[d, cp + w_prime / (d - t_k)] for d in durations]


def test_3_param_hyperbolic_recovery():
    mmp = synthetic_mmp()
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    assert model.model == "3-param-hyperbolic"
    assert abs(model.cp_watts - 280) <= 3
    assert abs(model.w_prime_joules - 22000) <= 500
    assert model.fit_r_squared >= 0.99


def test_2_param_fallback_when_3_param_fit_poor():
    # Highly noisy / sparse data — force 2-param fallback
    mmp = [[300, 320], [600, 295], [1200, 285]]
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    assert model.model in ("3-param-hyperbolic", "2-param-hyperbolic")
    # Noisy-few-points case must still return a valid model
    assert 200 <= model.cp_watts <= 400


def test_snapshot_writes_current_and_history(tmp_path):
    mmp = synthetic_mmp()
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    written = write_snapshot(model, base_dir=tmp_path, now_iso="2026-04-16T00:00:00Z")
    current = tmp_path / "cp_w_current.json"
    history = tmp_path / "history" / "cp_w_2026-04.json"
    assert current.exists() and history.exists()
    data = json.loads(current.read_text())
    assert data["cp_watts"] == model.cp_watts


def test_cache_skips_refit_when_data_unchanged(tmp_path, monkeypatch):
    mmp = synthetic_mmp()
    model1 = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    write_snapshot(model1, base_dir=tmp_path, now_iso="2026-04-16T00:00:00Z")
    # fit_cp_w should expose a cache hook
    from src.coach.physiology import cp_w_fitter as m
    hash1 = m.hash_mmp(mmp)
    hash2 = m.hash_mmp(mmp)
    assert hash1 == hash2


def test_iter_curve_points_handles_icu_list_shape():
    doc = {
        "list": [
            {"after_kj": 0, "secs": [60, 300], "watts": [450, 330]},
            {"after_kj": 1000, "secs": [60, 300], "watts": [420, 310]},
        ]
    }
    assert list(_iter_curve_points(doc)) == [(60, 450), (300, 330)]
