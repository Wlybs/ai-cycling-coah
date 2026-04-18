import json
import subprocess

res = subprocess.run(['python', 'scripts/extract_ride_summary.py', 'i139065650'], capture_output=True, text=True, encoding='utf-8')
d = json.loads(res.stdout)

print("--- LAPS ---")
for l in d['laps']:
    print(f"Lap {l['lap']}: {l['duration']} @ {l['avg_watts']}W, HR {l['avg_hr']}, Cad {l['avg_cadence']}, MaxW {l.get('max_watts', 'N/A')}")

print("\n--- ICU INTERVALS ---")
for i in d['icu_intervals']:
    print(f"ICU: {i['elapsed']} @ {i['avg_watts']}W (NP {i['NP']}), HR {i['avg_hr']}")
