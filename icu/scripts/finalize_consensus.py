"""Phase 3 — finalize a Gemini council response into the decision ledger.

Default behaviour is DRY-RUN: print the would-be ledger entry and exit 0.
With --confirm, validate + append the entry; respect content-hash
idempotency (T66.3) so a re-run on the same response file is a no-op.

Reads:
  --response       path to council.response.md (the user's pasted Gemini reply)
  --ledger         path to decisions.jsonl
  --athlete-state  path to JSON file matching AthleteStateRef shape

Writes (only when --confirm):
  one append line in the ledger JSONL via LedgerWriter.record(...)

Exit codes:
  0 - success (dry-run, applied, or duplicate-skipped)
  2 - input error (missing file, malformed JSON, parser violations,
                   schema validation failure)
  3 - internal/IO error during ledger write

API_FREE: no LLM SDK, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Sequence

# Allow `python scripts/finalize_consensus.py ...` from icu/.
_ICU_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ICU_ROOT))
os.environ.setdefault("ICU_LOG_DIR", str(_ICU_ROOT / "logs"))

from src.coach.consensus.response_parser import parse as parse_council  # noqa: E402
from src.coach.consensus.types import (  # noqa: E402
    ConsensusValidationError,
    CouncilVerdict,
)
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.types import AthleteStateRef  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


# ---------- argparse ----------

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 - finalize a 4-role council response into the ledger. "
            "Default = dry-run print; pass --confirm to actually append."
        ),
    )
    p.add_argument("--response", required=True, type=Path,
                   help="Path to council.response.md (Gemini reply).")
    p.add_argument("--ledger", required=True, type=Path,
                   help="Path to ledger JSONL (decisions.jsonl).")
    p.add_argument("--athlete-state", required=True, type=Path,
                   help="Path to AthleteStateRef JSON.")
    gate = p.add_mutually_exclusive_group()
    gate.add_argument("--confirm", action="store_true",
                      help="Actually append to the ledger. "
                           "Default = dry-run.")
    gate.add_argument("--dry-run", action="store_true",
                      help="Explicit dry-run (default behavior).")
    return p.parse_args(argv)


# ---------- entry helpers ----------

def _content_hash(verdict: CouncilVerdict) -> str:
    """Stable content-hash for idempotency (T66.3).

    Hash domain: mode + verdict + confidence + justification +
    summary_json (sorted) + concatenated expert role bodies.
    Deterministic across re-runs because we sort dict keys + use UTF-8.
    """
    blob = json.dumps(
        {
            "mode": verdict.mode,
            "verdict": verdict.verdict,
            "confidence": round(verdict.confidence, 6),
            "justification": verdict.justification,
            "summary_json": verdict.summary_json,
            "turns": [
                {"role": t.role, "body_md": t.body_md}
                for t in verdict.expert_turns
            ],
        },
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _print_dry_run(verdict: CouncilVerdict,
                   athlete_state: AthleteStateRef,
                   evidence_path: Path,
                   content_hash: str) -> None:
    payload = verdict.model_dump()
    entry_preview = {
        "decision_type": "consensus_verdict",
        "source": "consensus.council",
        "athlete_state_ref": athlete_state.model_dump(),
        "confidence": verdict.confidence,
        "evidence_refs": [str(evidence_path)],
        "payload": payload,
        "content_hash": content_hash,
    }
    print("[DRY-RUN] would append the following ledger entry:")
    print(json.dumps(entry_preview, indent=2,
                     sort_keys=True, ensure_ascii=False))
    print("\nRe-run with --confirm to actually append.")


# ---------- main ----------

def _read_response(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: response file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read response file: {exc}", file=sys.stderr)
        raise SystemExit(2)


def _read_athlete_state(path: Path) -> AthleteStateRef:
    if not path.exists():
        print(f"ERROR: athlete-state file not found: {path}",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: athlete-state JSON malformed: {exc}",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        return AthleteStateRef.model_validate(raw)
    except Exception as exc:
        print(f"ERROR: athlete-state schema validation failed: {exc}",
              file=sys.stderr)
        raise SystemExit(2)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    # ---- Phase 1: read + parse + validate (BEFORE any ledger touch) ----
    try:
        response_md = _read_response(args.response)
        athlete_state = _read_athlete_state(args.athlete_state)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        verdict = parse_council(response_md, mode="council")
    except ConsensusValidationError as exc:
        print("ERROR: council response failed parser validation:",
              file=sys.stderr)
        for v in exc.violations:
            print(f"  - {v}", file=sys.stderr)
        return 2

    content_hash = _content_hash(verdict)

    # ---- Phase 2: dry-run vs confirm ----
    if not args.confirm:
        _print_dry_run(verdict, athlete_state, args.response, content_hash)
        return 0

    # T66.2 will fill in ledger append; T66.1 only ships dry-run.
    return _append_to_ledger(verdict, athlete_state, args.response,
                             args.ledger, content_hash)


def _append_to_ledger(
    verdict: CouncilVerdict,
    athlete_state: AthleteStateRef,
    evidence_path: Path,
    ledger_path: Path,
    content_hash: str,
) -> int:
    """Append one consensus_verdict entry to the ledger (idempotent).

    Pre-conditions (must all be true before this function is reached):
      - response file was read successfully
      - athlete-state JSON parsed AND schema-validated
      - council response parsed via response_parser.parse - no violations

    Idempotency probe (T66.3): scan existing ledger for a prior
    consensus_verdict entry with the same payload.content_hash. On hit,
    print 'Already finalized: ...' and return 0 without writing. The
    probe runs BEFORE LedgerWriter.record so the rollback contract from
    T66.2 is preserved (no bytes mutated on duplicate).

    On success: prints the new entry_id; returns 0.
    On IO failure during the actual write: prints to stderr, returns 3.
    """
    # ---- idempotency probe ----
    if ledger_path.exists():
        try:
            reader = LedgerReader(ledger_path)
            existing = reader.query(
                decision_type="consensus_verdict",
                limit=None,
            )
        except Exception as exc:
            print(f"ERROR: ledger read for idempotency probe failed: {exc}",
                  file=sys.stderr)
            return 3
        for prior in existing:
            if prior.payload.get("content_hash") == content_hash:
                print(
                    f"Already finalized: content_hash={content_hash[:12]}... "
                    f"existing entry_id={prior.entry_id}"
                )
                return 0

    # ---- new append ----
    payload = verdict.model_dump()
    payload["content_hash"] = content_hash

    try:
        writer = LedgerWriter(ledger_path)
        entry_id = writer.record(
            decision_type="consensus_verdict",
            source="consensus.council",
            athlete_state=athlete_state,
            payload=payload,
            evidence_refs=[str(evidence_path)],
            confidence=verdict.confidence,
            superseded_by=None,
        )
    except Exception as exc:  # IO / fcntl / fsync failure
        print(f"ERROR: ledger write failed: {exc}", file=sys.stderr)
        return 3

    print(f"Appended consensus_verdict entry_id={entry_id} "
          f"(content_hash={content_hash[:12]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
