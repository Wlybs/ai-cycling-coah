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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/finalize_consensus.py ...` from icu/.
_ICU_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ICU_ROOT))
os.environ.setdefault("ICU_LOG_DIR", str(_ICU_ROOT / "logs"))

from src.coach.consensus.council_prompt import VerdictRequest  # noqa: E402
from src.coach.consensus.history_injector import HistoryTriplet  # noqa: E402
from src.coach.consensus.response_parser import parse as parse_council  # noqa: E402
from src.coach.consensus.strict_prompt import (  # noqa: E402
    STRICT_STEP_TO_ROLE,
    build_strict_prompt,
)
from src.coach.consensus.types import (  # noqa: E402
    ConsensusValidationError,
    CouncilVerdict,
)
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.types import AthleteStateRef  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


_NEXT_STEPS_STRICT_TEMPLATE: dict[int, str] = {
    2: ("Next steps (strict step 2 — Critic):\n"
        "  1. Open 2_critic.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 2_critic.response.md.\n"
        "  3. Run: scripts/finalize_consensus.py --mode strict --step 3 "
        "--consensus-dir <this_dir>"),
    3: ("Next steps (strict step 3 — Physiologist):\n"
        "  1. Open 3_physiologist.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 3_physiologist.response.md.\n"
        "  3. Run: scripts/finalize_consensus.py --mode strict --step 4 "
        "--consensus-dir <this_dir>"),
    4: ("Next steps (strict step 4 — Arbiter):\n"
        "  1. Open 4_arbiter.prompt.md, paste into Gemini.\n"
        "  2. Save reply as 4_arbiter.response.md.\n"
        "  3. Re-run step 4 (dry-run preview), then add --confirm + "
        "--athlete-state + --ledger to append."),
}


_TAG_RE_CACHE: dict[str, re.Pattern] = {}


def _extract_role_body(md: str, role: str) -> str:
    """Body inside <role>...</role>; raise on missing/duplicate/blank."""
    pat = _TAG_RE_CACHE.get(role)
    if pat is None:
        pat = re.compile(rf"<{role}>(.*?)</{role}>",
                         re.DOTALL | re.IGNORECASE)
        _TAG_RE_CACHE[role] = pat
    matches = pat.findall(md)
    if len(matches) != 1:
        raise ValueError(f"malformed role tag: expected exactly one "
                         f"<{role}>...</{role}>, got {len(matches)}")
    body = matches[0].strip()
    if not body:
        raise ValueError(f"role tag <{role}> body is blank")
    return body


def _load_strict_inputs(
    consensus_dir: Path,
) -> tuple[VerdictRequest, list[HistoryTriplet] | None]:
    req_path = consensus_dir / "verdict_request.json"
    if not req_path.exists():
        raise FileNotFoundError(
            f"verdict_request.json not in {consensus_dir}")
    req_payload = json.loads(req_path.read_text(encoding="utf-8"))
    request = VerdictRequest.model_validate(req_payload)
    history: list[HistoryTriplet] | None = None
    hist_path = consensus_dir / "history.json"
    if hist_path.exists():
        hp = json.loads(hist_path.read_text(encoding="utf-8"))
        if not isinstance(hp, list):
            raise ValueError("history.json must be a JSON list")
        history = [HistoryTriplet.model_validate(t) for t in hp]
    return request, history


def _read_prior_responses(consensus_dir: Path, step: int) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in range(1, step):
        role = STRICT_STEP_TO_ROLE[s]
        path = consensus_dir / f"{s}_{role}.response.md"
        if not path.exists():
            raise FileNotFoundError(
                f"prior strict response missing: {path.name}")
        md = path.read_text(encoding="utf-8")
        body = _extract_role_body(md, role)
        out[role] = f"<{role}>\n{body}\n</{role}>"
    return out


# ---------- argparse ----------

def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 - finalize a council response. Default = "
                    "dry-run; --confirm to append. --mode strict drives "
                    "the 4-step state machine via --step + --consensus-dir.",
    )
    p.add_argument("--mode", choices=("council", "strict"),
                   default="council")
    p.add_argument("--response", type=Path, default=None)
    p.add_argument("--ledger", type=Path, default=None)
    p.add_argument("--athlete-state", type=Path, default=None)
    p.add_argument("--step", type=int, choices=(2, 3, 4), default=None,
                   help="Strict mode only.")
    p.add_argument("--consensus-dir", type=Path, default=None,
                   help="Strict mode only.")
    gate = p.add_mutually_exclusive_group()
    gate.add_argument("--confirm", action="store_true")
    gate.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> int | None:
    if args.mode == "strict":
        if args.step is None:
            print("ERROR: --mode strict requires --step {2,3,4}.",
                  file=sys.stderr)
            return 2
        if args.consensus_dir is None:
            print("ERROR: --mode strict requires --consensus-dir <dir>.",
                  file=sys.stderr)
            return 2
        if (args.step == 4 and args.confirm
                and (args.ledger is None or args.athlete_state is None)):
            print("ERROR: strict step 4 --confirm requires --ledger "
                  "AND --athlete-state.", file=sys.stderr)
            return 2
        return None
    if args.step is not None:
        print("ERROR: --step requires --mode strict.", file=sys.stderr)
        return 2
    if (args.response is None or args.ledger is None
            or args.athlete_state is None):
        print("ERROR: council mode requires --response, --ledger, "
              "--athlete-state.", file=sys.stderr)
        return 2
    return None


def _strict_main(args: argparse.Namespace) -> int:
    consensus_dir: Path = args.consensus_dir
    if not consensus_dir.is_dir():
        print(f"ERROR: --consensus-dir not a directory: {consensus_dir}",
              file=sys.stderr)
        return 2

    step: int = args.step
    arbiter_response = consensus_dir / "4_arbiter.response.md"
    if step == 4 and (args.confirm or arbiter_response.exists()):
        return _strict_finalize_step4(args, consensus_dir)

    try:
        request, history = _load_strict_inputs(consensus_dir)
        priors = _read_prior_responses(consensus_dir, step)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: strict step {step} input: {exc}",
              file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: strict step {step} validation: {exc}",
              file=sys.stderr)
        return 2

    try:
        body = build_strict_prompt(
            step=step, request=request,
            history=history, prior_responses=priors)
    except ValueError as exc:
        print(f"ERROR: build_strict_prompt step {step}: {exc}",
              file=sys.stderr)
        return 2

    role = STRICT_STEP_TO_ROLE[step]
    out_path = consensus_dir / f"{step}_{role}.prompt.md"
    try:
        out_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write {out_path}: {exc}", file=sys.stderr)
        return 3

    print(f"Wrote strict step-{step} prompt -> {out_path}")
    print(_NEXT_STEPS_STRICT_TEMPLATE[step])
    return 0


def _strict_finalize_step4(args: argparse.Namespace,
                           consensus_dir: Path) -> int:
    print("[T68.2 stub] step 4 finalize not yet implemented",
          file=sys.stderr)
    return 0


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

    rc = _validate_args(args)
    if rc is not None:
        return rc

    if args.mode == "strict":
        return _strict_main(args)

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
