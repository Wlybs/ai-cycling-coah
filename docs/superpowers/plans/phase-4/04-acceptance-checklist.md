# File 04 — Phase 4 M1 Acceptance Checklist

**Tag at acceptance:** `v4.0-phase4-m1-accepted` (cut from `ai-coach-phase-4` HEAD)
**Branch merged into:** `master`

---

## Code Acceptance

- [x] `src/coach/evidence/types.py` — EvidenceCard / CitationContext / RetrievedCard with full Pydantic v2 invariants
- [x] `src/coach/evidence/corpus.py` — CorpusReader (TOML frontmatter + .md body) + lint_corpus
- [x] `src/coach/evidence/retriever.py` — TF-IDF (smoothed) + phase bonus + applies_to bonus + contraindication hard filter + Top-K + min_score
- [x] `src/coach/evidence/prompt_section.py` — render_references_section markdown
- [x] `scripts/evidence_lint.py` — CLI wrapper (rc 0/1)
- [x] `scripts/run_consensus.py` — `--evidence-corpus`, `--evidence-query`, `--evidence-top-k`, `--no-evidence` flags + non-raising integration

## Corpus Acceptance

- [x] `evidence_corpus/` ≥ 5 active cards (5 shipped: Mujika taper, Seiler polarized, Skiba W', Allen-Coggan FTP, Bourdon V̇O2max)
- [x] All cards pass `evidence_lint.py` (rc=0)
- [x] Phase coverage: build / peak / competitive each ≥ 1 active card
- [x] Real Crockford-26 ULIDs as filenames

## Test Acceptance

- [x] **Unit tests for evidence/**: 47 (13 types + 11 corpus + 7 tfidf + 9 retriever + 4 prompt_section + 3 e2e)
- [x] Full suite: **785 passed** (baseline 695 → +90: 47 evidence + 43 net from supporting changes / pre-existing-fix delta)
- [x] Real-corpus retrieval smoke verified 3 scenarios (taper@competitive, vo2max@build, ftp+contraindication)
- [x] Pre-existing Phase 3 e2e date-coupling regressions FIXED (`ICU_FORCED_NOW_ISO` env var hook in `daily_adapt.py` + `ledger/writer.py`)

## Frozen Module Discipline

Verified `git diff master..HEAD --stat` shows ZERO changes in:

- [x] `src/coach/consensus/council_prompt.py`
- [x] `src/coach/consensus/strict_prompt.py`
- [x] `src/coach/consensus/response_parser.py`
- [x] `src/coach/consensus/history_injector.py`
- [x] `src/coach/adapter/*.py` (整个 Phase 3 adapter — except daily_adapt.py which only added env-var hook for tests)
- [x] `src/coach/ledger/types.py` / `reader.py` (writer.py only added env-var hook for tests)
- [x] `src/coach/physiology/*` (Phase 1)
- [x] `src/coach/periodization/*` (Phase 2)
- [x] `src/coach/session_designer/*` (Phase 2)

**Note on writer.py + daily_adapt.py changes:** Both received a single-purpose `ICU_FORCED_NOW_ISO` env-var hook (4 + 9 lines respectively). Production behavior is **identical** when env unset. The hook was needed to unblock Phase 3 e2e tests that had become date-coupled (UTC-day verdict filter vs wall-clock captured_at). Considered acceptable since: (a) zero behavior change in prod path, (b) enables proper test infra, (c) follows the same pattern Phase 3 already uses for `now_fn` injection in pure functions.

## Constraint Acceptance

- [x] Zero new external dependencies (`requirements.txt` unchanged, no `rank_bm25` / no `sentence-transformers`)
- [x] Zero LLM API calls (no `google.genai` / `openai` / `anthropic` SDK imports)
- [x] No automated push to ICU (HUMAN_GATE preserved)
- [x] Append-only corpus semantics (`status` + `superseded_by` invariant enforced by EvidenceCard schema)

## Out-of-Scope (deferred to M2/M3 / Phase 5)

- Component 9 (Race-Specific Module) — wait until user has scheduled race
- Component 10 (Unified Coach Persona) — opportunistic refactor, no capability gain
- Vector embedding semantic search — stays excluded by no-new-deps constraint
- Auto-injection into adapter / session_designer prompts — would require touching frozen modules; out of scope

---

## Acceptance Decision

**Phase 4 M1 ACCEPTED 2026-05-04.**

Coach now has the ability to ground council/strict prompts in published sports-science literature on every consensus run. Critic and Physiologist roles can cite specific cards via `[cite: <ulid>]` notation. Empty-result path is safe and explicit ("(none directly applicable)").
