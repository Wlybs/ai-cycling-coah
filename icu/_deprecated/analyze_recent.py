import json
import subprocess
import os
import sys

ids = ["i137083876", "i137331114", "i137513392", "i138057807", "i138344084"]

for i in ids:
    res = subprocess.run(["python", "scripts/extract_ride_summary.py", i], capture_output=True, text=True, encoding='utf-8')
    try:
        r = json.loads(res.stdout)
        d = r['header']['date']
        print(f"\n=== {d} | {r['header']['name']} ===")
        print(f"Class: {r['training_classification']['description']}")
        m = r['metrics']
        print(f"Metrics: TSS={m['TSS']} NP={m['NP']} AP={m['AP']} IF={m['IF']} VI={m['VI']:.3f} HR={m['avg_hr']} Cad={m['avg_cadence']} Decoupling={m.get('decoupling','N/A')} EF={m.get('EF','N/A')}")
        f = r['form']
        print(f"Form: CTL={f['CTL']} ATL={f['ATL']} TSB={f['TSB']}")
        pz = [z['zone']+":"+z['pct'] for z in r['power_zones'] if float(z['pct'][:-1]) > 1.0]
        print(f"Zones: {', '.join(pz)}")
        print("Intervals:")
        for j, wi in enumerate(r['work_intervals']):
            if j >= 5: # Limit to 5 intervals to save space
                print("  ... and more")
                break
            print(f"  {j+1}: {wi['duration']} @ {wi['avg_watts']}W, HR {wi['avg_hr']}, Cad {wi['avg_cadence']}")
    except json.JSONDecodeError as e:
        print(f"Error parsing json for {i}: {e}")
        print(res.stdout[:200])

