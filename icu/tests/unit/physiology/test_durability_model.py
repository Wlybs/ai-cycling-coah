from src.coach.physiology.durability_model import fit_durability


def synthetic_ride(duration_s=10800, peak_w=400, decay_per_1000kj=0.05):
    # Power as rough function of cumulative kJ — used to generate checkpoints
    stream = []
    kj = 0.0
    for t in range(duration_s):
        p = peak_w * max(0.70, (1.0 - decay_per_1000kj * (kj / 1000)))
        stream.append(p)
        kj += p / 1000  # Watts / 1000 = kJ per second
    return {"activity_id": f"i{duration_s}", "power_stream": stream}


def test_fit_durability_decays_positively():
    rides = [synthetic_ride() for _ in range(5)]
    curve = fit_durability(rides)
    assert curve.sample_size_rides == 5
    assert curve.fresh_mmp_w["300s"] > 0
    # Decay rate must be non-negative (power drops or holds)
    for dur in ("60s", "300s", "1200s"):
        assert curve.decay_rate_pct_per_1000kj[dur] >= 0
    # 2500 kJ fatigued MMP must be <= fresh
    assert curve.fatigued_mmp_w["2500kj"]["300s"] <= curve.fresh_mmp_w["300s"]


def test_insufficient_data_returns_empty_curve():
    curve = fit_durability([])
    assert curve.sample_size_rides == 0
