# Phase 4 Plan Index — Evidence RAG (M1)

**Branch:** `ai-coach-phase-4`
**Blueprint:** [`docs/superpowers/specs/2026-05-04-phase-4-blueprint.md`](../../specs/2026-05-04-phase-4-blueprint.md)
**Status:** Index authored 2026-05-04，task specs 待陆续撰写
**Hard scope:** 仅 Component 8 (Evidence RAG)。Component 9 / 10 推到 M2/M3，本 index 不覆盖。

---

## Task Map (4 spec files, ~8 sub-tasks T73-T80)

| File | Tasks | Goal |
|---|---|---|
| [01-evidence-types-corpus.md](./01-evidence-types-corpus.md) | T73 + T74 | EvidenceCard Pydantic schema + CorpusReader + 5 种子卡片 + lint CLI |
| [02-evidence-retriever.md](./02-evidence-retriever.md) | T75 + T76 | BM25/TF-IDF retriever + CitationContext + Top-K filter + 阈值 |
| [03-evidence-prompt-integration.md](./03-evidence-prompt-integration.md) | T77 + T78 | render_references_section + run_consensus.py 接入 + e2e |
| [04-acceptance-checklist.md](./04-acceptance-checklist.md) | T79 | 实地验收 checklist + tag `v4.0-phase4-m1-accepted` |

---

## Sequence Discipline

每个 task file 撰写本身是一次独立 session（5 步 TDD + 完整代码块）；实施同样一 file 一 session。严格按 01 → 04 顺序，前一文件 acceptance pass 才动下一文件。

**Frozen modules (绝对不可改一字):**
- `src/coach/consensus/council_prompt.py`
- `src/coach/consensus/strict_prompt.py`
- `src/coach/consensus/response_parser.py`
- `src/coach/consensus/history_injector.py`
- `src/coach/adapter/*.py` (整个 Phase 3 adapter)
- `src/coach/ledger/*.py` (整个 Phase 3 ledger)
- 任何 Phase 1/2 模块

接入只能通过新模块 `src/coach/evidence/*.py` + 修改 `scripts/run_consensus.py` 的 prompt 拼装外层。

**新增依赖检查:**
- 实施第一步先 `grep rank_bm25 icu/requirements.txt` 确认是否已存在；不存在则走纯 Python TF-IDF 自实现（≤120 行 retriever.py 内嵌）

---

## Acceptance for Phase 4 M1 (汇总，详细见 04 文件)

- [ ] 全套 unit + e2e: ≥ 720 项绿（baseline 695 + 6 e2e + Phase 4 新增 ≥ 19）
- [ ] `evidence_corpus/` 首发 ≥ 5 张 active 卡片，lint 0 violation
- [ ] e2e 实地用 `coach_memory/ledger/decisions.jsonl` 真实数据跑 council with references，prompt 文件含 References 子段
- [ ] frozen modules diff 全空
- [ ] requirements.txt 无新增（或仅启用 rank_bm25 如已存在）
- [ ] `git tag v4.0-phase4-m1-accepted`

---

## Why this order matters

01 (types + corpus) → 02 (retrieval) → 03 (integration) → 04 (acceptance) 是严格依赖链：
- 02 需要 01 的 EvidenceCard 类型才能 retrieve
- 03 需要 02 的 retriever 才能 render references 段
- 04 需要 03 跑通 e2e 才能验收

不要跳步，不要并行 implement —— 每步都要等前一步 acceptance pass。
