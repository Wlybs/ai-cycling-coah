import xml.etree.ElementTree as ET
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

tree = ET.parse(r'D:\Cycling\icu\race_map\2026_4_12.gpx')
root = tree.getroot()
ns = ''
if '}' in root.tag:
    ns = root.tag.split('}')[0] + '}'

points = []
for trk in root.findall(f'.//{ns}trkpt'):
    lat = float(trk.attrib['lat'])
    lon = float(trk.attrib['lon'])
    ele_node = trk.find(f'{ns}ele')
    ele = float(ele_node.text) if ele_node is not None else 0.0
    points.append((lat, lon, ele))

total_dist = 0.0
total_gain = 0.0
distance_array = [0.0]

for i in range(1, len(points)):
    d = haversine(points[i-1][0], points[i-1][1], points[i][0], points[i][1])
    total_dist += d
    distance_array.append(total_dist)
    gain = points[i][2] - points[i-1][2]
    if gain > 0:
        total_gain += gain

min_ele = min(p[2] for p in points)
max_ele = max(p[2] for p in points)

climbs = []
climb_start_idx = 0
current_max_ele = points[0][2]

for i in range(1, len(points)):
    ele = points[i][2]
    if ele > current_max_ele:
        current_max_ele = ele
    else:
        drop = current_max_ele - ele
        if drop > 15:
            gain = current_max_ele - points[climb_start_idx][2]
            if gain > 30:
                end_idx = i - 1
                dist = distance_array[end_idx] - distance_array[climb_start_idx]
                if dist > 0:
                    avg_grad = (gain / (dist * 1000)) * 100
                else:
                    avg_grad = 0
                climbs.append({
                    'start_dist': distance_array[climb_start_idx],
                    'end_dist': distance_array[end_idx],
                    'dist': dist,
                    'gain': gain,
                    'avg_grad': avg_grad
                })
            climb_start_idx = i
            current_max_ele = ele

gain = current_max_ele - points[climb_start_idx][2]
if gain > 30:
    end_idx = len(points) - 1
    dist = distance_array[end_idx] - distance_array[climb_start_idx]
    if dist > 0:
        avg_grad = (gain / (dist * 1000)) * 100
    else:
        avg_grad = 0
    climbs.append({
        'start_dist': distance_array[climb_start_idx],
        'end_dist': distance_array[end_idx],
        'dist': dist,
        'gain': gain,
        'avg_grad': avg_grad
    })

print(f"Single Lap Distance: {total_dist:.2f} km")
print(f"Single Lap Elevation Gain: {total_gain:.0f} m")
print(f"Min Elevation: {min_ele:.0f} m")
print(f"Max Elevation: {max_ele:.0f} m")
print("\nMajor Climbs per lap:")
for i, c in enumerate(climbs):
    print(f"Climb {i+1}: Start at {c['start_dist']:.2f}km, Length: {c['dist']:.2f}km, Gain: {c['gain']:.0f}m, Avg Gradient: {c['avg_grad']:.1f}%")
