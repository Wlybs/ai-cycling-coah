"""Phase 4 Evidence RAG — frozen Pydantic v2 schemas."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator


# ---------- regex constants ----------

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
SNAKE_CASE_TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
SNAKE_CASE_APPLIES_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
TOKEN_SPLIT_PATTERN = re.compile(r"[^a-z0-9]+")


PhaseLiteral = Literal[
    "base", "build", "peak", "competitive", "transition", "off_season"
]
StatusLiteral = Literal["active", "deprecated", "needs_review"]


# ---------- EvidenceCard ----------

class EvidenceCard(BaseModel):
    """单张证据卡片。append-only 语义；deprecate 走 status + superseded_by。"""

    model_config = {"frozen": True}

    ulid: str = Field(..., description="Crockford base32, 26 chars, primary key")
    title: str = Field(..., min_length=10)
    authors: list[str] = Field(..., min_length=1)
    year: int = Field(..., ge=1950, le=2100)
    source: str = Field(..., min_length=5)
    tags: list[str] = Field(..., min_length=1)
    phase: list[PhaseLiteral] = Field(default_factory=list)
    applies_to: list[str] = Field(default_factory=list)
    finding: str = Field(..., min_length=20)
    dosing_hint: str = Field(..., min_length=10)
    contraindications: list[str] = Field(default_factory=list)
    status: StatusLiteral = "active"
    superseded_by: str | None = None
    body_md: str = Field(..., description="Markdown body after frontmatter")

    @model_validator(mode="after")
    def _validate_ulid(self) -> "EvidenceCard":
        if not ULID_PATTERN.match(self.ulid):
            raise ValueError(f"ulid not Crockford-26: {self.ulid!r}")
        return self

    @model_validator(mode="after")
    def _validate_tags(self) -> "EvidenceCard":
        for t in self.tags:
            if not SNAKE_CASE_TAG_PATTERN.match(t):
                raise ValueError(f"tag must be snake_case lowercase: {t!r}")
        return self

    @model_validator(mode="after")
    def _validate_applies_to(self) -> "EvidenceCard":
        for a in self.applies_to:
            if not SNAKE_CASE_APPLIES_PATTERN.match(a):
                raise ValueError(f"applies_to must be snake_case lowercase: {a!r}")
        return self

    @model_validator(mode="after")
    def _validate_status_supersede_consistency(self) -> "EvidenceCard":
        if self.status == "active" and self.superseded_by is not None:
            raise ValueError("active cards must have superseded_by=None")
        if self.status == "deprecated" and self.superseded_by is None:
            raise ValueError("deprecated cards must have superseded_by set")
        if self.superseded_by is not None and not ULID_PATTERN.match(self.superseded_by):
            raise ValueError(f"superseded_by must be valid ULID: {self.superseded_by!r}")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def body_tokens(self) -> list[str]:
        """Lowercase tokens of body_md, split on non-alphanumeric. Used by retriever."""
        return [t for t in TOKEN_SPLIT_PATTERN.split(self.body_md.lower()) if t]


# ---------- CitationContext ----------

class CitationContext(BaseModel):
    """Retriever 的查询上下文 —— 由 verdict_request / athlete_state 拼装而来。"""

    model_config = {"frozen": True}

    query_terms: list[str] = Field(..., min_length=1)
    phase: PhaseLiteral | None = None
    applies_to_filter: list[str] = Field(default_factory=list)
    contraindications_present: list[str] = Field(default_factory=list)
    top_k: int = Field(3, ge=1, le=10)
    min_score: float = Field(0.10, ge=0.0, le=1.0)


# ---------- RetrievedCard ----------

class RetrievedCard(BaseModel):
    """Retriever 输出元素 —— card + 透明分数 + 命中关键词。"""

    model_config = {"frozen": True}

    card: EvidenceCard
    score: float = Field(..., ge=0.0)
    matched_terms: list[str] = Field(default_factory=list)
