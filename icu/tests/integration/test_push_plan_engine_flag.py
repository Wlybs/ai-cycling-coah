"""Integration tests for push_plan.py --engine v1|v2 flag."""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add icu/ to path so we can import scripts module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import push_plan


@pytest.mark.integration
def test_push_plan_default_engine_runs_v1():
    """Default (no --engine) should run v1 path."""
    with patch("scripts.push_plan.generate_plan") as mock_v1, \
         patch("scripts.push_plan._run_v2_engine") as mock_v2, \
         patch("sys.argv", ["push_plan.py", "--week", "2026-04-20"]), \
         patch("os.chdir"):
        push_plan.main()
        mock_v1.assert_called_once()
        mock_v2.assert_not_called()


@pytest.mark.integration
def test_push_plan_engine_v2_calls_v2_and_returns():
    """--engine v2 with success should call v2 and NOT call v1."""
    with patch("scripts.push_plan._run_v2_engine", return_value=True) as mock_v2, \
         patch("scripts.push_plan.generate_plan") as mock_v1, \
         patch("sys.argv", ["push_plan.py", "--week", "2026-04-20", "--engine", "v2"]), \
         patch("os.chdir"):
        push_plan.main()
        mock_v2.assert_called_once()
        mock_v1.assert_not_called()


@pytest.mark.integration
def test_push_plan_engine_v2_falls_back_to_v1_on_error():
    """--engine v2 with failure should call v2, then fall back to v1."""
    with patch("scripts.push_plan._run_v2_engine", return_value=False) as mock_v2, \
         patch("scripts.push_plan.generate_plan") as mock_v1, \
         patch("sys.argv", ["push_plan.py", "--week", "2026-04-20", "--engine", "v2"]), \
         patch("os.chdir"):
        push_plan.main()
        mock_v2.assert_called_once()
        mock_v1.assert_called_once()


@pytest.mark.integration
def test_run_v2_engine_prints_warning_on_error(capsys):
    """_run_v2_engine should print warning and return False on error."""
    from src.coach.session_designer.generator_v2 import GeneratePlanV2Result

    with patch(
        "src.coach.session_designer.generator_v2.generate_plan_v2",
        return_value=GeneratePlanV2Result(
            status="error",
            error="forced test error",
        ),
    ):
        result = push_plan._run_v2_engine(date(2026, 4, 20), date(2026, 4, 26))
        assert result is False

        captured = capsys.readouterr()
        assert "v2 engine failed" in captured.err
        assert "forced test error" in captured.err
        assert "falling back to v1" in captured.err
