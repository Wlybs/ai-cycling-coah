# Phase 1 — Integration - sync tail, plan_generator, Coach Brief (Tasks 19-21)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 19: Integration — extend `sync_data.py` tail

**Files:**
- Modify: `icu/scripts/sync_data.py`
- Create: `icu/scripts/refresh_physiology.py`
- Create: `icu/scripts/run_deep_analysis.py`
- Create: `icu/tests/integration/test_sync_integration.py`

- [ ] **Step 1: Write failing integration test**

Write `icu/tests/integration/test_sync_integration.py`:
```python
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_refresh_physiology_script_is_callable_standalone():
    script = REPO / "scripts" / "refresh_physiology.py"
    assert script.exists()


@pytest.mark.integration
def test_run_deep_analysis_script_is_callable():
    script = REPO / "scripts" / "run_deep_analysis.py"
    assert script.exists()


@pytest.mark.integration
def test_sync_data_imports_new_steps():
    sd = (REPO / "scripts" / "sync_data.py").read_text()
    assert "refresh_physiology" in sd
    assert "run_deep_analysis" in sd
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement `refresh_physiology.py`**

Write `icu/scripts/refresh_physiology.py`:
```python
"""Standalone physiology refresher. Called by sync_data.py or directly for debugging."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.physiology.refresher import refresh_all


def _load_activities(warehouse):
    out = []
    detail_dir = warehouse / "5_Activities_Detail"
    if not detail_dir.exists():
        return out
    for f in sorted(detail_dir.glob("*/activity.json")):
        try:
            doc = json.loads(f.read_text())
            streams_file = f.parent / "streams.json"
            if streams_file.exists():
                streams = json.loads(streams_file.read_text())
                doc["power_stream"] = streams.get("watts") or streams.get("power") or []
            out.append(doc)
        except Exception as exc:
            print(f"skip {f}: {exc}", file=sys.stderr)
    return out


def _load_wellness(warehouse):
    out = {}
    w = warehouse / "2_Wellness"
    if not w.exists():
        return out
    for f in w.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict) and "date" in d:
                out[d["date"]] = d
            elif isinstance(d, list):
                for rec in d:
                    out[rec.get("id") or rec.get("date")] = rec
        except Exception:
            pass
    return out


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    activities = _load_activities(warehouse)
    wellness = _load_wellness(warehouse)
    result = refresh_all(warehouse, memory, activities, wellness)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Implement `run_deep_analysis.py`**

Write `icu/scripts/run_deep_analysis.py`:
```python
"""Runs deep analysis for newly synced activities. Called by sync_data.py."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.deep_analyzer.orchestrator import analyze_new


def _load_activity_list(warehouse):
    path = warehouse / "4_Activities_List" / "activities.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _load_streams_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / activity_id / "streams.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
    return loader


def _load_wbal_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / f"{activity_id}_wbalance.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
    return loader


def _load_physiology(memory):
    phys_dir = memory / "physiology"
    bundle = {"cp_w": None, "durability": None, "response": None}
    for key, fname in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = phys_dir / fname
        if p.exists():
            bundle[key] = json.loads(p.read_text())
    return bundle


def _make_client():
    load_dotenv(REPO / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    output_dir = memory / "deep_analysis"
    client = _make_client()
    athlete = json.loads((warehouse / "1_Profile" / "athlete.json").read_text()) if (warehouse / "1_Profile" / "athlete.json").exists() else {}
    activities = _load_activity_list(warehouse)
    physiology = _load_physiology(memory)

    results = analyze_new(
        activities_iter=activities,
        physiology_bundle=physiology,
        athlete=athlete,
        output_dir=output_dir,
        client=client,
        load_streams=_load_streams_for(warehouse),
        load_wbal=_load_wbal_for(warehouse),
        history_for=lambda act: [a for a in activities if a.get("id") != act["id"]][:20],
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Modify `sync_data.py` to call the two new scripts**

Edit `icu/scripts/sync_data.py` — append after the existing `run_script("build_memory.py")` line (before the failures summary print):

```python
    # 8. Phase 1 — physiology refresh (soft-fail)
    run_script("refresh_physiology.py")

    # 9. Phase 1 — deep analysis (soft-fail)
    run_script("run_deep_analysis.py")

    # 10. Phase 1 — Coach Brief update (soft-fail)
    run_script("update_coach_brief.py")
```

The existing `run_script` helper already catches `CalledProcessError` and tracks failures without halting the pipeline — that is our soft-fail mechanism.

- [ ] **Step 6: Run integration test**

Run: `cd icu && .venv/bin/pytest tests/integration/test_sync_integration.py -v`
Expected: PASS (update_coach_brief.py existence will fail until Task 21 — move that assertion into Task 21's test).

- [ ] **Step 7: Commit**

```bash
git add icu/scripts/refresh_physiology.py icu/scripts/run_deep_analysis.py icu/scripts/sync_data.py icu/tests/integration/test_sync_integration.py
git commit -m "feat(coach): wire Phase 1 physiology+deep-analysis into sync_data"
```

---

## Task 20: `plan_generator.py` prompt injection

**Files:**
- Create: `icu/src/coach/phase1_injection.py`
- Modify: `icu/src/coach/plan_generator.py` (lines 245–260 region — prompt assembly)
- Create: `icu/tests/unit/coach/test_phase1_injection.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/coach/test_phase1_injection.py`:
```python
import json
from pathlib import Path

from src.coach.phase1_injection import inject_phase1_context


def test_no_files_returns_base_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = "BASE PROMPT"
    assert inject_phase1_context(base, base_dir=tmp_path) == base


def test_injects_cp_w_and_hints(tmp_path):
    (tmp_path / "coach_memory" / "physiology").mkdir(parents=True)
    (tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 295, "w_prime_joules": 22500, "fit_r_squared": 0.97,
        "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 7
    }))
    (tmp_path / "coach_memory" / "deep_analysis").mkdir()
    (tmp_path / "coach_memory" / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.72, "progression_flag": "progression",
        "next_plan_hints": ["下次延长恢复时长", "提高 VO2max 刺激下限"],
        "knee_flag": None,
    }))
    out = inject_phase1_context("BASE PROMPT", base_dir=tmp_path)
    assert "BASE PROMPT" in out
    assert "个人 CP 295W" in out or "CP: 295" in out
    assert "下次延长恢复时长" in out
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement injection helper**

Write `icu/src/coach/phase1_injection.py`:
```python
import json
from pathlib import Path


def _load_json_safe(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tail_reports(dir_: Path, n: int = 5) -> list[str]:
    if not dir_.exists():
        return []
    md_files = sorted(dir_.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    return [f.read_text(encoding="utf-8") for f in md_files]


def render_phase1_context_block(physiology, durability, response, summary, recent_reports) -> str:
    lines = ["\n---\n## Phase 1 个性化体能注入（由确定性模型生成）\n"]

    if physiology:
        cp = physiology.get("cp_watts")
        wp = physiology.get("w_prime_joules")
        r2 = physiology.get("fit_r_squared")
        ftp = physiology.get("athlete_ftp_set")
        delta = physiology.get("cp_vs_ftp_delta_w")
        lines.append(f"- **个人 CP {cp}W / W' {wp}J**（拟合 R²={r2}）；与设定 FTP {ftp}W 偏差 {delta:+d}W。规划强度时以 **CP 而非 FTP** 作为阈值。")

    if durability and durability.get("decay_rate_pct_per_1000kj"):
        decay = durability["decay_rate_pct_per_1000kj"]
        lines.append(f"- **耐力衰减率**：60s 档 {decay.get('60s', 0)}%/1000kJ，5min 档 {decay.get('300s', 0)}%/1000kJ。长距离/赛前补能策略按此比例推。")

    if response and response.get("types"):
        parts = []
        for t, stats in response["types"].items():
            parts.append(f"{t}={stats['tolerance_class']}")
        lines.append(f"- **各类刺激耐受画像**：{', '.join(parts)}。对 `low` 类刺激延长恢复，对 `high` 类可提高频率/强度。")
        knee = response.get("knee_loading", {})
        if knee.get("flag"):
            lines.append(f"- **右膝负荷标记**：{knee['flag']}（90 日内摇车 {knee.get('standing_climb_minutes_90d', 0)} 分钟）。避免连续多天出现摇车爆发动作。")

    if summary:
        lines.append(f"- **最近一次深度分析**：{summary.get('headline_verdict', '')}（stimulus={summary.get('stimulus_score')}，progression={summary.get('progression_flag')}）。")
        if summary.get("next_plan_hints"):
            lines.append("  - 执行下列 hints：")
            for h in summary["next_plan_hints"]:
                lines.append(f"    * {h}")

    if recent_reports:
        lines.append("\n### 最近 5 篇深度分析摘要（下次怎么办段已由系统抽取）")
        for md in recent_reports:
            if "## 下次怎么办" in md:
                idx = md.index("## 下次怎么办")
                end = md.find("##", idx + 3)
                block = md[idx: end if end > 0 else len(md)].strip()
                lines.append(block + "\n")

    lines.append(
        "\n**硬规则**：若最近 3 次 stimulus_score 均 < 0.4，说明存在系统性 under-prescription — "
        "把周 TSS 目标提高到历史 90 天峰值的 90%。默认一周 1 天**完全休息**（不安排恢复骑），除非 response.high 允许。\n"
    )
    return "\n".join(lines)


def inject_phase1_context(base_prompt: str, base_dir: Path | None = None) -> str:
    base_dir = Path(base_dir) if base_dir else Path.cwd()
    physiology = _load_json_safe(base_dir / "coach_memory" / "physiology" / "cp_w_current.json")
    durability = _load_json_safe(base_dir / "coach_memory" / "physiology" / "durability.json")
    response = _load_json_safe(base_dir / "coach_memory" / "physiology" / "response_profile.json")
    summary = _load_json_safe(base_dir / "coach_memory" / "deep_analysis" / "summary_latest.json")
    recent = _tail_reports(base_dir / "coach_memory" / "deep_analysis", n=5)

    if not any([physiology, durability, response, summary]):
        return base_prompt

    return base_prompt + render_phase1_context_block(physiology, durability, response, summary, recent)
```

- [ ] **Step 4: Wire into `plan_generator.py`**

Edit `icu/src/coach/plan_generator.py` — at the top add:
```python
from src.coach.phase1_injection import inject_phase1_context
```

Then in `generate_plan()` (around line 253), change the prompt assembly from:
```python
    prompt = f"""{system_prompt}
```
to wrap the final prompt before the `client.models.generate_content` call:
```python
    prompt = inject_phase1_context(prompt)
```
Place this `inject_phase1_context` call on the line immediately before the existing `genai` / `generate_content` call inside `generate_plan`.

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/coach/test_phase1_injection.py -v`

- [ ] **Step 6: Commit**

```bash
git add icu/src/coach/phase1_injection.py icu/src/coach/plan_generator.py icu/tests/unit/coach/test_phase1_injection.py
git commit -m "feat(coach): inject Phase 1 physiology context into plan_generator prompt"
```

---

## Task 21: Coach Brief (GEMINI.md) updater

**Files:**
- Create: `icu/scripts/update_coach_brief.py`
- Create: `icu/src/coach/brief_updater.py`
- Create: `icu/tests/unit/coach/test_brief_updater.py`
- Modify: `icu/GEMINI.md` (insert markers)

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/coach/test_brief_updater.py`:
```python
import json
from pathlib import Path

from src.coach.brief_updater import update_brief, BEGIN, END


def test_inserts_block_between_markers(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(f"intro\n{BEGIN}\nold\n{END}\ntail\n")

    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.55, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": "watch",
    }))
    (mem / "physiology").mkdir()
    (mem / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 292, "w_prime_joules": 21800, "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 4,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    content = gemini.read_text()
    assert "intro" in content and "tail" in content
    assert "起步冒进" in content
    assert "CP 292" in content or "CP: 292" in content
    assert content.count(BEGIN) == 1 and content.count(END) == 1


def test_appends_markers_if_absent(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text("no markers yet\n")
    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": [], "headline_verdict": "x",
        "stimulus_score": 0.5, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": None,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    c = gemini.read_text()
    assert BEGIN in c and END in c
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement updater module**

Write `icu/src/coach/brief_updater.py`:
```python
import json
import re
from pathlib import Path

BEGIN = "<!-- BEGIN: phase1_coach_brief -->"
END = "<!-- END: phase1_coach_brief -->"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _recent_stimulus_trend(memory_dir: Path, n: int = 3) -> list[float]:
    # Scan trace files, pick last n by mtime, read their summaries indirectly via the trace itself
    da = memory_dir / "deep_analysis"
    if not da.exists():
        return []
    traces = sorted(da.glob("*.trace.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    scores = []
    for t in traces:
        try:
            doc = json.loads(t.read_text())
            # Summary was written as <id>.md sibling; reconstruct stimulus from findings
            # For Coach Brief we just need the presence; score comes from summary_latest.json
        except Exception:
            pass
    # Read summary_latest's score as the most recent anchor; full history requires summary archive — deferred
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    if summary:
        scores.append(summary.get("stimulus_score", 0.0))
    return scores


def render_brief(physiology, summary, recent_scores, response_knee) -> str:
    lines = [BEGIN]
    lines.append("## 当前画像（自动更新，勿手动编辑本段）")
    if physiology:
        lines.append(f"- 个人 CP {physiology['cp_watts']}W / W' {physiology['w_prime_joules']}J"
                     f"（vs 设定 FTP {physiology['athlete_ftp_set']}W，差 {physiology['cp_vs_ftp_delta_w']:+d}W）")
    if summary:
        lines.append(f"- 最近深度分析：{summary['headline_verdict']}（stimulus={summary['stimulus_score']}, {summary['progression_flag']}）")
    if recent_scores:
        lines.append(f"- 近 {len(recent_scores)} 次 stimulus 均值 = {round(sum(recent_scores)/len(recent_scores), 2)}")
    if response_knee:
        lines.append(f"- 右膝负荷标记：{response_knee}")
    lines.append(END)
    return "\n".join(lines)


def update_brief(gemini_path: Path, memory_dir: Path) -> None:
    physiology = _load(memory_dir / "physiology" / "cp_w_current.json")
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    response = _load(memory_dir / "physiology" / "response_profile.json") or {}
    knee_flag = response.get("knee_loading", {}).get("flag") if isinstance(response, dict) else None
    scores = _recent_stimulus_trend(memory_dir)

    block = render_brief(physiology, summary, scores, knee_flag)

    content = gemini_path.read_text(encoding="utf-8") if gemini_path.exists() else ""
    if BEGIN in content and END in content:
        new = re.sub(
            rf"{re.escape(BEGIN)}.*?{re.escape(END)}",
            block,
            content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        new = content.rstrip() + "\n\n" + block + "\n"
    gemini_path.write_text(new, encoding="utf-8")
```

- [ ] **Step 4: Implement script**

Write `icu/scripts/update_coach_brief.py`:
```python
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.brief_updater import update_brief


def main():
    update_brief(gemini_path=REPO / "GEMINI.md", memory_dir=REPO / "coach_memory")
    print("coach brief updated")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add markers to GEMINI.md**

Edit `icu/GEMINI.md` — append at the end (unless already present):
```
<!-- BEGIN: phase1_coach_brief -->
<!-- END: phase1_coach_brief -->
```

- [ ] **Step 6: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/coach/test_brief_updater.py -v`

- [ ] **Step 7: Commit**

```bash
git add icu/src/coach/brief_updater.py icu/scripts/update_coach_brief.py icu/GEMINI.md icu/tests/unit/coach/test_brief_updater.py
git commit -m "feat(coach): auto-update GEMINI.md Coach Brief from Phase 1 outputs"
```

---

