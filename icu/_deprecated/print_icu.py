import json
import sys

d = json.load(open('icu_data_warehouse/5_Activities_Detail/2026-04-12_i139065650.json', encoding='utf-8'))
icu = d['icu_intervals']
for i in icu:
    print(f"ICU: {i['start_time']}-{i['end_time']}s | {i['elapsed_time']}s @ {i['average_watts']}W")
