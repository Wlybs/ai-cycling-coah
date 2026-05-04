# File 03 — Evidence Prompt Integration

**Tasks:** T77 (`prompt_section.py`) + T78 (`run_consensus.py` 接入 + e2e)
**Branch:** `ai-coach-phase-4`
**Frozen modules:** `council_prompt.py`, `strict_prompt.py`, `response_parser.py`, `history_injector.py` —— **all forbidden to edit**

---

## T77 — `src/coach/evidence/prompt_section.py`

### Public API

```python
def render_references_section(retrieved: list[RetrievedCard]) -> str: ...
```

### Output formats

**Empty input** → returns:
```markdown

## References (auto-retrieved by Phase 4 evidence retriever)

(none directly applicable for this context)
```

**Non-empty** → returns:
```markdown

## References (auto-retrieved by Phase 4 evidence retriever)

1. **[<ulid>] <title>** (score <0.000>)
   - matched: term1, term2, term3
   - finding: <card.finding>
   - dosing_hint: <card.dosing_hint>

2. **[<ulid2>] ...**
```

### Tests (`tests/unit/evidence/test_prompt_section.py`, ≥ 4)

1. Empty list → "(none directly applicable" present
2. Single card → "1. **[<ulid>]" + "matched:" + "finding:" + "dosing_hint:" all present
3. 3 cards → headers "1. ", "2. ", "3. " all present in order
4. matched_terms with empty list → "matched: (none)" or similar safe rendering

---

## T78 — `scripts/run_consensus.py` integration

### CLI additions

| Flag | Type | Default | Behavior |
|---|---|---|---|
| `--evidence-corpus PATH` | Path | `evidence_corpus` | Path to corpus dir |
| `--evidence-query t1,t2` | str | derived from athlete_state | comma-separated query terms |
| `--evidence-top-k N` | int | 3 | passed to CitationContext.top_k |
| `--no-evidence` | flag | False | Skip retrieval entirely (debug/test) |

### Auto-derive query terms (if `--evidence-query` not provided)

From `request.athlete_state` and `request.periodization_summary`:
- If `athlete_state.phase` (str) present → include it as a term
- If `periodization_summary.focus_theme` (str) present → tokenize lowercase + add
- If empty → fall back to `["base", "endurance"]` (safe generic)

Phase derivation: `context.phase = request.athlete_state.phase` if it's a known PhaseLiteral else None.

### Integration point

After existing line `body = build_council_prompt(...)` (or strict equivalent):
```python
if not args.no_evidence:
    refs_md = _retrieve_and_render_refs(args, request)  # new helper
    body = body + refs_md
```

Then existing `out_path.write_text(body, ...)` captures everything.

`_retrieve_and_render_refs` is a thin private helper at script level (not a module-level coupling). It catches retrieval errors and returns empty-state markdown so prompt write never fails because of evidence module.

### Frozen module discipline

- `council_prompt.py`, `strict_prompt.py`, `response_parser.py`, `history_injector.py` git diff MUST be empty
- Phase 1/2/3 modules also untouched
- Only file modified outside `evidence/` is `scripts/run_consensus.py` + new `tests/unit/evidence/test_prompt_section.py` + new `tests/e2e/test_evidence_prompt_integration.py`

---

## E2E Test (`tests/e2e/test_evidence_prompt_integration.py`)

Single test: `test_council_prompt_contains_references_section`
- Set up tmp_path with: minimal `verdict_request.json` (real fixture pattern from existing test_phase3_full_chain.py) + the real `evidence_corpus/`
- Run `scripts/run_consensus.py --mode council --verdict-request <fix> --evidence-corpus <real corpus> --out <tmp>/council.prompt.md`
- Assert: rc==0, output file exists, contains `"## References (auto-retrieved"`, contains at least one `**[01HXR0NM8K`

Plus: `test_no_evidence_flag_suppresses_section` 
- Same as above with `--no-evidence`
- Assert: output exists, does NOT contain `"## References"`

---

## Acceptance for File 03

- [ ] `prompt_section.py` rendered with both empty and populated branches
- [ ] `run_consensus.py` accepts new flags; backward compatible (existing tests for run_consensus pass unchanged)
- [ ] Frozen modules diff empty (verified by `git diff --stat src/coach/consensus/`)
- [ ] e2e test produces prompt with References section using real corpus
- [ ] Full unit + e2e: 735 → ≥ 740 (≥ 4 prompt_section + 2 e2e)
- [ ] commit: `feat(coach-phase4): T77-T78 prompt integration + run_consensus references`
