import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.coach.physiology.refresher import refresh_all
from src.coach.deep_analyzer.orchestrator import analyze_new

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "rides"


def _seed_warehouse(base: Path):
    (base / "icu_data_warehouse" / "3_PowerData").mkdir(parents=True)
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_90d.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1200, 780, 560, 450, 340, 310, 290],
    }))
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_all_time.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1389, 850, 600, 480, 360, 320, 295],
    }))
    (base / "icu_data_warehouse" / "1_Profile").mkdir(parents=True)
    (base / "icu_data_warehouse" / "1_Profile" / "athlete.json").write_text(json.dumps({
        "weight": 62, "ftp": 288, "hr_max": 195,
    }))


@pytest.mark.e2e
def test_full_phase1_pipeline_with_mocked_gemini(tmp_path):
    _seed_warehouse(tmp_path)
    activity = json.loads((FIXTURE_DIR / "interval_ride_synthetic.json").read_text())

    refresh_result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[{**activity, "power_stream": [300] * 3600}],
        wellness_by_date={},
    )
    assert refresh_result["cp_w"]["status"] == "ok"

    physiology_bundle = {
        "cp_w": json.loads((tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").read_text()),
        "durability": json.loads((tmp_path / "coach_memory" / "physiology" / "durability.json").read_text()),
        "response": None,
    }

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=(
        "# 活动 iE2E1 深度分析 — 2026-04-15 vo2max\n\n"
        "**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ\n\n"
        "## 今日结论\n刺激到位节奏平稳。\n\n"
        "## 关键发现\n### 1. 节奏稳定\n> 证据: 首末段差 <3%\n- 结论: 能按计划执行\n- 联系画像: Type II 优势，这类短间歇正是强项\n\n"
        "## 下次怎么办\n1. 保持强度提升刺激下限\n\n"
        "## 附:本次激活的分析维度\n- [x] pacing\n"
    ))

    out_dir = tmp_path / "coach_memory" / "deep_analysis"
    results = analyze_new(
        activities_iter=[activity],
        physiology_bundle=physiology_bundle,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "ACL post-op"},
        output_dir=out_dir,
        client=fake_client,
    )

    assert results[0]["status"] == "ok"
    assert (out_dir / "iE2E1.md").exists()
    assert (out_dir / "iE2E1.trace.json").exists()
    assert (out_dir / "summary_latest.json").exists()
    assert (out_dir / "_state.json").exists()
