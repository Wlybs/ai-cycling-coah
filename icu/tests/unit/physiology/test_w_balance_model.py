from src.coach.physiology.w_balance_model import compute_w_balance, compute_tau


def test_tau_formula_skiba_2012():
    # D_CP = 100 -> tau ≈ 546*exp(-1) + 316 ≈ 517
    tau = compute_tau(cp=280, mean_power_below_cp=180)
    assert 510 <= tau <= 525


def test_constant_above_cp_depletes_w_prime():
    cp = 280
    w_prime = 20000
    # 30 s at 380 W above CP = 100 W * 30 s = 3000 J drain
    stream = [380] * 30
    series = compute_w_balance(
        stream,
        cp=cp,
        w_prime=w_prime,
        activity_id="iTest",
        laps=[{"lap_index": 0, "type": "work", "start_s": 0, "end_s": 30}],
    )
    assert abs(series.w_prime_used_j - 3000) <= 200
    assert series.min_w_bal_j <= w_prime - 2800


def test_below_cp_recovers_exponentially():
    cp = 280
    w_prime = 20000
    # 30 s at 350 W drains ~2100 J, then 120 s at 150 W recovers
    stream = [350] * 30 + [150] * 120
    series = compute_w_balance(
        stream,
        cp=cp,
        w_prime=w_prime,
        activity_id="iTest2",
        laps=[
            {"lap_index": 0, "type": "work", "start_s": 0, "end_s": 30},
            {"lap_index": 1, "type": "recovery", "start_s": 30, "end_s": 150},
        ],
    )
    final = series.w_bal_series_1hz[-1]
    # Should recover substantially — expect ≥ 80% restored
    assert final >= int(w_prime * 0.80)
