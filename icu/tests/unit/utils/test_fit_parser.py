"""Unit tests for src.utils.fit_parser.parse_fit_laps.

Real FIT files are binary SDK-encoded, so we stub `fitdecode.FitReader`
with a fake iterable that yields our controlled frame objects. The gzip
pre-decode path is exercised by feeding a gzip-wrapped payload; the
actual bytes are opaque to the mocked reader.
"""
import gzip
from datetime import datetime, timezone
from unittest.mock import patch

import fitdecode
import pytest

from src.utils import fit_parser


class FakeFrame:
    def __init__(self, frame_type, name, values=None):
        self.frame_type = frame_type
        self.name = name
        self._values = values or {}

    def get_value(self, key):
        return self._values.get(key)


class FakeFitReader:
    def __init__(self, frames):
        self._frames = frames

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self._frames)


def _patch_reader(frames):
    return patch.object(
        fit_parser.fitdecode, "FitReader", lambda _buf: FakeFitReader(frames)
    )


# ── Happy path ─────────────────────────────────────────────────────────────


class TestParseFitLaps:
    def test_extracts_lap_fields(self):
        ts = datetime(2026, 4, 18, 10, 0, 0, tzinfo=timezone.utc)
        frames = [
            FakeFrame(
                fitdecode.FIT_FRAME_DATA,
                "lap",
                {
                    "start_time": ts,
                    "total_elapsed_time": 300.5,
                    "avg_power": 220,
                    "avg_heart_rate": 150,
                    "avg_cadence": 85,
                    "max_power": 900,
                },
            ),
            FakeFrame(
                fitdecode.FIT_FRAME_DATA,
                "lap",
                {
                    "start_time": ts,
                    "total_elapsed_time": 180.0,
                    "avg_power": 240,
                    "avg_heart_rate": 160,
                    "avg_cadence": 90,
                    "max_power": 1000,
                },
            ),
        ]
        with _patch_reader(frames):
            laps = fit_parser.parse_fit_laps(b"fake fit bytes")
        assert len(laps) == 2
        assert laps[0] == {
            "lap_number": 1,
            "duration_sec": 300.5,
            "avg_watts": 220,
            "avg_hr": 150,
            "avg_cadence": 85,
            "max_watts": 900,
            "timestamp_iso": ts.isoformat(),
        }
        assert laps[1]["lap_number"] == 2
        assert laps[1]["avg_watts"] == 240

    def test_handles_gzipped_input(self):
        payload = gzip.compress(b"fake inner fit bytes")
        frames = [
            FakeFrame(
                fitdecode.FIT_FRAME_DATA,
                "lap",
                {
                    "start_time": None,
                    "total_elapsed_time": 60.0,
                    "avg_power": 200,
                    "avg_heart_rate": 140,
                    "avg_cadence": 80,
                    "max_power": 500,
                },
            )
        ]
        with _patch_reader(frames):
            laps = fit_parser.parse_fit_laps(payload)
        assert len(laps) == 1
        assert laps[0]["timestamp_iso"] is None  # None start_time handled

    def test_skips_non_lap_frames(self):
        ts = datetime(2026, 4, 18, tzinfo=timezone.utc)
        frames = [
            FakeFrame(fitdecode.FIT_FRAME_DATA, "record", {"power": 100}),
            FakeFrame(fitdecode.FIT_FRAME_HEADER, "hdr"),  # non-data frame
            FakeFrame(
                fitdecode.FIT_FRAME_DATA,
                "lap",
                {
                    "start_time": ts,
                    "total_elapsed_time": 10.0,
                    "avg_power": 100,
                    "avg_heart_rate": 120,
                    "avg_cadence": 70,
                    "max_power": 200,
                },
            ),
            FakeFrame(fitdecode.FIT_FRAME_DATA, "session", {}),
        ]
        with _patch_reader(frames):
            laps = fit_parser.parse_fit_laps(b"x")
        assert len(laps) == 1
        assert laps[0]["lap_number"] == 1

    def test_empty_when_no_lap_frames(self):
        frames = [FakeFrame(fitdecode.FIT_FRAME_DATA, "record", {"power": 100})]
        with _patch_reader(frames):
            assert fit_parser.parse_fit_laps(b"x") == []

    def test_returns_empty_list_on_parser_error(self, capsys):
        def _boom(_buf):
            raise ValueError("corrupt FIT")

        with patch.object(fit_parser.fitdecode, "FitReader", _boom):
            result = fit_parser.parse_fit_laps(b"broken bytes")
        assert result == []
        captured = capsys.readouterr()
        assert "FIT parsing error" in captured.out

    def test_missing_fields_become_none(self):
        frames = [
            FakeFrame(
                fitdecode.FIT_FRAME_DATA,
                "lap",
                {"start_time": None},  # all optional numeric fields absent
            )
        ]
        with _patch_reader(frames):
            laps = fit_parser.parse_fit_laps(b"x")
        assert laps[0]["avg_watts"] is None
        assert laps[0]["avg_hr"] is None
        assert laps[0]["max_watts"] is None
        assert laps[0]["timestamp_iso"] is None
