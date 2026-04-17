from src.coach.deep_analyzer.sub_analyzers.durability import analyze


def test_below_baseline_flags_deficit():
    personal = {
        "fresh_mmp_w": {"300s": 350},
        "fatigued_mmp_w": {
            "1500kj": {"300s": 330},
            "2000kj": {"300s": 320},
            "2500kj": {"300s": 310},
        },
    }
    ride = {"id": "iA", "total_kj": 2600, "fatigued_mmp_w": {"1500kj": {"300s": 300}}}
    findings = analyze(ride, personal_curve=personal)
    assert findings.metrics["durability_deficit_pct_300s"] > 0
    assert "deficit" in str(findings.metrics).lower() or findings.verdict == "疲劳衰退显著"


def test_above_baseline_shows_bonus():
    personal = {
        "fresh_mmp_w": {"300s": 330},
        "fatigued_mmp_w": {
            "1500kj": {"300s": 310}, "2000kj": {"300s": 300}, "2500kj": {"300s": 290},
        },
    }
    ride = {"id": "iB", "total_kj": 2800, "fatigued_mmp_w": {"2500kj": {"300s": 310}}}
    findings = analyze(ride, personal_curve=personal)
    assert findings.verdict == "爬坡表现超预期"


def test_short_ride_returns_insufficient():
    ride = {"id": "iC", "total_kj": 400, "fatigued_mmp_w": {}}
    findings = analyze(ride, personal_curve={"fresh_mmp_w": {"300s": 330}, "fatigued_mmp_w": {}})
    assert findings.verdict == "数据不足"
