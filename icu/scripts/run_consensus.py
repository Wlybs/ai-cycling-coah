"""Phase 3 - assemble a council prompt for the user to paste into Gemini.

Reads:
  --verdict-request <path>   JSON of VerdictRequest fields
  [--history <path>]         JSON of list[HistoryTriplet]
  [--out <path>]             default ./council.prompt.md

Writes:
  one markdown file at --out

Exit codes:
  0 - success
  2 - input file error (missing, unreadable, bad JSON, wrong shape)
  3 - output write error

API_FREE: no LLM SDK, no network.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

# Allow `python scripts/run_consensus.py ...` from icu/.
_ICU_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ICU_ROOT))

# Pin the JSONL logger to an absolute path under icu/ so the CLI is robust
# to the caller's CWD. Module-level logger reads ICU_LOG_DIR at import time,
# so we must set it before importing council_prompt.
os.environ.setdefault("ICU_LOG_DIR", str(_ICU_ROOT / "logs"))

from src.coach import consensus as _consensus_pkg  # noqa: E402,F401
from src.coach.common.logging import get_logger as _get_logger  # noqa: E402
from src.coach.consensus import council_prompt as _council_prompt_mod  # noqa: E402
from src.coach.consensus.council_prompt import (  # noqa: E402
    VerdictRequest,
    build_council_prompt,
)
from src.coach.consensus.history_injector import HistoryTriplet  # noqa: E402

# If council_prompt was already imported under a relative ICU_LOG_DIR
# (e.g. earlier in a pytest session), rebind its module-level logger to one
# rooted at the absolute icu/ path so writes never depend on CWD.
if not _council_prompt_mod._log.log_dir.is_absolute():
    _council_prompt_mod._log = _get_logger("consensus")


_NEXT_STEPS = (
    "Next steps:\n"
    "  1. Open the file, copy its contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save the LLM response as council.response.md.\n"
    "  4. Run: scripts/finalize_consensus.py --response council.response.md "
    "\\\n"
    "         --ledger coach_memory/ledger/decisions.jsonl"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 - assemble a 4-section council prompt from a "
            "VerdictRequest JSON. API-free; emits a markdown file the "
            "user pastes into Gemini."
        ),
    )
    p.add_argument("--verdict-request", required=True, type=Path,
                   help="Path to VerdictRequest JSON.")
    p.add_argument("--history", type=Path, default=None,
                   help="Optional: path to JSON list of HistoryTriplet.")
    p.add_argument("--out", type=Path,
                   default=Path("council.prompt.md"),
                   help="Output markdown path (default ./council.prompt.md)")
    return p.parse_args(argv)


def _load_json_or_die(path: Path, label: str) -> object:
    if not path.exists():
        print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {label} JSON is malformed at {path}: {exc}",
              file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"ERROR: cannot read {label} file {path}: {exc}",
              file=sys.stderr)
        raise SystemExit(2)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        # argparse exits with 2 on parse errors - pass through.
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        req_payload = _load_json_or_die(args.verdict_request,
                                        "verdict-request")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        request = VerdictRequest.model_validate(req_payload)
    except Exception as exc:  # pydantic.ValidationError or similar
        print(f"ERROR: verdict-request schema validation failed: {exc}",
              file=sys.stderr)
        return 2

    history: list[HistoryTriplet] | None = None
    if args.history is not None:
        try:
            hist_payload = _load_json_or_die(args.history, "history")
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        if not isinstance(hist_payload, list):
            print(
                f"ERROR: history JSON must be a list, got "
                f"{type(hist_payload).__name__}",
                file=sys.stderr,
            )
            return 2
        try:
            history = [HistoryTriplet.model_validate(t)
                       for t in hist_payload]
        except Exception as exc:
            print(f"ERROR: history triplet schema validation failed: {exc}",
                  file=sys.stderr)
            return 2

    body = build_council_prompt(request, history=history)

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write output {args.out}: {exc}",
              file=sys.stderr)
        return 3

    print(f"Wrote council prompt -> {args.out}")
    print(_NEXT_STEPS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
