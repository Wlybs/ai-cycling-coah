# Phase 1 — Report composer and deep analyzer orchestrator (Tasks 17-18)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 17: Report composer (Gemini prose renderer)

**Files:**
- Create: `icu/src/coach/deep_analyzer/report_composer.py`
- Create: `icu/src/coach/deep_analyzer/prompts/report_system.md`
- Create: `icu/tests/unit/deep_analyzer/test_report_composer.py`

- [ ] **Step 1: Write failing test with mocked Gemini**

Write `icu/tests/unit/deep_analyzer/test_report_composer.py`:
```python
from unittest.mock import MagicMock

from src.coach.deep_analyzer.report_composer import compose, validate_report
from src.coach.deep_analyzer.types import Findings


FAKE_REPORT = """# 活动 i123 深度分析 — 2026-04-15 vo2max

**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ

## 今日结论
刺激对位但 W' 管理偏激进，下周建议延长恢复区间。

## 关键发现

### 1. 节奏稳定但末段略掉
> 证据: 前1/3 320W 对比后1/3 280W，差值 +12.5%
- 结论: 典型起步冒进，可能吃掉后段储备
- 联系画像: Type II 占优，起步爆点是优势但需要配速控制

### 2. W' 债务过度
> 证据: 最低 W'bal 8%，低于15%累计 240s
- 结论: 已越过安全线，累积恢复不充分
- 联系画像: 62kg轻量运动员，W' 池小，债务管理对抗周容错率更低

## 下次怎么办
1. 将 VO2max 间歇组间休息延长到 3:1
2. 每周一次纯休息替代恢复骑

## 附:本次激活的分析维度
- [x] pacing
- [x] w_balance
- [ ] durability
- [ ] climbing
- [x] target_align
- [x] historical_cmp
"""


def test_validate_accepts_well_formed_report():
    ok, reasons = validate_report(FAKE_REPORT)
    assert ok, reasons


def test_validate_rejects_missing_evidence():
    bad = FAKE_REPORT.replace("> 证据:", "> Not evidence:", 1)
    ok, reasons = validate_report(bad)
    assert not ok


def test_compose_calls_gemini_and_returns_markdown():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = FAKE_REPORT
    fake_client.models.generate_content.return_value = fake_response

    activity = {"id": "i123", "date": "2026-04-15", "type": "vo2max",
                "duration_s": 3600, "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810}
    findings = [Findings(analyzer="pacing", metrics={}, verdict="起步冒进", evidence=[("x", "y")])]

    md = compose(
        activity=activity,
        findings=findings,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "right ACL post-op"},
        physiology={"cp_watts": 285, "w_prime_joules": 22000},
        activated_set={"pacing", "w_balance"},
        client=fake_client,
    )
    assert "今日结论" in md
    fake_client.models.generate_content.assert_called_once()
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Write the system prompt**

Write `icu/src/coach/deep_analyzer/prompts/report_system.md`:
```markdown
你是一位资深职业自行车教练，负责为精确的体能模型产出的发现撰写中文分析报告。**不得重复陈述 ICU 已经展示的原始指标（如 NP/IF/TSS 的数字本身）**——只输出解释和洞察。

严格遵守以下结构（禁止修改章节标题）：

# 活动 <id> 深度分析 — <date> <type>

**Session 概要** · 由系统一句话提供，原样照抄

## 今日结论
1-2 句话定性总结。

## 关键发现
对每一条发现使用：
### N. <主题>
> 证据: <逐字引用传入 findings 中的一条 evidence>
- 结论: <据此推断出的教练级解读>
- 联系画像: <把该发现与运动员画像 (62kg, Type II dominant, 右膝 ACL 术后) 联系起来>

## 下次怎么办
1-3 条下次训练的可执行建议（足以作为 plan_generator 输入）。

## 附:本次激活的分析维度
用 `- [x]` 标出本次激活的分析维度，`- [ ]` 标出未激活。

禁止：
- 重复原始指标（如“NP 为 285W，IF 0.95”——这些已在 Session 概要里）
- 空泛建议（“继续努力”“多休息”——必须具体到动作）
- 未配 `> 证据:` 行的结论
```

- [ ] **Step 4: Implement composer**

Write `icu/src/coach/deep_analyzer/report_composer.py`:
```python
import re
from pathlib import Path
from typing import Iterable

from .types import Findings

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "report_system.md"
SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _session_line(activity: dict) -> str:
    dur = int(activity.get("duration_s", 0) / 60)
    np = activity.get("np_watts", "-")
    tss = activity.get("tss", "-")
    if_val = activity.get("if", "-")
    kj = activity.get("total_kj", "-")
    return f"{dur} 分钟 · NP {np} W · TSS {tss} · IF {if_val} · {kj} kJ"


def _activated_checklist(activated_set) -> str:
    lines = []
    for name in SUB_ANALYZERS:
        mark = "x" if name in activated_set else " "
        lines.append(f"- [{mark}] {name}")
    return "\n".join(lines)


def validate_report(md: str) -> tuple[bool, list[str]]:
    reasons = []
    required_sections = ["## 今日结论", "## 关键发现", "## 下次怎么办"]
    for sec in required_sections:
        if sec not in md:
            reasons.append(f"missing section {sec}")
    findings_block = md.split("## 关键发现", 1)[-1].split("## 下次怎么办", 1)[0]
    subsections = re.findall(r"###\s+\d+\.", findings_block)
    for i, _ in enumerate(subsections):
        # each subsection must have a `> 证据:` line
        start = findings_block.find(f"### {i+1}.")
        end = findings_block.find(f"### {i+2}.") if i + 2 <= len(subsections) else len(findings_block)
        block = findings_block[start:end]
        if "> 证据:" not in block:
            reasons.append(f"finding {i+1} missing 证据 line")
    banned = re.search(r"NP 为 \d+W|IF 为 \d\.\d+", md)
    if banned:
        reasons.append(f"banned raw-metric restatement: {banned.group(0)}")
    return (len(reasons) == 0), reasons


def compose(
    activity: dict,
    findings: Iterable[Findings],
    athlete: dict,
    physiology: dict,
    activated_set: set[str],
    client,
    model: str = "gemini-2.5-flash",
) -> str:
    system_prompt = _load_system_prompt()
    findings_json = [f.model_dump() for f in findings]
    user_payload = {
        "activity_id": activity["id"],
        "date": activity.get("date", ""),
        "type": activity.get("type", ""),
        "session_line": _session_line(activity),
        "athlete": athlete,
        "physiology": physiology,
        "findings": findings_json,
        "activated_checklist": _activated_checklist(activated_set),
    }
    import json as _json
    payload_text = _json.dumps(user_payload, ensure_ascii=False, indent=2)

    prompt = system_prompt + "\n\n---\n\n输入 JSON：\n```json\n" + payload_text + "\n```"

    response = client.models.generate_content(model=model, contents=prompt)
    md = response.text
    return md
```

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/deep_analyzer/test_report_composer.py -v`

- [ ] **Step 6: Commit**

```bash
git add icu/src/coach/deep_analyzer/report_composer.py icu/src/coach/deep_analyzer/prompts/report_system.md icu/tests/unit/deep_analyzer/test_report_composer.py
git commit -m "feat(coach): add Gemini-backed report composer with structural validator"
```

---

## Task 18: Deep analyzer orchestrator

**Files:**
- Create: `icu/src/coach/deep_analyzer/orchestrator.py`
- Create: `icu/tests/unit/deep_analyzer/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_orchestrator.py`:
```python
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.coach.deep_analyzer.orchestrator import analyze_one


def _fake_report():
    return (
        "# 活动 i1 深度分析 — 2026-04-15 vo2max\n\n"
        "**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ\n\n"
        "## 今日结论\n刺激到位但 W' 债务偏深。\n\n"
        "## 关键发现\n### 1. 节奏问题\n> 证据: 前后段差 +12%\n- 结论: 起步冒进\n- 联系画像: Type II 优势但需配速\n\n"
        "## 下次怎么办\n1. 延长组间休息\n\n"
        "## 附:本次激活的分析维度\n- [x] pacing\n- [ ] durability\n"
    )


def test_analyze_one_writes_report_and_trace(tmp_path, monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=_fake_report())

    activity = {
        "id": "i1", "date": "2026-04-15", "type": "vo2max", "duration_s": 3600,
        "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810,
        "laps": [
            {"lap_index": 0, "type": "work", "duration_s": 240, "avg_power": 320, "np_power": 330, "if": 1.10},
            {"lap_index": 1, "type": "recovery", "duration_s": 120, "avg_power": 180, "if": 0.64},
        ],
        "planned_type": "vo2max",
    }
    physiology_bundle = {
        "cp_w": {"cp_watts": 285, "w_prime_joules": 22000},
        "durability": {},
        "response": {},
    }

    result = analyze_one(
        activity=activity,
        streams=None,
        wbal_series=None,
        physiology_bundle=physiology_bundle,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "ACL post-op"},
        history=[],
        output_dir=tmp_path,
        client=fake_client,
    )

    md_path = tmp_path / "i1.md"
    trace_path = tmp_path / "i1.trace.json"
    assert md_path.exists() and trace_path.exists()
    trace = json.loads(trace_path.read_text())
    assert "features" in trace and "relevance" in trace and "activated" in trace
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/orchestrator.py`:
```python
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from . import feature_detector, router, report_composer
from .sub_analyzers import pacing, w_balance, durability, climbing, target_align, historical_cmp
from .types import SummaryLatest, StateFile

LOG = get_logger("deep_analyzer")
SUB_FUNCS = {
    "pacing": lambda act, streams, wbal, phys, hist: pacing.analyze(act, physiology=phys),
    "w_balance": lambda act, streams, wbal, phys, hist: w_balance.analyze(act, physiology=phys, wbal_series=wbal),
    "durability": lambda act, streams, wbal, phys, hist: durability.analyze(act, personal_curve=phys.get("durability") if phys else None),
    "climbing": lambda act, streams, wbal, phys, hist: climbing.analyze(act, streams=streams or {}, physiology=phys),
    "target_align": lambda act, streams, wbal, phys, hist: target_align.analyze(act, physiology=phys),
    "historical_cmp": lambda act, streams, wbal, phys, hist: historical_cmp.analyze(act, history=hist or []),
}


def _stimulus_score(findings_list) -> float:
    verdicts = [f.verdict for f in findings_list]
    score = 0.5
    if "命中" in verdicts:
        score += 0.15
    if "W' 管理得当" in verdicts:
        score += 0.1
    if "过度依赖 W' 债务" in verdicts or "后段崩盘" in verdicts:
        score -= 0.2
    if "进步" in verdicts:
        score += 0.1
    if "退步" in verdicts:
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 2)


def _progression_flag(findings_list) -> str:
    for f in findings_list:
        if f.analyzer == "historical_cmp":
            if f.verdict == "退步":
                return "regression_severe" if f.metrics.get("confidence") == "high" else "regression_mild"
            if f.verdict == "进步":
                return "progression"
            if f.verdict == "持平":
                return "flat"
    return "flat"


def _next_plan_hints(findings_list) -> list[str]:
    hints = []
    for f in findings_list:
        if f.verdict == "过度依赖 W' 债务":
            hints.append("下次间歇延长恢复时长至 3:1 以保护 W' 恢复")
        if f.verdict == "起步冒进":
            hints.append("下次以目标功率下限起始，前两组压住")
        if f.verdict == "刺激错配" and f.metrics.get("under_prescription_flag"):
            hints.append("连续多次未达刺激——教练需提高目标区间下限")
    return hints


def analyze_one(
    activity: dict,
    streams: Optional[dict],
    wbal_series: Optional[dict],
    physiology_bundle: dict,
    athlete: dict,
    history: list,
    output_dir: Path,
    client,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    physiology_flat = {}
    cp_w = physiology_bundle.get("cp_w") or {}
    physiology_flat.update(cp_w)
    physiology_flat["durability"] = physiology_bundle.get("durability")
    physiology_flat["response"] = physiology_bundle.get("response")
    if wbal_series:
        physiology_flat["min_w_bal_pct"] = wbal_series.get("min_w_bal_pct")

    features = feature_detector.detect_features(activity, streams, physiology_flat, athlete)
    relevance = router.route(features)
    activated = {name for name, score in relevance.items() if score >= 0.5}

    findings_list = []
    for name in activated:
        try:
            findings_list.append(SUB_FUNCS[name](activity, streams, wbal_series, physiology_flat, history))
        except Exception as e:
            LOG.event(action=f"sub_{name}", activity_id=activity["id"], status="error", error=str(e))

    try:
        md = report_composer.compose(
            activity=activity,
            findings=findings_list,
            athlete=athlete,
            physiology=physiology_flat,
            activated_set=activated,
            client=client,
        )
    except Exception as e:
        LOG.event(action="compose", activity_id=activity["id"], status="error", error=str(e))
        (output_dir / f"{activity['id']}.raw.json").write_text(
            json.dumps([f.model_dump() for f in findings_list], ensure_ascii=False, indent=2)
        )
        return {"status": "report_failed", "error": str(e)}

    (output_dir / f"{activity['id']}.md").write_text(md, encoding="utf-8")
    trace = {
        "features": features.model_dump(),
        "relevance": relevance,
        "activated": sorted(activated),
        "findings": [f.model_dump() for f in findings_list],
    }
    (output_dir / f"{activity['id']}.trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))

    headline = next((f.verdict for f in findings_list if f.analyzer in ("pacing", "target_align", "historical_cmp")), "分析完成")
    summary = SummaryLatest(
        activity_id=activity["id"],
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        sub_analyzers_run=sorted(activated),
        headline_verdict=headline,
        stimulus_score=_stimulus_score(findings_list),
        progression_flag=_progression_flag(findings_list),
        next_plan_hints=_next_plan_hints(findings_list),
        knee_flag=(physiology_bundle.get("response") or {}).get("knee_loading", {}).get("flag"),
    )
    (output_dir / "summary_latest.json").write_text(summary.model_dump_json(indent=2))

    LOG.event(action="analyze_one", activity_id=activity["id"], duration_ms=int((time.monotonic() - t0) * 1000), status="ok")
    return {"status": "ok", "activated": sorted(activated)}


def analyze_new(
    activities_iter,
    physiology_bundle: dict,
    athlete: dict,
    output_dir: Path,
    client,
    load_streams=None,
    load_wbal=None,
    history_for=None,
) -> list:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "_state.json"
    state = StateFile.model_validate_json(state_path.read_text()) if state_path.exists() else StateFile()
    last_id = state.last_analyzed_activity_id
    results = []
    last_seen = last_id
    for activity in activities_iter:
        if last_id and activity["id"] == last_id:
            continue
        streams = load_streams(activity["id"]) if load_streams else None
        wbal = load_wbal(activity["id"]) if load_wbal else None
        history = history_for(activity) if history_for else []
        res = analyze_one(
            activity=activity,
            streams=streams,
            wbal_series=wbal,
            physiology_bundle=physiology_bundle,
            athlete=athlete,
            history=history,
            output_dir=output_dir,
            client=client,
        )
        results.append({"activity_id": activity["id"], **res})
        last_seen = activity["id"]
    state.last_analyzed_activity_id = last_seen
    state.last_analyzed_at = datetime.now(timezone.utc).isoformat()
    state_path.write_text(state.model_dump_json(indent=2))
    return results
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ -v`

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/orchestrator.py icu/tests/unit/deep_analyzer/test_orchestrator.py
git commit -m "feat(coach): add deep analyzer orchestrator with state tracking"
```

---

