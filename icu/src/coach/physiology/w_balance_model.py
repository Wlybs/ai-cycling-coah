import math
from typing import Iterable, Sequence

from .types import LapWBal, WBalanceSeries


def compute_tau(cp: float, mean_power_below_cp: float) -> float:
    d_cp = cp - mean_power_below_cp
    return 546.0 * math.exp(-0.01 * d_cp) + 316.0


def compute_w_balance(
    stream: Sequence[float],
    *,
    cp: float,
    w_prime: float,
    activity_id: str,
    laps: Iterable[dict],
    dt: float = 1.0,
) -> WBalanceSeries:
    below = [p for p in stream if p is not None and p <= cp]
    mean_below = sum(below) / len(below) if below else cp * 0.6
    tau = compute_tau(cp, mean_below)

    series = []
    w_bal = float(w_prime)
    for p in stream:
        if p is None:
            series.append(int(round(w_bal)))
            continue
        if p > cp:
            w_bal = w_bal - (p - cp) * dt
        else:
            w_bal = w_prime - (w_prime - w_bal) * math.exp(-dt / tau)
        series.append(int(round(w_bal)))

    min_bal = min(series)
    min_idx = series.index(min_bal)
    sec_below_15 = sum(1 for v in series if v < 0.15 * w_prime)

    lap_rows = []
    for lap in laps:
        start = int(lap["start_s"])
        end = min(int(lap["end_s"]), len(series) - 1)
        if end <= start:
            continue
        start_val = series[start]
        end_val = series[end]
        depletion = (start_val - end_val) / w_prime * 100 if w_prime else 0.0
        lap_rows.append(
            LapWBal(
                lap_index=int(lap["lap_index"]),
                type=lap.get("type", "steady"),
                w_bal_start_j=start_val,
                w_bal_end_j=end_val,
                depletion_pct=round(depletion, 1),
            )
        )

    w_prime_used = int(round(w_prime - min_bal)) if min_bal < w_prime else 0

    return WBalanceSeries(
        activity_id=activity_id,
        cp_used_w=int(cp),
        w_prime_used_j=w_prime_used,
        tau_s=round(tau, 1),
        min_w_bal_j=min_bal,
        min_w_bal_pct=round(min_bal / w_prime * 100, 1),
        min_w_bal_timestamp_s=min_idx,
        seconds_below_15pct=sec_below_15,
        laps=lap_rows,
        w_bal_series_1hz=series,
    )
