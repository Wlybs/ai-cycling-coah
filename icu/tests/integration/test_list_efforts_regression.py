"""回归：两次被本人纠正过的团骑，期望值按原始流逐秒手算核对（夹具只含 time / watts）。

- 10-29 AWE：只看 ICU 记圈最大值时报成 1 次冲刺，本人说"我不止冲刺了一次"；原始流是 4 次。
- 10-25 Crazies：把"全程最好 20 秒"写成"终点冲刺 20 秒 750W"。原始流里终点是一段连续发力，
  功率中途没有回落；本人自己的冲刺（会话按叙述约 11 秒）从这一段的 1s 峰时刻开始。
"""
from pathlib import Path

import pytest

from scripts.list_efforts import analyze_file

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "efforts"


def _effort_at(report, start_clock):
    [effort] = [e for e in report["efforts"] if e["start_clock"] == start_clock]
    return effort


class TestAwe20261029:
    report = analyze_file(FIXTURES / "2026-10-29_i203196687.json")

    def test_four_sprints_from_the_raw_stream(self):
        sprints = [
            (e["start_clock"], e["duration_s"], e["avg_w"], e["peak_1s_w"], e["peak_1s_clock"], e["peak_5s_w"])
            for e in self.report["efforts"] if e["kind"] == "冲刺"
        ]
        assert sprints == [
            ("21:33:29", 22, 704, 994, "21:33:38", 959),
            ("21:46:50", 12, 884, 1085, "21:46:54", 978),
            ("21:50:13", 19, 633, 882, "21:50:21", 826),
            ("21:50:51", 13, 594, 912, "21:51:02", 717),
        ]
        assert self.report["counts"]["冲刺"] == 4

    def test_701w_surge_before_the_solo_pull_is_an_acceleration(self):
        effort = _effort_at(self.report, "21:39:56")
        assert (effort["kind"], effort["duration_s"], effort["peak_1s_w"]) == ("加速", 18, 701)


class TestCrazies20261025:
    report = analyze_file(FIXTURES / "2026-10-25_i201276413.json")

    def test_finish_is_one_continuous_effort_peaking_where_the_own_sprint_starts(self):
        effort = _effort_at(self.report, "08:32:06")
        assert (effort["kind"], effort["end_clock"], effort["duration_s"], effort["avg_w"]) == (
            "冲刺", "08:32:30", 25, 728)
        assert (effort["peak_1s_w"], effort["peak_1s_clock"]) == (995, "08:32:20")

    def test_solo_attack_is_a_sprint(self):
        effort = _effort_at(self.report, "08:10:29")
        assert (effort["kind"], effort["end_clock"], effort["duration_s"]) == ("冲刺", "08:11:12", 44)
        assert (effort["peak_1s_w"], effort["peak_1s_clock"]) == (1128, "08:10:35")

    def test_three_second_stand_up_burst_near_57km_is_an_acceleration(self):
        effort = _effort_at(self.report, "08:04:27")
        assert (effort["kind"], effort["duration_s"], effort["peak_1s_w"]) == ("加速", 3, 813)
