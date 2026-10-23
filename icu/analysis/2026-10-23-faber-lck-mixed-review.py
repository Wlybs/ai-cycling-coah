# 2026-10-23 Faber 六趟整坡SST + Mandai/New Tiew 转场 + LCK 3组阈值 混合课复盘。
# 起爆校准沿 stream-onset-detect：阈值按每段计划目标功率的比例（onset 0.91/0.83/0.77、offset 0.80，
# 与 2026-10-20 8×3 脚本 320/290/270、280 对 350W 目标的比例相同）；lap 按 FIT 时间戳映射 streams.time。
# 原始数据：icu/icu_data_warehouse/9_Coach_Raw/2026-10-23-faber-lck-mixed/
# 用法：python this.py <raw>/2026-10-23_i200729542.json
import bisect
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(sys.argv[1], encoding='utf-8'))
s = d['summary']
st = d['streams']
T = st['time']
W = [x or 0 for x in st['watts']]
HR = st['heartrate']
C = st['cadence']
A = st['altitude']
V = st['velocity_smooth']
N = len(T)

ONSET = (0.91, 0.83, 0.77)
OFFSET = 0.80
WIN = 8
# FIT 圈号 → 计划目标功率（revision26/28：Faber 六趟约 280W；LCK 290/295/295）
TARGET = {2: 280, 4: 280, 6: 280, 8: 280, 10: 280, 12: 280, 15: 290, 17: 295, 19: 295}


def utc(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00'))


T0 = utc(s['start_date'])


def lap_window(lap):
    off = (utc(lap['timestamp_iso']) - T0).total_seconds()
    return bisect.bisect_left(T, off), bisect.bisect_left(T, off + lap['duration_sec'])


def mean(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else float('nan')


def norm_power(seg):
    if len(seg) < 30:
        return mean(seg)
    roll = [sum(seg[i:i + 30]) / 30 for i in range(len(seg) - 29)]
    return mean([r ** 4 for r in roll]) ** 0.25


def onset(si, tgt):
    a, b, c = (r * tgt for r in ONSET)
    for i in range(max(0, si - WIN), min(N - 3, si + WIN)):
        if W[i] >= a and W[i + 1] >= b and W[i + 2] >= c:
            return i
    return si


def offset(o, ei, tgt):
    for i in range(min(N - 2, ei + WIN), o + 10, -1):
        if W[i] >= OFFSET * tgt:
            return i + 1
    return ei


def band_time(a, b, lo, hi):
    return sum(1 for w in W[a:b] if lo <= w <= hi)


def seg_summary(tag, a, b):
    hr = [h for h in HR[a:b] if h]
    dist = sum(v or 0 for v in V[a:b])
    print(f"{tag}: idx {a}-{b} elapsed {T[b - 1] - T[a] + 1}s samples(moving) {b - a}s dist {dist / 1000:.1f}km "
          f"avgW {mean(W[a:b]):.0f} NP {norm_power(W[a:b]):.0f} HR {mean(hr):.0f} "
          f"t185-205 {band_time(a, b, 185, 205)}s t>=220 {band_time(a, b, 220, 9999)}s t<100 {band_time(a, b, 0, 99)}s")


for k in ['name', 'start_date_local', 'moving_time', 'elapsed_time', 'distance', 'icu_rpe', 'feel', 'average_temp',
          'min_temp', 'max_temp', 'total_elevation_gain', 'icu_training_load', 'icu_average_watts',
          'icu_weighted_avg_watts', 'icu_intensity', 'icu_ftp', 'icu_joules', 'average_heartrate', 'max_heartrate',
          'lthr', 'carbs_ingested']:
    print(k, '=', s.get(k))

print('\n== lap 对齐核对：文件索引 vs 时间戳映射')
laps = d['laps']
for lap in laps:
    a, b = lap_window(lap)
    print(f"lap{lap['lap_number']:2d} file {lap['stream_start_index']}-{lap['stream_end_index']} ts {a}-{b} "
          f"fitAvg {lap['avg_watts']} streamAvg {mean(W[a:b]):.0f}")

print('\n== 工作段（stream onset 校准）')
print('lap tgt lapsi detsi dsi dei  dur  lapW  detW   NP  1/3  2/3  3/3  HRavg HRst HRend HRmax '
      'cadNZ cad<70% dAlt grade  kmh  min5s max5s')
reps = []
for num, tgt in TARGET.items():
    lap = laps[num - 1]
    si, ei = lap_window(lap)
    o = onset(si, tgt)
    f = offset(o, ei, tgt)
    seg = W[o:f]
    n = f - o
    thirds = [mean(seg[k * n // 3:(k + 1) * n // 3]) for k in range(3)]
    cad_nz = [c for c in C[o:f] if c]
    hr = [h for h in HR[o:f] if h]
    dalt = A[f - 1] - A[o]
    dist = sum(v or 0 for v in V[o:f])
    roll5 = [sum(seg[i:i + 5]) / 5 for i in range(n - 4)]
    print(f"{num:3d} {tgt} {si:5d} {o:5d} {o - si:+3d} {f - ei:+3d} {n:4d} {mean(W[si:ei]):5.0f} {mean(seg):5.1f} "
          f"{norm_power(seg):4.0f} {thirds[0]:4.0f} {thirds[1]:4.0f} {thirds[2]:4.0f}  {mean(hr):5.1f} {HR[o]:4d} "
          f"{HR[f - 1]:5d} {max(hr):5d} {mean(cad_nz):5.1f} {100 * sum(1 for c in cad_nz if c < 70) / len(cad_nz):6.0f} "
          f"{dalt:5.1f} {100 * dalt / dist:5.2f} {3.6 * dist / n:4.1f} {min(roll5):5.0f} {max(roll5):5.0f}")
    reps.append((num, tgt, o, f))

print('\n== 组间恢复（上一段 offset → 下一段 onset）')
for (n1, _, _, f1), (n2, _, o2, _) in zip(reps, reps[1:]):
    hr = [h for h in HR[f1:o2] if h]
    print(f"lap{n1}->lap{n2}: elapsed {T[o2] - T[f1]}s avgW {mean(W[f1:o2]):.0f} HRend(工作) {HR[f1 - 1]} "
          f"HRmin {min(hr)} HR at next onset {HR[o2]}")

faber = [r for r in reps if r[1] == 280]
lck = [r for r in reps if r[1] != 280]
for tag, group in [('Faber', faber), ('LCK', lck)]:
    work = sum(f - o for _, _, o, f in group)
    joules = sum(sum(W[o:f]) for _, _, o, f in group)
    print(f"{tag} 工作合计 {work}s 加权均 {joules / work:.1f}W")

print('\n== 非工作段')
seg_summary('出发→Faber首趟', 0, faber[0][2])
seg_summary('Faber末趟→LCK首组', faber[-1][3], lck[0][2])
seg_summary('LCK末组→结束', lck[-1][3], N)
gaps = [(T[i - 1], T[i] - T[i - 1]) for i in range(1, N) if T[i] - T[i - 1] >= 60]
print('≥60s 暂停（起点elapsed, 时长）:', gaps)

print('\n== 今日连续窗口最佳（只取无暂停窗口）')
for L in [300, 600, 720, 1200]:
    best = 0
    run = sum(W[:L])
    for i in range(N - L + 1):
        if i:
            run += W[i + L - 1] - W[i - 1]
        if T[i + L - 1] - T[i] == L - 1 and run / L > best:
            best = run / L
    print(f"best {L}s {best:.0f}W")
