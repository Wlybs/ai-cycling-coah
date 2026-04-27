"""Multi-Expert Consensus — Phase 3 的 council/strict 审查骨架。

公开入口：
- CouncilVerdict / ExpertTurn / ConsensusValidationError: 类型与异常（见 types.py）
- ResponseParser: Gemini 4-段 + summary_json 解析 + 硬规则校验（见 response_parser.py）
- HistoryInjector: 调 LedgerReader 拼相似 context-verdict-outcome 三元组（见 history_injector.py）

API_FREE：本包不 import google.genai 也不做任何 network call。所有 LLM 交互
通过 prompt 文件 → 用户手工粘贴回 response 文件的异步流。
"""
