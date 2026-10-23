"""Update 5/27 + 5/29 events to swapped plan v7.1.

5/27: Outdoor 自由巡山 race-specific (was LSD only)
5/29: LSD 4h + opener bursts (was race-rhythm)

Usage:
  python scripts/fix_527_529_swap.py          # dry-run
  python scripts/fix_527_529_swap.py --execute # PUT to ICU
"""
import base64
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.coach.plan_generator import _workout_text_to_zwo, _sanitize_for_zwo_description


def build_527_xunshan_payload() -> dict:
    """5/27 自由巡山 — outdoor adventure ride, terrain-driven intensity."""
    return {
        "id": 109138282,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-27T11:00:00",
        "name": "自由巡山 4-5h race-specific (5/31 prep)",
        "icu_training_load": 285,
        "indoor": False,
        "moving_time": 16200,
        "external_id": "vault_plan_v7.1_5_27_xunshan",
        "description": (
            "难度 7/10 (race week race-specific quality day + 热适应 day-1)\n\n"
            "自由巡山 4-5h outdoor, terrain-driven intensity (sim race 决策模式):\n\n"
            "🚴 强度规则:\n"
            "- 长坡 (≥5min): SS/Threshold 270-290W (想刷 KOM 也行, 限 1 次)\n"
            "- 短坡 (<5min): Z2 natural 200-240W, 不主动加速\n"
            "- 平路: Z2 200-220W\n"
            "- 下坡: 荡腿 Z1 130-160W (维持血流, 不滑行无功率)\n\n"
            "🔥 底线:\n"
            "- 长坡 SS/Threshold RPE 上限 8 (race-3 不烧 race-day 池子)\n"
            "- KOM attempt 单次 max 5-10min, 不堆多 KOM (累积 fatigue 进 race)\n"
            "- 短坡 + 平路真 Z2, 不主动挑战 路上骑手\n"
            "- 下坡 skill caution, 不极限过弯 (5/24 hard rule)\n\n"
            "📋 路线: 用户自由选, 低海拔避免叠加 elevation 主体, 正午时段 11:00-15:30 = 热适应 day-1\n\n"
            "🍞 补给 (4-5h race-day 补给模板预演):\n"
            "- 出发前 1.5h: 米糊+香蕉+蜂蜜 (~120-150g carb) + 咖啡\n"
            "- 路上水壶: 电解质粉 + carb powder (~60g carb/壶)\n"
            "- 每 30min: 1 gel (45g) → 总 6-8 gel = 270-360g carb\n"
            "- 长坡前 5min: 1 gel pre-load\n"
            "- 电解质必加 (钠 500-800mg/h)\n"
            "- 水: 1L/h, 总 4-5L (热暴露)\n"
            "- 不补冰水 (热适应)\n"
            "- 回程最后 30min IF ≤ 0.55 防累\n"
            "- 结束 30min: 米糊 80g + protein 30g + 电解质大杯\n"
            "- 晚饭 250-300g carb\n\n"
            "Plan v7.1 (2026-05-26 锁定, swap from LSD → race-specific quality).\n"
            "Race-specific value: terrain-driven intensity 直接 sim race 太子尖决策模式 (vs structured workout)."
        ),
        "workout_doc": None,  # free ride
    }


def build_529_lsd_opener_payload() -> dict:
    """5/29 LSD 4h + opener bursts (race-2 prime)."""
    workout_text = (
        "- 180m 67% LSD 主体 Z2 200-220W\n"
        "- 25m 65% Z2 continuous 前奏\n"
        "5x\n"
        "- 30s 175% opener burst 525W\n"
        "- 270s 50% Z1 full recovery 150W\n"
        "- 5m 60% Z2 cool down home"
    )
    notes = (
        "难度 6/10 (race day-2 LSD + opener prime + 热适应 day-2)\n\n"
        "结构: 4h Z2 长拉, 末段 1h 嵌入 5 × 30s opener bursts.\n\n"
        "🚴 主体 (0-3h): Z2 长拉 200-220W\n"
        "- 路线自由, 平路 + 缓坡\n"
        "- HR 145-160 范围, 不漂移\n"
        "- 不主动找硬坡, 不追路上骑手\n\n"
        "🔥 末段 1h opener:\n"
        "- 5 × 30s @ 525W (Type-II 神经 prime)\n"
        "- 每个 burst 完全 recovery 4:30\n"
        "- 末段 5min Z2 cool home\n\n"
        "🎯 关键约束:\n"
        "- Opener bursts 必须在末段 1h 内, 不放前 3h\n"
        "- 每个 burst 完全 recovery 4-5min, 不短间隔\n"
        "- 5 个上限, 不做 6+\n"
        "- 不刷 KOM, 不连续硬冲\n"
        "- bursts 不超 600W (race-day 弹药)\n\n"
        "📋 路线: 用户选熟悉 long route, 末段段平路做 bursts 安全\n"
        "时间窗: 正午 11:00-15:00 = 热适应 day-2\n\n"
        "🍞 补给 (race-day 模板第二次预演):\n"
        "- 出发前 1.5h: 米糊 100g + 香蕉 + 黑咖啡\n"
        "- 路上水壶: 电解质 + carb 60g\n"
        "- 每 30-40min: 1 gel\n"
        "- 总 6-7 gel = 270-315g carb\n"
        "- 水: 1L/h\n"
        "- 不补冰水\n"
        "- post 30min: 米糊 80g + protein 30g + 电解质\n"
        "- 晚饭 300g carb (5/30 super-compensation 启动)\n\n"
        "Glycogen super-compensation logic: 5/29 LSD drain → 5/30 rest carb load → 5/31 race-morning 超量储备 (+5-10% vs race-rhythm 5/29).\n\n"
        "Plan v7.1 (swap from race-rhythm → LSD + opener)."
    )
    name = "LSD 4h + 5× opener bursts (race day-2 prime + glycogen drain)"
    notes_safe = _sanitize_for_zwo_description(notes)
    zwo = _workout_text_to_zwo(workout_text, name=name, description=notes_safe)
    return {
        "id": 109138284,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-29T11:00:00",
        "name": name,
        "filename": "2026-05-29_lsd_opener.zwo",
        "file_contents_base64": base64.b64encode(zwo.encode("utf-8")).decode("ascii"),
        "icu_training_load": 240,
        "indoor": False,
        "external_id": "vault_plan_v7.1_5_29_lsd_opener",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    payloads = [
        ("PUT 1/2: 5/27 自由巡山 race-specific (was LSD)", build_527_xunshan_payload()),
        ("PUT 2/2: 5/29 LSD + opener (was race-rhythm)", build_529_lsd_opener_payload()),
    ]

    for label, p in payloads:
        print(f"\n{'='*70}\n  {label}\n{'='*70}")
        print(f"  PUT /athlete/i176789/events/{p['id']}")
        print(f"  name: {p['name']}")
        print(f"  TSS: {p['icu_training_load']}")
        if 'filename' in p:
            print(f"  filename: {p['filename']} (ZWO)")

    if not args.execute:
        print("\n  DRY-RUN ONLY.")
        return

    print(f"\n{'='*70}\n  EXECUTING\n{'='*70}")
    c = ICUClient()
    for label, p in payloads:
        eid = p['id']
        print(f"\n  PUT {eid} ({p['name'][:50]}...) ", end='', flush=True)
        try:
            result = c.update_event(eid, p)
            print(f"OK → TSS={result.get('icu_training_load')}")
        except Exception as e:
            print(f"FAILED: {e}")
            return
    # Second PUT for 5/29 to enforce TSS (ICU recomputes from ZWO)
    print(f"\n  Second PUT for 5/29 to enforce TSS=240...")
    eid_529 = 109138284
    cur = c._get(f"/athlete/{c.athlete_id}/events/{eid_529}", params={"resolve":"true"})
    fix_payload = {
        "type": cur.get("type","Ride"),
        "category": cur.get("category"),
        "start_date_local": cur.get("start_date_local"),
        "name": cur.get("name"),
        "icu_training_load": 240,
        "indoor": cur.get("indoor",False),
        "external_id": cur.get("external_id"),
    }
    r = c.update_event(eid_529, fix_payload)
    print(f"  TSS enforced: {r.get('icu_training_load')} steps={len((r.get('workout_doc') or {}).get('steps',[]))}")
    print(f"\n  Done.")


if __name__ == "__main__":
    main()
