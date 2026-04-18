import json

from src.coach.deep_analyzer.orchestrator import analyze_one


def test_analyze_one_writes_prompt_and_trace(tmp_path):
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
    )

    prompt_path = tmp_path / "i1.prompt.md"
    trace_path = tmp_path / "i1.trace.json"
    summary_path = tmp_path / "summary_latest.json"

    assert prompt_path.exists(), "analyze_one must write <id>.prompt.md for manual LLM paste"
    assert trace_path.exists()
    assert summary_path.exists()

    # Legacy Gemini-generated file must NOT be produced any longer.
    assert not (tmp_path / "i1.md").exists()

    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert '"activity_id": "i1"' in prompt_text
    assert "输入 JSON：" in prompt_text

    trace = json.loads(trace_path.read_text())
    assert "features" in trace and "relevance" in trace and "activated" in trace
    assert result["status"] == "ok"
    assert result["prompt_path"].endswith("i1.prompt.md")


def test_analyze_one_has_no_client_parameter(tmp_path):
    """Regression: the `client` kwarg was removed when the pipeline went
    API-free. Calling with it must raise TypeError."""
    import pytest

    activity = {"id": "iX", "date": "2026-04-15", "type": "endurance",
                "duration_s": 1800, "np_watts": 200, "tss": 30, "if": 0.7, "total_kj": 300}
    with pytest.raises(TypeError):
        analyze_one(
            activity=activity, streams=None, wbal_series=None,
            physiology_bundle={"cp_w": {}, "durability": {}, "response": {}},
            athlete={}, history=[], output_dir=tmp_path,
            client=object(),  # type: ignore[call-arg]
        )
