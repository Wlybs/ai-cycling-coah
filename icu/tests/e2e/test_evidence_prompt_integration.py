"""E2E: run_consensus.py council mode injects References section from real corpus."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]


def _verdict_request_payload() -> dict:
    return {
        "plan": {
            "week_start": "2026-04-20",
            "week_end": "2026-04-26",
            "focus_theme": "BUILD",
            "weekly_tss_target": 525,
            "days": [
                {"day_of_week": "Tue", "training_type": "VO2max",
                 "name": "5x4min @CP", "duration_min": 75, "target_tss": 90,
                 "power_range_w": "260-280W", "tier": "HIGH"},
            ],
        },
        "athlete_state": {
            "ctl": 70.0, "atl": 68.0, "tsb": 2.0,
            "w_prime": 14_500, "phase": "BUILD", "week_of_year": 17,
        },
        "physiology": {"cp_w": 285, "w_prime_j": 14_500},
        "wellness_trend": [],
        "periodization_summary": {"phase": "BUILD",
                                  "weekly_tss_target": 525,
                                  "focus_theme": "vo2max intervals taper"},
    }


@pytest.fixture
def fixture_dir(tmp_path):
    req_path = tmp_path / "verdict_request.json"
    req_path.write_text(json.dumps(_verdict_request_payload()),
                        encoding="utf-8")
    return tmp_path, req_path


def _run_consensus(req_path: Path, out_path: Path, *extra: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "ICU_LOG_DIR": str(out_path.parent / ".logs")}
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "run_consensus.py"),
         "--mode", "council",
         "--verdict-request", str(req_path),
         "--out", str(out_path), *extra],
        capture_output=True, text=True, env=env, cwd=str(REPO),
    )


def test_council_prompt_contains_references_section(fixture_dir):
    tmp, req = fixture_dir
    out = tmp / "council.prompt.md"
    proc = _run_consensus(req, out, "--evidence-corpus",
                          str(REPO / "evidence_corpus"))
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    body = out.read_text(encoding="utf-8")
    assert "## References (auto-retrieved" in body
    assert "**[01HXR0NM8K" in body  # at least one real card cited


def test_no_evidence_flag_suppresses_section(fixture_dir):
    tmp, req = fixture_dir
    out = tmp / "council.prompt.md"
    proc = _run_consensus(req, out, "--no-evidence",
                          "--evidence-corpus", str(REPO / "evidence_corpus"))
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    body = out.read_text(encoding="utf-8")
    assert "## References" not in body


def test_missing_corpus_does_not_break_prompt(fixture_dir):
    tmp, req = fixture_dir
    out = tmp / "council.prompt.md"
    proc = _run_consensus(req, out, "--evidence-corpus",
                          str(tmp / "nonexistent_corpus"))
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    body = out.read_text(encoding="utf-8")
    # Body still written; no References section since corpus missing
    assert "## References" not in body
    assert "WARN: evidence corpus not found" in proc.stderr
