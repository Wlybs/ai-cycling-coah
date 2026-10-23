"""Push race-week plan 5/26-5/31 to ICU — 5/31 太子尖 prep.

6 PUT operations, no DELETE, no new event creation. Existing event IDs:
  - 109138281 (5/26) → Indoor TTE Race Mirror 2:00
  - 109138282 (5/27) → Z2 长拉 4-5h outdoor
  - 109138283 (5/28) → REST (keep)
  - 109138284 (5/29) → Mountain 2 race-rhythm 多 climb 变奏
  - 109138286 (5/30) → REST (race-1 hard rule)
  - 109138350 (5/31) → RACE (keep skeleton, update description)

Usage:
  python scripts/push_plan_race_week_5_31.py          # dry-run
  python scripts/push_plan_race_week_5_31.py --execute # PUT to ICU
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.fetcher.icu_client import ICUClient


def build_526_tte_payload() -> dict:
    """5/26 Indoor Trainer TTE Race Mirror — 2:00. NEW event (POST not PUT).

    Structure:
      Warmup ramp 15min (Z1→Z2)
      Set 1: 30min @ 280-290W (HC2 mirror + 8min over-shoot)
      Z1 recovery 10min @ 150W
      Set 2: 25min @ 285-295W (HC3 mirror, fatigued state)
      Z2 endurance 25min @ 220-240W
      Cooldown 15min ramp down

    TSS workout ~185-200, FTP=300W
    """
    workout_doc = {
        "description": (
            "Indoor Trainer TTE Race Mirror (5/31 太子尖 prep)\n"
            "Set 1: 30min @ 285W (HC2 22min sustained mirror + 8min over)\n"
            "Set 2: 25min @ 290W (HC3 mirror, fatigued state)\n"
            "Z2 padding + cooldown\n"
            "AC 16°C 全程 cool, 不混热"
        ),
        "ftp": 300,
        "duration": 7200,  # 2h
        "steps": [
            # Warmup ramp 15min (Z1 → Z2 progressive)
            {"duration": 900, "warmup": True, "ramp": True,
             "power": {"value": 60, "units": "%ftp"},
             "_power": {"value": 180.0, "start": 140.0, "end": 220.0}},
            # Set 1: 30min @ 285W (sweet spot upper, HC2 sim)
            {"duration": 1800,
             "power": {"value": 95, "units": "%ftp"},
             "_power": {"value": 285.0, "start": 280.0, "end": 290.0}},
            # Z1 recovery 10min (race 中段 sim)
            {"duration": 600,
             "power": {"value": 50, "units": "%ftp"},
             "_power": {"value": 150.0, "start": 145.0, "end": 155.0}},
            # Set 2: 25min @ 290W (FTP-edge, HC3 fatigued sim)
            {"duration": 1500,
             "power": {"value": 97, "units": "%ftp"},
             "_power": {"value": 290.0, "start": 285.0, "end": 295.0}},
            # Z2 endurance 25min @ 230W (巩固有氧底盘)
            {"duration": 1500,
             "power": {"value": 77, "units": "%ftp"},
             "_power": {"value": 230.0, "start": 220.0, "end": 240.0}},
            # Cooldown 15min ramp down
            {"duration": 900, "cooldown": True, "ramp": True,
             "power": {"value": 55, "units": "%ftp"},
             "_power": {"value": 165.0, "start": 200.0, "end": 130.0}},
        ],
    }

    return {
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "WORKOUT",
        "type": "Ride",
        "name": "Indoor TTE Race Mirror 30+25 (5/31 太子尖 prep)",
        "start_date_local": "2026-05-26T13:00:00",
        "end_date_local": "2026-05-26T15:00:00",
        "icu_training_load": 195,
        "description": (
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
            "- AC 16°C 全程 cool, 不混热 (5/27 outdoor 长拉 + 5/29 race-rhythm 已 cover 热适应)\n"
            "- 风扇坏 → AC + 多喝水补偿\n\n"
            "🍞 补给 (2h trainer):\n"
            "- 起前 1 gel\n"
            "- 60min 处: 1 gel + 500ml 电解质\n"
            "- 90min 处: 1 gel + 250ml\n"
            "- post 30min: 米糊 100g + protein 30g + 电解质大杯\n"
            "- 晚饭 250g+ carb (5/27 长拉 glycogen 储备)\n\n"
            "🎯 决策门槛:\n"
            "- Set 1 末 5min 功率掉 >10W → ease 5W 撑完\n"
            "- Set 1 末 10min 功率掉 >20W → 收, 进 Z1\n"
            "- Set 2 起手 RPE 9 → 砍 Set 2 到 12-15min\n"
            "- HR 触 max-3 (197+) → ease\n\n"
            "TSS target ~185-200. 此课直接 attack TTE 短板, race-week 最核心 quality 日.\n"
            "Plan v7 (2026-05-26 锁定终版)."
        ),
        "indoor": True,
        "moving_time": 7200,
        "external_id": "vault_plan_v7_5_26_tte_indoor",
        "training_availability": "NORMAL",
        "workout_doc": workout_doc,
    }


def build_527_z2long_payload() -> dict:
    """5/27 Outdoor Z2 长拉 4-5h + 热适应正午时段."""
    return {
        "id": 109138282,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "WORKOUT",
        "type": "Ride",
        "name": "Z2 长拉 4-5h outdoor + 热适应正午 (5/31 prep)",
        "start_date_local": "2026-05-27T11:00:00",
        "end_date_local": "2026-05-27T15:30:00",
        "icu_training_load": 210,
        "description": (
            "难度 6/10 (race week aerobic 巩固 + 热适应 day-1)\n\n"
            "功率区间:\n"
            "- 全程 Z2 200-220W (67-73% FTP)\n"
            "- IF 目标 0.68-0.72 → TSS ~200-220\n"
            "- 不冲坡, 不响应路上骑手, 纯巩固有氧\n\n"
            "🔥 底线:\n"
            "- AP 200-220W 自然踩\n"
            "- 不上 sweet spot, 不冲坡\n"
            "- 11:00-15:30 正午时段 = 热适应主体 (Périard 60-90min 持续热暴露协议)\n"
            "- 不补冰水, 主动暴露\n\n"
            "📋 路线: 用户选熟悉 long route, 低海拔避免 elevation 叠加\n\n"
            "🍞 补给 (4-5h ride, race-day 补给模板预演):\n"
            "- 出发前 1.5h: 米糊+香蕉+蜂蜜 (~120-150g carb) + 咖啡\n"
            "- 路上水壶: 电解质粉 + carb powder (~60g carb/壶)\n"
            "- 每 30min: 1 gel (45g) → 总 6-8 gel = 270-360g carb\n"
            "- 电解质必加 (钠 500-800mg/h)\n"
            "- 水: 1L/h, 共 4-5L (热暴露出汗大)\n"
            "- 回程最后 30min IF ≤ 0.55 防过累\n"
            "- 结束 30min: 米糊 80g + protein 30g + 电解质大杯\n"
            "- 晚饭 250-300g carb (race week glycogen 巩固)\n\n"
            "目的: race week aerobic engine 巩固 + 热适应 day-1 partial benefit (3 天累积 ~30-40%).\n"
            "Plan v7."
        ),
        "indoor": False,
        "moving_time": 16200,  # 4.5h
        "external_id": "vault_plan_v7_5_27_z2_long",
        "training_availability": "NORMAL",
        "workout_doc": None,  # free ride
    }


def build_528_rest_payload() -> dict:
    """5/28 REST."""
    return {
        "id": 109138283,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "NOTE",
        "name": "完全休息 (race day-3, glycogen + 神经 reset)",
        "start_date_local": "2026-05-28T00:00:00",
        "end_date_local": "2026-05-28T23:59:00",
        "icu_training_load": 0,
        "description": (
            "难度 0/10. race day-3 完全休息.\n\n"
            "🔥 底线: 完全不上车. 不 commute, 不散步超过 45min.\n"
            "推荐 30min 散步 + 15min 拉伸 (重点股四头 + 髋屈肌).\n\n"
            "🍞 补给:\n"
            "- carb 7-8g/kg (~450-500g, race week 上限边缘)\n"
            "- 蛋白 1.6g/kg (~100g)\n"
            "- 多睡 8h+\n"
            "- 不喝酒\n"
            "- creatine 3g + β-丙氨酸 4g daily stack\n\n"
            "目的: 5/26 + 5/27 双峰 load 后, ATL 顶峰 ~105, 必须主动 reset 一天.\n"
            "Plan v7."
        ),
        "indoor": False,
        "show_as_note": True,
        "not_on_fitness_chart": True,
        "external_id": "vault_plan_v7_5_28_rest",
        "training_availability": "NORMAL",
        "workout_doc": None,
    }


def build_529_race_rhythm_payload() -> dict:
    """5/29 Mountain 2 多 climb race-rhythm ladder."""
    workout_doc = {
        "description": (
            "Mountain 2 多 climb race-rhythm ladder (5/31 太子尖 prep)\n"
            "Climb 1: 10min @ 275W (HC1 race-pace sim)\n"
            "Climb 2: 10min @ 285W (HC2 race-pace sim)\n"
            "Climb 3 (partial): 6min @ 295W (HC3 末段 sim) + 30s @ 600W sprint top\n"
            "Set 间 descent 5-6min recovery"
        ),
        "ftp": 300,
        "duration": 11400,  # ~3h10min total (含 commute)
        "steps": [
            # Warmup commute bike out (60min ramp 200W avg)
            {"duration": 3600, "warmup": True, "ramp": True,
             "power": {"value": 67, "units": "%ftp"},
             "_power": {"value": 200.0, "start": 180.0, "end": 220.0}},
            # Climb 1: 10min @ 275W (HC1 sim)
            {"duration": 600,
             "power": {"value": 92, "units": "%ftp"},
             "_power": {"value": 275.0, "start": 270.0, "end": 280.0}},
            # Descent recovery 5min
            {"duration": 300,
             "power": {"value": 50, "units": "%ftp"},
             "_power": {"value": 150.0, "start": 145.0, "end": 155.0}},
            # Climb 2: 10min @ 285W (HC2 sim)
            {"duration": 600,
             "power": {"value": 95, "units": "%ftp"},
             "_power": {"value": 285.0, "start": 280.0, "end": 290.0}},
            # Descent recovery 5min
            {"duration": 300,
             "power": {"value": 50, "units": "%ftp"},
             "_power": {"value": 150.0, "start": 145.0, "end": 155.0}},
            # Climb 3 partial: 6min @ 295W (HC3 末段 sim)
            {"duration": 360,
             "power": {"value": 98, "units": "%ftp"},
             "_power": {"value": 295.0, "start": 290.0, "end": 300.0}},
            # Sprint top: 30s @ 600W (终点 sim, Type-II 神经唤醒)
            {"duration": 30,
             "power": {"value": 200, "units": "%ftp"},
             "_power": {"value": 600.0, "start": 580.0, "end": 620.0}},
            # Cooldown commute bike home (60min)
            {"duration": 3600, "cooldown": True, "ramp": True,
             "power": {"value": 67, "units": "%ftp"},
             "_power": {"value": 200.0, "start": 220.0, "end": 180.0}},
            # Continued Z2 padding (10min)
            {"duration": 600,
             "power": {"value": 70, "units": "%ftp"},
             "_power": {"value": 210.0, "start": 200.0, "end": 220.0}},
        ],
    }

    return {
        "id": 109138284,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "WORKOUT",
        "type": "Ride",
        "name": "Mountain 2 race-rhythm 3 climb ladder + sprint (5/31 prep)",
        "start_date_local": "2026-05-29T10:00:00",
        "end_date_local": "2026-05-29T13:10:00",
        "icu_training_load": 160,
        "description": (
            "难度 7/10 (race day-2 race-rhythm + 热适应 day-3)\n\n"
            "功率结构 (Mountain 2 多 climb ladder):\n"
            "- Climb 1: 10-11min @ 270-280W (sweet spot, HC1 race-pace sim)\n"
            "- Descent + reposition: 5-6min Z1\n"
            "- Climb 2: 10-11min @ 280-290W (sweet spot 上沿, HC2 race-pace sim)\n"
            "- Descent + reposition: 5-6min Z1\n"
            "- Climb 3 (上半段, 6-7min): @ 290-300W (FTP-edge, HC3 末段 sim)\n"
            "- 到 6-7 分钟节点立刻接 30s @ 600W (Type-II 神经唤醒 + 终点 sim)\n"
            "- 下坡撤退, bike home Z2 巩固\n\n"
            "🔥 底线:\n"
            "- Climb 1/2 是 race-pace 不是 max, RPE 7-8 not 9\n"
            "- Climb 3 是 race-specific sim, RPE 8-9 OK\n"
            "- Sprint 不超 700W (留 race-day 弹药)\n"
            "- 周五 Mountain 2 人少, 训练 OK\n\n"
            "📋 路线: 25-30km bike out → Mountain 2 (3.1km × 6.6%) → 3 个 climb → bike home\n\n"
            "🍞 补给 (~3h ride):\n"
            "- 出发前 1h: 米糊 100g + 香蕉 + 黑咖啡\n"
            "- 水壶: 电解质 + carb powder ~60g\n"
            "- Climb 1 前: 1 gel\n"
            "- Climb 2 后: 1 gel + 250ml\n"
            "- bike home 段: 1 gel\n"
            "- 总 3-4 gel = 135-180g carb\n"
            "- post 30min: 米糊 80g + protein 30g + 电解质\n\n"
            "🎯 决策门槛:\n"
            "- Climb 1 RPE 已 9 + 功率掉 → 砍后续 2 climbs\n"
            "- Climb 2 完不成 280W → Climb 3 取消\n"
            "- Sprint 不到 600W 也 OK, 不强求 (race-day 弹药优先)\n\n"
            "热适应 day-3: 10:00-13:10 正午时段, 不补冰水, 主动暴露.\n"
            "Plan v7."
        ),
        "indoor": False,
        "moving_time": 11400,
        "external_id": "vault_plan_v7_5_29_mt2_race_rhythm",
        "training_availability": "NORMAL",
        "workout_doc": workout_doc,
    }


def build_530_rest_payload() -> dict:
    """5/30 REST race-1 hard rule."""
    return {
        "id": 109138286,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "NOTE",
        "name": "完全休息 (race day-1, hard rule, 不开腿)",
        "start_date_local": "2026-05-30T00:00:00",
        "end_date_local": "2026-05-30T23:59:00",
        "icu_training_load": 0,
        "description": (
            "难度 0/10. race day-1, athlete.md HARD RULE: 不开腿.\n\n"
            "🔥 底线: 完全不上车. 不 commute, 不开腿课.\n"
            "- 30min 散步 + 20min 拉伸 (重点股四头 + 髋屈肌 + 腰)\n"
            "- mental prep: 复盘 race-day 战术 (HC2 决策门槛 + sprint 200m hard rule)\n"
            "- race-day morning warmup 自带激活, 今天不需要 opener\n\n"
            "🍞 补给 (race-day -1, glycogen super-compensation 收尾):\n"
            "- carb 8-10g/kg (~500-610g, race-day 上限)\n"
            "- 蛋白 1.6g/kg (~100g)\n"
            "- 早 200g carb 早饭\n"
            "- 午 250g carb 午饭\n"
            "- 晚 200g carb 晚饭 (8 点前吃完)\n"
            "- 电解质粉补足\n"
            "- 多睡 8-9h (race-day morning 7:00 起算)\n"
            "- 不喝酒, 不熬夜\n"
            "- creatine 3g + β-丙氨酸 4g\n\n"
            "🎒 装备准备 (今晚检查):\n"
            "- 自行车 + 头盔通风版 (不带 aero) + 浅色 jersey + bib\n"
            "- 防晒霜 50+ SPF\n"
            "- 2 × 750ml bidon (电解质 + 水)\n"
            "- 6 gels + 1 备用\n"
            "- 咖啡因粉 200mg (赛前 30min)\n"
            "- 甜菜根粉 5g (赛前 3h)\n"
            "- creatine 3g (赛前 3h)\n"
            "- 34T-34T 起步配置 (athlete 标配)\n"
            "- ❌ 不带 jacket / 不带臂套 / 不带 aero 头盔 (高温赛)\n"
            "- ice sock or 颈部冰巾 (race-day morning cooling)\n\n"
            "目的: 5/27 + 5/29 双峰 load 后, ATL 顶峰 ~99, 5/30 完全 rest 让 ATL 落到 ~85.\n"
            "race-morning TSB 预期 +10-12 (sweet spot 中位).\n"
            "Plan v7."
        ),
        "indoor": False,
        "show_as_note": True,
        "not_on_fitness_chart": True,
        "external_id": "vault_plan_v7_5_30_rest_race_1",
        "training_availability": "NORMAL",
        "workout_doc": None,
    }


def build_531_race_payload() -> dict:
    """5/31 太子尖 race tag + race-day 战术 + 补给摘要."""
    return {
        "id": 109138350,
        "calendar_id": 1,
        "athlete_id": "i176789",
        "category": "RACE_A",
        "type": "Ride",
        "name": "🏁 5/31 太子尖 race (47.2km / +1197m, 本月最难, 保 first group)",
        "start_date_local": "2026-05-31T09:00:00",
        "end_date_local": "2026-05-31T11:30:00",
        "icu_training_load": 200,
        "description": (
            "难度 10/10 — 5 月 race block 最难一场, 本月 A race.\n\n"
            "📊 race 架构 (GPX 实测, 与旧 5/4 report 不同):\n"
            "- 总 47.2km / +1197m / 海拔 160→1357m\n"
            "- 3 段 HC + 9km 中段恢复 (不是 23km 单 TT)\n"
            "  - 接近段 0-10.7km (1.7% flat with bump at km 9 9.1%)\n"
            "  - HC1: 13.4-16.4km (3km @ 5.6%, ~10min) — 第一筛选\n"
            "  - 中段 1: 16.4-24km (7.6km, 下坡+flat, 池子 reset 窗)\n"
            "  - HC2: 24-31km (7km @ 4.8%, ~22min) — RACE 核心开关\n"
            "  - 中段 2: 31-40km (9km bumpy flat, Phase C 控场预期窗)\n"
            "  - HC3: 40.2-47km (6.8km @ 5.4%, ~20min) — 终段\n"
            "  - 终点 500m: 200m @ 6-8% 短陡 + 100m 缓 + 50m 平\n\n"
            "🏁 战术 (athlete.md hard rule 锁定):\n"
            "1. 接近段: AP 180-220W, draft mid-后段, km 9 短坎不主动\n"
            "2. HC1: AP 280-300W ≈ FTP, 跟集团末位, 池子预算 13-16 kJ\n"
            "3. 中段 1: AP 150-200W reset, HR降 LTHR-12, 强制补给 1 gel km 18-20\n"
            "4. HC2 (RACE 核心 22min):\n"
            "   - 前 10min: AP 280-300W 跟集团\n"
            "   - 后 12min: 决策门槛 RPE 9 = release (HARD RULE)\n"
            "5. 中段 2: AP 200-240W, 强制补给 2 gels + 500ml km 32-35\n"
            "6. HC3: AP 270-290W 守集团, km 44-46 防御追击不主动\n"
            "7. 终点 200m: counter ≤ 200m (HARD RULE), 等 200m 牌再开\n\n"
            "👥 集团架构: 6 人冠军车队 + 多个类似车队 + 你单兵\n"
            "- 车队 3 阶段: Phase A 轮流 wear-down → Phase B 单飞 → Phase C 控场\n"
            "- 你不响应任何 attack, 蹭 draft 守 first group\n\n"
            "🌡 高温 race (无树荫):\n"
            "- 头盔通风, 浅色 jersey, 防晒 50+\n"
            "- HR 触 195+ 是热门槛红线 (race-3 carryover max HR -3~5 bpm)\n"
            "- 2 × 750ml bidon (电解质 + 水)\n"
            "- 起前 cooling: 冷水浸毛巾颈+大腿 5min + 冰水 200ml\n\n"
            "🍞 补给 (~1h40min race):\n"
            "- 起前 -3h: 米糊+香蕉+蜂蜜 150g carb + creatine 3g + 甜菜根粉 5g + 黑咖啡\n"
            "- 起前 -1h: 1 gel + 电解质水 250ml\n"
            "- 起前 -30min: 咖啡因粉 200mg (3.3mg/kg)\n"
            "- 起前 -5min: 1 gel\n"
            "- 赛中: 6 gels (270g) + 50g bidon = 320g carb ≈ 192g/h\n"
            "- post 30min: 米糊 100g + protein 30g + carb powder 50g\n\n"
            "🎯 预测名次:\n"
            "- base case (HC2 顶住 + sprint OK): 8-10 名\n"
            "- upside (热应对完美 + HC2 顶住 + sprint A+): 5-7 名\n"
            "- downside (HC2 掉 + 热衰竭): 15-20 名\n"
            "- DNF 概率 <5%\n\n"
            "目标: 保 first group (= 8-12 名 race-class ceiling)\n"
            "Plan v7 / GPX 实测 / 详 [[vault sessions/2026-05-26-5-31-taizijian-gpx-prep]]"
        ),
        "indoor": False,
        "moving_time": 6000,  # ~100min
        "external_id": "vault_plan_v7_5_31_race_taizijian",
        "training_availability": "NORMAL",
        "workout_doc": None,
    }


def print_payload_summary(label: str, payload: dict):
    """Print a human-readable summary of one PUT payload."""
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    eid = payload.get('id', 'NEW (POST)')
    print(f"  /athlete/i176789/events/{eid}")
    print(f"  Name: {payload['name']}")
    print(f"  Start: {payload['start_date_local']}")
    print(f"  Category: {payload['category']}")
    print(f"  TSS: {payload.get('icu_training_load', 0)}")
    desc = payload.get('description', '')
    print(f"  Description ({len(desc)} chars)")
    wd = payload.get('workout_doc')
    if wd:
        steps = wd.get('steps', [])
        print(f"  Workout steps: {len(steps)} top-level")
        for i, s in enumerate(steps):
            if 'reps' in s:
                print(f"    [{i}] {s.get('text', '')} {s.get('reps')}× duration={s['duration']}s")
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
        print(f"  Workout doc: None (free ride / note)")


def main():
    parser = argparse.ArgumentParser(description="Push race-week plan 5/26-5/31 to ICU")
    parser.add_argument("--execute", action="store_true",
                        help="Actually PUT to ICU API (default: dry-run only)")
    args = parser.parse_args()

    # (label, payload, op) — op="POST" for new event, "PUT" for update
    payloads = [
        ("POST 1/6: 5/26 Indoor TTE Race Mirror (NEW event)", build_526_tte_payload(), "POST"),
        ("PUT 2/6: 5/27 Z2 长拉 4-5h outdoor (replaces 109138282)", build_527_z2long_payload(), "PUT"),
        ("PUT 3/6: 5/28 REST (keeps 109138283, updates desc)", build_528_rest_payload(), "PUT"),
        ("PUT 4/6: 5/29 Mountain 2 race-rhythm (replaces 109138284)", build_529_race_rhythm_payload(), "PUT"),
        ("PUT 5/6: 5/30 REST race-1 (replaces 109138286)", build_530_rest_payload(), "PUT"),
        ("PUT 6/6: 5/31 race tag (updates 109138350)", build_531_race_payload(), "PUT"),
    ]

    for label, p, op in payloads:
        print_payload_summary(label, p)

    if not args.execute:
        print(f"\n{'=' * 70}")
        print("  DRY-RUN ONLY. No API calls made.")
        print("  To execute: python scripts/push_plan_race_week_5_31.py --execute")
        print(f"{'=' * 70}")
        return

    # Execute
    print(f"\n{'=' * 70}")
    print("  EXECUTING — calling ICU API now")
    print(f"{'=' * 70}")
    client = ICUClient()
    for label, p, op in payloads:
        eid = p.get('id', 'NEW')
        print(f"\n  {op} event {eid} ({p['name'][:50]}...) ", end='', flush=True)
        try:
            if op == "POST":
                result = client.create_event(p)
            else:
                result = client.update_event(eid, p)
            print(f"OK")
            print(f"    -> id: {result.get('id', '?')}")
            print(f"    -> name: {result.get('name', '?')}")
            print(f"    -> start: {result.get('start_date_local', '?')}")
            print(f"    -> TSS: {result.get('icu_training_load', '?')}")
        except Exception as e:
            print(f"FAILED: {e}")
            return
    print(f"\n  All 6 operations succeeded.")
    print(f"  Next: cd icu && .venv/bin/python scripts/sync_events.py")


if __name__ == "__main__":
    main()
