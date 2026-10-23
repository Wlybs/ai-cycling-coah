# 2026-10-23 混合课追问核对：用原始流检验本人体感描述。
# 1) LCK 第2/3组逐分钟功率/心率（本人：第三组前5min踩高、5–9min压住、最后1min加）
# 2) Faber 六趟踏频分布（本人：目标 50–60rpm 低踏频力量SST）
# 3) 转场 lap14 在 190–210W 时的心率与踏频，对照同日出发段和近几次户外骑行（本人：200W 约150bpm 偏高、踏频不自主变低）
# 用法：python this.py <warehouse>/5_Activities_Detail
import bisect
import json
import pathlib
import statistics as stats
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DETAIL = pathlib.Path(sys.argv[1])
TODAY = DETAIL / '2026-10-23_i200729542.json'


def utc(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00'))


def load(path):
    d = json.loads(path.read_text(encoding='utf-8'))
    st = d['streams']
    return d, st['time'], [x or 0 for x in st['watts']], st['heartrate'], [x or 0 for x in st['cadence']]


def lap_window(d, T, lap):
    off = (utc(lap['timestamp_iso']) - utc(d['summary']['start_date'])).total_seconds()
    return bisect.bisect_left(T, off), bisect.bisect_left(T, off + lap['duration_sec'])


def per_minute(tag, W, HR, a, b):
    print(tag)
    for k, i in enumerate(range(a, b, 60)):
        j = min(i + 60, b)
        hr = [h for h in HR[i:j] if h]
        print(f"  min{k + 1:2d} {sum(W[i:j]) / (j - i):5.0f}W HR {stats.mean(hr):5.1f}")


def matched_windows(T, W, HR, C, a, b, lo=190, hi=210, win=60):
    """无暂停 60s 窗口里均功率落在 [lo, hi] 的 (心率均值, 非零踏频均值)。"""
    out = []
    for i in range(a, b - win, 15):
        if T[i + win - 1] - T[i] != win - 1:
            continue
        p = sum(W[i:i + win]) / win
        hr = [h for h in HR[i:i + win] if h]
        cad = [c for c in C[i:i + win] if c]
        if lo <= p <= hi and len(hr) > 50 and len(cad) > 50:
            out.append((stats.mean(hr), stats.mean(cad)))
    return out


def describe(tag, rows):
    if not rows:
        print(f"{tag}: 无匹配窗口")
        return
    hrs = [r[0] for r in rows]
    cads = [r[1] for r in rows]
    print(f"{tag}: 窗口{len(rows)} HR中位 {stats.median(hrs):.0f} 踏频中位 {stats.median(cads):.0f}")


d, T, W, HR, C = load(TODAY)
laps = d['laps']
win = {lap['lap_number']: lap_window(d, T, lap) for lap in laps}

per_minute('== LCK 第2组（lap17）逐分钟', W, HR, *win[17])
per_minute('== LCK 第3组（lap19）逐分钟', W, HR, *win[19])

print('\n== Faber 六趟非零踏频分布')
for n in (2, 4, 6, 8, 10, 12):
    a, b = win[n]
    cad = [c for c in C[a:b] if c]
    bands = [sum(1 for c in cad if lo <= c < hi) / len(cad) * 100 for lo, hi in ((0, 50), (50, 60), (60, 70), (70, 999))]
    print(f"lap{n:2d} 中位 {stats.median(cad):.0f}rpm  <50 {bands[0]:.0f}%  50–60 {bands[1]:.0f}%  60–70 {bands[2]:.0f}%  ≥70 {bands[3]:.0f}%")

print('\n== 190–210W 时心率/踏频（60s 无暂停窗口，跳过前20min）')
describe('今天 lap1 出发段', matched_windows(T, W, HR, C, 1200, win[1][1]))
describe('今天 lap13 Faber→市区', matched_windows(T, W, HR, C, *win[13]))
describe('今天 lap14 Mandai→LCK', matched_windows(T, W, HR, C, *win[14]))
a, b = win[14]
half = (a + b) // 2
describe('  lap14 前半', matched_windows(T, W, HR, C, a, half))
describe('  lap14 后半', matched_windows(T, W, HR, C, half, b))

print('\n== 近期户外骑行同功率对照（Ride，跳过前20min）')
for path in sorted(DETAIL.glob('2026-*.json')):
    if path == TODAY or path.name < '2026-09-20':
        continue
    dd, TT, WW, HH, CC = load(path)
    s = dd['summary']
    if s.get('type') not in (None, 'Ride') or s.get('trainer'):
        continue
    if 'Zwift' in (s.get('name') or ''):
        continue
    describe(f"{path.name[:10]} {(s.get('name') or '')[:16]:16s} {s.get('average_temp')}°C",
             matched_windows(TT, WW, HH, CC, 1200, len(TT)))
