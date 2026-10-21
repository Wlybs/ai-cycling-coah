"""trend_analyzer 核心计算逻辑的单元测试。"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.analyzer.trend_analyzer import (
    analyze_aerobic_efficiency,
    analyze_recovery_patterns,
    classify_power_zone,
)

# ── classify_power_zone ─────────────────────────────────────────────────────

class TestClassifyPowerZone:
    ZONE_PCTS = [55, 75, 90, 105, 120, 150, 999]
    FTP = 288

    def test_zone1_active_recovery(self):
        assert classify_power_zone(100, self.FTP, self.ZONE_PCTS) == 0  # 35% FTP

    def test_zone2_endurance(self):
        assert classify_power_zone(180, self.FTP, self.ZONE_PCTS) == 1  # 62.5% FTP

    def test_zone4_threshold(self):
        assert classify_power_zone(280, self.FTP, self.ZONE_PCTS) == 3  # 97.2% FTP

    def test_zone5_vo2max(self):
        assert classify_power_zone(320, self.FTP, self.ZONE_PCTS) == 4  # 111% FTP

    def test_zone7_neuromuscular(self):
        assert classify_power_zone(800, self.FTP, self.ZONE_PCTS) == 6  # 278% FTP

    def test_exact_boundary_upper(self):
        # 55% of 288 = 158.4W — right at boundary → zone 0
        watts = int(288 * 0.55)
        assert classify_power_zone(watts, self.FTP, self.ZONE_PCTS) == 0

    def test_just_above_boundary(self):
        watts = int(288 * 0.55) + 1
        assert classify_power_zone(watts, self.FTP, self.ZONE_PCTS) == 1

    def test_zero_watts(self):
        assert classify_power_zone(0, self.FTP, self.ZONE_PCTS) == -1

    def test_none_watts(self):
        assert classify_power_zone(None, self.FTP, self.ZONE_PCTS) == -1

    def test_none_ftp(self):
        assert classify_power_zone(200, None, self.ZONE_PCTS) == -1


# ── analyze_aerobic_efficiency ──────────────────────────────────────────────

class TestAerobicEfficiency:
    def _make_activity(self, date, np, hr, ftp=288, tss=100, duration=3600):
        return {
            "start_date_local": f"{date}T09:00:00",
            "icu_weighted_avg_watts": np,
            "average_heartrate": hr,
            "icu_training_load": tss,
            "moving_time": duration,
            "icu_ftp": ftp,
            "name": "test ride",
        }

    def test_ef_calculation(self):
        acts = [self._make_activity("2099-01-01", 200, 150)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert result is not None
        assert len(result["ef_trend"]) == 1
        assert result["ef_trend"][0]["ef"] == round(200 / 150, 3)

    def test_ride_type_endurance(self):
        # IF < 0.75 → Endurance
        acts = [self._make_activity("2099-01-01", 200, 150, ftp=288)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert result["ef_trend"][0]["ride_type"] == "Endurance"

    def test_ride_type_tempo(self):
        # IF 0.75-0.90 → Tempo
        acts = [self._make_activity("2099-01-01", 230, 150, ftp=288)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert result["ef_trend"][0]["ride_type"] == "Tempo"

    def test_ride_type_threshold(self):
        # IF >= 0.90 → Threshold+
        acts = [self._make_activity("2099-01-01", 280, 160, ftp=288)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert result["ef_trend"][0]["ride_type"] == "Threshold+"

    def test_skips_low_hr(self):
        acts = [self._make_activity("2099-01-01", 200, 50)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert len(result["ef_trend"]) == 0

    def test_skips_missing_np(self):
        acts = [self._make_activity("2099-01-01", None, 150)]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert len(result["ef_trend"]) == 0

    def test_summary_4w_split(self):
        acts = [
            self._make_activity("2099-01-01", 200, 150),
            self._make_activity("2099-06-01", 220, 150),
        ]
        result = analyze_aerobic_efficiency(acts, weeks=9999)
        assert result["summary"]["total_rides_analyzed"] == 2


# ── analyze_recovery_patterns ───────────────────────────────────────────────

class TestRecoveryPatterns:
    def _make_activity(self, date, ctl, atl, np=200, ftp=288, tss=100):
        return {
            "start_date_local": f"{date}T09:00:00",
            "icu_ctl": ctl,
            "icu_atl": atl,
            "icu_weighted_avg_watts": np,
            "icu_ftp": ftp,
            "icu_training_load": tss,
        }

    def test_tsb_calculation(self):
        acts = [self._make_activity("2099-01-01", ctl=90, atl=110)]
        result = analyze_recovery_patterns(acts)
        assert result["records"][0]["tsb"] == -20.0

    def test_high_vs_low_tsb_grouping(self):
        acts = [
            self._make_activity("2099-01-01", ctl=90, atl=80, np=250),   # TSB +10 → high
            self._make_activity("2099-01-02", ctl=90, atl=100, np=220),  # TSB -10 → low
        ]
        result = analyze_recovery_patterns(acts)
        assert result["summary"]["high_tsb_avg_if"] is not None
        assert result["summary"]["low_tsb_avg_if"] is not None

    def test_no_overtraining_when_fresh(self):
        acts = [self._make_activity("2099-06-01", ctl=80, atl=70)]
        result = analyze_recovery_patterns(acts)
        assert result["summary"]["overtraining_risk"] is False

    def test_skips_missing_ctl(self):
        acts = [{"start_date_local": "2099-01-01T09:00:00", "icu_ctl": None, "icu_atl": 100}]
        result = analyze_recovery_patterns(acts)
        assert len(result["records"]) == 0
