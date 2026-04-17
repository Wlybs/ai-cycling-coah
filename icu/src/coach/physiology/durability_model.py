from datetime import datetime, timezone
from typing import List

from .types import DurabilityCurve

CHECKPOINTS_KJ = [500, 1500, 2000, 2500]
DURATIONS_S = [60, 300, 1200]


def _mmp_at_window(stream, start_idx, duration_s):
    end = start_idx + duration_s
    if end > len(stream):
        return None
    best = 0.0
    window_sum = sum(stream[start_idx:start_idx + duration_s])
    best = window_sum
    for i in range(start_idx + 1, end):
        window_sum += stream[i + duration_s - 1] if i + duration_s - 1 < len(stream) else 0
        window_sum -= stream[i - 1]
        if i + duration_s > len(stream):
            break
        best = max(best, window_sum)
    return best / duration_s


def _index_at_cumulative_kj(stream, target_kj):
    kj = 0.0
    for i, p in enumerate(stream):
        kj += (p or 0) / 1000.0
        if kj >= target_kj:
            return i
    return None


def fit_durability(rides: list) -> DurabilityCurve:
    if not rides:
        return DurabilityCurve(
            generated_at=datetime.now(timezone.utc).isoformat(),
            sample_size_rides=0,
            fresh_mmp_w={f"{d}s": 0 for d in DURATIONS_S},
            fatigued_mmp_w={f"{k}kj": {f"{d}s": 0 for d in DURATIONS_S} for k in CHECKPOINTS_KJ[1:]},
            decay_rate_pct_per_1000kj={f"{d}s": 0.0 for d in DURATIONS_S},
        )

    fresh_by_dur = {d: [] for d in DURATIONS_S}
    fatigued = {k: {d: [] for d in DURATIONS_S} for k in CHECKPOINTS_KJ[1:]}

    for ride in rides:
        stream = ride["power_stream"]
        fresh_idx = _index_at_cumulative_kj(stream, CHECKPOINTS_KJ[0])
        if fresh_idx is None:
            continue
        for d in DURATIONS_S:
            val = _mmp_at_window(stream, 0, d)
            if val is not None:
                fresh_by_dur[d].append(val)
        for kj_target in CHECKPOINTS_KJ[1:]:
            idx = _index_at_cumulative_kj(stream, kj_target)
            if idx is None:
                continue
            for d in DURATIONS_S:
                val = _mmp_at_window(stream, idx, d)
                if val is not None:
                    fatigued[kj_target][d].append(val)

    fresh_mmp = {f"{d}s": int(round(max(fresh_by_dur[d], default=0))) for d in DURATIONS_S}
    fatigued_out = {
        f"{k}kj": {
            f"{d}s": int(round(sum(fatigued[k][d]) / len(fatigued[k][d]))) if fatigued[k][d] else 0
            for d in DURATIONS_S
        }
        for k in CHECKPOINTS_KJ[1:]
    }
    decay = {}
    for d in DURATIONS_S:
        fresh_w = fresh_mmp[f"{d}s"] or 1
        fat_w = fatigued_out["2500kj"][f"{d}s"]
        delta_pct = max(0.0, (fresh_w - fat_w) / fresh_w * 100 / 2.5)
        decay[f"{d}s"] = round(delta_pct, 2)

    return DurabilityCurve(
        generated_at=datetime.now(timezone.utc).isoformat(),
        sample_size_rides=len(rides),
        fresh_mmp_w=fresh_mmp,
        fatigued_mmp_w=fatigued_out,
        decay_rate_pct_per_1000kj=decay,
    )
