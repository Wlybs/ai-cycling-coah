"""Unit tests for scripts.run_consensus."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_consensus import main as run_main


def _verdict_request_payload() -> dict:
    return {
        "plan": {
            "week_start": "2026-04-20",
            "week_end": "2026-04-26",
            "focus_theme": "BUILD",
            "weekly_tss_target": 525,
            "days": [
                {"day_of_week": d, "training_type": "Endurance",
                 "name": "Z2", "duration_min": 60, "target_tss": 50,
                 "power_range_w": "150-180W", "tier": "MID"}
                for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            ],
            "recent_stimulus_scores": [0.55, 0.55, 0.55],
            "recent_w_prime_negatives": [3, 3, 3],
        },
        "athlete_state": {
            "ctl": 70.0, "atl": 68.0, "tsb": 2.0,
            "w_prime": 14_500,
            "phase": "BUILD", "week_of_year": 17,
        },
        "physiology": {"cp_w": 285, "w_prime_j": 14_500,
                       "durability_index": 0.74,
                       "response_profile": {"types": {}},
                       "knee_flag": "OK"},
        "wellness_trend": [],
        "periodization_summary": {"phase": "BUILD",
                                  "weekly_tss_target": 525},
    }


def _history_payload() -> list[dict]:
    return [
        {
            "plan_entry_id": "01HZZZ" + "0" * 20,
            "context": {"phase": "BUILD", "total_tss": 520, "ctl": 70.0,
                        "week_of_year": 14,
                        "plan_period": "2026-04-06_2026-04-12"},
            "verdict": "ACCEPT",
            "outcome": "consensus.ACCEPT@0.82",
        },
    ]


# ---------- happy path ----------

class TestRunConsensusHappyPath:

    def test_writes_prompt_with_no_history(self, tmp_path, capsys):
        req_path = tmp_path / "req.json"
        out_path = tmp_path / "council.prompt.md"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")

        rc = run_main([
            "--verdict-request", str(req_path),
            "--out", str(out_path),
        ])

        assert rc == 0
        body = out_path.read_text(encoding="utf-8")
        assert "## Section A" in body
        assert "## Section D" in body
        assert "(no historical context)" in body
        assert "<summary_json>" in body
        out = capsys.readouterr().out
        assert "council.prompt.md" in out
        assert "finalize_consensus" in out

    def test_writes_prompt_with_history(self, tmp_path):
        req_path = tmp_path / "req.json"
        hist_path = tmp_path / "hist.json"
        out_path = tmp_path / "council.prompt.md"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        hist_path.write_text(json.dumps(_history_payload()),
                             encoding="utf-8")

        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(hist_path),
            "--out", str(out_path),
        ])
        assert rc == 0
        body = out_path.read_text(encoding="utf-8")
        assert "01HZZZ" in body
        assert "(no historical context)" not in body

    def test_default_out_is_council_prompt_md(self, tmp_path,
                                              monkeypatch):
        req_path = tmp_path / "req.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = run_main([
            "--verdict-request", str(req_path),
        ])
        assert rc == 0
        assert (tmp_path / "council.prompt.md").exists()


# ---------- error paths ----------

class TestRunConsensusErrors:

    def test_missing_verdict_request_file_exit_2(self, tmp_path, capsys):
        out_path = tmp_path / "out.md"
        rc = run_main([
            "--verdict-request", str(tmp_path / "absent.json"),
            "--out", str(out_path),
        ])
        assert rc == 2
        err = capsys.readouterr().err
        assert "verdict-request" in err.lower() or "absent.json" in err
        assert not out_path.exists()

    def test_malformed_verdict_request_exit_2(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        out_path = tmp_path / "out.md"
        rc = run_main([
            "--verdict-request", str(bad),
            "--out", str(out_path),
        ])
        assert rc == 2
        assert not out_path.exists()

    def test_missing_history_file_exit_2(self, tmp_path):
        req_path = tmp_path / "req.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        out_path = tmp_path / "out.md"
        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(tmp_path / "absent_history.json"),
            "--out", str(out_path),
        ])
        assert rc == 2
        assert not out_path.exists()

    def test_history_payload_must_be_list(self, tmp_path):
        req_path = tmp_path / "req.json"
        hist_path = tmp_path / "hist.json"
        req_path.write_text(json.dumps(_verdict_request_payload()),
                            encoding="utf-8")
        hist_path.write_text(json.dumps({"not": "a list"}),
                             encoding="utf-8")
        out_path = tmp_path / "out.md"
        rc = run_main([
            "--verdict-request", str(req_path),
            "--history", str(hist_path),
            "--out", str(out_path),
        ])
        assert rc == 2
        assert not out_path.exists()


# ---------- API_FREE invariant ----------

class TestApiFreeInvariant:

    def test_no_llm_sdk_imported(self):
        text = Path("scripts/run_consensus.py").read_text(encoding="utf-8")
        forbidden = ("google.genai", "from google import genai",
                     "import requests", "import urllib", "import httpx")
        for needle in forbidden:
            assert needle not in text, (
                f"run_consensus.py must remain API_FREE; found {needle!r}")


# ============================================================
# T67.3 — strict mode + --reuse
# ============================================================

import json
from pathlib import Path

import pytest


_BASE_REQUEST = {
    "plan": {
        "plan_period": "2026-W17",
        "weekly_tss_target": 380,
        "days": [
            {"day": "Mon", "training_type": "Endurance",
             "duration_min": 90, "tier": "MEDIUM"},
            {"day": "Wed", "training_type": "VO2max",
             "duration_min": 75, "tier": "HIGH"},
        ],
    },
    "athlete_state": {
        "ctl": 68.0, "atl": 72.0, "tsb": -4.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    },
    "physiology": {"cp_watts": 288, "w_prime_joules": 18000},
    "wellness_trend": [],
    "periodization_summary": {"phase": "BUILD"},
}


def _write_request(dir_: Path) -> Path:
    p = dir_ / "verdict_request.json"
    p.write_text(json.dumps(_BASE_REQUEST, indent=2,
                            sort_keys=True, ensure_ascii=False),
                 encoding="utf-8")
    return p


def test_strict_mode_emits_1_planner_prompt(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out_dir = tmp_path / "consensus_2026-04-27_1200"
    rc = main([
        "--mode", "strict",
        "--verdict-request", str(req),
        "--out", str(out_dir / "1_planner.prompt.md"),
    ])
    assert rc == 0
    written = out_dir / "1_planner.prompt.md"
    assert written.exists()
    body = written.read_text(encoding="utf-8")
    assert "<planner>" in body
    # Must NOT include other roles' Section A rules
    assert "Critic (`<critic>`)" not in body


def test_strict_mode_persists_inputs_for_reuse(tmp_path: Path) -> None:
    """Strict mode without --reuse must drop verdict_request.json next
    to the prompt for later --reuse."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out_dir = tmp_path / "consensus_X"
    rc = main(["--mode", "strict", "--verdict-request", str(req),
               "--out", str(out_dir / "1_planner.prompt.md")])
    assert rc == 0
    assert (out_dir / "verdict_request.json").exists()


def test_strict_reuse_reads_inputs_from_dir(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_T"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    body = (consensus_dir / "1_planner.prompt.md").read_text(encoding="utf-8")
    assert "<planner>" in body


def test_strict_reuse_missing_verdict_request_returns_2(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "empty_dir"
    consensus_dir.mkdir(parents=True)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 2


def test_strict_reuse_with_history_json(tmp_path: Path) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_with_history"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    (consensus_dir / "history.json").write_text(json.dumps([{
        "plan_entry_id": "01HXYZABCD0123456789ABCDEF",
        "context": {"ctl": 65, "phase": "BUILD"},
        "verdict": "ACCEPT", "outcome": "consensus.ACCEPT@0.78",
    }]), encoding="utf-8")
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    body = (consensus_dir / "1_planner.prompt.md").read_text(encoding="utf-8")
    assert "01HXYZABCD0123456789ABCDEF" in body


def test_strict_without_reuse_requires_verdict_request(tmp_path: Path) -> None:
    """`--mode strict` without --reuse must require --verdict-request."""
    from scripts.run_consensus import main
    with pytest.raises(SystemExit):
        # argparse exits with 2 when a required flag is missing
        main(["--mode", "strict"])


def test_council_mode_default_unchanged(tmp_path: Path) -> None:
    """Regression: council mode (default) writes the original 4-role
    prompt and ignores any strict-only flags."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    rc = main([
        "--verdict-request", str(req),
        "--out", str(tmp_path / "council.prompt.md"),
    ])
    assert rc == 0
    body = (tmp_path / "council.prompt.md").read_text(encoding="utf-8")
    # Council mode emits all 4 roles in Section A
    assert "Critic (`<critic>`)" in body
    assert "Physiologist (`<physiologist>`)" in body
    assert "Arbiter (`<arbiter>`)" in body


def test_council_mode_also_persists_inputs(tmp_path: Path) -> None:
    """Council mode persists verdict_request.json next to the council
    prompt so a future strict --reuse invocation can pick it up."""
    from scripts.run_consensus import main
    req = _write_request(tmp_path)
    out = tmp_path / "consensus_dir" / "council.prompt.md"
    rc = main([
        "--verdict-request", str(req),
        "--out", str(out),
    ])
    assert rc == 0
    assert (tmp_path / "consensus_dir" / "verdict_request.json").exists()


def test_strict_reuse_emits_strict_next_steps(tmp_path: Path,
                                              capsys) -> None:
    from scripts.run_consensus import main
    consensus_dir = tmp_path / "consensus_NEXT"
    consensus_dir.mkdir(parents=True)
    _write_request(consensus_dir)
    rc = main(["--mode", "strict", "--reuse", str(consensus_dir)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "--mode strict --step 2" in captured.out
    assert "1_planner.response.md" in captured.out
