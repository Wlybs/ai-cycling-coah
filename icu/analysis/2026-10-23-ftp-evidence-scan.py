# 2026-10-23 FTP 证据扫描：近六周每次骑行的连续最佳窗口与持续工作段（只读）。
# 每个窗口：均功率、均心率、末分钟心率、非零踏频、窗口前已做功(kJ)、温度、ICU RPE/feel。
# 另列 90 天负荷极值，供"明天骑不骑"参考。
# 用法：python this.py <warehouse 根目录>
import json
import pathlib
import statistics as stats
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(sys.argv[1])
DETAIL = ROOT / 'icu_data_warehouse' / '5_Activities_Detail'
WINDOWS = (300, 480, 600, 720, 1200, 1800)


def best_window(T, W, L):
    best, at = 0.0, None
    run = sum(W[:L])
    for i in range(len(W) - L + 1):
        if i:
            run += W[i + L - 1] - W[i - 1]
        if T[i + L - 1] - T[i] == L - 1 and run / L > best:
            best, at = run / L, i
    return best, at


def describe(T, W, HR, C, i, L):
    hr = [h for h in HR[i:i + L] if h]
    tail = [h for h in HR[i + L - 60:i + L] if h]
    cad = [c for c in C[i:i + L] if c]
    kj_before = sum(W[:i]) / 1000
    return (f"HR均{stats.mean(hr):5.1f} 末分钟{stats.mean(tail):5.1f} 踏频{stats.median(cad):3.0f} "
            f"前置{kj_before:5.0f}kJ/{T[i] / 3600:4.2f}h")


ft = json.loads((ROOT / 'coach_memory' / 'fitness_trend.json').read_text(encoding='utf-8'))
trend = ft['trend']
peak_atl = max(trend, key=lambda r: r.get('atl') or 0)
low_tsb = min(trend, key=lambda r: r['tsb'] if r.get('tsb') is not None else 99)
print('90天 ATL 最高:', peak_atl)
print('90天 TSB 最低:', low_tsb)

for path in sorted(DETAIL.glob('2026-*.json')):
    if path.name < '2026-09-08':
        continue
    d = json.loads(path.read_text(encoding='utf-8'))
    s = d['summary']
    st = d['streams']
    if not isinstance(st, dict) or not st.get('watts'):
        continue
    T = st['time']
    W = [x or 0 for x in st['watts']]
    HR = st.get('heartrate') or [0] * len(W)
    C = [x or 0 for x in (st.get('cadence') or [0] * len(W))]
    name = (s.get('name') or '').replace('\n', ' ')[:28]
    print(f"\n### {path.name[:10]} {name} | {s.get('type')} trainer={s.get('trainer')} "
          f"{s.get('average_temp')}°C TSS{s.get('icu_training_load')} RPE{s.get('icu_rpe')} feel{s.get('feel')} "
          f"移动{(s.get('moving_time') or 0) / 3600:.2f}h")
    for L in WINDOWS:
        if len(W) < L:
            continue
        p, i = best_window(T, W, L)
        if i is not None and p >= 240:
            print(f"  best{L // 60:3d}min {p:5.1f}W  " + describe(T, W, HR, C, i, L))
    for w in d.get('icu_intervals') or []:
        mt = w.get('moving_time') or 0
        aw = w.get('average_watts') or 0
        if w.get('type') == 'WORK' and mt >= 480 and aw >= 265:
            print(f"  WORK {mt / 60:5.1f}min {aw}W HR均{w.get('average_heartrate')} 最高{w.get('max_heartrate')} "
                  f"踏频{round(w.get('average_cadence') or 0)} 起点{(w.get('start_time') or 0) / 3600:4.2f}h")
