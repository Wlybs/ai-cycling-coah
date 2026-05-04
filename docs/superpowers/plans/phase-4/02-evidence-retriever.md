# File 02 — Evidence Retriever

**Tasks:** T75 (TF-IDF scoring) + T76 (Top-K + phase bonus + filters)
**Branch:** `ai-coach-phase-4`
**Frozen modules:** none (purely additive); only allowed schema augment is `CitationContext.contraindications_present` (additive, default `[]`)

---

## Algorithm Decisions

**Why TF-IDF (not BM25):** No new external dep, pure-Python implementable in ≤80 lines. BM25 would require either `rank_bm25` (not in requirements.txt) or a more complex implementation. TF-IDF gives interpretable scores and good top-3 quality on a 5-50 card corpus — semantic depth doesn't matter much when N is small.

**Token namespace.** Each card's "search corpus" = `tags + body_tokens` (not title — title noise distracts; tags + body cover what we need).

**Phase semantics.** Card `phase = []` (empty) means "applies to all phases" (no bonus, no penalty). If non-empty, must contain `context.phase` to earn 1.5× bonus.

**applies_to semantics.** Card `applies_to = []` means "all athletes" — neutral. If non-empty AND intersects `context.applies_to_filter`, bonus 1.3×. If non-empty AND no intersection, **no penalty** (the card is still eligible but doesn't get bonus).

**Contraindications.** Hard filter: if `context.contraindications_present` intersects `card.contraindications`, the card is **excluded entirely** before scoring.

**Determinism.** `sorted(..., key=(score_desc, ulid_asc))` for ties.

---

## T75 — TF-IDF Core (`src/coach/evidence/retriever.py` part 1)

### Functions

```python
def _tokenize_query(terms: list[str]) -> list[str]: ...
    # Lowercase + strip; reject empty after strip; preserve order, allow dupes (for repeat-emphasis)

def _build_idf(cards: list[EvidenceCard]) -> dict[str, float]: ...
    # idf(t) = log(N / (1 + df(t))); over BOTH tags and body_tokens
    # N = number of *active* cards (deprecated already filtered upstream)

def _card_search_terms(card: EvidenceCard) -> list[str]: ...
    # Return card.tags + card.body_tokens (already lowercase)

def _raw_score(query: list[str], card: EvidenceCard, idf: dict[str, float]) -> tuple[float, list[str]]: ...
    # Returns (raw_score, matched_terms)
    # raw_score = sum over t in query of (count_in_card(t) * idf.get(t, 0.0))
    # matched_terms = unique query terms whose count_in_card > 0
```

### T75 Tests (`tests/unit/evidence/test_retriever_tfidf.py`, ≥ 6)

1. `_build_idf` empty card list → empty dict
2. `_build_idf` single card → all tokens have idf = log(1 / 2) ≈ -0.693 (rare-token reward absent in N=1)
3. `_build_idf` 3 cards, "taper" appears in 1 → idf("taper") > idf(common_word_in_all_3)
4. `_raw_score` 0 matched terms → score 0, matched_terms []
5. `_raw_score` 2 matched terms → score > 0, matched_terms contains both
6. `_raw_score` deterministic: same inputs → same output (no randomness)

---

## T76 — Top-K Retrieval (`src/coach/evidence/retriever.py` part 2)

### Schema augmentation

In `src/coach/evidence/types.py`:
```python
class CitationContext(BaseModel):
    ...
    contraindications_present: list[str] = Field(default_factory=list)
```

Default `[]` keeps all existing tests passing.

### Public API

```python
def retrieve(
    *, context: CitationContext, cards: list[EvidenceCard],
) -> list[RetrievedCard]: ...
```

Behavior:
1. Filter `cards` to status="active" only
2. Filter out cards whose `contraindications` ∩ `context.contraindications_present` non-empty
3. Compute idf over the remaining cards
4. For each card, raw_score + multipliers:
   - phase_bonus = 1.5 if context.phase and context.phase in card.phase else 1.0
   - applies_bonus = 1.3 if card.applies_to and set(card.applies_to) ∩ set(context.applies_to_filter) else 1.0
   - final_score = raw_score * phase_bonus * applies_bonus
5. Normalize: divide all final_scores by max, so top card = 1.0 (only if max > 0)
6. Sort by (-normalized_score, card.ulid)
7. Truncate to top_k
8. Drop any with normalized_score < context.min_score
9. Return list[RetrievedCard]

### T76 Tests (`tests/unit/evidence/test_retriever.py`, ≥ 8)

1. Empty cards → empty result
2. No query match → empty result (all scores zero)
3. Single perfect match → returns 1 RetrievedCard, score normalized to 1.0
4. Top-K truncation: 5 matching cards, top_k=2 → returns 2
5. min_score filter: cards below threshold excluded
6. Phase bonus: same raw_score, only one card matches phase → that one ranks higher
7. Contraindication filter: card with contraindication present in context excluded entirely
8. Deprecated cards excluded
9. Determinism: same inputs run twice → identical output (including ulid ordering on ties)

---

## Acceptance for File 02

- [ ] `src/coach/evidence/retriever.py` ≤ 200 lines including docstrings
- [ ] `CitationContext.contraindications_present` added (default `[]`)
- [ ] All new tests green; full unit suite 719 → ≥ 733 (no regression)
- [ ] `evidence_lint` still clean (corpus unchanged)
- [ ] Determinism test passes 100 consecutive runs (or assert via fixed-seed fixture)
- [ ] commit message: `feat(coach-phase4): T75-T76 evidence retriever (TF-IDF + phase bonus + filters)`
