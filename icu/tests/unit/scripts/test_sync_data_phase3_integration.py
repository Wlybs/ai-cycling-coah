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


def test_step13_invokes_action_suggester(capsys) -> None:
    sd = _import_main()
    captured_calls: list[tuple] = []

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    fake_module = type("M", (), {})()
    fake_module.suggest_actions = lambda *a, **kw: (
        captured_calls.append(("suggest", a, kw)) or ["建议一", "建议二"]
    )
    fake_module.print_suggestions = lambda lines, *, header: (
        captured_calls.append(("print", lines, header))
    )

    import sys
    sys.modules["src.coach.common.action_suggester"] = fake_module

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    suggest_calls = [c for c in captured_calls if c[0] == "suggest"]
    print_calls = [c for c in captured_calls if c[0] == "print"]
    assert len(suggest_calls) == 1
    assert len(print_calls) == 1
    assert print_calls[0][1] == ["建议一", "建议二"]

    del sys.modules["src.coach.common.action_suggester"]


def test_step13_import_error_swallowed_does_not_add_to_failures(
        capsys) -> None:
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    import builtins
    real_import = builtins.__import__

    def boom(name, *a, **kw):
        if "action_suggester" in name:
            raise ImportError(f"No module named {name}")
        return real_import(name, *a, **kw)

    with patch.object(builtins, "__import__", side_effect=boom), \
         patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert "action_suggester" not in sd.failures
    captured = capsys.readouterr()
    assert "Phase 3 suggester unavailable" in captured.out


def test_step13_unexpected_exception_added_to_failures(capsys) -> None:
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    fake_module = type("M", (), {})()
    fake_module.suggest_actions = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("ledger corrupt")
    )
    fake_module.print_suggestions = lambda lines, *, header: None

    import sys
    sys.modules["src.coach.common.action_suggester"] = fake_module

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert "action_suggester" in sd.failures
    captured = capsys.readouterr()
    assert "suggester failed" in captured.out

    del sys.modules["src.coach.common.action_suggester"]


def test_main_exit_does_not_raise_when_phase3_step_fails(capsys) -> None:
    """Phase 1/2 sync MUST stay green even when Phase 3 explodes."""
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        if any("ingest_ledger.py" in p for p in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        # Must not raise SystemExit non-zero / propagate exceptions
        sd.main()
