"""Fix ICU chart rendering for race week 5/26-5/31 events.

Workout chart 颜色块需要 ZWO 文件 (filename + file_contents_base64), 不是 workout_doc JSON.
重 PUT 5/26 + 5/29 (workout events) with ZWO.
其它 (5/27 free ride / 5/28 rest / 5/30 rest / 5/31 race) 不需要 chart.

Usage:
  python scripts/fix_race_week_charts.py          # dry-run
  python scripts/fix_race_week_charts.py --execute # PUT to ICU
"""
import base64
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.coach.plan_generator import _workout_text_to_zwo, _sanitize_for_zwo_description


# ============================================================
# WORKOUT TEXT — ZWO 源
# ============================================================

WORKOUT_526_TEXT = """
- 15m 60% warmup ramp 130→220W
- 30m 95% Set 1: HC2 mirror 285W
- 10m 50% Z1 recovery 150W
- 25m 97% Set 2: HC3 fatigued 290W
- 25m 77% Z2 endurance 230W
- 15m 55% cooldown ramp 200→130W
"""

WORKOUT_529_TEXT = """
- 60m 67% bike out warmup ramp 200W
- 10m 92% Climb 1: HC1 sim 275W
- 5m 50% descent 1
- 10m 95% Climb 2: HC2 sim 285W
- 5m 50% descent 2
- 6m 98% Climb 3 partial: HC3 sim 295W
- 30s 200% terminal sprint 600W
- 60m 67% bike home cooldown 200W
- 10m 70% Z2 padding 210W
"""


def build_526_payload(event_id: int) -> dict:
    """5/26 Indoor TTE Race Mirror — ZWO upload for chart rendering."""
    workout_text = WORKOUT_526_TEXT.strip()
    notes = (
        "难度 8/10 (race week TTE focus, 5/31 太子尖 prep)\n\n"
        "今天 TSB +26 深 stale, 必须 load 不能 rest.\n"
        "race demand: HC2 22min sustained @ 300W+, TTE 你的短板.\n\n"
        "功率结构:\n"
        "- Warmup 15min progressive ramp 130→220W\n"
        "- Set 1: 30min @ 280-290W (HC2 race-pace + 8min over-shoot)\n"
        "- Z1 recovery 10min @ 150W (race 中段 Phase C sim)\n"
        "- Set 2: 25min @ 285-295W (HC3 race-pace, fatigued state)\n"
        "- Z2 endurance 25min @ 220-240W (巩固有氧底盘)\n"
        "- Cooldown 15min ramp down\n\n"
        "🔥 底线:\n"
        "- Set 1 30min @ 285W: 一段长肉条不打断, 不嵌 surge\n"
        "- Set 2 25min @ 290W: 累状态下顶 FTP-edge\n"
        "- 不做 sprint / surge / VO2max / 热块 (留 race-day 弹药)\n\n"
        "📋 环境:\n"
        "- AC 16°C 全程 cool, 不混热\n"
        "- 风扇坏 → AC + 多喝水补偿\n\n"
        "🍞 补给 (2h trainer):\n"
        "- 起前 1 gel\n"
        "- 60min 处: 1 gel + 500ml 电解质\n"
        "- 90min 处: 1 gel + 250ml\n"
        "- post 30min: 米糊 100g + protein 30g + 电解质大杯\n\n"
        "🎯 决策门槛:\n"
        "- Set 1 末段功率掉 >10W → ease 5W\n"
        "- Set 1 末段功率掉 >20W → 收 进 Z1\n"
        "- Set 2 起手 RPE 9 → 砍 Set 2 到 12-15min\n"
        "- HR 触 max-3 (197+) → ease\n\n"
        "Plan v7 (2026-05-26 锁定终版)."
    )
    name = "Indoor TTE Race Mirror 30+25 (5/31 太子尖 prep)"
    notes_safe = _sanitize_for_zwo_description(notes)
    zwo = _workout_text_to_zwo(workout_text, name=name, description=notes_safe)
    return {
        "id": event_id,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-26T13:00:00",
        "name": name,
        "filename": f"2026-05-26_tte_race_mirror.zwo",
        "file_contents_base64": base64.b64encode(zwo.encode("utf-8")).decode("ascii"),
        "icu_training_load": 195,
        "indoor": True,
        "external_id": "vault_plan_v7_5_26_tte_indoor",
    }


def build_529_payload(event_id: int) -> dict:
    """5/29 Mountain 2 race-rhythm — ZWO upload for chart rendering."""
    workout_text = WORKOUT_529_TEXT.strip()
    notes = (
        "难度 7/10 (race day-2 race-rhythm + 热适应 day-3)\n\n"
        "功率结构 (Mountain 2 多 climb ladder):\n"
        "- Climb 1: 10-11min @ 270-280W (sweet spot, HC1 race-pace sim)\n"
        "- Descent + reposition: 5-6min Z1\n"
        "- Climb 2: 10-11min @ 280-290W (sweet spot 上沿, HC2 race-pace sim)\n"
        "- Descent + reposition: 5-6min Z1\n"
        "- Climb 3 上半段 6-7min @ 290-300W (FTP-edge, HC3 末段 sim)\n"
        "- 终段 30s @ 600W (Type-II 神经唤醒 + 终点 sim)\n\n"
        "🔥 底线:\n"
        "- Climb 1/2 是 race-pace, RPE 7-8 not 9\n"
        "- Climb 3 是 race-specific sim, RPE 8-9 OK\n"
        "- Sprint 不超 700W (留 race-day 弹药)\n"
        "- 周五 Mountain 2 人少, 训练 OK\n\n"
        "📋 路线: 25-30km bike out → Mountain 2 (3.1km × 6.6%) → 3 climbs → bike home\n\n"
        "🍞 补给 (~3h ride):\n"
        "- 出发前 1h: 米糊 100g + 香蕉 + 黑咖啡\n"
        "- 水壶: 电解质 + carb powder ~60g\n"
        "- Climb 1 前: 1 gel\n"
        "- Climb 2 后: 1 gel + 250ml\n"
        "- bike home: 1 gel\n"
        "- post 30min: 米糊 80g + protein 30g + 电解质\n\n"
        "🎯 决策门槛:\n"
        "- Climb 1 RPE 9 + 功率掉 → 砍后续 2 climbs\n"
        "- Climb 2 完不成 280W → Climb 3 取消\n"
        "- Sprint 不到 600W 也 OK\n\n"
        "热适应 day-3: 10:00-13:10 正午时段, 不补冰水.\n"
        "Plan v7."
    )
    name = "Mountain 2 race-rhythm 3 climb ladder + sprint (5/31 prep)"
    notes_safe = _sanitize_for_zwo_description(notes)
    zwo = _workout_text_to_zwo(workout_text, name=name, description=notes_safe)
    return {
        "id": event_id,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-29T10:00:00",
        "name": name,
        "filename": f"2026-05-29_mt2_race_rhythm.zwo",
        "file_contents_base64": base64.b64encode(zwo.encode("utf-8")).decode("ascii"),
        "icu_training_load": 160,
        "indoor": False,
        "external_id": "vault_plan_v7_5_29_mt2_race_rhythm",
    }


def main():
    parser = argparse.ArgumentParser(description="Fix ICU chart for race week workouts")
    parser.add_argument("--execute", action="store_true", help="PUT to ICU")
    args = parser.parse_args()

    payloads = [
        ("PUT 1/2: 5/26 Indoor TTE (id=112384615) with ZWO", build_526_payload(112384615)),
        ("PUT 2/2: 5/29 Mt2 race-rhythm (id=109138284) with ZWO", build_529_payload(109138284)),
    ]

    for label, p in payloads:
        print(f"\n{'='*70}\n  {label}\n{'='*70}")
        print(f"  filename: {p['filename']}")
        print(f"  TSS: {p['icu_training_load']}")
        zwo_decoded = base64.b64decode(p['file_contents_base64']).decode('utf-8')
        # Show ZWO workout block
        lines = zwo_decoded.split('\n')
        in_workout = False
        for ln in lines:
            if '<workout>' in ln:
                in_workout = True
            if in_workout:
                print(f"  {ln}")
            if '</workout>' in ln:
                in_workout = False
                break

    if not args.execute:
        print("\n  DRY-RUN ONLY. Use --execute to PUT.")
        return

    print(f"\n{'='*70}\n  EXECUTING — calling ICU API\n{'='*70}")
    client = ICUClient()
    for label, p in payloads:
        eid = p['id']
        print(f"\n  PUT event {eid} ({p['name'][:50]}...) ", end='', flush=True)
        try:
            result = client.update_event(eid, p)
            print(f"OK")
            print(f"    -> name: {result.get('name', '?')}")
            print(f"    -> TSS: {result.get('icu_training_load', '?')}")
            steps = (result.get('workout_doc') or {}).get('steps', [])
            print(f"    -> steps in workout_doc: {len(steps)}")
        except Exception as e:
            print(f"FAILED: {e}")
            return
    print(f"\n  Done. Refresh ICU UI to verify chart visible.")


if __name__ == "__main__":
    main()
