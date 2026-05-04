# AI Coach — Phase 4 Blueprint

> Evidence-Grounded Coaching: 给 Coach 接上"教科书 + 文献"骨架，让推理可被引用、可被反驳

**Status:** 蓝图定稿 (2026-05-04)，待实施
**Branch:** `ai-coach-phase-4` (cut from master @ `9aa370b`)
**Dependencies:** Phase 1（生理模型 + 深度分析器）、Phase 2（Periodization Engine + Session Designer）、Phase 3（Adapter + Consensus + Ledger）—— 全部已并入 master 并打 tag `v3.0.1`
**Parent:** [`2026-04-16-ai-coach-scheme-4-blueprint.md`](./2026-04-16-ai-coach-scheme-4-blueprint.md) —— Component 8/9/10 具体化

---

## Motivation

Phase 1-3 让 Coach 拥有了「这个运动员的生理模型」「确定性 session 合成」「多视角审查 + 自适应 + 决策记忆」。但用户给出的两条核心反馈仍未根除：

1. **"分析太表面"** —— Consensus 的 Critic / Physiologist 角色虽然有触发器要求 ≥3 数据点 + 物理量关键词，但缺少**外部权威背书**。Critic 说 "你的 Z4 间歇频率太密"，没法引 "Per Seiler 2010, 80/20 polarized 模型对耐力人群..." 来强化结论。议论的"抓地力"不足，用户当然觉得表面。

2. **"练得不够狠"** —— 同样的根因。Adapter 说 "今日改 endurance"，没法附 "Per Mujika 2009 taper meta-analysis, 在你这种 ATL/CTL 比 1.07 的状态下，强度保留 + 体量减 50% 才是正解"。所以 Coach 显得软。

**Phase 4 的核心赌注：把"权威文献的引用能力"做成一种基础设施 —— 不是一锤子的 RAG demo，而是 Phase 3 的 council/strict prompt 在生成时能像查字典一样调出 1-3 条相关 evidence card 注入 Section A 的 "References" 子段。**

Component 9 (Race-Specific) 和 10 (Unified Persona) 并入 Phase 4 总目录但**降级为 M2/M3**，理由见下方"Scope Re-prioritization"。

---

## Hard Constraints (沿袭 Phase 3 + Phase 4 增项)

1. **不修改 Phase 1/2/3 任何已交付代码。** Phase 4 通过引入新的 helper 函数 + prompt 段渲染钩子接入。Council prompt / strict prompt 在 Phase 3 已经 frozen，Phase 4 只能**在 Section A 末尾注入 References 子段**，不能修改前 4 节结构。
2. **零 LLM API 调用。** 不用 sentence-transformers / openai-embedding / 任何向量化 SaaS。Evidence retriever 走纯 Python 词法 + 标签匹配（BM25 或更简单的 TF-IDF + tag overlap）。
3. **不引入新外部依赖。** 仍是 Python 3.11 + Pydantic v2 + scipy + pytest + 标准库。BM25 用纯 Python 实现（≤120 行）或干脆用 `rank_bm25` 已在系统的 `requirements.txt` 里 —— 实施前 grep 确认；如未安装就走 TF-IDF 自实现。
4. **Evidence 内容人工策划。** 不爬网。每条 evidence card 是 Markdown + YAML frontmatter，由用户/我手工从原始论文抄关键 finding + dosing recommendation + 适用条件。语料库小而精（≤50 张卡片首发），后续按需扩。
5. **Append-only 语料管理。** 卡片用 ULID 命名 + frontmatter `superseded_by` 字段允许打 deprecated 标记。检索器不返回 deprecated 卡片，但物理保留以备 audit。
6. **检索透明可解释。** 每次注入 references 时，prompt 里附"为什么命中此卡"（matched terms + score），方便用户判断是否相关。

---

## Design Principles

- **Evidence 是引用，不是真理。** Critic 角色被指示 "如有相关 evidence 命中，可在自己论点末附 [cite: card_ulid] 但不必 paraphrase 卡片原文 —— 用你自己的话讲完逻辑后引用即可"。Coach 的个人观点优先，evidence 作为支撑/反例使用。
- **检索粒度 = 决策粒度。** 不为每个 sentence 检索；只在 council/strict prompt 拼装时触发 1 次检索（基于 athlete_state + 7-day load + verdict_request 的关键词）；返回 Top-K 卡片直接进 prompt。
- **回退优于出错。** 检索结果 0 命中 → prompt 注入 "**References**: (none directly applicable for this context)"，不抛错。
- **隔离测试。** Evidence retriever 必须可 unit test —— 喂固定语料 + 固定 query → 断言 Top-K 输出确定。不能因为依赖 ULID 时序或 wall clock 而非确定。
- **HUMAN_GATE 不变。** Phase 4 引入的所有新脚本仍走 prompt 文件 → 用户手工跑 LLM → 回填的工作流；没有任何 SDK 调用。

---

## Scope Re-prioritization (与 Scheme 4 蓝图差异)

| 原 Scheme 4 列表 | Phase 4 重排 | 理由 |
|---|---|---|
| Component 8 Evidence RAG | **M1 必交付** | 直接打中"分析太表面"反馈；技术风险中等可控 |
| Component 9 Race-Specific | **M2 推到下次有真实赛事时** | 你当前赛事状态（per memory `race_prep_2026.md`）是 "context only"，protocol 也已删除；现在做race-sim ride generator 没数据驱动需求 |
| Component 10 Unified Persona | **M3 机会型重构，不在 M1 路径上** | persona 统一是 "nice to have"；Phase 1-3 各自的 prompt 各自正常工作，重构动力不足；等 M1 落地后看是否需要再开 |

**Phase 4 = 即 Evidence RAG。** 后续如要做 Race-Specific 或 Persona，单独起 Phase 4.5 / Phase 5。

---

## Architecture — Component 8 (Evidence RAG)

### 模块结构

```
icu/src/coach/evidence/
├── __init__.py
├── types.py            # EvidenceCard / RetrievedCard / CitationContext (Pydantic v2)
├── corpus.py           # CorpusReader: 扫 evidence_corpus/*.md → list[EvidenceCard]
├── retriever.py        # 词法检索（BM25 或 TF-IDF + tag overlap），返回 Top-K
├── prompt_section.py   # render_references_section(retrieved) → str (markdown)
└── (no scripts/ —— retriever 调用点在 Phase 3 council_prompt + strict_prompt)

icu/evidence_corpus/
├── 01HXR0NM8K... .md   # 单卡片，ULID 命名，frontmatter + body
├── 01HXR0NM8L... .md
└── ...                 # 首发 ≤50 张，后续按需

icu/scripts/
└── evidence_lint.py    # CLI: 校验 corpus 全部 cards frontmatter 合规、ULID 唯一、tag 在白名单内
```

### EvidenceCard schema (frontmatter YAML + body MD)

```yaml
---
ulid: 01HXR0NM8K...                # primary key, 命名同文件名
title: "Mujika & Padilla 2003 — Tapering meta-analysis"
authors: ["Mujika I", "Padilla S"]
year: 2003
source: "Med Sci Sports Exerc 35(7):1182-7"
tags: ["taper", "peaking", "endurance", "intensity_preservation", "volume_reduction"]
phase: ["competitive", "transition"]   # 适用 periodization phase
applies_to: ["all_athletes"]           # 或 ["fast_twitch", "post_acl"] 等限定标签
finding: "Volume reduction of 41-60% with intensity maintained yields optimal performance gains over 7-21 day taper."
dosing_hint: "Reduce weekly volume by ~50%, keep all interval session intensities unchanged, drop steady-state mileage first."
contraindications: []
status: "active"                       # active | deprecated | needs_review
superseded_by: null
---

## Body (人工撰写的核心内容 + Coach 怎么用)

# 详细引文段落、与本 athlete 的相关性注释 ...
```

### Retrieval algorithm

输入：`CitationContext` Pydantic 对象，字段包括：
- `query_terms: list[str]` —— 来自 verdict_request / athlete_state / 7-day load 的关键词（"taper", "low_hrv", "z2", ...）
- `phase: str | None` —— 当前 periodization phase
- `applies_to_filter: list[str] | None` —— athlete 个人标签（"fast_twitch", "post_acl"）
- `top_k: int = 3`

输出：`list[RetrievedCard]`，每个含 `card: EvidenceCard, score: float, matched_terms: list[str]`。

打分：`score = bm25(query_terms, card.tags + card.body_tokens) × phase_match_bonus × applies_to_filter`。
- `phase_match_bonus = 1.5 if context.phase in card.phase else 1.0`
- `applies_to_filter` 命中 athlete 标签 ×1.3，硬性 contraindication 命中 ×0（直接过滤）
- Deprecated 卡片直接过滤
- Top-K 前要求 `score ≥ MIN_SCORE` 阈值，否则截断（确保"宁缺毋滥"）

### Integration points (修改最小化)

**Phase 3 council_prompt.py**（已 frozen 不能改）→ 通过新增的 `prompt_section.render_references_section()` 在 council prompt 拼装的**外层**追加。具体：
- 在 `scripts/run_consensus.py` 拼 prompt 时，先调 `retriever.retrieve(context) → top_k`
- 然后 `final_prompt = council_prompt.build(...) + "\n\n" + render_references_section(top_k)`
- council_prompt.py 自身**不改一字** —— 这是 Phase 4 触不可破的硬约束（参见 [Coach Phase 3 plan status memory] 关于不改 frozen modules 的纪律）

**`scripts/run_consensus.py` 加 `--evidence-corpus PATH`** 参数，默认指向 `evidence_corpus/`，缺省也允许传 `--no-evidence` 来 disable 注入（debugging 用）。

### Acceptance criteria for Component 8

- [ ] `evidence_corpus/` 首发 ≥ 5 张精选卡片（覆盖 taper / polarization / W' 恢复 / FTP 测试协议 / 强度区间）
- [ ] `evidence_lint.py` 跑全 corpus 0 violation
- [ ] `retriever.retrieve()` 单元测试 ≥ 12 项（命中、未命中、phase 加权、contraindication 排除、deprecated 排除、top-K 截断、确定性）
- [ ] `render_references_section()` 单元测试 ≥ 4 项（含 / 不含 references 两种 markdown 输出格式稳定）
- [ ] e2e: 跑 `run_consensus.py --mode council --verdict-request <fixture> --evidence-corpus <fixture>` 产出 prompt 文件含 References 子段，引用 1-3 张卡片，每张含 matched_terms 注释
- [ ] Phase 3 frozen 模块（council_prompt.py / strict_prompt.py / response_parser.py / history_injector.py）git diff 全空
- [ ] 全套 unit + e2e 不退化（baseline 695 + 6 → 至少 ≥ 720）

---

## File Map (Phase 4 M1)

| # | File | Tasks | Scope |
|---|---|---|---|
| 01 | `01-evidence-types-corpus.md` | T73 (types) + T74 (corpus reader + lint script) | 5 张种子卡片 + Pydantic schema + lint CLI |
| 02 | `02-evidence-retriever.md` | T75 (BM25 / TF-IDF + tags) + T76 (CitationContext + Top-K) | retrieval 算法本体 |
| 03 | `03-evidence-prompt-integration.md` | T77 (`render_references_section`) + T78 (`run_consensus.py` 接入 + e2e) | 把 retriever 焊到 Phase 3 council prompt 外层 |
| 04 | `04-acceptance-checklist.md` | T79 实地验收 | 用真实 wellness + ledger 跑 council with references，确认 prompt 文件完整 |

预计 4 个 task spec session + 4 个 implementation session，两周内可收。

**M2/M3 暂不开 task file —— 待 M1 落地、用户使用反馈再决定要不要做。**

---

## Out of Scope (明确不做)

- Vector embedding / semantic search（违反"零外部 SaaS + 不引入新依赖"）
- 自动从论文 PDF 抽 finding（手工策划保证质量）
- Evidence card 的版本控制 / merging（appendr-only + supersede 已够）
- 把 evidence 注入 session_designer / adapter prompt（这两处 prompt 在 Phase 1/2 frozen，要改它们要单独 ADR）
- Race-Specific & Unified Persona（推到 M2/M3，见上方 Scope Re-prioritization）

---

## End-State Vision for Phase 4 M1

Coach 在跑 council consensus 时，prompt 文件最后会自动多一段：

```markdown
## References (auto-retrieved by Phase 4 evidence retriever)

1. **[01HXR0NM8K] Mujika & Padilla 2003 — Tapering meta-analysis** (score 0.78)
   - matched: taper, peaking, endurance
   - finding: Volume reduction of 41-60% with intensity maintained yields optimal performance gains over 7-21 day taper.
   - dosing_hint: Reduce weekly volume by ~50%, keep all interval session intensities unchanged, drop steady-state mileage first.

2. **[01HXR0NM8L] Seiler 2010 — Polarized training intensity distribution** (score 0.62)
   ...

(retriever returned 2/3 above MIN_SCORE threshold; refer to Critic for whether these apply)
```

Critic / Physiologist 在 Section A 写论点时**可以**写 "[cite: 01HXR0NM8K]" 来锚定结论。response_parser 不强制要求引用（避免 LLM 强凑），只在 user 阅读时增强可信度。

**这就是 Phase 4 M1 的全部目标 —— 让 Coach 议论"有书可查"。**
