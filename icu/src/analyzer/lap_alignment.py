"""FIT 计圈 → streams 样本索引对齐（bd Cycling-vje）。

FIT 的 duration_sec 是 total_elapsed_time（含暂停），streams 按样本计、暂停期间没有样本，
所以不能把 duration_sec 累加当索引。这里按墙钟时间切窗：
起点 = lap timestamp_iso − 活动 start_date（UTC），终点 = 起点 + duration_sec，
再在 streams.time 上二分查找得到 [start, end) 样本索引。
"""
import bisect
from datetime import UTC, datetime


def _parse_utc(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def lap_stream_window(
    lap_start_iso: str | None,
    duration_sec: float | None,
    activity_start_utc: str | None,
    stream_time: list,
) -> tuple[int, int] | None:
    """返回 lap 在 streams 里的 [start, end) 索引；信息不全时返回 None。"""
    if not lap_start_iso or duration_sec is None or not activity_start_utc or not stream_time:
        return None
    offset = (_parse_utc(lap_start_iso) - _parse_utc(activity_start_utc)).total_seconds()
    start = bisect.bisect_left(stream_time, offset)
    end = bisect.bisect_left(stream_time, offset + duration_sec)
    return start, end


def align_laps_to_streams(laps: list, stream_time: list, activity_start_utc: str | None) -> list:
    """给每个 lap 写入 stream_start_index / stream_end_index（原地修改并返回同一列表）。

    对不齐的 lap（缺起始时间或时长）索引写 None，下游会退回用 FIT 自带的均值。
    """
    for lap in laps:
        window = lap_stream_window(
            lap.get("timestamp_iso"), lap.get("duration_sec"), activity_start_utc, stream_time
        )
        lap["stream_start_index"], lap["stream_end_index"] = window if window else (None, None)
    return laps
