import json
from pathlib import Path

from src.coach.brief_updater import update_brief, BEGIN, END


def test_inserts_block_between_markers(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(f"intro\n{BEGIN}\nold\n{END}\ntail\n")

    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.55, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": "watch",
    }))
    (mem / "physiology").mkdir()
    (mem / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 292, "w_prime_joules": 21800, "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 4,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    content = gemini.read_text()
    assert "intro" in content and "tail" in content
    assert "起步冒进" in content
    assert "CP 292" in content or "CP: 292" in content
    assert content.count(BEGIN) == 1 and content.count(END) == 1


def test_appends_markers_if_absent(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text("no markers yet\n")
    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": [], "headline_verdict": "x",
        "stimulus_score": 0.5, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": None,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    c = gemini.read_text()
    assert BEGIN in c and END in c
