# 2026-10-23 Faber 六趟：按坡度分段看踏频（核对本人"陡段 50–60、部分 45–50@约290W，坡顶平段未控踏频"）。
# 坡度：按速度积分得距离，每 50m 取海拔差；≥4% 记陡段、<2.5% 记平段。
# 用法：python this.py <raw>/2026-10-23_i200729542.json
import bisect
import json
import statistics as stats
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(sys.argv[1], encoding='utf-8'))
s = d['summary']
st = d['streams']
T = st['time']
W = [x or 0 for x in st['watts']]
C = [x or 0 for x in st['cadence']]
A = st['altitude']
V = [x or 0 for x in st['velocity_smooth']]


def utc(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00'))


def lap_window(lap):
    off = (utc(lap['timestamp_iso']) - utc(s['start_date'])).total_seconds()
    return bisect.bisect_left(T, off), bisect.bisect_left(T, off + lap['duration_sec'])


def grade_per_sample(a, b, step=50.0):
    """每个样本所在 50m 距离格的平均坡度（%）。"""
    dist = [0.0]
    for i in range(a + 1, b):
        dist.append(dist[-1] + V[i])
    grades = [0.0] * (b - a)
    k = 0
    while k < len(dist):
        j = bisect.bisect_left(dist, dist[k] + step, lo=k)
        j = min(j, len(dist) - 1)
        if j <= k:
            break
        g = (A[a + j] - A[a + k]) / max(dist[j] - dist[k], 1.0) * 100
        for m in range(k, j):
            grades[m] = g
        k = j
    grades[-1] = grades[-2] if len(grades) > 1 else 0.0
    return grades


def band(rows):
    cad = [c for c, _ in rows if c]
    pw = [w for _, w in rows]
    if not cad:
        return 'n=0'
    return f"n={len(rows):3d}s 踏频中位 {stats.median(cad):4.0f} 均功率 {stats.mean(pw):4.0f}W"


print('lap | 陡段(≥4%) | 平段(<2.5%) | 踏频<55 时长 | 45–50rpm 且30s均≥270W 时长 | 最后60s 踏频中位')
for n in (2, 4, 6, 8, 10, 12):
    a, b = lap_window(d['laps'][n - 1])
    g = grade_per_sample(a, b)
    steep = [(C[a + i], W[a + i]) for i in range(b - a) if g[i] >= 4]
    flat = [(C[a + i], W[a + i]) for i in range(b - a) if g[i] < 2.5]
    low55 = sum(1 for i in range(a, b) if 0 < C[i] < 55)
    hit = 0
    for i in range(a, b):
        lo, hi = max(a, i - 15), min(b, i + 15)
        if 45 <= C[i] <= 50 and sum(W[lo:hi]) / (hi - lo) >= 270:
            hit += 1
    tail = [c for c in C[b - 60:b] if c]
    print(f"{n:3d} | {band(steep)} | {band(flat)} | {low55:3d}s | {hit:3d}s | {stats.median(tail):.0f}")

print('\n每趟按 30s 分段：踏频中位 / 均功率 / 坡度')
for n in (2, 4, 6, 8, 10, 12):
    a, b = lap_window(d['laps'][n - 1])
    g = grade_per_sample(a, b)
    parts = []
    for i in range(a, b, 30):
        j = min(i + 30, b)
        cad = [c for c in C[i:j] if c]
        parts.append(f"{stats.median(cad) if cad else 0:.0f}/{sum(W[i:j]) / (j - i):.0f}/{stats.mean(g[i - a:j - a]):.1f}")
    print(f"lap{n:2d}: " + '  '.join(parts))
