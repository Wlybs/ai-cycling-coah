# AI 骑行教练系统

基于 **Intervals.icu** 数据的 4 阶段教练系统：

- **Phase 1** — 个体化生理建模（CP/W'、durability、response profile）+ 深度骑行分析
- **Phase 2** — 周期化引擎 + Session Designer（确定性周计划合成）
- **Phase 3** — Daily Adaptation（每日自适应红黄绿灯）+ Multi-Expert Consensus（4 角色议事评审）+ Decision Ledger（append-only 决策账本）
- **Phase 4** — Evidence RAG（教练论点引用 Mujika / Seiler / Skiba / Allen-Coggan / Bourdon 等文献）

**零 LLM API 调用**：所有 LLM 交互走 prompt 文件 → 用户手动粘贴 Gemini CLI / Claude Code → 回填 → 解析。无需 `GEMINI_API_KEY`。

**当前版本**：master @ tag `v4.0-phase4-m1-accepted`，测试 794/794 全绿。

---

## 目录

- [快速开始](#快速开始)
- [日常工作流（5 分钟）](#日常工作流5-分钟)
- [Council 评审工作流（周/双周一次）](#council-评审工作流周双周一次)
- [脚本清单速查](#脚本清单速查)
- [系统架构](#系统架构)
- [文件地图](#文件地图)
- [故障排查](#故障排查)
- [版本与标签](#版本与标签)

---

## 快速开始

```bash
# 1. 首次初始化
cd /mnt/d/Cycling/icu
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 编辑 .env 填入 ICU 凭证（见下方"环境变量"）

# 3. 第一次同步（会做完整的 sync + Phase 1 生理建模 + Phase 3 ledger backfill）
.venv/bin/python scripts/sync_data.py
```

### 环境变量（`.env`）

```ini
API_KEY=...              # Intervals.icu → Settings → API
ATHLETE_ID=i176789       # 你的 athlete id
PROXY_PORT=7897          # 国内网络可选；无代理删除此行
```

> `.env` **永远不入库**，`.gitignore` 已排除。
> 系统**永远不调用** Gemini / OpenAI / Anthropic API（HARD CONSTRAINT）。

---

## 日常工作流（5 分钟）

### 跑一条命令，看一个文件

```bash
cd /mnt/d/Cycling/icu
.venv/bin/python scripts/sync_data.py
```

这一条会做 13 步：

| # | 步骤 | 产物 |
|---|------|------|
| 1 | sync_profile / sport_settings / wellness / power_curves / activities_list / activity_detail / events | `icu_data_warehouse/*` 更新 |
| 2 | build_memory | `coach_memory/*` 提炼 |
| 3 | refresh_physiology | CP/W' 重拟合 |
| 4 | run_deep_analysis | 单次骑行深挖（如有新骑行） |
| 5 | update_coach_brief | `GEMINI.md` 注入最新 Coach Brief |
| 6 | **Phase 3 ingest_ledger** | Phase 2 决策回灌 ledger |
| 7 | **Phase 3 daily_adapt** | 4 信号评估 → ledger `adaptation_verdict` |
| 8 | **Phase 3 action_suggester** | 终端打印主动建议 |

### 看结果

```bash
# 看今日 verdict（黄/红时才会有文件，绿色不写）
ls coach_memory/adapter/today_*.md
cat coach_memory/adapter/today_<日期>.md

# 看 ledger 最新决策
tail -1 coach_memory/ledger/decisions.jsonl | python3 -m json.tool

# 看 suggester 当前在催什么
.venv/bin/python -c "
from src.coach.common.action_suggester import suggest_actions, print_suggestions
from pathlib import Path
print_suggestions(suggest_actions(
    Path('coach_memory/ledger/decisions.jsonl'),
    Path('coach_memory/periodization'),
    Path('coach_memory/deep_analysis'),
), header='📌 当前建议')"
```

### 判断逻辑

| Verdict | 表现 | 你做什么 |
|---|---|---|
| **🟢 GREEN** | 没有 today_md 文件，suggester 也无动作 | 按原计划训练，不用动 |
| **🟡 YELLOW** | today_md 含温和提醒（降一档强度、warmup 延长） | 自己决定改不改 |
| **🔴 RED** | today_md 含替代 session + apply 命令 | 想接受 → 跑下方 apply_adaptation |

### 红灯时一键写回 ICU 日历

```bash
.venv/bin/python scripts/apply_adaptation.py --confirm <日期>
```

把替代 session（如 Threshold → Recovery）真实推送到 ICU。**HUMAN_GATE 设计**：sync_data 自动流程绝不写回，必须主动跑这条才会动。

---

## Council 评审工作流（周/双周一次）

当 suggester 提示"距上次 consensus_verdict 已超过 14 天"或"phase 切换需复审"时，跑这条链：

```bash
# 1. 一键拼 verdict_request（从 coach_memory + warehouse 自动构造）
.venv/bin/python scripts/prepare_verdict_request.py --out /tmp/vr.json

# 2. 生成 council prompt（自动注入 Phase 4 References）
.venv/bin/python scripts/run_consensus.py --mode council \
    --verdict-request /tmp/vr.json \
    --out /tmp/council.prompt.md

# 3. 复制 /tmp/council.prompt.md 全文进 Gemini CLI / Claude Code 教练模式
#    让 4 角色（Planner/Critic/Physiologist/Arbiter）评审
#    保存返回内容到 /tmp/council.response.md

# 4. 解析回复 + 写入决策账本
.venv/bin/python scripts/finalize_consensus.py \
    --response /tmp/council.response.md \
    --ledger coach_memory/ledger/decisions.jsonl \
    --athlete-state /tmp/vr.json \
    --confirm
```

### Council prompt 结构

prompt 文件分 4 个 section + Phase 4 References 段：

```
Section A — Roles & Hard Rules
  · Planner / Critic / Physiologist / Arbiter 各自职责
  · UNDER-DOSED 6-item 检查清单
Section B — Input Data
  · weekly_plan / athlete_state / physiology / wellness_trend / periodization_summary
Section C — History triplets （ledger 中相似 context 的过往决策）
Section D — Output schema（response_parser 强校验的格式契约）

## References (auto-retrieved by Phase 4 evidence retriever)
  1. **[ULID] Title** (score X.XXX)
     - matched: ...
     - finding: ...
     - dosing_hint: ...
```

### 不满意 council 这一轮？升级 strict 模式

```bash
.venv/bin/python scripts/run_consensus.py --mode strict \
    --reuse coach_memory/consensus/<上一轮目录>
# 4 步独立 prompt（Planner / Critic / Physiologist / Arbiter 各跑一遍）
# 每步都需要单独的 LLM 回复 + finalize_consensus --mode strict --step N
```

---

## 脚本清单速查

### 日常 / 自动化

```bash
.venv/bin/python scripts/sync_data.py                      # 主同步（含全部 13 步）
.venv/bin/python scripts/apply_adaptation.py --confirm <日期>  # 红灯时把替代 session 写回 ICU
```

### Council 评审

```bash
.venv/bin/python scripts/prepare_verdict_request.py --out <path>             # 拼 verdict_request
.venv/bin/python scripts/run_consensus.py --mode council|strict ...          # 生成 prompt
.venv/bin/python scripts/finalize_consensus.py --response <md> --confirm     # 解析回复入账本
```

### Phase 4 Evidence 维护

```bash
.venv/bin/python scripts/evidence_lint.py --corpus evidence_corpus/   # 校验种子卡片
# 加新卡片：放 evidence_corpus/<新ULID>.md，按现有格式写 TOML frontmatter + body，再 lint 一次
```

### 数据 / 分析（按需）

```bash
.venv/bin/python scripts/sync_profile.py / sync_wellness.py / ...     # 单独同步某一类
.venv/bin/python scripts/build_memory.py                              # 仅重建 coach_memory
.venv/bin/python scripts/refresh_physiology.py                        # 仅刷新 CP/W'
.venv/bin/python scripts/run_deep_analysis.py <ride_id>               # 单次骑行深挖
.venv/bin/python scripts/extract_ride_summary.py <ride_id>            # 提取骑行结构化摘要
.venv/bin/python scripts/analyze_gpx.py <gpx>                         # GPX 赛道地形分析
.venv/bin/python scripts/push_plan.py [--push --plan-file <json>]     # 周计划生成 + ICU 推送
.venv/bin/python scripts/manage_memory.py [--apply|--status]          # 清理过期 memory 条目
.venv/bin/python scripts/ingest_ledger.py --memory ... --warehouse .. # 单独跑 Phase 2→ledger 回灌
.venv/bin/python scripts/daily_adapt.py --date YYYY-MM-DD --memory .. # 单独跑某天 adapter
```

### 运行测试

```bash
.venv/bin/pytest tests/ -q                # 全套（794 项，约 30s）
.venv/bin/pytest tests/unit/evidence/ -q  # 仅 Phase 4
.venv/bin/pytest tests/e2e/ -q            # 端到端
```

---

## 系统架构

```
Intervals.icu API
       ↓
icu_data_warehouse/  ← 原始数据（不要手动改）
       ↓
src/coach/physiology/   ← Phase 1: CP/W'、durability、response_profile
src/coach/deep_analyzer/ ← Phase 1: 单次骑行多维分析
       ↓
src/coach/periodization/  ← Phase 2: macro→meso→micro 周期化
src/coach/session_designer/ ← Phase 2: 周计划合成
       ↓
src/coach/adapter/        ← Phase 3: 每日 4 信号评估 + 红黄绿决策
src/coach/consensus/      ← Phase 3: 4 角色议事 (council + strict 双模式)
src/coach/ledger/         ← Phase 3: append-only 决策账本（JSONL）
       ↓
src/coach/evidence/       ← Phase 4: 文献检索 (TF-IDF) + Council prompt References 段
       ↓
src/coach/common/action_suggester/ ← 4 触发器主动建议下一步动作
```

### 关键约束（HARD CONSTRAINTS）

1. **零 LLM API 调用** — 所有 LLM 交互走 prompt 文件 + 手工粘贴 + 解析
2. **HUMAN_GATE on ICU writes** — 任何写回 ICU 日历的操作必须用户主动 `--confirm`
3. **Append-only 决策账本** — 永不修改历史，纠错走 `superseded_by` 指针
4. **冻结模块** — Phase 3 council_prompt / strict_prompt / response_parser / history_injector 在 Phase 4 后完全冻结，不得改一字

---

## 文件地图

### 顶层

| 文件 | 用途 |
|------|------|
| `GEMINI.md` | Gemini CLI 系统提示词 + Coach Brief（由 `update_coach_brief.py` 自动刷新） |
| `requirements.txt` | Python 依赖（无新增依赖；纯 stdlib + scipy + pydantic + pytest） |
| `.env` | API 密钥（**禁止提交**） |
| `.gitignore` | 排除 `.env / .venv / __pycache__ / icu_data_warehouse / reports / coach_memory / logs / .pytest_cache` |

### `scripts/` — 可执行 CLI

按照"何时用"分组：

**日常自动化** （随 `sync_data.py` 触发）
- `sync_*.py` × 8 — 各类数据同步
- `build_memory.py / refresh_physiology.py / update_coach_brief.py` — 派生数据
- `ingest_ledger.py / daily_adapt.py` — Phase 3 自动管线

**用户手动触发**
- `apply_adaptation.py --confirm <date>` — 红灯接受替代 session
- `prepare_verdict_request.py` — 拼 council 输入
- `run_consensus.py / finalize_consensus.py` — council 评审
- `push_plan.py [--push --plan-file ...]` — 周计划生成 + ICU 推送

**按需诊断**
- `analyze_rides.py / analyze_gpx.py / extract_ride_summary.py / run_deep_analysis.py` — 分析
- `evidence_lint.py` — 校验种子卡库
- `physiology_audit.py` — 生理档案审计
- `manage_memory.py [--status|--apply]` — 清理过期 memory

### `src/coach/` — 核心模块

| 子包 | 用途 | Phase |
|---|---|---|
| `physiology/` | CP/W' 拟合、durability、response profile | 1 |
| `deep_analyzer/` | 单次骑行多分析器 | 1 |
| `periodization/` | macro/meso/micro 周期化 | 2 |
| `session_designer/` | 周计划合成（compose_session） | 2 |
| `adapter/` | daily_adapt + rules + session_revisor + apply_adaptation | 3 |
| `consensus/` | council_prompt + strict_prompt + response_parser + history_injector | 3 |
| `ledger/` | LedgerWriter + LedgerReader (append-only JSONL) | 3 |
| `evidence/` | EvidenceCard schema + CorpusReader + TF-IDF retriever + prompt_section | 4 |
| `common/` | logging + action_suggester + verdict_request_builder + 工具 | 跨 phase |

### `evidence_corpus/` — Phase 4 文献卡库

5 张种子卡（`<ULID>.md` 命名，TOML frontmatter + Markdown body）：

| ULID | 主题 | 适用 Phase |
|---|---|---|
| `01HXR0NM8KT...A1` | Mujika & Padilla 2003 — Taper meta-analysis | competitive / transition |
| `01HXR0NM8KS...B2` | Seiler 2010 — Polarized 80/20 | base / build |
| `01HXR0NM8KW...C3` | Skiba 2012 — W' balance / recovery kinetics | build / peak / competitive |
| `01HXR0NM8KF...D4` | Allen-Coggan FTP testing | base / build |
| `01HXR0NM8KV...E5` | Bourdon et al. 2017 — VO2max interval dose | build / peak |

**加新卡**：
1. 文件名必须是 `<新ULID>.md`（26 字 Crockford base32，无 I/L/O/U）
2. TOML frontmatter 含 `ulid / title / authors / year / source / tags / phase / applies_to / finding / dosing_hint / contraindications / status / superseded_by`
3. Body 段落自由（中英混排），Markdown
4. 跑 `scripts/evidence_lint.py --corpus evidence_corpus/` 验证 0 violation
5. 自动出现在下次 `run_consensus.py` 输出的 References 段

### `coach_memory/` — 教练记忆（自动 + 手动混合）

**自动生成**（每次 sync_data 覆盖，禁止手动编辑）
- `athlete_snapshot.json / fitness_trend.json / training_history.json / training_analysis.json`
- `physiology/cp_w_current.json / durability.json / response_profile.json`
- `periodization/phase_current.json / periodization_current.json / micro_cycle_*.json / macro_plan.json / meso_block.json`
- `plans/plan_<YYYYMMDD>.json` — 周计划
- `adapter/today_<日期>.md` — Phase 3 红黄灯报告
- `adapter/proposed_session_<日期>.json` — 红灯时的替代 session
- **`ledger/decisions.jsonl`** — Phase 3 决策账本（append-only）

**手动维护**（自动机制不会覆盖）
- `body_status.md` — 伤病、疲劳、身体状况（`[resolved]` 后 30 天自动归档）
- `race_calendar.md` — 比赛日历
- `periodization_2026.md` — 年度周期化方案
- `nutrition_strategy.md` — 补给方案
- `workout_library.md` — 课表模板
- `pb_reference.md` — PB 参考
- `coach_log.md` — 教练观察日志（>80 条时旧条自动汇总）

### `icu_data_warehouse/` — 原始数据仓库

8 个目录（`1_Profile / 2_Wellness / 3_PowerData / 4_Activities_List / 5_Activities_Detail / 6_SportSettings / 7_Gear / 8_Events`），由 sync 脚本写入，**禁止手动改**。

### `tests/` — 测试

- `tests/unit/` — 模块单元（physiology / periodization / session_designer / adapter / consensus / ledger / evidence / common）
- `tests/e2e/` — 端到端（Phase 3 全链路、evidence prompt 集成、full sync）
- `tests/fixtures/` — 共享 fixture 数据

---

## 故障排查

| 症状 | 可能原因 | 处理 |
|---|---|---|
| `sync_data.py` 报 401 | API_KEY / ATHLETE_ID 错 | 重新生成 ICU API key 写入 `.env` |
| sync 极慢/超时 | 国内网络无代理 | `.env` 设 `PROXY_PORT=<本地代理端口>` |
| `daily_adapt.py` 报 `No wellness entry for <date>` | 当日 wellness 还没 sync | 先跑 `sync_wellness.py` 或 `sync_data.py` |
| `daily_adapt.py` 报 `validation error: soreness_score` | ICU 实际数据 vs schema 不一致 | 已修于 v3.0.1（Optional soreness）；如再现请贴报错 |
| `apply_adaptation.py` 报 `No adaptation_verdict found` | 当日 daily_adapt 没成功写 verdict | 检查 `coach_memory/ledger/decisions.jsonl` 最后一条；必要时手动跑 `daily_adapt.py --date <日期>` |
| `run_consensus.py` 报 `verdict-request file not found` | 未跑 `prepare_verdict_request.py` 或路径错 | 先跑 prepare_verdict_request 生成 |
| Council prompt 中 References 段为 "(none directly applicable)" | query terms 与卡片 tags/body/phase 都没交集 | 加 `--evidence-query <自定义 terms>` 或往 corpus 加更贴近的卡 |
| `finalize_consensus.py` 报 `Critic must contain ≥3 numbered points` | LLM 回复不规范 | 把 prompt 完整重新粘贴到 LLM；按 Section A 的 hard rule 让 LLM 重写 |
| `Phase 3 suggester unavailable` | sys.path 缺失（已修于 `f2ed381`） | 拉最新 master |
| 教练对话读不到最新数据 | 忘了 sync_data | 跑 `sync_data.py`（含 build_memory + refresh_physiology + update_coach_brief） |
| 测试 `test_apply_adaptation_writes_adaptation_applied` 失败 | 日期耦合（修于 `eeba7d0` ICU_FORCED_NOW_ISO 注入） | 拉最新 master |

---

## 版本与标签

| Tag | Commit | 内容 |
|---|---|---|
| `v2.0-phase2-complete` | `0fba835` | Phase 2 周期化 + Session Designer 完成 |
| `v3.0-phase3-m1-accepted` | `8d5afe8` | Phase 3 M1：adapter + consensus(council) + ledger |
| `v3.0.1` | `9aa370b` | Optional soreness 修补（解 ICU 真实数据 None） |
| `v4.0-phase4-m1-accepted` | `db1c918` | Phase 4 M1：Evidence RAG + 5 种子卡 + Council References 注入 |

---

## 路线图（已知未做的）

按优先级（用户使用反馈驱动启动）：

1. **Component 9 — Race-Specific Module** — 赛道地形建模 + race-sim ride generator + openers，**等真实赛事 schedule 出现** 时启动
2. **Component 10 — Unified Coach Persona** — 合并 GEMINI.md + 各模块 prompt 为单一 base persona，**对当前 prompt 风格不满意时** 再做
3. **Component 11 后半 — Observability tools** — Gemini req/resp 完整捕获 + 决策 replay CLI + diff/compare 工具，**ledger 长大或要做事后复盘** 时再做
4. **task #5：ingest_ledger 识别 plan_*.{json,md}** — 当前真实数据下 weekly_plan_assembled = 0，影响 Critic 历史 context 完整性。修起来 ≤30 行，**不影响 daily 使用**
5. **Evidence corpus 扩到 30-50 张** — 5 张种子卡覆盖 taper / polarized / W' / FTP / VO2max；扩展按使用反馈定主题

---

## bd Issue Tracking（开发用）

```bash
bd ready                 # 查看可做的任务
bd show <id>             # 查看详情
bd update <id> --claim   # 认领
bd close <id>            # 标记完成
bd sync                  # 同步到 git
```

更多见仓库根目录 `AGENTS.md`。
