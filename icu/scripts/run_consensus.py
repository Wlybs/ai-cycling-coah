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
from src.coach.evidence.corpus import CorpusReader  # noqa: E402
from src.coach.evidence.prompt_section import render_references_section  # noqa: E402
from src.coach.evidence.retriever import retrieve as _retrieve_evidence  # noqa: E402
from src.coach.evidence.types import CitationContext  # noqa: E402

_KNOWN_PHASES = {"base", "build", "peak", "competitive", "transition", "off_season"}

# If council_prompt was already imported under a relative ICU_LOG_DIR
# (e.g. earlier in a pytest session), rebind its module-level logger to one
# rooted at the absolute icu/ path so writes never depend on CWD.
if not _council_prompt_mod._log.log_dir.is_absolute():
    _council_prompt_mod._log = _get_logger("consensus")


_NEXT_STEPS_COUNCIL = (
    "Next steps (council mode):\n"
    "  1. Open the file, copy contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save reply as council.response.md.\n"
    "  4. Run: scripts/finalize_consensus.py --response council.response.md "
    "\\\n"
    "         --ledger coach_memory/ledger/decisions.jsonl"
)
_NEXT_STEPS_STRICT = (
    "Next steps (strict step 1 — Planner):\n"
    "  1. Open 1_planner.prompt.md, copy contents.\n"
    "  2. Paste into Gemini CLI / Claude Code coach mode.\n"
    "  3. Save reply as 1_planner.response.md (same dir).\n"
    "  4. Run: scripts/finalize_consensus.py --mode strict --step 2 \\\n"
    "         --consensus-dir <this_dir>"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 - assemble a council prompt; --mode strict "
                    "+ --reuse drive the strict 4-step variant.",
    )
    p.add_argument("--mode", choices=("council", "strict"),
                   default="council")
    p.add_argument("--verdict-request", type=Path, default=None,
                   help="Required unless --reuse.")
    p.add_argument("--history", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None,
                   help="Default: ./council.prompt.md (council) or "
                        "./coach_memory/consensus/1_planner.prompt.md "
                        "(strict). Ignored when --reuse is set.")
    p.add_argument("--evidence-corpus", type=Path,
                   default=Path("evidence_corpus"),
                   help="Path to evidence corpus dir (default: evidence_corpus)")
    p.add_argument("--evidence-query", type=str, default=None,
                   help="Comma-separated query terms; auto-derived if omitted")
    p.add_argument("--evidence-top-k", type=int, default=3,
                   help="Top-K evidence cards to inject (default 3)")
    p.add_argument("--no-evidence", action="store_true",
                   help="Skip evidence retrieval entirely (debug/test)")
    p.add_argument("--reuse", type=Path, default=None,
                   help="Strict only: reuse an existing consensus dir.")
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


def _derive_query_terms(request: "VerdictRequest") -> list[str]:
    """Auto-derive evidence query terms from request when --evidence-query absent."""
    terms: list[str] = []
    phase = getattr(request.athlete_state, "phase", None)
    if phase:
        terms.append(str(phase).lower())
    focus = (request.periodization_summary or {}).get("focus_theme")
    if isinstance(focus, str):
        terms.extend(t for t in focus.lower().split() if t.isalnum())
    if not terms:
        terms = ["base", "endurance"]
    return terms


def _retrieve_and_render_refs(args: argparse.Namespace,
                              request: "VerdictRequest") -> str:
    """Retrieve top-K evidence + render markdown. Never raises; '' on any error."""
    if args.no_evidence:
        return ""
    try:
        corpus_dir: Path = args.evidence_corpus
        if not corpus_dir.exists():
            print(f"WARN: evidence corpus not found at {corpus_dir}; "
                  f"skipping references", file=sys.stderr)
            return ""
        cards = CorpusReader(corpus_dir).load_active()
        if args.evidence_query:
            query_terms = [t.strip().lower() for t in args.evidence_query.split(",")
                           if t.strip()]
        else:
            query_terms = _derive_query_terms(request)
        phase_raw = getattr(request.athlete_state, "phase", None)
        phase_low = str(phase_raw).lower() if phase_raw else None
        phase = phase_low if phase_low in _KNOWN_PHASES else None
        ctx = CitationContext(
            query_terms=query_terms,
            phase=phase,
            top_k=args.evidence_top_k,
        )
        retrieved = _retrieve_evidence(context=ctx, cards=cards)
        return render_references_section(retrieved)
    except Exception as exc:  # never block prompt write
        print(f"WARN: evidence retrieval failed: {exc}", file=sys.stderr)
        return ""


def _persist_inputs(consensus_dir: Path,
                    request_payload: object,
                    history_payload: object | None) -> None:
    consensus_dir.mkdir(parents=True, exist_ok=True)
    (consensus_dir / "verdict_request.json").write_text(
        json.dumps(request_payload, indent=2,
                   sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    if history_payload is not None:
        (consensus_dir / "history.json").write_text(
            json.dumps(history_payload, indent=2,
                       sort_keys=True, ensure_ascii=False),
            encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    # Resolve inputs based on mode + flags.
    if args.mode == "strict" and args.reuse is not None:
        request_path = args.reuse / "verdict_request.json"
        history_path = args.reuse / "history.json"
        if not history_path.exists():
            history_path = None
        out_path = args.reuse / "1_planner.prompt.md"
    else:
        if args.verdict_request is None:
            print("ERROR: --verdict-request required (or use --reuse "
                  "with --mode strict).", file=sys.stderr)
            raise SystemExit(2)
        request_path = args.verdict_request
        history_path = args.history
        if args.out is not None:
            out_path = args.out
        elif args.mode == "strict":
            out_path = Path("coach_memory/consensus/1_planner.prompt.md")
        else:
            out_path = Path("council.prompt.md")

    try:
        req_payload = _load_json_or_die(request_path, "verdict-request")
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        request = VerdictRequest.model_validate(req_payload)
    except Exception as exc:
        print(f"ERROR: verdict-request schema validation: {exc}",
              file=sys.stderr)
        return 2

    history: list[HistoryTriplet] | None = None
    history_payload_for_persist: object | None = None
    if history_path is not None:
        try:
            hist_payload = _load_json_or_die(history_path, "history")
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        if not isinstance(hist_payload, list):
            print(f"ERROR: history JSON must be a list, got "
                  f"{type(hist_payload).__name__}", file=sys.stderr)
            return 2
        try:
            history = [HistoryTriplet.model_validate(t)
                       for t in hist_payload]
            history_payload_for_persist = hist_payload
        except Exception as exc:
            print(f"ERROR: history schema: {exc}", file=sys.stderr)
            return 2

    if args.mode == "strict":
        from src.coach.consensus.strict_prompt import build_strict_prompt
        body = build_strict_prompt(step=1, request=request, history=history)
        next_steps = _NEXT_STEPS_STRICT
    else:
        body = build_council_prompt(request, history=history)
        next_steps = _NEXT_STEPS_COUNCIL

    body = body + _retrieve_and_render_refs(args, request)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write output {out_path}: {exc}",
              file=sys.stderr)
        return 3

    try:
        _persist_inputs(out_path.parent, req_payload,
                        history_payload_for_persist)
    except OSError as exc:
        print(f"ERROR: cannot persist inputs to {out_path.parent}: {exc}",
              file=sys.stderr)
        return 3

    print(f"Wrote {args.mode} prompt -> {out_path}")
    print(next_steps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
