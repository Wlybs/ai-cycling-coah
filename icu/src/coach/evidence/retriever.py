"""Phase 4 Evidence — TF-IDF retriever (no external deps).

Public API: `retrieve(*, context, cards) -> list[RetrievedCard]`.

Scoring:
- TF-IDF over (tags + body_tokens) with smoothed IDF: log((N+1)/(df+1)) + 1
- phase_bonus 1.5x if context.phase ∈ card.phase
- applies_bonus 1.3x if card.applies_to ∩ context.applies_to_filter non-empty
- Hard contraindication filter before scoring
- Deprecated cards excluded
- Normalize to top=1.0; truncate to top_k; drop below min_score
- Tie-break: ULID lex ascending
"""
from __future__ import annotations

import math
from collections import Counter

from src.coach.evidence.types import CitationContext, EvidenceCard, RetrievedCard


_PHASE_BONUS = 1.5
_APPLIES_BONUS = 1.3


def _card_search_terms(card: EvidenceCard) -> list[str]:
    # Include phase metadata as synthetic tokens so phase-as-query-term lexically
    # matches cards declared for that phase (e.g. query "transition" hits a card
    # whose phase=["competitive","transition"] even when body never says it).
    return list(card.tags) + list(card.body_tokens) + list(card.phase)


def _build_idf(cards: list[EvidenceCard]) -> dict[str, float]:
    if not cards:
        return {}
    n = len(cards)
    df: Counter[str] = Counter()
    for card in cards:
        for tok in set(_card_search_terms(card)):
            df[tok] += 1
    return {t: math.log((n + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}


def _raw_score(
    query: list[str], card: EvidenceCard, idf: dict[str, float],
) -> tuple[float, list[str]]:
    counts = Counter(_card_search_terms(card))
    score = 0.0
    matched_seen: set[str] = set()
    matched_ordered: list[str] = []
    for term in query:
        tf = counts.get(term, 0)
        if tf > 0:
            score += tf * idf.get(term, 0.0)
            if term not in matched_seen:
                matched_seen.add(term)
                matched_ordered.append(term)
    return score, matched_ordered


def _phase_bonus(card: EvidenceCard, ctx: CitationContext) -> float:
    if ctx.phase is not None and ctx.phase in card.phase:
        return _PHASE_BONUS
    return 1.0


def _applies_bonus(card: EvidenceCard, ctx: CitationContext) -> float:
    if card.applies_to and set(card.applies_to) & set(ctx.applies_to_filter):
        return _APPLIES_BONUS
    return 1.0


def _is_contraindicated(card: EvidenceCard, ctx: CitationContext) -> bool:
    return bool(set(card.contraindications) & set(ctx.contraindications_present))


def retrieve(
    *, context: CitationContext, cards: list[EvidenceCard],
) -> list[RetrievedCard]:
    """Top-K evidence retrieval; returns [] when no card scores > 0."""
    eligible = [
        c for c in cards
        if c.status == "active" and not _is_contraindicated(c, context)
    ]
    if not eligible:
        return []

    idf = _build_idf(eligible)
    query = [t.lower().strip() for t in context.query_terms if t.strip()]

    scored: list[tuple[EvidenceCard, float, list[str]]] = []
    for card in eligible:
        raw, matched = _raw_score(query, card, idf)
        if raw <= 0.0:
            continue
        final = raw * _phase_bonus(card, context) * _applies_bonus(card, context)
        scored.append((card, final, matched))

    if not scored:
        return []

    max_score = max(s for _, s, _ in scored)
    if max_score <= 0.0:
        return []

    normalized = [(c, s / max_score, m) for c, s, m in scored]
    normalized.sort(key=lambda x: (-x[1], x[0].ulid))

    out: list[RetrievedCard] = []
    for card, score, matched in normalized[: context.top_k]:
        if score < context.min_score:
            continue
        out.append(RetrievedCard(card=card, score=score, matched_terms=matched))
    return out
