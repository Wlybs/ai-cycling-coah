"""Decision Ledger — Phase 3 的 append-only 决策账本。

公开入口：
- LedgerWriter: 原子 append JSONL（见 writer.py）
- LedgerReader: 查询 / 相似 context 检索 / 决策链追溯（见 reader.py）
- DecisionEntry / AthleteStateRef / DECISION_TYPES: 类型和常量（见 types.py）

所有持久化通过单文件 `coach_memory/ledger/decisions.jsonl` 完成。
Schema / 约束见 docs/superpowers/specs/2026-04-19-phase-3-blueprint.md。
"""
