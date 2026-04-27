"""Consensus 类型定义：CouncilVerdict / ExpertTurn / ConsensusValidationError。"""
from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- 枚举（与 00-index.md naming conventions 对齐） ----------

ExpertRole = Literal["planner", "critic", "physiologist", "arbiter"]
EXPERT_ROLES: tuple[str, ...] = get_args(ExpertRole)

Verdict = Literal["ACCEPT", "REVISE", "REJECT"]
VERDICTS: tuple[str, ...] = get_args(Verdict)

Mode = Literal["council", "strict"]
MODES: tuple[str, ...] = get_args(Mode)


# ---------- ExpertTurn ----------

class ExpertTurn(BaseModel):
    """单个角色的发言。

    body_md 保留原始 markdown（含 `<role>` 包裹外的内容），方便回写
    verdict.md 时复刻原文风格。cited_data 是 parser 抽出的原子引用片段
    （如 "CP=288W"、"weekly_plan.total_tss=320"），用于硬规则计数。
    """

    model_config = {"frozen": True}

    role: ExpertRole
    body_md: str = Field(..., description="角色段落原文 markdown")
    cited_data: list[str] = Field(default_factory=list,
                                  description="parser 抽出的引用片段（数据/字段名）")

    @field_validator("body_md")
    @classmethod
    def _body_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("body_md must not be blank")
        return v


# ---------- CouncilVerdict ----------

class CouncilVerdict(BaseModel):
    """parser 成功解析后的裁决产物。

    summary_json 保留原始解析得到的 dict（不重新打包），后续 ledger payload
    可以直传，避免二次序列化漂移。
    """

    model_config = {"frozen": True}

    mode: Mode
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(..., min_length=1)
    expert_turns: list[ExpertTurn] = Field(..., min_length=1)
    summary_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _council_requires_four_roles(self) -> "CouncilVerdict":
        if self.mode == "council":
            roles = {t.role for t in self.expert_turns}
            missing = set(EXPERT_ROLES) - roles
            if missing:
                raise ValueError(
                    f"council mode requires all 4 roles; missing: {sorted(missing)}"
                )
        return self


# ---------- Exception ----------

class ConsensusValidationError(Exception):
    """Gemini response 不合规 → parser 抛出。带 violations 列表用于打印 + 重跑。"""

    def __init__(self, violations: list[str]) -> None:
        if not violations:
            raise ValueError("ConsensusValidationError requires ≥1 violation")
        self.violations = list(violations)
        super().__init__("; ".join(self.violations))
