import json
with open('latest_6_rides.json', encoding='utf-16') as f:
    rides = json.load(f)
rides.reverse()
for r in rides:
    d = r['header']['date']
    if d <= '2026-04-02':
        continue
    print(f"\n=== {d} | {r['header']['name']} ===")
    print(f"Class: {r['training_classification']['description']}")
    m = r['metrics']
    print(f"Metrics: TSS={m['TSS']} NP={m['NP']} AP={m['AP']} IF={m['IF']} VI={m['VI']:.3f} HR={m['avg_hr']} Cad={m['avg_cadence']} Decoupling={m.get('decoupling','N/A')} EF={m.get('EF','N/A')}")
    f = r['form']
    print(f"Form: CTL={f['CTL']} ATL={f['ATL']} TSB={f['TSB']}")
    pz = [z['zone']+":"+z['pct'] for z in r['power_zones'] if float(z['pct'][:-1]) > 1.0]
    print(f"Zones: {', '.join(pz)}")
    print("Intervals:")
    for i, wi in enumerate(r['work_intervals']):
        print(f"  {i+1}: {wi['duration']} @ {wi['avg_watts']}W, HR {wi['avg_hr']}, Cad {wi['avg_cadence']}")
