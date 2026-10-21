# CLAUDE.md

@vault/INDEX.md
@vault/athlete-quick-facts.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The relative imports above work in every worktree and on both Windows and WSL. `@vault/athlete-quick-facts.md` holds facts the athlete has already answered (equipment, fuels, schedule, coaching preferences) - never re-ask them. `@vault/INDEX.md` auto-loads the cycling coach's persistent narrative memory (decisions, races, KOM targets, recent sessions). Deeper vault notes are read on-demand by the `cycling-coach` skill.

## Project Overview

This is a cycling data analysis project built around the **Intervals.icu** API. The main codebase lives in `icu/` and handles syncing athlete data (activities, wellness, power curves), parsing FIT files, and generating training analysis reports.

The repo also uses **bd (beads)** for issue tracking — see AGENTS.md for full bd workflow details.

## Key Commands

```bash
# 创建虚拟环境（首次）
python3 -m venv icu/.venv

# 安装依赖
icu/.venv/bin/pip install -r icu/requirements.txt

# 同步所有数据（从 icu/ 目录运行）
cd icu && .venv/bin/python scripts/sync_data.py

# 单独同步各类数据
.venv/bin/python scripts/sync_profile.py
.venv/bin/python scripts/sync_wellness.py
.venv/bin/python scripts/sync_power_curves.py
.venv/bin/python scripts/sync_activities_list.py [天数]
.venv/bin/python scripts/sync_activity_detail.py [数量] [天数]

# 训练计划生成（Gemini API，消耗额度）
.venv/bin/python scripts/push_plan.py               # 生成下周计划（仅本地）
.venv/bin/python scripts/push_plan.py --push        # 生成并推送到 ICU 日历
.venv/bin/python scripts/push_plan.py --push --delete-existing  # 覆盖推送
.venv/bin/python scripts/push_plan.py --week 2026-03-16  # 指定周

# 构建/刷新 Coach 记忆（同步数据后运行）
.venv/bin/python scripts/build_memory.py

# Coach 记忆管理（清理过期条目）
.venv/bin/python scripts/manage_memory.py           # 预览清理内容
.venv/bin/python scripts/manage_memory.py --apply   # 执行清理
.venv/bin/python scripts/manage_memory.py --status  # 查看记忆文件状态

# Issue tracking
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Architecture

### Data Flow
`Intervals.icu API` → `icu/src/fetcher/icu_client.py` → `icu/scripts/sync_*.py` → `icu/icu_data_warehouse/`

- **`icu/src/fetcher/icu_client.py`** — Central API client. Uses `.env` for credentials (`API_KEY`, `ATHLETE_ID`, optional `PROXY_PORT`).
- **`icu/scripts/sync_data.py`** — Orchestrator that runs all sync scripts in sequence.
- **`icu/icu_data_warehouse/`** — Structured local data store:
  - `1_Profile/` — 运动员档案
  - `2_Wellness/` — 健康数据（含 CTL/ATL/TSB/HRV）
  - `3_PowerData/` — 功率曲线（90天 + 全生涯）
  - `4_Activities_List/` — 活动列表
  - `5_Activities_Detail/` — 活动详情（FIT计圈 + Streams + ICU间歇段 + 功率/心率直方图）
  - `6_SportSettings/` — 功率/心率区间设置
  - `7_Gear/` — 装备数据
  - `8_Events/` — 日历事件（计划训练）
- **`icu/src/analyzer/`** — Power data and ride analysis.
- **`icu/src/coach/`** — Automated coaching insights from training data.
- **`icu/src/utils/fit_parser.py`** — Binary .fit file parser.
- **`icu/prompts/`** — AI prompt templates for analysis/coaching features.

### Environment

The `.env` file in `icu/` contains API credentials — never commit or expose it. The API client supports an optional HTTP proxy via `PROXY_PORT`.

## Coaching & Data Analysis

When the user asks any coaching / training / FTP / CP / W' / race-prep / recovery / ride-evaluation question:

1. **Invoke the `cycling-coach` skill via the Skill tool BEFORE answering.** Do not draft any coaching reply without it.
2. **Sync fresh data first.** Run `cd icu && .venv/bin/python scripts/sync_data.py` before analysis. Never reach for cached or hardcoded values like `FTP=288W`.
3. **Quote the data points.** Every coaching response must include an evidence block listing the exact numbers being used, with source file + timestamp:
   ```
   [evidence: ftp_set=300W from athlete_snapshot.json updated 2026-05-04]
   [evidence: cp5_pb=387W from snapshot.recent_pbs.5min (90d rolling window)]
   ```
4. **Confirm rolling-window PB anchors.** ICU's `recent_pbs.Nmin` is a rolling-window peak, not a true all-out effort at that duration. Before any CP/FTP calculation, confirm with the user that the snapshot value matches an actual best effort.
5. **Anti-sycophancy.** When the user pushes back, re-examine the data BEFORE changing your answer. If the data supports your original position, hold it with a fresh evidence citation. Agreeable capitulation is a bug, not a feature.
6. **No hardcoded athlete numbers.** All FTP / weight / Pmax / CP must read from `coach_memory/athlete_snapshot.json` or live data. See memory entry `feedback_no_hardcoded_athlete_data.md`.
7. **Conversational format.** 2–3 paragraphs max for normal questions. No data dumps unless the user explicitly asks for a table.

## Context & Long Tasks

For plans, specs, or analysis documents:

1. **Shard upfront.** Any document expected to exceed 1500 lines must be split into 500–800 line numbered shards (`01_overview.md`, `02_<topic>.md`, …) with an `index.md` BEFORE writing content. Don't wait for `Prompt is too long` to force the split.
2. **Subagent dispatch is the default for multi-task phases.** When implementing multi-task specs (T-IDs, file shards), dispatch each task to a subagent via the Agent tool with two-stage review (correctness + spec-compliance) before commit. Sessions that tried monolithic main-thread execution have repeatedly hit context-overflow failures.
3. **Spec audit before coding.** Before any subagent starts implementation, run a spec-audit subagent that reads all shards and reports internal contradictions, ambiguous open questions, and cross-file dependency conflicts. Do not begin coding until cleared.
4. **Checkpoint long autonomous runs.** Before starting any overnight / autonomous session, dump current state to memory and prepare a resume prompt. If main-thread context exceeds 70%, finalize the current task and exit with a resume command — do not push to failure.
5. **Use `ctx_execute` / `ctx_execute_file` for analysis, never `Read` for large data files.** Write/Edit are correct for files you intend to modify; for analysis use the sandboxed tools so raw output stays out of the main context.

## Conventions

- Primary language is Python. Comments and UI strings are in Chinese (中文).
- Use `--json` flag when calling bd programmatically.
- Use non-interactive flags (`-f`) for shell file operations (cp, mv, rm) to avoid hanging — see AGENTS.md.
- Always push to remote before ending a session — see AGENTS.md "Landing the Plane" section.
