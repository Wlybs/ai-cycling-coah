# 2026-10-20 8x3min VO2 rep review (stream onset 320/290/270, offset 280).
# Raw data: icu/icu_data_warehouse/9_Coach_Raw/2026-10-20-eight-by-three-vo2/
# Usage: python this.py <raw>/2026-10-20_i199292147.json
import json,sys,statistics as S
sys.stdout.reconfigure(encoding='utf-8')
d=json.load(open(sys.argv[1],encoding='utf-8'))
s=d['summary']
for k in ['name','description','start_date_local','moving_time','elapsed_time','icu_rpe','feel','average_temp','total_elevation_gain','decoupling','icu_hr_zone_times','icu_zone_times','carbs_ingested','icu_w_prime','icu_pm_cp','icu_pm_w_prime','icu_pm_ftp','icu_rolling_ftp','icu_rolling_w_prime','icu_sweet_spot_min','lthr','athlete_max_hr','icu_resting_hr']:
    print(k,'=',s.get(k))
st=d['streams'];W=[x or 0 for x in st['watts']];HR=st['heartrate'];C=st['cadence'];A=st['altitude'];V=st['velocity_smooth'];WB=st['w_bal']
ivs=[w for w in d['icu_intervals'] if (w.get('average_watts') or 0)>300 and 150<(w.get('moving_time') or 0)<200]
WIN=8
def onset(si):
    for i in range(max(0,si-WIN),min(len(W)-3,si+WIN)):
        if W[i]>=320 and W[i+1]>=290 and W[i+2]>=270: return i
    return si
def offset(o,ei):
    for i in range(min(len(W)-2,ei+WIN),o+10,-1):
        if W[i]>=280: return i+1
    return ei
def m(a): a=[x for x in a if x is not None]; return sum(a)/len(a) if a else float('nan')
prev_e=None
print('rep lapsi detsi dsi lapavg detavg detdur dei  p0-30 p30-150 p150-end  hrAvg hrMax hrStart hrEnd cad  dAlt grade% wbalMin  recDur recW hrRecEnd')
rows=[]
for n,w in enumerate(ivs,1):
    si,ei=w['start_index'],w['end_index']
    o=onset(si); f=offset(o,ei)
    seg=W[o:f]
    a0=m(seg[:30]);a1=m(seg[30:150]);a2=m(seg[150:])
    dalt=(A[f-1]-A[o]) if A[o] is not None and A[f-1] is not None else None
    dist=sum(v or 0 for v in V[o:f])
    grade=dalt/dist*100 if dist and dalt is not None else None
    rec=''
    if n<len(ivs):
        nxt=onset(ivs[n]['start_index'])
        rec=f"{nxt-f:4d}s {m(W[f:nxt]):4.0f}W hr{HR[nxt-1]}"
    print(f"{n:2d} {si:5d} {o:5d} {o-si:+3d} {w['average_watts']:4d} {m(seg):5.1f} {f-o:4d} {f-ei:+3d}  {a0:4.0f} {a1:4.0f} {a2:4.0f}  {m(HR[o:f]):5.1f} {max(h for h in HR[o:f] if h):4d} {HR[o]} {HR[f-1]} {m(C[o:f]):4.1f} {dalt:5.1f} {grade:4.1f} {min(WB[o:f+5]):6.0f}  {rec}")
    rows.append(m(seg))
print('det mean',m(rows),'lap mean',m([w['average_watts'] for w in ivs]))
# warmup & post
print('warmup 0-',ivs[0]['start_index'],'avgW',m(W[:ivs[0]['start_index']]),'avgHR',m(HR[:ivs[0]['start_index']]))
e=ivs[-1]['end_index'];print('post avgW',m(W[e:]),'avgHR',m(HR[e:]),'dur',len(W)-e)
# best efforts
for L in [60,180,300]:
    best=max(sum(W[i:i+L])/L for i in range(len(W)-L));print('best',L,round(best))
