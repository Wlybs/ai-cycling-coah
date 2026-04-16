from src.coach.deep_analyzer.types import Features, Findings, SummaryLatest


def test_features_defaults_false():
    f = Features(duration_seconds=3600, total_kj=800)
    assert f.has_intervals is False
    assert f.heat_stress is False


def test_findings_evidence_tuple():
    f = Findings(
        analyzer="pacing",
        metrics={"vi_mean": 1.04},
        verdict="节奏平稳",
        evidence=[("前1/3与后1/3功率差 < 3%", "laps[0..3] vs laps[-3..]")],
    )
    assert f.evidence[0][0].startswith("前1/3")


def test_summary_latest_enum_progression():
    s = SummaryLatest(
        activity_id="i1",
        analyzed_at="2026-04-16T00:00:00Z",
        sub_analyzers_run=["pacing"],
        headline_verdict="节奏平稳",
        stimulus_score=0.62,
        progression_flag="progression",
        next_plan_hints=["保持当前强度"],
        knee_flag=None,
    )
    assert s.progression_flag == "progression"
