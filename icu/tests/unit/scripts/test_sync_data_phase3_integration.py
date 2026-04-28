"""T70.1 RED — sync_data.py steps 11 + 12 wiring."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


def _import_main():
    """Import sync_data.main fresh each call — module is a script."""
    import importlib
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    import sync_data  # type: ignore
    importlib.reload(sync_data)
    return sync_data


def test_step11_invokes_ingest_ledger() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    invoked = [c for c in captured if any("ingest_ledger.py" in p for p in c)]
    assert len(invoked) == 1, f"ingest_ledger.py should be invoked exactly once: {captured}"
    assert "--memory" in invoked[0]
    assert "--warehouse" in invoked[0]


def test_step12_invokes_daily_adapt() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    invoked = [c for c in captured if any("daily_adapt.py" in p for p in c)]
    assert len(invoked) == 1
    assert "--date" in invoked[0]
    assert "--memory" in invoked[0]
    assert "--warehouse" in invoked[0]


def test_step11_then_step12_order_preserved() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    idx_ingest = next(i for i, c in enumerate(captured)
                      if any("ingest_ledger.py" in p for p in c))
    idx_adapt = next(i for i, c in enumerate(captured)
                     if any("daily_adapt.py" in p for p in c))
    assert idx_ingest < idx_adapt


def test_step11_failure_does_not_abort_step12() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        if any("ingest_ledger.py" in p for p in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert any("daily_adapt.py" in p for c in captured for p in c), (
        "daily_adapt.py must still run after ingest_ledger.py failure"
    )
    assert "ingest_ledger.py" in sd.failures
