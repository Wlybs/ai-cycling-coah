# 2026-10-23 骑手画像：功率曲线（近90天 vs 生涯）、W/kg、各时长相对生涯最好的落差、
# ICU 功率模型（CP/W′/Pmax）、近两周静息心率/HRV、当前负荷。只读。
# 用法：python this.py <icu 根目录>
import json
import pathlib
import statistics as stats
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(sys.argv[1])
CURVES = ROOT / 'icu_data_warehouse' / '3_PowerData'
DURATIONS = (5, 15, 30, 60, 120, 180, 300, 600, 1200, 3600)
WEIGHTS = (61.0, 63.0)


def load_curve(name):
    d = json.loads((CURVES / name).read_text(encoding='utf-8'))
    item = d['list'][0]
    acts = d.get('activities') or {}
    return item, acts


def at(item, acts, secs):
    if secs not in item['secs']:
        return None, None, None
    k = item['secs'].index(secs)
    aid = item['activity_id'][k]
    date = (acts.get(aid) or {}).get('start_date_local', '')[:10]
    return item['watts'][k], aid, date


recent, recent_acts = load_curve('power_curves_90d.json')
career, career_acts = load_curve('power_curves_all_time.json')

print('时长 | 近90天 W (日期) | 生涯 W (日期) | 落差 | 近90天 W/kg @61/63 | 生涯 W/kg @61/63')
for secs in DURATIONS:
    w90, _, d90 = at(recent, recent_acts, secs)
    wall, _, dall = at(career, career_acts, secs)
    if w90 is None or wall is None:
        continue
    drop = (w90 - wall) / wall * 100
    wkg90 = '/'.join(f"{w90 / kg:.2f}" for kg in WEIGHTS)
    wkgall = '/'.join(f"{wall / kg:.2f}" for kg in WEIGHTS)
    print(f"{secs:5d}s | {w90:4d} ({d90}) | {wall:4d} ({dall}) | {drop:+5.1f}% | {wkg90} | {wkgall}")

for label, item in (('近90天', recent), ('生涯', career)):
    for m in item.get('powerModels') or []:
        print(f"{label} 模型 {m['type']:12s} CP {m.get('criticalPower')} W′ {m.get('wPrime')} J Pmax {m.get('pMax')}")

snap = json.loads((ROOT / 'coach_memory' / 'athlete_snapshot.json').read_text(encoding='utf-8'))
print('\nsnapshot', snap['updated_at'], 'ftp_set', snap['ftp_set'], 'lthr', snap.get('lthr'),
      'w_prime', snap.get('w_prime'), 'weight', snap.get('weight_kg'))
for kg in WEIGHTS:
    print(f"  FTP {snap['ftp_set']}W @ {kg}kg = {snap['ftp_set'] / kg:.2f} W/kg")

rows = json.loads((ROOT / 'icu_data_warehouse' / '2_Wellness' / 'wellness_history.json').read_text(encoding='utf-8'))
rows = rows if isinstance(rows, list) else rows.get('data')
last14 = rows[-14:]
rhr = [r['restingHR'] for r in last14 if r.get('restingHR')]
hrv = [r['hrv'] for r in last14 if r.get('hrv')]
print(f"\n近14天 静息心率 均{stats.mean(rhr):.1f} 范围{min(rhr)}–{max(rhr)}；HRV 均{stats.mean(hrv):.1f} 范围{min(hrv):.0f}–{max(hrv):.0f}")

ft = json.loads((ROOT / 'coach_memory' / 'fitness_trend.json').read_text(encoding='utf-8'))
trend = ft['trend']
print('当前负荷', ft['current'])
print('90天内 CTL 最低', min(trend, key=lambda r: r['ctl'])['ctl'], '最高', max(trend, key=lambda r: r['ctl'])['ctl'])
