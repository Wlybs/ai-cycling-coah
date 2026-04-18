import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_refresh_physiology_script_is_callable_standalone():
    script = REPO / "scripts" / "refresh_physiology.py"
    assert script.exists()


@pytest.mark.integration
def test_run_deep_analysis_script_is_callable():
    script = REPO / "scripts" / "run_deep_analysis.py"
    assert script.exists()


@pytest.mark.integration
def test_sync_data_imports_new_steps():
    sd = (REPO / "scripts" / "sync_data.py").read_text()
    assert "refresh_physiology" in sd
    assert "run_deep_analysis" in sd
