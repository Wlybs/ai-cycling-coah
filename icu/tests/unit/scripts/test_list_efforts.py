"""Unit tests for scripts/list_efforts.py（找详情文件、距离来源、文本 / JSON 输出）。"""
import json

import pytest

from scripts.list_efforts import analyze_file, find_detail_file, main, ride_distance


def _write_detail(path, *, ftp=300, start="2026-10-29T18:55:13", streams=None, summary_extra=None):
    summary = {"id": "i1", "start_date_local": start, "icu_ftp": ftp, **(summary_extra or {})}
    if streams is None:
        # t=10..14 一次 5 秒、峰值 850W 的冲刺；t=20..22 一次 3 秒加速
        watts = [200] * 10 + [600, 600, 850, 600, 600] + [200] * 5 + [450, 420, 400] + [200] * 7
        streams = {"time": list(range(len(watts))), "watts": watts}
    path.write_text(json.dumps({"summary": summary, "streams": streams}), encoding="utf-8")
    return path


class TestFindDetailFile:
    def test_finds_file_by_activity_id_in_name(self, tmp_path):
        target = tmp_path / "2026-10-29_i203196687.json"
        target.write_text("{}", encoding="utf-8")
        (tmp_path / "2026-10-28_i202627708.json").write_text("{}", encoding="utf-8")
        assert find_detail_file("i203196687", tmp_path) == target

    def test_falls_back_to_summary_id_for_legacy_names(self, tmp_path):
        (tmp_path / "2026-01-15_其他骑_FULL.json").write_text(
            json.dumps({"summary": {"id": "i8"}}), encoding="utf-8")
        legacy = tmp_path / "2026-01-14_康复骑_FULL.json"
        legacy.write_text(json.dumps({"summary": {"id": "i9"}}), encoding="utf-8")
        assert find_detail_file("i9", tmp_path) == legacy

    def test_accepts_a_detail_file_path(self, tmp_path):
        path = _write_detail(tmp_path / "anything.json")
        assert find_detail_file(str(path), tmp_path / "unused") == path

    def test_unknown_activity_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_detail_file("i404", tmp_path)


class TestRideDistance:
    def test_prefers_the_distance_stream(self):
        streams = {"time": [0, 1, 2], "distance": [0.0, 7.0, 15.0], "velocity_smooth": [9, 9, 9]}
        assert ride_distance(streams, {"distance": 999}) == ([0.0, 7.0, 15.0], "distance 流")

    def test_estimates_from_speed_scaled_to_summary_distance(self):
        streams = {"time": [0, 1, 2, 3], "velocity_smooth": [10.0, 10.0, 10.0, 10.0]}
        distance, source = ride_distance(streams, {"distance": 60.0})
        assert distance == pytest.approx([0.0, 20.0, 40.0, 60.0])
        assert source == "车速积分估算"

    def test_speed_is_not_integrated_across_a_recording_pause(self):
        streams = {"time": [0, 1, 2, 100, 101], "velocity_smooth": [5.0] * 5}
        distance, _ = ride_distance(streams, {})
        assert distance == pytest.approx([0.0, 5.0, 10.0, 10.0, 15.0])

    def test_no_distance_without_distance_or_speed(self):
        assert ride_distance({"time": [0, 1], "watts": [100, 100]}, {}) == (None, None)


class TestAnalyzeFile:
    def test_lists_efforts_with_local_clock_times(self, tmp_path):
        report = analyze_file(_write_detail(tmp_path / "ride.json"))
        sprint, burst = report["efforts"]
        assert (sprint["kind"], sprint["start_clock"], sprint["end_clock"]) == ("冲刺", "18:55:23", "18:55:27")
        assert (sprint["duration_s"], sprint["avg_w"], sprint["peak_1s_w"], sprint["peak_1s_clock"]) == (
            5, 650, 850, "18:55:25")
        assert (burst["kind"], burst["start_clock"], burst["duration_s"]) == ("加速", "18:55:33", 3)
        assert report["counts"] == {"冲刺": 1, "加速": 1}

    def test_reports_thresholds_in_watts_for_this_ftp(self, tmp_path):
        report = analyze_file(_write_detail(tmp_path / "ride.json", ftp=270))
        assert report["thresholds_w"]["onset"] == [359, 316, 289]
        assert report["thresholds_w"]["offset"] == 316
        assert report["thresholds_w"]["sprint_peak"] == 720

    def test_legacy_list_streams_are_read(self, tmp_path):
        watts = [200] * 5 + [500] * 5 + [200] * 5
        streams = [{"type": "time", "data": list(range(15))}, {"type": "watts", "data": watts}]
        report = analyze_file(_write_detail(tmp_path / "ride.json", streams=streams))
        assert [e["start_clock"] for e in report["efforts"]] == ["18:55:18"]

    def test_start_km_from_speed_estimate(self, tmp_path):
        watts = [200] * 5 + [500] * 5 + [200] * 5
        streams = {"time": list(range(15)), "watts": watts, "velocity_smooth": [10.0] * 15}
        report = analyze_file(_write_detail(tmp_path / "ride.json", streams=streams))
        assert report["distance_source"] == "车速积分估算"
        assert report["efforts"][0]["start_km"] == pytest.approx(0.05)


class TestMain:
    def test_text_output_shows_counts_and_each_effort(self, tmp_path, capsys):
        assert main([str(_write_detail(tmp_path / "ride.json"))]) == 0
        out = capsys.readouterr().out
        assert "冲刺 1 次" in out and "加速 1 次" in out
        assert "18:55:23" in out and "18:55:33" in out

    def test_json_output_is_machine_readable(self, tmp_path, capsys):
        assert main([str(_write_detail(tmp_path / "ride.json")), "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert [e["kind"] for e in report["efforts"]] == ["冲刺", "加速"]

    def test_missing_ftp_is_an_error_not_a_default(self, tmp_path, capsys):
        assert main([str(_write_detail(tmp_path / "ride.json", ftp=None))]) != 0
        assert "icu_ftp" in capsys.readouterr().err

    def test_ride_without_power_is_an_error_not_zero_efforts(self, tmp_path, capsys):
        path = _write_detail(tmp_path / "ride.json", streams={"heartrate": [100, 101, 102]})
        assert main([str(path)]) != 0
        assert "watts" in capsys.readouterr().err
