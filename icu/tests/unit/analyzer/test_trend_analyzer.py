"""Unit tests for src/analyzer/trend_analyzer.py."""
import json
from datetime import datetime, timedelta

import pytest

from src.analyzer import trend_analyzer as ta


# ─── classify_power_zone ────────────────────────────────────────────────────

class TestClassifyPowerZone:
    ZONES = [55, 75, 90, 105, 120, 150, 999]

    def test_missing_watts_returns_minus_one(self):
        assert ta.classify_power_zone(None, 250, self.ZONES) == -1
        assert ta.classify_power_zone(0, 250, self.ZONES) == -1

    def test_missing_ftp_returns_minus_one(self):
        assert ta.classify_power_zone(200, 0, self.ZONES) == -1

    def test_z1_low_end(self):
        # 100W / 250 = 40% → Z1 (i=0, upper=55)
        assert ta.classify_power_zone(100, 250, self.ZONES) == 0

    def test_z4_at_ftp(self):
        # 250W / 250 = 100% → between 90 and 105 → Z4 (i=3)
        assert ta.classify_power_zone(250, 250, self.ZONES) == 3

    def test_above_all_zones_caps_at_last(self):
        # pct 4000% — falls through loop; function returns last index
        assert ta.classify_power_zone(10000, 250, self.ZONES) == len(self.ZONES) - 1


# ─── get_zone_config ────────────────────────────────────────────────────────

class TestGetZoneConfig:
    def test_defaults_when_no_settings(self, monkeypatch):
        monkeypatch.setattr(ta, "_load", lambda rel: None)
        cfg = ta.get_zone_config()
        assert cfg["ftp"] == 288
        assert len(cfg["power_zone_pcts"]) == 7

    def test_reads_settings_list(self, monkeypatch):
        settings = [{
            "ftp": 250,
            "power_zones": [55, 75, 90, 105, 120, 150, 999],
            "power_zone_names": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"],
            "lthr": 170,
            "hr_zones": [120, 140, 155, 165, 175],
        }]
        monkeypatch.setattr(ta, "_load", lambda rel: settings)
        cfg = ta.get_zone_config()
        assert cfg["ftp"] == 250
        assert cfg["lthr"] == 170
        assert cfg["hr_zone_boundaries"] == [120, 140, 155, 165, 175]


# ─── analyze_aerobic_efficiency ─────────────────────────────────────────────

def _act(date, *, np=None, hr=None, ftp=288, tss=50, dur=3600, name="Ride"):
    return {
        "start_date_local": f"{date}T08:00:00",
        "icu_weighted_avg_watts": np,
        "average_heartrate": hr,
        "icu_training_load": tss,
        "moving_time": dur,
        "icu_ftp": ftp,
        "name": name,
    }


class TestAnalyzeAerobicEfficiency:
    def test_classifies_endurance_tempo_and_threshold(self):
        today = datetime.now().strftime("%Y-%m-%d")
        acts = [
            _act(today, np=150, hr=130, ftp=250),   # IF=0.6 Endurance
            _act(today, np=200, hr=150, ftp=250),   # IF=0.8 Tempo
            _act(today, np=240, hr=170, ftp=250),   # IF=0.96 Threshold+
        ]
        result = ta.analyze_aerobic_efficiency(acts, weeks=12)
        types = {r["ride_type"] for r in result["ef_trend"]}
        assert types == {"Endurance", "Tempo", "Threshold+"}

    def test_skips_rides_missing_np_or_hr(self):
        today = datetime.now().strftime("%Y-%m-%d")
        acts = [
            _act(today, np=None, hr=150),
            _act(today, np=200, hr=None),
            _act(today, np=200, hr=50),  # hr < 60 filter
            _act(today, np=200, hr=150),
        ]
        result = ta.analyze_aerobic_efficiency(acts, weeks=12)
        assert result["summary"]["total_rides_analyzed"] == 1

    def test_filters_by_cutoff(self):
        old = (datetime.now() - timedelta(weeks=20)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        result = ta.analyze_aerobic_efficiency(
            [_act(old, np=200, hr=150), _act(today, np=200, hr=150)],
            weeks=12,
        )
        assert result["summary"]["total_rides_analyzed"] == 1


# ─── analyze_ftp_trend ──────────────────────────────────────────────────────

class TestAnalyzeFtpTrend:
    def test_empty_returns_none(self):
        assert ta.analyze_ftp_trend([]) is None

    def test_progression_summary(self):
        acts = [
            {"start_date_local": "2026-01-01", "icu_ftp": 250, "icu_pm_ftp": 245},
            {"start_date_local": "2026-02-01", "icu_ftp": 270, "icu_pm_ftp": 265},
            {"start_date_local": "2026-03-01", "icu_ftp": 288, "icu_pm_ftp": 290},
        ]
        result = ta.analyze_ftp_trend(acts)
        s = result["summary"]
        assert s["earliest_ftp"] == 250
        assert s["current_ftp"] == 288
        assert s["ftp_change"] == 38
        assert s["peak_eftp_in_history"] == 290

    def test_dedupes_same_date(self):
        acts = [
            {"start_date_local": "2026-01-01T08:00", "icu_ftp": 250},
            {"start_date_local": "2026-01-01T16:00", "icu_ftp": 260},
        ]
        assert len(ta.analyze_ftp_trend(acts)["history"]) == 1

    def test_falls_back_to_rolling_ftp(self):
        acts = [{
            "start_date_local": "2026-01-01", "icu_ftp": 250,
            "icu_pm_ftp": None, "icu_rolling_ftp": 255,
        }]
        result = ta.analyze_ftp_trend(acts)
        assert result["history"][0]["eftp"] == 255


# ─── analyze_recovery_patterns ──────────────────────────────────────────────

class TestAnalyzeRecoveryPatterns:
    def test_buckets_by_tsb(self):
        acts = [
            {"start_date_local": "2026-03-01", "icu_ctl": 60, "icu_atl": 50,
             "icu_weighted_avg_watts": 240, "icu_ftp": 250, "icu_training_load": 100},
            {"start_date_local": "2026-03-05", "icu_ctl": 60, "icu_atl": 70,
             "icu_weighted_avg_watts": 200, "icu_ftp": 250, "icu_training_load": 80},
        ]
        result = ta.analyze_recovery_patterns(acts)
        assert result["summary"]["high_tsb_avg_if"] is not None
        assert result["summary"]["low_tsb_avg_if"] is not None

    def test_skips_records_missing_ctl_or_atl(self):
        acts = [
            {"start_date_local": "2026-03-01", "icu_ctl": None, "icu_atl": 50},
            {"start_date_local": "2026-03-02", "icu_ctl": 60, "icu_atl": None},
        ]
        assert ta.analyze_recovery_patterns(acts)["records"] == []

    def test_overtraining_risk_flagged_with_three_recent_negatives(self):
        today = datetime.now()
        acts = []
        for i in range(5):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            acts.append({
                "start_date_local": d,
                "icu_ctl": 60, "icu_atl": 80,  # TSB = -20
            })
        result = ta.analyze_recovery_patterns(acts)
        assert result["summary"]["overtraining_risk"] is True

    def test_overtraining_risk_false_with_stable_tsb(self):
        acts = [{
            "start_date_local": datetime.now().strftime("%Y-%m-%d"),
            "icu_ctl": 60, "icu_atl": 55,
        }]
        result = ta.analyze_recovery_patterns(acts)
        assert result["summary"]["overtraining_risk"] is False


# ─── detect_recovery_alerts ─────────────────────────────────────────────────

class TestDetectRecoveryAlerts:
    def test_no_wellness_returns_green(self, monkeypatch):
        monkeypatch.setattr(ta, "_load", lambda rel: [])
        out = ta.detect_recovery_alerts()
        assert out["alert_level"] == "green"
        assert out["alerts"] == []

    def test_hrv_drop_alert(self, monkeypatch):
        today = datetime.now()
        wellness = []
        # 22 older-week days at HRV=60 (still inside 30d window)
        for i in range(8, 30):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            wellness.append({"id": d, "hrvSDNN": 60, "restingHR": 50})
        # 7 recent days at HRV=40 → well under 85% of 30d baseline
        for i in range(7):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            wellness.append({"id": d, "hrvSDNN": 40, "restingHR": 50})
        monkeypatch.setattr(ta, "_load", lambda rel: wellness)
        out = ta.detect_recovery_alerts()
        assert any(a["kind"] == "hrv_drop" for a in out["alerts"])

    def test_rhr_elevated_alert(self, monkeypatch):
        today = datetime.now()
        wellness = []
        for i in range(30):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            rhr = 60 if i < 7 else 50  # recent week elevated vs baseline
            wellness.append({"id": d, "hrvSDNN": 60, "restingHR": rhr})
        monkeypatch.setattr(ta, "_load", lambda rel: wellness)
        out = ta.detect_recovery_alerts(baseline_rhr=50)
        assert any(a["kind"] == "rhr_elevated" for a in out["alerts"])

    def test_fatigue_self_two_consecutive_days(self, monkeypatch):
        today = datetime.now()
        wellness = [
            {"id": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
             "hrvSDNN": 60, "restingHR": 50, "fatigue": 4, "motivation": 5},
            {"id": today.strftime("%Y-%m-%d"),
             "hrvSDNN": 60, "restingHR": 50, "fatigue": 5, "motivation": 5},
        ]
        monkeypatch.setattr(ta, "_load", lambda rel: wellness)
        out = ta.detect_recovery_alerts()
        assert any(a["kind"] == "fatigue_self" for a in out["alerts"])

    def test_motivation_self_two_consecutive_days(self, monkeypatch):
        today = datetime.now()
        wellness = [
            {"id": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
             "hrvSDNN": 60, "restingHR": 50, "fatigue": 1, "motivation": 2},
            {"id": today.strftime("%Y-%m-%d"),
             "hrvSDNN": 60, "restingHR": 50, "fatigue": 1, "motivation": 1},
        ]
        monkeypatch.setattr(ta, "_load", lambda rel: wellness)
        out = ta.detect_recovery_alerts()
        assert any(a["kind"] == "motivation_self" for a in out["alerts"])

    def test_multiple_alerts_escalate_to_red(self, monkeypatch):
        today = datetime.now()
        wellness = []
        for i in range(30):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if i < 7:
                wellness.append({
                    "id": d, "hrvSDNN": 30, "restingHR": 60,  # both bad
                    "fatigue": 5, "motivation": 1,
                })
            else:
                wellness.append({"id": d, "hrvSDNN": 60, "restingHR": 50})
        monkeypatch.setattr(ta, "_load", lambda rel: wellness)
        out = ta.detect_recovery_alerts(baseline_rhr=50)
        assert out["alert_level"] == "red"
        assert len(out["alerts"]) >= 2


# ─── detect_race_readiness ──────────────────────────────────────────────────

def _load_factory(events=None, wellness=None):
    events = events or []
    wellness = wellness or []

    def _load(rel):
        if "events" in rel:
            return events
        if "wellness" in rel:
            return wellness
        return None

    return _load


class TestDetectRaceReadiness:
    def test_no_events_returns_empty_window(self, monkeypatch):
        monkeypatch.setattr(ta, "_load", _load_factory())
        out = ta.detect_race_readiness(days_ahead=10)
        assert out["races_within_window"] == []
        assert out["recommendation"] is None

    def test_race_a_within_window_sets_tight_tsb_target(self, monkeypatch):
        today = datetime.now().date()
        race_date = (today + timedelta(days=5)).isoformat()
        events = [{
            "category": "RACE_A",
            "start_date_local": race_date,
            "name": "Hill Climb",
        }]
        wellness = [{"id": today.isoformat(), "ctl": 60, "atl": 55}]
        monkeypatch.setattr(ta, "_load", _load_factory(events, wellness))
        out = ta.detect_race_readiness(days_ahead=10)
        assert len(out["races_within_window"]) == 1
        assert out["races_within_window"][0]["priority"] == "RACE_A"
        assert out["target_tsb_for_next_race"] == "0 to +5"
        assert out["current_tsb"] == pytest.approx(5.0)

    def test_race_a_openers_recommendation_at_d_minus_2(self, monkeypatch):
        today = datetime.now().date()
        race_date = (today + timedelta(days=2)).isoformat()
        events = [{
            "category": "RACE_A",
            "start_date_local": race_date,
            "name": "Hill Climb",
        }]
        monkeypatch.setattr(ta, "_load", _load_factory(events))
        out = ta.detect_race_readiness(days_ahead=10)
        assert any("Openers" in r for r in out["recommendation"])

    def test_race_a_high_tsb_warns(self, monkeypatch):
        today = datetime.now().date()
        race_date = (today + timedelta(days=2)).isoformat()
        events = [{
            "category": "RACE_A",
            "start_date_local": race_date,
            "name": "A",
        }]
        wellness = [{"id": today.isoformat(), "ctl": 80, "atl": 65}]  # TSB=15
        monkeypatch.setattr(ta, "_load", _load_factory(events, wellness))
        out = ta.detect_race_readiness(days_ahead=10)
        assert any("staleness" in r for r in out["recommendation"])

    def test_race_b_recommendation(self, monkeypatch):
        today = datetime.now().date()
        race_date = (today + timedelta(days=3)).isoformat()
        events = [{
            "category": "RACE_B",
            "start_date_local": race_date,
            "name": "B event",
        }]
        monkeypatch.setattr(ta, "_load", _load_factory(events))
        out = ta.detect_race_readiness(days_ahead=10)
        assert out["target_tsb_for_next_race"] == "+5 to +10"
        assert any("Priority B" in r for r in out["recommendation"])

    def test_non_race_events_are_ignored(self, monkeypatch):
        today = datetime.now().date()
        events = [{
            "category": "WORKOUT",
            "start_date_local": (today + timedelta(days=3)).isoformat(),
            "name": "Interval",
        }]
        monkeypatch.setattr(ta, "_load", _load_factory(events))
        out = ta.detect_race_readiness(days_ahead=10)
        assert out["races_within_window"] == []

    def test_invalid_race_date_is_skipped(self, monkeypatch):
        events = [{
            "category": "RACE_A",
            "start_date_local": "not-a-date",
            "name": "Bad",
        }]
        monkeypatch.setattr(ta, "_load", _load_factory(events))
        out = ta.detect_race_readiness(days_ahead=10)
        assert out["races_within_window"] == []


# ─── analyze_power_curve_comparison ─────────────────────────────────────────

class TestAnalyzePowerCurveComparison:
    def test_extracts_key_durations(self, monkeypatch):
        c90 = {"list": [{"secs": [5, 60, 300, 1200], "values": [800, 600, 350, 280]}]}
        call = {"list": [{"secs": [5, 60, 300, 1200], "values": [1000, 700, 400, 300]}]}

        def _load(rel):
            if "90d" in rel:
                return c90
            return call

        monkeypatch.setattr(ta, "_load", _load)
        out = ta.analyze_power_curve_comparison()
        assert out["mmp_90d"]["5s"] == 800
        assert out["mmp_all_time"]["5s"] == 1000
        assert out["comparison"]["5s"]["pct_of_alltime"] == 80.0

    def test_missing_data_yields_empty_mmps(self, monkeypatch):
        monkeypatch.setattr(ta, "_load", lambda rel: None)
        out = ta.analyze_power_curve_comparison()
        assert out["mmp_90d"] == {}
        assert out["mmp_all_time"] == {}
        # comparison keys still present but values are None
        assert out["comparison"]["5s"]["pct_of_alltime"] is None


# ─── analyze_intensity_distribution ─────────────────────────────────────────

class TestAnalyzeIntensityDistribution:
    ZONE_CFG = {
        "ftp": 250,
        "power_zone_pcts": [55, 75, 90, 105, 120, 150, 999],
        "power_zone_names": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"],
    }

    def test_returns_none_when_no_streams(self, tmp_path, monkeypatch):
        wh = tmp_path / "warehouse"
        (wh / "5_Activities_Detail").mkdir(parents=True)
        monkeypatch.setattr(ta, "WAREHOUSE", str(wh))
        assert ta.analyze_intensity_distribution([], self.ZONE_CFG, weeks=8) is None

    def test_computes_distribution_from_fixture_file(self, tmp_path, monkeypatch):
        wh = tmp_path / "warehouse"
        detail = wh / "5_Activities_Detail"
        detail.mkdir(parents=True)
        today = datetime.now().strftime("%Y-%m-%d")
        # 60s at 100W (Z1) + 60s at 250W (Z4)
        (detail / f"{today}_ride.json").write_text(json.dumps({
            "streams": {"watts": [100] * 60 + [250] * 60}
        }))
        monkeypatch.setattr(ta, "WAREHOUSE", str(wh))
        result = ta.analyze_intensity_distribution([], self.ZONE_CFG, weeks=8)
        assert result is not None
        assert result["activities_analyzed"] == 1
        pol = result["polarization"]
        assert pol["low_intensity_pct"] > 0
        assert pol["high_intensity_pct"] > 0

    def test_skips_files_outside_cutoff(self, tmp_path, monkeypatch):
        wh = tmp_path / "warehouse"
        detail = wh / "5_Activities_Detail"
        detail.mkdir(parents=True)
        # Date clearly older than 8 weeks
        old = (datetime.now() - timedelta(weeks=20)).strftime("%Y-%m-%d")
        (detail / f"{old}_oldride.json").write_text(json.dumps({
            "streams": {"watts": [200] * 60}
        }))
        monkeypatch.setattr(ta, "WAREHOUSE", str(wh))
        assert ta.analyze_intensity_distribution([], self.ZONE_CFG, weeks=8) is None

    def test_ignores_none_watts_values(self, tmp_path, monkeypatch):
        wh = tmp_path / "warehouse"
        detail = wh / "5_Activities_Detail"
        detail.mkdir(parents=True)
        today = datetime.now().strftime("%Y-%m-%d")
        (detail / f"{today}_ride.json").write_text(json.dumps({
            "streams": {"watts": [None, None, 200, 200]}
        }))
        monkeypatch.setattr(ta, "WAREHOUSE", str(wh))
        result = ta.analyze_intensity_distribution([], self.ZONE_CFG, weeks=8)
        # Only 2 samples counted (the non-None 200W)
        total_secs = sum(z["seconds"] for z in result["zone_distribution"])
        assert total_secs == 2
