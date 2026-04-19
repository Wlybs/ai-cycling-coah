# AI Coach — Phase 3 Blueprint

> Adaptive Intelligence: Daily Adaptation + Multi-Expert Consensus + Long-Term Memory

**Status:** 蓝图已定稿 (2026-04-19)，待实施
**Dependencies:** Phase 1（生理模型+深度分析器，已并入 master）、Phase 2（Periodization Engine + Session Designer，进行中于 `ai-coach-phase-2` 分支）
**Parent:** [`2026-04-16-ai-coach-scheme-4-blueprint.md`](./2026-04-16-ai-coach-scheme-4-blueprint.md) —— 本蓝图是整体方案 4 的 Component 5/6/7 具体化

---

## Motivation

Phase 1 交付了"这个运动员"的生理模型（CP/W'、durability、响应轮廓）和深度事后分析。Phase 2 交付了从生理意图到每日 session 的确定性合成。但系统到 Phase 2 结束时仍有 **三个结构性缺陷**：

1. **没记忆。** 每次生成周计划都是无历史的独立推理。过去相似 context 下的 outcome（做了什么、实际 stimulus 如何、progression 趋势）完全不进下次决策。用户反馈 "coach 分析太表面" 的根因 —— 没有历史 = 每次重新猜。

2. **没审查。** Phase 2 的 `session_designer` + Gemini 单次叙述调用是流水线，输出直接写 `reports/plan_*.json`。没有反向质疑机制。用户反馈 "coach 练得不够狠" 的直接体现 —— 单一视角容易偏乐观。

3. **没适应。** 每周一的计划生成后就定死；后续 7 天里无论 HRV 崩、睡眠差、前日 W' 透支，原定 HARD 日照样挂在 ICU 日历上。调整完全靠用户自己觉察 —— 系统不参与。

Phase 3 对症下药：**Adaptation Engine**（每日再评估）、**Multi-Expert Consensus**（多视角审查）、**Decision Ledger**（长期记忆）。三者联动，让 Coach 第一次具备"反思 + 调整 + 记忆"。

---

## Hard Constraints

1. **不修改 Phase 1/2 任何已交付代码。** 包括 `src/coach/physiology/*`、`src/coach/deep_analyzer/*`、`src/coach/periodization/*`、`src/coach/session_designer/*`。Phase 3 对 Phase 1/2 产物**只读**，通过公开的 Pydantic 类型反序列化。
2. **零 LLM API 调用。** 所有 LLM 交互走 prompt 文件工作流：Python 生成 prompt → 用户手工粘贴到 Gemini CLI / Claude Code coach mode → 用户把回复存回文件 → Python 解析。系统绝不 import `google.genai` 或类似 SDK 做 request。
3. **人类闸门必选。** 任何写回 ICU 日历、覆盖既有训练计划的操作，必须经用户一键命令确认。Adapter 红灯绝不自动推送。
4. **Python 3.11+ / Pydantic v2 / 不引入新外部依赖。** 复用 Phase 1/2 已装的 `scipy`, `pydantic`, `pytest`。

---

## Design Principles

- **只建议，不替代决策。** 系统可以"建议"跑 Consensus、"建议"接受 Adapter 红灯；最终动作必须用户主动触发。
- **Append-only 写入。** 决策账本永不修改历史记录；纠错走 `superseded_by` 指针。
- **Deterministic 在前，LLM 在后。** Adapter 四信号阈值判定是纯 Python 规则；Consensus 的硬规则校验（Critic 必须 ≥3 条、Physiologist 必须引 3/4 项数据）也是 Python 校验 —— LLM 只负责生成内容，结构性正确性由代码保证。
- **回退优于出错。** Ledger 不存在 → history 注入空 section + 提示 "no history"；Gemini 回复不合规 → parser 拒绝入库 + 提示重跑 prompt。绝不在数据缺失时瞎编。
- **File-first 而非 stateful service。** 所有模块间通信走 JSON 文件，不起长进程、不需要 daemon。Phase 3 仍是 "跑几下脚本" 的工作流。

---

## Architecture

### 组件总览

```
icu/src/coach/
├── physiology/          ← Phase 1（不动）
├── deep_analyzer/       ← Phase 1（不动）
├── periodization/       ← Phase 2（不动）
├── session_designer/    ← Phase 2（不动）
│
├── ledger/              ← Phase 3 新增 (Component 7)
│   ├── types.py             # DecisionEntry Pydantic 模型
│   ├── writer.py            # LedgerWriter: 原子 append JSONL
│   ├── reader.py            # LedgerReader: query + query_similar
│   └── ingester.py          # 扫 Phase 2 产物回补 entries
│
├── adapter/             ← Phase 3 新增 (Component 5)
│   ├── types.py             # AdaptationVerdict, SignalSnapshot
│   ├── rules.py             # 4 信号阈值 + 红/黄/绿判定
│   ├── session_revisor.py   # 红灯时用 Phase 2 designer 合成替代 session
│   └── prompt_builder.py    # 人类可读 nudge/override 说明生成
│
└── consensus/           ← Phase 3 新增 (Component 6)
    ├── types.py             # CouncilVerdict, ExpertTurn
    ├── council_prompt.py    # 默认 council 模式 prompt 拼装
    ├── strict_prompt.py     # strict 4-step prompt 拼装
    ├── response_parser.py   # 抽取 <summary_json> + 硬规则校验
    └── history_injector.py  # 从 Ledger 抽取相似 context 注入 prompt
```

### 新脚本

```
icu/scripts/
├── daily_adapt.py           # sync_data.py 之后追加；产出 adapter verdict
├── apply_adaptation.py      # 红灯时用户敲；真正写回 ICU 日历
├── run_consensus.py         # 生成 council.prompt；--mode strict 切 4-step
├── finalize_consensus.py    # 解析 response、写 ledger、生成 verdict
└── ingest_ledger.py         # 扫 Phase 2 产物回补 ledger entries
```

### 数据流

```
─── 周级节奏（由用户发起） ───────────────────────────────────

push_plan.py --engine v2 ──→ Phase 2 产出 plan_YYYYMMDD.{json,md,trace.json}
                                     │
                                     ▼  (可选 --with-consensus)
                             run_consensus.py ──→ council.prompt.md
                                     │
                                     ▼  [用户粘贴 → 存回 council.response.md]
                             finalize_consensus.py
                                     │
                                     ├── 解析 + 校验硬规则
                                     ├── 写 ledger: consensus_verdict
                                     └── 产出 verdict.md（含引导文案：
                                         "如不满意可敲 run_consensus.py --mode strict --reuse <ts>"）

─── 日级节奏（sync_data 自动触发） ────────────────────────────

sync_data.py ──→ ingest_ledger.py ──→ 补写 Phase 2 派生的 ledger entries
              └→ daily_adapt.py ──→ AdaptationVerdict
                        │
                        ├── green: 写 ledger，结束
                        ├── yellow: 写 ledger + today_yellow_<date>.md（nudge）
                        └── red:   写 ledger + today_red_<date>.md
                                   + proposed_session_<date>.json
                                   + 终端建议敲 apply_adaptation.py
                                          │
                                          ▼  (用户确认)
                                   apply_adaptation.py ──→ ICU PATCH
                                                       └→ 写 ledger: adaptation_applied
```

---

## Component 5 · Adaptation Engine

### 职责

每日对比"今天原计划"和"今天实时状态"，判定 green / yellow / red，并在红灯时合成可执行的替代 session。

### 输入（只读 Phase 1/2 产物）

| 文件 | 用途 |
|---|---|
| `coach_memory/periodization/micro_cycle_<year-week>.json` | 今日 `DayIntent`（SessionType + IntensityTier） |
| `coach_memory/reports/plan_<date>.json` | 今日完整 `DesignedSession` |
| `icu_data_warehouse/2_Wellness/wellness_history.json` | HRV / restingHR / sleep / soreness / fatigue / mood |
| `coach_memory/deep_analysis/summary_latest.json` | 昨日 `stimulus_score`, `progression_flag`, `knee_flag` |
| `coach_memory/physiology/cp_w_current.json` | `w_prime_joules` |
| `coach_memory/ledger/decisions.jsonl` | 最近 14 天 adapter verdict（用于连红检测） |

### 规则引擎（确定性 Python）

四个独立信号打分，**任一出红即红**：

| 信号 | 阈值（Green / Yellow / Red） | 数据源 |
|---|---|---|
| HRV 偏离 vs 28d rolling mean | ≥ −5% / −5~−10% / <−10% 或 连续 2d <−5% | wellness_history |
| 睡眠债 | ≥7h 且 7d 均 ≥6.5h / 5.5~7h / <5.5h 或 连续 3d <6h | wellness_history |
| W' 账户 (昨日 W'balance_min %) | >−50% / −50~−80% / <−80% 或 昨日 stimulus>0.85+今日 HARD | deep_analysis + physiology |
| 主观（fatigue/soreness/mood） | 全 ≥3 / 任一 =2 / 任一 =1 或 任二 =2 | wellness_history |

**特殊护栏**：
- `knee_flag == "caution"` + 今日计划含 standing climb/VO2max → 强制红
- 过去 3 天已有 3 次红 + 今天又判红 → 升级为 "建议 48h 完全休息"（写专门 rest prescription）

所有阈值常量定义在 `adapter/rules.py` 顶部，每条 docstring 写**为什么是这个数字**（避免调参失忆）。

### 三档动作

| Verdict | Ledger | 可见文件 | ICU 动作 |
|---|---|---|---|
| GREEN | 1 条 entry（signals_snapshot） | 无 | 无 |
| YELLOW | 1 条 entry + nudge_lines | `adapter/today_yellow_<date>.md` | 无 |
| RED | 1 条 entry（含 original + proposed ref） | `adapter/today_red_<date>.md`<br>`adapter/proposed_session_<date>.json` | 无（等用户敲命令） |

### 红灯替代 session 合成

`session_revisor.py` 调 Phase 2 `session_designer` 包已暴露的合成入口（Phase 2 T39–T40 交付的 composer / assembler 公开函数；具体函数名以 Phase 2 `types.py` + `__init__.py` 实际导出为准），传入降载 intent 表：

| 原 intent | 降载为 |
|---|---|
| HARD（Threshold / VO2max / Neuromuscular / Race） | Recovery 45–60min Z2 |
| MEDIUM（Tempo / sweet-spot） | Easy 60–90min Z2 |
| EASY（Aerobic） | Rest（完全不骑） |
| REST | 保持 Rest |

产出是合法的 `DesignedSession`（Phase 2 Pydantic 校验通过）。

### apply_adaptation.py 行为

```
1. 读 proposed_session_<date>.json
2. 读 .env 获取 ICU API key
3. ICU 日历: 
   a. 找当天原 event_id（通过 date 匹配）
   b. PATCH name/description/workout_doc 换成 proposed session
   c. 失败回退: 保留原 event + 新建替代 event + 警告 + 退出非零
4. 写 ledger: decision_type="adaptation_applied", evidence_refs 指向原 + proposed
5. 打印成功
```

ICU 调用不 import Phase 2 的 `push_plan.py`；直接用 `icu/src/fetcher/icu_client.py` 的底层 API 客户端。避免与 Phase 2 脚本耦合。

---

## Component 6 · Multi-Expert Consensus

### 职责

让 Gemini 在单次（或 4 轮严格模式）prompt 里扮演 Planner / Critic / Physiologist / Arbiter，对 Phase 2 产出的 WeeklyPlan 做结构化审查。

### 触发方式

**系统永不自动触发**。

- 用户手动：`icu/.venv/bin/python scripts/run_consensus.py`
- 周计划生成时 opt-in：`push_plan.py --engine v2 --with-consensus`
- 启发式**建议**（只打印文字，不执行）：
  - Phase Detector 在本周触发阶段切换（phase_transition）
  - Phase 2 触发了 safety guard violation（weekly_plan_assembled 的 trace 含 violations）
  - 距上次 consensus_verdict > 14 天
  - 最近 3 条 deep_analysis stimulus_score 趋势下滑

这些触发条件由 Phase 3 集成任务中新增的一个 summary 打印钩子实现（`coach/common/action_suggester.py` 工具模块 + 在 `sync_data.py` 或 `daily_adapt.py` 末尾调用；具体落点在 M1 集成任务决定）。钩子只印字，不执行命令。

### 默认模式：单 prompt council

`council_prompt.py` 产出 `coach_memory/consensus/<timestamp>/council.prompt.md`。四段结构：

- **Section A — 角色与硬规则**
  - Planner: `<planner>` 包裹，给每日 prescription + 本周训练目标 + 引 ≥2 个数值依据
  - Critic: `<critic>` 包裹，**≥3 条 Planner 没提的反对点**，每条引具体数据；并运行 **6 条 UNDER-DOSED 检查**（见下）
  - Physiologist: `<physiologist>` 包裹，**引 3/4 项物理量**（CP, W', durability, response_profile），给周末 W' balance 预估，点出 knee_flag 状态
  - Arbiter: `<arbiter>` 包裹，出 ACCEPT / REVISE / REJECT + confidence ∈ [0,1] + 一句话 justification；REVISE 时列具体改动 (day, from, to)
- **Section B — 输入数据：** WeeklyPlan JSON, PeriodizationSnapshot, 生理 snapshot 摘要, 28 天 wellness 趋势
- **Section C — 历史参考（Active Ledger）：** 3–8 条最相似 context 的 `weekly_plan_assembled` + 追溯后续 `consensus_verdict` / `adaptation_verdict` / deep_analysis stimulus_score → 压成 context-verdict-outcome 三元组
- **Section D — 输出格式：** 四 role 顺序 + 末尾 `<summary_json>` parsable JSON

### 6 条 UNDER-DOSED 检查清单（Critic role 硬规则）

每条给 OK / UNDER-DOSED 判定：

1. 本周 HARD 日数 vs Meso 阶段应配额（BUILD: 2–3 次底线；≤1 即 UNDER-DOSED）
2. VO2max/Threshold session 工作间总时长 vs `response_profile.types[<type>].tolerance_class`（high tolerance = 18–24min work 底线）
3. 周总 TSS vs CTL 对应 acceptable load band（低于下界 = UNDER-DOSED）
4. Race 前 6 周是否至少 1 次 race-sim session（PEAK phase 必做）
5. 过去 3 周 stimulus_score 均值 < 0.45 → UNDER-DOSED
6. 过去 3 周是否至少 2 次 session 使 W' balance < −50%（无 = 缺高强度）

### Strict 模式触发：用户不满意时升级

Council 的 `verdict.md` 末尾自动追加引导文案：

> 如对此结论不满意，可敲：
> `icu/.venv/bin/python scripts/run_consensus.py --mode strict --reuse <timestamp>`
> 将复用本次输入数据，拆成 4 轮独立 prompt（Planner → Critic → Physiologist → Arbiter）。

Strict 流：`strict_prompt.py` 生成 `1_planner.prompt.md`；用户粘贴、存回 `1_planner.response.md`；敲 `finalize_consensus.py --step 2` 自动拼 `2_critic.prompt.md`（含 Planner 回复 + "挑刺"指令）。以此类推至 step 4，产出 strict_verdict.md。

Strict 和 council 共享 90% prompt 模板（Section B/C 输入、Section D 输出格式）；只拆 Section A 的 role 指令。

### 响应解析 + 硬规则校验

`response_parser.py`:
- 抽 `<summary_json>` 块
- 校验 Critic 的 `critic_hard_points` 数组 ≥3
- 校验 Physiologist 内容中出现 CP/W'/durability/response_profile 中至少 3 项关键词
- 校验 Arbiter verdict ∈ {ACCEPT, REVISE, REJECT}
- 校验 confidence ∈ [0,1]
- **任一失败 → 不写 ledger + 打印具体违规条目 + exit 非零 + 建议重跑 prompt**

---

## Component 7 · Decision Ledger

### 存储

单文件 JSONL：`coach_memory/ledger/decisions.jsonl`。不分季度、不建索引（YAGNI：量级在可预见年份内 < 5 MB，全量扫描即可）。

### Schema (`ledger/types.py`)

```python
class AthleteStateRef(BaseModel):
    ctl: float
    atl: float
    tsb: float
    w_prime: int            # joules
    phase: str              # Phase enum value
    week_of_year: int

class DecisionEntry(BaseModel):
    schema_version: int = 1
    entry_id: str           # ULID (time-sortable)
    timestamp: datetime     # UTC
    decision_type: Literal[
        "phase_transition",
        "macro_plan_generated",
        "meso_block_created",
        "micro_cycle_generated",
        "weekly_plan_assembled",
        "consensus_verdict",
        "adaptation_verdict",
        "adaptation_applied",
    ]
    source: str             # e.g. "adapter.daily", "consensus.council"
    athlete_state_ref: AthleteStateRef
    confidence: float | None
    payload: dict           # 按 decision_type 变结构
    evidence_refs: list[str] = []
    superseded_by: str | None = None   # ULID of an EARLIER entry this one supersedes/corrects; set at write time of the newer entry (append-only-safe)
```

### Writer API

```python
writer = LedgerWriter()  # 读 decisions.jsonl
writer.record(
    decision_type="adaptation_verdict",
    source="adapter.daily",
    athlete_state=<auto-built from Phase 1/2 snapshots>,
    payload={...},
    evidence_refs=["physiology/cp_w_current.json"],
    confidence=1.0,
)
# 原子 append: tempfile + os.replace
```

原子性：tempfile → `os.replace` 保证单次 append 要么完整要么不存在；并发场景下用文件锁（`fcntl.flock`）避免 race。

### Reader API

```python
reader = LedgerReader()

# 通用时间窗 + 类型过滤
reader.query(decision_type="consensus_verdict", since=dt, limit=8)

# 相似 context 查询（Active Ledger 的关键）
reader.query_similar(
    athlete_state=current_state,
    decision_type="weekly_plan_assembled",
    ctl_tolerance=5.0,
    phase_match=True,
    limit=5,
)

# 追溯决策链
reader.trace_chain(entry_id="...")  # 从 entry_id 出发顺着 superseded_by 指针回溯到被其修正的更早 entry，返回整条修正链
```

`query_similar` 实现：纯 Python 过滤（phase 全等 + |ctl 差| ≤ tolerance），按时间倒序，取 limit。无需向量检索。

### Ingester（回补 Phase 2 决策，守"不改 Phase 2"约束）

`ingester.py` 扫描规则：

- `periodization/phase_current.json`：若当前 phase 与最新 `phase_transition` entry 的 `to_phase` 不同 → 写新 transition
- `periodization/macro_plan.json`：若文件 mtime > 最新 `macro_plan_generated` entry 时间 → 写新条
- `periodization/meso_block.json`：同上
- `periodization/micro_cycle_*.json`：按 year-week 标识去重
- `reports/plan_*.trace.json`：每个新 plan 写 `weekly_plan_assembled`，payload 摘取 session 物理来源（CP 段、模板来源、TSS 计算）

**幂等**：基于"最新 entry 时间戳 vs 文件 mtime"判断，跑两次只多写需要的 entry。

**执行时机**：`sync_data.py` 末尾自动调 `ingest_ledger.py`；也可手动跑。

### Payload 示例

**consensus_verdict**
```json
{
  "verdict": "REVISE",
  "confidence": 0.72,
  "mode": "council",
  "headline_rationale": "BUILD 第 3 周 HARD 配额不足",
  "critic_hard_points": ["...", "...", "..."],
  "revisions": [{"date": "2026-04-22", "from": "Tempo 60min", "to": "Threshold 4x8"}],
  "prompt_file": "coach_memory/consensus/2026-04-19_2130/council.prompt.md",
  "response_file": "coach_memory/consensus/2026-04-19_2130/council.response.md"
}
```

**adaptation_verdict (red)**
```json
{
  "verdict": "red",
  "signals_snapshot": {
    "hrv_deviation_pct": -12.3,
    "sleep_hours": 5.2,
    "w_prime_balance_min_pct": -85.0,
    "subjective": {"fatigue": 1, "soreness": 2, "mood": 3}
  },
  "triggered_rules": ["hrv_red_threshold", "sleep_debt_acute"],
  "original_session": "Threshold 4x8 @ 250W",
  "proposed_session_ref": "coach_memory/adapter/proposed_session_2026-04-20.json"
}
```

---

## Pain-Point Attack Mapping

| 痛点 | Phase 3 对抗机制 | 落地位置 |
|---|---|---|
| "练得不够狠" | Critic role 6 条 UNDER-DOSED 检查清单强制执行 | `consensus/council_prompt.py` Section A Critic 硬规则 |
| "分析太表面" | Physiologist role 强制引用 3/4 项物理量 + W' balance 预估 | 同上 Physiologist 硬规则 |
| "没记忆、每周从头猜" | Active Ledger 注入相似 context 的 context-verdict-outcome 三元组 | `consensus/history_injector.py` |
| "看着建议不执行" | Adapter 红灯生成完整替代 session + 一键命令 | `adapter/session_revisor.py` + `scripts/apply_adaptation.py` |

---

## Integration Contracts（与 Phase 1/2 的对接）

**只读清单（不改）：**

| Path | Type | 用途 |
|---|---|---|
| `coach_memory/physiology/cp_w_current.json` | `CPWModel` | Adapter + Consensus + Ledger |
| `coach_memory/physiology/durability.json` | `DurabilityCurve` | Consensus |
| `coach_memory/physiology/response_profile.json` | `ResponseProfile` | Consensus |
| `coach_memory/deep_analysis/summary_latest.json` | — | Adapter |
| `coach_memory/periodization/periodization_current.json` | `PeriodizationSnapshot` | Consensus + Adapter |
| `coach_memory/periodization/micro_cycle_*.json` | `MicroCycle` | Adapter |
| `coach_memory/reports/plan_*.{json,md,trace.json}` | `WeeklyPlan` | Consensus + Ingester |
| `icu_data_warehouse/2_Wellness/wellness_history.json` | — | Adapter + Consensus |
| `icu_data_warehouse/1_Profile/athlete.json` | — | Consensus |

**Phase 2 API 调用点：**
- `session_designer.compose_session(intent, physiology)` — Adapter red 路径用，合成降载 session

**回退契约：**
- Ledger 缺失：history_injector 返回空，prompt Section C 显式写 "no historical context available"
- Phase 2 产物缺失：Adapter / Consensus 报清晰错误 + exit；绝不瞎编 input
- Gemini response 不合规：parser 拒绝入库 + 指示重跑

---

## Scope Split

### M1（Phase 3 MVP，必做）

- Ledger infrastructure（types / writer / reader / ingester）
- Adapter（rules / session_revisor / daily_adapt / apply_adaptation）
- Consensus 默认 council 模式（council_prompt / response_parser / history_injector / run_consensus / finalize_consensus）
- `sync_data.py` 集成（ingest_ledger + 建议钩子）
- e2e + 真仓库验收

### M2（Phase 3 可延后，不阻塞 M1 发布）

- Consensus strict 模式（strict_prompt / finalize --step N state machine）
- `ledger_digest.py` 季度回顾 prompt 生成

---

## Out of Scope（推到 Phase 4）

- Evidence RAG / 文献引用 / embedding + 向量检索
- Race-specific module（冲刺前 5 天协议自动化，对接 `problem.md`）
- Unified Persona（统一的 coach 对话入口）
- 删除 Phase 1 的 `phase1_injection.py` / `brief_updater.py`（Phase 4 才收尾）
- 删除 Phase 2 保留的 legacy `plan_generator.py` fallback

---

## Testing Strategy

- **Ledger**: types 往返序列化、原子写入抗中断（kill -9 后仍合法 JSONL）、并发 record 不丢、query_similar 过滤正确、ingester 幂等
- **Adapter**: rules 100% 分支覆盖（黄金值表 + 边界 fixture）、session_revisor 产出合法 `DesignedSession`、apply_adaptation mock ICU client 验 PATCH payload
- **Consensus**: prompt 拼装稳定（固定 fixture 输入 → 固定 prompt 文本哈希）、response_parser 对硬规则违规的 6 种模式全部拒绝、history_injector 空 ledger / 少量 ledger / 完整 ledger 三种路径
- **E2E**: 真 Phase 2 产物 fixture → ingester → run_consensus → 假 Gemini 响应 → finalize → daily_adapt → apply_adaptation，全链路跑通 + ledger 每个 decision_type 都有至少 1 条
- **真仓库验收**: 在 `/mnt/d/Cycling` 上跑一次完整流：`sync_data` → `push_plan --engine v2 --with-consensus` → 手动粘贴 council → `finalize_consensus` → 隔日 `daily_adapt` → assert 所有文件产出符合 schema

---

## End State

Phase 3 完成后的系统表现：

- 每次生成周计划时，可 opt-in 跑 Consensus；Gemini 以三专家 + 仲裁视角审查；Critic 必须跑完 6 条 UNDER-DOSED 检查，Physiologist 必须引用具体生理数字 —— 两项直接对准用户反馈痛点
- 每天早上自动判定红/黄/绿；红灯时用户敲一条命令即可把替代 session 推给 ICU；绿/黄无噪音
- 每个决策（Phase 2 派生的 + Phase 3 新做的）在 Ledger 留一条结构化记录；下次 Consensus 自动把过去 60 天相似 context 的 outcome 注入 prompt → 系统第一次具备记忆
- Phase 1 / Phase 2 代码零改动；所有新能力通过文件契约 + 只读 API 实现
- 不消耗 Gemini API 额度；所有 LLM 交互走 prompt 文件 → 用户粘贴 → 回写的异步工作流

---

## References

- [`2026-04-16-ai-coach-scheme-4-blueprint.md`](./2026-04-16-ai-coach-scheme-4-blueprint.md) — 整体方案 4 蓝图
- [`2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`](./2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md) — Phase 1 spec（Phase 3 消费其产物）
- `docs/superpowers/plans/phase-2/00-index.md`（于 `ai-coach-phase-2` 分支）— Phase 2 计划（Phase 3 消费其产物）
- `problem.md` — 赛前 5 天协议（Phase 4 race-specific 模块将对接）
