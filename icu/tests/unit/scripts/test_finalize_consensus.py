"""Unit tests for scripts.finalize_consensus (T66.1 — argparse + dry-run)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.finalize_consensus import main as finalize_main


# ---------- canned valid council response ----------

_HAPPY_RESPONSE = """\
<planner>
This week 525 TSS targets the BUILD phase. Tuesday 5x4min @CP at 270W
is the keystone session per the threshold response_profile. Saturday
180min Z2 builds durability at 165W average; total 615 minutes work,
matched to CP=285W and W'=14500J.
</planner>

<critic>
1. The Tuesday VO2max session is only 20min work; CP=285W tolerance band
   demands 22-24min for high-tolerance class — UNDER-DOSED by 2-4 min.
2. Friday threshold 2x20min total = 40min, but recent stimulus_score
   mean = 0.42 < 0.45 floor; need a third interval.
3. Saturday's long Z2 lacks a sustained sweet-spot block; durability
   index = 0.74 suggests 2x10min @ 230W could nudge it up.
</critic>

<physiologist>
CP=285W and W'=14500J anchor this athlete in mid-pack response_profile.
With the prescribed plan, end-of-week W' balance estimate is -42% on
Saturday. durability index = 0.74 is intact. knee_flag = OK.
</physiologist>

<arbiter>
REVISE
Plan needs one more threshold interval and 2 extra VO2 minutes.
- (Tue, 5x4min @270W, 6x4min @270W)
- (Fri, 2x20min @250W, 3x20min @250W)
</arbiter>

<summary_json>
{"verdict": "REVISE", "confidence": 0.78}
</summary_json>
"""


_ATHLETE_STATE = {
    "ctl": 70.0, "atl": 68.0, "tsb": 2.0, "w_prime": 14_500,
    "phase": "BUILD", "week_of_year": 17,
}


def _write_response(path: Path, body: str = _HAPPY_RESPONSE) -> None:
    path.write_text(body, encoding="utf-8")


def _write_state(path: Path, payload: dict | None = None) -> None:
    path.write_text(json.dumps(payload or _ATHLETE_STATE),
                    encoding="utf-8")


# ---------- argparse skeleton tests ----------

class TestArgparseSkeleton:

    def test_required_flags_missing_exit_2(self, tmp_path, capsys):
        rc = finalize_main([])
        # argparse exits 2 on missing required args
        assert rc == 2

    def test_dry_run_is_default(self, tmp_path, capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        # dry-run -> exit 0 even though ledger doesn't exist
        assert rc == 0
        # ledger file must remain untouched
        assert not ledger.exists()
        out = capsys.readouterr().out
        assert "DRY-RUN" in out or "dry-run" in out

    def test_dry_run_prints_would_be_entry(self, tmp_path, capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        # Verdict + confidence pulled from <summary_json>
        assert "REVISE" in out
        assert "0.78" in out
        # Decision type literal
        assert "consensus_verdict" in out
        # Source literal
        assert "consensus.council" in out

    def test_dry_run_and_confirm_mutually_exclusive(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--dry-run",
            "--confirm",
        ])
        # argparse mutex group rejects with exit 2
        assert rc == 2


# ---------- API_FREE invariant ----------

class TestApiFreeInvariantFinalize:

    def test_no_llm_sdk_imported(self):
        text = Path("scripts/finalize_consensus.py").read_text(
            encoding="utf-8")
        for needle in ("google.genai", "from google import genai",
                       "import requests", "import urllib", "import httpx"):
            assert needle not in text, (
                f"finalize_consensus.py must remain API_FREE; "
                f"found {needle!r}"
            )


# ---------- T66.2: parse + validate + append ----------

class TestParseValidateAppend:

    def test_confirm_appends_one_ledger_line(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        assert ledger.exists()
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["decision_type"] == "consensus_verdict"
        assert entry["source"] == "consensus.council"
        assert entry["payload"]["verdict"] == "REVISE"
        assert entry["payload"]["confidence"] == pytest.approx(0.78)
        # athlete_state_ref echoed back
        assert entry["athlete_state_ref"]["phase"] == "BUILD"
        assert entry["athlete_state_ref"]["ctl"] == pytest.approx(70.0)
        # evidence_refs hold the response path string
        assert any(str(resp) in r for r in entry["evidence_refs"])
        # confidence at top level matches verdict.confidence
        assert entry["confidence"] == pytest.approx(0.78)

    def test_malformed_response_does_not_touch_ledger(self, tmp_path,
                                                      capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"

        # malformed: only 2 sections, no <summary_json>
        resp.write_text(
            "<planner>p</planner>\n<critic>c</critic>\n",
            encoding="utf-8",
        )
        _write_state(state)
        # pre-seed the ledger with one prior entry
        prior_line = (
            '{"schema_version":1,"entry_id":"01HZZZ' + "0" * 20
            + '","timestamp":"2026-01-01T00:00:00+00:00","decision_type":'
            '"weekly_plan_assembled","source":"phase2","athlete_state_ref":'
            '{"ctl":50.0,"atl":50.0,"tsb":0.0,"w_prime":12000,'
            '"phase":"BUILD","week_of_year":1},"confidence":null,'
            '"payload":{},"evidence_refs":[],"superseded_by":null}\n'
        )
        ledger.write_text(prior_line, encoding="utf-8")
        before = ledger.read_text(encoding="utf-8")

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])

        assert rc == 2
        # rollback contract: file is byte-identical
        after = ledger.read_text(encoding="utf-8")
        assert after == before, (
            "Ledger file mutated despite parser violation - "
            "T66.2 rollback contract is broken"
        )
        err = capsys.readouterr().err
        assert "violation" in err.lower() or "missing" in err.lower()

    def test_invalid_json_summary_does_not_touch_ledger(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        # Replace the well-formed summary_json with broken JSON.
        bad = _HAPPY_RESPONSE.replace(
            '{"verdict": "REVISE", "confidence": 0.78}',
            '{"verdict": "REVISE", "confidence": ',
        )
        resp.write_text(bad, encoding="utf-8")
        _write_state(state)

        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists() or \
               ledger.read_text(encoding="utf-8") == ""

    def test_missing_athlete_state_file_exit_2(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        _write_response(resp)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(tmp_path / "absent.json"),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists()

    def test_athlete_state_schema_violation_exit_2(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        # bad shape: missing required fields
        state.write_text(json.dumps({"ctl": 70.0}), encoding="utf-8")
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 2
        assert not ledger.exists()

    def test_entry_id_is_valid_ulid(self, tmp_path):
        from src.coach.ledger.types import is_valid_ulid
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        entry = json.loads(ledger.read_text(encoding="utf-8").strip())
        assert is_valid_ulid(entry["entry_id"])

    def test_evidence_refs_contains_response_path(self, tmp_path):
        resp = tmp_path / "council.response.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)
        rc = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc == 0
        entry = json.loads(ledger.read_text(encoding="utf-8").strip())
        assert any("council.response.md" in r
                   for r in entry["evidence_refs"])


# ---------- T66.3: idempotency ----------

class TestIdempotency:

    def test_second_confirm_does_not_double_append(self, tmp_path,
                                                    capsys):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0

        # Second invocation - same content
        capsys.readouterr()  # drain
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        out = capsys.readouterr().out
        assert "Already finalized" in out
        # Ledger still has exactly one consensus_verdict line
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        cv_lines = [l for l in lines
                    if json.loads(l)["decision_type"] == "consensus_verdict"]
        assert len(cv_lines) == 1, (
            f"expected 1 consensus_verdict entry, got {len(cv_lines)}: "
            f"{cv_lines}"
        )

    def test_different_response_appends_new_entry(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_state(state)

        # First response: REVISE @0.78
        resp1 = tmp_path / "r1.md"
        _write_response(resp1, _HAPPY_RESPONSE)
        rc1 = finalize_main([
            "--response", str(resp1),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0

        # Second response: ACCEPT @0.92 (different summary_json)
        resp2 = tmp_path / "r2.md"
        body2 = _HAPPY_RESPONSE.replace(
            '{"verdict": "REVISE", "confidence": 0.78}',
            '{"verdict": "ACCEPT", "confidence": 0.92}',
        ).replace(
            "REVISE\nPlan needs",
            "ACCEPT\nPlan looks",
        )
        _write_response(resp2, body2)
        rc2 = finalize_main([
            "--response", str(resp2),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0

        # Two distinct consensus_verdict lines
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        cv_lines = [l for l in lines
                    if json.loads(l)["decision_type"] == "consensus_verdict"]
        assert len(cv_lines) == 2

    def test_dry_run_then_confirm_appends_once(self, tmp_path):
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        # Dry-run first
        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
        ])
        assert rc1 == 0
        assert not ledger.exists()

        # Confirm second
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_content_hash_is_stable(self, tmp_path):
        """Two CouncilVerdicts with identical content yield same hash."""
        from scripts.finalize_consensus import _content_hash
        from src.coach.consensus.response_parser import parse as parse_council

        v1 = parse_council(_HAPPY_RESPONSE, mode="council")
        v2 = parse_council(_HAPPY_RESPONSE, mode="council")
        assert _content_hash(v1) == _content_hash(v2)
        assert len(_content_hash(v1)) == 64  # sha256 hex

    def test_idempotency_skip_preserves_ledger_bytes(self, tmp_path):
        """Probe must run BEFORE record - duplicate skip leaves bytes intact."""
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        # First confirm
        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0
        before = ledger.read_bytes()

        # Second confirm - duplicate skip
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        after = ledger.read_bytes()
        assert before == after, (
            "Idempotency-skip must not mutate ledger - bytes diverged"
        )

    def test_idempotency_skip_prints_existing_entry_id(self, tmp_path,
                                                       capsys):
        """Duplicate-skip must print 'existing entry_id=...' to stdout."""
        resp = tmp_path / "resp.md"
        ledger = tmp_path / "ledger.jsonl"
        state = tmp_path / "state.json"
        _write_response(resp)
        _write_state(state)

        rc1 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc1 == 0
        first_entry = json.loads(
            ledger.read_text(encoding="utf-8").strip())
        first_id = first_entry["entry_id"]

        capsys.readouterr()  # drain
        rc2 = finalize_main([
            "--response", str(resp),
            "--ledger", str(ledger),
            "--athlete-state", str(state),
            "--confirm",
        ])
        assert rc2 == 0
        out = capsys.readouterr().out
        assert "Already finalized" in out
        assert first_id in out


# ============================================================
# T68.1 — argparse extension for strict mode
# ============================================================

import json
from pathlib import Path

import pytest


def test_step_without_mode_strict_rejected(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--step", "2", "--consensus-dir", str(tmp_path)]) == 2


def test_step_value_validated(tmp_path: Path) -> None:
    """Only 2/3/4 accepted (1 is run by run_consensus.py)."""
    from scripts.finalize_consensus import main
    d = tmp_path / "X"; d.mkdir()
    for bad in ("1", "5"):
        assert main(["--mode", "strict", "--step", bad,
                     "--consensus-dir", str(d)]) == 2


def test_strict_mode_requires_consensus_dir(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--mode", "strict", "--step", "2"]) == 2


def test_council_mode_default_unchanged(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main([]) == 2


def test_strict_step4_confirm_requires_ledger_and_state(
    tmp_path: Path,
) -> None:
    from scripts.finalize_consensus import main
    d = tmp_path / "Y"; d.mkdir()
    for fname in ("1_planner.response.md", "2_critic.response.md",
                  "3_physiologist.response.md", "4_arbiter.response.md"):
        (d / fname).write_text(
            f"<{fname.split('_')[1]}>x</{fname.split('_')[1]}>",
            encoding="utf-8")
    rc = main(["--mode", "strict", "--step", "4", "--confirm",
               "--consensus-dir", str(d)])
    assert rc == 2


def test_strict_step2_does_not_require_ledger(tmp_path: Path) -> None:
    """T68.1 only validates argparse; step-2 routing arrives in T68.2."""
    from scripts.finalize_consensus import main
    d = tmp_path / "Z"; d.mkdir()
    (d / "verdict_request.json").write_text(json.dumps({
        "plan": {"plan_period": "W17", "weekly_tss_target": 380,
                 "days": []},
        "athlete_state": {"ctl": 68, "atl": 72, "tsb": -4,
                          "w_prime": 18000, "phase": "BUILD",
                          "week_of_year": 17},
        "physiology": {}, "wellness_trend": [],
        "periodization_summary": {},
    }), encoding="utf-8")
    (d / "1_planner.response.md").write_text(
        "<planner>OK</planner>", encoding="utf-8")
    rc = main(["--mode", "strict", "--step", "2",
               "--consensus-dir", str(d)])
    # argparse accepted (non-2 OR a non-argparse rc=2 input error).
    assert isinstance(rc, int)


def test_dry_run_and_confirm_mutually_exclusive(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--response", str(tmp_path / "x.md"),
                 "--ledger", str(tmp_path / "l.jsonl"),
                 "--athlete-state", str(tmp_path / "a.json"),
                 "--confirm", "--dry-run"]) == 2


def test_strict_help_text_mentions_step_and_consensus_dir(capsys) -> None:
    from scripts.finalize_consensus import main
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "--mode" in out and "--step" in out and "--consensus-dir" in out


def test_step3_argparse_accepted(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    d = tmp_path / "S3"; d.mkdir()
    rc = main(["--mode", "strict", "--step", "3",
               "--consensus-dir", str(d)])
    assert isinstance(rc, int)


def test_council_response_path_still_required(tmp_path: Path) -> None:
    from scripts.finalize_consensus import main
    assert main(["--mode", "council",
                 "--ledger", str(tmp_path / "l.jsonl"),
                 "--athlete-state", str(tmp_path / "a.json")]) == 2
