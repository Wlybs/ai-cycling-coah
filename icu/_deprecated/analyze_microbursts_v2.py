import json

d = json.load(open('icu_data_warehouse/5_Activities_Detail/2026-04-12_i139065650.json', encoding='utf-8'))
streams = d.get('streams', {})
watts = streams.get('watts', [])
alt = streams.get('altitude', [])
time = streams.get('time', [])

def analyze_segment(s_idx, e_idx, name):
    w_seg = watts[s_idx:e_idx]
    t_seg = time[s_idx:e_idx]
    if not w_seg:
        print(f"Empty segment for {name}")
        return
        
    blocks = []
    current_state = None
    start_i = 0
    
    for i, w in enumerate(w_seg):
        state = 'pedaling' if w >= 100 else 'coasting' # use 100W as threshold for "起脚"
        if current_state is None:
            current_state = state
            start_i = i
        elif state != current_state:
            block_w = w_seg[start_i:i]
            dur = t_seg[i] - t_seg[start_i]
            blocks.append({
                'state': current_state,
                'duration': dur,
                'avg_watts': sum(block_w)/len(block_w) if block_w else 0
            })
            current_state = state
            start_i = i
            
    if current_state is not None:
        block_w = w_seg[start_i:]
        dur = t_seg[-1] - t_seg[start_i] if len(t_seg) > 1 else 0
        blocks.append({
            'state': current_state,
            'duration': dur,
            'avg_watts': sum(block_w)/len(block_w) if block_w else 0
        })
        
    # Consolidate small blocks (<4s)
    cons = []
    for b in blocks:
        if cons and b['duration'] < 4:
            cons[-1]['duration'] += b['duration']
        else:
            cons.append(b)
            
    print(f"\n=== {name} (Total {t_seg[-1]-t_seg[0]}s, Avg {sum(w_seg)/len(w_seg):.0f}W) ===")
    for b in cons:
        if b['duration'] >= 2:
            if b['state'] == 'pedaling':
                print(f"  -> 踩踏起脚: {b['duration']}s @ {b['avg_watts']:.0f}W")
            else:
                print(f"  -> 停脚滑行: {b['duration']}s @ {b['avg_watts']:.0f}W")

icu = d['icu_intervals']
# 1: Lap 2
analyze_segment(icu[1]['start_index'], icu[1]['end_index'], "第1组 (Lap 2)")

# 2: Lap 4
analyze_segment(icu[3]['start_index'], icu[3]['end_index'], "第2组 (Lap 4)")

# 3: Lap 6
analyze_segment(icu[5]['start_index'], icu[5]['end_index'], "第3组 (Lap 6)")

# 4: Lap 8+9
s8 = icu[7]['start_index']
e9 = icu[8]['end_index']
analyze_segment(s8, e9, "第4组 (Lap 8+9)")

# 5: Lap 11 (Need to find the climb part)
s11 = icu[10]['start_index']
e11 = icu[10]['end_index']
alt11 = alt[s11:e11]
peak_rel_idx = alt11.index(max(alt11))
peak_idx = s11 + peak_rel_idx
analyze_segment(s11, peak_idx, "第5组 (Lap 11 上坡段)")

# 6: Lap 12
analyze_segment(icu[11]['start_index'], icu[11]['end_index'], "第6组 (Lap 12)")

