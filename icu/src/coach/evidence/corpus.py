"""Phase 4 Evidence — file-based CorpusReader + lint helpers."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from src.coach.evidence.types import EvidenceCard


_FRONTMATTER_DELIM = "+++"
_REQUIRED_PHASES = {"build", "peak", "competitive"}


@dataclass(frozen=True)
class Violation:
    ulid: str
    field: str
    message: str


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split `+++\\nTOML\\n+++\\n<body>` → (parsed dict, body str)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise ValueError("missing opening +++ frontmatter delimiter")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("missing closing +++ frontmatter delimiter")
    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:]).strip()
    try:
        parsed = tomllib.loads(fm_text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"frontmatter TOML parse failed: {exc}") from exc
    return parsed, body


def _build_card(parsed: dict, body: str) -> EvidenceCard:
    payload = dict(parsed)
    payload["body_md"] = body
    sup = payload.get("superseded_by")
    if sup == "":
        payload["superseded_by"] = None
    return EvidenceCard(**payload)


class CorpusReader:
    """Append-only file-backed reader. Filename must equal `{ulid}.md`."""

    def __init__(self, corpus_dir: Path) -> None:
        self.corpus_dir = Path(corpus_dir)

    def _iter_card_files(self):
        if not self.corpus_dir.exists():
            return
        for p in sorted(self.corpus_dir.glob("*.md")):
            if p.name.startswith("_"):
                continue
            yield p

    def load_all(self) -> list[EvidenceCard]:
        cards: list[EvidenceCard] = []
        for path in self._iter_card_files():
            text = path.read_text(encoding="utf-8")
            parsed, body = _split_frontmatter(text)
            card = _build_card(parsed, body)
            expected_name = f"{card.ulid}.md"
            if path.name != expected_name:
                raise ValueError(
                    f"filename {path.name!r} does not match frontmatter ulid "
                    f"({card.ulid!r}); expected {expected_name!r}"
                )
            cards.append(card)
        return cards

    def load_active(self) -> list[EvidenceCard]:
        return [c for c in self.load_all() if c.status == "active"]

    def find(self, ulid: str) -> EvidenceCard | None:
        for c in self.load_all():
            if c.ulid == ulid:
                return c
        return None


def lint_corpus(corpus_dir: Path) -> list[Violation]:
    """Return all violations; empty list = clean. Never raises."""
    violations: list[Violation] = []
    cards: list[EvidenceCard] = []
    reader = CorpusReader(corpus_dir)
    for path in reader._iter_card_files():
        try:
            text = path.read_text(encoding="utf-8")
            parsed, body = _split_frontmatter(text)
            card = _build_card(parsed, body)
        except (ValueError, ValidationError) as exc:
            violations.append(Violation(
                ulid=path.stem, field="frontmatter",
                message=f"parse failed: {exc}",
            ))
            continue
        expected_name = f"{card.ulid}.md"
        if path.name != expected_name:
            violations.append(Violation(
                ulid=card.ulid, field="filename",
                message=f"filename {path.name!r} != {expected_name!r}",
            ))
        cards.append(card)

    known_ulids = {c.ulid for c in cards}
    for c in cards:
        if c.superseded_by is not None and c.superseded_by not in known_ulids:
            violations.append(Violation(
                ulid=c.ulid, field="superseded_by",
                message=f"superseded_by={c.superseded_by!r} references unknown ULID",
            ))

    actives = [c for c in cards if c.status == "active"]
    if not actives:
        violations.append(Violation(
            ulid="-", field="corpus",
            message="corpus has no active cards (need at least one)",
        ))

    covered_phases = set()
    for c in actives:
        covered_phases.update(c.phase)
    missing = _REQUIRED_PHASES - covered_phases
    if missing:
        violations.append(Violation(
            ulid="-", field="corpus",
            message=f"phase coverage gap: missing {sorted(missing)} "
                    f"(need at least one active card per {sorted(_REQUIRED_PHASES)})",
        ))

    return violations
