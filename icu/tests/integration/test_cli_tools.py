import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_analyze_rides_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "analyze_rides.py"), "--help"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
    assert "--activity" in result.stdout and "--dry-run" in result.stdout


@pytest.mark.integration
def test_physiology_audit_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "physiology_audit.py"), "--help"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
