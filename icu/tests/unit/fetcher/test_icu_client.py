"""Unit tests for src.fetcher.icu_client.ICUClient.

The client is a thin wrapper over `requests.request`. Tests here patch
the module-level `requests` symbol so no real HTTP is issued, and patch
`time.sleep` so retry paths don't actually wait.
"""
from unittest.mock import patch, MagicMock

import pytest
import requests as real_requests

from src.fetcher import icu_client as icu_mod
from src.fetcher.icu_client import ICUClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "i123456")
    monkeypatch.delenv("PROXY_PORT", raising=False)
    return ICUClient()


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(icu_mod.time, "sleep", lambda _s: None)


def _make_response(status=200, json_data=None, content=b""):
    resp = MagicMock(spec=real_requests.Response)
    resp.status_code = status
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = content
    if 400 <= status < 600:
        resp.raise_for_status.side_effect = real_requests.HTTPError(
            f"{status} error", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── __init__ ───────────────────────────────────────────────────────────────


class TestInit:
    def test_reads_credentials_from_env(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "k")
        monkeypatch.setenv("ATHLETE_ID", "a1")
        monkeypatch.delenv("PROXY_PORT", raising=False)
        c = ICUClient()
        assert c.api_key == "k"
        assert c.athlete_id == "a1"
        assert c.auth == ("API_KEY", "k")
        assert c.base_url == "https://intervals.icu/api/v1"
        assert c.proxies is None

    def test_proxy_built_when_port_set(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "k")
        monkeypatch.setenv("ATHLETE_ID", "a1")
        monkeypatch.setenv("PROXY_PORT", "7890")
        c = ICUClient()
        assert c.proxies == {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }


# ── _request ───────────────────────────────────────────────────────────────


class TestRequest:
    def test_returns_response_on_200(self, client):
        resp = _make_response(200, {"ok": True})
        with patch.object(icu_mod.requests, "request", return_value=resp) as m:
            result = client._request("GET", "/foo", params={"a": 1})
        assert result is resp
        m.assert_called_once()
        args, kwargs = m.call_args
        assert args == ("GET", "https://intervals.icu/api/v1/foo")
        assert kwargs["auth"] == ("API_KEY", "test-key")
        assert kwargs["proxies"] is None
        assert kwargs["params"] == {"a": 1}

    def test_retries_on_retryable_status_then_succeeds(self, client):
        bad = _make_response(503)
        good = _make_response(200, {"ok": 1})
        with patch.object(icu_mod.requests, "request", side_effect=[bad, bad, good]) as m:
            result = client._request("GET", "/x")
        assert result is good
        assert m.call_count == 3

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_statuses_trigger_retry(self, client, status):
        bad = _make_response(status)
        good = _make_response(200, {})
        with patch.object(icu_mod.requests, "request", side_effect=[bad, good]) as m:
            client._request("GET", "/x")
        assert m.call_count == 2

    def test_raises_after_exhausting_retries(self, client):
        bad = _make_response(503)
        with patch.object(icu_mod.requests, "request", return_value=bad):
            with pytest.raises(real_requests.HTTPError):
                client._request("GET", "/x")

    def test_non_retryable_status_raises_immediately(self, client):
        bad = _make_response(404)
        with patch.object(icu_mod.requests, "request", return_value=bad) as m:
            with pytest.raises(real_requests.HTTPError):
                client._request("GET", "/x")
        assert m.call_count == 1

    def test_connection_error_retries_then_raises(self, client):
        with patch.object(
            icu_mod.requests,
            "request",
            side_effect=real_requests.ConnectionError("boom"),
        ) as m:
            with pytest.raises(real_requests.ConnectionError):
                client._request("GET", "/x")
        assert m.call_count == icu_mod.MAX_RETRIES + 1

    def test_connection_error_then_success(self, client):
        good = _make_response(200, {"ok": True})
        with patch.object(
            icu_mod.requests,
            "request",
            side_effect=[real_requests.ConnectionError("once"), good],
        ) as m:
            result = client._request("GET", "/x")
        assert result is good
        assert m.call_count == 2


# ── Thin helpers ───────────────────────────────────────────────────────────


class TestHelpers:
    def test_get_returns_json(self, client):
        resp = _make_response(200, {"value": 42})
        with patch.object(icu_mod.requests, "request", return_value=resp):
            assert client._get("/anywhere") == {"value": 42}

    def test_get_bytes_returns_content(self, client):
        resp = _make_response(200, content=b"\x01\x02\x03")
        with patch.object(icu_mod.requests, "request", return_value=resp):
            assert client._get_bytes("/file") == b"\x01\x02\x03"


# ── Endpoint wrappers ──────────────────────────────────────────────────────


class TestEndpoints:
    @pytest.fixture
    def mock_req(self):
        with patch.object(icu_mod.requests, "request") as m:
            yield m

    def _ok(self, data=None, content=b""):
        return _make_response(200, json_data=data or {}, content=content)

    def test_get_athlete(self, client, mock_req):
        mock_req.return_value = self._ok({"id": "i123456"})
        assert client.get_athlete() == {"id": "i123456"}
        assert mock_req.call_args.args[1].endswith("/athlete/i123456")

    def test_get_sport_settings(self, client, mock_req):
        mock_req.return_value = self._ok({"ftp": 288})
        client.get_sport_settings()
        assert mock_req.call_args.args[1].endswith(
            "/athlete/i123456/sport-settings"
        )

    def test_get_wellness_passes_cols_and_dates(self, client, mock_req):
        mock_req.return_value = self._ok([])
        client.get_wellness("2026-01-01", "2026-01-31")
        params = mock_req.call_args.kwargs["params"]
        assert params["oldest"] == "2026-01-01"
        assert params["newest"] == "2026-01-31"
        assert "ctl" in params["cols"] and "hrv" in params["cols"]

    def test_get_activities(self, client, mock_req):
        mock_req.return_value = self._ok([])
        client.get_activities("2026-01-01", "2026-01-31")
        assert mock_req.call_args.kwargs["params"] == {
            "oldest": "2026-01-01",
            "newest": "2026-01-31",
        }
        assert mock_req.call_args.args[1].endswith("/athlete/i123456/activities")

    def test_get_activity_forces_intervals_true(self, client, mock_req):
        mock_req.return_value = self._ok({"id": "abc"})
        client.get_activity("abc")
        assert mock_req.call_args.kwargs["params"] == {"intervals": "true"}
        assert mock_req.call_args.args[1].endswith("/activity/abc")

    def test_get_activity_file_returns_bytes(self, client, mock_req):
        mock_req.return_value = self._ok(content=b"FIT\x00raw")
        out = client.get_activity_file("abc")
        assert out == b"FIT\x00raw"
        assert mock_req.call_args.args[1].endswith("/activity/abc/file")

    def test_get_activity_streams_default_types(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_activity_streams("abc")
        types = mock_req.call_args.kwargs["params"]["types"]
        for key in ("time", "watts", "heartrate", "cadence", "w_bal"):
            assert key in types

    def test_get_activity_streams_custom_types(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_activity_streams("abc", types="time,watts")
        assert mock_req.call_args.kwargs["params"]["types"] == "time,watts"

    def test_histograms(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_power_histogram("abc")
        assert mock_req.call_args.args[1].endswith("/activity/abc/power-histogram")
        client.get_hr_histogram("abc")
        assert mock_req.call_args.args[1].endswith("/activity/abc/hr-histogram")

    def test_get_power_curves_without_dates(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_power_curves()
        params = mock_req.call_args.kwargs["params"]
        assert params == {"type": "Ride"}

    def test_get_power_curves_with_dates_and_type(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_power_curves(oldest="2026-01-01", newest="2026-04-01", type="Run")
        assert mock_req.call_args.kwargs["params"] == {
            "type": "Run",
            "start": "2026-01-01",
            "end": "2026-04-01",
        }

    def test_get_hr_curves_without_dates(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_hr_curves()
        assert mock_req.call_args.kwargs["params"] == {}

    def test_get_hr_curves_with_dates(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.get_hr_curves(oldest="2026-01-01", newest="2026-04-01")
        assert mock_req.call_args.kwargs["params"] == {
            "start": "2026-01-01",
            "end": "2026-04-01",
        }

    def test_get_events_resolves(self, client, mock_req):
        mock_req.return_value = self._ok([])
        client.get_events("2026-01-01", "2026-01-31")
        params = mock_req.call_args.kwargs["params"]
        assert params["resolve"] == "true"
        assert params["oldest"] == "2026-01-01"

    def test_create_event_posts_json(self, client, mock_req):
        mock_req.return_value = self._ok({"id": "evt1"})
        payload = {"category": "WORKOUT", "name": "VO2"}
        assert client.create_event(payload) == {"id": "evt1"}
        assert mock_req.call_args.args[0] == "POST"
        assert mock_req.call_args.args[1].endswith("/athlete/i123456/events")
        assert mock_req.call_args.kwargs["json"] == payload

    def test_delete_event_calls_delete(self, client, mock_req):
        mock_req.return_value = self._ok({})
        client.delete_event("evt1")
        assert mock_req.call_args.args[0] == "DELETE"
        assert mock_req.call_args.args[1].endswith("/athlete/i123456/events/evt1")

    def test_get_workouts(self, client, mock_req):
        mock_req.return_value = self._ok([])
        client.get_workouts()
        assert mock_req.call_args.args[1].endswith("/athlete/i123456/workouts")
