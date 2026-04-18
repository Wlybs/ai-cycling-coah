"""Raw-stream lap re-segmentation.

When the athlete forgot to press the lap button, accidentally double-pressed,
or did a group ride where a single recorded lap contains attack/draft/pull
sub-phases, the aggregate lap metrics hide the real training content. This
module re-segments a lap's raw watts stream into consecutive homogeneous-
intensity runs so the coach can analyze the real work.
"""
from __future__ import annotations

from typing import Literal

SegmentClass = Literal["high", "medium", "low"]


def _smooth_5s(watts: list[int | float]) -> list[float]:
    """5-second centered moving average; output same length as input."""
    n = len(watts)
    out: list[float] = [0.0] * n
    for i in range(n):
        lo = max(0, i - 2)
        hi = min(n, i + 3)
        window = [float(w or 0) for w in watts[lo:hi]]
        out[i] = sum(window) / len(window) if window else 0.0
    return out


def _classify(w: float, ftp: int, *, high_pct: float, med_pct: float) -> SegmentClass:
    pct = w / max(ftp, 1)
    if pct >= high_pct:
        return "high"
    if pct >= med_pct:
        return "medium"
    return "low"


def segment_lap_by_power(
    watts: list[int | float],
    ftp: int,
    *,
    min_segment_s: int = 10,
    high_pct: float = 0.90,
    med_pct: float = 0.60,
) -> list[dict]:
    """Run-length-encode a watts stream into intensity-class runs.

    Samples are assumed to be 1 Hz. 5 s smoothing suppresses spikes before
    classification. Runs shorter than ``min_segment_s`` are merged into the
    adjacent longer run (removes classifier flutter at zone boundaries).

    Args:
      watts: 1 Hz power samples for the lap window.
      ftp: athlete FTP in watts (used to normalize thresholds).
      min_segment_s: minimum emitted segment duration; shorter runs merge.
      high_pct / med_pct: FTP-fraction thresholds for high / medium classes.
        For solo intervals use defaults (0.90 / 0.60). For group-ride attack
        detection try (1.50 / 1.00) — attack = burst above FTP×1.5.

    Returns:
      List of dicts with keys: class, start_s, end_s, duration_s, avg_w,
      max_w, if (avg relative to FTP). Empty list for empty input.
    """
    if not watts:
        return []
    smoothed = _smooth_5s(watts)
    classes = [_classify(w, ftp, high_pct=high_pct, med_pct=med_pct) for w in smoothed]

    runs: list[list] = []
    cur_class = classes[0]
    cur_start = 0
    for i in range(1, len(classes)):
        if classes[i] != cur_class:
            runs.append([cur_class, cur_start, i])
            cur_class = classes[i]
            cur_start = i
    runs.append([cur_class, cur_start, len(classes)])

    # Iteratively merge short runs into the longer neighbor.
    while True:
        merged = False
        i = 0
        while i < len(runs):
            dur = runs[i][2] - runs[i][1]
            if dur < min_segment_s and len(runs) > 1:
                left = runs[i - 1] if i > 0 else None
                right = runs[i + 1] if i + 1 < len(runs) else None
                if left is None:
                    target = right
                elif right is None:
                    target = left
                else:
                    left_dur = left[2] - left[1]
                    right_dur = right[2] - right[1]
                    target = left if left_dur >= right_dur else right
                if target is left:
                    target[2] = runs[i][2]
                    del runs[i]
                else:
                    target[1] = runs[i][1]
                    del runs[i]
                merged = True
            else:
                i += 1
        if not merged:
            break

    # Coalesce any adjacent same-class runs produced by the merge pass.
    i = 0
    while i + 1 < len(runs):
        if runs[i][0] == runs[i + 1][0]:
            runs[i][2] = runs[i + 1][2]
            del runs[i + 1]
        else:
            i += 1

    out: list[dict] = []
    for klass, s, e in runs:
        w_slice = [float(w or 0) for w in watts[s:e]]
        if not w_slice:
            continue
        avg = sum(w_slice) / len(w_slice)
        out.append(
            {
                "class": klass,
                "start_s": s,
                "end_s": e,
                "duration_s": e - s,
                "avg_w": round(avg),
                "max_w": int(max(w_slice)),
                "if": round(avg / ftp, 3) if ftp else None,
            }
        )
    return out
