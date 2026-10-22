"""Unit tests for src/analyzer/lap_alignment.py (bd Cycling-vje)."""
from src.analyzer.lap_alignment import align_laps_to_streams, lap_stream_window

START = "2026-10-21T01:00:00Z"

# 带 100s 暂停的合成流：记录 0–99s，暂停，200–299s 再记录。共 200 个样本。
PAUSED_TIME = list(range(0, 100)) + list(range(200, 300))
PAUSED_WATTS = [150] * 50 + [250] * 50 + [300] * 100

# FIT 计圈：duration_sec 是 total_elapsed_time，含暂停。
PAUSED_LAPS = [
    {"lap_number": 1, "duration_sec": 50.0, "timestamp_iso": "2026-10-21T01:00:00+00:00"},
    {"lap_number": 2, "duration_sec": 150.0, "timestamp_iso": "2026-10-21T01:00:50+00:00"},
    {"lap_number": 3, "duration_sec": 100.0, "timestamp_iso": "2026-10-21T01:03:20+00:00"},
]


def _legacy_cumulative_indices(laps, total_points):
    """旧 sync_activity_detail.py 的逻辑：按 duration_sec 累加当作样本数。"""
    out, cur = [], 0
    for lap in laps:
        end = min(cur + int(lap["duration_sec"]), total_points)
        out.append((cur, end))
        cur = end
    return out


def _mean(vals):
    return sum(vals) / len(vals)


class TestLegacyLogicMisaligns:
    def test_cumulative_duration_overruns_after_pause(self):
        legacy = _legacy_cumulative_indices(PAUSED_LAPS, len(PAUSED_TIME))
        # lap 2 吞掉了 lap 3 的全部样本，lap 3 为空
        assert legacy[1] == (50, 200)
        assert legacy[2] == (200, 200)


class TestLapStreamWindow:
    def test_window_maps_wall_clock_to_samples_across_pause(self):
        assert lap_stream_window("2026-10-21T01:00:50+00:00", 150.0, START, PAUSED_TIME) == (50, 100)
        assert lap_stream_window("2026-10-21T01:03:20+00:00", 100.0, START, PAUSED_TIME) == (100, 200)

    def test_naive_lap_timestamp_is_treated_as_utc(self):
        assert lap_stream_window("2026-10-21T01:03:20", 100.0, START, PAUSED_TIME) == (100, 200)

    def test_missing_inputs_return_none(self):
        assert lap_stream_window(None, 100.0, START, PAUSED_TIME) is None
        assert lap_stream_window("2026-10-21T01:03:20+00:00", None, START, PAUSED_TIME) is None
        assert lap_stream_window("2026-10-21T01:03:20+00:00", 100.0, None, PAUSED_TIME) is None
        assert lap_stream_window("2026-10-21T01:03:20+00:00", 100.0, START, []) is None


class TestAlignLapsToStreams:
    def test_paused_ride_lap_power_matches_segments(self):
        laps = align_laps_to_streams([dict(l) for l in PAUSED_LAPS], PAUSED_TIME, START)
        means = [_mean(PAUSED_WATTS[l["stream_start_index"]:l["stream_end_index"]]) for l in laps]
        assert means == [150, 250, 300]

    def test_unalignable_lap_gets_none_indices(self):
        laps = align_laps_to_streams([{"lap_number": 1, "duration_sec": 60.0}], PAUSED_TIME, START)
        assert laps[0]["stream_start_index"] is None
        assert laps[0]["stream_end_index"] is None

    def test_gapless_stream_matches_legacy(self):
        time = list(range(300))
        laps = align_laps_to_streams([dict(l) for l in PAUSED_LAPS], time, START)
        got = [(l["stream_start_index"], l["stream_end_index"]) for l in laps]
        assert got == _legacy_cumulative_indices(PAUSED_LAPS, len(time))
