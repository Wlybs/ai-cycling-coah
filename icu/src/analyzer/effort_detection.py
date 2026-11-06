"""从原始功率流里列出全部发力，并把冲刺和一般加速分开（只看 streams，不看 ICU 记圈）。

判据全部是 ftp_set 的倍数（ftp_set = 该活动 summary.icu_ftp，骑行当时的设定值），不写死瓦数：
- 起爆：连续 3 秒依次 ≥ 1.33 / 1.17 / 1.07 × ftp_set。
- 结束：功率 < 1.17 × ftp_set 连续 2 秒，或遇到记录暂停（streams.time 跳秒）；只桥接 1 秒的掉点。
  发力的最后一秒 = 结束前最后一个 ≥ 1.17 × ftp_set 的样本。
- 冲刺：1s 峰 ≥ 800/300 × ftp_set（≈2.67 倍）且整段 ≥ 5 秒；其余都是加速。

依据（都来自本项目自己的数据和既有规则，不是文献阈值）：
- 起爆 / 结束比例沿用 stream-onset-detect skill 的 race-rhythm spike 档
  （2026-05-12 按当时瓦数 ÷ FTP 300 换算锁定）。
- 只桥接 1 秒掉点：冲刺中换挡会掉 1 秒（10-29 AWE 第 175.6 分钟那 1 秒 276W、踏频 75）。
  这是能复现 10-29 复盘 4 次冲刺边界（22 / 12 / 19 / 13 秒）的最小容忍。
- 冲刺峰值 800/300：10-29 复盘按原始流重查时用的"1s 峰 ≥800W"（当时 ftp_set 300），
  复盘记录里本人没有对查出的 4 次冲刺提出异议。
- 冲刺至少 5 秒：本人说 10-25 Crazies 57km 附近只是"站起摇两下"，原始流里 56.8km 有一次
  1s 峰 813W、只有 3 秒的爆发（两者对应是推断）；会话确认的最短冲刺是 12 秒（10-29 第 171.6 分钟）。
  5 秒也保证 5s 峰算得出来。

注意：时长是整段发力，包含同一段里冲刺前后的高功率，不等于本人体感的"冲刺时长"；
冲刺最猛的位置看 1s 峰时刻。流按 1 Hz 处理，缺失的功率按 0W 算。
"""
from __future__ import annotations

from dataclasses import dataclass

ONSET_FTP_RATIOS = (1.33, 1.17, 1.07)
OFFSET_FTP_RATIO = 1.17
MAX_DIP_S = 1
SPRINT_PEAK_FTP_RATIO = 800 / 300
SPRINT_MIN_DURATION_S = 5

SPRINT = "冲刺"
ACCELERATION = "加速"


@dataclass(frozen=True)
class Effort:
    start_s: int            # streams.time，秒（含）
    end_s: int              # streams.time，秒（含）
    duration_s: int
    avg_w: float
    peak_1s_w: float
    peak_1s_s: int          # 1s 峰所在的 streams.time
    peak_5s_w: float | None  # 整段不足 5 秒时为 None
    start_m: float | None   # 起点距离（米）；没有距离序列时为 None
    kind: str               # SPRINT / ACCELERATION


def detect_efforts(time, watts, ftp, distance=None) -> list[Effort]:
    """按时间顺序返回整次骑行的全部发力。distance 是与 time 对齐的累计距离（米），可选。"""
    if not ftp or ftp <= 0:
        raise ValueError(f"需要该活动的 ftp_set（summary.icu_ftp），收到 {ftp!r}")
    if len(time) != len(watts):
        raise ValueError(f"time 与 watts 长度不一致：{len(time)} vs {len(watts)}")
    if distance is not None and len(distance) != len(time):
        raise ValueError(f"distance 与 time 长度不一致：{len(distance)} vs {len(time)}")

    w = [x or 0 for x in watts]
    onset = [r * ftp for r in ONSET_FTP_RATIOS]
    offset = OFFSET_FTP_RATIO * ftp

    efforts = []
    i = 0
    while i + 2 < len(w):
        if _is_onset(time, w, i, onset):
            end = _effort_end(time, w, i, offset)
            efforts.append(_build_effort(time, w, i, end, ftp, distance))
            i = end + 1
        else:
            i += 1
    return efforts


def _is_onset(time, w, i, onset) -> bool:
    consecutive = time[i + 1] - time[i] == 1 and time[i + 2] - time[i + 1] == 1
    return consecutive and all(w[i + k] >= onset[k] for k in range(3))


def _effort_end(time, w, start, offset) -> int:
    """从起爆点往后走，返回最后一个 ≥ offset 的下标；掉点超过 MAX_DIP_S 秒或遇到暂停即停。"""
    last, dips = start, 0
    for j in range(start + 1, len(w)):
        if time[j] - time[j - 1] != 1:
            break
        if w[j] >= offset:
            last, dips = j, 0
        else:
            dips += 1
            if dips > MAX_DIP_S:
                break
    return last


def _build_effort(time, w, start, end, ftp, distance) -> Effort:
    seg = w[start:end + 1]
    peak_at = max(range(len(seg)), key=seg.__getitem__)
    peak_5s = max(sum(seg[k:k + 5]) / 5 for k in range(len(seg) - 4)) if len(seg) >= 5 else None
    is_sprint = seg[peak_at] >= SPRINT_PEAK_FTP_RATIO * ftp and len(seg) >= SPRINT_MIN_DURATION_S
    return Effort(
        start_s=time[start],
        end_s=time[end],
        duration_s=len(seg),
        avg_w=sum(seg) / len(seg),
        peak_1s_w=seg[peak_at],
        peak_1s_s=time[start + peak_at],
        peak_5s_w=peak_5s,
        start_m=distance[start] if distance is not None else None,
        kind=SPRINT if is_sprint else ACCELERATION,
    )
