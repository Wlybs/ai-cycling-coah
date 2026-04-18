# AI 骑行教练系统

基于 **Intervals.icu** 数据，以 **Gemini CLI** 作为交互式教练，并通过 **Gemini API** 自动生成周训练计划推送到 ICU 日历。内置深度分析（Deep Analyzer）与运动员生理档案（Physiology Profile），使教练对话具备"个体化生理上下文"。

---

## 快速开始

```bash
# 1. 首次初始化
cd /mnt/d/Cycling/icu
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 编辑 .env 填入密钥（见下方"环境变量"）

# 2. 每次使用前同步数据（推荐在骑行后立即运行）
.venv/bin/python scripts/sync_data.py

# 3. 打开教练对话
cd /mnt/d/Cycling/icu && gemini
```

### 环境变量（`.env`）

```ini
GEMINI_API_KEY=...   # Gemini API Key（仅生成训练计划时消耗额度）
API_KEY=...          # Intervals.icu → Settings → API
ATHLETE_ID=i176789
PROXY_PORT=7897      # 无代理则删除此行
```

> `.env` **不得提交 git**，`.gitignore` 已排除。

---

## 数据流

```
Intervals.icu API
       │
       ▼
scripts/sync_data.py           ← 一键同步（调用所有 sync_*）
       │
       ├─▶ icu_data_warehouse/       ← 原始数据仓库（不要手动修改）
       │
       ├─▶ scripts/build_memory.py  → coach_memory/   ← 教练直接读取
       │
       └─▶ scripts/refresh_physiology.py → 生理档案快照

可选：
  scripts/run_deep_analysis.py  → 对单次骑行做多分析器深挖
  scripts/push_plan.py          → 用 Gemini API 生成周计划并推送 ICU 日历
```

---

## 日常工作流

```
骑完车后：
  sync_data.py  →  gemini
  （教练自动读取 coach_memory/ 与生理档案并点评本次骑行）

每周一次：
  sync_data.py  →  push_plan.py --push
  （下周计划直接进入 ICU 日历，可选 --delete-existing 覆盖）

深度复盘（关键骑行后）：
  scripts/run_deep_analysis.py <activity_id>
  → 产出 intra-ride 与 context 维度的结构化分析

特殊情况（伤病 / 出差 / 比赛）：
  手动编辑 coach_memory/body_status.md 或 race_calendar.md
  手动更新 coach_memory/periodization_2026.md 的长期周期化方案

周期性维护：
  scripts/manage_memory.py --status   # 查看记忆文件状态
  scripts/manage_memory.py            # 预览清理
  scripts/manage_memory.py --apply    # 执行清理（过期 body_status、past races 等）
```

---

## 关键命令速查

```bash
# ── 数据同步 ──
.venv/bin/python scripts/sync_data.py                         # 全量一键同步
.venv/bin/python scripts/sync_profile.py                      # 运动员档案
.venv/bin/python scripts/sync_wellness.py                     # HRV/RHR/CTL/ATL/TSB
.venv/bin/python scripts/sync_power_curves.py                 # 功率曲线（90天+全生涯）
.venv/bin/python scripts/sync_activities_list.py [天数]       # 活动列表
.venv/bin/python scripts/sync_activity_detail.py [数量] [天数] # 单次骑行详情
.venv/bin/python scripts/sync_sport_settings.py               # 功率/心率区间
.venv/bin/python scripts/sync_events.py                       # ICU 日历事件

# ── 记忆构建 / 维护 ──
.venv/bin/python scripts/build_memory.py                      # 提炼 coach_memory/
.venv/bin/python scripts/refresh_physiology.py                # 刷新生理档案
.venv/bin/python scripts/update_coach_brief.py                # 更新 GEMINI.md 中的 Coach Brief
.venv/bin/python scripts/manage_memory.py [--apply|--status]  # 清理过期条目

# ── 训练计划 ──
.venv/bin/python scripts/push_plan.py                         # 生成下周计划（仅本地 reports/）
.venv/bin/python scripts/push_plan.py --push                  # 推送到 ICU 日历
.venv/bin/python scripts/push_plan.py --push --delete-existing# 覆盖推送
.venv/bin/python scripts/push_plan.py --week 2026-03-16       # 指定周（任意该周日期）

# ── 分析 / 审计 ──
.venv/bin/python scripts/analyze_rides.py                     # 批量骑行分析 CLI
.venv/bin/python scripts/analyze_gpx.py <gpx>                 # 分析 GPX 赛道
.venv/bin/python scripts/extract_ride_summary.py <ride_id>    # 提取单次骑行结构化摘要
.venv/bin/python scripts/run_deep_analysis.py <ride_id>       # 深度分析（多分析器）
.venv/bin/python scripts/physiology_audit.py                  # 生理档案审计
```

---

## 文件地图

### 顶层

| 文件 | 用途 |
|------|------|
| `GEMINI.md` | Gemini **CLI** 系统提示词：教练身份、启动协议、Coach Brief（由 `update_coach_brief.py` 自动刷新） |
| `requirements.txt` | Python 依赖列表 |
| `.env` | API 密钥（**禁止提交**） |
| `.gitignore` | 排除 `.env`、`.venv`、`__pycache__`、`reports/` 等 |

---

### scripts/ — 可执行脚本

**同步类**（随 `sync_data.py` 一并执行）：

| 脚本 | 用途 |
|------|------|
| `sync_data.py` | **主同步脚本**：依次执行所有 `sync_*` 并触发 `build_memory` / `refresh_physiology` |
| `sync_profile.py` | 运动员基本档案（FTP、体重） |
| `sync_wellness.py` | 每日健康数据（HRV、RHR、睡眠、CTL/ATL/TSB） |
| `sync_power_curves.py` | 功率曲线（90天最佳 + 全生涯最佳） |
| `sync_activities_list.py` | 活动列表（含 TSS、NP 摘要） |
| `sync_activity_detail.py` | 单次骑行完整数据（FIT 计圈、streams、ICU 间歇段、功率/心率直方图） |
| `sync_sport_settings.py` | 功率/心率区间配置 |
| `sync_events.py` | ICU 日历事件（含已计划比赛） |

**教练类**：

| 脚本 | 用途 | 频率 |
|------|------|------|
| `build_memory.py` | 从 `icu_data_warehouse/` 提炼 `coach_memory/` JSON | 随 sync_data |
| `refresh_physiology.py` | 生成运动员生理档案快照 | 随 sync_data |
| `update_coach_brief.py` | 把 Phase 1 生理摘要注入 `GEMINI.md` 的 Coach Brief 段 | 随 sync_data |
| `push_plan.py` | 调用 Gemini API 生成结构化周计划，可选推送 ICU 日历 | 每周一次 |
| `manage_memory.py` | 清理 `coach_memory/` 中过期条目（past races、resolved issues、log 摘要） | 按需 |

**分析类**（按需运行）：

| 脚本 | 用途 |
|------|------|
| `extract_ride_summary.py` | 提取单次骑行的结构化摘要（header / metrics / zones / laps / intervals / form） |
| `analyze_rides.py` | 批量骑行分析 CLI（支持多 ride_id） |
| `run_deep_analysis.py` | 对单次骑行运行 Deep Analyzer（intra + context 多分析器） |
| `analyze_gpx.py` | 赛道 GPX 地形分析（爬升段、坡度分布） |
| `physiology_audit.py` | 生理档案审计 CLI |

---

### coach_memory/ — 教练记忆

Gemini CLI 启动时自动读取这个目录的所有文件。

**自动生成**（每次 `sync_data.py` 覆盖，不要手动编辑）：

| 文件 | 内容 |
|------|------|
| `athlete_snapshot.json` | 当前 FTP、eFTP、LTHR、W'、体重 |
| `fitness_trend.json` | 近 90 天 CTL/ATL/TSB 逐日趋势 |
| `training_history.json` | 近 12 周训练摘要 + 最近 30 次骑行列表 |
| `training_analysis.json` | 强度分布、有氧效率 EF、功率曲线对比 |

**手动维护**（由运动员或教练编辑，不会被自动覆盖）：

| 文件 | 内容 | 清理规则 |
|------|------|---------|
| `body_status.md` | 伤病、疲劳、身体状况记录 | `[resolved]` 且 > 30 天自动删除 |
| `race_calendar.md` | 即将到来的比赛、优先级、目标 | 比赛日过去 > 7 天自动移出 |
| `periodization_2026.md` | 年度周期化方案（宏观训练阶段） | 手动更新 |
| `nutrition_strategy.md` | 训练日与比赛日补给方案 | 手动更新 |
| `workout_library.md` | 常用课表模板（间歇、LSD、甜点段） | 手动更新 |
| `pb_reference.md` | 功率 / 爬升 / TTE 等关键 PB 参考 | 手动更新 |
| `coach_log.md` | 教练持续观察日志 | 超 80 条时最旧 30 条自动汇总 |

---

### icu_data_warehouse/ — 原始数据仓库

由 `sync_*` 脚本写入，**禁止手动修改**。

| 目录 | 内容 | 主要读取方 |
|------|------|-----------|
| `1_Profile/` | 运动员档案 JSON | `memory_builder.py` |
| `2_Wellness/` | 每日健康数据（HRV、RHR、睡眠、CTL/ATL/TSB） | `memory_builder.py` |
| `3_PowerData/` | 功率曲线（90天 + 全生涯最佳） | `trend_analyzer.py` |
| `4_Activities_List/` | 活动列表（含 TSS、NP 摘要） | `memory_builder.py` |
| `5_Activities_Detail/` | 每次骑行完整数据（FIT 计圈 + streams + ICU 间歇段 + 直方图） | Gemini CLI 点评骑行时直读；`extract_ride_summary.py` |
| `6_SportSettings/` | 功率/心率区间配置 | `memory_builder.py`、`trend_analyzer.py` |
| `8_Events/` | ICU 日历事件（含 A/B/C 级比赛） | `plan_generator.py` |

---

### src/ — 核心逻辑

| 模块 | 文件 | 用途 |
|------|------|------|
| `fetcher/` | `icu_client.py` | Intervals.icu API 封装（所有 HTTP 请求、代理、重试） |
| `coach/` | `memory_builder.py` | 从 warehouse 提炼数据写入 `coach_memory/` |
| `coach/` | `plan_generator.py` | 调用 Gemini API 生成结构化周计划、推送 ICU |
| `coach/` | `plan_evaluator.py` | 计划评估（难度、区间分布、恢复合理性） |
| `coach/` | `brief_updater.py` | 自动更新 `GEMINI.md` 中的 Coach Brief 段落 |
| `coach/` | `phase1_injection.py` | 把 Phase 1 生理上下文注入 `plan_generator` prompt |
| `analyzer/` | `analyzer.py` | 单次骑行分析工具函数 |
| `analyzer/` | `trend_analyzer.py` | 强度分布、EF 趋势、功率曲线对比 |
| `utils/` | `common.py` | 路径、JSON 读写等公用函数 |
| `utils/` | `fit_parser.py` | 解析二进制 `.fit` 文件提取计圈数据 |

---

### prompts/ — AI 提示词

| 文件 | 用途 |
|------|------|
| `prompt_coach.md` | `push_plan.py` 调用 Gemini API 时使用的教练 system prompt（中文、详细） |

> `GEMINI.md`（顶层）是 Gemini **CLI** 的 system prompt；`prompt_coach.md` 是 Gemini **API** 调用时的 system prompt。两者独立、互不覆盖。

---

### reports/ — 生成的计划文件

| 文件 | 内容 |
|------|------|
| `plan_YYYYMMDD.md` | 可读版周训练计划（表格 + 每日详细说明） |
| `plan_YYYYMMDD.json` | 结构化计划数据（推送 ICU 使用的格式） |

---

### tests/ — 测试

| 目录 | 内容 |
|------|------|
| `tests/e2e/` | 端到端测试（数据流、计划生成） |
| `tests/fixtures/` | 测试固件数据 |
| `tests/test_trend_analyzer.py` | 趋势分析器单元测试 |

---

## 故障排查

| 症状 | 可能原因 | 处理 |
|------|---------|------|
| `sync_data.py` 报 401 | `API_KEY` 或 `ATHLETE_ID` 错误 | 在 ICU → Settings → API 重新生成并写入 `.env` |
| `push_plan.py` 报 `GEMINI_API_KEY` 缺失 | `.env` 未配置或变量名错写 | 检查 `.env`；确认 `GEMINI_API_KEY` 拼写正确 |
| 同步极慢 / 超时 | 未开代理（国内网络） | 在 `.env` 设 `PROXY_PORT=<本地代理端口>` |
| 教练对话读不到最新数据 | 忘记跑 `build_memory.py` | 运行 `sync_data.py`（会自动触发），或单独跑 `build_memory.py` |
| 计划覆盖失败 | ICU 日历已有冲突事件 | 加 `--delete-existing` 强制覆盖 |

---

## bd Issue Tracking

```bash
bd ready                 # 查看可做的任务
bd show <id>             # 查看详情
bd update <id> --claim   # 认领
bd close <id>            # 标记完成
bd sync                  # 同步到 git
```

更多 bd 工作流见仓库根目录 `AGENTS.md`。
