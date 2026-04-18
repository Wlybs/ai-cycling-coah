# AI Coach — Phase 2 Implementation Plan (Index)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用确定性的 Periodization Engine + Session Designer 替换目前"一次性把 JSON 扔给 Gemini 让它猜一个周计划"的 `plan_generator.py` 旧路径，让每一节课都从生理学意图出发，基于 Phase 1 的 CP/W' / durability / response_profile 算出来，再由 Gemini 负责把叙述性文字写好。

**Architecture:** 两层新包 + 一次可回退的切换：
- `icu/src/coach/periodization/` — 宏观/中观/微观三层周期化引擎，自动识别所处阶段 (Base/Build/Peak/Taper/Race/Transition)，输出 `PeriodizationSnapshot`；
- `icu/src/coach/session_designer/` — 基于 Phase 1 生理模型 + 当周 `MicroCycle` 的意图，合成每一天的训练结构 (`DesignedSession`)，组成 `WeeklyPlan`；Gemini 只做一次"写叙述"的调用；
- `scripts/push_plan.py` 新增 `--engine v2` 选项，默认暂时走旧 `plan_generator.py`（Phase 3 Adaptation Engine 并入前保持可回退）。

**Tech Stack:** Python 3.11+, Pydantic v2, scipy（已在 Phase 1 引入）, google-genai, pytest。不引入新外部依赖。

## Scope

Phase 2 实现 Scheme 4 蓝图中的 **Component 2 + Component 3**：
- Component 2: Periodization Engine (`icu/src/coach/periodization/`)
- Component 3: Session Designer (refactor of `plan_generator.py` as a sibling package)

蓝图：[`../../specs/2026-04-16-ai-coach-scheme-4-blueprint.md`](../../specs/2026-04-16-ai-coach-scheme-4-blueprint.md)
Phase 1 spec（Phase 2 消费的输出契约）：[`../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`](../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md)

### Out of scope (recorded for clarity)

- Multi-expert Planner/Critic/Physiologist consensus (Phase 3)
- Decision ledger / daily adaptation engine (Phase 3)
- Evidence RAG / race-specific module / unified persona (Phase 4)
- 修改 Phase 1 已交付文件：`src/coach/physiology/*`、`src/coach/deep_analyzer/*`、`scripts/sync_data.py`、`scripts/refresh_physiology.py`、`scripts/run_deep_analysis.py`、`scripts/update_coach_brief.py`、`src/coach/phase1_injection.py`、`src/coach/brief_updater.py`
- 删除旧 `plan_generator.py`：Phase 2 只做并行替代 + 回退开关，Phase 3 才移除 legacy

## Foundational contracts (read before starting any file)

### Inputs Phase 2 consumes（来自 Phase 1，不新建、不重算）

| Path | Pydantic model | Keys used in Phase 2 |
|---|---|---|
| `coach_memory/physiology/cp_w_current.json` | `CPWModel` | `cp_watts`, `w_prime_joules`, `fit_r_squared`, `athlete_ftp_set` |
| `coach_memory/physiology/durability.json` | `DurabilityCurve` | `decay_rate_pct_per_1000kj["60s"]`, `decay_rate_pct_per_1000kj["300s"]`, `sample_size_rides` |
| `coach_memory/physiology/response_profile.json` | `ResponseProfile` | `types[<session_type>].tolerance_class`, `knee_loading.flag`, `knee_loading.standing_climb_minutes_90d` |
| `coach_memory/deep_analysis/summary_latest.json` | — | `headline_verdict`, `stimulus_score`, `progression_flag`, `next_plan_hints`, `knee_flag` |
| `icu_data_warehouse/2_Wellness/wellness_history.json` | — | `ctl`, `atl`, `rampRate`, `restingHR`, `hrv`, date 字段 |
| `icu_data_warehouse/8_Events/events.json` | — | `category`, `name`, `start_date_local`, `description`（筛选 RACE / 重要赛事） |
| `icu_data_warehouse/1_Profile/athlete.json` | — | `ftp`, `hr_max`, `weight` |
| `coach_memory/race_calendar.md`（可选手工） | — | 人类可读 fallback，当 events 无 RACE 分类时使用 |

### Outputs Phase 2 produces（全部新增，写到 `coach_memory/periodization/` 和 `reports/`）

```
coach_memory/
├── periodization/
│   ├── phase_current.json         # current phase + transition reasons (由 phase_detector 写)
│   ├── macro_plan.json            # season layout (由 macro_planner 写)
│   ├── meso_block.json            # current 3-6-week block (由 meso_builder 写)
│   ├── micro_cycle_YYYY-WW.json   # current week's daily intent sequence (由 micro_cycle 写)
│   └── periodization_current.json # facade snapshot: 合集，供 session_designer 消费
└── reports/
    ├── plan_YYYYMMDD.json         # 兼容旧格式（Pydantic 校验后的 WeeklyPlan）
    ├── plan_YYYYMMDD.md           # 叙述 markdown
    └── plan_YYYYMMDD.trace.json   # 新增：每日 DesignedSession 的物理来源 trace（CP/W'、模板来源、TSS 计算）
```

### User-approved decisions (locked 2026-04-18)

These shape safety/protection rules; any future PR that removes or loosens them must state justification.

1. **CTL_BASE_PROTECT = 75** — 当 `last_ctl < 75` 且不处于 TAPER/PEAK/RACE 窗口时，强制 Phase = BASE。目的：伤病恢复后重返、长停训后重新加载时不被直接安排高强度。落地位置：`periodization/phase_detector.py` rule #4；`periodization/macro_planner.py` 无赛历默认路径。
2. **HARD_DAYS_WEEKLY_LIMIT = 4** — 一周 HARD 日数 ≥ 4 触发 `w_prime_weekly_overdraw` violation。Assembler 自动把第 4 次起的 HARD 日降级为 MEDIUM (sweet-spot)。依据：标准 BUILD 周 2–3 次 HARD 是常态；4 次起累积疲劳风险显著。落地位置：`session_designer/safety_guards.py`；`session_designer/assembler.py::_revise_for_violations`。

### Stable naming conventions (用于跨文件引用)

- 所有 Pydantic 模型放 `types.py`，类名用 `PascalCase`，字段用 `snake_case`。
- 阶段枚举值：`Phase.BASE / BUILD / PEAK / TAPER / RACE / TRANSITION`（大写常量，匹配 blueprint 文案）。
- 每日 `IntensityTier`：`REST / EASY / MEDIUM / HARD / RACE_SIM`（大写常量）。
- 每日 `SessionType`：`Rest / Recovery / Aerobic / Tempo / Threshold / VO2max / Neuromuscular / Race`（与旧 `plan_generator.DayPlan.training_type` 完全一致，保证 ICU 日历同步兼容）。
- JSONL 日志模块名：`periodization_engine`、`session_designer`（复用 Phase 1 的 `src.coach.common.logging.get_logger`）。

## Execution rules (read before starting any file)

1. **One file per session.** 从 01 → 11 顺序推进。绝不在一个 session 内链式跑多个文件 — 完成、commit、`save-progress`、结束、下一个 session 从头开始。
2. **TDD required.** 每个任务的第一步都是 RED 测试：先写测试，运行确认失败，再写最小实现，运行确认通过，再 commit。
3. **Delegate big writes.** 若某个任务单次需要写 >300 行代码，用 `Agent` 工具派子代理执行，主对话只接收 "done + 文件列表"。
4. **Context hygiene.**
   - 分析已有源代码用 `ctx_execute_file`（摘要入 context）— 只有真要 `Edit` 那个文件时才 `Read` 它。
   - 不要 `Read` Phase 1 已完成的源文件去"确认"；只读 `types.py` 当你要使用它导出的类型。
   - 多个探索命令走 `ctx_batch_execute`，一次 round trip。
5. **Checkpoint discipline.** 每个文件完成后：`pytest` 通过 + commit 用 `feat(coach-phase2):` 前缀 + 运行 `save-progress` + 结束 session。
6. **Never write >600 lines in a single Write.** 若实现文件超过 ~500 行，拆模块。
7. **No Phase 1 edits.** 不改 Phase 1 已交付文件。Phase 1 的 `phase1_injection.py` 在 Phase 2 落地后变成冗余 — 由 Phase 3 移除；Phase 2 只是绕过它（设 `--engine v2` 时不调用）。
8. **Fallback is the first release gate.** 任何时候 `--engine v2` 出错都必须自动回退到旧 `plan_generator.generate_plan()`，不能阻塞用户 push_plan 的日常使用（参见 10-integration.md T46 guardrail）。

## File map

| # | File | Tasks | Focus | Depends on |
|---|---|---|---|---|
| 1 | [01-periodization-infrastructure.md](./01-periodization-infrastructure.md) | T25–T27 | 包骨架、Pydantic 类型、snapshot IO | — |
| 2 | [02-phase-detector.md](./02-phase-detector.md) | T28–T29 | CTL 斜率 + 赛历 → 当前阶段 | 01 |
| 3 | [03-macro-planner.md](./03-macro-planner.md) | T30–T31 | 赛历 → 宏观阶段窗口 | 01, 02 |
| 4 | [04-meso-builder.md](./04-meso-builder.md) | T32–T33 | 3-6 周中观块（3:1 / 2:1 / 极化） | 01, 03 |
| 5 | [05-micro-cycle.md](./05-micro-cycle.md) | T34–T35 | 当周 7 日 intent 序列 + engine 汇总 facade | 01–04 |
| 6 | [06-session-designer-infra.md](./06-session-designer-infra.md) | T36–T38 | designer 包、类型、workout library、intent translator | 01, 05 |
| 7 | [07-session-composer.md](./07-session-composer.md) | T39–T40 | 用 CP/W'/durability 把模板实化成 WorkoutSteps | 06, Phase 1 physiology |
| 8 | [08-weekly-assembler.md](./08-weekly-assembler.md) | T41–T42 | 合成 WeeklyPlan + Pydantic 校验 + 护栏 | 07 |
| 9 | [09-prose-generator.md](./09-prose-generator.md) | T43–T44 | Gemini 单次调用写叙述 + trace | 08 |
| 10 | [10-integration.md](./10-integration.md) | T45–T46 | push_plan.py `--engine v2` 接线 + 回退 | 05, 09 |
| 11 | [11-cli-tests-acceptance.md](./11-cli-tests-acceptance.md) | T47–T49 | `periodization_audit` / `plan_preview` CLI + e2e + 真仓库验收 | 全部 |

Dependency order 严格。每个文件假定所有更低编号文件已完成、测试通过、提交入库。

## Task ID numbering

Phase 1 用了 T1–T24。Phase 2 从 **T25** 开始编号，避免歧义。最终 Phase 2 覆盖 T25–T49（共 25 个 task）。

## Handoff

**Start here:** 打开 [`01-periodization-infrastructure.md`](./01-periodization-infrastructure.md)。应用 `superpowers:subagent-driven-development`。顺序执行 T25–T27。Commit。结束 session。

**Subagent brief template:**

> 使用 `docs/superpowers/plans/phase-2/<file>.md`。遵循 `superpowers:subagent-driven-development`。按顺序执行其中任务。每个任务：先写 RED 测试并运行确认失败 → 实现最小代码 → 再跑一次确认通过 → 提交。不得修改 Phase 1 任何已交付文件（见 00-index.md "Out of scope"）。报告回：(a) 完成的 task ID、(b) 新建/修改的文件、(c) 与计划的任何偏离及原因。

**When all 11 files are green:**
- Phase 2 完成。执行 `11-cli-tests-acceptance.md` 中的验收清单。
- 把 `ai-coach-phase-2` 分支 merge 回 master（需先 rebase 吸收 Phase 1 T22–T24 的合并）。
- 进入 Phase 3 brainstorm：Adaptation Engine + Multi-Expert Consensus + Decision Ledger。
