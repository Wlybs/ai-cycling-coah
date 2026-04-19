# Phase 2 — Integration (Tasks T45–T46)

> **Revised 2026-04-19:** API-free prose flow. No `google.genai` import, no
> `enrich_with_prose` call. Uses `plan_writer.save_weekly_plan` +
> `prose_io.render_prose_prompt` + `prose_io.load_and_apply_prose`.
> See [`../../specs/2026-04-19-phase-2-file-09-redesign.md`](../../specs/2026-04-19-phase-2-file-09-redesign.md).

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/session_designer/generator_v2.py`（门面：`generate_plan_v2`）
- `icu/scripts/push_plan.py`（**只追加 args + import，不重写旧逻辑**）
- `icu/tests/unit/session_designer/test_generator_v2.py`
- `icu/tests/integration/test_push_plan_engine_flag.py`

**Goal:** 把 Phase 2 全栈（Periodization → Designer → Prose → save）串成一个 `generate_plan_v2()` 函数；在 `push_plan.py` 加 `--engine v2` 开关；失败必自动回退到旧 `plan_generator.generate_plan()`。

---

## Task 45: generate_plan_v2 facade

**Files:**
- Create: `icu/src/coach/session_designer/generator_v2.py`
- Create: `icu/tests/unit/session_designer/test_generator_v2.py`

### Algorithm

1. Parse `week_start / week_end` — 如果调用方给了，用；否则走 `plan_generator._next_week_range()`（read-only reuse，不修改旧文件）
2. 读 warehouse + memory（与 engine.py 相同的路径解析）
3. 调 `periodization.engine.refresh_periodization(reference_date=week_start)` → 结果里 `micro_cycle` 对应到目标周
4. 如果 refresh 返回 `status != ok`，raise；由 CLI 决定是否回退
5. 调 `session_designer.assembler.design_week(micro, memory_dir)` → `(plan, sessions, violations)`
6. 调 `prose_io.render_prose_prompt()` 生成提示词（API-free，仅本地）
7. 调 `save_weekly_plan()` 生成 json + md + prose_prompt；`write_plan_trace()` 生成 trace
8. 如果 `push_to_icu`：调用已有的 `src.coach.plan_generator._push_to_icu(plan_dict)` — 这是 Phase 1 未标记为"禁止修改"的 helper，可以 import 重用。但要确认 `_push_to_icu` 能吃 `plan.model_dump()` 结果（DayPlanV2 字段与 legacy DayPlan 一对一，应可以直接吃）
9. 返回 `{status, plan_path, trace_path, violations, prose_prompt_path}`
10. 用户在 Claude Code 或 Gemini 中粘贴提示词，获得 JSON 响应后，运行 `load_and_apply_prose()` 合并

### Important guardrails

- **Do not** import `plan_generator.generate_plan()` — 它会触发一次完整 Gemini 调用，我们要自己控制
- **Do** import `plan_generator._push_to_icu` + `plan_generator._next_week_range`（utility reuse，不修改那个文件）
- 所有 Gemini 失败都走 fallback；CLI 失败才走 engine=legacy fallback

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_generator_v2.py`:
```python
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.coach.session_designer.generator_v2 import (
    generate_plan_v2, GeneratePlanV2Result,
)


def _seed_warehouse_and_memory(tmp_path):
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "2_Wellness").mkdir(parents=True)
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "1_Profile").mkdir(parents=True)
    (warehouse / "2_Wellness" / "wellness_history.json").write_text(json.dumps([
        {"id": f"2026-03-{d:02d}", "ctl": 80 + d * 0.4, "atl": 90}
        for d in range(1, 32)
    ] + [
        {"id": f"2026-04-{d:02d}", "ctl": 92 + d * 0.2, "atl": 95}
        for d in range(1, 19)
    ]))
    (warehouse / "8_Events" / "events.json").write_text(json.dumps([
        {"id": 1, "category": "RACE", "name": "Goal",
         "start_date_local": "2026-06-15T08:00:00"},
    ]))
    (warehouse / "1_Profile" / "athlete.json").write_text(json.dumps({
        "ftp": 288, "hr_max": 195, "weight": 62}))

    memory = tmp_path / "coach_memory"
    (memory / "physiology").mkdir(parents=True)
    (memory / "deep_analysis").mkdir()
    (memory / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 280, "w_prime_joules": 22000,
        "fit_r_squared": 0.95, "athlete_ftp_set": 288,
    }))
    (memory / "physiology" / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0},
        "sample_size_rides": 12,
    }))
    (memory / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {"Threshold": {"tolerance_class": "medium"},
                  "VO2max": {"tolerance_class": "medium"}},
        "knee_loading": {"flag": None, "standing_climb_minutes_90d": 0},
    }))
    return warehouse, memory


def test_generate_plan_v2_without_push_generates_skeleton(tmp_path):
    warehouse, memory = _seed_warehouse_and_memory(tmp_path)
    reports = tmp_path / "reports"
    result = generate_plan_v2(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        warehouse_dir=warehouse,
        memory_dir=memory,
        reports_dir=reports,
        push_to_icu=False,
    )
    assert isinstance(result, GeneratePlanV2Result)
    assert result.status == "ok"
    assert Path(result.plan_json_path).exists()
    assert Path(result.trace_path).exists()
    assert result.prose_prompt_path is not None
    assert Path(result.prose_prompt_path).exists()


def test_generate_plan_v2_with_push_calls_icu_only(tmp_path):
    warehouse, memory = _seed_warehouse_and_memory(tmp_path)
    reports = tmp_path / "reports"

    pushed = {"called": False}
    with patch("src.coach.plan_generator._push_to_icu",
               lambda plan_dict: pushed.__setitem__("called", True)):
        result = generate_plan_v2(
            week_start=date(2026, 4, 20),
            week_end=date(2026, 4, 26),
            warehouse_dir=warehouse, memory_dir=memory, reports_dir=reports,
            push_to_icu=True,
        )
    assert result.status == "ok"
    assert pushed["called"] is True
    assert Path(result.prose_prompt_path).exists()


def test_generate_plan_v2_returns_error_when_periodization_fails(tmp_path):
    warehouse = tmp_path / "icu_data_warehouse"
    warehouse.mkdir()
    memory = tmp_path / "coach_memory"
    memory.mkdir()
    # No wellness / events / athlete — engine should still build something
    # so force failure by patching refresh_periodization
    with patch(
        "src.coach.periodization.engine.refresh_periodization",
        return_value={"status": "error", "error": "forced"},
    ):
        result = generate_plan_v2(
            week_start=date(2026, 4, 20),
            week_end=date(2026, 4, 26),
            warehouse_dir=warehouse, memory_dir=memory,
            reports_dir=tmp_path / "reports",
            push_to_icu=False,
        )
    assert result.status == "error"
    assert "forced" in (result.error or "")
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement generator_v2**

Write `icu/src/coach/session_designer/generator_v2.py`:
```python
"""Phase 2 全栈门面：Periodization + Designer + Prose IO + Save + ICU push（API-free）。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date as DateT, datetime, timezone
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from ..periodization import engine as periodization_engine
from ..periodization.snapshot_io import load_periodization_snapshot
from .assembler import design_week, write_plan_trace
from .plan_writer import save_weekly_plan
from .prose_io import render_prose_prompt

LOG = get_logger("generate_plan_v2")


@dataclass
class GeneratePlanV2Result:
    status: str  # "ok" | "error"
    plan_json_path: Optional[str] = None
    plan_md_path: Optional[str] = None
    trace_path: Optional[str] = None
    prose_prompt_path: Optional[str] = None
    error: Optional[str] = None
    violations: Optional[list] = None


def _physiology_summary(memory_dir: Path) -> dict:
    import json
    phys_dir = Path(memory_dir) / "physiology"
    cp = wp = d60 = None
    knee = None
    try:
        cp_doc = json.loads((phys_dir / "cp_w_current.json").read_text())
        cp = int(cp_doc.get("cp_watts") or 0)
        wp = int(cp_doc.get("w_prime_joules") or 0)
    except Exception:
        pass
    try:
        dur_doc = json.loads((phys_dir / "durability.json").read_text())
        d60 = ((dur_doc.get("decay_rate_pct_per_1000kj") or {})
               .get("60s"))
    except Exception:
        pass
    try:
        resp_doc = json.loads((phys_dir / "response_profile.json").read_text())
        knee = (resp_doc.get("knee_loading") or {}).get("flag")
    except Exception:
        pass
    return {"cp": cp, "w_prime": wp,
            "durability_60s_pct": d60, "knee_flag": knee}


def generate_plan_v2(
    week_start: DateT,
    week_end: DateT,
    warehouse_dir: Path,
    memory_dir: Path,
    reports_dir: Path,
    push_to_icu: bool,
) -> GeneratePlanV2Result:
    t0 = time.monotonic()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1) Periodization refresh for target week
    refresh = periodization_engine.refresh_periodization(
        warehouse_dir=warehouse_dir,
        memory_dir=memory_dir,
        reference_date=week_start,
        generated_at=now_iso,
    )
    if refresh.get("status") != "ok":
        LOG.event(action="generate_plan_v2", status="error",
                  stage="periodization", error=refresh.get("error"))
        return GeneratePlanV2Result(
            status="error", error=refresh.get("error") or "periodization failed")

    snap = load_periodization_snapshot(Path(memory_dir) / "periodization")
    if snap is None:
        return GeneratePlanV2Result(
            status="error", error="periodization snapshot missing after refresh")

    # 2) Design week
    plan, sessions, violations = design_week(
        micro_cycle=snap.micro, memory_dir=memory_dir,
    )

    # 3) Generate prose prompt (API-free)
    physio_summary = _physiology_summary(memory_dir)
    prose_prompt = render_prose_prompt(
        plan=plan,
        phase_rationale=snap.micro.intent.rationale,
        phase_value=snap.current_phase.value,
        physiology_summary=physio_summary,
        violations=[v.model_dump() for v in violations],
    )

    # 4) Save reports (includes prose prompt)
    paths = save_weekly_plan(
        plan=plan, out_dir=reports_dir, prose_prompt=prose_prompt,
    )
    trace_path = write_plan_trace(
        out_dir=reports_dir, week_start=week_start,
        sessions=sessions, violations=violations, generated_at=now_iso,
    )

    # 5) ICU push (reuse legacy helper — read-only import)
    if push_to_icu:
        try:
            from src.coach.plan_generator import _push_to_icu
            _push_to_icu(plan.model_dump())
        except Exception as e:
            LOG.event(action="generate_plan_v2", status="error",
                      stage="push", error=str(e))
            return GeneratePlanV2Result(
                status="error", error=f"icu push failed: {e}",
                plan_json_path=paths["json"], plan_md_path=paths["md"],
                trace_path=trace_path,
                prose_prompt_path=paths.get("prose_prompt"),
                violations=[v.model_dump() for v in violations],
            )

    duration_ms = int((time.monotonic() - t0) * 1000)
    LOG.event(action="generate_plan_v2", status="ok",
              duration_ms=duration_ms,
              phase=snap.current_phase.value,
              violations_remaining=len(violations))

    return GeneratePlanV2Result(
        status="ok",
        plan_json_path=paths["json"],
        plan_md_path=paths["md"],
        trace_path=trace_path,
        prose_prompt_path=paths.get("prose_prompt"),
        violations=[v.model_dump() for v in violations],
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_generator_v2.py -v`
Expected: PASS all three.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/generator_v2.py \
        icu/tests/unit/session_designer/test_generator_v2.py
git commit -m "feat(coach-phase2): generate_plan_v2 facade (periodization + designer + prose + ICU push)"
```

---

## Task 46: push_plan.py `--engine v2` switch + fallback

**Goal:** 在 `scripts/push_plan.py` 里加 `--engine v1|v2` 选项：
- 默认 `v1`（走 legacy `generate_plan`） — 生产线保持不变
- `v2` 走 `generate_plan_v2`
- 如果 v2 返回 `error`，自动回退到 v1（打印 warning）

这是 **Phase 2 里唯一需要修改 `scripts/push_plan.py`** 的地方。改动限定在 `parse_args` 扩展 + 一个 `if engine == 'v2'` 分支，不触碰旧逻辑代码。

**Files:**
- Modify: `icu/scripts/push_plan.py`（仅追加）
- Create: `icu/tests/integration/test_push_plan_engine_flag.py`

### CLI Flags Reference

| Flag | Purpose |
|------|---------|
| `--engine v2` | Run `generate_plan_v2` (API-free skeleton + prose prompt). Default v1 for backward compatibility. |
| `--engine v1` | Legacy `generate_plan` — requires Gemini API key if `--push` is used. |
| `--push` | Push skeleton or enriched plan to ICU calendar. Works with both engines. |
| `--delete-existing` | Clear existing plan events before push (must use with `--push`). |
| `--week YYYY-MM-DD` | Target week (any day in week; rounded to Monday). If omitted, uses next week. |

- [ ] **Step 1: Write failing integration test**

Write `icu/tests/integration/test_push_plan_engine_flag.py`:
```python
import json
import subprocess
import sys
from pathlib import Path


def test_engine_v2_arg_accepted(tmp_path, monkeypatch):
    """Smoke-test: push_plan.py --engine v2 不崩，且不推送 ICU。"""
    # 执行 push_plan.py --engine v2 --week 2026-04-20 的 argv 解析，不真跑
    from icu.scripts.push_plan import parse_args

    # 模拟 argv
    monkeypatch.setattr(sys, "argv", [
        "push_plan.py", "--engine", "v2", "--week", "2026-04-20",
    ])
    push, delete_existing, week_start, engine = parse_args()
    assert engine == "v2"
    assert push is False
    assert week_start.isoformat() == "2026-04-20"


def test_engine_v1_default(monkeypatch):
    from icu.scripts.push_plan import parse_args
    monkeypatch.setattr(sys, "argv", ["push_plan.py"])
    push, delete_existing, week_start, engine = parse_args()
    assert engine == "v1"


def test_engine_invalid_value_raises(monkeypatch):
    from icu.scripts.push_plan import parse_args
    import pytest
    monkeypatch.setattr(sys, "argv", [
        "push_plan.py", "--engine", "blah",
    ])
    with pytest.raises(SystemExit):
        parse_args()
```

> **Note:** 如果 `icu/scripts/` 还未配置为 package（没有 `__init__.py`），改用 `importlib.util.spec_from_file_location` 动态加载；本项目 `scripts/` 在 Phase 1 已经建立为 `icu.scripts` 可导入路径（`sys.path.insert` 技巧），T22 阶段如有改动保持兼容。

- [ ] **Step 2: Run — fail**

Expected: FAIL — `parse_args` signature has 3 return values, not 4.

- [ ] **Step 3: Extend `scripts/push_plan.py` — minimal diff**

**Rule:** 只新增 argv 解析项、只在 `if engine == 'v2'` 分支里 import `generate_plan_v2`。旧 `generate_plan(...)` 分支完全不动。

Append / modify in `icu/scripts/push_plan.py`:
```python
# （在 parse_args 内部）
def parse_args():
    args = sys.argv[1:]
    push = "--push" in args
    delete_existing = "--delete-existing" in args

    week_start = None
    if "--week" in args:
        idx = args.index("--week")
        if idx + 1 < len(args):
            try:
                ref_date = datetime.strptime(args[idx + 1], "%Y-%m-%d").date()
                monday = ref_date - timedelta(days=ref_date.weekday())
                week_start = monday
            except ValueError:
                print(f"❌ 日期格式错误，应为 YYYY-MM-DD: {args[idx + 1]}")
                sys.exit(1)

    engine = "v1"
    if "--engine" in args:
        idx = args.index("--engine")
        if idx + 1 < len(args):
            val = args[idx + 1]
            if val not in ("v1", "v2"):
                print(f"❌ --engine 只接受 v1 或 v2, 收到 {val}")
                sys.exit(1)
            engine = val

    return push, delete_existing, week_start, engine
```

在 `__main__` 分支内加 engine 分支：
```python
if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    push, delete_existing, week_start, engine = parse_args()

    if week_start is None:
        week_start, week_end = _next_week_range()
    else:
        week_end = week_start + timedelta(days=6)

    print(f"计划周期: {week_start} 至 {week_end}")

    if delete_existing and push:
        print("\n🗑️  删除已有计划事件...")
        delete_plan_events(week_start, week_end)

    if engine == "v2":
        from src.utils.common import get_warehouse_dir
        from src.coach.session_designer.generator_v2 import generate_plan_v2
        result = generate_plan_v2(
            week_start=week_start, week_end=week_end,
            warehouse_dir=Path(get_warehouse_dir()),
            memory_dir=Path(get_warehouse_dir()).parent / "coach_memory",
            reports_dir=Path(get_warehouse_dir()).parent / "reports",
            push_to_icu=push,
        )
        if result.status == "ok":
            print(f"✅ v2 骨架计划已保存: {result.plan_json_path}")
            print(f"📝 教练叙述提示词: {result.prose_prompt_path}")
            if push:
                print(f"   （已推送到 ICU）")
            if result.violations:
                print(f"⚠️  未解决护栏: {result.violations}")
        else:
            print(f"⚠️  v2 失败回退 v1: {result.error}")
            generate_plan(week_start=week_start, week_end=week_end,
                          push_to_icu=push)
    else:
        generate_plan(week_start=week_start, week_end=week_end,
                      push_to_icu=push)
```

补一处 `import` 与 `from pathlib import Path`（文件顶部若未导入）：
```python
from pathlib import Path  # add if missing
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/integration/test_push_plan_engine_flag.py -v`
Expected: PASS all three.

- [ ] **Step 5: Manual smoke test**

```bash
cd icu && .venv/bin/python scripts/push_plan.py --engine v2 --week 2026-04-20
```

Expected output：
- 打印 `计划周期: 2026-04-20 至 2026-04-26`
- 如果 Phase 1 outputs 齐全：打印 `✅ v2 计划已保存: reports/plan_20260420.json`
- 如果 violations 有剩余：打印 warning 但不中断
- 若 periodization refresh 失败：打印 `⚠️ v2 失败回退 v1`，走旧 `generate_plan()`，但旧路径在本地仅生成 JSON + MD，不推送（因为没有 `--push`）

- [ ] **Step 6: Commit**

```bash
git add icu/scripts/push_plan.py \
        icu/tests/integration/test_push_plan_engine_flag.py
git commit -m "feat(coach-phase2): push_plan.py --engine v2 flag with automatic fallback to v1"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/` 全绿
- [ ] 2 次提交（T45 / T46）
- [ ] 手工烟雾测试通过
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`11-cli-tests-acceptance.md`](./11-cli-tests-acceptance.md) 开始。
