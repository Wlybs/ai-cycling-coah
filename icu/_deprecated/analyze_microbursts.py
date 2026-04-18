import json

def analyze_lap(watts, lap_name):
    # Find contiguous blocks of pedaling (>=50W) and coasting (<50W)
    blocks = []
    current_state = None # 'pedaling' or 'coasting'
    start_idx = 0
    
    for i, w in enumerate(watts):
        state = 'pedaling' if w >= 50 else 'coasting'
        if current_state is None:
            current_state = state
            start_idx = i
        elif state != current_state:
            block_watts = watts[start_idx:i]
            blocks.append({
                'state': current_state,
                'duration': len(block_watts),
                'avg_watts': sum(block_watts)/len(block_watts) if block_watts else 0
            })
            current_state = state
            start_idx = i
            
    # Add last block
    if current_state is not None:
        block_watts = watts[start_idx:]
        blocks.append({
            'state': current_state,
            'duration': len(block_watts),
            'avg_watts': sum(block_watts)/len(block_watts) if block_watts else 0
        })
        
    print(f"\n--- {lap_name} Breakdown (Total {len(watts)}s, Avg {sum(watts)/len(watts) if len(watts) else 0:.1f}W) ---")
    
    # Consolidate very short blocks (e.g., < 3s) to avoid noise
    consolidated = []
    for b in blocks:
        if consolidated and b['duration'] < 3 and b['state'] == 'coasting':
            # Ignore micro-coasting
            consolidated[-1]['duration'] += b['duration']
            # Recompute avg is complex without raw, but let's just print raw blocks > 3s for clarity
            pass

    # Print significant blocks
    for b in blocks:
        if b['duration'] >= 2: # Filter out 1s noise
            if b['state'] == 'pedaling':
                print(f"馃毈 璧疯剼 {b['duration']}s @ {b['avg_watts']:.0f}W")
            else:
                print(f"鈱 鍋滆剼/婊戣 {b['duration']}s @ {b['avg_watts']:.0f}W")

d = json.load(open('icu_data_warehouse/5_Activities_Detail/2026-04-12_i139065650.json', encoding='utf-8'))
streams = d.get('streams', {})
watts = streams.get('watts', [])
alt = streams.get('altitude', [])

laps = d['laps']

# Helper to get watts for a lap
def get_lap_watts(lap_num):
    lap = next(l for l in laps if l['lap_number'] == lap_num)
    start = lap['stream_start_index']
    end = start + int(lap['duration_sec'])
    return watts[start:end], start, end

# Lap 2
w2, s2, e2 = get_lap_watts(2)
analyze_lap(w2, "绗1缁 (Lap 2)")

# Lap 4
w4, s4, e4 = get_lap_watts(4)
analyze_lap(w4, "绗2缁 (Lap 4)")

# Lap 6
w6, s6, e6 = get_lap_watts(6)
analyze_lap(w6, "绗3缁 (Lap 6)")

# Lap 8+9
lap8 = next(l for l in laps if l['lap_number'] == 8)
lap9 = next(l for l in laps if l['lap_number'] == 9)
s8 = lap8['stream_start_index']
e9 = lap9['stream_start_index'] + int(lap9['duration_sec'])
w89 = watts[s8:e9]
analyze_lap(w89, "绗4缁 (Lap 8+9)")

# Get Lap 11 climb part using ICU intervals directly
icu_11 = d['icu_intervals'][11] # The 349W part
s11 = icu_11['start_index']
e11 = icu_11['end_index']
w11 = watts[s11:e11]
alt11 = alt[s11:e11]

print(f"\n--- Lap 11 (鍘熷鏁版嵁) ---")
print(f"鎬婚暱搴: {len(w11)}s")
analyze_lap(w11, "绗5缁 鐖潯閮ㄥ垎 (Lap 11/12 Split)")

# Lap 12 is actually ICU interval 12 or 14?
# Let's map exactly based on user's statement.
# User said Lap 2, 4, 6, 8+9, 11, 12
# The 349W part is ICU index 11 (235s).
# What is the actual "lap 12"? Wait, the ICU index 11 is the 349W part. Is that lap 11 or 12?


# Lap 12
w12, s12, e12 = get_lap_watts(12)
analyze_lap(w12, "绗6缁 (Lap 12)")

