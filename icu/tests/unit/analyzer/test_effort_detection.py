"""Unit tests for src/analyzer/effort_detection.py（合成功率流，ftp_set=300 时阈值为 399/351/321W、冲刺 800W）。"""
import pytest

from src.analyzer.effort_detection import detect_efforts

FTP = 300


def _ride(*segments):
    """[(秒数, 瓦数), ...] → 无暂停的 1 Hz (time, watts)。"""
    watts = []
    for seconds, w in segments:
        watts += [w] * seconds
    return list(range(len(watts))), watts


def _spans(efforts):
    return [(e.start_s, e.end_s) for e in efforts]


class TestEffortBoundaries:
    def test_starts_at_onset_and_ends_at_last_sample_above_offset(self):
        time = list(range(20))
        watts = [200] * 10 + [450, 400, 360, 500, 380] + [200] * 5
        [e] = detect_efforts(time, watts, FTP)
        assert (e.start_s, e.end_s, e.duration_s) == (10, 14, 5)
        assert e.avg_w == pytest.approx((450 + 400 + 360 + 500 + 380) / 5)

    def test_single_spike_is_not_an_effort(self):
        time, watts = _ride((5, 200), (1, 900), (5, 200))
        assert detect_efforts(time, watts, FTP) == []

    def test_onset_needs_the_third_second_too(self):
        time = list(range(11))
        watts = [200] * 4 + [500, 500, 300] + [200] * 4
        assert detect_efforts(time, watts, FTP) == []

    def test_one_second_dip_is_bridged(self):
        time, watts = _ride((5, 200), (5, 500), (1, 300), (5, 500), (5, 200))
        [e] = detect_efforts(time, watts, FTP)
        assert (e.start_s, e.end_s) == (5, 15)
        assert e.avg_w == pytest.approx((500 * 10 + 300) / 11)

    def test_two_second_dip_splits_into_two_efforts(self):
        time, watts = _ride((5, 200), (5, 500), (2, 300), (5, 500), (5, 200))
        assert _spans(detect_efforts(time, watts, FTP)) == [(5, 9), (12, 16)]

    def test_trailing_samples_below_offset_are_not_counted(self):
        time = list(range(8))
        watts = [200, 200, 200, 500, 500, 500, 340, 200]
        [e] = detect_efforts(time, watts, FTP)
        assert (e.start_s, e.end_s, e.duration_s) == (3, 5, 3)

    def test_effort_running_to_end_of_stream_is_kept(self):
        time, watts = _ride((5, 200), (5, 500))
        assert _spans(detect_efforts(time, watts, FTP)) == [(5, 9)]

    def test_recording_pause_ends_the_effort(self):
        time = list(range(10)) + list(range(30, 40))
        watts = [500] * 20
        assert _spans(detect_efforts(time, watts, FTP)) == [(0, 9), (30, 39)]

    def test_onset_cannot_straddle_a_recording_pause(self):
        time = [0, 1, 2, 3, 4, 20, 21, 22]
        watts = [200, 200, 200, 450, 400, 360, 200, 200]
        assert detect_efforts(time, watts, FTP) == []

    def test_missing_watts_count_as_zero(self):
        time = list(range(10))
        watts = [500, 500, 500, None, None, 500, 500, 500, 200, 200]
        assert _spans(detect_efforts(time, watts, FTP)) == [(0, 2), (5, 7)]


class TestHysteresis:
    def test_power_between_offset_and_onset_does_not_start_an_effort(self):
        time, watts = _ride((5, 200), (10, 380), (5, 200))
        assert detect_efforts(time, watts, FTP) == []

    def test_power_between_offset_and_onset_keeps_an_effort_going(self):
        time = list(range(23))
        watts = [200] * 5 + [450, 400, 380] + [380] * 10 + [200] * 5
        assert _spans(detect_efforts(time, watts, FTP)) == [(5, 17)]


class TestThresholdsScaleWithFtp:
    def test_same_watts_are_an_effort_only_for_a_lower_ftp(self):
        time, watts = _ride((5, 150), (6, 300), (5, 150))
        assert detect_efforts(time, watts, 300) == []
        assert _spans(detect_efforts(time, watts, 200)) == [(5, 10)]

    @pytest.mark.parametrize("ftp", [0, None, -1])
    def test_rejects_missing_or_non_positive_ftp(self, ftp):
        time, watts = _ride((10, 500))
        with pytest.raises(ValueError):
            detect_efforts(time, watts, ftp)

    def test_rejects_streams_of_different_length(self):
        with pytest.raises(ValueError):
            detect_efforts([0, 1, 2], [500, 500], FTP)


class TestSprintClassification:
    def test_high_peak_held_for_five_seconds_is_a_sprint(self):
        time, watts = _ride((5, 200), (2, 600), (1, 850), (2, 600), (5, 200))
        [e] = detect_efforts(time, watts, FTP)
        assert e.kind == "冲刺"

    def test_same_shape_below_sprint_peak_is_an_acceleration(self):
        time, watts = _ride((5, 200), (2, 600), (1, 750), (2, 600), (5, 200))
        [e] = detect_efforts(time, watts, FTP)
        assert e.kind == "加速"

    def test_sprint_peak_scales_with_ftp(self):
        time, watts = _ride((5, 200), (2, 600), (1, 750), (2, 600), (5, 200))
        [e] = detect_efforts(time, watts, 250)
        assert e.kind == "冲刺"

    def test_burst_shorter_than_five_seconds_is_an_acceleration(self):
        time = list(range(10))
        watts = [200, 200, 850, 700, 600, 600, 300, 200, 200, 200]
        [e] = detect_efforts(time, watts, FTP)
        assert (e.duration_s, e.peak_1s_w, e.kind) == (4, 850, "加速")


class TestPeaks:
    def test_one_second_peak_and_its_time(self):
        time = list(range(100, 110))
        watts = [200, 200, 450, 500, 900, 600, 500, 450, 200, 200]
        [e] = detect_efforts(time, watts, FTP)
        assert (e.peak_1s_w, e.peak_1s_s) == (900, 104)

    def test_five_second_peak_is_best_window_inside_the_effort(self):
        time = list(range(9))
        watts = [500, 600, 700, 800, 900, 1000, 400, 200, 200]
        [e] = detect_efforts(time, watts, FTP)
        assert e.peak_5s_w == pytest.approx(800)

    def test_five_second_peak_is_none_for_shorter_effort(self):
        time = list(range(8))
        watts = [200, 500, 500, 500, 500, 200, 200, 200]
        [e] = detect_efforts(time, watts, FTP)
        assert e.peak_5s_w is None


class TestStartDistance:
    def test_start_distance_comes_from_the_distance_series(self):
        time, watts = _ride((5, 200), (5, 500), (5, 200))
        distance = [i * 10.0 for i in range(len(time))]
        [e] = detect_efforts(time, watts, FTP, distance=distance)
        assert e.start_m == pytest.approx(50.0)

    def test_start_distance_is_none_without_distance(self):
        time, watts = _ride((5, 200), (5, 500), (5, 200))
        [e] = detect_efforts(time, watts, FTP)
        assert e.start_m is None
