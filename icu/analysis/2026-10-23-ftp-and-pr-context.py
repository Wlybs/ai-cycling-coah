# 2026-10-23 FTP 与 Faber 测试时机的补充核对（只读）。
# 1) 10/4 Crazies 最佳 20min 窗口的标准化功率与波动：判断那次 295W/HR187 是不是稳态
# 2) 10/18 与今天各持续段的心率爬升速度（bpm/min，取第3分钟到结束）
# 3) Faber 两个 PR（8/8、9/8）当天及前几天的 CTL/ATL/TSB
# 用法：python this.py <warehouse 根目录>
import json
import pathlib
import statistics as stats
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(sys.argv[1])
DETAIL = ROOT / 'icu_data_warehouse' / '5_Activities_Detail'


def load(name):
    d = json.loads((DETAIL / name).read_text(encoding='utf-8'))
    st = d['streams']
    return d, st['time'], [x or 0 for x in st['watts']], st['heartrate']


def best_window(T, W, L):
    best, at = 0.0, None
    run = sum(W[:L])
    for i in range(len(W) - L + 1):
        if i:
            run += W[i + L - 1] - W[i - 1]
        if T[i + L - 1] - T[i] == L - 1 and run / L > best:
            best, at = run / L, i
    return best, at


def norm_power(seg):
    roll = [sum(seg[i:i + 30]) / 30 for i in range(len(seg) - 29)]
    return stats.mean([r ** 4 for r in roll]) ** 0.25


def hr_slope(HR, a, b):
    """第3分钟起到结束，按分钟均值做最小二乘斜率（bpm/min）。"""
    mins = [stats.mean([h for h in HR[i:i + 60] if h]) for i in range(a + 120, b - 59, 60)]
    xs = list(range(len(mins)))
    if len(xs) < 3:
        return float('nan')
    mx, my = stats.mean(xs), stats.mean(mins)
    return sum((x - mx) * (y - my) for x, y in zip(xs, mins)) / sum((x - mx) ** 2 for x in xs)


print('== 10/4 最佳20min窗口')
d, T, W, HR = load('2026-10-04_i193197201.json')
p, i = best_window(T, W, 1200)
seg = W[i:i + 1200]
np_ = norm_power(seg)
print(f"均功率 {p:.1f}W  NP {np_:.1f}W  VI {np_ / p:.3f}  >350W {sum(1 for w in seg if w > 350)}s  "
      f"<200W {sum(1 for w in seg if w < 200)}s  HR均 {stats.mean([h for h in HR[i:i + 1200] if h]):.1f}  "
      f"HR最高 {max(h for h in HR[i:i + 1200] if h)}  起点 {T[i] / 60:.1f}min")
print('全趟最高心率', max(h for h in HR if h), ' 名称:', d['summary'].get('name'), '| 描述:', d['summary'].get('description'))

print('\n== 持续段心率爬升（第3分钟起）')
for name, spans in [('2026-10-18_i198487369.json', None), ('2026-10-23_i200729542.json', None)]:
    d, T, W, HR = load(name)
    for w in d.get('icu_intervals') or []:
        if w.get('type') == 'WORK' and (w.get('moving_time') or 0) >= 480 and (w.get('average_watts') or 0) >= 265:
            a, b = w['start_index'], w['end_index']
            print(f"{name[:10]} {w['moving_time'] / 60:4.1f}min {w['average_watts']}W NP{norm_power(W[a:b]):.0f} "
                  f"HR {HR[a + 120]}→{HR[b - 1]} 斜率 {hr_slope(HR, a, b):+.2f} bpm/min")

print('\n== Faber PR 日前后负荷（wellness）')
rows = json.loads((ROOT / 'icu_data_warehouse' / '2_Wellness' / 'wellness_history.json').read_text(encoding='utf-8'))
rows = rows if isinstance(rows, list) else rows.get('data')
by_day = {r['id']: r for r in rows}
for day in ['2026-08-0' + str(k) for k in range(4, 10)] + ['2026-09-0' + str(k) for k in range(4, 10)]:
    r = by_day.get(day)
    if r:
        ctl, atl = r.get('ctl') or 0, r.get('atl') or 0
        print(f"{day} CTL {ctl:5.1f} ATL {atl:5.1f} TSB {ctl - atl:+6.1f} HRV {r.get('hrv')} RHR {r.get('restingHR')}")
