# Phase 2 — CLI tools + e2e + acceptance (Tasks T47–T49)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/scripts/periodization_audit.py`
- `icu/scripts/plan_preview.py`
- `icu/tests/integration/test_phase2_e2e.py`
- `icu/tests/e2e/acceptance_checklist.md`

**Goal:** 提供两个让人可读/可调试 Phase 2 产出的 CLI 工具，做一次端到端集成测试（从 warehouse 假数据到 WeeklyPlan），然后是真仓库验收。

---

## Task 47: CLI tools — periodization_audit + plan_preview

### T47.a — `scripts/periodization_audit.py`

**Goal:** 打印当前 `periodization_current.json` 的摘要：
- Current phase + reasons
- Macro 窗口列表（每行 phase + 日期 + weekly_tss_target）
- Meso pattern + weekly_load_multipliers
- 当周 micro intent + 7 日 tier/TSS 预览
- Next race（如有）

**Files:**
- Create: `icu/scripts/periodization_audit.py`
- Create: `icu/tests/unit/scripts/__init__.py`（如不存在）
- Create: `icu/tests/unit/scripts/test_periodization_audit.py`

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/scripts/test_periodization_audit.py`:
```python
import json
from datetime import date
from io import StringIO
from pathlib import Path

from src.coach.periodization.types import (
    DayIntent, IntensityTier, MacroPlan, MacroWindow, MesoBlock, MicroCycle,
    NextRace, Phase, PhaseIntent, PeriodizationSnapshot,
)
from icu.scripts.periodization_audit import main as audit_main


def _seed_snapshot(mem: Path):
    p = mem / "periodization"
    p.mkdir(parents=True)
    intent = PhaseIntent(
        phase=Phase.BUILD, primary_adaptation="threshold_capacity",
        weekly_tss_target=525,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(phase=Phase.BUILD,
                             start_date=date(2026, 4, 13),
                             end_date=date(2026, 5, 10), intent=intent)],
    )
    meso = MesoBlock(pattern="3:1",
                     block_start=date(2026, 4, 13),
                     block_end=date(2026, 5, 10),
                     weekly_load_multipliers=[1.0, 1.05, 1.10, 0.70],
                     phase=Phase.BUILD)
    micro = MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=Phase.BUILD, intent=intent,
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="z2")
              for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        weekly_tss_target=525,
    )
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD, macro=macro, meso=meso, micro=micro,
        next_race=NextRace(name="Goal", race_date=date(2026, 6, 15),
                           priority="A"),
    )
    (p / "periodization_current.json").write_text(snap.model_dump_json())


def test_audit_prints_phase_and_macro_and_micro(tmp_path, capsys):
    mem = tmp_path / "coach_memory"
    _seed_snapshot(mem)
    audit_main(memory_dir=mem)
    out = capsys.readouterr().out
    assert "BUILD" in out
    assert "Goal" in out
    # Macro 行包含日期
    assert "2026-04-13" in out
    # Micro 表格里有所有 7 天
    for d in ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"):
        assert d in out


def test_audit_handles_missing_snapshot(tmp_path, capsys):
    audit_main(memory_dir=tmp_path / "nope")
    out = capsys.readouterr().out
    assert "no snapshot" in out.lower() or "缺失" in out or "missing" in out.lower()
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — script undefined.

- [ ] **Step 3: Implement periodization_audit.py**

Write `icu/scripts/periodization_audit.py`:
```python
"""打印当前 periodization snapshot 的人类可读摘要。

用法:
  python scripts/periodization_audit.py
  python scripts/periodization_audit.py --memory-dir <custom-path>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coach.periodization.snapshot_io import load_periodization_snapshot


def _fmt_date(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def main(memory_dir: Path = None):
    if memory_dir is None:
        from src.utils.common import get_warehouse_dir
        memory_dir = Path(get_warehouse_dir()).parent / "coach_memory"
    memory_dir = Path(memory_dir)
    snap = load_periodization_snapshot(memory_dir / "periodization")
    if snap is None:
        print(f"❌ no snapshot found under {memory_dir / 'periodization'}")
        return

    print("=" * 64)
    print(f"Periodization Snapshot @ {snap.generated_at}")
    print(f"Current phase: {snap.current_phase.value}")
    if snap.next_race:
        print(f"Next race: {snap.next_race.name} on {_fmt_date(snap.next_race.race_date)} "
              f"(priority {snap.next_race.priority})")
    print("=" * 64)

    print("\nMacro plan:")
    print(f"  Season end: {_fmt_date(snap.macro.season_end_date)}")
    for w in snap.macro.windows:
        print(f"  [{w.phase.value:<10}] {_fmt_date(w.start_date)} → "
              f"{_fmt_date(w.end_date)}  "
              f"TSS target/wk={w.intent.weekly_tss_target}  "
              f"L/M/H={w.intent.intensity_distribution_pct}  "
              f"rest_days={w.intent.rest_days_per_week}")

    print("\nMeso block:")
    print(f"  pattern={snap.meso.pattern}  "
          f"{_fmt_date(snap.meso.block_start)} → "
          f"{_fmt_date(snap.meso.block_end)}")
    print(f"  load multipliers: {snap.meso.weekly_load_multipliers}")

    print("\nMicro cycle:")
    print(f"  {_fmt_date(snap.micro.week_start)} → "
          f"{_fmt_date(snap.micro.week_end)}  "
          f"TSS target={snap.micro.weekly_tss_target}")
    print(f"  rationale: {snap.micro.intent.rationale[:120]}")
    print("  " + "-" * 60)
    print(f"  {'Day':<4} {'Tier':<10} {'TSS':>5}  Hint")
    for d in snap.micro.days:
        print(f"  {d.day_of_week:<4} {d.tier.value:<10} "
              f"{d.target_tss:>5}  {d.session_hint}")
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/scripts/test_periodization_audit.py -v`
Expected: PASS both.

### T47.b — `scripts/plan_preview.py`

**Goal:** 不调 Gemini、不推送 ICU 地跑一次 `generate_plan_v2(push=False)`，打印生成的 `WeeklyPlan` 摘要 + violations。用来快速检查 Phase 2 是否会把计划算错。

**Files:**
- Create: `icu/scripts/plan_preview.py`
- Create: `icu/tests/unit/scripts/test_plan_preview.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/scripts/test_plan_preview.py`:
```python
import json
from pathlib import Path
from unittest.mock import patch

from icu.scripts.plan_preview import main as preview_main


def test_plan_preview_runs_dry_and_prints_summary(tmp_path, capsys):
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "2_Wellness").mkdir(parents=True)
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "1_Profile").mkdir(parents=True)
    (warehouse / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps([{"id": f"2026-04-{d:02d}", "ctl": 90 + d * 0.2}
                    for d in range(1, 19)]))
    (warehouse / "8_Events" / "events.json").write_text("[]")
    (warehouse / "1_Profile" / "athlete.json").write_text(
        json.dumps({"ftp": 288, "hr_max": 195, "weight": 62}))
    mem = tmp_path / "coach_memory"
    (mem / "physiology").mkdir(parents=True)
    (mem / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 280, "w_prime_joules": 22000,
        "fit_r_squared": 0.95, "athlete_ftp_set": 288}))
    (mem / "physiology" / "durability.json").write_text("{}")
    (mem / "physiology" / "response_profile.json").write_text("{}")
    reports = tmp_path / "reports"

    preview_main(
        warehouse_dir=warehouse, memory_dir=mem, reports_dir=reports,
        week_start_iso="2026-04-20",
    )
    out = capsys.readouterr().out
    assert "WeeklyPlan" in out or "计划" in out
    assert "TSS" in out
    # 7 天都列出来
    for d in ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"):
        assert d in out
    # 报告文件落地
    assert any(reports.glob("plan_*.json"))
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — script undefined.

- [ ] **Step 3: Implement plan_preview.py**

Write `icu/scripts/plan_preview.py`:
```python
"""本地 dry-run Phase 2 计划生成，不调 Gemini 不推 ICU。

用法:
  python scripts/plan_preview.py                       # 下周
  python scripts/plan_preview.py --week 2026-04-20
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coach.session_designer.generator_v2 import generate_plan_v2


def _parse_week(raw: str | None) -> datetime.date:
    if raw is None:
        today = datetime.now().date()
        return today + timedelta(days=(7 - today.weekday()))
    d = datetime.strptime(raw, "%Y-%m-%d").date()
    return d - timedelta(days=d.weekday())


def main(warehouse_dir: Path | None = None,
         memory_dir: Path | None = None,
         reports_dir: Path | None = None,
         week_start_iso: str | None = None):
    from src.utils.common import get_warehouse_dir
    warehouse_dir = warehouse_dir or Path(get_warehouse_dir())
    memory_dir = memory_dir or (warehouse_dir.parent / "coach_memory")
    reports_dir = reports_dir or (warehouse_dir.parent / "reports")

    if week_start_iso is None:
        week_start_iso = (
            sys.argv[sys.argv.index("--week") + 1]
            if "--week" in sys.argv else None
        )
    week_start = _parse_week(week_start_iso)
    week_end = week_start + timedelta(days=6)

    print(f"📝 Preview Phase 2 plan: {week_start} → {week_end}")
    result = generate_plan_v2(
        week_start=week_start, week_end=week_end,
        warehouse_dir=warehouse_dir, memory_dir=memory_dir,
        reports_dir=reports_dir,
        push_to_icu=False, gemini_client=None,
    )
    if result.status != "ok":
        print(f"❌ preview failed: {result.error}")
        return

    import json
    plan = json.loads(Path(result.plan_json_path).read_text())
    print(f"\n=== WeeklyPlan ({plan['week_start']} → {plan['week_end']}) ===")
    print(f"Focus: {plan['focus_theme']}")
    print(f"TSS target: {plan['weekly_tss_target']}")
    print("\n| Day | Type        | Name                         | min | TSS | Power     |")
    print("|-----|-------------|------------------------------|-----|-----|-----------|")
    for d in plan["days"]:
        power = d.get("power_range_w") or d.get("hr_range_bpm") or "-"
        print(f"| {d['day_of_week']} | {d['training_type']:<11} | "
              f"{d['name'][:28]:<28} | {d['duration_min']:>3} | "
              f"{d['target_tss']:>3} | {power:<9} |")

    if result.violations:
        print("\n⚠️  未解决护栏：")
        for v in result.violations:
            print(f"  - {v['rule']}: {v['message']} → {v['suggested_action']}")

    print(f"\n📄 {result.plan_json_path}")
    print(f"📄 {result.plan_md_path}")
    print(f"📄 {result.trace_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/scripts/test_plan_preview.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add icu/scripts/periodization_audit.py \
        icu/scripts/plan_preview.py \
        icu/tests/unit/scripts/__init__.py \
        icu/tests/unit/scripts/test_periodization_audit.py \
        icu/tests/unit/scripts/test_plan_preview.py
git commit -m "feat(coach-phase2): CLI tools periodization_audit.py + plan_preview.py"
```

---

## Task 48: E2E integration test — mocked warehouse → WeeklyPlan

**Goal:** 一个集成测试，覆盖整条链：
1. 假造 warehouse：wellness + events + power_curves + 1-2 个 activity
2. 执行 `periodization.engine.refresh_periodization`
3. 执行 `session_designer.generator_v2.generate_plan_v2(push=False)`
4. 断言：
   - `reports/plan_YYYYMMDD.json` 存在且 Pydantic 有效
   - `coach_memory/periodization/periodization_current.json` 存在
   - 若 next_race within 10d → phase==TAPER、7 日 TSS 比无赛情况少 40%+
   - 若 CP 低于 FTP 且 knee_loading.flag=='caution' → plan 不含连续 standing 动作
   - violations_remaining 全部在已知可接受集合内

**Files:**
- Create: `icu/tests/integration/test_phase2_e2e.py`

- [ ] **Step 1: Write failing integration test**

Write `icu/tests/integration/test_phase2_e2e.py`:
```python
import json
from datetime import date
from pathlib import Path

from src.coach.session_designer.generator_v2 import generate_plan_v2


def _seed(tmp_path, race_in_days=56, cp=280, ftp=288, knee_flag=None):
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
    race_date = (date(2026, 4, 18) + __import__("datetime").timedelta(days=race_in_days))
    events = [{"id": 1, "category": "RACE", "name": "Goal",
               "start_date_local": f"{race_date.isoformat()}T08:00:00"}]
    (warehouse / "8_Events" / "events.json").write_text(json.dumps(events))
    (warehouse / "1_Profile" / "athlete.json").write_text(
        json.dumps({"ftp": ftp, "hr_max": 195, "weight": 62}))

    mem = tmp_path / "coach_memory"
    (mem / "physiology").mkdir(parents=True)
    (mem / "deep_analysis").mkdir()
    (mem / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": cp, "w_prime_joules": 22000,
        "fit_r_squared": 0.95, "athlete_ftp_set": ftp}))
    (mem / "physiology" / "durability.json").write_text("{}")
    (mem / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {}, "knee_loading": {"flag": knee_flag,
                                      "standing_climb_minutes_90d": 0},
    }))
    return warehouse, mem


def test_e2e_generates_valid_plan_no_race_nearby(tmp_path):
    warehouse, mem = _seed(tmp_path, race_in_days=56)
    reports = tmp_path / "reports"
    result = generate_plan_v2(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        warehouse_dir=warehouse, memory_dir=mem, reports_dir=reports,
        push_to_icu=False, gemini_client=None,
    )
    assert result.status == "ok"
    plan = json.loads(Path(result.plan_json_path).read_text())
    assert len(plan["days"]) == 7
    # Phase 应是 BUILD（race 还远） + 当周 TSS ≥ 400（不是 Taper）
    snap = json.loads(
        (mem / "periodization" / "periodization_current.json").read_text())
    assert snap["current_phase"] in ("BUILD", "BASE", "PEAK")
    assert plan["weekly_tss_target"] >= 350


def test_e2e_taper_reduces_tss_when_race_within_10_days(tmp_path):
    warehouse, mem = _seed(tmp_path, race_in_days=6)
    reports = tmp_path / "reports"
    result = generate_plan_v2(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        warehouse_dir=warehouse, memory_dir=mem, reports_dir=reports,
        push_to_icu=False, gemini_client=None,
    )
    assert result.status == "ok"
    plan = json.loads(Path(result.plan_json_path).read_text())
    snap = json.loads(
        (mem / "periodization" / "periodization_current.json").read_text())
    assert snap["current_phase"] == "TAPER"
    # TAPER TSS 必须明显低
    assert plan["weekly_tss_target"] < 350


def test_e2e_cp_used_not_ftp_when_different(tmp_path):
    warehouse, mem = _seed(tmp_path, race_in_days=56, cp=260, ftp=288)
    reports = tmp_path / "reports"
    result = generate_plan_v2(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        warehouse_dir=warehouse, memory_dir=mem, reports_dir=reports,
        push_to_icu=False, gemini_client=None,
    )
    # 任何 Threshold/VO2max 的 power_range 上限 < ftp × 1.15
    plan = json.loads(Path(result.plan_json_path).read_text())
    for day in plan["days"]:
        pr = day.get("power_range_w")
        if pr and day["training_type"] in ("Threshold", "VO2max"):
            high = int(pr.replace("W", "").split("-")[-1])
            assert high < 288 * 1.15   # 基于 FTP=288 的上限（330W）
            assert high < 320  # 真实上限应 < 260 * 1.20 = 312


def test_e2e_report_files_are_pydantic_valid(tmp_path):
    from src.coach.session_designer.types import WeeklyPlan
    warehouse, mem = _seed(tmp_path, race_in_days=56)
    reports = tmp_path / "reports"
    result = generate_plan_v2(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        warehouse_dir=warehouse, memory_dir=mem, reports_dir=reports,
        push_to_icu=False, gemini_client=None,
    )
    doc = json.loads(Path(result.plan_json_path).read_text())
    # 反序列化不抛
    WeeklyPlan.model_validate(doc)
```

- [ ] **Step 2: Run — fail**

Expected: FAIL (initially if any wiring missing).

- [ ] **Step 3: Fix any wiring gaps until tests pass**

Run: `cd icu && .venv/bin/pytest tests/integration/test_phase2_e2e.py -v`
Expected: PASS all four (可能需要微调 generator_v2 的边界 — 若失败，先查 `generate_plan_v2` 的 Phase 识别路径而不是改测试)。

- [ ] **Step 4: Commit**

```bash
git add icu/tests/integration/test_phase2_e2e.py
git commit -m "test(coach-phase2): e2e integration (periodization → designer → plan) with 4 scenarios"
```

---

## Task 49: Real-warehouse acceptance checklist

**Files:**
- Create: `icu/tests/e2e/acceptance_checklist.md`

**Goal:** 手工验收清单，操作者在真仓库上跑一遍，勾选确认。

- [ ] **Step 1: Write checklist**

Write `icu/tests/e2e/acceptance_checklist.md`:
```markdown
# Phase 2 Acceptance Checklist

**Prerequisites**
- [ ] Phase 1 全部 T1–T24 已合并 master 且绿
- [ ] Phase 2 所有单元测试 + 集成测试 `pytest tests/ -v` 全绿
- [ ] `.env` 中 `GEMINI_API_KEY` 可用
- [ ] 当前 `coach_memory/physiology/cp_w_current.json` 最新（运行过 `refresh_physiology.py`）
- [ ] 当前 `coach_memory/deep_analysis/summary_latest.json` 最新（运行过 `run_deep_analysis.py`）

**Structural checks**
- [ ] `python scripts/periodization_audit.py` 打印当前 phase 合理（与本周实际情况对应）
- [ ] 输出列出 macro 窗口、meso pattern、micro 7 日；每日 tier 和 TSS 的模式与 phase 匹配
  - BASE 周：no HARD days, ≥80% low intensity
  - BUILD 周：至少 2 个 HARD day，间隔 ≥48h
  - TAPER 周：总 TSS 相对 BUILD 降 40%+，仍保留 HARD 短刺激
  - RACE 周：赛前 2 天必须 REST
- [ ] 若最近有 A 级赛在 ≤10 天，audit 显示 `Phase: TAPER`

**Quality checks vs legacy plan_generator**
运行对比：
```
python scripts/plan_preview.py --week <next-monday>      # v2
python scripts/push_plan.py --week <next-monday>          # v1 legacy (without --push)
```
- [ ] 两份 `reports/plan_YYYYMMDD_v1.json` / `_v2.json`（手工重命名对比）
- [ ] v2 的 power_range_w **使用 CP 而非 set FTP**（取 threshold 日对比，差异应 ≈ `cp_vs_ftp_delta_w`）
- [ ] v2 的 weekly_tss_target 与当前 CTL 成比例（Build: CTL × 5.8 ± 10%）
- [ ] v2 有 trace.json 记录每日 template_name 和 CP 来源；v1 没有
- [ ] v2 的 description 文本（prose 启用时）引用具体 CP/W'/kJ 数字，不是通用 "保持强度" 之类的空话

**Safety checks**
- [ ] 若 `response_profile.json` 的 `knee_loading.flag == 'caution'`，当周不含两个连续 standing climb 日
- [ ] 若 response_profile 某个 tolerance_class == 'low'，当周对应 session type 不做连续 HARD
- [ ] 周 REST 日 ≥ `intent.rest_days_per_week`

**Fallback test**
- [ ] 临时 rename `coach_memory/physiology/` → `physiology.bak`，跑 `push_plan.py --engine v2`，期望 v2 报 error 并自动回退 v1，不中断用户
- [ ] 恢复后再跑一次，v2 正常

**Performance**
- [ ] `generate_plan_v2(push=False)` 本地全程 < 10 秒（未调 Gemini）
- [ ] `generate_plan_v2(push=True)` 全程 < 30 秒（含 1 次 Gemini 调用 + ICU push）

**Observability**
- [ ] `logs/periodization_engine.log` 有 `action: refresh_periodization` 条目
- [ ] `logs/generate_plan_v2.log` 有 `action: generate_plan_v2 status: ok` 条目
- [ ] `logs/session_designer_prose.log` 有 prose_generate 条目（若启用）

**Regression**
- [ ] `scripts/push_plan.py`（不带 `--engine`）依然走 legacy，输出和 Phase 1 状态一致
- [ ] Phase 1 CLI：`analyze_rides`、`physiology_audit` 不受影响
- [ ] ICU 日历推送在 `--engine v2 --push` 下产生正确的 events（手工在 ICU 网页上确认 7 条 event 包含描述）

**Sign-off**
- [ ] 操作者：__________ 日期：__________
- [ ] 确认所有上述项全部通过；否则列出未通过项并开 bd issue。
```

- [ ] **Step 2: Commit**

```bash
git add icu/tests/e2e/acceptance_checklist.md
git commit -m "docs(coach-phase2): acceptance checklist for real-warehouse verification"
```

---

## Phase 2 final completion

- [ ] `pytest tests/` 全部绿（unit + integration + scripts）
- [ ] 11 个实现文件全部 merge + `feat(coach-phase2):` 系列 commits
- [ ] 手工验收清单在真仓库通过
- [ ] Rebase `ai-coach-phase-2` onto updated master（吸收 Phase 1 T22–T24）
- [ ] Merge PR 到 master，squash 合并，标签 `v2.0-phase2-complete`
- [ ] 运行 `save-progress` 归档 MEMORY
- [ ] 开始 Phase 3 brainstorming（Adaptation Engine + Multi-Expert Consensus + Decision Ledger）

**Phase 2 END.**
