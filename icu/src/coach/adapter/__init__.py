"""Adaptation Engine — Phase 3 每日再评估的判定层。

公开入口：
- SignalSnapshot / AdaptationVerdict: 类型（见 types.py）
- evaluate_signals(snapshot, history) → AdaptationVerdict: 主判定函数（见 rules.py）

本包以 **纯函数为主**：evaluate_signals / revise_session / build_*_nudge 等均为
输入 dataclass、输出 dataclass，0 文件 IO，0 LLM 调用。
唯一例外是 `run_daily_adapt`：它是 IO 协调器（读 wellness/plan/ledger，
写 markdown / proposed_session / ledger entry），通过依赖注入接收 writer/reader。
ICU PATCH 在 scripts/apply_adaptation.py 完成。
判定规则与阈值见 docs/superpowers/specs/2026-04-19-phase-3-blueprint.md §Component 5。
"""
from .daily_adapt import run as run_daily_adapt
from .prompt_builder import build_red_override, build_yellow_nudge
from .rules import evaluate_signals
from .session_revisor import revise_session
from .types import (
    RECOMMENDED_ACTIONS,
    SIGNAL_KEYS,
    VERDICT_VALUES,
    AdaptationVerdict,
    RecommendedAction,
    SignalSnapshot,
    Verdict,
)

__all__ = [
    "AdaptationVerdict",
    "RECOMMENDED_ACTIONS",
    "RecommendedAction",
    "SIGNAL_KEYS",
    "SignalSnapshot",
    "VERDICT_VALUES",
    "Verdict",
    "build_red_override",
    "build_yellow_nudge",
    "evaluate_signals",
    "revise_session",
    "run_daily_adapt",
]
