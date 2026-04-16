import json
from pathlib import Path

from src.coach.common.logging import get_logger


def test_logger_writes_structured_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("ICU_LOG_DIR", str(tmp_path))
    log = get_logger("cp_w_fitter")
    log.event(action="fit", activity_id=None, duration_ms=42, status="ok")
    log_file = tmp_path / "cp_w_fitter.log"
    assert log_file.exists()
    line = log_file.read_text().strip().splitlines()[-1]
    rec = json.loads(line)
    assert rec["module"] == "cp_w_fitter"
    assert rec["action"] == "fit"
    assert rec["status"] == "ok"
    assert rec["duration_ms"] == 42
    assert "ts" in rec


def test_logger_records_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ICU_LOG_DIR", str(tmp_path))
    log = get_logger("w_balance")
    log.event(action="compute", activity_id="i1", duration_ms=5, status="error", error="bad stream")
    rec = json.loads((tmp_path / "w_balance.log").read_text().strip())
    assert rec["error"] == "bad stream"
    assert rec["activity_id"] == "i1"
