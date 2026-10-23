"""Push plan v6.9 — 5/13 LSD + 5/14 REST + 5/15 race-rhythm B****-v2 to ICU.

3 PUT operations, no DELETE, no new event creation. Existing event IDs:
  - 109138215 (5/13 REST → LSD)
  - 109138212 (5/14 race-rhythm → REST)
  - 109138217 (5/15 短-强 → race-rhythm B****-v2)

Untouched: 109138208 (5/12 done), 109138210 (5/11 done), 109138221 (5/17 race).

Usage:
  python scripts/push_plan_v6.9.py          # dry-run, prints payloads only
  python scripts/push_plan_v6.9.py --execute # actually PUT to ICU
"""
import json
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient


# ============================================================
# PAYLOAD CONSTRUCTION
# ============================================================

def build_lsd_payload() -> dict:
    """5/13 LSD 4.5h Z2 — replaces 109138215 (was REST)."""
    return {
        "id": 109138215,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "WORKOUT",
        "type": "Ride",
        "name": "Z2 LSD 100-120km / 1000-1500m 爬升 / 朋友陪骑",
        "start_date_local": "2026-05-13T09:30:00",
        "end_date_local": "2026-05-13T14:00:00",
        "icu_training_load": 190,
        "description": (
            "难度 5/10 (race day-4 LSD, 临时插入 plan v6.9)\n\n"
            "功率区间:\n"
            "- 全程 Z2 偏弱: 170-180W (57-60% FTP)\n"
            "- 爬段最多 Z2 上限: ≤200W\n"
            "- 与朋友休闲骑, 不主动进攻\n"
            "- IF 目标 0.62-0.66 → TSS 175-220\n\n"
            "🔥 底线: AP 170-180W, 绝对不加 set, 绝对不末段冲刺.\n"
            "回程最后 30km IF ≤ 0.50. 爬段换 34T 飞踏 ≥90rpm, 不顶扭矩 (保护右膝).\n\n"
            "🍞 补给 (~4.5h ride):\n"
            "- 出发前 1h: 燕麦+蜂蜜+奶粉+鸡蛋 (~100-120g carb)\n"
            "- ride 中: 45g gel × 1-2/h = 45-90g/h\n"
            "- 电解质必加 (钠 500-800mg/h)\n"
            "- 水: 750ml-1L/h, 共 3.5-4.5L\n"
            "- 结束 30min 内: 60g carb + 20g protein (恢复奶昔 / 牛奶+香蕉+面包)\n"
            "- 晚饭: 米饭/面 + 蛋白质 100g + 蔬菜, 碳水 250-350g (不到撑)\n"
            "- 不喝酒\n\n"
            "目的: race day TSB 拉回 +0~+5, 避免 5/13 REST 后 race day 鲜过头 +16."
        ),
        "indoor": False,
        "moving_time": 16200,  # 4.5h
        "external_id": "vault_plan_v6.9_5_13_lsd",
        "training_availability": "NORMAL",
        "workout_doc": None,  # free ride
    }


def build_rest_payload() -> dict:
    """5/14 REST — replaces 109138212 (was race-rhythm)."""
    return {
        "id": 109138212,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "NOTE",
        "name": "完全休息 + 散步 + 拉伸 (race day-3)",
        "start_date_local": "2026-05-14T00:00:00",
        "end_date_local": "2026-05-14T23:59:00",
        "icu_training_load": 0,
        "description": (
            "难度 0/10. race day-3 完全休息.\n\n"
            "🔥 底线: 完全不上车.\n"
            "推荐 30min 散步 + 15min 拉伸 (重点股四头).\n\n"
            "🍞 补给:\n"
            "- 正常 carb 7-8g/kg (~500g, race week 上限)\n"
            "- 蛋白 1.6g/kg (~100g)\n"
            "- 多睡 8h+\n"
            "- 不喝酒\n"
            "- creatine 3g + β-丙氨酸 4g daily stack"
        ),
        "indoor": False,
        "show_as_note": True,
        "not_on_fitness_chart": True,
        "external_id": "vault_plan_v6.9_5_14_rest",
        "training_availability": "NORMAL",
        "workout_doc": None,
    }


def build_race_rhythm_payload() -> dict:
    """5/15 Race-rhythm B****-v2 — replaces 109138217 (was 短-强).

    Structure: 3 set × 3×(90s @ 105%/315W + 15s @ 160%/480W) on Mountain 1 B.
    """
    workout_doc = {
        "description": (
            "Mountain 1 B Race-rhythm B****-v2 (race day-2 opener)\n"
            "3 set × 3×(90s @ 105% + 15s @ 160% spike)\n"
            "Set 间 4min descent recovery"
        ),
        "ftp": 300,
        "duration": 8580,  # 60min warmup + 3min intro + (5.25min × 3 set + 4min × 2 recovery) + 60min cooldown
        "steps": [
            # Warmup commute ramp (1h)
            {"duration": 3600, "warmup": True, "ramp": True,
             "power": {"value": 55, "units": "%ftp"},
             "_power": {"value": 165.0, "start": 160.0, "end": 170.0}},
            # Intro Z2
            {"duration": 180,
             "power": {"value": 65, "units": "%ftp"},
             "_power": {"value": 195.0, "start": 190.0, "end": 200.0}},
            # Set 1: 3 cycles × (90s @ 315W + 15s @ 480W)
            {"text": "3x", "duration": 315, "distance": 0.0, "reps": 3, "steps": [
                {"duration": 90,
                 "power": {"value": 105, "units": "%ftp"},
                 "_power": {"value": 315.0, "start": 305.0, "end": 325.0}},
                {"duration": 15,
                 "power": {"value": 160, "units": "%ftp"},
                 "_power": {"value": 480.0, "start": 450.0, "end": 510.0}},
            ]},
            # Descent recovery 1
            {"duration": 240,
             "power": {"value": 50, "units": "%ftp"},
             "_power": {"value": 150.0, "start": 145.0, "end": 155.0}},
            # Set 2
            {"text": "3x", "duration": 315, "distance": 0.0, "reps": 3, "steps": [
                {"duration": 90,
                 "power": {"value": 105, "units": "%ftp"},
                 "_power": {"value": 315.0, "start": 305.0, "end": 325.0}},
                {"duration": 15,
                 "power": {"value": 160, "units": "%ftp"},
                 "_power": {"value": 480.0, "start": 450.0, "end": 510.0}},
            ]},
            # Descent recovery 2
            {"duration": 240,
             "power": {"value": 50, "units": "%ftp"},
             "_power": {"value": 150.0, "start": 145.0, "end": 155.0}},
            # Set 3
            {"text": "3x", "duration": 315, "distance": 0.0, "reps": 3, "steps": [
                {"duration": 90,
                 "power": {"value": 105, "units": "%ftp"},
                 "_power": {"value": 315.0, "start": 305.0, "end": 325.0}},
                {"duration": 15,
                 "power": {"value": 160, "units": "%ftp"},
                 "_power": {"value": 480.0, "start": 450.0, "end": 510.0}},
            ]},
            # Cooldown commute (1h)
            {"duration": 3600, "cooldown": True, "ramp": True,
             "power": {"value": 55, "units": "%ftp"},
             "_power": {"value": 165.0, "start": 160.0, "end": 170.0}},
        ],
    }

    return {
        "id": 109138217,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "WORKOUT",
        "type": "Ride",
        "name": "Mountain 1 B Race-rhythm 3 set × 3×(90s+15s) opener",
        "start_date_local": "2026-05-15T10:00:00",
        "end_date_local": "2026-05-15T12:30:00",
        "icu_training_load": 135,
        "description": (
            "难度 7/10 (race day-2 opener, plan v6.9)\n\n"
            "功率区间:\n"
            "- 稳态 90s: 305-325W (102-108% FTP, race-pace match)\n"
            "- 摇车 spike 15s: 450-510W avg target 480W (150-170%, 摇车自然爆发)\n\n"
            "3 set × 3×(90s + 15s) mixed VO2max + race-spike on Mountain 1 B.\n"
            "Set 间 4min descent recovery. 每 set 5.25min, total work 15.75min, 9 spike total.\n\n"
            "🔥 底线: 3 set 必完成. 稳态守 305W 不掉, spike 摇车爆发 ≥450W.\n"
            "第 1 set 第 1 cycle 不要冲过头 (>600W avg).\n\n"
            "🍞 补给 (~2.5h total ride with commute):\n"
            "- 出发前 1.5h: 燕麦/米糊 + 香蕉 (~80g carb)\n"
            "- 水壶: 电解质粉 + carb powder\n"
            "- 第 1 set 前: 1 gel (45g)\n"
            "- 第 2 set 前: 1 gel\n"
            "- 总赛中: 2-3 gel = 90-135g carb\n"
            "- post 30min: 米糊 + protein 30g + carb 80g\n\n"
            "Race-specific: 模拟 5/17 race 决战段 attack/defend 防守动作 (15s 摇车贴上对手).\n"
            "W' burn 估 ~15kJ (race day 48h 后 95%+ 回血).\n\n"
            "第 1 set 判官:\n"
            "- 3 spike 都到 480W + 稳态守住 315W RPE 8 → 完整 3 set\n"
            "- 第 1 set 整体跌到 290W → 砍 2 set 不要硬撑 (糖原信号或 5/13 长骑负荷重了)"
        ),
        "indoor": False,
        "moving_time": 8580,
        "external_id": "vault_plan_v6.9_5_15_race_rhythm",
        "training_availability": "NORMAL",
        "workout_doc": workout_doc,
    }


# ============================================================
# DRY-RUN & EXECUTE
# ============================================================

def print_payload_summary(label: str, payload: dict):
    """Print a human-readable summary of one PUT payload."""
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    print(f"  PUT /athlete/i176789/events/{payload['id']}")
    print(f"  Name: {payload['name']}")
    print(f"  Start: {payload['start_date_local']}")
    print(f"  Category: {payload['category']}")
    print(f"  TSS: {payload.get('icu_training_load', 0)}")
    desc = payload.get('description', '')
    print(f"  Description ({len(desc)} chars):")
    for line in desc.split('\n'):
        print(f"    {line}")
    wd = payload.get('workout_doc')
    if wd:
        steps = wd.get('steps', [])
        print(f"  Workout steps: {len(steps)} top-level steps")
        for i, s in enumerate(steps):
            if 'reps' in s:
                print(f"    [{i}] {s.get('text', '')} {s.get('reps')}× duration={s['duration']}s "
                      f"sub-steps: {len(s.get('steps', []))}")
                for j, sub in enumerate(s.get('steps', [])):
                    print(f"        [{i}.{j}] {sub['duration']}s @ "
                          f"{sub['power']['value']}{sub['power']['units']} "
                          f"= {sub['_power']['value']}W")
            else:
                power = s.get('power', {})
                p_val = power.get('value', '?')
                p_unit = power.get('units', '')
                actual = s.get('_power', {}).get('value', '?')
                flags = []
                if s.get('warmup'):
                    flags.append('warmup')
                if s.get('cooldown'):
                    flags.append('cooldown')
                if s.get('ramp'):
                    flags.append('ramp')
                flag_str = f" [{','.join(flags)}]" if flags else ""
                print(f"    [{i}] {s['duration']}s @ {p_val}{p_unit} = {actual}W{flag_str}")
    else:
        print(f"  Workout doc: None (free ride)")


def main():
    parser = argparse.ArgumentParser(description="Push plan v6.9 to ICU calendar")
    parser.add_argument("--execute", action="store_true",
                        help="Actually PUT to ICU API (default: dry-run only)")
    args = parser.parse_args()

    payloads = [
        ("PUT 1/3: 5/13 LSD (replaces REST 109138215)", build_lsd_payload()),
        ("PUT 2/3: 5/14 REST (replaces race-rhythm 109138212)", build_rest_payload()),
        ("PUT 3/3: 5/15 race-rhythm B****-v2 (replaces 短-强 109138217)", build_race_rhythm_payload()),
    ]

    for label, p in payloads:
        print_payload_summary(label, p)

    if not args.execute:
        print(f"\n{'=' * 70}")
        print("  DRY-RUN ONLY. No API calls made.")
        print("  To execute: python scripts/push_plan_v6.9.py --execute")
        print(f"{'=' * 70}")
        return

    # Execute
    print(f"\n{'=' * 70}")
    print("  EXECUTING — calling ICU API now")
    print(f"{'=' * 70}")
    client = ICUClient()
    for label, p in payloads:
        eid = p['id']
        print(f"\n  PUT event {eid} ({p['name'][:50]}...) ", end='', flush=True)
        try:
            result = client.update_event(eid, p)
            print(f"OK")
            print(f"    → name: {result.get('name', '?')}")
            print(f"    → start: {result.get('start_date_local', '?')}")
            print(f"    → TSS: {result.get('icu_training_load', '?')}")
        except Exception as e:
            print(f"FAILED: {e}")
            return
    print(f"\n  All 3 PUT operations succeeded.")
    print(f"  Next: cd icu && .venv/bin/python scripts/sync_events.py")
    print(f"        # sync to icu_data_warehouse/8_Events/events.json")


if __name__ == "__main__":
    main()
