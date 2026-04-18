"""Unit tests for src/analyzer/analyzer.py."""
import json
import os

import pytest

from src.analyzer.analyzer import (
    MetricsCalculator,
    RideAnalyzer,
    get_latest_file,
)


# ─── MetricsCalculator.calculate_np ─────────────────────────────────────────

class TestCalculateNP:
    def test_empty_stream_returns_zero(self):
        assert MetricsCalculator.calculate_np([]) == 0

    def test_stream_shorter_than_rolling_window_returns_simple_mean(self):
        # Fewer than 30 samples → rolling buffer never fills, falls back to mean
        stream = [200] * 10
        assert MetricsCalculator.calculate_np(stream) == 200

    def test_constant_power_yields_same_np(self):
        # 60 samples of constant 200W → NP ≈ 200
        stream = [200] * 60
        assert MetricsCalculator.calculate_np(stream) == 200

    def test_variable_power_np_exceeds_mean(self):
        # Alternating 0/400 → arithmetic mean 200, but NP should be higher
        # because 4th-power mean weights high segments more heavily
        stream = ([0] * 30) + ([400] * 30)
        mean = sum(stream) / len(stream)
        np = MetricsCalculator.calculate_np(stream)
        assert np >= mean


# ─── MetricsCalculator.calculate_decoupling ─────────────────────────────────

class TestCalculateDecoupling:
    def test_empty_streams_return_none(self):
        assert MetricsCalculator.calculate_decoupling([], []) is None

    def test_mismatched_lengths_return_none(self):
        assert MetricsCalculator.calculate_decoupling([1, 2, 3], [1, 2]) is None

    def test_short_stream_under_1200_returns_none(self):
        watts = [200] * 1000
        hr = [150] * 1000
        assert MetricsCalculator.calculate_decoupling(watts, hr) is None

    def test_zero_hr_returns_none(self):
        watts = [200] * 1200
        hr = [0] * 1200
        assert MetricsCalculator.calculate_decoupling(watts, hr) is None

    def test_stable_ride_near_zero_decoupling(self):
        watts = [200] * 1200
        hr = [150] * 1200
        result = MetricsCalculator.calculate_decoupling(watts, hr)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_fatigue_pattern_positive_decoupling(self):
        # Same power but rising HR in second half → aerobic drift
        watts = [200] * 1200
        hr = [140] * 600 + [160] * 600
        result = MetricsCalculator.calculate_decoupling(watts, hr)
        assert result > 5


# ─── Helpers ────────────────────────────────────────────────────────────────

def _write_ride_json(tmp_path, data):
    f = tmp_path / "ride.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return str(f)


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Redirect analyzer module constants at empty tmp dirs."""
    from src.analyzer import analyzer as mod
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(mod, "PROFILE_DIR", str(empty))
    monkeypatch.setattr(mod, "WELLNESS_DIR", str(empty))
    monkeypatch.setattr(mod, "REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(mod, "DETAIL_DIR", str(tmp_path / "detail"))
    return tmp_path


# ─── RideAnalyzer.__init__ ──────────────────────────────────────────────────

class TestRideAnalyzerInit:
    def test_uses_summary_ftp_and_weight(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250, "icu_weight": 60},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.ftp == 250
        assert ra.weight == 60

    def test_defaults_when_summary_missing_fields(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {"summary": {}, "laps": [], "streams": {}})
        ra = RideAnalyzer(f)
        assert ra.ftp == 200
        assert ra.weight == 65.0

    def test_cp_uses_max_of_icu_cp_and_ftp(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 280, "icu_pm_cp": 250},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.cp == 280  # FTP > CP → CP bumped up

    def test_cp_keeps_icu_cp_when_higher(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250, "icu_pm_cp": 290},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.cp == 290

    def test_invalid_file_triggers_exit(self, tmp_path, isolated_env):
        with pytest.raises(SystemExit):
            RideAnalyzer(str(tmp_path / "does_not_exist.json"))

    def test_profile_overrides_summary(self, tmp_path, monkeypatch):
        from src.analyzer import analyzer as mod
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "athlete_profile.json").write_text(
            json.dumps({"icu_ftp": 300, "weight": 62}),
            encoding="utf-8",
        )
        wellness_dir = tmp_path / "wellness"
        wellness_dir.mkdir()
        monkeypatch.setattr(mod, "PROFILE_DIR", str(profile_dir))
        monkeypatch.setattr(mod, "WELLNESS_DIR", str(wellness_dir))
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 200, "icu_weight": 70},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.ftp == 300
        assert ra.weight == 62

    def test_wellness_matched_by_date(self, tmp_path, monkeypatch):
        from src.analyzer import analyzer as mod
        wellness_dir = tmp_path / "wellness"
        wellness_dir.mkdir()
        (wellness_dir / "wellness_history.json").write_text(
            json.dumps([
                {"id": "2026-04-17", "hrvSDNN": 55},
                {"id": "2026-04-18", "hrvSDNN": 60, "restingHR": 45},
            ]),
            encoding="utf-8",
        )
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        monkeypatch.setattr(mod, "WELLNESS_DIR", str(wellness_dir))
        monkeypatch.setattr(mod, "PROFILE_DIR", str(profile_dir))
        f = _write_ride_json(tmp_path, {
            "summary": {"start_date_local": "2026-04-18T10:00:00"},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.wellness is not None
        assert ra.wellness["hrvSDNN"] == 60

    def test_wellness_returns_none_when_missing(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"start_date_local": "2026-04-18"},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        assert ra.wellness is None


# ─── Formatting helpers ─────────────────────────────────────────────────────

class TestFormatHelpers:
    @pytest.fixture
    def ra(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250}, "laps": [], "streams": {},
        })
        return RideAnalyzer(f)

    def test_fmt_time_none_and_zero(self, ra):
        assert ra._fmt_time(None) == "--:--"
        assert ra._fmt_time(0) == "--:--"

    def test_fmt_time_minutes_and_seconds(self, ra):
        assert ra._fmt_time(90) == "1m30s"

    def test_fmt_time_with_hours(self, ra):
        # 3661s = 1h1m1s → shows "1h1m"
        assert ra._fmt_time(3661) == "1h1m"

    def test_log_appends_to_buffer(self, ra):
        ra._log("line1")
        ra._log("line2")
        assert ra.output_buffer == ["line1", "line2"]


# ─── analyze_lap ────────────────────────────────────────────────────────────

class TestAnalyzeLap:
    @pytest.fixture
    def ra_tempo_stream(self, tmp_path, isolated_env):
        streams = {
            "watts": [200] * 300,
            "heartrate": [150] * 300,
        }
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [], "streams": streams,
        })
        return RideAnalyzer(f)

    def test_short_lap_below_5s_returns_none(self, ra_tempo_stream):
        assert ra_tempo_stream.analyze_lap({"duration_sec": 3}, 0) is None

    def test_tempo_classification_from_stream(self, ra_tempo_stream):
        lap = {
            "duration_sec": 300,
            "avg_watts": 0,  # overwritten from streams
            "avg_hr": 0,
            "stream_start_index": 0,
            "stream_end_index": 300,
        }
        result = ra_tempo_stream.analyze_lap(lap, 0)
        # IF = 200/250 = 0.8 → Tempo band [0.75, 0.88)
        assert result["type"] == "Tempo"
        assert result["w"] == 200
        assert result["hr"] == 150
        assert result["if"] == pytest.approx(0.8)
        assert result["id"] == 1

    def test_data_anomaly_low_power_high_hr(self, tmp_path, isolated_env):
        # Power clearly off, HR high → device anomaly warning
        streams = {
            "watts": [10] * 200,
            "heartrate": [130] * 200,
        }
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [], "streams": streams,
        })
        ra = RideAnalyzer(f)
        lap = {
            "duration_sec": 120,
            "avg_watts": 10,
            "avg_hr": 130,
            "stream_start_index": 0,
            "stream_end_index": 200,
        }
        result = ra.analyze_lap(lap, 0)
        assert "数据存疑" in result["insight"]

    def test_downhill_recovery_marks_descent(self, tmp_path, isolated_env):
        # Low IF + strong descent → labeled as downhill recovery, not fatigue
        streams = {
            "watts": [100] * 200,
            "heartrate": [120] * 200,
            "altitude": [500.0 - 0.5 * i for i in range(200)],  # drops 100m
        }
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [], "streams": streams,
        })
        ra = RideAnalyzer(f)
        lap = {
            "duration_sec": 200,
            "avg_watts": 100,
            "avg_hr": 120,
            "stream_start_index": 0,
            "stream_end_index": 200,
        }
        result = ra.analyze_lap(lap, 0)
        assert result["type"] == "Downhill恢复"
        assert "下坡" in result["insight"]

    def test_hrr_computed_from_hr_stream(self, tmp_path, isolated_env):
        # HR falls from 160 to 140 across lap → hrr = 20 using end sample
        hr_stream = [160] + [150] * 40 + [140] * 9  # 50 samples, < 60
        streams = {
            "watts": [150] * 50,
            "heartrate": hr_stream,
        }
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [], "streams": streams,
        })
        ra = RideAnalyzer(f)
        lap = {
            "duration_sec": 50,
            "avg_watts": 150,
            "avg_hr": 150,
            "stream_start_index": 0,
            "stream_end_index": 50,
        }
        result = ra.analyze_lap(lap, 0)
        assert result["hrr"] == 20  # 160 - 140

    def test_lap_without_stream_indices_uses_lap_avgs(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [], "streams": {},
        })
        ra = RideAnalyzer(f)
        lap = {"duration_sec": 300, "avg_watts": 180, "avg_hr": 140}
        result = ra.analyze_lap(lap, 2)
        # NP falls back to 0 (no stream chunk) → if=0 → Recovery
        assert result is not None
        assert result["w"] == 180
        assert result["id"] == 3


# ─── calculate_full_ride_metrics ────────────────────────────────────────────

class TestCalculateFullRideMetrics:
    def test_empty_watts_returns_empty(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {}, "laps": [], "streams": {"watts": []},
        })
        ra = RideAnalyzer(f)
        assert ra.calculate_full_ride_metrics() == {}

    def test_basic_aggregate_metrics(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [],
            "streams": {"watts": [200] * 100, "heartrate": [150] * 100},
        })
        ra = RideAnalyzer(f)
        m = ra.calculate_full_ride_metrics()
        assert m["avg_p"] == 200
        assert m["avg_hr"] == 150
        assert m["if"] == pytest.approx(0.8)
        assert m["vi"] == pytest.approx(1.0)

    def test_handles_none_values_in_stream(self, tmp_path, isolated_env):
        f = _write_ride_json(tmp_path, {
            "summary": {"icu_ftp": 250},
            "laps": [],
            "streams": {"watts": [200, None, 200], "heartrate": [150, None, 150]},
        })
        ra = RideAnalyzer(f)
        m = ra.calculate_full_ride_metrics()
        # Nones become 0 → avg_p = 133
        assert m["avg_p"] == (200 + 0 + 200) // 3


# ─── get_latest_file ────────────────────────────────────────────────────────

class TestGetLatestFile:
    def test_empty_dir_returns_none(self, tmp_path, monkeypatch):
        from src.analyzer import analyzer as mod
        empty = tmp_path / "detail"
        empty.mkdir()
        monkeypatch.setattr(mod, "DETAIL_DIR", str(empty))
        assert get_latest_file() is None

    def test_returns_newest_by_mtime(self, tmp_path, monkeypatch):
        from src.analyzer import analyzer as mod
        detail = tmp_path / "detail"
        detail.mkdir()
        old = detail / "old.json"
        new = detail / "new.json"
        old.write_text("{}")
        new.write_text("{}")
        os.utime(str(old), (1000, 1000))
        os.utime(str(new), (2000, 2000))
        monkeypatch.setattr(mod, "DETAIL_DIR", str(detail))
        assert get_latest_file() == str(new)
