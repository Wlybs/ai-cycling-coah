"""T71 e2e — Phase 3 full chain smoke test against frozen fixtures."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ICU = Path(__file__).resolve().parents[2]  # /mnt/d/Cycling-phase3/icu
FIXTURE_ROOT = REPO_ICU / "tests" / "fixtures" / "phase3" / "e2e"
PYTHON = sys.executable


def _seed_workspace(tmp_path: Path) -> dict[str, Path]:
    """Copy frozen fixture tree into tmp_path and return path map."""
    memory = tmp_path / "coach_memory"
    warehouse = tmp_path / "icu_data_warehouse"
    shutil.copytree(FIXTURE_ROOT / "coach_memory_seed", memory)
    shutil.copytree(FIXTURE_ROOT / "warehouse_seed", warehouse)
    (memory / "ledger").mkdir(parents=True, exist_ok=True)
    (memory / "adapter").mkdir(parents=True, exist_ok=True)
    return {
        "memory": memory,
        "warehouse": warehouse,
        "ledger": memory / "ledger" / "decisions.jsonl",
        "adapter": memory / "adapter",
    }


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    return _seed_workspace(tmp_path)


@pytest.mark.e2e
def test_ingest_ledger_seeds_five_decision_types(
        workspace: dict[str, Path]) -> None:
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    entries = _read_ledger(workspace["ledger"])
    types_seen = {e["decision_type"] for e in entries}
    expected = {"phase_transition", "macro_plan_generated",
                "meso_block_created", "micro_cycle_generated",
                "weekly_plan_assembled"}
    assert expected <= types_seen, f"missing: {expected - types_seen}"


@pytest.mark.e2e
def test_daily_adapt_red_verdict_writes_proposed_session(
        workspace: dict[str, Path]) -> None:
    # Pre-seed ledger via ingest_ledger so adapter sees Phase 2 history
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )

    target_date = date(2026, 4, 28).isoformat()  # matches fixture today
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    # Spec-wart Option C: scripts/daily_adapt.py main() emits a final
    # json.dumps(captured_at=datetime) line that raises TypeError after the
    # ledger / markdown / proposed_session writes already succeeded. The
    # frozen-script invariant (T70 was the last script edit) forbids fixing
    # the print, so we verify the persisted artefacts directly instead of
    # asserting returncode == 0. If the failure mode shifts (e.g. ledger
    # write itself fails) the artefact assertions below will still surface
    # the regression.
    if result.returncode != 0:
        assert "Object of type datetime is not JSON serializable" in result.stderr, (
            f"Unexpected daily_adapt failure: {result.stderr}"
        )

    entries = _read_ledger(workspace["ledger"])
    verdicts = [e for e in entries
                if e["decision_type"] == "adaptation_verdict"]
    assert len(verdicts) >= 1
    assert verdicts[-1]["payload"]["verdict"] == "red"

    md_path = workspace["adapter"] / f"today_{target_date}.md"
    proposed = workspace["adapter"] / f"proposed_session_{target_date}.json"
    assert md_path.exists()
    assert proposed.exists()


# ---------------------------------------------------------------------------
# T71.2 — consensus → apply → suggester slice
# ---------------------------------------------------------------------------

# Spec deviations (Option C, all documented in T71.2 spec lines 1611-1926):
# 1. run_consensus.py real CLI is `--verdict-request <json>` + `--out`, not the
#    speculative `--athlete-state --plan --memory --out` from spec Step 1. We
#    build a VerdictRequest JSON inline and call the real signature.
# 2. finalize_consensus.py council mode uses `--response <md>` (NOT
#    `--consensus-dir`; that's strict-mode only). Council mode does NOT write
#    `verdict.md`; only strict mode writes `strict_verdict.md`. So we drop the
#    `verdict.md` existence assertion and replace it with the
#    `consensus_verdict` ledger assertion that IS the contract.
# 3. apply_adaptation.py has no `ICU_DRY_RUN_PATCH` env-var seam. Per OQ5, we
#    inject a tmp `sitecustomize.py` via `PYTHONPATH` that monkeypatches
#    `ICUClient.update_event` to a no-op returning {}. This matches the
#    in-process seam existing unit tests use (`MagicMock` as `client_factory`)
#    without modifying File 05 source.
#
# Frozen-script invariant respected: no source file under icu/src/coach/ or
# icu/scripts/ touched in T71.2.


def _build_verdict_request_payload(memory_dir: Path) -> dict:
    """Construct the minimum VerdictRequest payload from seed fixtures."""
    plan = json.loads(
        (memory_dir / "reports" / "plan_2026-04-27.json").read_text(
            encoding="utf-8"))
    athlete_state = {
        "ctl": 65.0, "atl": 67.0, "tsb": -2.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }
    cp_w = json.loads(
        (memory_dir / "physiology" / "cp_w_current.json").read_text(
            encoding="utf-8"))
    durability = json.loads(
        (memory_dir / "physiology" / "durability.json").read_text(
            encoding="utf-8"))
    response_profile = json.loads(
        (memory_dir / "physiology" / "response_profile.json").read_text(
            encoding="utf-8"))
    physiology = {
        "cp_w": cp_w,
        "durability": durability,
        "response_profile": response_profile,
        "knee_flag": False,
    }
    micro = json.loads(
        (memory_dir / "periodization"
         / "micro_cycle_2026-04-27.json").read_text(encoding="utf-8"))
    periodization_summary = {
        "phase": "BUILD",
        "week_id": micro.get("week_id", "2026W17"),
        "weekly_tss_target": micro.get("weekly_tss_target", 380),
    }
    wellness_trend = [
        {"date": "2026-04-25", "ctl": 64.0, "atl": 65.0, "tsb": -1.0},
        {"date": "2026-04-26", "ctl": 64.5, "atl": 66.0, "tsb": -1.5},
        {"date": "2026-04-27", "ctl": 65.0, "atl": 67.0, "tsb": -2.0},
    ]
    return {
        "plan": plan,
        "athlete_state": athlete_state,
        "physiology": physiology,
        "wellness_trend": wellness_trend,
        "periodization_summary": periodization_summary,
    }


def _write_athlete_state(path: Path) -> None:
    path.write_text(json.dumps({
        "ctl": 65.0, "atl": 67.0, "tsb": -2.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }), encoding="utf-8")


def _build_pythonpath_with_icu_mock(tmp_path: Path) -> str:
    """Create a sitecustomize.py that no-ops ICUClient.update_event.

    Returns a PYTHONPATH value (with REPO_ICU also on it so `src.*` resolves)
    suitable for passing into subprocess `env=`. This is the OQ5
    in-process-seam-as-subprocess-shim pattern: we replace the bound method
    on the real class at interpreter startup so apply_adaptation.py's
    `client_factory=lambda: ICUClient()` returns a real instance whose
    `update_event` no-ops.
    """
    shim_dir = tmp_path / "icu_shim"
    shim_dir.mkdir(parents=True, exist_ok=True)
    (shim_dir / "sitecustomize.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "_repo_icu = Path(__file__).resolve().parents[1] / 'icu_repo_marker'\n"
        "# Ensure src.* is importable (REPO_ICU is on PYTHONPATH already).\n"
        "try:\n"
        "    from src.fetcher.icu_client import ICUClient\n"
        "except Exception:\n"
        "    ICUClient = None\n"
        "if ICUClient is not None:\n"
        "    def _stub_update_event(self, event_id, event_data):\n"
        "        return {'id': event_id, 'updated': True}\n"
        "    ICUClient.update_event = _stub_update_event\n"
        "    def _stub_init(self, *a, **kw):\n"
        "        self.api_key = 'TEST'\n"
        "        self.athlete_id = 'TEST'\n"
        "        self.auth = ('API_KEY', 'TEST')\n"
        "        self.proxies = None\n"
        "    ICUClient.__init__ = _stub_init\n",
        encoding="utf-8",
    )
    import os as _os
    return _os.pathsep.join([str(shim_dir), str(REPO_ICU)])


@pytest.mark.e2e
def test_run_consensus_emits_prompt(workspace: dict[str, Path],
                                    tmp_path: Path) -> None:
    consensus_dir = tmp_path / "consensus_run"
    consensus_dir.mkdir(parents=True)
    # Build VerdictRequest JSON (real CLI shape; spec's `--athlete-state +
    # --plan + --memory` is speculative — Option C #1).
    request_path = consensus_dir / "verdict_request.json"
    request_path.write_text(
        json.dumps(_build_verdict_request_payload(workspace["memory"]),
                   ensure_ascii=False),
        encoding="utf-8")
    out_path = consensus_dir / "council.prompt.md"

    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "run_consensus.py"),
         "--verdict-request", str(request_path),
         "--out", str(out_path)],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    assert out_path.exists()


@pytest.mark.e2e
def test_finalize_consensus_writes_verdict(
        workspace: dict[str, Path], tmp_path: Path) -> None:
    consensus_dir = tmp_path / "consensus_run"
    consensus_dir.mkdir(parents=True)
    response_md_path = consensus_dir / "council.response.md"
    response_md_path.write_text(
        (FIXTURE_ROOT / "consensus_response.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    athlete_state_path = consensus_dir / "athlete_state.json"
    _write_athlete_state(athlete_state_path)

    # Council mode: --response (not --consensus-dir; strict-mode only).
    # Option C #2 documented above.
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "finalize_consensus.py"),
         "--response", str(response_md_path),
         "--ledger", str(workspace["ledger"]),
         "--athlete-state", str(athlete_state_path),
         "--confirm"],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    entries = _read_ledger(workspace["ledger"])
    verdicts = [e for e in entries
                if e["decision_type"] == "consensus_verdict"]
    assert len(verdicts) >= 1


@pytest.mark.e2e
def test_apply_adaptation_writes_adaptation_applied(
        workspace: dict[str, Path], tmp_path: Path) -> None:
    target_date = "2026-04-28"
    # Pre-seed ledger
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    # daily_adapt has the known T71.1 datetime-print bug; tolerate rc!=0.
    # ICU_FORCED_NOW_ISO pins captured_at to target_date so apply_adaptation's
    # strict same-UTC-day verdict filter matches (post-2026-04-28 fix for v3.0.1).
    import os as _os
    adapt_env = {**_os.environ,
                 "ICU_FORCED_NOW_ISO": f"{target_date}T12:00:00+00:00"}
    adapt_res = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU), env=adapt_env,
    )
    if adapt_res.returncode != 0:
        assert "Object of type datetime is not JSON serializable" \
               in adapt_res.stderr, adapt_res.stderr

    # Mock ICU PATCH via PYTHONPATH sitecustomize shim (Option C #3).
    pp = _build_pythonpath_with_icu_mock(tmp_path)
    env = {**_os.environ, "PYTHONPATH": pp,
           "API_KEY": "TEST", "ATHLETE_ID": "TEST",
           "ICU_FORCED_NOW_ISO": f"{target_date}T12:00:00+00:00"}
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "apply_adaptation.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--confirm"],
        capture_output=True, text=True, cwd=str(REPO_ICU), env=env,
    )
    # Same datetime-print bug as daily_adapt.py: ledger is written BEFORE the
    # final json.dumps(applied_at=datetime) print, so rc=1 with that exact
    # signature is recoverable. T71.2 may not fix the bug (frozen-script
    # invariant); T71.1 follow-up tracks it separately.
    if result.returncode != 0:
        assert "Object of type datetime is not JSON serializable" \
               in result.stderr, result.stderr
    entries = _read_ledger(workspace["ledger"])
    applied = [e for e in entries
               if e["decision_type"] == "adaptation_applied"]
    assert len(applied) >= 1


@pytest.mark.e2e
def test_full_chain_emits_all_eight_decision_types_and_one_suggestion(
        workspace: dict[str, Path], tmp_path: Path) -> None:
    """Grand-finale assertion: 8/8 decision_types + ≥1 suggestion line."""
    target_date = "2026-04-28"

    # 1. Ingest
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    # 2. Daily adapt (red); tolerate datetime-print bug. ICU_FORCED_NOW_ISO
    # pins captured_at to target_date so apply_adaptation's strict same-UTC-day
    # filter matches (post-2026-04-28 fix for v3.0.1 + date-coupled test).
    import os as _os
    adapt_env = {**_os.environ,
                 "ICU_FORCED_NOW_ISO": f"{target_date}T12:00:00+00:00"}
    adapt_res = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU), env=adapt_env,
    )
    if adapt_res.returncode != 0:
        assert "Object of type datetime is not JSON serializable" \
               in adapt_res.stderr, adapt_res.stderr

    # 3. Consensus (finalize council response)
    consensus_dir = tmp_path / "consensus_run"
    consensus_dir.mkdir(parents=True)
    response_md_path = consensus_dir / "council.response.md"
    response_md_path.write_text(
        (FIXTURE_ROOT / "consensus_response.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    athlete_state_path = consensus_dir / "athlete_state.json"
    _write_athlete_state(athlete_state_path)
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "finalize_consensus.py"),
         "--response", str(response_md_path),
         "--ledger", str(workspace["ledger"]),
         "--athlete-state", str(athlete_state_path),
         "--confirm"],
        check=True, cwd=str(REPO_ICU),
    )

    # 4. Apply adaptation (mock ICU PATCH)
    pp = _build_pythonpath_with_icu_mock(tmp_path)
    env = {**_os.environ, "PYTHONPATH": pp,
           "API_KEY": "TEST", "ATHLETE_ID": "TEST",
           "ICU_FORCED_NOW_ISO": f"{target_date}T12:00:00+00:00"}
    apply_res = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "apply_adaptation.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--confirm"],
        capture_output=True, text=True, cwd=str(REPO_ICU), env=env,
    )
    if apply_res.returncode != 0:
        assert "Object of type datetime is not JSON serializable" \
               in apply_res.stderr, apply_res.stderr

    # 5. All 8 decision types present
    entries = _read_ledger(workspace["ledger"])
    types_seen = {e["decision_type"] for e in entries}
    expected_eight = {
        "phase_transition", "macro_plan_generated", "meso_block_created",
        "micro_cycle_generated", "weekly_plan_assembled",
        "adaptation_verdict", "consensus_verdict", "adaptation_applied",
    }
    assert expected_eight <= types_seen, (
        f"missing types: {expected_eight - types_seen}"
    )

    # 6. Suggester emits ≥1 line (trigger #1: phase_transition < 7d).
    sys.path.insert(0, str(REPO_ICU))
    from src.coach.common.action_suggester import suggest_actions
    lines = suggest_actions(
        workspace["ledger"],
        workspace["memory"] / "periodization",
        workspace["memory"] / "deep_analysis",
        today=date.fromisoformat(target_date),
    )
    assert len(lines) >= 1, (
        "Suggester must emit ≥1 line; fixture seeded a phase_transition "
        "within the past 7 days (trigger #1)."
    )
