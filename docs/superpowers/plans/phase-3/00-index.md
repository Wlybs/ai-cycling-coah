# AI Coach — Phase 3 Implementation Plan (Index)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 Coach 系统装上 **记忆（Ledger）+ 反思（Consensus）+ 调整（Adapter）**：每个决策（Phase 2 派生的 + Phase 3 新做的）沉淀到 append-only JSONL，Consensus 在生成新计划时把相似 context 的历史 outcome 回读进 prompt；每日按 4 信号规则判定红/黄/绿，红灯时合成可执行替代 session 并经用户一键确认后写回 ICU。

**Architecture:** 三个新包 + 五条新脚本 + 零 Phase 1/2 改动：
- `icu/src/coach/ledger/` — append-only 决策账本（types / writer / reader / ingester）；单文件 JSONL，纯 Python 过滤查询
- `icu/src/coach/adapter/` — 每日再评估（确定性规则引擎 + 红灯降载 session 合成）
- `icu/src/coach/consensus/` — 多专家审查（单 prompt council 默认；strict 4-step 可延后）；通过 prompt 文件走 API-free 工作流
- 集成：`sync_data.py` 收尾自动调 ingester + daily_adapt；用户手动跑 `run_consensus.py` / `apply_adaptation.py`

**Tech Stack:** Python 3.11+, Pydantic v2（已在 Phase 1 引入）, scipy（已在 Phase 1 引入）, pytest。**不引入任何新外部依赖**；禁止 import `google.genai` 及任何 LLM SDK。

## Scope

Phase 3 实现蓝图中的 **Component 5 + 6 + 7**（Phase 4 才做 Evidence RAG）：
- Component 5: Adaptation Engine (`icu/src/coach/adapter/`)
- Component 6: Multi-Expert Consensus (`icu/src/coach/consensus/`)
- Component 7: Decision Ledger (`icu/src/coach/ledger/`)

蓝图：[`../../specs/2026-04-19-phase-3-blueprint.md`](../../specs/2026-04-19-phase-3-blueprint.md)
Phase 1 spec（Phase 3 消费其产物）：[`../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`](../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md)
Phase 2 plan（Phase 3 消费其产物）：`docs/superpowers/plans/phase-2/00-index.md`（于 `ai-coach-phase-2` 分支）

### In scope (M1 — Phase 3 MVP)

- Ledger 基础设施（types / writer / reader / ingester）
- Adapter 完整路径（rules / session_revisor / daily_adapt / apply_adaptation）
- Consensus **默认 council 模式**（council_prompt / response_parser / history_injector / run_consensus / finalize_consensus）
- `sync_data.py` 集成：末尾自动跑 ingest_ledger + daily_adapt + 建议钩子
- e2e + 真仓库验收

### M2 (Phase 3 可延后，不阻塞 M1 发布)

- Consensus **strict 4-step 模式**（strict_prompt / finalize_consensus --step N state machine）
- `ledger_digest.py` 季度回顾 prompt 生成

### Out of scope (Phase 4)

- Evidence RAG / 文献引用 / embedding + 向量检索
- Race-specific module（赛前 5 天协议自动化，对接 `problem.md`）
- Unified Persona（统一的 coach 对话入口）
- 删除 Phase 1 的 `phase1_injection.py` / `brief_updater.py`
- 删除 Phase 2 保留的 legacy `plan_generator.py` fallback
- **修改 Phase 1/2 任何已交付文件**（HARD 约束）：
  - Phase 1: `src/coach/physiology/*`、`src/coach/deep_analyzer/*`、`scripts/sync_data.py` 中 Phase 1 所写的段落、`scripts/refresh_physiology.py`、`scripts/run_deep_analysis.py`、`scripts/update_coach_brief.py`、`src/coach/phase1_injection.py`、`src/coach/brief_updater.py`
  - Phase 2: `src/coach/periodization/*`、`src/coach/session_designer/*`、Phase 2 在 `scripts/push_plan.py` 的新增段落
  - **允许**：在 `scripts/sync_data.py` 末尾追加 Phase 3 调用（ingester + daily_adapt + 建议钩子），属于集成点扩展而非修改 Phase 1/2 逻辑

## Foundational contracts (read before starting any file)

### Inputs Phase 3 consumes (来自 Phase 1 + Phase 2，只读、不改、不重算)

| Path | Pydantic model | Keys used in Phase 3 |
|---|---|---|
| `coach_memory/physiology/cp_w_current.json` | `CPWModel` | `cp_watts`, `w_prime_joules`, `athlete_ftp_set` |
| `coach_memory/physiology/durability.json` | `DurabilityCurve` | `decay_rate_pct_per_1000kj["60s"/"300s"]`, `sample_size_rides` |
| `coach_memory/physiology/response_profile.json` | `ResponseProfile` | `types[<session_type>].tolerance_class`, `knee_loading.flag` |
| `coach_memory/deep_analysis/summary_latest.json` | — | `headline_verdict`, `stimulus_score`, `progression_flag`, `knee_flag` |
| `coach_memory/periodization/periodization_current.json` | `PeriodizationSnapshot` | `phase`, `meso_block`, `micro_cycle`（Consensus / Adapter） |
| `coach_memory/periodization/phase_current.json` | — | `phase`, `transition_reasons`（Ingester） |
| `coach_memory/periodization/macro_plan.json` | — | `generated_at`, season layout（Ingester） |
| `coach_memory/periodization/meso_block.json` | — | `block_id`, `generated_at`（Ingester） |
| `coach_memory/periodization/micro_cycle_*.json` | `MicroCycle` | 今日 `DayIntent`（Adapter） |
| `coach_memory/reports/plan_*.json` | `WeeklyPlan` | 今日 `DesignedSession`（Adapter）、完整 plan（Consensus） |
| `coach_memory/reports/plan_*.trace.json` | — | session 物理来源摘要（Ingester 抽 payload） |
| `icu_data_warehouse/2_Wellness/wellness_history.json` | — | `hrv`, `restingHR`, `sleepSecs`, `soreness`, `fatigue`, `stress`, `mood`, `ctl`, `atl`, date |
| `icu_data_warehouse/1_Profile/athlete.json` | — | `ftp`, `hr_max`, `weight`（Consensus 上下文） |
| `icu_data_warehouse/8_Events/events.json` | — | 今日 event_id（apply_adaptation PATCH 定位） |

### Outputs Phase 3 produces（全部新增，写到 `coach_memory/ledger/`, `coach_memory/adapter/`, `coach_memory/consensus/`）

```
coach_memory/
├── ledger/
│   └── decisions.jsonl                        # 唯一账本文件，append-only
├── adapter/
│   ├── today_yellow_<YYYY-MM-DD>.md           # 黄灯 nudge 说明（人类可读）
│   ├── today_red_<YYYY-MM-DD>.md              # 红灯 override 说明（人类可读）
│   └── proposed_session_<YYYY-MM-DD>.json     # 红灯替代 session（Phase 2 DesignedSession schema）
└── consensus/
    └── <YYYY-MM-DD_HHMM>/
        ├── council.prompt.md                  # 默认模式 prompt
        ├── council.response.md                # 用户粘贴回的 Gemini 回复
        ├── verdict.md                         # 解析后人类可读裁决（含 strict 引导文案）
        ├── 1_planner.prompt.md                # strict M2：只在 --mode strict 时存在
        ├── 1_planner.response.md
        ├── 2_critic.prompt.md
        ├── 2_critic.response.md
        ├── 3_physiologist.prompt.md
        ├── 3_physiologist.response.md
        ├── 4_arbiter.prompt.md
        ├── 4_arbiter.response.md
        └── strict_verdict.md
```

### User-approved decisions (locked 2026-04-19)

These shape safety/behavior rules; any future PR that removes or loosens them must state justification.

1. **API_FREE_WORKFLOW** — Phase 3 绝不 import `google.genai` / 任何 LLM SDK 做 network request。所有 LLM 交互通过 prompt 文件 → 用户手工粘贴 → 回写 response 文件的异步流。违反即拒绝合并。
2. **PHASE_1_2_IMMUTABILITY** — Phase 3 不修改 Phase 1/2 任何已交付源文件（清单见 Out of scope）。允许的唯一扩展点：`scripts/sync_data.py` 末尾追加 Phase 3 调用。
3. **HUMAN_GATE_ON_ICU_WRITE** — Adapter 红灯产出替代 session 但**绝不自动推送**。用户必须敲 `scripts/apply_adaptation.py --date <date> --confirm` 才写回 ICU。绿灯 = 0 动作；黄灯 = 只写文件不触 ICU。
4. **APPEND_ONLY_LEDGER** — `decisions.jsonl` 绝不修改已写入 entry；纠错走 `superseded_by` 字段指向后续 entry。任何直接改文件的改动视为破坏不变量。
5. **CRITIC_3_POINTS_MIN** — Consensus council prompt 的 Critic role 硬性要求 ≥3 条独立反对点且每条引具体数据；response_parser 校验不通过 → 拒绝写 ledger + 提示重跑 prompt。
6. **PHYSIOLOGIST_QUANT_3_OF_4** — Physiologist role 必须引用 CP/W'/durability/response_profile 四项中至少 3 项关键词；校验失败同上处理。
7. **RED_NO_AUTO_ESCALATE** — Adapter 永不自动升级到 strict consensus；strict 只在用户显式敲 `--mode strict --reuse <ts>` 时触发。
8. **NO_NEW_DEPS** — 不新增 `requirements.txt` 条目。ULID 生成用标准库搓（`time_ns` + `secrets` 做 Crockford base32），不引第三方 ulid 包。

### Stable naming conventions (用于跨文件引用)

- 所有 Pydantic 模型放各子包的 `types.py`，类名 `PascalCase`，字段 `snake_case`。
- `decision_type` 枚举值 8 种（严格匹配蓝图 Payload 示例）：`phase_transition` / `macro_plan_generated` / `meso_block_created` / `micro_cycle_generated` / `weekly_plan_assembled` / `consensus_verdict` / `adaptation_verdict` / `adaptation_applied`。
- Adapter verdict 枚举：`green` / `yellow` / `red`（小写，与 JSON payload 一致）。
- Consensus mode 枚举：`council` / `strict`。
- Consensus verdict 枚举：`ACCEPT` / `REVISE` / `REJECT`（大写，Gemini 输出强约定）。
- JSONL 日志模块名：`ledger`、`adapter`、`consensus`（复用 Phase 1 的 `src.coach.common.logging.get_logger`）。
- ULID 字段统一叫 `entry_id`（`DecisionEntry` 主键）；时间戳字段统一叫 `timestamp`（UTC、ISO 8601）。

## Execution rules (read before starting any file)

1. **One file per session.** 从 01 → 09 顺序推进。绝不在一个 session 内链式跑多个文件 — 完成、commit、`save-progress`、结束、下一个 session 从头开始。
2. **TDD required.** 每个任务的第一步都是 RED 测试：先写测试、跑 `pytest` 确认失败、再写最小实现、再跑一次确认通过、再 commit。
3. **Delegate big writes.** 若某个任务单次需要写 > 300 行代码，用 `Agent` 工具派子代理执行，主对话只接收 "done + 文件列表"。使用记忆里的 "Subagent TDD preflight checklist"。
4. **Context hygiene.**
   - 分析已有源代码用 `ctx_execute_file`（摘要入 context）— 只有真要 `Edit` 那个文件时才 `Read` 它。
   - 不要 `Read` Phase 1/2 已完成的源文件去"确认"；只读 `types.py` 当你要使用它导出的类型。
   - 多个探索命令走 `ctx_batch_execute`，一次 round trip。
5. **Checkpoint discipline.** 每个文件完成后：`pytest` 通过 + commit 用 `feat(coach-phase3):` 前缀 + 运行 `save-progress` + 结束 session。
6. **Never write > 600 lines in a single Write.** 若实现文件超过 ~500 行，拆模块。
7. **No Phase 1/2 edits.** 不改 Phase 1/2 已交付文件。唯一允许的扩展：`scripts/sync_data.py` 末尾追加 Phase 3 调用（ingester + daily_adapt + 建议钩子），以向后兼容方式（Phase 3 模块缺失时跳过）。
8. **Fallback is the first release gate.** 任何时候 Phase 3 组件失败都必须优雅降级：
   - Ledger 缺失 → history_injector 返空 + prompt 显式声明 "no historical context"
   - Phase 1/2 产物缺失 → 清晰错误 + exit 非零，绝不瞎编
   - Gemini response 不合规 → parser 拒绝入库 + 提示重跑 prompt
   - `sync_data.py` 末尾的 Phase 3 调用失败 → 打印警告但不让整个 sync 退出非零（参见 09-integration T71 guardrail）

## File map

| # | File | Tasks | Focus | Depends on |
|---|---|---|---|---|
| 1 | [01-ledger-infrastructure.md](./01-ledger-infrastructure.md) | T50–T52 | 包骨架、`DecisionEntry` Pydantic 类型、`LedgerWriter` 原子 append + 文件锁、`LedgerReader` `query`/`query_similar`/`trace_chain` | — |
| 2 | [02-ledger-ingester.md](./02-ledger-ingester.md) | T53–T54 | `Ingester` 扫 Phase 2 产物回补 5 种 decision_type + `scripts/ingest_ledger.py` 幂等命令 | 01 |
| 3 | [03-adapter-infrastructure.md](./03-adapter-infrastructure.md) | T55–T57 | adapter 包骨架、`AdaptationVerdict`/`SignalSnapshot` 类型、`rules.py` 4 信号 + 2 护栏 + 阈值常量 docstring | 01 |
| 4 | [04-adapter-session-revisor.md](./04-adapter-session-revisor.md) | T58–T59 | `session_revisor.py` 降载映射 + 调 Phase 2 composer、`prompt_builder.py` 人类可读 nudge/override md 生成 | 03, Phase 2 session_designer |
| 5 | [05-adapter-integration.md](./05-adapter-integration.md) | T60–T61 | `scripts/daily_adapt.py` 主流程、`scripts/apply_adaptation.py` ICU PATCH + 回滚、mock ICU 的 e2e fixture | 04 |
| 6 | [06-consensus-infrastructure.md](./06-consensus-infrastructure.md) | T62–T64 | consensus 包骨架、`CouncilVerdict`/`ExpertTurn` 类型、`response_parser.py` 硬规则校验、`history_injector.py` 调 LedgerReader 压缩三元组 | 01 |
| 7 | [07-consensus-council.md](./07-consensus-council.md) | T65–T66 | `council_prompt.py` 四段模板拼装（Section A/B/C/D）+ 6 条 UNDER-DOSED 检查注入、`scripts/run_consensus.py` 默认模式 + `scripts/finalize_consensus.py` 解析入库 | 06 |
| 8 | [08-consensus-strict.md](./08-consensus-strict.md) | T67–T68 | **[M2]** `strict_prompt.py` 4 步模板（共用 Section B/C/D，拆 Section A role 指令）+ `finalize_consensus.py --step N` state machine | 07 |
| 9 | [09-integration-cli-tests.md](./09-integration-cli-tests.md) | T69–T72 | `coach/common/action_suggester.py` 启发式建议钩子、`sync_data.py` 末尾集成（ingester + daily_adapt + suggester，带失败不阻塞保护）、e2e 真实 fixture 全链路、真仓库验收清单 | 全部 |

Dependency order 严格。每个文件假定所有更低编号文件已完成、测试通过、提交入库。M2 文件（08）不阻塞 M1 发布 —— 完成 01–07 + 09 即可声明 Phase 3 M1 交付。

## Task ID numbering

Phase 1 用了 T1–T24；Phase 2 用了 T25–T49。Phase 3 从 **T50** 开始编号，避免歧义。最终 Phase 3 覆盖 T50–T72（共 23 个 task）：

- **M1 范围**: T50–T66 (01–07) + T69–T72 (09) = **21 个 task**
- **M2 范围**: T67–T68 (08) = **2 个 task**

## Handoff

**Start here:** 打开 [`01-ledger-infrastructure.md`](./01-ledger-infrastructure.md)。应用 `superpowers:subagent-driven-development`。顺序执行 T50–T52。Commit。运行 `save-progress`。结束 session。

**Subagent brief template:**

> 使用 `docs/superpowers/plans/phase-3/<file>.md`。遵循 `superpowers:subagent-driven-development`。按顺序执行其中任务。每个任务：先写 RED 测试并运行确认失败 → 实现最小代码 → 再跑一次确认通过 → 提交。
>
> **绝对不得修改的文件**（见 00-index.md "Out of scope" HARD 约束）：
> - `src/coach/physiology/*`、`src/coach/deep_analyzer/*`、`src/coach/periodization/*`、`src/coach/session_designer/*`
> - `scripts/refresh_physiology.py`、`scripts/run_deep_analysis.py`、`scripts/update_coach_brief.py`、`src/coach/phase1_injection.py`、`src/coach/brief_updater.py`
> - Phase 2 在 `scripts/push_plan.py` 已写入的段落（允许追加新 flag 但不改既有逻辑）
>
> **允许的 Phase 1/2 touchpoint**：在 `scripts/sync_data.py` **末尾**追加 Phase 3 调用段落（只追加，不改之前的段落）；调用必须以 try/except 包裹 + 失败时只打印警告（见 09-integration T71 guardrail）。
>
> **API-free 强约束**：禁止 import `google.genai` 或任何 LLM SDK 做 network 调用。所有 LLM 交互走 prompt 文件。
>
> 报告回：(a) 完成的 task ID、(b) 新建/修改的文件、(c) `pytest` 输出摘要、(d) 与计划的任何偏离及原因。

**When all 9 files are green:**

- Phase 3 M1 或 M1+M2 完成。执行 `09-integration-cli-tests.md` 中的验收清单（含真仓库 `/mnt/d/Cycling` 的一次完整端到端跑）。
- 把 `ai-coach-phase-3` 分支 merge 回 master（需先 rebase 吸收 Phase 2 merge 的产物）。
- 进入 Phase 4 brainstorm：Evidence RAG + Race-Specific Module + Unified Persona + legacy 清理。

**Author authorship notes for downstream plan files (01–09):**

下游 9 个任务文件尚未撰写。每个文件应当：
- 顶端重述本 index 里对应行的 Focus + Depends on
- 列出具体要创建/修改的文件路径（精确到 `icu/src/coach/<pkg>/<file>.py`）
- 每个 task 分 5 步：写 RED 测试 → 跑测试确认失败 → 写最小实现 → 跑测试确认通过 → commit
- 每步给出具体代码（而非占位）；测试、实现都 literal
- 测试引用真实 fixture 路径（建议放 `icu/tests/fixtures/phase3/`，与 Phase 1/2 fixture 目录隔离）
- Commit message 统一 `feat(coach-phase3): <one-line summary>` 或 `test(coach-phase3): <one-line summary>` 前缀
