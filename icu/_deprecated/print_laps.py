import json
import subprocess

ids = ["i137083876", "i137331114", "i137513392", "i138057807", "i138344084", "i138607618"]

for i in ids:
    res = subprocess.run(["python", "scripts/extract_ride_summary.py", i], capture_output=True, text=True, encoding='utf-8')
    try:
        r = json.loads(res.stdout)
        d = r['header']['date']
        print(f"\n=== {d} | {r['header']['name']} ===")
        for l in r['laps']:
            print(f"Lap {l['lap']}: {l['duration']} @ {l['avg_watts']}W, HR {l['avg_hr']}, Cad {l['avg_cadence']}, MaxW {l.get('max_watts', 'N/A')}")
    except json.JSONDecodeError as e:
        print(f"Error parsing json for {i}: {e}")
