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


def test_analyze_one_writes_report_and_trace(tmp_path):
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
