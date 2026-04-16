import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class JSONLLogger:
    def __init__(self, module: str, log_dir: Path):
        self.module = module
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"{module}.log"

    def event(
        self,
        action: str,
        *,
        activity_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        status: str = "ok",
        error: Optional[str] = None,
        **extra: Any,
    ) -> None:
        rec: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "module": self.module,
            "activity_id": activity_id,
            "action": action,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
        }
        rec.update(extra)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def get_logger(module: str) -> JSONLLogger:
    log_dir = Path(os.environ.get("ICU_LOG_DIR", "icu/logs"))
    return JSONLLogger(module, log_dir)
