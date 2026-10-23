# 2026-10-23 核对 1 分钟 637W（90天与生涯最好，活动 i195605523）是否是可信的真实输出。
# 打印最佳 60s 窗口前后每 5s 的功率/踏频/速度/心率/海拔，以及单秒最高值和异常尖峰数。
# 用法：python this.py <warehouse>/5_Activities_Detail/2026-10-10_i195605523.json
import json
import statistics as stats
import sys

sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(sys.argv[1], encoding='utf-8'))
s = d['summary']
st = d['streams']
T = st['time']
W = [x or 0 for x in st['watts']]
C = [x or 0 for x in st['cadence']]
HR = st['heartrate']
A = st['altitude']
V = [x or 0 for x in st['velocity_smooth']]
print('name:', s.get('name'))
print('description:', s.get('description'))
print('device', s.get('device_name'), 'power_meter', s.get('power_meter'), 'temp', s.get('average_temp'),
      'RPE', s.get('icu_rpe'), 'feel', s.get('feel'))


def best(L):
    b, at = 0.0, 0
    run = sum(W[:L])
    for i in range(len(W) - L + 1):
        if i:
            run += W[i + L - 1] - W[i - 1]
        if T[i + L - 1] - T[i] == L - 1 and run / L > b:
            b, at = run / L, i
    return b, at


p60, i60 = best(60)
p30, i30 = best(30)
print(f"best60 {p60:.1f}W at elapsed {T[i60]}s ({T[i60] / 60:.1f}min)；best30 {p30:.1f}W at {T[i30]}s")
seg = W[i60:i60 + 60]
print(f"60s 内：单秒最高 {max(seg)}W  >1500W 的秒数 {sum(1 for w in seg if w > 1500)}  "
      f"踏频中位 {stats.median([c for c in C[i60:i60 + 60] if c])}  "
      f"海拔 {A[i60]:.1f}→{A[i60 + 59]:.1f}m  距离 {sum(V[i60:i60 + 60]):.0f}m")
print('全趟单秒最高功率', max(W), ' 全趟最高心率', max(h for h in HR if h))
print('\n每 5s（从窗口前 30s 到窗口后 60s）：功率 / 踏频 / 速度km/h / 心率 / 海拔')
for i in range(max(0, i60 - 30), min(len(W) - 5, i60 + 120), 5):
    tag = '*' if i60 <= i < i60 + 60 else ' '
    print(f"{tag} t{T[i]:5d} {sum(W[i:i + 5]) / 5:6.0f}W {stats.mean(C[i:i + 5]):4.0f}rpm "
          f"{3.6 * stats.mean(V[i:i + 5]):5.1f} {HR[i]} {A[i]:6.1f}")
