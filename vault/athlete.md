# Athlete — 长期定性档案

> **HARD RULE**: 这里**只放定性 / 不变项**。所有数值（FTP / 体重 / Pmax / CP / W'）从 `icu/coach_memory/athlete_snapshot.json` 等 sync 输出读，**永远不从这里读**。

## 身份

- 吴佳乐 / wjlwjl1202@gmail.com
- 杭电毕业生
- WSL2 + Windows，主要从 `/mnt/d/Cycling/icu/` 工作

## 生理 / 训练特质（定性）

- **Type-II 主导**（fast-twitch dominant）。配速 + 高 cadence 是反本能的，需要刻意练。
- **神经系统敏感**。TSB > +15 反而会神经性 stale（HR 飙升、力量空心）。**A 赛 taper 目标 TSB = 0 ~ +5**，绝对不是教科书 +20。
- **Anaerobic-dominant PD shape**。5/60min 比例 ≈ 1.41，属于 Ardennes / Puncheur 体质，不是 long-aerobic specialist。**自分类 = 爬坡手 / Puncheur**。
- **疲劳衰减率高**，CP5/CP9 等满血纸面数据在比赛后期兑现率约 85-90%。战术核心 = 节省 W'，疲劳后的相对优势。
- **低 cadence 习惯**：心率会被压低但肌肉疲劳累积更快。长 ride 中 cadence 漂移可能是有意控速，不是被动衰减。
- **股四头主导发力模式（HARD RULE 2026-05-12）** — 用户主动选择 + 输出功率更高（试过后侧链发力但功率显著降低）。这是 Type-II 主导运动员的最优发力策略，**不是 ACL 术后代偿**，不要建议改。后果：
  - 强度大 / 拉扯多 → 大腿前侧（股四头）先酸，后侧链很少酸
  - 多次摇车起爆（高扭矩）会显著放大酸感（5/12 实测 12 次 r1 高扭矩 → 大腿前侧明显酸）
  - **TT 姿势放大股四头酸感**（髋角变小 + 肌纤维拉长状态下发力）→ 高扭矩课后 24-48h 不上 TT
  - **race 中股四头是限速因素** → 起跑后 30 min 内不上 TT，长平路上 TT 警惕大腿前侧"酸"（不是"紧"）信号
- **「末段 all-out」长期训练习惯（HARD RULE 2026-05-12）** — 大多数训练用户会在最后一个 set 主动追加额外压榨（even 在课表没要求时）。Belief = "更进一步压榨能更好提高"。教练响应：
  - **base / build 期**：OK，作为有效的"破天花板"刺激
  - **race 周（race 前 7 天）**：风险高（消耗 race day 神经资源 + 拉长恢复期）
  - **课表设计原则**：不要假装用户会按字面 hold 住，要么显式把"末段额外压榨空间"纳入设计（推荐），要么明确写"末段不要 all-out hold X W 收尾"
  - 5/12 实测：30/30 课最后 1 ascent 主动 all-out → 等于"30/30 + 末段冲刺课"两课合一

## 受伤 / 医疗（永久）

- **右膝 ACL 重建** — 完全愈合。无痛时 100% 训练。**任何新膝痛立刻 flag**。
- **半月板**（详见 5/4 athlete_snapshot 上下文）— 已稳定。

## 装备

- 公路车 6.3 kg
- 34T 牙盘 + 34T 飞轮（1:1）— 备爬坡赛配置

## Bike fit / 姿态耐受（2026-06-22 视频校准）

- IMG_7959 = 坐垫中部 + 上把位，普通骑行姿态。
- IMG_7960 = 坐垫后部，平路偶尔后坐姿态。
- IMG_7961 = 坐垫前部，高强度爬坡姿态。
- IMG_7962 = 模拟 TT 低趴姿态，速度很快时追求气动收益；长时间持续会诱发腰疼。
- IMG_7963 = 下把位巡航姿态，用于平路巡航并缓解 7962 的肌肉压力；长时间持续也会诱发腰疼。
- 2026-06-22 用户反馈：五种姿态均无明显即时不适，腰疼只在 7962/7963 持续时间很长时出现。

## 训练偏好 / 反 pattern

- 不喜欢被欠练。觉得"教练给得不够狠"是过往主要痛点。
- 接受 SST 大容量退阶 + 微间歇变种，单次绞肉机课表（IF 0.88+）不能日日练。
- **拒绝 sycophancy**。我顶回去时，先 re-check 数据再决定是否改口；3 次 flip = 必须 restart。
- **课表里不出现 Z1，也不出现 <1h 的 Z2**（HARD RULE 2026-05-11）。Active recovery 选项 = 全休 或 ≥60min Z2，没有中间档。Coach 不要安排 "30-40min Z1 easy" 这种课。
- **赛前一天不开腿**（HARD RULE 2026-05-11）。race-1 习惯是休息或随便骑（commute），不要正式开腿课（30s × N short bursts 也不要）。race day morning warmup 自带激活。
- **race calendar 整体优先于单点 peaking**（HARD RULE 2026-05-11）。多场 race 块（如 5/17 → 5/31 这种 20 天连续 race）时拒绝为单场 A 赛牺牲后续 race 的 W' adaptation 准备。Coach 设计 plan 必须把整个 race block 的 adaptation 窗口纳入考虑，不要只盯下一场。

## 数据契约

- 所有"今天 FTP 多少"的问题：读 `icu/coach_memory/athlete_snapshot.json` `ftp_set` 字段
- 体重：读 `summary.icu_weight`（来自最新活动）
- 90d PB：`snapshot.recent_pbs.<duration>min.watts_90d`，**注意是 rolling-window，不是真 all-out**，用之前先和我确认锚点
- 校准过的爬坡 η 表：见 `~/.claude/projects/-mnt-d-Cycling/memory/calibrated_climbing_efficiency.md`，4-6%≈0.70 / 6-8%≈0.74 / 8-12%≈0.85+

## TSS 负荷分级（用户自定义，HARD RULE 2026-05-09）

| 类型 | 周 TSS 范围 | 单日 TSS |
|---|---|---|
| **高负荷周** | 900-1000+ | — |
| **普通周** | 600-800 | — |
| **减量周** | 400-600 | — |
| **大负荷单日** | — | **≥200**（**触发次日强制休**） |
| **中等单日** | — | **100-199**（**可背靠背**） |
| **轻日** | — | <100 |

## 训练日编排规则（HARD RULE 2026-05-09 修订 v2）

- **强制休息触发条件**：单日 TSS **>200 AND TSB <-20**（两个条件**同时**满足才强制休）
- TSB ≥ -20 → 即使单日 200+ TSS 也可继续训练（身体疲劳尚可）
- 单日 ≤200 TSS → 任何 TSB 状态都可继续
- **"强度后跟有氧"是 coach 判断，不是死规矩** — 是否要 A 日由 coach 根据上下文（race 临近度 / HRV / 课表组合）决定，不是机械应用
- 用户偏好：少天数高质量 > 天天练
- 用户偏好：active recovery → 全休（如果不是必需）

**plan 设计 checklist**：
- 单日 TSS > 200 + TSB < -20 时下一日 → 强制全休
- 否则 coach 自由决定下一日（可训可休）
- 永远参考最新 fitness_trend.json 的 TSB 决定，不假设

**违规反例**：
- ❌ 任何课后机械加 A 日（"因为 H 后必须 A"），不考虑实际需要
- ❌ 把"用户状态好"的日子排成 90min Z2 (~65 TSS) 的轻松课
- ❌ 见单日 200+ 自动后排休，不管 TSB

**当前 TSB 参考**（plan 设计时每次拉最新值）：
- TSB > 0 → 完全可训
- TSB -10 至 0 → 可训正常
- TSB -20 至 -10 → 警觉，硬日后看 HRV
- TSB < -20 + 200+ TSS → 强制休

## 训练执行环境（HARD RULE 2026-05-09）

**用户偏好：路骑 > 骑行台**（race-specificity，模拟真实爬坡节奏 + 变速）

**仅这 3 类 session 必须上骑行台**：
1. 30/30 类 Tabata — 节奏精确路骑做不准
2. 赛前开腿 — 时间短，需要精准 anaerobic 激活
3. HRV 警报后恢复 spin — 控制不要骑过头

**其它一律路骑优先**（race-rhythm / OU / SST / Z2 长拉 等）

## 家附近可用爬坡场地（HARD RULE 2026-05-09 修订）

| 场地 | 距家 | 细节 | 适合 session | 周末可用？ |
|---|---|---|---|---|
| **Mountain 1 A 面** | 25km bike out | 2.23km × 5.6% = **5-6min 爬, descent 3-4min** | 1-2 set race-rhythm 单 set / 短间歇 | ❌ **景区，周六周日避** |
| **Mountain 1 B 面** | 25km bike out | 2.52km × 5.6% = **6-7min 爬, descent 3-4min** | 1 set race-rhythm 完整 / 短-中 间歇 | ❌ **景区，周六周日避** |
| **Mountain 2** | 30km bike out | 3.1km × 6.6% = **10-11min 爬, descent 5min** | 1 set OU **10min 版本** / SST 单组 / 中长间歇 | ✅ 周末 OK |
| **Mountain 3** | 25km bike out | 0.8km × 8.1% = **2-3min 爬, descent 2min**，结构 **陡-缓-陡-缓-陡**（陡 ~15% / 缓 ~3%） | **30/30 / 30/15 / 40/20 完美**（terrain-driven），1 ascent = 3 reps natural | ✅ 周末 OK，人少 |
| 其它远坡 | >30km | 太远，纯 bike 热身浪费时间 | 必须 4+2 | — |

**门口平路充足** → Z2 / 长拉 / 神经短爆 / 恢复 spin / **不能上坡的高强度课**（如 opener、平路冲刺）

## Mountain 3 30/30 模板（HARD RULE）

利用 Mountain 3 陡-缓-陡-缓-陡 自然节奏：
- 1 ascent = 3 个 30s 强度段（terrain-driven，不靠计时器）
- 4 ascents = 12 reps 30/30（标准 1 set）
- 8 ascents = 24 reps（标准 2 sets）
- ascent 之间 4-5min recovery（descent + reposition）

**最适合**：30/30 Tabata、30/15 Bartali 风格、40/20 hover above CP

## 补给库存与策略（HARD RULE 2026-05-09 修订 v2）

### 库存清单
| 物品 | 单位 | 用途 |
|---|---|---|
| **Gel** | 45g carb / 只 | 训练中 / 赛前 / 赛中快糖 |
| **电解质粉** | 一袋一壶 | 长 ride 水壶必加 |
| **Protein powder** | post-workout | 30min 黄金窗口 |
| **Carb powder** | post-workout | 30min 黄金窗口 |
| **米糊** | post-workout | 30min 易消化恢复 carb |
| **咖啡因粉** | 200mg / 只 | 赛前 30min, race-day only |
| **甜菜根粉** | 5g / 只 | 赛前 2-3h, race-day only |
| **Creatine** | 3-5g / day | 持续摄入 (loading + maintenance) |
| **β-丙氨酸** | 4-6g / day | 持续摄入 (4-6 周 loading 提 lactate buffer) |

### 用户饮食习惯（基线）
- **每日 2 顿正餐**（早餐 + 晚餐 或 午餐 + 晚餐）
- **轻吃**：1 顿 ~100g carb（一碗多米饭 / 中份意面）= 不饿
- **重吃**：1 顿 3-5g/kg = 180-300g carb（**很饱**）
- **主要 carb 源**：白米饭 / 面条 / 意面（高 GI 易消化）
- **高碳水耐受能力**：每日上限 10g/kg = 610g/day（普通人 7-8g/kg），**训练中可吸收 60-90g/hr**

### 日常 carb 摄入按训练负荷自适应（HARD RULE）

| 当日类型 | Carb 目标 | 怎么吃 |
|---|---|---|
| Rest 日 | **5g/kg = ~300g** | 2 × 150g 正餐即可 |
| 轻日 (~50 TSS) | **5-6g/kg = ~350g** | 2 × 150g + 训练 1 gel + 米糊 |
| 中等训练 (~100 TSS) | **6-7g/kg = ~400g** | 2 × 150g + 训练 100g (gel) + 米糊 50g |
| 硬日路骑 (~150-180 TSS) | **8-9g/kg = ~500-550g** | 2 × 200g + 训练 4 gel (180g) + 米糊 80g |
| Race day | **8-10g/kg = ~500-610g** | 早 150g + 赛中 + post 200g + 晚 200g |

**含义**：
- **不要强求每日 7-8g/kg**，会持续水重 + 肠胃负担
- 训练日补给 + post 米糊**自然累计** carb，不用刻意吃
- 10g/kg 极限留给 race 周后段 + race day + carb-load 战略时刻

### 训练日补给模板

**长 ride (>2h, 含 commute, 如 5/10/11/13)**:
- 出发前 2h: 米糊+香蕉+咖啡 (~100-120g carb)
- 路上水壶: 电解质粉 + carb powder (~60g carb/壶)
- 1 set 前: 1 gel (45g)
- 长 set 之间: 1 gel 每 30-40min（视长度 2-3 个）
- 回程后段: 1 gel
- **post (30min 内)**: 米糊 + protein 30g + carb powder 80-100g

**短 session (<60min)**:
- 出发前 1h: 1 gel + 电解质水
- 中无需补
- post: protein 25g + 米糊小份 (~50g carb)

**Rest day**:
- 正常 carb 5g/kg = ~300g
- protein 1.6g/kg
- creatine + β-丙氨酸 持续摄入

### Race-day 完整协议（5/17 / 5/23 / 5/24 / 5/31）

**赛前**:
- 3-4h: 米糊+香蕉+蜂蜜 ~150g carb + creatine 3g + 甜菜根粉 5g + 黑咖啡
- 1-2h: 1 gel + 电解质水
- 30min: **咖啡因粉 200mg** (3.3mg/kg 完美剂量)
- 5min: 1 gel (即时葡萄糖)

**赛中** (race < 30min): 通常无需补（>45min 才需要每 25min 1 gel）

**赛后** (30min 内): 米糊大份 ~100g carb + protein 30g + carb powder 50g

**赛日晚**: 200g+ carb 晚餐 准备后续 (e.g., 5/23/24 背靠背 race)

### 永久 stack（每日固定，包括 rest 日）
- Creatine 3g
- β-丙氨酸 4g（loading 阶段分次 1-2g 每次避免 paresthesia）

## Commute 功率管理（HARD RULE 2026-05-09）

**核心原则：commute 不是训练核心，不需严格监控功率**

| 场景 | 功率 | 监控要求 |
|---|---|---|
| 任何 commute (race 周 / 非 race 周) | **AP 150-180W**（自然踩, "Z1.5"=高 Z1/低 Z2 边界）| ❌ 不看码表 |
| Race day eve commute (e.g., 5/16) | **< 150W** 刻意保腿 | 偶尔瞄一眼 |
| Race-day to start line | < 150W + 短爆 1-2 次激活 | 不看 |

**含义**：
- 出门 commute 自然踩 = 完美（150-180W AP 自然落在 50-60% FTP）
- 不用强迫 Z1 也不用强迫 Z2，路况会决定
- TSS 贡献 ~30-35 TSS/hr，对 race-week fatigue 影响极小
- 真正要踩准的是**workout intervals**（330W / 450W 这些），commute 随便

**违反此规则的写法**（应避免）：
- ❌ "commute out 严格 Z1 (130-160W)"
- ❌ "commute back 必须 Z2 (180-220W) 多积 CTL"
- ✅ "commute 随便踩，AP 自然 150-180W"

## ICU ZWO 推送陷阱（HARD RULE 2026-05-09）

**已知 ICU 行为**：所有通过 `events/bulk` 推送的 ZWO workout 会被 ICU 自动在最开头加一个 **60min Z1 phantom warmup**（"1power_zone" 内部 notation），无视我送的 ZWO 是否含 explicit `<Warmup>` 元素。

**含义**：
- 我送的 workout_text 总时长 = X
- ICU 实际显示 = X + 60min phantom

**Workaround**：在 workout_text 设计时**预留 60min phantom 作为 commute 起始段**：
- 25km commute（60min）→ 完全靠 phantom，workout_text 里**不要**写 commute out
- 30km commute（70min）→ phantom 60min + workout_text 里写 10min Z1 = 70min
- 35km+ commute → phantom + 实际差额

**workout_text 第一行约定**：
- 25km 起：`- 5m Z1 base 暖身 (ICU 自动加 60min Z1 = commute out)`
- 30km 起：`- 10m Z1 commute 末段 (ICU 自动加 60min)`
- trainer / 本地：随意写，phantom 仍会出现（trainer 的 phantom 算 warmup）

**TSS 影响**：phantom 60min Z1 ≈ +25-30 TSS（按 ICU 算法）。考虑总 TSS 时知晓。

## 室内骑行台执行限制（HARD RULE 2026-05-09 / **撤回并修订 2026-05-26**）

### 旧版规则 (撤回)
~~仅这 3 类 session 可上 trainer~~
~~禁止 trainer >100% FTP / OU / Tabata / Opener~~

**为什么撤回**: 这条规则是 5/9 当时用户"路骑优先"偏好被硬编码成 HARD RULE, **没有生物学根据**。trainer 可以做任何强度的工作, 只是 race-specificity 上不如 outdoor。用户 2026-05-26 当面 push 这条 "破规定" 正确。

### 修订后规则

**Outdoor 优先 race-specific work**, 因为:
- 真实坡度 / wind / draft 模拟 race-day 环境
- heat exposure 自然累积
- race-craft 神经印记 (变速 / 摇车 / 视觉 cue / 集团节奏读取)

**Trainer 何时可用 (任何强度)**:
- 户外不可行 (雨 / 极热 / 极冷 / 路况 / 时间窗)
- 精确 wattage 需求 (FTP test / 严格分段 ss / 短间歇精度)
- race week 神经锁定 short session
- VO2max 间歇 (短时高强度, 户外难无中断完成)
- Smart trainer 反应迟滞 ~0.5-1s 短时 sprint 仍可做

**Trainer 真实限制 (生物学约束, 不是偏好)**:
- 散热差 (无 wind cooling) → core temp 上升快, 长时高强度**必须风扇满载 + 室内 ≤25°C** 否则功率打折
- draft 缺失 → 不练 race-craft / 集团节奏读取
- 60min 以上单调度 → 心理 fatigue, mental drift, 功率 sustainability 折扣

**Race-specific 训练优先级**:
1. Outdoor 爬坡 (race-specific 最佳)
2. Outdoor 本地平路 (race-specific 中)
3. Trainer 任何强度 (race-specific 最差但 OK)
4. 雨天 / 路况差 / 时间紧 → trainer 不需要回避任何强度

## 4+2 (车+骑) 经济性规则（HARD RULE）

**4+2 决策**：
- ✅ 优势：减少热身时间，提高做功组训练时间效率
- ❌ 成本：1h 单程 + 油费 + 路费

**仅这种情况值得 4+2**：
- 单日训练 TSS ≥ 200（大负荷训练日）
- 课表性质需要特定地形（如长爬、特殊坡度组合）
- 时间宝贵但需要高强度

**race week / 减量周 / 平日训练** → 优先 Mountain 1 / 2 + bike out，不 4+2

## 路骑 commute TSS 估算（HARD RULE）

每个 plan 的 TSS 估算必须区分**workout TSS** vs **total ride TSS**：

- 25km bike out @ Z2 ≈ 60min → +40-45 TSS
- 30km bike out @ Z2 ≈ 75min → +50-55 TSS
- bike back 类似（如果还有 Z2 配速）
- 总 commute add-on：80-110 TSS（25km 来回）/ 100-130 TSS（30km 来回）

**plan 标 target_tss 时**：
- 工作组段 TSS（workout structure）
- + commute TSS（bike out + back）
- = 实际总 ride TSS（用户实际承受 + ICU 上传后真值）

## 路骑功率匹配规则（HARD RULE 2026-05-09）

**真理**：W' 重建只看 P_recovery vs CP 的差值时间积分，**不看是 50W 还是 150W**。
- Skiba τ @ 150W = 28s
- Skiba τ @ 50W = 22s
- Skiba τ @ 0W (滑行) = 21s

5min 任何低于 CP 的 P_recovery 都能 99% 重建 W'。

**因此**：
- ✅ 间歇恢复段 = 下坡滑行 / 红绿灯 / 任何低于 CP 的功率，无所谓精确瓦数
- ✅ 工作段功率 ≥ 目标 90% × 时长 ≥ 目标 90% = 算达标
- ✅ ICU compliance 80%+ = session 成功

**plan 设计时的隐含假设**：
- workout_text 里的 `5m Z1 组间` 表示"约 5 分钟的恢复"，不是必须 150W 平均
- workout_text 里的 `90s 110% 稳态` 是工作段，必须按目标达成

**地形匹配建议**（每次 plan 设计时附带）：
- 短 burst 间歇 (90s + 30s) → 6-8min 中坡 × N 趟
- 长 sustained 间歇 (12-15min) → 15-20min 长坡 × N 趟
- 30/30 短爆 → 上骑行台 / 平路
- Z2 长拉 → 任何缓坡 / 平路

## 比赛功率推算 HARD RULE 2026-05-09

**禁用**: 用 60min PB (=274W) 作为 TTE 上限或 race 决战段配速参考。
**原因**: 60min PB 不是 all-out 测试 (用户自述), 严重低估真实 60min 能力。

**正确做法**: 推算 race 长 sustained 段时用：
- **真实 CP60 ~290-300W** (用户自评 + ECP 模型 312W + 多源共识)
- 5/10/20min PBs (387/342/313W) 都是 all-out, 可信
- 33min sustainable: ~88-95% FTP (264-285W)
- 50min sustainable: ~87-92% FTP (261-276W)
- 60min sustainable: ~88-93% FTP (264-279W)

**Race NP 高于 sustained 估算**: 实战有大量 burst (25-30s @ 130-165%) 攻击/防守, NP 比纯稳态高 5-10%. workout_text 必须含 burst pattern 才接近真实 NP.

## 历史负荷上限（基于近 12 周 wellness ctlLoad 真值，HARD RULE）

**数据源契约**: 周 TSS = `wellness_history.json` 每日 `atlLoad`/`ctlLoad` 求和 — **不是**活动表 `icu_training_load` 求和（后者会漏手动登记/力量/无 GPS 训练，可低估 100-200 TSS/周）。

| 维度 | 值 | 触发后果 |
|---|---|---|
| 单日峰值 | **~300 TSS** | W14 4/1 实测 300，W18 五一 284-251 反复 |
| 单周峰值 | **1100-1200 TSS** (1-2 次/季) | 必须接 1 周大幅减量（W18 1154 → W19 485 实证） |
| 持续高负荷上限 | **900-1000 TSS/周 × 3-4 周** | W14/W15 连续 994/920 + W18 验证 |
| 4 周块上限 | **3400-3700 TSS** (3 高 + 1 减) | 月均 ~850/周 |
| 月均上限 | **~3500 TSS/月** | 近 10 周月均 3201 已接近 |
| **硬天花板**：单周 >1200 TSS | — | 当前 CTL 105 撑不住，必须先把 CTL 抬到 110+ |

历史规律：高负荷后强制恢复（W15 920 → W16 468, W18 1154 → W19 485）= 自适应反馈，不是失败，是身体保护机制。

近 10 周（W10-W19）频次分布：
- 高负荷 (≥900): 3 周（W14 994 / W15 920 / W18 1154）
- 普通 (600-899): 3 周
- 减量 (400-599): 3 周
- 低/恢复 (<400): 1 周

= **教科书 3:3:3:1 周期化**，自适应良好。

**违规反例**：
- ❌ "近 4 周均 TSS 606，你常规周是 600" — 4 周均值是高/普通/低混合，**不是常规周基线**
- ❌ "150 TSS 是大负荷训练" — 150 是中等，可背靠背
- ❌ "race week 应深 taper 到 250 TSS" — race week + multi-race tail 应在 500-650（减量上限/普通下限）

**合规推断**：
- ✅ Race week 含比赛 + multi-race tail：500-650 TSS
- ✅ 单 A 赛深 taper（无后续比赛）：400-500 TSS
- ✅ 季中维持周（无比赛）：600-800 TSS
- ✅ 容量积累周：900+ TSS

历史对照（2026 4-5 月数据样本）：
- W15 (4/6-12): 493 TSS — 维持/recovery
- W16 (4/13-19): 265 TSS — 病/伤特殊周
- W17 (4/20-26): 523 TSS — 含 4/25 race week
- W18 (4/27-5/3): 1154 TSS — 五一假期高负荷
- W19 (5/4-10): 485 TSS — KOM rehearsal week

## 功率曲线数据质量（HARD RULE，2026-05-09 锁定 + 修订）

| 时长 slot | 数据质量 | 可用作什么 |
|---|---|---|
| 5s — 20min | ✅ **at-max 真测试** | CP/W' 模型锚点、类型分类、能力上限 |
| 55min | ⚠️ **subjective ~90% RPE** (i133847457 3/22) | **不可数学反推**（RPE 体感污染严重）；仅作"曾经能 hold 281W × 55min"的存在性证明 |
| 30min / 40min / 60min / 90min / 2h / 3h / 4h | ❌ **训练 ride 切片，sub-max** | **禁止**用于计算 CP、判定 long-duration 形态 |
| 用户自报 CP60 = 290W | 📌 **当前工作锚点**（自我评估，比模型外推可信） | 训练区间、配速规划、比赛战术 |

**违规反例**：
- ❌ "你 60min 只有 4.57 W/kg = Cat 2/3 弱" — 60min 是 sub-max
- ❌ "5min/60min = 1.39 验证 Puncheur" — 分母 sub-max
- ❌ "55min @ 90% effort → CP55 = 281/0.9 = 312W" — **RPE 不能这样数学反推**（情绪/温度/疲劳全污染）
- ❌ "ECP CP=312W、FFT=319W、反推 312W → 三方共识" — **假共识**，三个都从 ≤8.5min 外推
- ❌ "FTP 300W 保守 5%" — 基于上面的假共识，撤回

**合规推断**：
- ✅ "5min/20min = 1.24" — 两端都 at-max
- ✅ "Sprinter 世界级（5s/1min）" — 4/9 全力 sprint ride
- ✅ "5min/60min = 1.33（用用户 290W 锚点）" — 分子 at-max，分母用用户自评
- ✅ "60min 4.75 W/kg = Cat 2，长爬略弱"（用 290W 锚点 + 用户自评）

**真实 CP60 仍然未知**。唯一靠谱的锁定方式是赛后做正式 CP60 全力测试。在那之前，用 290W 作为工作值，不要用任何"乐观估计"取代。

## W'/CP 锚点（HARD RULE，2026-05-09 锁定，9 源核算 + 5/8 KOM 实测验证）

**双层池模型**：

| 池 | 容量 | 何时使用 |
|---|---|---|
| 真 W' (rapidly accessible) | **22-25 kJ** | 任何 hard 努力都从这里抽 |
| AWC (Anaerobic Work Capacity, 应急) | +10-12 kJ | 仅极限努力开启（race-day max / KOM 攻击） |
| **总池上限** | **35-36 kJ** | 5/8 KOM 实测净放电 35.4 kJ 锁定 |

**CP = 300W**（5/8 KOM 反推完美匹配，与 FTP set 一致）

**9 源 W' 估计 spread 12-42 kJ，不是计算错误，是 2-参数模型局限**：
- 短锚 (1+20min): 高 CP 低 W' (15 kJ)
- 中锚 (3+20min): 平衡 (21 kJ)
- 长锚 (10+20min): 低 CP 高 W' (34 kJ)
- ICU ECP / Wellness sportInfo: 25 kJ ← 多源共识
- 5/8 KOM 实战净放电: 35 kJ ← 黄金标准（含 AWC）

**这告诉我们**：你的"工作 W'" ≈ 25 kJ，"应急总池" ≈ 35 kJ，差距 10 kJ 是 AWC 应急层。

## 高强度 session 设计 HARD RULE（修订版）

所有 ≥110% FTP burst 间歇 session 设计前必做：

```
W'_per_cycle = (P_steady - CP) × t_steady + (P_burst - CP) × t_burst
W'_per_set = cycles_per_set × W'_per_cycle
```

**校核三档**：

| 用途 | W' 上限 | 校核 |
|---|---|---|
| 训练 session（保守，不开 AWC） | **22 kJ/set** | 留缓冲给 reload 不完全 |
| race-day max（开 AWC 一次） | **30 kJ** | 真 W' + 部分 AWC |
| 绝对天花板（不可超） | **36 kJ** | 5/8 实测上限 |

多 set 校核（80% 重建率，5min Z1 between）：
- Set N 进入时 W' = (Set N-1 剩余 + 80% × (22 - 剩余))
- 任何 set 出现负值 → 借 AWC，必须警示

**违规反例**：
- ❌ v6 原版 5/10：4 set × 4 cycles × 500W = 35 kJ/set 累积要 140 kJ（理论上不可能）
- ❌ v6.1 5/10：3 set × 3 cycles × 450W = 21.6 kJ/set 看起来 OK，但累积到 set 3 借 AWC 12 kJ（达 5/8 KOM 极限）

**合规设计**：
- ✅ 3 set × 2 cycles × 450W = 14.4 kJ/set（远在 22 内）
- ✅ 3 set × 3 cycles × 400W = 17.1 kJ/set（在 22 内 + 能完成）

## 反 sycophancy 个案：3 种变种全部识别

### 变种 1：顺着用户说（基础）
- 用户 push back → 立刻改答案，不重读数据

### 变种 2：用乐观估计给台阶下（2026-05-09 第一次教训）
- 被纠正"30+ min sub-max"后，用 281/0.9 的脆弱算式造"FTP 偏保守 5%"的乐观结论
- 让用户感觉"也许我其实更强"但无数据基础

### 变种 3：用"你在变好"叙事包装数据（2026-05-09 第二次教训）
- 把 4/25 W' 留 26% 缓冲解读为"节奏好/进步 13 名"
- 实际两场 IF 都 1.04-1.05、生理输出一样
- W' 差异和名次差异都受多因素影响（集团规模 / 课程长度），不能归单一变量
- 编"显著进步"因果链 = 让用户感觉良好但 distort 真相

**统一规则**：
1. 契约不允许的就是不允许，不要绕道
2. 多因素结果不能归单变量
3. 实测出什么就说什么，不为情感价值修辞
4. 用户的"打脸"是机会不是威胁，每次都重读数据再答

## 沟通规则：禁用内部代号 + 大白话原则 (HARD RULE，2026-05-09 锁定，2026-05-10 v2 加强)

### 历史
- v1 (5/9): 禁用临时代号（S1/S2/Phase X）
- v2 (5/10) 加强: 5/10 教练在热适应分析时仍堆"代谢端 dose 没拿满 / lactate clearance / W' 9kJ / HR Z5 / IF / TSS"等术语，用户反应"听不懂，重新解释"——v1 不够严格

### v2 规则（教练面向用户输出适用）

#### 黑名单（不能裸写，**首次出现必须用中文+一句解释**）
| 术语 | 大白话替代 |
|---|---|
| W' / W prime | 爆发力池 / 无氧储备池（"超过 1 小时极限那部分劲儿要从这里掏"） |
| FTP | 1 小时极限功率（你的是 300W） |
| CP / critical power | 接近 FTP 的"理论可无限维持功率" |
| VO2max | 最大吸氧能力 / 最大有氧引擎转速 |
| Lactate clearance | 清乳酸能力（"踩着喘但不彻底炸"的耐受） |
| IF (intensity factor) | 训练强度系数（与 1 小时极限的比值） |
| TSS | 训练负荷分（一次训练对身体的累积压力） |
| HR Z1-Z5 | 心率第 1-5 区（首次必须说"第 5 区是接近最大心率的最炸区间"等） |
| NP / weighted power | 加权平均功率（考虑爆发的真实平均） |
| Decoupling | 心率漂移（同样功率下后段心率比前段高多少 %） |
| ATL/CTL/TSB | 短期/长期/状态平衡（疲劳/训练量/今天好不好状态的指标） |
| Polarization Index | 训练极化指数（高低强度分布的"两极化"程度） |
| MCT | 乳酸搬运分子（清乳酸用的） |
| Race-specificity | 比赛专项性（"这课练的是不是比赛真要用的能力"） |
| dose | 训练剂量 / 训练量 |
| 代谢端 / 神经端 / CV 系统 / 散热端 | 能量代谢这块 / 肌肉爆发这块 / 心肺血管这块 / 出汗散热这块 |

#### 沟通原则
1. **每次解释一个判断，先讲"我看到什么数据"，再讲"这数据说明什么"，最后讲"所以下次怎么改"**——不堆术语链
2. **打比方比堆专业词更有效**：举铁 / 跑步 / 储水池 / 油箱 等日常场景类比
3. **首次出现专业词强制注释**——一段对话里同一个词第二次出现可以裸写
4. **vault 文件可以保留专业术语**（机器可读 + 自己复盘用），但**对话输出必须翻译**

#### 自检
回答前问自己：**如果我现在在咖啡馆当面跟用户说，他能不能不查字典就听懂？** 不能 → 重写。

### v1 的成功项保留
- 给比赛段命名：起跑爆点段 / 稳态主段 / 中段拉锯 / 末段冲刺
- 给课表命名：起跑课 / 稳态加速课 / 疲劳冲刺课 / 30 秒爆破课 / 全程模拟课
- 一行说明 WHY 这个课练什么实战场景

### 5/10 违规案例（学习用）
> "W' 只用 9kJ + HR Z5=0 + 主观刚好用完 = 代谢端 lactate clearance dose 没拿满"

**翻译为大白话**：
> "你今天爆发力池只用了 36%（25 千焦的池子用了 9 千焦），心率虽然冲到 186 但没真正炸到最炸那一档，可是你自己觉得'刚好用完'——这意思是身体核心还能再上，但被热挡住了，所以'清乳酸'这个能力今天没练透。"

**注：上述判断本身后来被发现是错的，详见下条 hard rule。**

---

## 课型 dose 评估标准 (HARD RULE，2026-05-10 锁定)

### 触发
- 5/10 OU 评分时教练用了 W' burner 课的标准（W' 烧空、HR Z5 时长）评 OU 课
- 用户 push back: "心率训练时本来就比比赛低，OU 强度也不该让心率到 Z5；W' 课表是你自己设计的，按要求踩 W' 当然只用这点"
- 教练 admit error：5/10 OU 是 A+ 完成度，不是 A

### 规则
**不同课型有不同的 dose 评估签名，不能跨用**：

| 课型 | 该课型期望签名 | 不应该有的信号 |
|---|---|---|
| **OU 1/1 @ 110/90%** | 心率第 4 区为主，第 5 区少；W' 池子部分消耗（30-50%）；4 set 不衰减 | 心率到第 5 区（强度太高，变 VO2max 课）；W' 烧空（变 W' burner，4 set 完不成） |
| **VO2max 间歇** (4×4min @ 115-120%) | 心率第 5 区为主；末段衰减 5-15% | 心率不进第 5 区（强度不足） |
| **W' burner** (30/30 @ 130%) | W' 池子接近烧空（70-90%）；4-5 个循环必衰减 | W' 完整保留（强度不够） |
| **race-rhythm 模拟** (3×3×450W) | 短冲达目标功率；组间恢复完整；W' 烧 60-80% | 功率掉到 400W 以下（疲劳过早） |
| **threshold/SST** (5×8min @ 90-95%) | HR 漂移 ≥5bpm；功率维持 | W' 显著消耗（强度太高） |

### 评估时检查
1. **课型 → 期望签名**先确认，再看数据
2. **不要用 A 课的优秀签名当 B 课的优秀标准**
3. **完成 = 按设计目标功率/时长执行 + 期望签名出现 + 主观体感"用完"**——这就是 A+
4. **"还有余量"≠ 没拿满**：要看课型设计本意。OU 设计就是不烧空，"余量"是设计内的

### 5/10 OU 重评分
- 4 set × 5 cycles × 1min @ 330W 全部命中（avg 329.5W）
- HR 第 4 区 23 分钟（OU 期望签名 ✓）
- W' 用 36%（OU 期望签名 ✓——不烧空）
- 主观"刚好用完"
- = **A+ 完成度，race-specific lactate clearance 训练目标完整交付**

### 检测
- 教练每次评分前先问"这是什么课型？该看什么签名？"
- 看到"心率没到 Z5""W' 没烧空"先问"这个课型本来要这些吗？"——不要默认是 bug

---

## 高强度课 vs 热适应课分时段架构 (HARD RULE，2026-05-10 锁定，2026-05-10 v2 重写)

### 历史
- v1（已撤回）: 高温日 IF 收紧 + 避高温窗 — 把热当纯负面因子，**错**
- 用户 push back: 5月赛季前需要主动训练热适应不能避热
- v2（当前）: 区分高强度课和热适应课，**分时段架构**

### 核心原理
两类训练目标对环境温度的偏好相反：

| 训练目标 | 偏好温度 | 经典 protocol |
|---|---|---|
| **热适应**（血浆扩张 + 出汗效率 + 心率漂移降低） | **高温暴露** | Z2-Z3 60-90min, IF 0.65-0.75, 主动核心温度 ≥38.5°C, 14天累积刺激 |
| **代谢/神经端**（lactate clearance / VO2max / W' burst / FTP） | **凉时段** | 高强度课目标功率 dose，需要散热不限速 |

### 规则
**高强度课和热适应课分时段执行**：

- **高强度课**（OU / 30/30 / race-rhythm / 起跑课 / 全程模拟课 / 任何 IF ≥0.85 或含 above-FTP intervals 的课）→ **放凉时段** 6:30-9:30 / 17:30-19:30
- **热适应课**（专属，目标是热适应不是功率）→ **放高温窗** 11:00-14:00 / Z2-Z3 60-90min / 不补冰水 / 故意暴露
- **混合不允许**：不要把高强度课放高温窗"顺便练热适应"——双折扣（高强度因热打折、热适应因强度截短训练时长）

### 5月赛季前热适应 protocol
- 频次: 周 2-3 次专属热适应课
- 形式: 正午 Z2 60-90min 室外 / commute 中午时段加长 / trainer 室内不开空调
- 累积刺激: 14 天连续才能拿到血浆扩张 5-12% 的完整收益（Périard 2015）
- 检测: 同等 IF 下 HR drift 减少 ≥5bpm = 热适应见效

### 5/10 教训
- OU 在高温窗做"刚好用完" = 代谢端 dose 没拿满（W' 9/25kJ, HR Z5=0），race-specific lactate clearance 训练效益打折
- 如果当时凉时段做，大概率扛 112/88 或第 5 组
- 但当时"既要 OU 又要练热"是混合，是 v1 rule 错误的根源

### 检测红旗
- 高强度课主观"刚好用完"+ 物理数据"还有大量余量"（W'<60% / HR Z5<10%）→ 热在限速代谢端
- 该课的 race-specific 训练目标（如 lactate clearance）没拿满 dose
- 应对: 该课改凉时段，热端单独放专属课

---

## TSS 预估系统偏差 (HARD RULE，2026-05-10 锁定)

### 触发
- 5/10 计划 TSS=230，实测 TSS=167，**偏差 27.4% 高估**
- 用户指出: "你课表预计的 tss 比我实际踩的 tss 会高"
- 验证: 偏差是系统性的，不是单次

### 校准系数
**实测 TSS = 计划 TSS × 0.73**（折算 27% 高估）

应用于 5/11-5/17 plan：

| 日 | 计划 TSS | 校准实测预期 |
|---|---|---|
| 5/11 30/30 | 140 | ~102 |
| 5/13 race-rhythm | 175 | ~128 |
| 5/16 opener | 55 | ~40 |
| 5/17 race | 80 | ~58 |

### 偏差来源分析（2026-05-10 数据深挖结果）

**27% 偏差拆解为两层**：

| 层 | 偏差量 | 来源 |
|---|---|---|
| 层 1: ICU 显示 TSS vs 理论计划 NP 法 | **23% 高估** | ICU 对 OU / 30/30 / interval 课打"结构加成"，系统数字虚高 |
| 层 2: 理论计划 NP 法 vs 实际执行 | 5% 低估 | 用户执行非常标准，commute idle 秒拉低 5% NP |

**5/10 实证**:
- ICU 标 TSS = 230
- 分段简单累加法 (Σ IF²×duration) = 146 TSS
- **加权平均功率法（真 NP）= 176 TSS** ← 真实身体负荷
- 实测 = 167 (距真 NP 计划只差 5%)

**段对比验证用户执行精准度**:
- Commute（140min @ 55% 计划 vs 127min @ 57% 实测）→ TSS 贡献 71 vs 69，差 3%
- 工作组（264W 计划 vs 264W 实测）→ TSS 贡献 75 vs 73，差 3%
- 用户执行平均误差 ≤ 5% → 不需要"为偏差预留余量"

### 关键区分: TSS 偏差 ≠ W' 池消耗偏差
- **TSS 看的是平均值（NP/FTP），受 commute / recovery 段拖累**
- **W' 池消耗看的是 over-FTP 累积（峰值段时长 × 超 CP 部分）**
- 二者独立！高强度课的 over 段功率命中率高 → W' 消耗按设计走，不受 TSS 偏差影响

### 数据证据
5/10 OU: TSS 167 (低于估 27%) + W' 消耗 9 kJ (高于 OU 设计预期 5-7 kJ 30-80%)——双向偏离同时存在，证明 TSS 和 W' 是独立维度。

### 应用规则
1. 后续 plan 给用户展示时，**TSS 数字必须给两个**: 计划 TSS + 校准实测预期 (× 0.73)
2. ATL 曲线分析必须用校准后数字
3. **W' 池消耗预测不应用 TSS 校准系数**——按课型设计参数算（OU 5-7 kJ / 30/30 17-20 kJ / race-rhythm 12-15 kJ / threshold 3-5 kJ）
4. race day 池子状态预测必须基于 W' 消耗 + 回血时间，不基于 TSS 累积

---

## HRV 闸门覆盖规则 (HARD RULE，2026-05-10 锁定)

### 触发
- 5/10 早 HRV=64，闸门"60-64 → Z1 60min"应降量
- 用户主观"身体可以"覆盖闸门 → 完整 OU 4 set，结果 A 级
- 但常态化覆盖会架空闸门作为过载预警的功能

### 规则
1. **每月最多 2 次主观覆盖 HRV 闸门**
2. 每次覆盖事后必须在 session log 标注：主观依据 + 结果是否过载
3. 连续 14 天出现覆盖 → 闸门规则失效，必须停止覆盖到 HRV 回 baseline ≥4 天
4. 覆盖只允许边缘场景（HRV 在闸门下沿 1-2 单位）；**不可覆盖 HRV <60 红色闸门**

### 主观依据要求
- 睡眠好 / 腿感轻 / 心情好 / 食欲正常 4 项至少 3 项 yes
- 单纯"我觉得行"不够 → 当次必须展开 4 项依据落 session log

### 当前 HRV baseline (5/4-5/8: 66/71/65/70/65)
- mean ≈ 67.4 → baseline 闸门 ≈ 64.5
- 5/10 HRV=64 在闸门下沿 0.5 单位，属"边缘可覆盖"区间

---

## 爬坡赛 race-class ceiling (HARD RULE，2026-05-25 锁定)

### 用户自述定位
> "我所有的爬坡赛都没有能力带领第一集团控速，我的实力在第一集团的最后面（一般 5-10 名，锁定最前面的名次，我跟住第一集团就需要 allout，我能苟活到第一集团最后就是胜利）。"

### 含义
- **5 月 race-class ceiling = 5-10 名**（架构性，不是发挥问题）
- **苟住第一集团 = allout**：没有 move-up 能力，没有主动驱动配速能力
- **唯一战术武器 = 末段 counter 或 sprint**（不是 move-up，不是 mid-race attack）
- 爬坡起点 + 缓坡 + 集团赛 draft 收益巨大 → 前组极难被打散 → 体能 ceiling 直接锁名次区间

### 5/23 平王 stream 实测验证
- climb b5 AP 334W（全场最高 5min）= **不是主动驱动**，是集团 sprint 集结加速的死扛跟上代价
- HR 末段 199-200 = max，cad 99 不掉 = 神经肌肉端没崩，是 W' 池见底
- EF 反向 decoupling -5.8% = aerobic ceiling 已到，不是富余信号

### 教练禁项
- ❌ 建议"climb 倒数 1-2km move-up 到前 3 位" — 用户根本做不到
- ❌ 用"主动驱动 / 控速 / 配速 leader" 任何包含主动权的措辞
- ❌ 把"末段 AP 上升"解读为"还有富余/可以更激进"——可能只是 sprint 集结加速的代价
- ❌ 解读"前组对手减速 = 机会" — 在 climb-start 缓坡集团赛里减速 = sprint 集结的 bunching，不是疲劳信号；用户从集团尾部读不到前组真实状态（结构性盲区）

### counter 距离硬数字 (climb-start 缓坡集团赛 only)
- W_bal=0 状态下 AWC 池上限 = 10-12 kJ
- 全开 sprint ~560W 透支速率 = 270J/s
- 12-15s 全开后开始衰减
- → **counter 距离上限 = 200m**（看到终点牌再开）
- 距离 ≥ 300m 不主动起手，等到 200m 牌或同等距离再开
- **不解读"前面减速"**，只看距离

### 类似画像选手的真实 ceiling 解锁路径
- AWC 池容量训练（10→12 kJ）= 多 15-20% counter 弹药
- race-day pacing 改善 ROI 极低（结构已最优）
- → race 块结束后单独 plan AWC capacity 块（5/31 race 之后讨论）

### Race-class 适用范围
- 5/17 千峡湖 + 5/23 平王 = climb-start 缓坡集团赛
- 5/24 ≠ 同性质（用户确认）→ counter 200m 数字不适用，5/24 单独建模
- 5/31 太子尖性质待 GPX/赛况确认后决定

---

## Trainer power gap 观察日志 (N=1, 不 lock rule, 2026-05-26)

### 实测案例
- 5/26 trainer 20min @ 285W → RPE 10/10 (Set 1 完成 67% 提前 bail)
- 5/24 武义 race C1 路骑 7:20 @ 318W → RPE 6
- Δ ≈ -33W at similar perception

### Confounders (用户 push 出的)
- 今日湿度可能偏高 (室外雨天, 室内空气湿度上升)
- AC 16°C 但风扇坏, 局部散热差
- 神经端 race-week stale (TSB +26 morning) 主观 RPE 放大
- 一次性 N=1 data point 不可推 general

### 教练规则 (不基于此单点)
- 不主动给 trainer 课表降功率
- 设计 trainer 课表时仍按 路骑功率 target 设计
- 用户实测后失败 → 当次接受, 下次同条件再观察
- **累积 3+ trainer quality session** 后, 如果 -25W gap 持续 → 才考虑 lock rule

### Plan v7.1 swap 影响
今天 trainer 没完成 → race-week 总 load 不足 → swap 5/27 outdoor 加量 (自由巡山 race-specific 285 TSS) + 5/29 swap LSD + opener (240 TSS) 补足 → race-morning TSB 落 +9 sweet spot.

**元教训**: race week 用户 TSB +26 起开始 quality 课表, trainer 强度容易出问题. 未来 race week 教练应优先 outdoor 安排 quality, trainer 仅作 backup.

---

## race-day 体感两类极限信号区分（HARD RULE 2026-05-26）

5/24 武义 race C5 vs C8 km3 实测对比锁定。

### A 类 急性 W' 透支
- **体感**: 腿灼烧 / 呼吸急促 / 主观"刚刚好的边缘" / RPE 8-9 / "顶不动但还能扛"
- **关键标志**: 还能 push 接近 CP+ 的功率 (300-350W)
- **代谢**: glycolytic burn / W' 池真消耗
- **w_bal 数据**: 见底 / 透支 / 在负值附近
- **典型场景**: 单次 4-7 分钟陡爬末段
- **5/24 实例**: C5 末段 RPE 8-9 顶住 (AP 327W / HR 185 / W_bal -807J)
- **race-day 决策**: 顶过去 = race 主线; 若已知后面还有重坡，主动降到 CP 让 W' 部分回血

### B 类 累积有氧端见底
- **体感**: 全身重 / 心肺很喘 / 腿没力气 / 主观"什么都做不出来" / **低功率也难受**
- **关键标志**: 即使低于 CP 的功率也维持不住
- **代谢**: aerobic system + 糖原累积耗损 / 不是 W' 池问题
- **w_bal 数据**: 可能显示充沛（**这是模型盲区**）
- **典型场景**: race 70-90 分钟后的末段爬坡 / multi-climb 后半段
- **5/24 实例**: C8 km3 体感"腿没力气心肺喘" (AP 281W = CP / HR 185 / W_bal 还有 8 kJ)
- **race-day 决策**: 不可"补"回去 → 只能 self-pace 守住集团 / 放弃响应攻击 / 准备末段无法 sprint

### 教练读 w_bal 数字不能脱离上下文
- 仅看 w_bal 数值 = 错（看不到 B 类）
- 必须叠加: race 累计时长 / 累计爬坡时长 / 用户 RPE 描述类别
- 用户描述"还能顶但难受" = A 类 / w_bal 数字可信
- 用户描述"腿没力气 + 低功率也难受" = B 类 / w_bal 数字误导

---

## 池子分析方法学：禁用 icu_pm_cp 作为生理 CP（HARD RULE 2026-05-26）

### 问题
ICU 活动 summary 的 `icu_pm_cp` / `icu_pm_w_prime` 是 **per-activity 的 Power Manager 估值**：
- 用当次 ride 的 PD 曲线 + 近期历史拟合 ECP
- 每场 race 都漂浮（5/17=290 / 5/23=291 / 5/24=281）
- 漂浮源于算法 lag + 当次峰值数据形态，**不是当天生理 CP 真在 race 间波动 10W**
- 同源问题：`eftp`（estimated FTP）也是单次 ride 反推

### 教练分析规则
1. **池子分析始终用 vault 锁定的 CP=300W**（5/8 KOM 反推 + FTP matched + 多场 race 验证）
2. **每场 race 计算 over-CP integral 用 300W**，不用 activity.icu_pm_cp
3. **不引用 `icu_pm_cp` / `icu_pm_w_prime` 作为锚点**——这两个字段只能作为"ICU 算法当前对这次活动的内部估值"参考
4. 若需要 race-day 漂浮信号 → 看活动 NP / IF / HR drift / 用户 RPE，不看 icu_pm_cp

### 实测案例（5/26 session 校准）
用 CP=300W 重算 3 场 race 单次最深透支：
- 5/17: 982s @ avg 316W → (316-300)×982 = **15.7 kJ over CP**
- 5/23: 1234s @ avg 312W → (312-300)×1234 = **14.8 kJ over CP**
- 5/24 C1: 339s @ avg 344W → (344-300)×339 = **14.9 kJ over CP**

加上 Skiba 模型连续 sub-CP recovery 动态 → 真实池子峰值消耗 14-16 kJ
= **3 场 race 都消耗的是真 W' (22-25 kJ 池)**，没真触 AWC 储备区

---

## race-day TSB 计算 (HARD RULE 2026-05-26)

### 问题
ICU wellness_history.json 每日 `atl` / `ctl` / `tsb` 字段是 **EOD 值**（包含当日所有活动 load）。如果用 race-day 当日 EOD 算"race 时 TSB"，会把 race 本身的 load 算进去 → 严重低估实际 race-morning TSB。

### 5/23 实证
- 5/22 EOD: atl=77.5, ctl=97.0 → race-morning TSB = ctl - atl = **+19.5** （正确）
- 5/23 EOD: atl=86.1, ctl=98.1 → +12.0 （错误：含 5/23 race 后 load 142 TSS 已部分计入 atl）
- 5/23 race-morning 真值 ≥ +19.5（用户主观"too fresh, HR too high"= 已踩 +15 stale 红线）

### 教练规则
1. race-morning TSB 永远用**前一日 EOD 的 atl/ctl**反推（`pre_race_TSB = prev_day.ctl - prev_day.atl`）
2. 不引用 race-day 当日 EOD atl/ctl/tsb（含当日 load，污染）
3. 不引用 activity.icu_pm_cp / icu_pm_w_prime（per-activity ECP 估值，算法 lag）
4. 写训练块 / race 前评估时同样规则

### 验证 sync 完整性步骤
每次教练 session 用 TSB 前必须验证 sync 完整:
- `wellness.atlLoad[date] === sum(activity.icu_training_load for date)` 否则 sync 不完整
- 5/17-5/24 验证通过 (delta 全部 = 0)

---

## 车队战术 3 阶段模型 + 7 类爬坡 signature (HARD RULE 2026-05-26)

### 5/24 武义实证锚定 (车队 4 人，1/3/5/7 名包揽)

#### 3 阶段战术模型

```
Phase A — 磨损攻击 (wear-down)
  - N 个队友轮流 attack 竞争对手
  - 每次 attack: 1 人冲 → 等竞争对手响应 → 下一人接力
  - 持续直到竞争对手"没力气回应"
  - 信号: 多坡持续 high power + 高 surge 密度 + 多次接力
  - 5/24 实例: C2-C4 期间, 多个短中爬坡的累积消耗

Phase B — 单飞突围
  - 当且仅当竞争对手疲软到不响应时, 队伍最强 1 人 attack
  - sustained 高功率突围 (非短 burst)
  - 信号: 单段 ≥3min @ AP ≥330W + macro CV <0.10 + 末尾一人单脱
  - 5/24 实例: C4 (4:15 @ 7.5% @ AP 338W @ macro CV 0.08, 冠军末尾单脱)

Phase C — 控场保护
  - 剩下 N-1 人在第一集团**不主动追**
  - 故意降配速, 让单飞员拉开
  - 追单飞员的责任落在其他队的散兵
  - 信号: surge 密度 <0.5/min, heavy surge ≈0, macroCV <0.10
  - 5/24 实例: C6/C7 (surge 0.3-0.5/min, 用户休息窗)
```

#### 7 类爬坡 signature 识别表

| 类型 | Surge密度 | Heavy ≥500W | %overCP | HR Z5 | macroCV | 谁在 attack | 用户响应 |
|---|---|---|---|---|---|---|---|
| ① 抢位段 | 1.5+/min | 多 | 中 50-60% | 低 30% | 中 0.18 | 各队抢前位 | 蹭 draft, 后段 |
| ② 短坡试探 | 1+/min | 0-1 | 中 50% | 0-30% | 中 | 团队看谁喘 | 不 over-respond |
| ③ Phase A 长坡 + Phase B 单飞 | 1-1.5/min | 1 (= solo) | **78%+** | 中高 59% | **<0.10** | 团队 sustained rotation 末尾单飞 | **池子 all-in 顶 4-5min**, 顶住才进最终前组 |
| ④ Phase B 后 chase phase | 1+/min | 中 | 中 60% | 70% | 0.13 | 散兵 chase 单飞员 | 见 ⑦ |
| ⑤ Phase C 控场 | **<0.5/min** | 0 | 中低 35-50% | 中 43% | **<0.10** | 团队控场保护单飞 | **休息 / 补给 / 重置池子** |
| ⑥ 终爬重组 | 1+/min | 多 | 50% | 高 **85%+** | 0.10 | 各队 sprint 重组 | 守集团 + 不响应 attack |
| **⑦ 防御追击坡** | **1.5+/min** | 多 | 60% | **70%** | 0.13 | 其他车队散兵 chase + 集团整体追 | **必须跟集团 (没选择不跟)** / 池子会烧到见底但被动消耗 |

#### 核心识别公式
- **Phase A→B 转折点**: %overCP ≥75% AND macroCV <0.10 AND sustained ≥3min
- **Phase C 控场窗 (你的休息机会)**: surge density <0.5/min AND macroCV <0.10 持续 ≥3min
- **防御追击坡 (类型 ⑦)**: surge density >1.5/min 在 Phase B 之后 + 集团整体跟车 → **必须跟, 不跟就掉队**

---

## 下坡 attack 隐性池子税 (HARD RULE 2026-05-26)

### 5/24 实测
7 段下坡（climb 间过渡）共 19 次 ≥400W attack，单次峰值 544-702W。

用户**不敢极限下坡过弯**（疲劳 + skill caution），被 attack 拉开 5-50m gap。

### 隐性能耗估算
- 每次 reconnect: 10-30s solo 状态（脱 draft）→ aerodynamic penalty 50-80W extra
- 7 个下坡过渡 = **~10 kJ 隐性糖原 + 神经端消耗**
- **完全在 ICU w_bal 模型盲区**（看不到 draft 损失）
- 但是真实累积疲劳的重要来源，**直接造成 race 后 30 min B 类"低功率难受"体感**

### 教练分析规则
1. multi-climb race 分析必须涵盖 climb 间下坡过渡的 surge 数据
2. 不只看 climb 段功率/池子, 还要看 transition tax
3. race 总隐性消耗 ≈ N_descents × 1-2 kJ (N = 下坡次数, 含 attack 多寡)
4. 用户体感"开局腿差 / 末段全身重 / 低功率也难受" → 可能是隐性税累积 + B 类有氧端见底, 不是显性 W' 池问题

### 训练 implication
- race-specific 训练应包含 descent recovery 段练 reconnect 加速能力（短 30s 半 max effort 模拟）
- 但更高 ROI = race-day 下坡 skill 训练（敢极限过弯 = 不掉队 = 隐性税降为 0）
- 这是 race-craft 训练不是体能训练

### 含义
- 此前用 `icu_pm_cp` 算的"5/23 池子消耗 19 kJ + sprint 6.5 kJ = 接近天花板"是**方法学污染**的结论，**撤回**
- race 战术（车队赛"不响应进攻 + 集团最后面"）让用户主动节能，**不会榨干 AWC**
- AWC 容量上限只能用 5/8 KOM solo 实测（35.4 kJ 放电）作为下限锚点
- **池子修订 v1 (5/26 早版) AWC 下调到 7-10 kJ 撤回**，恢复 10-12 kJ
- 现 race 状态 ≥ 5/8 KOM 状态（lactate clearance / glycolytic 训练效益累积），35.4 kJ 是下限

## 2026-10-16 用户当前目标与可用时间

- 为2027比赛积累长期能力，无具体赛事日期；希望全面、缓慢稳定进步。
- 时间上每天能骑，但不喜欢天天训练；每周最多安排两次3.5h以上训练。
- 当前疼痛、力量训练经验与比赛类型待确认；旧赛季数值/状态不自动延用。

## 2026-10-16 本轮用户明确更新（覆盖此前不完整信息）

- 出生日期：2003-12-02；国籍：中国；截至2026-10-16没有UCI执照。用户要求长期记住，后续查资格先读，不重复询问。2027按出生年计比赛年龄24岁。
- 2026-09-24摔车，2026-10-02恢复训练；9月底低训练量为恢复期，不能用作常态容量。当前用户自报身体状况良好。
- 常态每周可10–15小时，不喜欢天天练；每周最多两次3.5小时以上。有室内骑行台，可室内外结合。
- 目标2027年6月Singapore national road race（官方具体日期与路线待公告）；另寻找从新加坡交通方便、周末、非crit、纯爬坡或丘陵筛选的大组赛。
- 近期只确认约45秒全力输出；长时滚动PB不代表极限测试。用户体感FTP约300W为2026-10-16主观反馈，实时设定仍读JSON，不永久锁数值。


## 2026-10-16 追加：历史巅峰、训练时间线与新加坡环境（用户明确确认）

- 生涯最佳爬坡与FTP核心窗口：2026-04-01至2026-06-01；用户后续确认最后巅峰延续至2026-06-09，该日全力CP5纳入基准；后续以此为已实现历史能力基准，不能将恢复期曲线当作长期上限。具体持续输出核验见[[sessions/2026-10-16-peak-baseline-and-crazies]]及其原始分析，当前数值仍从实时JSON读取。
- 六月底、七月和八月初为停训/恢复阶段，约八月开始恢复训练；与9/24摔车、10/2复训为不同事件。
- 用户自觉9/8状态优于10/6；10/14室内长骑状态不错。
- 来新加坡后室内Z2功率/心率表现较室外好；在中国阶段室内主观更难受。室内外使用同一功率计。
- 室内固定条件：空调设22°C、最大风扇；实际约26°C、RH70%。常规LSD每小时45–60g碳水、500–700mL水；这是本人实践，非对所有课型的固定营养处方。
- 每周日参加Crazies团骑；用户认为本地团骑和比赛短爆发要求突出。后续周结构应计入该日真实强度暴露。
- 10/13停止第5组的用户报告原因：高温、高湿、严重烟霾导致体感差，主动不坚持；不默认判为生理输出失败。
- 5/27第一爬坡被用户确认是最接近正式全力FTP测试的历史锚点；没有确认30–60分钟全力测试。旧生理标签不作为预测遗传天花板的证据。


## 2026-10-16 最新补充：主动筛选角色与分析协作

- Crazies通常是主动进攻筛选者，每次一般1–2次不足1分钟的burst；通常不掉队。偶尔掉队多发生在长时间轮车、拉扯后再遇加速。不能默认按被动跟车者解释。
- 6/9为最后巅峰期，用户确认该次CP5全力。核心4/1–6/1报告不包含它只是日期筛选，完整能力基准必须补回该锚点，详见[[sessions/2026-10-16-june9-peak-and-attack-role]]。
- 协作偏好：为节省教练token，复杂算法/批量数据分析可给用户可执行prompts，由同项目Claude Code完成，再由教练读取产物与整合判断；不必为小型核验增加交接。


## 2026-10-16 路线标注（用户确认）

- 57km通常主动attack；若未筛选完，60km再次attack；74km为团骑爬坡终点，有人同行时终点冲刺。
- 8/30：57km没有主动防守、计划慢追，坡顶未接上前方breakaway；下坡追赶，60km刚接上时被attack掉队。不要把57km较低输出直接归为体能退步，也不要只由这次事件诊断生理短板。
