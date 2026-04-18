import json
from pathlib import Path

from src.coach.phase1_injection import inject_phase1_context


def test_no_files_returns_base_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = "BASE PROMPT"
    assert inject_phase1_context(base, base_dir=tmp_path) == base


def test_injects_cp_w_and_hints(tmp_path):
    (tmp_path / "coach_memory" / "physiology").mkdir(parents=True)
    (tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 295, "w_prime_joules": 22500, "fit_r_squared": 0.97,
        "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 7
    }))
    (tmp_path / "coach_memory" / "deep_analysis").mkdir()
    (tmp_path / "coach_memory" / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.72, "progression_flag": "progression",
        "next_plan_hints": ["下次延长恢复时长", "提高 VO2max 刺激下限"],
        "knee_flag": None,
    }))
    out = inject_phase1_context("BASE PROMPT", base_dir=tmp_path)
    assert "BASE PROMPT" in out
    assert "个人 CP 295W" in out or "CP: 295" in out
    assert "下次延长恢复时长" in out
