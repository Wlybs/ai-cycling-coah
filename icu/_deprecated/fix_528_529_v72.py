"""Update 5/28 + 5/29 events to v7.2 plan (user proposal: 5/28 LSD, 5/29 short opener).

5/28: REST → LSD 3.5h pure Z2 200 TSS (was NOTE rest, becomes WORKOUT)
5/29: LSD 4h + opener → Light Z2 + opener 1.5-2h (TSS 240 → 100)

Math: race-morning TSB 5/31 ≈ +3.2 (in athlete.md sweet spot 0~+5)

Usage:
  python scripts/fix_528_529_v72.py --execute
"""
import base64
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient
from src.coach.plan_generator import _workout_text_to_zwo, _sanitize_for_zwo_description


def build_528_lsd_payload() -> dict:
    """5/28 LSD 3.5h pure Z2."""
    return {
        "id": 109138283,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-28T11:00:00",
        "end_date_local": "2026-05-28T14:30:00",
        "name": "LSD 3.5h 纯 Z2 (race day-3, glycogen drain)",
        "icu_training_load": 200,
        "indoor": False,
        "moving_time": 12600,  # 3.5h
        "show_as_note": False,
        "not_on_fitness_chart": False,
        "external_id": "vault_plan_v7.2_5_28_lsd_pure_z2",
        "description": (
            "难度 5/10 (race day-3 pure LSD + 热适应 day-2)\n\n"
            "结构: 3.5h Z2 长拉, 纯低强度, 不上 SS, 不刷坡.\n\n"
            "🚴 强度规则 (HARD CONSTRAINT):\n"
            "- AP 200-220W 全程 (66-73% FTP)\n"
            "- RPE 5-6 全程\n"
            "- HR 145-160 不漂移\n"
            "- 长坡上 Z2 上沿 ≤240W (不上 SS)\n"
            "- 短坡 + 平路 真 Z2\n"
            "- 下坡荡腿 Z1\n\n"
            "🔥 底线:\n"
            "- 不上 SS / Threshold / FTP, 即便感觉好\n"
            "- 不冲坡, 不主动找硬路段\n"
            "- 不刷 KOM\n"
            "- 不响应路上骑手 (这一天是 glycogen drain day, 不是表演)\n\n"
            "📋 路线: 低海拔平路居多, 偶尔缓坡 OK\n"
            "时间窗: 11:00-14:30 正午时段 = 热适应 day-2\n\n"
            "🍞 补给 (3.5h):\n"
            "- 出发前 1h: 米糊 + 香蕉 + 黑咖啡 (~100g carb)\n"
            "- 水壶: 电解质 + carb powder ~60g/瓶\n"
            "- 每 30-40min: 1 gel\n"
            "- 总 4-5 gel = 180-225g carb in-ride\n"
            "- 不补冰水 (热适应)\n"
            "- 水: 1L/h, 总 ~3.5L\n"
            "- post 30min: 米糊 80g + protein 30g + 电解质\n"
            "- **晚饭关键**: 250-300g carb (启动 5/29-5/30 super-compensation, 不饮酒)\n\n"
            "🎯 5/27 巡山 RPE feedback 触发:\n"
            "- 5/27 巡山 finish RPE ≤ 8.5: 本课正常 3.5h\n"
            "- 5/27 巡山 finish RPE 10: 本课砍到 2h Z2 (TSS 130)\n\n"
            "目的: glycogen drain day, 配合 5/30 carb load = race-day 5/31 super-compensation +5-10% storage.\n"
            "Plan v7.2 (user proposal: LSD 5/28 vs v7.1 5/29 swap, 数学上 TSB +3.2 in athlete sweet spot 0~+5)."
        ),
        "workout_doc": None,  # free ride
    }


def build_529_light_opener_payload() -> dict:
    """5/29 Light Z2 + opener (race day-2 prime)."""
    workout_text = (
        "- 60m 67% Z2 暖身 + 巡 200-220W\n"
        "5x\n"
        "- 30s 175% opener burst 525W\n"
        "- 270s 50% Z1 full recovery 150W\n"
        "- 25m 60% Z2 cool down home"
    )
    notes = (
        "难度 5/10 (race day-2 opener prime + 热适应 day-3)\n\n"
        "结构: 1h Z2 + 末段 5 × 30s opener bursts + 25min cool. Total ~1.5h.\n\n"
        "🚴 主体 (0-1h): Z2 200-220W\n"
        "- 路线自由, 平路 + 缓坡\n"
        "- HR 145-160\n"
        "- 不主动找硬坡\n\n"
        "🔥 末段 30min opener (1h-1:30):\n"
        "- 5 × 30s @ 525W (Type-II 神经 prime)\n"
        "- 每个 burst 完全 recovery 4:30\n"
        "- 总 27:30 (含 recovery)\n\n"
        "🎯 关键约束:\n"
        "- bursts 不超 600W (race-day 弹药)\n"
        "- 5 个上限, 不做 6+\n"
        "- 不刷 KOM, 不追路上骑手\n"
        "- 不堆 Z2 (砍 v7.1 的 4h LSD 到 1.5h)\n\n"
        "🩺 5/29 morning HRV 闸门 (HARD RULE):\n"
        "- HRV < 59 (baseline 67 - 8): 完全休 跳过本课\n"
        "- HRV 59-62: 砍 opener 到 3 个\n"
        "- HRV ≥ 63: 完整 5 个 opener\n\n"
        "📋 路线: 1h Z2 出去, 找平路做 bursts 安全, cool home\n"
        "时间窗: 11:00-12:30 正午 = 热适应 day-3 (partial benefit)\n\n"
        "🍞 补给 (1.5h):\n"
        "- 出发前 1h: 1 gel + 电解质 250ml\n"
        "- 水壶: 电解质 + carb powder ~30g\n"
        "- bursts 前 5min: 1 gel pre-load\n"
        "- 总 2-3 gel = 90-135g carb\n"
        "- 不补冰水\n"
        "- post 30min: 米糊 80g + protein 30g + 电解质\n"
        "- 晚饭 200-250g carb (5/30 super-compensation 主体)\n\n"
        "Plan v7.2 (砍 v7.1 5/29 LSD 4h → 1.5h light, 数学上为 TSB +3.2 sweet spot)."
    )
    name = "Light Z2 + 5× opener bursts (race day-2 prime, v7.2)"
    notes_safe = _sanitize_for_zwo_description(notes)
    zwo = _workout_text_to_zwo(workout_text, name=name, description=notes_safe)
    return {
        "id": 109138284,
        "type": "Ride",
        "category": "WORKOUT",
        "start_date_local": "2026-05-29T11:00:00",
        "end_date_local": "2026-05-29T12:30:00",
        "name": name,
        "filename": "2026-05-29_light_opener.zwo",
        "file_contents_base64": base64.b64encode(zwo.encode("utf-8")).decode("ascii"),
        "icu_training_load": 100,
        "indoor": False,
        "external_id": "vault_plan_v7.2_5_29_light_opener",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    payloads = [
        ("PUT 1/2: 5/28 LSD 3.5h Z2 (was REST 109138283)", build_528_lsd_payload()),
        ("PUT 2/2: 5/29 Light Z2 + opener (was LSD+opener 109138284)", build_529_light_opener_payload()),
    ]

    for label, p in payloads:
        print(f"\n  {label}")
        print(f"  PUT /events/{p['id']} name='{p['name'][:50]}' TSS={p['icu_training_load']}")

    if not args.execute:
        print("\n  DRY-RUN ONLY.")
        return

    c = ICUClient()
    for label, p in payloads:
        eid = p['id']
        print(f"\n  PUT {eid} ", end='', flush=True)
        try:
            result = c.update_event(eid, p)
            print(f"OK → TSS={result.get('icu_training_load')}")
        except Exception as e:
            print(f"FAILED: {e}")
            return
    # Second PUT for 5/29 to enforce TSS (ICU may recompute from ZWO)
    print(f"\n  Second PUT for 5/29 to enforce TSS=100...")
    cur = c._get(f"/athlete/{c.athlete_id}/events/109138284", params={"resolve":"true"})
    fix = {
        "type": cur.get("type","Ride"),
        "category": cur.get("category"),
        "start_date_local": cur.get("start_date_local"),
        "name": cur.get("name"),
        "icu_training_load": 100,
        "indoor": False,
        "external_id": cur.get("external_id"),
    }
    r = c.update_event(109138284, fix)
    print(f"  TSS enforced: {r.get('icu_training_load')} steps={len((r.get('workout_doc') or {}).get('steps',[]))}")
    print("\n  Done.")


if __name__ == "__main__":
    main()
