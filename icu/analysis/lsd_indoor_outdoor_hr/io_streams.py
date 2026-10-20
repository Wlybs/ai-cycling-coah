"""读取本次只读抓取的活动清单 / 原始 streams，统一成按秒的 numpy 数组。

ICU streams 是 list[{type, data, data2?}]；latlng 的 data=纬度、data2=经度，均可能为 null。
不补零、不插值：time 不连续处保留为 gap，由 segments.py 分类。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RAW_DIR = Path("D:/Cycling/icu/icu_data_warehouse/9_Coach_Raw/2026-10-20-outdoor-lsd-tradeoff")
LIST_FILE = RAW_DIR / "activities_2026-08-01_2026-10-20.json"
WELLNESS_FILE = Path("D:/Cycling/icu/icu_data_warehouse/2_Wellness/wellness_history.json")
SNAPSHOT_FILE = Path("D:/Cycling/icu/coach_memory/athlete_snapshot.json")

SCALAR_STREAMS = ("time", "watts", "heartrate", "cadence", "velocity_smooth", "distance", "temp", "altitude")


@dataclass
class Ride:
    aid: str
    meta: dict
    t: np.ndarray            # elapsed seconds since start (int, strictly increasing)
    p: np.ndarray            # watts (nan = missing)
    hr: np.ndarray
    cad: np.ndarray
    v: np.ndarray            # m/s (nan = missing)
    dist: np.ndarray
    temp: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    indoor: bool
    notes: list = field(default_factory=list)


def _to_float(values: list | None, n: int) -> np.ndarray:
    if values is None:
        return np.full(n, np.nan)
    return np.array([np.nan if x is None else float(x) for x in values], dtype=float)


def load_activity_list() -> list[dict]:
    acts = json.loads(LIST_FILE.read_text(encoding="utf-8"))
    return sorted(acts, key=lambda a: a.get("start_date_local") or "")


def load_streams(aid: str) -> dict[str, np.ndarray]:
    raw = json.loads((RAW_DIR / f"streams_{aid}.json").read_text(encoding="utf-8"))
    entries = raw if isinstance(raw, list) else [{"type": k, "data": v} for k, v in raw.items()]
    by_type = {e["type"]: e for e in entries}
    n = len(by_type["time"]["data"])
    out = {k: _to_float(by_type.get(k, {}).get("data"), n) for k in SCALAR_STREAMS}
    ll = by_type.get("latlng", {})
    out["lat"] = _to_float(ll.get("data"), n)
    out["lon"] = _to_float(ll.get("data2"), n)
    return out


def is_indoor(meta: dict) -> bool:
    """VirtualRide 或 trainer=True 视为室内；10/01 Zwift 为 VirtualRide 但 trainer=False，按类型判室内。"""
    return meta.get("type") == "VirtualRide" or bool(meta.get("trainer"))


def load_ride(meta: dict) -> Ride:
    s = load_streams(meta["id"])
    t = s["time"].astype(int)
    if np.any(np.diff(t) <= 0):
        raise ValueError(f"{meta['id']}: time stream not strictly increasing")
    indoor = is_indoor(meta)
    v = s["velocity_smooth"]
    notes = []
    if indoor:
        notes.append("indoor: velocity is virtual (Zwift) or absent; moving state inferred from power/cadence")
    return Ride(meta["id"], meta, t, s["watts"], s["heartrate"], s["cadence"], v, s["distance"],
                s["temp"], s["lat"], s["lon"], indoor, notes)


def load_wellness() -> dict[str, dict]:
    items = json.loads(WELLNESS_FILE.read_text(encoding="utf-8"))
    return {e["id"]: e for e in items}


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
