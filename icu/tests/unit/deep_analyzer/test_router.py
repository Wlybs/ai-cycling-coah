from src.coach.deep_analyzer.router import route
from src.coach.deep_analyzer.types import Features


def test_race_activates_all_six():
    f = Features(duration_seconds=3600, total_kj=700, is_race=True)
    r = route(f)
    assert set(r.keys()) == {"pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"}
    assert all(score >= 0.5 for score in r.values())


def test_intervals_activates_pacing_and_wbal():
    f = Features(duration_seconds=3600, total_kj=500, has_intervals=True)
    r = route(f)
    assert r["pacing"] >= 0.5 and r["w_balance"] >= 0.5


def test_endurance_long_activates_durability():
    f = Features(duration_seconds=10800, total_kj=2800, is_endurance_long=True)
    r = route(f)
    assert r["durability"] >= 0.5


def test_plain_z2_only_historical():
    f = Features(duration_seconds=3600, total_kj=400)
    r = route(f)
    activated = [k for k, v in r.items() if v >= 0.5]
    assert activated == ["historical_cmp"]
