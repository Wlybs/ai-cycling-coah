"""Unit tests for src/coach/plan_evaluator.py — stale-plan handling."""
import json

import pytest

from src.coach import plan_evaluator as pe


def _write_plan(reports_dir, stamp, week_start, week_end):
    path = reports_dir / f"plan_{stamp}.json"
    path.write_text(json.dumps({
        "week_start": week_start,
        "week_end": week_end,
        "days": [],
    }), encoding="utf-8")
    return path


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    memory = tmp_path / "coach_memory"
    reports.mkdir()
    memory.mkdir()
    monkeypatch.setattr(pe, "REPORTS_DIR", str(reports))
    monkeypatch.setattr(pe, "MEMORY_DIR", str(memory))
    return reports, memory


class TestFindLatestPlan:
    def test_ignores_plans_that_ended_long_ago(self, dirs):
        reports, _ = dirs
        _write_plan(reports, "20260523", "2026-05-23", "2026-05-31")
        assert pe._find_latest_plan(today="2026-10-16") is None

    def test_picks_plan_covering_today(self, dirs):
        reports, _ = dirs
        _write_plan(reports, "20260523", "2026-05-23", "2026-05-31")
        current = _write_plan(reports, "20261012", "2026-10-12", "2026-10-18")
        assert pe._find_latest_plan(today="2026-10-16") == str(current)

    def test_last_week_plan_still_counts(self, dirs):
        reports, _ = dirs
        last_week = _write_plan(reports, "20261005", "2026-10-05", "2026-10-11")
        assert pe._find_latest_plan(today="2026-10-16") == str(last_week)

    def test_skips_future_plan_in_favour_of_current(self, dirs):
        reports, _ = dirs
        current = _write_plan(reports, "20261012", "2026-10-12", "2026-10-18")
        _write_plan(reports, "20261019", "2026-10-19", "2026-10-25")
        assert pe._find_latest_plan(today="2026-10-16") == str(current)


class TestEvaluateWithoutRecentPlan:
    def test_overwrites_stale_adherence_with_status_stub(self, dirs):
        reports, memory = dirs
        _write_plan(reports, "20260523", "2026-05-23", "2026-05-31")
        stale = memory / "plan_adherence.json"
        stale.write_text(json.dumps({"plan_file": "plan_20260523.json",
                                     "summary": {"completed_days": 3}}), encoding="utf-8")

        assert pe.evaluate_plan(verbose=False) is None

        out = json.loads(stale.read_text(encoding="utf-8"))
        assert out["status"] == "no_recent_plan"
        assert "summary" not in out  # downstream skips the 上周计划执行情况 section
