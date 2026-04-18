"""Unit tests for src.utils.common."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.utils import common


# ── setup_encoding ─────────────────────────────────────────────────────────


class TestSetupEncoding:
    def test_noop_on_non_win32(self, monkeypatch):
        monkeypatch.setattr(common.sys, "platform", "linux")
        stdout = MagicMock()
        monkeypatch.setattr(common.sys, "stdout", stdout)
        common.setup_encoding()
        stdout.reconfigure.assert_not_called()

    def test_forces_utf8_on_win32(self, monkeypatch):
        monkeypatch.setattr(common.sys, "platform", "win32")
        stdout = MagicMock()
        monkeypatch.setattr(common.sys, "stdout", stdout)
        common.setup_encoding()
        stdout.reconfigure.assert_called_once_with(encoding="utf-8")


# ── get_warehouse_dir ──────────────────────────────────────────────────────


class TestGetWarehouseDir:
    def test_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("OUTPUT_WAREHOUSE_DIR", raising=False)
        assert common.get_warehouse_dir() == "./icu_data_warehouse"

    def test_uses_env_override(self, monkeypatch):
        monkeypatch.setenv("OUTPUT_WAREHOUSE_DIR", "/tmp/custom")
        assert common.get_warehouse_dir() == "/tmp/custom"


# ── save_json ──────────────────────────────────────────────────────────────


class TestSaveJson:
    def test_writes_valid_json_and_returns_path(self, tmp_path):
        folder = tmp_path / "nested" / "dir"
        out = common.save_json({"a": 1, "b": [2, 3]}, str(folder), "data.json")
        assert out == str(folder / "data.json")
        with open(out, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {"a": 1, "b": [2, 3]}

    def test_creates_missing_directory(self, tmp_path):
        folder = tmp_path / "does_not_exist_yet"
        assert not folder.exists()
        common.save_json({"k": "v"}, str(folder), "f.json")
        assert folder.is_dir()

    def test_preserves_unicode_without_escaping(self, tmp_path):
        common.save_json({"name": "张三", "emoji": "🚴"}, str(tmp_path), "u.json")
        with open(tmp_path / "u.json", "r", encoding="utf-8") as f:
            raw = f.read()
        assert "张三" in raw
        assert "🚴" in raw
        assert "\\u" not in raw  # ensure_ascii=False


# ── load_json ──────────────────────────────────────────────────────────────


class TestLoadJson:
    def test_loads_valid_json(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text('{"k": 1}', encoding="utf-8")
        assert common.load_json(str(path)) == {"k": 1}

    def test_returns_none_on_missing_file(self, tmp_path):
        assert common.load_json(str(tmp_path / "nope.json")) is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not { valid json", encoding="utf-8")
        assert common.load_json(str(path)) is None

    def test_roundtrip(self, tmp_path):
        original = {"list": [1, 2, 3], "nested": {"k": "v"}, "chinese": "中文"}
        out_path = common.save_json(original, str(tmp_path), "rt.json")
        assert common.load_json(out_path) == original
