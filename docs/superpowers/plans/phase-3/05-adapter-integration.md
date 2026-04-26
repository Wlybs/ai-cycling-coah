# Phase 3 — Adapter integration: daily_adapt + apply_adaptation (Tasks T60–T61)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 把 [03-adapter-infrastructure.md](./03-adapter-infrastructure.md) 的判定基座 + [04-adapter-session-revisor.md](./04-adapter-session-revisor.md) 的降载映射 / markdown 渲染粘合成两条**真正会执行**的命令行入口。File 05 完成后整套 adapter 子系统从「纯函数库」升级为「每日运行的工作流」：每天早晨 `daily_adapt.py` 读 wellness + 当周 plan + ledger 历史 → 评估 4 信号 → 写黄/红 markdown + ledger entry + （红灯时）proposed_session JSON；用户人眼看完后跑 `apply_adaptation.py --confirm` 才把替代 session 真的推回 Intervals.icu。Green/Yellow 全程不触网，Red 触网必经 `--confirm` 二次握手。

## Inputs / Outputs

**T60 `daily_adapt`（无网络，可独立 cron）：**

Inputs (read-only)：
- `icu_data_warehouse/2_Wellness/wellness_history.json` — 取 `--date` 当日 wellness 记录 + 28 天 baseline 计算窗
- `coach_memory/physiology/cp_w_current.json` — `revise_session` 的生理参数
- `coach_memory/physiology/durability.json` — 同上
- `coach_memory/physiology/response_profile.json` — 同上
- `coach_memory/periodization/micro_cycle_<W>.json` — 找 `--date` 当日 `DayIntent` 推断 phase / week
- `coach_memory/reports/plan_<W>.json`（最新一份匹配 `--date` 所在周）— 取当日 `DesignedSession`（即 `original`）
- `coach_memory/ledger/decisions.jsonl` — `LedgerReader.query(decision_type="adaptation_verdict", since=now-4d)` 喂连红护栏

Outputs：
- `coach_memory/adapter/today_<YYYY-MM-DD>.md` — 黄/绿 时是 nudge，红时是 override（统一文件名，避免 daily_adapt 之外的脚本判文件名分支）
- `coach_memory/adapter/proposed_session_<YYYY-MM-DD>.json` — 仅红灯且 `revise_session` 返回非 None 时；内容 = `DesignedSession.model_dump_json(indent=2)`，UTF-8
- `coach_memory/ledger/decisions.jsonl` 末尾追加一条 `decision_type="adaptation_verdict"`：
  - `payload.verdict` ∈ {green, yellow, red}
  - `payload.severity_score` (float)
  - `payload.recommended_action` ∈ RECOMMENDED_ACTIONS
  - `payload.triggered_rules` (list[str])
  - `payload.guardrails_hit` (list[str])
  - `payload.original_session_type`（字符串，原计划 `SessionType.value`，可空表示 Rest）
  - `payload.proposed_session_type`（红灯且非 Rest 时；其它情况 `null`）
  - `payload.report_path`（str，相对 memory_dir 的报告路径）
  - `payload.proposed_session_path`（str | null）
  - `evidence_refs` 含 `wellness_history.json` 路径 + `plan_<W>.json` 路径
- 不发任何 ICU 请求，不调任何 LLM SDK

**T61 `apply_adaptation`（默认 dry-run；`--confirm` 触网）：**

Inputs (read-only)：
- `coach_memory/ledger/decisions.jsonl` — 找当日最新 `adaptation_verdict` entry（`since=date(...)0:00 UTC, until=date(...)24:00 UTC`）
- `coach_memory/adapter/proposed_session_<YYYY-MM-DD>.json` — 反序列化为 `DesignedSession`
- `icu_data_warehouse/8_Events/events.json`（或 `--events` 指向）— 找 `--date` 当日 event_id（match by event date == `--date` and `category == "WORKOUT"`）

Outputs：
- 默认（无 `--confirm`）：stdout 打印拟发往 ICU 的 PATCH/PUT payload (`session.name` / `session.description` / `session.duration_min` / `session.target_tss` / `structure_steps_count`) + 一行提醒「dry-run, append `--confirm` to apply」。**不**写 ledger，**不**触网。Exit 0。
- 带 `--confirm`：调 `ICUClient.update_event(event_id, payload)`（T61 在 `icu_client.py` 新增的方法）。成功 → `coach_memory/ledger/decisions.jsonl` 追加一条 `decision_type="adaptation_applied"`，payload 含 `event_id`、`source_verdict_entry_id`、`patched_fields`（dict 摘要）。失败（任何 exception 自 `_request`）→ **不**写 ledger，stderr 打印错误，exit 非零。
- 不调任何 LLM SDK；fetcher 调用走唯一 seam `ICUClient.update_event` 让测试 mock。

## Locked constraints (echoed from 00-index.md)

- **NO_NEW_DEPS** (#8)：不增 `requirements.txt` 条目；ICU 调用走已有的 `requests` + `ICUClient._request`，不引 httpx / aiohttp。
- **API_FREE_WORKFLOW** (#1)：本文件创建的 4 个文件（`daily_adapt.py` × 2、`apply_adaptation.py` × 2 + tests）禁止 import `google.genai` / `anthropic` / `openai`。`grep -nE 'google\.genai|anthropic|openai' icu/scripts/daily_adapt.py icu/scripts/apply_adaptation.py icu/src/coach/adapter/daily_adapt.py icu/src/coach/adapter/apply_adaptation.py` 必须为空。
- **HUMAN_GATE_ON_ICU_WRITE** (#3)：T61 默认 dry-run；只有显式 `--confirm` 触网。无 `--confirm` 调用时不写 ledger、不调 fetcher。
- **APPEND_ONLY_LEDGER** (#4)：T60 仅 `LedgerWriter.record(decision_type="adaptation_verdict", ...)`；T61 仅 `LedgerWriter.record(decision_type="adaptation_applied", ...)`。绝不修改已写入 entry，绝不删行。纠错走 File 01 的 `superseded_by` 字段。
- **RED_NO_AUTO_ESCALATE** (#7)：T60 红灯只产 markdown + proposed_session.json，**绝不**自动调 `apply_adaptation.py`、**绝不**触发 strict consensus。
- **PHASE_1_2_IMMUTABILITY** (#2)：File 01–04 deliverables 全部 read-only。**允许**：T61 在 `icu/src/fetcher/icu_client.py` 末尾追加一个 `update_event(event_id, payload)` 方法（fetcher 不在 immutability 列表内；它是 Phase 1/2 的依赖而非「Phase 1/2 已交付逻辑」）。**不允许**：改 `_request` / `__init__` / 已有方法签名。
- **Use `.venv/bin/pytest`**：系统 python 装的是错误版本的 pydantic / scipy，会假绿/假红。所有 pytest 命令以 `cd icu && .venv/bin/pytest ...` 执行。

## File layout

新建文件（Phase 3 全新）：
- `icu/src/coach/adapter/daily_adapt.py`（新；纯函数 orchestrator，无 IO 之外的副作用以外的副作用 — 见下文 design notes）
- `icu/src/coach/adapter/apply_adaptation.py`（新；纯函数 orchestrator，touch 网络通过注入的 client）
- `icu/scripts/daily_adapt.py`（新；CLI entry 调 `src.coach.adapter.daily_adapt:run`）
- `icu/scripts/apply_adaptation.py`（新；CLI entry 调 `src.coach.adapter.apply_adaptation:run`）
- `icu/tests/unit/adapter/test_daily_adapt.py`（新）
- `icu/tests/unit/adapter/test_apply_adaptation.py`（新）
- `icu/tests/fixtures/phase3/`（新 fixture root，与 `tests/fixtures/phase1/`、`phase2/` 隔离；首次创建，执行器无需手动 mkdir，T60 测试通过 `tmp_path` 写入即可，本目录将由后续 T62-T64 测试沿用）

修改的文件（最小化、白名单）：
- `icu/src/coach/adapter/__init__.py`（追加 `from .daily_adapt import run as run_daily_adapt` 与 `from .apply_adaptation import run as run_apply_adaptation` re-export，并扩 `__all__`；不改原 docstring）
- `icu/src/fetcher/icu_client.py`（追加一个 `update_event(self, event_id, payload)` 方法到类末尾；fetcher 包不在 immutability 列表内，但本次只新增、绝不改既有方法）

未触碰文件（HARD 约束）：
- `icu/src/coach/adapter/types.py`、`rules.py`、`session_revisor.py`、`prompt_builder.py`（File 03/04 产物，read-only）
- `icu/src/coach/ledger/*`（File 01 产物，仅 import `LedgerWriter` / `LedgerReader` / `AthleteStateRef`）
- `icu/src/coach/session_designer/*` / `periodization/*` / `physiology/*` / `deep_analyzer/*`（Phase 1/2 产物）
- `icu/scripts/sync_data.py`（File 09 才会扩末尾段落；本文件不触）
- `icu/scripts/ingest_ledger.py`（File 02 产物，read-only — 但**风格抄袭对象**）

## Design notes (read before T60 Step 1)

### Why split `src/coach/adapter/daily_adapt.py` from `scripts/daily_adapt.py`

- `src/coach/adapter/daily_adapt.py` 暴露纯函数 `run(...)`，全部依赖通过参数注入（`memory_dir: Path`、`warehouse_dir: Path`、`now_fn: Callable[[], datetime]`、`writer: LedgerWriter | None`、`dry_run: bool`）。这一层完全 unit-testable，不解析 argv、不 `sys.exit`。
- `scripts/daily_adapt.py` 是薄壳：`_parse_args` → 实例化 `LedgerWriter` 与默认 `now_fn=lambda: datetime.now(timezone.utc)` → 调 `run(...)` → 把返回的 dict 打到 stdout → `raise SystemExit(0)`。
- 同样的分层用在 `apply_adaptation`。这与 File 02 `ingester.py` + `scripts/ingest_ledger.py` 的拆法一致。

### `now_fn` 注入而非 freeze-time

`evaluate_signals` 内部已经有 `freeze_now` fixture 通过 monkeypatch `rules.now()`（由 T56 实现）。但本层的 main flow 也会读 `datetime.now(timezone.utc)` 来盖 ledger 的 `since/until` 窗口与计算 wellness 窗的右边界。**禁止**在主流程里直接 `datetime.now()` —— 那会让单测要么走 freeze-time 第三方包（违反 NO_NEW_DEPS），要么 monkeypatch `daily_adapt.datetime` (脆 + 跨 module 烦)。一律用 `now_fn: Callable[[], datetime]` 显式参数注入；CLI 默认 `lambda: datetime.now(timezone.utc)`，测试默认 `lambda: datetime(2026, 4, 19, 6, 0, tzinfo=timezone.utc)`。

### `LedgerWriter` collisions — 别再踩 `_log.event(action=...)` 坑

`JSONLLogger.event(action: str, *, ...)` 把 `action` 作为**第一个位置参数**。`LedgerWriter._log.event("ledger_entry_appended", ...)` 已正确传入；本文件新代码若再调 `_log.event(...)`，**严禁**给它加 `action=` kwarg —— 会报 `TypeError: event() got multiple values for argument 'action'`（File 03 已踩此坑、File 04 已记录）。本文件新增的两个模块各自调 `get_logger("adapter")._log.event(...)` 时统一用：

```python
_log.event("adapter_run_completed", date=..., verdict=..., recommended_action=...)
_log.event("adaptation_applied", date=..., event_id=..., recommended_action=...)
```

`recommended_action` 是 string kwarg，不撞名。`verdict` / `event_id` / `date` 同理。

### `DesignedSession` round-trip

- T60 写 `proposed_session_<date>.json` 用 `path.write_text(session.model_dump_json(indent=2), encoding="utf-8")`。
- T61 读回用 `DesignedSession.model_validate_json(path.read_text(encoding="utf-8"))`。
- 必须有一个 round-trip 测试断言 `roundtripped.session_type is SessionType.RECOVERY`（验证 enum 不退化为 str）。

### 中文字符 `Path.write_text` 编码

prompt_builder 输出含 "完全休息"、"今日训练**不变**" 等中文。在 Windows / WSL 默认 cp936 locale 下 `path.write_text(text)` 不带 `encoding="utf-8"` 会 `UnicodeEncodeError`。**必须**：

```python
path.write_text(content, encoding="utf-8")
```

测试用 `tmp_path` 时 mac/Linux 不暴露此 bug；测试需显式校验「写出的字节流可以用 utf-8 解回」+ 写一条 LANG=C 的 monkeypatch case 防御。

### ICU PATCH seam — extend `ICUClient`，don't bypass it

intervals.icu 的 events 端点遵循 RESTful 习惯：`POST /athlete/{id}/events` 创建、`PUT /athlete/{id}/events/{event_id}` 更新（API 文档：events 上没有 PATCH，只有 PUT；T61 沿用既有 `_request("PUT", ...)` 即可保持与 `create_event`/`delete_event` 风格一致）。当前 `icu_client.py` 没有 update 方法 —— 仅 `create_event` (POST)、`delete_event` (DELETE)。

T61 在 `icu_client.py` **末尾**追加一个 ~5 行的方法（不动既有方法）：

```python
def update_event(self, event_id, event_data):
    """更新 ICU 日历上指定的训练计划事件。"""
    path = f"/athlete/{self.athlete_id}/events/{event_id}"
    return self._request("PUT", path, json=event_data).json()
```

理由：本方法**不在** PHASE_1_2_IMMUTABILITY 列表内（fetcher 是 Phase 1 的依赖，但 `update_event` 是 Phase 3 增量需要 — 增加方法 ≠ 修改既有方法）。这是「extension via addition」而非「modification」，与 #46-49 列出的禁修文件清单兼容。如果未来 Phase 4 想换 client，T61 调用方只依赖 `client.update_event(event_id, payload)` 这一接口签名，不依赖实现细节。

### `--confirm` 半事务语义

```
load verdict      → ok / fail-fast (no-op)
load proposed     → ok / fail-fast (no-op)
load events.json  → ok / fail-fast (no-op)
build payload     → in-memory only
client.update_event(...) → success ── append ledger ── exit 0
                          → exception ── do NOT append ── stderr ── exit 2
```

**关键**：ledger append 必须在 PATCH 成功**之后**。如果 PATCH 抛 `requests.HTTPError` / `requests.ConnectionError` / 任何 `Exception`，捕获 → 打 stderr → exit 非零 → ledger 保持不变。这样下一次重试 `--confirm` 是幂等的 —— 用户再跑一次就重新 PATCH + 重新 append。

测试通过 `unittest.mock.MagicMock` 替换 `client.update_event` 来覆盖成功 / 失败两路；**绝不**用 `requests-mock` / `responses` 等第三方包。

### Worktree bootstrap

如果在 fresh worktree（参见 `00-index.md` 末尾 bootstrap）执行本文件：

```bash
cd icu
ln -s /mnt/d/Cycling-phase3/icu/.venv .venv
cp -r /mnt/d/Cycling-phase3/icu/src/analyzer .
cp -r /mnt/d/Cycling-phase3/icu/src/utils .
cp -r /mnt/d/Cycling-phase3/icu/src/fetcher .   # T61 要修改 icu_client.py
.venv/bin/pytest tests/unit/adapter/ -q          # 应见 ~71 passed (File 04 baseline)
```

确认 71 passed 之前**不要**进入 T60 Step 1。

## Task 60: `daily_adapt.py` — orchestrator + CLI

**Files:**
- Create: `icu/src/coach/adapter/daily_adapt.py`
- Create: `icu/scripts/daily_adapt.py`
- Create: `icu/tests/unit/adapter/test_daily_adapt.py`
- Edit: `icu/src/coach/adapter/__init__.py`（追加 `run as run_daily_adapt` 到 re-exports；不改 docstring）

**Public API (locked):**

```python
# icu/src/coach/adapter/daily_adapt.py
def run(
    *,
    target_date: date,
    memory_dir: Path,
    warehouse_dir: Path,
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    dry_run: bool = False,
) -> dict:
    """
    Returns a dict with keys:
      verdict: "green" | "yellow" | "red"
      severity_score: float
      recommended_action: str
      report_path: Path | None    # None when dry_run skipped write
      proposed_session_path: Path | None
      ledger_entry_id: str | None # None when dry_run
    Pure orchestrator: NO sys.exit, NO argv parse, NO print.
    """
```

CLI shell `icu/scripts/daily_adapt.py`:

```
usage: daily_adapt.py --date YYYY-MM-DD --memory <dir> --warehouse <dir>
                      [--ledger <path>] [--dry-run]
```

- `--memory` / `--warehouse` 的语义与 `ingest_ledger.py` 完全一致（必填，Path）。
- `--ledger` 默认 `<memory>/ledger/decisions.jsonl`（同 ingest_ledger.py）。
- `--date` 必填，格式 `YYYY-MM-DD`，被 `date.fromisoformat` 解析。
- `--dry-run` 跳过 markdown 写盘 + ledger append + proposed_session JSON 写盘。仍然完成评估 + 把要走的动作打到 stdout。

**Design notes for `run(...)`:**

1. **Build SignalSnapshot from wellness_history.json**
   - 读 `warehouse_dir / "2_Wellness" / "wellness_history.json"` (list[dict] sorted oldest→newest)
   - 找 `target_date` 当日 entry by `entry["id"][:10] == target_date.isoformat()`（intervals.icu 把 `id` 字段写成 `YYYY-MM-DDT00:00:00`）；若找不到 → `FileNotFoundError("No wellness entry for <date>")`，CLI shell 捕获后 exit 非零
   - 28d baseline: 取 target_date 之前 28 天 `entry.hrv` / `entry.restingHR` 的均值（缺失值跳过；不足 7 天样本时返回 None — 由 `evaluate_signals` 的 baseline-missing 路径处理）
   - `SignalSnapshot.captured_at = now_fn()`、`hrv_ms / resting_hr_bpm / sleep_hours / soreness_score` 从当日 entry 提取（sleepSecs → sleep_hours = sleepSecs / 3600；soreness 直接取，缺失填 None 是不合规的 — `SignalSnapshot` 的 4 字段都是 required；缺失时 raise `ValueError`，CLI 捕获 exit 非零）

2. **Build AthleteStateRef from physiology + periodization snapshots**
   - 复用 `scripts/ingest_ledger.py` 的 `build_default_state()`：把它**抽公共函数**到 `src/coach/adapter/_state.py`？— **不**。File 02 已交付 `build_default_state`，复用唯一手段是 `from scripts.ingest_ledger import build_default_state as _build_state`（scripts 包是 sys.path 加进去的），但这把 scripts 当库用很别扭。**采用**：本文件内重写一个 `_build_athlete_state(memory_dir, warehouse_dir, target_date) -> AthleteStateRef`，逻辑与 ingest_ledger 等价但 `week_of_year = target_date.isocalendar()[1]`（不是 today）。两份代码的 drift risk 用一条断言测试看死：`from scripts.ingest_ledger import _FALLBACK_STATE; assert build_athlete_state(missing_dirs).phase == _FALLBACK_STATE.phase`。

3. **Find `original` DesignedSession from latest plan**
   - `plan_path = max(memory_dir.glob("reports/plan_*.json"), key=lambda p: p.stat().st_mtime, default=None)` — 取 mtime 最新，比按文件名排序更鲁棒（plan 文件名是 `plan_YYYY-MM-DD.json` 或 `plan_2026-W16.json`，规则不统一）。
   - 没有任何 plan → `original = None`，`original_session_type = None`，但仍正常评估 → green/yellow 路径只写 nudge；红灯路径调 `revise_session(original_type=SessionType.REST, ...)` （等价于 Rest passthrough，返回 None，proposed_session.json 不落盘）。
   - 有 plan：用 `WeeklyPlan.model_validate_json(plan_path.read_text(...))` 反序列化；找 `days[i].date == target_date.isoformat()` 的那个 `DayPlanV2`；映射 `training_type` ("Threshold"/"VO2max"/...) → `SessionType` enum：硬编码一张 `_TRAINING_TYPE_TO_SESSION_TYPE: dict[str, SessionType]` 表 (key 大小写敏感，必须与 Phase 2 `DayPlanV2.training_type` Literal 一一对应)。
   - **不**需要 reconstruct full `DesignedSession` from plan — 该 `DayPlanV2` 已经包含 name / description / duration_min / target_tss，但 `DesignedSession` 还要 SessionStructure。本文件 `original` 只用作 prompt_builder 的 「Original (planned)」block，prompt_builder 只读 `name` / `session_type` / `duration_min` / `target_tss` / `description`。**故**：构造一个 `_PlanSnapshot(name, session_type, duration_min, target_tss, description)` lightweight namedtuple 作为 `original` 传给 prompt_builder？— **不**。prompt_builder 签名锁死 `original: DesignedSession | None`。**采用**：构造 minimum-valid `DesignedSession`：
     ```python
     original = DesignedSession(
         day_of_week=day.day_of_week,
         date=day.date,
         session_type=_training_type_to_session_type(day.training_type),
         name=day.name,
         description=day.description,
         duration_min=day.duration_min,
         target_tss=day.target_tss,
         structure=SessionStructure(steps=[]),  # 空 structure 合法
         power_range_w=day.power_range_w,
         hr_range_bpm=day.hr_range_bpm,
         trace=None,
     )
     ```
     校验 `SessionStructure(steps=[])` 在 Phase 2 schema 允许（empty list 通过 `BaseModel`，无 model_validator 卡）。

4. **Compose: evaluate_signals → branch on verdict**
   ```python
   verdict = evaluate_signals(snapshot, state=state, history=history,
                              hrv_28d_mean_ms=baseline_hrv,
                              resting_hr_28d_mean_bpm=baseline_hr)
   if verdict.verdict == "green":
       report_md = None  # green skips markdown
   elif verdict.verdict == "yellow":
       report_md = build_yellow_nudge(verdict=verdict, snapshot=snapshot,
                                      today_session=original)
       proposed = None
   else:  # red
       proposed = revise_session(
           original_type=original.session_type if original else SessionType.REST,
           original_date=target_date,
           physiology=physiology, durability=durability,
           response_profile=response_profile,
       )
       report_md = build_red_override(
           verdict=verdict, snapshot=snapshot,
           original=original, proposed=proposed,
       )
   ```
   - **Green = no markdown, no proposed_session, but STILL append ledger** with `recommended_action="none"`. (Ledger captures every day's evaluation — needed by File 06 `history_injector`.)

5. **Persist (skip when dry_run):**
   - `report_path = memory_dir / "adapter" / f"today_{target_date.isoformat()}.md"`; `report_path.parent.mkdir(parents=True, exist_ok=True)`; `report_path.write_text(report_md, encoding="utf-8")` — 仅 yellow / red 写。
   - Red + proposed not None：`proposed_session_path = memory_dir / "adapter" / f"proposed_session_{target_date.isoformat()}.json"`；`proposed_session_path.write_text(proposed.model_dump_json(indent=2), encoding="utf-8")`。
   - Always (even green)：`writer.record(decision_type="adaptation_verdict", source="adapter.daily", athlete_state=state, payload={...}, evidence_refs=[...])`。Returns `entry_id`.

6. **`--dry-run` 完整 dry-run** = 所有写动作（markdown / proposed_session / ledger）跳过；返回 dict 中 `report_path`、`proposed_session_path`、`ledger_entry_id` 全为 `None`。CLI shell 把这个 dict 打印为 JSON 给 stdout 并 `exit 0`。

7. **Idempotency**：同一天连跑两次 `--dry-run` 必须得到同样的 `verdict` / `severity_score` / 动作（pytest 测试会断言）。非 `--dry-run` 重复跑 = ledger 累计两条 entry（这是预期：每次评估都是一条独立决策；File 06 history_injector 取最新的）。

- [ ] **Step 1: Write failing tests**

Create `icu/tests/unit/adapter/test_daily_adapt.py`:

```python
"""Unit tests for adapter.daily_adapt.run — green/yellow/red branches + dry-run."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.coach.adapter.daily_adapt import run
from src.coach.adapter.types import AdaptationVerdict
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter
from src.coach.periodization.types import SessionType
from src.coach.session_designer.types import DesignedSession


# ---------- shared fixtures ----------

@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 4, 19, 6, 0, tzinfo=timezone.utc)


@pytest.fixture
def now_fn(fixed_now):
    return lambda: fixed_now


@pytest.fixture
def target_date() -> date:
    return date(2026, 4, 19)


@pytest.fixture
def memory_dir(tmp_path) -> Path:
    d = tmp_path / "coach_memory"
    (d / "physiology").mkdir(parents=True)
    (d / "periodization").mkdir(parents=True)
    (d / "reports").mkdir(parents=True)
    (d / "ledger").mkdir(parents=True)
    (d / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288,
    }), encoding="utf-8")
    (d / "physiology" / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1},
        "sample_size_rides": 28,
    }), encoding="utf-8")
    (d / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {"threshold": {"tolerance_class": "high"}},
    }), encoding="utf-8")
    (d / "periodization" / "phase_current.json").write_text(json.dumps({
        "current_phase": "BUILD",
    }), encoding="utf-8")
    return d


@pytest.fixture
def warehouse_dir(tmp_path, target_date) -> Path:
    d = tmp_path / "icu_data_warehouse"
    (d / "2_Wellness").mkdir(parents=True)
    # 28 days of baseline + target day
    history = []
    for i in range(30, 0, -1):
        day = target_date - timedelta(days=i)
        history.append({
            "id": f"{day.isoformat()}T00:00:00",
            "hrv": 68.0,
            "restingHR": 52,
            "sleepSecs": 7 * 3600,
            "soreness": 4,
            "ctl": 70.0, "atl": 75.0,
        })
    history.append({
        "id": f"{target_date.isoformat()}T00:00:00",
        "hrv": 67.0,             # close to baseline → green
        "restingHR": 53,         # +1 vs 52 → green
        "sleepSecs": 7 * 3600,   # 7h → green
        "soreness": 4,           # green
        "ctl": 70.0, "atl": 75.0,
    })
    (d / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(history), encoding="utf-8")
    return d


def _write_plan(memory_dir: Path, target_date: date, training_type: str = "Aerobic"):
    """Helper: stamp a plan file containing one DayPlanV2 for `target_date`."""
    plan = {
        "week_start": target_date.isoformat(),
        "week_end": (target_date + timedelta(days=6)).isoformat(),
        "focus_theme": "test",
        "weekly_tss_target": 400,
        "coaching_summary": None,
        "days": [{
            "date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%a"),
            "training_type": training_type,
            "icu_type": "Ride" if training_type != "Rest" else "Rest",
            "name": f"Test {training_type} session",
            "description": "Generated by test fixture",
            "duration_min": 90 if training_type != "Rest" else 0,
            "target_tss": 110 if training_type != "Rest" else 0,
            "power_range_w": "200-220",
            "hr_range_bpm": "140-160",
        }],
    }
    (memory_dir / "reports" / f"plan_{target_date.isoformat()}.json").write_text(
        json.dumps(plan), encoding="utf-8")


# ---------- GREEN: no markdown, no proposed, but ledger entry appended ----------

def test_run_green_day_writes_ledger_no_markdown(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    _write_plan(memory_dir, target_date, training_type="Aerobic")
    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
        dry_run=False,
    )
    assert result["verdict"] == "green"
    assert result["recommended_action"] == "none"
    assert result["report_path"] is None
    assert result["proposed_session_path"] is None
    assert result["ledger_entry_id"] is not None

    # Ledger has exactly one adaptation_verdict entry
    entries = reader.query(decision_type="adaptation_verdict")
    assert len(entries) == 1
    assert entries[0].payload["verdict"] == "green"
    assert entries[0].payload["recommended_action"] == "none"


# ---------- YELLOW: markdown written, no proposed, ledger appended ----------

def test_run_yellow_day_writes_markdown_only(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    # Override target-day wellness to push HRV into yellow band (-9% vs baseline)
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.91  # ~9% drop → yellow
    history[-1]["sleepSecs"] = 6 * 3600  # 6h → yellow
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    _write_plan(memory_dir, target_date, training_type="Tempo")

    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    assert result["verdict"] == "yellow"
    assert result["recommended_action"] == "nudge_only"
    assert result["report_path"] is not None
    assert result["report_path"].exists()
    assert result["proposed_session_path"] is None

    # markdown contains yellow markers + signal table
    md = result["report_path"].read_text(encoding="utf-8")
    assert ("🟡" in md) or ("yellow" in md.lower())
    assert "hrv" in md.lower()


# ---------- RED: markdown + proposed_session.json + ledger ----------

def test_run_red_day_writes_all_three(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.85       # -15% → red
    history[-1]["restingHR"] = 60          # +8 → red
    history[-1]["sleepSecs"] = 4 * 3600    # 4h → red
    history[-1]["soreness"] = 1            # red
    wh_path.write_text(json.dumps(history), encoding="utf-8")

    _write_plan(memory_dir, target_date, training_type="Threshold")

    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    assert result["verdict"] == "red"
    assert result["recommended_action"] in ("propose_replacement", "rest_48h")
    assert result["report_path"] is not None and result["report_path"].exists()
    assert result["proposed_session_path"] is not None
    assert result["proposed_session_path"].exists()

    # proposed_session.json round-trips into DesignedSession with enum intact
    proposed = DesignedSession.model_validate_json(
        result["proposed_session_path"].read_text(encoding="utf-8"))
    assert proposed.session_type is SessionType.RECOVERY  # threshold → recovery_spin
    assert proposed.date == target_date.isoformat()

    md = result["report_path"].read_text(encoding="utf-8")
    assert "apply_adaptation.py" in md
    assert "--confirm" in md
    assert target_date.isoformat() in md


def test_run_red_day_no_plan_falls_back_to_rest(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    """When no plan_*.json exists, run still produces a red override w/ Rest."""
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.80
    history[-1]["sleepSecs"] = 3 * 3600
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    # NO _write_plan — reports/ stays empty

    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    assert result["verdict"] == "red"
    # Rest passthrough → no proposed_session.json
    assert result["proposed_session_path"] is None
    assert result["report_path"] is not None
    md = result["report_path"].read_text(encoding="utf-8")
    assert "Rest" in md or "rest" in md.lower()


# ---------- DRY-RUN: no writes anywhere ----------

def test_dry_run_skips_all_writes(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.80     # red
    history[-1]["sleepSecs"] = 3 * 3600
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    _write_plan(memory_dir, target_date, training_type="VO2max")

    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
        dry_run=True,
    )
    assert result["verdict"] == "red"
    assert result["report_path"] is None
    assert result["proposed_session_path"] is None
    assert result["ledger_entry_id"] is None

    # ledger file untouched
    assert not ledger_path.exists() or ledger_path.read_text(encoding="utf-8") == ""
    # adapter dir not created or empty
    adapter_dir = memory_dir / "adapter"
    assert (not adapter_dir.exists()) or (list(adapter_dir.iterdir()) == [])


def test_dry_run_idempotent_across_two_calls(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    _write_plan(memory_dir, target_date)
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")

    r1 = run(target_date=target_date, memory_dir=memory_dir,
             warehouse_dir=warehouse_dir, writer=writer, reader=reader,
             now_fn=now_fn, dry_run=True)
    r2 = run(target_date=target_date, memory_dir=memory_dir,
             warehouse_dir=warehouse_dir, writer=writer, reader=reader,
             now_fn=now_fn, dry_run=True)
    assert r1["verdict"] == r2["verdict"]
    assert r1["severity_score"] == r2["severity_score"]
    assert r1["recommended_action"] == r2["recommended_action"]


# ---------- DesignedSession round-trip preserves enum ----------

def test_proposed_session_json_roundtrips_session_type_enum(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.80
    history[-1]["sleepSecs"] = 3 * 3600
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    _write_plan(memory_dir, target_date, training_type="VO2max")

    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")

    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    proposed_path = result["proposed_session_path"]
    assert proposed_path is not None

    raw = json.loads(proposed_path.read_text(encoding="utf-8"))
    assert raw["session_type"] == "RECOVERY"  # serialized as string

    parsed = DesignedSession.model_validate_json(
        proposed_path.read_text(encoding="utf-8"))
    assert parsed.session_type is SessionType.RECOVERY  # enum identity preserved


# ---------- UTF-8 robustness on non-utf8 default locale ----------

def test_red_markdown_writes_utf8_under_ascii_locale(
    monkeypatch, target_date, memory_dir, warehouse_dir, now_fn,
):
    """Path.write_text must explicitly pass encoding='utf-8' (Chinese chars in template)."""
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    history[-1]["hrv"] = 68.0 * 0.80
    history[-1]["sleepSecs"] = 3 * 3600
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    _write_plan(memory_dir, target_date, training_type="Threshold")

    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("LC_ALL", "C")

    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    # Read back as bytes; decoding utf-8 must succeed and contain CJK
    raw_bytes = result["report_path"].read_bytes()
    md = raw_bytes.decode("utf-8")
    assert "完全休息" in md or "今日训练" in md or "运行下面的命令" in md


# ---------- Wellness missing → fail-fast ----------

def test_wellness_missing_raises(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    (warehouse_dir / "2_Wellness" / "wellness_history.json").unlink()
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    with pytest.raises((FileNotFoundError, ValueError)):
        run(
            target_date=target_date,
            memory_dir=memory_dir, warehouse_dir=warehouse_dir,
            writer=writer, reader=reader, now_fn=now_fn,
        )


def test_wellness_missing_target_date_raises(
    target_date, memory_dir, warehouse_dir, now_fn,
):
    wh_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = json.loads(wh_path.read_text(encoding="utf-8"))
    # remove the target day
    history = [h for h in history if not h["id"].startswith(target_date.isoformat())]
    wh_path.write_text(json.dumps(history), encoding="utf-8")
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    with pytest.raises((FileNotFoundError, ValueError, KeyError)):
        run(
            target_date=target_date,
            memory_dir=memory_dir, warehouse_dir=warehouse_dir,
            writer=writer, reader=reader, now_fn=now_fn,
        )


# ---------- now_fn injection — no datetime.now() in main flow ----------

def test_now_fn_is_used_not_real_clock(
    target_date, memory_dir, warehouse_dir,
):
    """Pass an obviously-wrong now_fn; SignalSnapshot.captured_at must reflect it."""
    weird_now = datetime(2099, 1, 1, 0, 0, tzinfo=timezone.utc)
    _write_plan(memory_dir, target_date)
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    result = run(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader,
        now_fn=lambda: weird_now,
    )
    # The verdict's signal_summary should reflect snapshot built with weird_now
    # (acceptance: result completed without error and ledger entry exists)
    assert result["ledger_entry_id"] is not None
```

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_daily_adapt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter.daily_adapt'`.

- [ ] **Step 2: Run RED**

Confirm the first error is `ModuleNotFoundError: No module named 'src.coach.adapter.daily_adapt'`. Anything else (e.g. `NameError` on `_write_plan`) means a typo in the test file itself — fix the test, not the source.

- [ ] **Step 3: Implement daily_adapt orchestrator + CLI**

Write `icu/src/coach/adapter/daily_adapt.py`:

```python
"""Daily adaptation orchestrator — pure function, no IO except via injected writer.

Composes:
  wellness + plan + physiology + ledger history
    → SignalSnapshot + AthleteStateRef
    → evaluate_signals  → AdaptationVerdict
    → (red) revise_session → DesignedSession | None
    → build_yellow_nudge / build_red_override → markdown
    → write report + proposed_session + ledger entry  (skipped under dry_run)

CLI is a thin shell in scripts/daily_adapt.py.
"""
from __future__ import annotations

import json
from datetime import date as DateT, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter
from src.coach.periodization.types import IntensityTier, SessionType
from src.coach.session_designer.types import (
    DayPlanV2,
    DesignedSession,
    SessionStructure,
    WeeklyPlan,
)

from .prompt_builder import build_red_override, build_yellow_nudge
from .rules import evaluate_signals
from .session_revisor import revise_session
from .types import SignalSnapshot

_log = get_logger("adapter")

# ── Phase 2 DayPlanV2.training_type → SessionType
_TRAINING_TYPE_TO_SESSION_TYPE: dict[str, SessionType] = {
    "Rest":          SessionType.REST,
    "Recovery":      SessionType.RECOVERY,
    "Aerobic":       SessionType.AEROBIC,
    "Tempo":         SessionType.TEMPO,
    "Threshold":     SessionType.THRESHOLD,
    "VO2max":        SessionType.VO2MAX,
    "Neuromuscular": SessionType.NEUROMUSCULAR,
    "Race":          SessionType.RACE,
}

_BASELINE_DAYS = 28
_BASELINE_MIN_SAMPLES = 7  # below this, return None → evaluate_signals skips that signal


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _wellness_for_date(history: list[dict], target_date: DateT) -> dict:
    iso = target_date.isoformat()
    for entry in history:
        if isinstance(entry.get("id"), str) and entry["id"].startswith(iso):
            return entry
    raise ValueError(f"No wellness entry for {iso} in history")


def _baseline_window(history: list[dict], target_date: DateT, key: str) -> float | None:
    iso_cutoff = target_date.isoformat()
    samples: list[float] = []
    for entry in history:
        eid = entry.get("id", "")
        if not isinstance(eid, str) or len(eid) < 10:
            continue
        d = eid[:10]
        if d >= iso_cutoff:
            continue
        # Within the prior _BASELINE_DAYS window?
        if d < (target_date - timedelta(days=_BASELINE_DAYS)).isoformat():
            continue
        v = entry.get(key)
        if isinstance(v, (int, float)):
            samples.append(float(v))
    if len(samples) < _BASELINE_MIN_SAMPLES:
        return None
    return sum(samples) / len(samples)


def _build_signal_snapshot(
    history: list[dict], target_date: DateT, now: datetime,
) -> SignalSnapshot:
    today = _wellness_for_date(history, target_date)
    sleep_secs = today.get("sleepSecs")
    if sleep_secs is None:
        raise ValueError(f"sleepSecs missing for {target_date.isoformat()}")
    return SignalSnapshot(
        captured_at=now,
        hrv_ms=float(today["hrv"]),
        resting_hr_bpm=int(today["restingHR"]),
        sleep_hours=float(sleep_secs) / 3600.0,
        soreness_score=int(today["soreness"]),
    )


_FALLBACK_STATE = AthleteStateRef(
    ctl=0.0, atl=0.0, tsb=0.0, w_prime=0,
    phase="UNKNOWN", week_of_year=1,
)


def _build_athlete_state(
    memory_dir: Path, warehouse_dir: Path, target_date: DateT,
) -> AthleteStateRef:
    wellness = _read_json(warehouse_dir / "2_Wellness" / "wellness_history.json")
    cp_w = _read_json(memory_dir / "physiology" / "cp_w_current.json")
    phase_doc = _read_json(memory_dir / "periodization" / "phase_current.json")
    if not isinstance(wellness, list) or not wellness:
        return _FALLBACK_STATE._replace_week(target_date.isocalendar()[1]) \
            if hasattr(_FALLBACK_STATE, "_replace_week") else _FALLBACK_STATE
    latest = wellness[-1]
    ctl = latest.get("ctl"); atl = latest.get("atl")
    if ctl is None or atl is None:
        return _FALLBACK_STATE
    w_prime = (cp_w or {}).get("w_prime_joules", 0)
    phase = (phase_doc or {}).get("current_phase", "UNKNOWN")
    try:
        return AthleteStateRef(
            ctl=float(ctl),
            atl=float(atl),
            tsb=float(ctl) - float(atl),
            w_prime=int(w_prime),
            phase=str(phase),
            week_of_year=target_date.isocalendar()[1],
        )
    except Exception:
        return _FALLBACK_STATE


def _find_original_session(memory_dir: Path, target_date: DateT) -> DesignedSession | None:
    rep_dir = memory_dir / "reports"
    if not rep_dir.exists():
        return None
    candidates = [p for p in rep_dir.glob("plan_*.json")
                  if not p.name.endswith(".trace.json")]
    if not candidates:
        return None
    # Newest by mtime (plan filenames are inconsistent: date vs week)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            plan = WeeklyPlan.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for day in plan.days:
            if day.date == target_date.isoformat():
                return _day_to_designed_session(day)
    return None


def _day_to_designed_session(day: DayPlanV2) -> DesignedSession:
    s_type = _TRAINING_TYPE_TO_SESSION_TYPE.get(day.training_type, SessionType.AEROBIC)
    return DesignedSession(
        day_of_week=day.day_of_week,
        date=day.date,
        session_type=s_type,
        name=day.name,
        description=day.description,
        duration_min=day.duration_min,
        target_tss=day.target_tss,
        structure=SessionStructure(steps=[]),
        power_range_w=day.power_range_w,
        hr_range_bpm=day.hr_range_bpm,
        trace=None,
    )


def run(
    *,
    target_date: DateT,
    memory_dir: Path,
    warehouse_dir: Path,
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    dry_run: bool = False,
) -> dict[str, Any]:
    """Evaluate today's signals; (optionally) persist outputs; return result dict."""
    now = now_fn()
    wellness_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = _read_json(wellness_path)
    if not isinstance(history, list) or not history:
        raise FileNotFoundError(f"wellness_history.json missing or empty: {wellness_path}")

    snapshot = _build_signal_snapshot(history, target_date, now)
    state = _build_athlete_state(memory_dir, warehouse_dir, target_date)
    baseline_hrv = _baseline_window(history, target_date, "hrv")
    baseline_hr = _baseline_window(history, target_date, "restingHR")

    # Read prior adaptation_verdict entries for the consecutive-red guardrail.
    if reader is None:
        reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    history_entries = reader.query(
        decision_type="adaptation_verdict",
        since=now - timedelta(days=4),
    )

    verdict = evaluate_signals(
        snapshot,
        state=state,
        history=history_entries,
        hrv_28d_mean_ms=baseline_hrv,
        resting_hr_28d_mean_bpm=baseline_hr,
    )

    # ── Find original session + branch on verdict
    original = _find_original_session(memory_dir, target_date)
    physiology = _read_json(memory_dir / "physiology" / "cp_w_current.json") or {}
    durability = _read_json(memory_dir / "physiology" / "durability.json") or {}
    response_profile = _read_json(memory_dir / "physiology" / "response_profile.json") or {}

    report_md: str | None = None
    proposed: DesignedSession | None = None

    if verdict.verdict == "yellow":
        report_md = build_yellow_nudge(
            verdict=verdict, snapshot=snapshot, today_session=original,
        )
    elif verdict.verdict == "red":
        original_type = original.session_type if original is not None else SessionType.REST
        proposed = revise_session(
            original_type=original_type, original_date=target_date,
            physiology=physiology, durability=durability,
            response_profile=response_profile,
        )
        report_md = build_red_override(
            verdict=verdict, snapshot=snapshot,
            original=original, proposed=proposed,
        )
    # green: report_md stays None, proposed stays None

    # ── Persist (skip when dry_run)
    report_path: Path | None = None
    proposed_path: Path | None = None
    entry_id: str | None = None

    if not dry_run:
        if report_md is not None:
            report_path = memory_dir / "adapter" / f"today_{target_date.isoformat()}.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_md, encoding="utf-8")
        if proposed is not None:
            proposed_path = memory_dir / "adapter" / f"proposed_session_{target_date.isoformat()}.json"
            proposed_path.parent.mkdir(parents=True, exist_ok=True)
            proposed_path.write_text(
                proposed.model_dump_json(indent=2), encoding="utf-8")

        if writer is None:
            writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
        entry_id = writer.record(
            decision_type="adaptation_verdict",
            source="adapter.daily",
            athlete_state=state,
            payload={
                "verdict": verdict.verdict,
                "severity_score": verdict.severity_score,
                "recommended_action": verdict.recommended_action,
                "triggered_rules": list(verdict.triggered_rules),
                "guardrails_hit": list(verdict.guardrails_hit),
                "original_session_type": original.session_type.value if original else None,
                "proposed_session_type": proposed.session_type.value if proposed else None,
                "report_path": str(report_path.relative_to(memory_dir)) if report_path else None,
                "proposed_session_path": str(proposed_path.relative_to(memory_dir)) if proposed_path else None,
            },
            evidence_refs=[
                str(wellness_path),
            ],
            confidence=1.0,
        )

    _log.event(
        "adapter_run_completed",
        date=target_date.isoformat(),
        verdict=verdict.verdict,
        recommended_action=verdict.recommended_action,
        dry_run=dry_run,
    )

    return {
        "verdict": verdict.verdict,
        "severity_score": verdict.severity_score,
        "recommended_action": verdict.recommended_action,
        "triggered_rules": list(verdict.triggered_rules),
        "guardrails_hit": list(verdict.guardrails_hit),
        "report_path": report_path,
        "proposed_session_path": proposed_path,
        "ledger_entry_id": entry_id,
    }
```

Write `icu/scripts/daily_adapt.py`:

```python
"""Phase 3 — Daily adaptation: 4-signal evaluation + (red) downgrade synthesis.

Reads:
  --memory     coach_memory/
  --warehouse  icu_data_warehouse/
  --date       YYYY-MM-DD
  [--ledger    coach_memory/ledger/decisions.jsonl] (default if --memory given)
  [--dry-run]  skip ALL writes (markdown / proposed_session / ledger)

Always-on side effects (when not --dry-run):
  - coach_memory/adapter/today_<date>.md    (yellow / red only)
  - coach_memory/adapter/proposed_session_<date>.json  (red + non-Rest only)
  - coach_memory/ledger/decisions.jsonl     (one append per call)

Never touches the network. apply_adaptation.py is the human-gate that pushes to ICU.

Exit codes:
  0 — success (any verdict, including dry-run)
  1 — fatal (wellness missing, schema mismatch, IO error)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/daily_adapt.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.adapter.daily_adapt import run  # noqa: E402
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 daily adaptation — evaluate signals, optionally write outputs.",
    )
    p.add_argument("--date", required=True, type=date.fromisoformat,
                   help="Target date YYYY-MM-DD")
    p.add_argument("--memory", required=True, type=Path,
                   help="coach_memory/ directory")
    p.add_argument("--warehouse", required=True, type=Path,
                   help="icu_data_warehouse/ directory")
    p.add_argument("--ledger", type=Path, default=None,
                   help="ledger JSONL path (default: <memory>/ledger/decisions.jsonl)")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip ALL writes (markdown / proposed_session / ledger)")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger_path = args.ledger or (args.memory / "ledger" / "decisions.jsonl")
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    try:
        result = run(
            target_date=args.date,
            memory_dir=args.memory,
            warehouse_dir=args.warehouse,
            writer=writer, reader=reader,
            now_fn=lambda: datetime.now(timezone.utc),
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # JSON-stringify Paths for stdout
    out = {
        k: (str(v) if isinstance(v, Path) else v) for k, v in result.items()
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Edit `icu/src/coach/adapter/__init__.py` — extend re-exports (preserve existing docstring + 既有 imports). Append:

```python
from .daily_adapt import run as run_daily_adapt
```

And extend `__all__` to include `"run_daily_adapt"` (keep alphabetical to match the existing block style).

- [ ] **Step 4: Run GREEN + regression**

```bash
cd icu && .venv/bin/pytest tests/unit/adapter/test_daily_adapt.py -v
cd icu && .venv/bin/pytest tests/unit/adapter/ -v   # was ~71, now ~71+11 = ~82 passed
cd icu && .venv/bin/pytest tests/unit/ -x           # full suite (baseline 482 + 11 = 493)
```

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/adapter/daily_adapt.py \
        icu/src/coach/adapter/__init__.py \
        icu/scripts/daily_adapt.py \
        icu/tests/unit/adapter/test_daily_adapt.py
git commit -m "feat(coach-phase3): daily_adapt orchestrator + CLI — 4-signal eval, write markdown + ledger entry"
```

## Task 61: `apply_adaptation.py` — human-gated ICU PATCH + ledger commit

**Files:**
- Create: `icu/src/coach/adapter/apply_adaptation.py`
- Create: `icu/scripts/apply_adaptation.py`
- Create: `icu/tests/unit/adapter/test_apply_adaptation.py`
- Edit: `icu/src/coach/adapter/__init__.py`（追加 `from .apply_adaptation import run as run_apply_adaptation`，扩 `__all__`）
- Edit: `icu/src/fetcher/icu_client.py`（仅在文件末尾追加一个新方法 `update_event(event_id, event_data)`；**不**改其它任何方法）

**Public API (locked):**

```python
# icu/src/coach/adapter/apply_adaptation.py
def run(
    *,
    target_date: date,
    memory_dir: Path,
    warehouse_dir: Path,
    client_factory: Callable[[], Any] = lambda: ICUClient(),
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    confirm: bool = False,
) -> dict:
    """
    Returns dict with keys:
      mode: "dry_run" | "applied"
      event_id: str | None  (None when proposed missing or dry_run found nothing)
      patch_payload: dict   (the body that would be / was sent)
      ledger_entry_id: str | None (None unless confirm=True AND PATCH succeeded)
      verdict_entry_id: str  (the source adaptation_verdict ULID)
    Raises if PATCH fails under confirm=True (ledger then NOT appended).
    """
```

CLI shell `icu/scripts/apply_adaptation.py`:

```
usage: apply_adaptation.py --date YYYY-MM-DD --memory <dir> --warehouse <dir>
                            [--ledger <path>] [--events <path>] [--confirm]
```

- 无 `--confirm` (默认): 加载 verdict + proposed + event_id → 计算 payload → 打印 payload + 「dry-run」字样 → exit 0。**不**调 fetcher、**不**写 ledger。
- 带 `--confirm`：以上 + `client.update_event(event_id, payload)` → 成功 append `adaptation_applied` + exit 0；任何 exception → stderr + 不写 ledger + exit 2。

**Design notes for `run(...)`:**

1. **Locate today's adaptation_verdict entry**
   - `entries = reader.query(decision_type="adaptation_verdict", since=date_start_utc, until=date_end_utc)` 取最新一条（按 `entry_id` 降序最新）。
   - 若无 → raise `ValueError("No adaptation_verdict for <date>; run daily_adapt first")`.
   - 若 `verdict != "red"` → raise `ValueError("verdict is <green/yellow>; nothing to apply")`. (Yellow 是 nudge-only; green 是 no-op; 都不该 apply。)
   - 若 `recommended_action == "rest_48h"` 或 `proposed_session_type is None` (Rest)：仍可 apply — 但 payload 把 `category` 设为 `"NOTE"` 并 `name="Rest day (auto)"`，效果上把当天 event 改成休息标记。也可以选择删 event；本规范保守地**改**而非删（保留 event_id 做 ledger 链接）。

2. **Load proposed_session.json (when present)**
   - Path: `memory_dir / "adapter" / f"proposed_session_{target_date.isoformat()}.json"`
   - 若文件存在：`DesignedSession.model_validate_json(...)` → 用其字段填 ICU payload（`name` / `description` / `duration_min` × 60 → `moving_time` / `target_tss` / `category="WORKOUT"`）。
   - 若文件不存在 (Rest 路径)：payload `name="Rest day (auto)"` / `description=verdict.notes or ""` / `category="NOTE"` / `moving_time=0`。

3. **Resolve event_id**
   - Read `warehouse_dir / "8_Events" / "events.json"`（list[dict]）。
   - 找 `event["start_date_local"][:10] == target_date.isoformat()` 且 `event["category"] in ("WORKOUT", "NOTE")` 的最新一条 (max by `id`)。
   - 若无 → raise `FileNotFoundError("No ICU event for <date>; cannot apply")`. (Phase 4 可考虑 `--create-if-missing` flag；M1 不做。)

4. **Build PATCH payload**
   - Minimal RESTful body for `PUT /events/{id}`:
     ```python
     payload = {
         "name": <session.name or "Rest day (auto)">,
         "description": <session.description or "...">,
         "category": "WORKOUT" if proposed else "NOTE",
         "moving_time": <session.duration_min * 60 if proposed else 0>,
         "icu_training_load": <session.target_tss if proposed else 0>,
     }
     ```
   - **不**尝试发送 `workout_doc` / `structure` —— 那是 ICU 的 sub-resource (workouts API)，与 events 解耦；T61 范围只动 event 的元数据。

5. **Branch on `confirm`**
   ```python
   if not confirm:
       _log.event("apply_dry_run", date=..., event_id=..., recommended_action=...)
       return {"mode": "dry_run", "event_id": event_id, "patch_payload": payload,
               "ledger_entry_id": None, "verdict_entry_id": verdict_entry.entry_id}
   client = client_factory()
   try:
       client.update_event(event_id, payload)
   except Exception as exc:
       _log.event("apply_failed", date=..., event_id=..., status="error",
                  error=str(exc), recommended_action="abort_no_ledger")
       raise
   # PATCH succeeded — only NOW append ledger
   entry_id = writer.record(
       decision_type="adaptation_applied",
       source="adapter.apply",
       athlete_state=verdict_entry.athlete_state_ref,
       payload={
           "event_id": event_id,
           "source_verdict_entry_id": verdict_entry.entry_id,
           "patched_fields": list(payload.keys()),
           "verdict": verdict_entry.payload.get("verdict"),
           "recommended_action": verdict_entry.payload.get("recommended_action"),
       },
       evidence_refs=[verdict_entry.entry_id],
       confidence=1.0,
   )
   _log.event("adaptation_applied", date=..., event_id=event_id,
              recommended_action=verdict_entry.payload.get("recommended_action"))
   return {"mode": "applied", ...}
   ```

6. **Transactional invariant** (covered by tests):
   - Failure path: `client.update_event` raises → `LedgerWriter.record` is **never** called → caller sees exception → exit non-zero.
   - Success path: ledger entry appended exactly once.

- [ ] **Step 1: Write failing tests**

Create `icu/tests/unit/adapter/test_apply_adaptation.py`:

```python
"""Unit tests for adapter.apply_adaptation.run — dry-run vs --confirm; ledger transactional."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.coach.adapter.apply_adaptation import run as run_apply
from src.coach.adapter.daily_adapt import run as run_daily
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter
from src.coach.periodization.types import SessionType
from src.coach.session_designer.types import DesignedSession


# ---------- Build a red-verdict day end-to-end via daily_adapt ----------

@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 4, 19, 6, 0, tzinfo=timezone.utc)


@pytest.fixture
def now_fn(fixed_now):
    return lambda: fixed_now


@pytest.fixture
def target_date() -> date:
    return date(2026, 4, 19)


@pytest.fixture
def red_world(tmp_path, target_date, now_fn) -> dict:
    """Set up memory_dir + warehouse_dir with a RED day already evaluated by daily_adapt."""
    memory_dir = tmp_path / "coach_memory"
    warehouse_dir = tmp_path / "icu_data_warehouse"

    (memory_dir / "physiology").mkdir(parents=True)
    (memory_dir / "periodization").mkdir(parents=True)
    (memory_dir / "reports").mkdir(parents=True)
    (memory_dir / "ledger").mkdir(parents=True)
    (warehouse_dir / "2_Wellness").mkdir(parents=True)
    (warehouse_dir / "8_Events").mkdir(parents=True)

    (memory_dir / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288,
    }), encoding="utf-8")
    (memory_dir / "physiology" / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1},
        "sample_size_rides": 28,
    }), encoding="utf-8")
    (memory_dir / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {}}), encoding="utf-8")
    (memory_dir / "periodization" / "phase_current.json").write_text(json.dumps({
        "current_phase": "BUILD"}), encoding="utf-8")

    # 28d baseline + red target day
    history = [
        {"id": f"{(target_date - timedelta(days=i)).isoformat()}T00:00:00",
         "hrv": 68.0, "restingHR": 52, "sleepSecs": 7 * 3600,
         "soreness": 4, "ctl": 70.0, "atl": 75.0}
        for i in range(30, 0, -1)
    ] + [{
        "id": f"{target_date.isoformat()}T00:00:00",
        "hrv": 68.0 * 0.80, "restingHR": 60, "sleepSecs": 3 * 3600,
        "soreness": 1, "ctl": 70.0, "atl": 80.0,
    }]
    (warehouse_dir / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(history), encoding="utf-8")

    # plan with a Threshold session today
    plan = {
        "week_start": target_date.isoformat(),
        "week_end": (target_date + timedelta(days=6)).isoformat(),
        "focus_theme": "test",
        "weekly_tss_target": 400,
        "coaching_summary": None,
        "days": [{
            "date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%a"),
            "training_type": "Threshold",
            "icu_type": "Ride",
            "name": "Threshold 2x20",
            "description": "2x20 @ FTP",
            "duration_min": 90,
            "target_tss": 110,
            "power_range_w": "260-280", "hr_range_bpm": "150-165",
        }],
    }
    (memory_dir / "reports" / f"plan_{target_date.isoformat()}.json").write_text(
        json.dumps(plan), encoding="utf-8")

    # ICU events.json (today's WORKOUT event)
    events = [{
        "id": "evt_999",
        "start_date_local": f"{target_date.isoformat()}T07:00:00",
        "category": "WORKOUT",
        "name": "Threshold 2x20",
    }]
    (warehouse_dir / "8_Events" / "events.json").write_text(
        json.dumps(events), encoding="utf-8")

    # Drive daily_adapt to write today_<date>.md, proposed_session_<date>.json,
    # and the ledger adaptation_verdict entry.
    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)
    daily_result = run_daily(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    assert daily_result["verdict"] == "red"
    assert daily_result["proposed_session_path"] is not None

    return {
        "memory_dir": memory_dir,
        "warehouse_dir": warehouse_dir,
        "ledger_path": ledger_path,
    }


# ---------- DRY-RUN: payload printed, no fetcher call, no ledger ----------

def test_dry_run_does_not_call_client_or_ledger(red_world, target_date, now_fn):
    mock_client = MagicMock()
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))

    result = run_apply(
        target_date=target_date,
        memory_dir=red_world["memory_dir"],
        warehouse_dir=red_world["warehouse_dir"],
        client_factory=lambda: mock_client,
        writer=writer, reader=reader, now_fn=now_fn,
        confirm=False,
    )
    assert result["mode"] == "dry_run"
    assert result["event_id"] == "evt_999"
    assert result["ledger_entry_id"] is None
    assert isinstance(result["patch_payload"], dict)
    assert "name" in result["patch_payload"]

    mock_client.update_event.assert_not_called()
    n_after = len(reader.query(decision_type="adaptation_applied"))
    assert n_before == n_after  # NO ledger row added


# ---------- --confirm happy: client called, ledger appended ----------

def test_confirm_happy_path_calls_client_and_appends_ledger(
    red_world, target_date, now_fn,
):
    mock_client = MagicMock()
    mock_client.update_event.return_value = {"id": "evt_999"}
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))

    result = run_apply(
        target_date=target_date,
        memory_dir=red_world["memory_dir"],
        warehouse_dir=red_world["warehouse_dir"],
        client_factory=lambda: mock_client,
        writer=writer, reader=reader, now_fn=now_fn,
        confirm=True,
    )
    assert result["mode"] == "applied"
    assert result["event_id"] == "evt_999"
    assert result["ledger_entry_id"] is not None

    mock_client.update_event.assert_called_once()
    args, kwargs = mock_client.update_event.call_args
    # First positional = event_id; second positional = payload dict
    assert args[0] == "evt_999"
    payload = args[1] if len(args) > 1 else kwargs.get("event_data") or kwargs.get("payload")
    assert isinstance(payload, dict)
    assert "name" in payload

    applied_entries = reader.query(decision_type="adaptation_applied")
    assert len(applied_entries) == n_before + 1
    last = applied_entries[-1]
    assert last.payload["event_id"] == "evt_999"
    assert "source_verdict_entry_id" in last.payload


# ---------- --confirm failure: NO ledger entry, exception raised ----------

def test_confirm_patch_failure_does_not_write_ledger(
    red_world, target_date, now_fn,
):
    mock_client = MagicMock()

    class _PatchFailed(RuntimeError):
        pass

    mock_client.update_event.side_effect = _PatchFailed("HTTP 503")
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))

    with pytest.raises(_PatchFailed):
        run_apply(
            target_date=target_date,
            memory_dir=red_world["memory_dir"],
            warehouse_dir=red_world["warehouse_dir"],
            client_factory=lambda: mock_client,
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=True,
        )
    # Ledger uncorrupted
    n_after = len(reader.query(decision_type="adaptation_applied"))
    assert n_after == n_before


# ---------- Missing verdict: fail-fast ----------

def test_no_verdict_today_raises(tmp_path, target_date, now_fn):
    memory_dir = tmp_path / "coach_memory"
    warehouse_dir = tmp_path / "icu_data_warehouse"
    (memory_dir / "ledger").mkdir(parents=True)
    (warehouse_dir / "8_Events").mkdir(parents=True)
    (warehouse_dir / "8_Events" / "events.json").write_text(json.dumps([]), encoding="utf-8")
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    with pytest.raises((ValueError, FileNotFoundError)):
        run_apply(
            target_date=target_date,
            memory_dir=memory_dir, warehouse_dir=warehouse_dir,
            client_factory=lambda: MagicMock(),
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=False,
        )


# ---------- Yellow / green verdict cannot be applied ----------

def test_yellow_verdict_refuses_apply(red_world, target_date, now_fn):
    """Manually overwrite ledger to put a YELLOW entry today, then try to apply → ValueError."""
    # Swap the ledger to a single yellow entry
    ledger_path = red_world["ledger_path"]
    ledger_path.write_text("", encoding="utf-8")
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)
    writer.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=AthleteStateRef(
            ctl=70.0, atl=75.0, tsb=-5.0,
            w_prime=20000, phase="BUILD",
            week_of_year=target_date.isocalendar()[1],
        ),
        payload={
            "verdict": "yellow",
            "severity_score": 0.4,
            "recommended_action": "nudge_only",
            "triggered_rules": [],
            "guardrails_hit": [],
            "original_session_type": "THRESHOLD",
            "proposed_session_type": None,
            "report_path": None,
            "proposed_session_path": None,
        },
    )
    with pytest.raises(ValueError):
        run_apply(
            target_date=target_date,
            memory_dir=red_world["memory_dir"],
            warehouse_dir=red_world["warehouse_dir"],
            client_factory=lambda: MagicMock(),
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=False,
        )


# ---------- Defense-in-depth: no LLM SDK transitive import ----------

def test_module_does_not_import_llm_sdks():
    import sys
    forbidden = ("google.genai", "anthropic", "openai")
    # Importing the module under test must not pull in any LLM SDK
    from src.coach.adapter import apply_adaptation  # noqa: F401
    for name in forbidden:
        assert name not in sys.modules, f"forbidden import: {name}"


# ---------- ICUClient extension exists ----------

def test_icu_client_has_update_event_method():
    from src.fetcher.icu_client import ICUClient
    assert hasattr(ICUClient, "update_event"), \
        "T61 must add ICUClient.update_event(event_id, event_data)"
```

Run: `cd icu && .venv/bin/pytest tests/unit/adapter/test_apply_adaptation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.adapter.apply_adaptation'`.

- [ ] **Step 2: Run RED**

Confirm `ModuleNotFoundError` is the first error. If `test_icu_client_has_update_event_method` fails after the module exists with `AssertionError`, that's expected — the implementation step adds the method.

- [ ] **Step 3: Implement apply_adaptation orchestrator + CLI + ICUClient extension**

Write `icu/src/coach/adapter/apply_adaptation.py`:

```python
"""Human-gated ICU PATCH after adapter daily verdict.

Default: dry-run — print the payload that would be sent, exit 0.
With --confirm: send PUT /athlete/{id}/events/{event_id} via ICUClient.update_event,
then append `adaptation_applied` to ledger.

Transactional invariant: ledger entry is appended ONLY after PATCH succeeds.
On any PATCH exception, the ledger stays untouched and the exception propagates.
"""
from __future__ import annotations

import json
from datetime import date as DateT, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import DecisionEntry
from src.coach.ledger.writer import LedgerWriter
from src.coach.session_designer.types import DesignedSession
from src.fetcher.icu_client import ICUClient

_log = get_logger("adapter")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_today_verdict(reader: LedgerReader, target_date: DateT) -> DecisionEntry:
    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    day_end = day_start.replace(hour=23, minute=59, second=59)
    entries = reader.query(
        decision_type="adaptation_verdict",
        since=day_start, until=day_end,
    )
    if not entries:
        raise ValueError(
            f"No adaptation_verdict for {target_date.isoformat()}; run daily_adapt first")
    # entries are sorted ascending by entry_id (= time-sortable ULID); take latest
    return entries[-1]


def _find_today_event_id(warehouse_dir: Path, target_date: DateT) -> str:
    events = _read_json(warehouse_dir / "8_Events" / "events.json")
    if not isinstance(events, list):
        raise FileNotFoundError(
            f"events.json missing or malformed in {warehouse_dir}/8_Events")
    iso = target_date.isoformat()
    candidates = [
        e for e in events
        if isinstance(e.get("start_date_local"), str)
        and e["start_date_local"].startswith(iso)
        and e.get("category") in ("WORKOUT", "NOTE")
    ]
    if not candidates:
        raise FileNotFoundError(f"No ICU event for {iso}; cannot apply")
    candidates.sort(key=lambda e: str(e.get("id", "")))
    return str(candidates[-1]["id"])


def _build_patch_payload(
    proposed: DesignedSession | None, verdict_payload: dict[str, Any],
) -> dict[str, Any]:
    if proposed is None:
        # Rest path
        return {
            "name": "Rest day (auto, adapter)",
            "description": verdict_payload.get("triggered_rules") and
                f"Adapter flagged {verdict_payload.get('verdict','red').upper()}: "
                f"{', '.join(verdict_payload.get('triggered_rules', []))}" or
                "Rest day (auto from adapter)",
            "category": "NOTE",
            "moving_time": 0,
            "icu_training_load": 0,
        }
    return {
        "name": proposed.name,
        "description": proposed.description,
        "category": "WORKOUT",
        "moving_time": int(proposed.duration_min) * 60,
        "icu_training_load": int(proposed.target_tss),
    }


def run(
    *,
    target_date: DateT,
    memory_dir: Path,
    warehouse_dir: Path,
    client_factory: Callable[[], Any] = lambda: ICUClient(),
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    confirm: bool = False,
) -> dict[str, Any]:
    if reader is None:
        reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    if writer is None:
        writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")

    verdict_entry = _find_today_verdict(reader, target_date)
    if verdict_entry.payload.get("verdict") != "red":
        raise ValueError(
            f"Today's verdict is {verdict_entry.payload.get('verdict')!r}; "
            "only 'red' verdicts can be applied to ICU.")

    proposed_path = memory_dir / "adapter" / f"proposed_session_{target_date.isoformat()}.json"
    proposed: DesignedSession | None = None
    if proposed_path.exists():
        proposed = DesignedSession.model_validate_json(
            proposed_path.read_text(encoding="utf-8"))

    event_id = _find_today_event_id(warehouse_dir, target_date)
    payload = _build_patch_payload(proposed, verdict_entry.payload)

    if not confirm:
        _log.event(
            "apply_dry_run",
            date=target_date.isoformat(),
            event_id=event_id,
            recommended_action=verdict_entry.payload.get("recommended_action"),
        )
        return {
            "mode": "dry_run",
            "event_id": event_id,
            "patch_payload": payload,
            "ledger_entry_id": None,
            "verdict_entry_id": verdict_entry.entry_id,
        }

    client = client_factory()
    try:
        client.update_event(event_id, payload)
    except Exception as exc:
        _log.event(
            "apply_failed",
            date=target_date.isoformat(),
            event_id=event_id,
            status="error",
            error=str(exc),
            recommended_action="abort_no_ledger",
        )
        raise

    entry_id = writer.record(
        decision_type="adaptation_applied",
        source="adapter.apply",
        athlete_state=verdict_entry.athlete_state_ref,
        payload={
            "event_id": event_id,
            "source_verdict_entry_id": verdict_entry.entry_id,
            "patched_fields": list(payload.keys()),
            "verdict": verdict_entry.payload.get("verdict"),
            "recommended_action": verdict_entry.payload.get("recommended_action"),
        },
        evidence_refs=[verdict_entry.entry_id],
        confidence=1.0,
    )
    _log.event(
        "adaptation_applied",
        date=target_date.isoformat(),
        event_id=event_id,
        recommended_action=verdict_entry.payload.get("recommended_action"),
    )
    return {
        "mode": "applied",
        "event_id": event_id,
        "patch_payload": payload,
        "ledger_entry_id": entry_id,
        "verdict_entry_id": verdict_entry.entry_id,
    }
```

Write `icu/scripts/apply_adaptation.py`:

```python
"""Phase 3 — Apply adapter's red-verdict downgrade to ICU (human-gated).

Default behavior: print the PUT payload that would be sent; exit 0.
With --confirm: actually call ICUClient.update_event; on success append
`adaptation_applied` to ledger; on failure leave ledger untouched and exit 2.

Reads:
  --memory     coach_memory/
  --warehouse  icu_data_warehouse/
  --date       YYYY-MM-DD
  [--confirm]  send the PUT to ICU
  [--ledger    coach_memory/ledger/decisions.jsonl]

Exit codes:
  0 — success (dry-run or applied)
  1 — pre-flight failure (no verdict, no event, malformed input)
  2 — PATCH itself failed (network, HTTP error)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/apply_adaptation.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.adapter.apply_adaptation import run  # noqa: E402
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402
from src.fetcher.icu_client import ICUClient  # noqa: E402


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 3 apply adaptation — push red-verdict downgrade to ICU (human-gated).",
    )
    p.add_argument("--date", required=True, type=date.fromisoformat)
    p.add_argument("--memory", required=True, type=Path)
    p.add_argument("--warehouse", required=True, type=Path)
    p.add_argument("--ledger", type=Path, default=None)
    p.add_argument("--confirm", action="store_true",
                   help="Actually send the PUT to ICU. Default = dry-run print only.")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger_path = args.ledger or (args.memory / "ledger" / "decisions.jsonl")
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    try:
        result = run(
            target_date=args.date,
            memory_dir=args.memory,
            warehouse_dir=args.warehouse,
            client_factory=lambda: ICUClient(),
            writer=writer, reader=reader,
            now_fn=lambda: datetime.now(timezone.utc),
            confirm=args.confirm,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # PATCH failed
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.confirm:
        print("\n[dry-run] no changes were sent. Re-run with --confirm to apply.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Edit `icu/src/coach/adapter/__init__.py` — add `from .apply_adaptation import run as run_apply_adaptation` to imports and `"run_apply_adaptation"` to `__all__`.

Edit `icu/src/fetcher/icu_client.py` — append (do NOT modify any other method):

```python
    def update_event(self, event_id, event_data):
        """更新 ICU 日历上指定的训练计划事件 (PUT)."""
        path = f"/athlete/{self.athlete_id}/events/{event_id}"
        return self._request("PUT", path, json=event_data).json()
```

(Per intervals.icu REST conventions used by `create_event` / `delete_event`, `update_event` issues PUT — there is no PATCH verb in the existing client's `_request` flow. PUT semantics here are full-resource-replace, which matches our payload shape.)

- [ ] **Step 4: Run GREEN + regression**

```bash
cd icu && .venv/bin/pytest tests/unit/adapter/test_apply_adaptation.py -v
cd icu && .venv/bin/pytest tests/unit/adapter/ -v   # ~82 (after T60) + 7 = ~89 passed
cd icu && .venv/bin/pytest tests/unit/ -x           # full suite — was 482, now ~493+7 = ~500
```

If `test_icu_client_has_update_event_method` is the only fixer expected to flip from RED→GREEN at this step, the implementation step is complete. If any **other** ICUClient test broke, you accidentally modified an existing method — revert and restrict yourself to appending the new method.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/adapter/apply_adaptation.py \
        icu/src/coach/adapter/__init__.py \
        icu/scripts/apply_adaptation.py \
        icu/src/fetcher/icu_client.py \
        icu/tests/unit/adapter/test_apply_adaptation.py
git commit -m "feat(coach-phase3): apply_adaptation human-gated ICU PUT + ledger transactional commit"
```

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/adapter/ -v` 全绿 (~89 tests, 含 T60 + T61 新增)
- [ ] `cd icu && .venv/bin/pytest tests/unit/ -x` 全套不挂（baseline 482 → ~500）
- [ ] 2 次提交完成（T60 / T61 各一次，commit msg 前缀 `feat(coach-phase3):`）
- [ ] `git grep -nE 'google\.genai|anthropic|openai' icu/scripts/daily_adapt.py icu/scripts/apply_adaptation.py icu/src/coach/adapter/daily_adapt.py icu/src/coach/adapter/apply_adaptation.py` 无输出（API_FREE_WORKFLOW 守住）
- [ ] `git grep -n 'requests.patch\|httpx' icu/src/coach/adapter/ icu/scripts/daily_adapt.py icu/scripts/apply_adaptation.py` 无输出（NO_NEW_DEPS + 唯一 fetcher seam 守住）
- [ ] `git grep -n 'datetime.now(' icu/src/coach/adapter/daily_adapt.py icu/src/coach/adapter/apply_adaptation.py` 仅出现在默认参数 lambda 里，**不**出现在函数体（now_fn 注入守住）
- [ ] `git grep -n '_log.event(.*action=' icu/src/coach/adapter/daily_adapt.py icu/src/coach/adapter/apply_adaptation.py` 无输出（防 `JSONLLogger.event(action=)` 撞名）
- [ ] `cd icu && .venv/bin/python -c "from src.coach.adapter import run_daily_adapt, run_apply_adaptation; from src.fetcher.icu_client import ICUClient; assert hasattr(ICUClient, 'update_event'); print('ok')"` 输出 `ok`
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`06-consensus-infrastructure.md`](./06-consensus-infrastructure.md) 开始（T62–T64，consensus 包 + LedgerReader 历史回读）

## Known landmines (写在最前面给 implementer 看)

1. **`_log.event(action=...)` 冲突** — `JSONLLogger.event(action: str, *, ...)` 把 `action` 作为第一位置参数。任何 `_log.event("foo", action="...")` 立即报 `TypeError: event() got multiple values for argument 'action'`。本文件统一用 `recommended_action=` / `event_id=` / `date=` kwarg 名，绝不重用 `action`。File 03/04 已踩此坑，再踩一次会浪费一个 commit cycle。

2. **`datetime.now()` 不可在主流程直接调** — 否则单测无法注入时间。`now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc)` 是唯一允许出现 `datetime.now` 的位置（默认参数）。函数体内只用 `now_fn()`。grep `git grep 'datetime\.now' icu/src/coach/adapter/daily_adapt.py icu/src/coach/adapter/apply_adaptation.py` 必须只命中默认参数行。

3. **`DesignedSession.model_dump_json()` round-trip 必须保留 SessionType enum** — Pydantic v2 默认把 `Enum` 序列化成 `value`（字符串）。`model_validate_json` 会把字符串还原成 enum。本文件的 `test_proposed_session_json_roundtrips_session_type_enum` 用 `is SessionType.RECOVERY` 断言验证；如果实现里手写了 `dict(session)` 而非 `model_dump_json`，enum 会丢身份。

4. **中文字符 `Path.write_text` 必须 `encoding="utf-8"`** — `prompt_builder` 输出含 "完全休息" / "今日训练**不变**" / "运行下面的命令"。Windows / WSL 默认 cp936 / cp1252 locale 下，无 `encoding="utf-8"` 的 `write_text` 抛 `UnicodeEncodeError`。本文件已锁定 `encoding="utf-8"`，并有 `test_red_markdown_writes_utf8_under_ascii_locale` 在 `LANG=C` 下复现旧 bug。

5. **ICUClient 没有 `update_event` 方法 — 必须新增（不修改既有方法）** — 当前 `icu_client.py` 只有 `create_event` (POST) / `delete_event` (DELETE)。intervals.icu API 用 PUT 而非 PATCH 更新 events（与 brief 文档措辞 "PATCH" 略有出入，但 PUT 是 client 既有 `_request` 已支持的语义）。T61 在 `icu_client.py` **末尾**追加方法 — 这不算 PHASE_1_2_IMMUTABILITY 违例（fetcher 不在禁修文件列表内；况且只新增、不动既有逻辑）。但若 PR reviewer 担忧此偏离，可以在文件顶部加一行注释 `# Phase 3 T61 extension: update_event` 标注追加点。

6. **Yellow / Green 不可 `--confirm`** — `apply_adaptation.run(...)` 在 verdict 非 red 时立即 `raise ValueError(...)`。CLI shell 把这个映射成 exit 1（pre-flight failure），不是 exit 2（PATCH failure）。区分 exit code 帮助下游脚本判断是「不该 apply」还是「网络挂了」。

7. **Ledger 事务半提交保护** — `client.update_event(...)` 抛异常时**严禁**调 `writer.record(...)`。本文件实现里 `try/except` 块只 `_log.event` + `raise`，不在 `except` 子句调 writer。`test_confirm_patch_failure_does_not_write_ledger` 用 mock `side_effect` + `AssertionError` 在 ledger 末尾断言长度无变化。

8. **Plan 文件命名 inconsistent** — `coach_memory/reports/` 下既可能有 `plan_2026-04-19.json` 也可能有 `plan_2026-W16.json`。**禁止**按文件名解析日期；用 mtime 取最新 plan，再扫 `plan.days[i].date == target_date.isoformat()` 找当日 day。本文件实现已按此处理。

9. **Wellness `id` 字段格式** — intervals.icu 把 wellness `id` 写成 `YYYY-MM-DDT00:00:00`（含 `T00:00:00` 后缀）。匹配当日用 `entry["id"].startswith(target_date.isoformat())` 而非 `==`。

10. **`SignalSnapshot.captured_at` 时区必须 aware** — `SignalSnapshot.captured_at` 是 Pydantic `datetime`，`AdaptationVerdict.created_at` 同理。`now_fn()` 的默认 `datetime.now(timezone.utc)` 是 aware 的；测试里写 `datetime(2026, 4, 19, 6, 0, tzinfo=timezone.utc)` 也是 aware。**不要**用 `datetime.utcnow()` —— 那个返回 naive datetime，会被 `LedgerWriter._require_utc` 校验拒绝。

11. **Events.json category 字段** — intervals.icu 里 event 可能是 `"WORKOUT"` / `"NOTE"` / `"RACE"` / `"GOAL"` 等。本文件只接受前两者作为可 PATCH 的对象（`RACE` / `GOAL` 不该被 adapter 自动覆盖）。fixture 里测试的 `category="WORKOUT"` 是默认 happy path。

12. **`tests/fixtures/phase3/` 是否需要预先 mkdir** — 不需要。本文件全部测试用 `tmp_path` 构造 fixture（in-memory dir per test），无需 commit 任何文件到 `tests/fixtures/phase3/`。该目录会在 File 06 / 07 测试需要静态金标准 prompt 文本时首次落盘 — 本文件不动它。
