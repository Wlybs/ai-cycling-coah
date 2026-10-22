# Compare HR>=180/185/188 time and lap reps across Faber VO2 sessions.
# Usage: python this.py <raw>/*.json
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
for p in sys.argv[1:]:
    d=json.load(open(p,encoding='utf-8'));s=d['summary'];st=d['streams'];HR=st['heartrate'];W=[x or 0 for x in st['watts']]
    print(p, s.get('name','').replace('\n',' | '), 'rpe',s.get('icu_rpe'),'feel',s.get('feel'),'temp',round(s.get('average_temp') or 0,1))
    for t in [180,185,188]: print('  HR>=',t, sum(1 for h in HR if h and h>=t),'s')
    print('  W>=330:',sum(1 for w in W if w>=330),'s')
    ivs=[w for w in d['icu_intervals'] if (w.get('average_watts') or 0)>300 and 150<(w.get('moving_time') or 0)<330]
    for w in ivs: print('   ',w['moving_time'],'s',w['average_watts'],'W hr',w.get('average_heartrate'),'/',w.get('max_heartrate'),'cad',round(w.get('average_cadence') or 0))
