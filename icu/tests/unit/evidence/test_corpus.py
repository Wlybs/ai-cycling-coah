"""T74: CorpusReader (TOML frontmatter + .md body) + lint helpers."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.coach.evidence.corpus import CorpusReader, lint_corpus
from src.coach.evidence.types import EvidenceCard


# Fixed valid ULIDs for fixtures
ULID_T = "01HXR0NM8KT0000000000000A1"
ULID_S = "01HXR0NM8KS0000000000000B2"
ULID_X = "01HXR0NM8KX0000000000000C3"


def _write_card(corpus: Path, ulid: str, *, status: str = "active",
                superseded_by: str | None = None,
                tags: list[str] | None = None,
                phase: list[str] | None = None) -> Path:
    tags = tags or ["taper"]
    phase = phase or ["competitive"]
    sup_line = f'superseded_by = "{superseded_by}"' if superseded_by else 'superseded_by = ""'
    tags_str = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
    phase_str = "[" + ", ".join(f'"{p}"' for p in phase) + "]"
    body = textwrap.dedent(f"""
    +++
    ulid = "{ulid}"
    title = "Test card title for ULID {ulid}"
    authors = ["Author A", "Author B"]
    year = 2020
    source = "Test Journal 1(2):3-4"
    tags = {tags_str}
    phase = {phase_str}
    applies_to = []
    finding = "Some finding statement that is at least 20 characters long."
    dosing_hint = "Some dosing hint."
    contraindications = []
    status = "{status}"
    {sup_line}
    +++

    # Body
    Lorem ipsum taper polarized recovery.
    """).strip()
    path = corpus / f"{ulid}.md"
    path.write_text(body, encoding="utf-8")
    return path


# ---------- CorpusReader ----------

def test_corpus_reader_load_all_three_cards(tmp_path):
    _write_card(tmp_path, ULID_T)
    _write_card(tmp_path, ULID_S)
    _write_card(tmp_path, ULID_X)
    cards = CorpusReader(tmp_path).load_all()
    assert len(cards) == 3
    assert {c.ulid for c in cards} == {ULID_T, ULID_S, ULID_X}
    assert all(isinstance(c, EvidenceCard) for c in cards)


def test_corpus_reader_load_active_filters_deprecated(tmp_path):
    _write_card(tmp_path, ULID_T, status="active")
    _write_card(tmp_path, ULID_S, status="deprecated", superseded_by=ULID_T)
    actives = CorpusReader(tmp_path).load_active()
    assert {c.ulid for c in actives} == {ULID_T}


def test_corpus_reader_find_hit_and_miss(tmp_path):
    _write_card(tmp_path, ULID_T)
    reader = CorpusReader(tmp_path)
    assert reader.find(ULID_T) is not None
    assert reader.find(ULID_S) is None


def test_corpus_reader_filename_must_match_ulid(tmp_path):
    # Write valid frontmatter with ULID_T but save under wrong filename
    _write_card(tmp_path, ULID_T).rename(tmp_path / "wrong-name.md")
    with pytest.raises(ValueError, match="filename"):
        CorpusReader(tmp_path).load_all()


def test_corpus_reader_skips_underscore_prefix(tmp_path):
    _write_card(tmp_path, ULID_T)
    (tmp_path / "_template.md").write_text("any junk", encoding="utf-8")
    cards = CorpusReader(tmp_path).load_all()
    assert {c.ulid for c in cards} == {ULID_T}


def test_corpus_reader_empty_dir_returns_empty_list(tmp_path):
    assert CorpusReader(tmp_path).load_all() == []


def test_corpus_reader_malformed_frontmatter_raises(tmp_path):
    bad = tmp_path / f"{ULID_T}.md"
    bad.write_text("no frontmatter at all", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        CorpusReader(tmp_path).load_all()


# ---------- lint_corpus ----------

def test_lint_clean_corpus_returns_no_violations(tmp_path):
    _write_card(tmp_path, ULID_T, phase=["competitive"])
    _write_card(tmp_path, ULID_S, phase=["build"])
    _write_card(tmp_path, ULID_X, phase=["peak"])
    violations = lint_corpus(tmp_path)
    assert violations == []


def test_lint_detects_stale_superseded_by(tmp_path):
    # ULID_T claims to be superseded by ULID_S, but ULID_S doesn't exist
    _write_card(tmp_path, ULID_T, status="deprecated", superseded_by=ULID_S)
    violations = lint_corpus(tmp_path)
    assert any("superseded_by" in v.message for v in violations)


def test_lint_requires_at_least_one_active_card(tmp_path):
    _write_card(tmp_path, ULID_T, status="deprecated", superseded_by=ULID_S)
    _write_card(tmp_path, ULID_S, status="deprecated", superseded_by=ULID_T)
    violations = lint_corpus(tmp_path)
    assert any("active" in v.message.lower() for v in violations)


def test_lint_requires_phase_coverage(tmp_path):
    # Only "competitive" phase — missing build/peak
    _write_card(tmp_path, ULID_T, phase=["competitive"])
    violations = lint_corpus(tmp_path)
    assert any("phase coverage" in v.message.lower() for v in violations)
