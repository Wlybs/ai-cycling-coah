"""CLI: validate evidence_corpus/ — run before any commit that touches cards.

Usage:
    .venv/bin/python scripts/evidence_lint.py [--corpus PATH]

Exit codes:
    0  clean
    1  one or more violations (printed to stderr)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.evidence.corpus import lint_corpus  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", type=Path, default=Path("evidence_corpus"),
        help="path to evidence corpus directory (default: evidence_corpus)",
    )
    args = parser.parse_args(argv)

    if not args.corpus.exists():
        print(f"ERROR: corpus path does not exist: {args.corpus}", file=sys.stderr)
        return 1

    violations = lint_corpus(args.corpus)
    if not violations:
        print(f"✓ corpus clean ({args.corpus})")
        return 0

    print(f"✗ {len(violations)} violation(s) in {args.corpus}:", file=sys.stderr)
    for v in violations:
        print(f"  [{v.ulid}] {v.field}: {v.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
