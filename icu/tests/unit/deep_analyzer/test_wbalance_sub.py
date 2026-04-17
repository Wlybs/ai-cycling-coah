from src.coach.deep_analyzer.sub_analyzers.w_balance import analyze


def test_missing_wbal_returns_insufficient():
    findings = analyze({"id": "iX"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=None)
    assert findings.verdict == "数据不足"


def test_reads_lap_depletions():
    wbal = {
        "min_w_bal_pct": 22,
        "seconds_below_15pct": 0,
        "laps": [
            {"lap_index": 0, "type": "work", "depletion_pct": 30},
            {"lap_index": 1, "type": "recovery", "depletion_pct": -18},
            {"lap_index": 2, "type": "work", "depletion_pct": 40},
        ],
    }
    findings = analyze({"id": "iY"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=wbal)
    assert findings.metrics["max_lap_depletion_pct"] == 40
    assert findings.verdict in ("W' 管理得当", "W' 管理失衡", "过度依赖 W' 债务")


def test_over_leveraged_verdict():
    wbal = {
        "min_w_bal_pct": 8,
        "seconds_below_15pct": 240,
        "laps": [
            {"lap_index": 0, "type": "work", "depletion_pct": 70},
            {"lap_index": 1, "type": "recovery", "depletion_pct": -5},
        ],
    }
    findings = analyze({"id": "iZ"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=wbal)
    assert findings.verdict == "过度依赖 W' 债务"
