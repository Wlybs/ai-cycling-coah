---
date: 2026-05-26
tags: [coach-session, race-prep, taizijian, gpx-analysis]
related: [[races]] [[athlete]] [[sessions/2026-05-26-5-24-wuyi-race-analysis]]
---

# 2026-05-26 ｜ 5/31 太子尖 GPX 战术 prep (第一轮)

## 用户原始请求
"先分析5/31的gpx"

## 数据快照
- GPX: `/mnt/d/Cycling/icu/race_map/0531太子尖.gpx` (934 pts, 47.2km, +1197m)
- vault 锁定: CP=300W, FTP=300W, W' 22-25 kJ, AWC +10-12 kJ, 总池 35-36 kJ
- 用户 race-class ceiling: 5-10 名 (athlete.md hard rule)
- 应用 hard rules: 7 类爬坡 signature + 车队战术 3 阶段 + 下坡隐性税 + race-day TSB methodology
- **旧 report 5/4 已过期**: 当时把 race 框为"23km 单 TT 决战段", GPX 实测是 **3 段 HC + 2 段恢复**

## 真实地形（GPX 实测，200m smoothed）

| 段 | km | 长度 | 爬升 | 平均坡 | 最陡 1km | 性质 |
|---|---|---|---|---|---|---|
| 接近段 | 0-10.7 | 10.7km | +245m | 1.7% | km 9 @ 9.1% × 0.8km 短坎 | flat + bump |
| **HC1** | 13.4-16.4 | 3.0km | +167m | 5.6% | km 14.8 @ 6.5% | 第一筛选 |
| 中段 1 | 16.4-24 | 7.6km | -10m 净 | rolling | — | **下坡+flat 池子 reset** |
| **HC2** | 24.0-31.0 | 7.0km | +336m | 4.8% | km 27.2 @ 5.9% | sustained 22min Phase A+B 主战场 |
| **中段 2** | **31-40** | 9.0km | +90m 净 | 1-3% bumpy | — | **Phase C 控场预期窗** |
| **HC3** | 40.2-47.0 | 6.8km | +370m | 5.4% | km 45 @ 6.2% | 终段决胜 |
| 终点 500m | 46.66-47.16 | 0.5km | +24m | 6-8% × 200m + 缓 + 平 50m | — | 不是纯爬冲线 |

总: 25.4km (54%) climb / 16.4km (35%) flat / 5.2km (11%) descent / +1271m climb_rise

## 7 类爬坡 signature 映射

| Climb | 预测类型 | 预测 surge density | 预测 macroCV | 用户战术 |
|---|---|---|---|---|
| km 9 短坎 | ② 短试探 | 1+/min | 中 | 不响应 |
| HC1 | ①+②混合 | 1+/min | 中 0.18 | 顶住, 蹭 6 人车队 draft |
| HC2 | ③ Phase A 长坡 + B 单飞 | 1-1.5/min, peak heavy | <0.10 | **池子 all-in 22min**, 顶住=进 first group |
| HC2 后 chase | ④/⑦ chase phase | 1.5+/min | 0.13 | **必须跟集团**, 池子可能见底 |
| 中段 2 | ⑤ Phase C 控场 | <0.5/min | <0.10 | **休息 + 补给 + 池子 reset 8-10 kJ** |
| HC3 | ⑥ 终爬重组 | 1+/min | 0.10 | 守集团 |
| HC3 末段 km 45 | ⑦ 防御追击 | 1.5+/min | 0.13 | 必须跟, 池子见底 |
| 终点 200m | sprint | — | — | counter ≤200m (5/23 hard rule) |

## 池子累积消耗预测（用 CP=300W）

| 段 | 预测消耗 over CP | 池子状态 |
|---|---|---|
| 接近段 km 9 小坎 | 2-4 kJ | 22 kJ left |
| HC1 顶住 | 13-16 kJ | 6-9 kJ ← 第一次见底 |
| 中段 1 (7.6km 下+平) | reset +12-14 kJ | 20-22 kJ |
| HC2 顶住 22min | 18-22 kJ | 0 ~ -2 kJ (借 AWC) |
| 中段 2 (9km 缓 Phase C) | reset +8-10 kJ | 8-10 kJ |
| HC3 全程 20min | 12-15 kJ | -2 ~ -5 kJ |
| 终点 sprint 200m | + 3-4 kJ AWC | AWC 大半罐 |

累积消耗 ≈ 50-60 kJ over CP. 池子上限 35 kJ → race 间歇 + draft 维持运转。

**比 5/24 武义 (估累积 ~35 kJ) 多 50%+, 是迄今最长最累 race.**

## 与之前 3 场 race 累积难度对比

| race | 决战段 | 累积难度 | 名次 |
|---|---|---|---|
| 5/17 千峡湖 | ~17min HC | 中 | 8th |
| 5/23 平王 | ~24min HC | 中-高 | 8th |
| 5/24 武义 | multi 8 climb 90min | 高 | 8th |
| **5/31 太子尖** | **3 段 HC 复合 100+min** | **最高 +30-50%** | ? |

## 战术框架（待用户确认 4 项后细化）

### 决策树
```
HC1 顶住: 进 first group
HC2 22min: 是否顶住决定 race
  ├─ 顶住 → first group → 中段 2 reset → HC3 sprint
  └─ 不顶 → 第二集团 → 守 11-20 名
中段 2: 强制补给 + reset, 不主动跟攻击
HC3 末段: 守集团到 200m
终点 200m: 短陡 sprint (Type-II 优势 + 5/23 counter 200m hard rule 匹配)
```

### 用户确认 (2026-05-26 second round)
1. **车队 6 人**: 含 5/24 那 4 人 + 加 2 = 团队默契极高 + 实力很强
2. **天气**: 很热 + 无树荫 → race breaker, 需 race-day cooling protocol
3. **训练块**: 用户自定"多堆有氧巩固耐力"框架, 教练校准为 "5/27 BIG + 5/28 LIGHT + 5/29 Z2" 双峰
4. **目标**: 保 first group (= 8-12 名预测)
5. **Race-day hard rules 接受**:
   - HC2 km 27-31 末段 12min RPE 9 = release (first group 末位 vs 第二集团 8-15 名选择)
   - 终点 sprint counter ≤ 200m (5/23 实测硬约束)
   - HRV/RHR race-day 降档触发: **用户拒绝**, 全力以赴 race style (recorded as athlete preference)

## 训练块 (5/26-5/30 锁定版)

### TSB 校准
- 5/26 morning TSB = **+26.2** (user 提供 ICU live 值, 比 EOD 推算高 ~5-10)
- 现状深 stale (>+15 红线 11 点), 必须 load 不能 rest

### 5/26-5/30 设计 (双峰 load 模式)

| 日 | 课表 | TSS | 设计目的 |
|---|---|---|---|
| **5/26 Tue (今天)** | Z2 长拉 2-2.5h (含 commute) | **120** | 启动 ATL load, 不堆 ss |
| **5/27 Wed BIG** | **Z2 3h + 2×15min @ 270W ss 上限 embedded** 正午时段 | **210** | 双峰主峰: race-specific 神经锁定 + 巩固有氧 + 热适应 day-1 |
| **5/28 Thu LIGHT** | commute Z2 60-75min (AP 165-200W 自然踩) | **60-80** | 主动维持 ATL (完全 rest 会让 TSB 反弹深 stale) |
| **5/29 Fri** | Z2 长拉 2h 正午 | **130** | 巩固有氧 + 热适应 day-2 |
| **5/30 Sat** | **完全休息** + 30min 散步 + 拉伸 | 0 | race-1 hard rule |
| **5/31 Sun** | RACE | — | — |

### PMC 预测
- 5/30 EOD: ATL ≈ 80 / CTL ≈ 96
- **5/31 race-morning TSB ≈ +13-15** (sweet spot 边缘, 你 5/24 race +12 实证 OK)

### 5/27 BIG DAY 具体结构
```
0:00-1:00 Z2 暖身 200-220W (60min)
1:00-1:15 Set 1: 15min @ 270W (88-92% FTP ss 上限)
1:15-1:25 Z1 recovery 10min @ 150-170W
1:25-1:40 Set 2: 15min @ 275W (HC2 22min sustained 神经锁定)
1:40-3:30 Z2 长拉 200-220W (110min) ← 巩固有氧主体
3:30-end commute / cool down
```
**正午时段** 11:00-14:00 开始, 不补冰水, 拿热适应剂量

### 修订后训练块 (2026-05-26 雨天 + 强度先 + 丰富版 final)

**5/26 today**: trainer race-sim multi-block (雨天 + athlete.md trainer 规则修订后 trainer 无强度限制)

```
Indoor trainer 100min race-architecture mirror:

0:00-0:25 Z2 暖身 @ 200-220W

HC1 sim (10min):
  0:25-0:33 8min @ 285-295W (FTP-edge sustained, 第一筛选 sim)
  0:33-0:35 2min Z1 (descent 1 sim)

中段 1 sim (8min):
  0:35-0:43 8min @ 220-240W (rolling tempo, race 真实中段)

HC2 sim — 核心 25min:
  0:43-1:08 25min @ 280-290W sustained
  内嵌 4 × 30s surge to 320-330W at 8/13/18/23min marks
  (sim race 集团 surge + Phase A wear-down)
  1:08-1:13 5min Z1 (中段 2 控场 sim)

HC3 sim (15min):
  1:13-1:25 12min @ 290-300W (FTP-edge 终段)
  1:25-1:28 3 × 30s @ 350W with 30s Z1 (race-finish 防御 surges)
  1:28-1:30 30s @ 600-700W (终点 200m sprint sim)

1:30-1:45 Z2 cooldown @ 200W (15min)

Total 1:45, workout TSS ~170-190
要求: 风扇满载 + 室内 ≤25°C (防热衰减功率)
```

**5/27 Wed**: Z2 长拉 4-5h outdoor (路线用户选, 正午时段)
**5/28 Thu**: REST
**5/29 Fri**: Mountain 2 多 climb 变奏 (10/10/6.5min ladder + 30s sprint)
**5/30 Sat**: REST
**5/31 Sun**: RACE

PMC 推算: race-morning TSB ≈ +10.5 (sweet spot 中位)

### 撤回历史
- v1 5/26 早版 "Z2 4-5h 5/26 + ss 5/27" (顺序错, 强度→有氧反了)
- v2 5/26 中版 "Mountain 2 outdoor 2 × 10min + outdoor Z2 commute" (今天雨天不可行)
- **v3 5/26 终版 (上面)**: trainer race-sim multi-block + athlete.md trainer 规则修订

### 为什么不上 FTP 多组 (用户提议 3-4 set FTP)
- 5 天 absorb window 不够 (FTP-level adaptation 第 10-14 天兑现)
- 多组 FTP 在 race week 大概率只剩 fatigue 不剩 adaptation
- 实证: 5/12 30/30 课表对照, 兑现率打折
- 替代方案: ss 上限 (88-92% FTP) 拿 race-specific 神经锁定 + 池子消耗少 30%

## Race-day 战术 (锁定版)

### 接近段 km 0-10.7 (~16 min)
- AP 180-220W, 蹭 draft, 集团 mid-后段
- km 9 短坎 9.1% × 0.8km: 跟集团节奏不主动
- **不参与任何 surge**

### HC1 km 13.4-16.4 (3km @ 5.6%, ~10 min)
- AP 280-300W ≈ FTP
- 跟集团 surge 上限 450W × ≤5s
- 位置: 第一集团末位 (max draft)
- 池子预算: 13-16 kJ
- 决策门槛: 末段 HR 触 max-3 (197+) 或 RPE 8.5+ → ease 5W

### 中段 1 km 16.4-24 (7.6km, ~12 min)
- AP 150-200W reset
- HR 降到 LTHR-12 = 176
- **强制补给 1**: km 18-20 处 1 gel
- 下坡不极限过弯 (5/24 hard rule)

### HC2 km 24-31 (7km @ 4.8%, ~22 min) — RACE 核心开关
**前 10min (km 24-27 @ ~4.5%)**:
- AP 280-300W (= FTP), 跟集团不主动

**后 12min (km 27-31 @ ~5%)**:
- 6 人车队预测 sustained AP 320-340W rotation
- 决策门槛:
  - km 27 时 HR ≤ 190 + RPE ≤ 8 → 继续 deploy 池子 all-in
  - km 27 时 HR ≥ 193 或 RPE 9 → **主动降 280W 进第二集团**
- **HARD RULE (用户接受)**: RPE 9 = release, 不硬撑半坡

### 中段 2 km 31-40 (9km bumpy, ~12 min) — Phase C 控场预期窗
- AP 200-240W 跟车
- **强制补给 2**: km 32-35 处 2 gels + 500ml 水
- HR 降到 LTHR-15 = 173
- 池子 reset +8-10 kJ

### HC3 km 40-47 (6.8km @ 5.4%, ~20 min)
- 前 5min AP 270-290W
- km 42-43: 0.5-1 gel
- **km 44.4-45.6 (1.2km @ 6.2%)**: ⑦ 防御追击坡, 必须跟集团, 不主动
- 末段 km 45-47: AP 260-280W 保留池子

### 终点 500m (200m @ 6-8% + 100m 缓 + 50m 平)
- **HARD RULE (用户接受)**: counter ≤ 200m
- 等 200m 牌再开
- 跟最强 sprinter 轮 + 最后 100m 出
- 8-10s @ 600-700W full deploy
- 平路 50m 拱顶过线

## 补给方案

```
赛前 -3h: 米糊+香蕉+蜂蜜 150g carb + creatine 3g + 甜菜根粉 5g + 黑咖啡
赛前 -1h: 1 gel + 电解质水 250ml
赛前 -30min: 咖啡因粉 200mg (3.3mg/kg)
赛前 -5min: 1 gel

赛中 (~100min):
  - bidon 1: 750ml 电解质 + 50g carb powder
  - bidon 2: 750ml 水
  - km 18-20: 1 gel
  - km 32-35: 2 gels + 500ml bidon 2
  - km 42-43: 0.5 gel
  - 总: 6 gels (270g) + 50g bidon = 320g carb ≈ 192g/h ✓

赛后 30min 黄金窗: 米糊 100g + protein 30g + carb powder 50g
赛后晚: 200g+ carb 晚餐
```

## Race-day 装备 (高温配置)
- ✅ 头盔通风版 (不带 aero)
- ✅ 浅色 jersey + bib
- ✅ 防晒 50+ SPF
- ✅ 2 × 750ml bidon
- ✅ 起前 cooling: 冷水浸毛巾颈+大腿 5min + 冰水 200ml 一口
- ❌ 不带 jacket / 不带臂套 / 不带 aero 头盔
- ✅ 34T-34T 起步配置 (athlete 标配)

## Race-day 热门槛
- HR 单 bpm ↑ ≈ core temp +0.05°C
- 你 max HR 200 → 极限 core temp ~39.5°C
- race-3 carryover max HR 预测 -3 bpm → 额外砍 0.15°C 储备
- **HR 触 195+ 是热门槛红线** (不是体能问题, 是散热)

## 风险评估

| 风险 | 概率 | 影响 | mitigation |
|---|---|---|---|
| HC2 后 12min 掉队 | 40-50% | first group 失败 → 12-25 名 | RPE 9 release hard rule |
| 热衰竭 (core temp >39.5°C) | 25-30% | DNF 或保守完赛 | 3 天正午热适应 + cooling protocol + HR 195 红线 |
| race-3 carryover max HR -3~5 bpm | 70%+ | 末段 sprint 不上 | -5 bpm 校准决策 |
| 下坡 attack 隐性税 (~10kJ) | 90%+ | C8 类"低功率难受" | 中段 1+2 充分补给 offset |
| 6 人车队 sustained > ceiling | 60%+ | HC2 dropped | 接受 race-class ceiling 5-10 名 |
| 终点 sprint 早开冲 | 0% | (用户接受 200m hard rule) | hard rule lock |

## 预测名次
- **base case** (HC2 顶住 + sprint OK): **8-10 名**
- **upside** (热应对完美 + HC2 顶住 + sprint A+): 5-7 名
- **downside** (HC2 掉 + 热衰竭): 15-20 名
- **DNF 概率**: <5%

## 6 人车队 + 多车队 + 单兵的架构含义
- HC2 sustained team rotation 比 5/24 4 人版强 50%+
- HC2 22min sustained 是用户 5/24 C4 (4:15) 的 5 倍时长 → 真实可能在 km 27-29 之间被甩开
- 中段 2 Phase C 控场更稳 (5 人控场 vs 5/24 的 3 人), 用户休息窗更友好
- 多车队 chase 互相消耗 → 用户 sit-in 不响应是最优 race-craft

## 触发器
- 用户确认 4 项未决议项 → 第二轮战术细化 (具体功率区间 / 补给点 / 装备 / 决策门槛)
- 5/26-5/30 训练块设计 (用户后续单独 prompt)
- race-morning TSB 预测 (用 5/26 EOD + 后续训练 atl/ctl drift 推算)
