from src.coach.common.lap_segmenter import segment_lap_by_power


def test_empty_input_returns_empty_list():
    assert segment_lap_by_power([], ftp=300) == []


def test_single_class_collapses_to_one_segment():
    watts = [200] * 60  # medium zone (200/300 = 67%)
    out = segment_lap_by_power(watts, ftp=300)
    assert len(out) == 1
    assert out[0]["class"] == "medium"
    assert out[0]["duration_s"] == 60
    assert out[0]["avg_w"] == 200


def test_high_then_low_splits_into_two():
    watts = [330] * 60 + [100] * 120  # VO2max then coast
    out = segment_lap_by_power(watts, ftp=300)
    assert len(out) == 2
    assert out[0]["class"] == "high"
    assert out[1]["class"] == "low"
    # Boundary may shift a few seconds due to 5s smoothing; allow tolerance
    assert abs(out[0]["duration_s"] - 60) <= 3
    assert abs(out[1]["duration_s"] - 120) <= 3


def test_short_spike_is_merged_into_neighbor():
    # 30s medium + 5s burst at 500W + 30s medium → spike < min_segment_s, merged away
    watts = [200] * 30 + [500] * 5 + [200] * 30
    out = segment_lap_by_power(watts, ftp=300, min_segment_s=10)
    assert len(out) == 1
    assert out[0]["class"] == "medium"
    assert out[0]["duration_s"] == 65


def test_group_ride_thresholds_detect_attack_above_ftp():
    """With --group thresholds (1.5/1.0 × FTP), bursts above FTP×1.5 classify as 'high'
    while sustained ~FTP is 'medium' and draft at 60% is 'low'."""
    # 40s draft @ 180W + 20s attack @ 500W + 60s pull @ 310W
    watts = [180] * 40 + [500] * 20 + [310] * 60
    out = segment_lap_by_power(watts, ftp=300, high_pct=1.5, med_pct=1.0)
    classes = [s["class"] for s in out]
    assert classes == ["low", "high", "medium"]


def test_sub_segment_fields_are_computed():
    watts = [330] * 30 + [100] * 30
    out = segment_lap_by_power(watts, ftp=300)
    assert out[0]["avg_w"] >= 300
    assert out[0]["max_w"] >= 300
    assert out[0]["if"] is not None
    assert out[0]["start_s"] == 0
    assert out[0]["end_s"] > 0
    assert out[1]["start_s"] == out[0]["end_s"]
