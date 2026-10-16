# Cycling Coach Vault — INDEX

> 这个文件**每个 session 自动加载**到 Claude Code / Gemini CLI 的 context。
> **保持 < 150 行**。详细内容放到下面引用的子笔记里，按需 Read 才加载。
> 路径: `/mnt/d/Cycling/vault/`  ｜ Owner: 吴佳乐 (wjlwjl1202@gmail.com)

---

## 这是什么

这是 ICU 自行车教练的**长期叙事记忆**。和 `icu/coach_memory/` 配合用：

- `icu/coach_memory/*.json` — 每次 sync 后**重新写入**的活体数值（FTP/CTL/ATL/PB/wellness）。**不要从 vault 读这些数字**，永远从 sync 输出读。
- `vault/` 这边 — **决策、事件、对话脉络**。这些不会被 sync 覆盖。

## 路由（写进哪里？）

| 内容类型 | 写到 |
|---|---|
| 这次教练会话的完整记录 | `sessions/YYYY-MM-DD-<slug>.md` 新建 |
| FTP / CP / 训练范式调整 | `decisions.md` append（带时间戳） |
| 比赛日历变更（新增/取消/优先级改） | `races.md` 替换对应段落 |
| KOM / 段目标（活跃 + 已完成） | `kom-targets.md` 替换对应段落 |
| 长期身体特质 / 装备 / 受伤史 | `athlete.md` 仅在事实变化时更新 |
| 临时 / sync 后即弃 | **不进 vault**，留在 `coach_memory/` |

## 子笔记

- [[athlete]] — 长期定性特质（Type-II / 受伤史 / 装备 / 训练偏好）
- [[decisions]] — 教练决策日志（FTP 调整、范式转向、协议变更）
- [[races]] — 比赛日历 + 历史结果
- [[kom-targets]] — 活跃 KOM 段目标 + 已完成
- [[training-plan]] — 当前激活的训练框架（4 套核心 session + 周结构 + 战术）
- [[racemap]] — 5 月 4 场赛事详细情报（GPX 路线 + 阶段功率 + 战术 + 补给 + 难度评估）
- [[sites/mountain-3-climb]] — Mountain 3 单 climb 三段地形 (r1 陡 / r2 短陡+平路 / r3 长陡到顶)、stream 实测数据、训练适配建议（2026-05-12 锁定）
- `sessions/` — 每次教练对话归档（按日期）

## 最近 5 次 session

- 2026-10-16 — [[sessions/2026-10-16-base-training-direction]] — 最新数据同步；目标2027长期发展；基础期四骑行日候选框架，待确认赛事类型、力量经验和当前疼痛。
- 2026-06-22 — [[sessions/2026-06-22-bike-fit-posture-map-followup]] — **骑行姿态功能定义 follow-up**：59 中坐上把，60 后坐平路，61 前坐高强度爬坡，62 TT 低趴，63 下把巡航；五姿态无明显即时不适，62/63 长时间腰疼。结论维持：鞍位先不大改，61/60 功能合理，62/63 控制持续时间并优先处理腰背耐受。
- 2026-06-22 — [[sessions/2026-06-22-bike-fit-video-review]] — **骑行姿态视频肉眼 fitting**：5 段侧面 trainer 视频，鞍高未见明显错误；主问题为 hoods 姿势手臂偏锁、前端支撑偏硬；IMG_7962 极低趴伏髋角过闭，只建议短时间 aero 使用，不建议长爬或股四头疲劳日使用。
- 2026-05-26 — [[sessions/2026-05-26-5-31-taizijian-gpx-prep]] — **5/31 太子尖 race prep 第二轮锁定 (战术 + 训练块 + 补给 + 装备 + 风险)**: 训练块双峰 load 模式 (5/26 Z2 120 / **5/27 BIG 3h+2×15min @ 270W ss 210 TSS 正午** / 5/28 LIGHT commute 60-80 / 5/29 Z2 130 / 5/30 REST) → race-morning TSB 预期 +13-15 (sweet spot 边缘)。5/27 不上 FTP 多组 (5 天 absorb window 不够), ss 上限拿 race-specific 神经锁定。**Race-day 战术锁**: HC1 顶住 → HC2 km 27 决策门槛 (RPE 9 = release hard rule) → 中段 2 强制补给 reset → HC3 跟集团不主动 → 终点 200m sprint counter (hard rule)。补给 6 gels + 2 bidon = 320g carb 100min。高温装备无 aero / 浅色 / cooling protocol / HR 195 热门槛红线。预测名次 base 8-10 / upside 5-7 / downside 15-20。**用户拒绝 race-day 降档触发, 全力以赴 race style 记录** (不强制改, athlete preference)
- 2026-05-26 — [[sessions/2026-05-26-5-24-wuyi-race-analysis]]: 47.2km/+1197m, 真实是 **3 段 HC race (HC1 3km 5.6% + HC2 7km 4.8% sustained 22min + HC3 6.8km 5.4%) + 9km 中段恢复窗**, 旧 5/4 report 错框为 23km 单 TT。终点 500m = 200m @ 6-8% 短陡 + 100m 缓 + 50m 平（匹配 5/23 counter 200m hard rule + 用户 Type-II 短陡 sprint 优势）。**累积消耗预测 50-60 kJ over CP, 比 5/24 武义 +30-50%, 5 月 race block 最难**。HC2 22min sustained team rotation 是用户 5/24 C4 (4:15) 时长 5 倍, 真实可能 km 27-29 被甩。决策树锁: HC1 顶住进 first group → HC2 顶住决定 race → 中段 2 强制补给 reset → HC3 守集团 → 终点 200m sprint。等用户确认 4 项 (车队 6 人构成/天气/训练块/预期目标) 后展开第二轮细化

## 当前活跃旗标

- **2026-10-16 当前入口**：目标为2027年长期备赛、暂无日期；不喜欢天天训练，最多每周两次3.5h以上。以下5月日期旗标是历史记录，不能作为当前课表或生理结论。

> 任何"未完结"或"需要关注"的事，写在这里，解决后划掉。

- ✅ **5/10 OU 完成 A+ 级** — 4 set 衰减<1%（target 330W avg 329.5W），race-specific lactate clearance 目标完整交付
- ✅ **5/11 RED 全休完成** — HRV 52→60 一夜回升 OK
- ✅ **5/12 30/30 超闸门 A+ 完成** — 36/36 reps full dose，rep avg 459W (105.5% of 435W target)，W' 池烧 71.4% 命中 burner 区间，negative split Q1→Q4；TSS 149 单日安全（HARD RULE 200 内）；今天还多骑了一次 13min 答辩后通勤 TSS 2
- 🟢 **5/26-5/31 race week plan v7.2 已推送 ICU** (2026-05-26, 用户 push 让 v7.1 的 TSB +9 落到 athlete.md 锁定 sweet spot 0~+5):
  - 5/26 Tue 13:00: Indoor TTE Race Mirror ✗ trainer Set 1 67% RPE 10 bail, 实 TSS 57 vs 计划 195
  - 5/27 Wed 11:00: **自由巡山 4-5h race-specific** TSS 285 — 长坡 SS/Thresh, 小坡 Z2, 下坡荡腿
  - 5/28 Thu 11:00: **LSD 3.5h 纯 Z2** TSS 200 — AP 200-220W 全程, 不上 SS, 热适应 day-2, glycogen drain day
  - 5/29 Fri 11:00: **Light Z2 + 5× opener bursts** TSS 100 — 1h Z2 + 末段 5×30s @ 525W (Type-II prime), 1.5h short, HRV gate
  - 5/30 Sat: 完全休息 race day-1
  - 5/31 Sun 09:00: 🏁 太子尖 race TSS 200
  - **race-morning TSB ≈ +3.2** ✓ 正中 athlete.md 锁定 sweet spot 0~+5
  - Plan v7.2 logic: 4 连 ride 日 (5/26-5/29) + 1 mid-week LSD instead of mid-rest = TSB 落 sweet spot 中位, glycogen super-compensation 双日 drain pattern
- 🟢 **5/26-5/31 race week plan v7 (原版, 已被 v7.1 覆盖)** (2026-05-26, scripts/push_plan_race_week_5_31.py, 1 POST + 5 PUT 全 OK):
  - 5/26 Tue 13:00: **Indoor TTE Race Mirror 30+25** (id=112384615, NEW) TSS 195 — Set1 30min @ 285W + Z1 10min + Set2 25min @ 290W + Z2 25min @ 230W
  - 5/27 Wed 11:00: **Z2 长拉 4-5h outdoor + 热适应正午** (id=109138282) TSS 210 — AP 200-220W 自然踩, 正午热暴露
  - 5/28 Thu: **完全休息 race day-3** (id=109138283) TSS 0 — 散步 + 拉伸
  - 5/29 Fri 10:00: **Mountain 2 race-rhythm 3 climb ladder + sprint** (id=109138284) TSS 160 — Climb1 10min @ 275W / Climb2 10min @ 285W / Climb3 6min @ 295W + 30s @ 600W
  - 5/30 Sat: **完全休息 race day-1 hard rule 不开腿** (id=109138286) TSS 0 — 装备 + carb load 收尾
  - 5/31 Sun 09:00: **🏁 太子尖 race** (id=109138350) RACE_A target TSS 200 — 47.2km/+1197m, 3 段 HC, 保 first group 8-12 名
  - **race-morning TSB 预期 +10-12** (sweet spot 中位)
- 🟢 **5/11-5/17 plan v6.9 已推送 ICU** (2026-05-12 22:00, scripts/push_plan_v6.9.py, 3 PUT ops 全 OK)：5/11 ✅ / 5/12 ✅
  - 5/13 Wed 09:30: **LSD 100-120km / 1000-1500m 爬升 / 朋友陪骑** (109138215) ICU 190 — AP 170-180W 不加 set 不末段冲, 回程 30km IF ≤0.50, 爬段 34T 飞踏 ≥90rpm
  - 5/14 Thu: **REST + 散步 + 拉伸 (race day-3)** (109138212) ICU 0 — 完全不上车, 30min 散步 + 15min 拉伸重点股四头
  - 5/15 Fri 10:00: **Mountain 1 B Race-rhythm 3 set × 3×(90s @ 315W + 15s @ 480W spike)** (109138217) ICU 135 — race day-2 opener, 9 个 spike 摇车爆发, 第 1 set 作判官
  - 5/16 Sat: DELETED（race-1 休息 / 随便骑 commute）
  - 5/17 Sun: 千峡湖 race (109138221) ICU 121 — TSB 投射 +7.5 偏鲜 2 点，起跑前 15-20min 常规热身即可
- 🔴 **HARD RULE 阀门设计降级 → user 体感优先** (5/12 锁定): HRV 单日数值不再硬挂 reps/dose 上限；只在 HRV 连续 2-3 天下滑 + RHR 比 baseline 高 5+ bpm 持续 2 天 时主动 flag 异常组合
- 🟡 **5/15 第 1 set 体感判官**：3 spike 都到 480W + 稳态 315W RPE 8 → 完整 3 set；第 1 set 整体跌到 290W → 砍 2 set 不要硬撑
- 🔴 **HARD RULE 课表 single source of truth = ICU push workout_doc** (5/12 锁定)：vault 简写 ("3×3×450W") 仅做参考，引用必查 ICU push 的 workout_doc 真实 steps（之前混淆 race-rhythm = 3×3min 稳态 450W vs 真实 3 set × 6min 含 9 次 W' burst）
- 🔴 **HARD RULE 阀门设计降级 (5/12 锁定)**: HRV 单日数值不再硬挂 reps 上限（5/10 OU 与 5/12 30/30 用户两次覆盖阀门均 A 级完成，3 次决策阀门错 2 次）；reps 数由用户体感决定；阀门仅作"异常趋势信号"——HRV 连续 2-3 天下滑 **AND** RHR 比 baseline 高 5+ bpm 持续 2 天 → 教练主动 flag，但不指定 dose
- 🟡 **5/13 早 HRV 仅作信号参考**（用户体感为主决策）：若 <55 或 RHR>52 持续 → 教练 flag 但 reps/dose 用户决定
- 🟡 **5/14 race-rhythm 3×3×450W 计划**：功率 450W 死守；reps 数 用户体感裁定
- 🟡 **5/16 早 HRV / RHR**（race day 状态最强单指标）：<55 或 RHR ≥52 → 5/17 race 目标降一档守 podium edge；≥60 + RHR ≤48 → A 赛目标冲
- 🟡 **5/16 commute AP <150W 强制**（race day eve hard rule，避免污染 5/17 morning HRV/RHR）
- ⚠️ **race day TSB 投射 +10~+13**（vs vault/races.md 原目标 +0~+5）— 今日 30/30 超闸门 dose 后 5/14 race-rhythm 回到原计划，CTL 微降+ATL 衰减更快 → "鲜过头"风险；mitigation = 起跑前 20-30 分钟主动开腿激活
- 🔴 **HARD RULE 累积（持续增长）**：
  - 单日 >200 TSS **AND** TSB <-20 → 次日强制休（两条同时）
  - race-specificity 矩阵审计
  - W'/CP 物理核算（双层池 22+12=36）
  - 路骑优先
  - 周末避 Mountain 1（Mountain 2/3 OK）
  - 室内 ≤ threshold
  - 25km commute → workout_text 不写 commute out（ICU phantom 60min 顶）；30km → 写 10min
  - 场地清单：Mountain 1/2/3 + 本地平路
  - **Carb 自适应**: rest 5g/kg / 中训练 6-7 / 硬日 8-9 / race-day 8-10（不强求日常 7-8g/kg）
  - **Commute 功率不严格监控**: AP 150-180W 自然踩, race day eve < 150W 例外
- 🔴 **HARD RULE TSS 分级**：高 900+ / 普通 600-800 / 减量 400-600 / 大单日 200-300 — 见 [[athlete]] § TSS 负荷分级
- 🟡 **林峰段 KOM 元数据待补**（段名/距离/爬升/目标功率/对应赛事）— 见 [[kom-targets]]
- 🟢 **5/17 A 赛**（Climbing Race 1）8 天 — taper 起点 5/12（待 5/10 HRV 决定是否前移）
- 🟢 **类型已锁定**: Sprinter + Puncheur，长爬 Cat 2 略弱（用户自评 CP60=290W 锚点） — 见 [[athlete]] / [[decisions]] 5/9 条目
- 🟢 **FTP 300W 维持不动**（撤回"保守 5%"的乐观估计）
- 🟡 **赛后 (5/24-5/27 窗口) 安排 CP20 + CP60 双测试** — 精确锚定 CP60 是 285/290/295 哪个；**5/10 icu_rolling_ftp=316W 信号存档作为参考**（不动 ftp_set=300W）
- 🟡 **推荐 高强度课 vs 热适应课分时段（非硬规则）**：用户偏好混合负荷模拟比赛日；专属热适应课 Z2-Z3 60-90min 高温窗仍是有效附加目标但不强制——v1 "避高温" 和 v2 "硬性分时段" 都已被 5/10 数据证伪
- 🔴 **HARD RULE 课型 dose 评估标准 (5/10 锁定)**：OU/VO2max/W' burner/race-rhythm/SST 各有期望签名，不能跨用——OU "心率不到 Z5 + W' 不烧空" 是设计内的正常签名不是 bug
- 🔴 **HARD RULE HRV 闸门覆盖**：每月 ≤2 次主观覆盖，每次事后复盘；连续 2 周覆盖 → 闸门作为过载预警失效
- 🔴 **HARD RULE 课表里不出现 Z1 / <1h Z2** (5/11 锁定)：active recovery 选项 = 全休 或 ≥60min Z2，没有中间档；coach 不要安排 30-40min Z1 easy
- 🔴 **HARD RULE race-1 不开腿** (5/11 锁定)：赛前一天习惯休息或随便骑（commute），不要正式开腿课；race day morning warmup 自带激活
- 🔴 **HARD RULE race calendar 整体优先于单点 peaking** (5/11 锁定)：多场 race 块设计 plan 必须纳入整个 race block 的 adaptation 窗口（如 5/17→5/31 20 天 race block），不要只盯下一场 A 赛牺牲后续准备
- 🔴 **HARD RULE coach session 数据完整性自检** (5/12 锁定)：用户当日多次 ride 场景下 sync_data.py 默认抓取条数不够；coach session 开场必须 cross-check `ls icu_data_warehouse/5_Activities_Detail/ | grep <today>` 确认活动数量后再分析，否则会基于不完整 evidence 给出反向判定 — 比 sycophancy 更危险因为无 push-back 信号
- 🔴🔴 **HARD RULE rep 分析必须 invoke `stream-onset-detect` skill** (5/12 锁定 / 5/15 升级 R20)：Garmin 记圈 vs 真实摇车起爆有 1-3s 漂移。任何 rep/set/interval/lap/spike/race-rhythm 分析**第一步必须 invoke `stream-onset-detect` skill via Skill tool**, 不接受用 ICU lap `average_watts` 直接判定。**违反 case 2026-05-15**: 用 lap 数字判 5/15 race-rhythm "spike 5/9 达标 / 稳态刚卡 target", 重做 stream-detect 后:稳态 lap 318W→真实 338W (+20W over target), spike peak lap-avg 474W→真实 peak 579W (+99W over), 9/9 全部超 480W → 完成度从"中等达标"翻转为"明显 over-target"。**lap 系统性低估**: 稳态切前缘 ramp-up (12-17s) → 偏低 6%；spike 把恢复 tail 算进去 → 偏低 20%+。**完成度判定 (A/A+/B) 必须基于 stream-detected, 不是 lap**。例外: LSD/比赛/通勤短骑不需要。SessionStart hook 自动加载 R20 提醒 — 见 memory `feedback_lap_alignment_drift.md` + `feedback_coach_session_protocol_v2.md` R20 + skill `stream-onset-detect`
- 🔴 **HARD RULE 教练分析后必须主动互动** (5/12 锁定)：每次训练分析输出后必须主动抛 1-3 个具体问题问体感/疑点/与数据不符之处，不能单方向输出结论自以为是 — 见 memory `feedback_active_interaction.md`
- 🔴 **HARD RULE 阀门设计降级** (5/12 锁定): HRV 单日数值不再硬挂 reps 上限（5/10 OU 与 5/12 30/30 用户两次覆盖阀门均 A 级完成，3 次决策阀门错 2 次）；reps 数由用户体感决定；阀门仅作"异常趋势信号"
- 🟡 **股四头疲劳风险 5/17 race day** (5/12 锁定): 今日 12 次 r1 高扭矩 + 末段 all-out → 大腿前侧酸；TT 姿势会放大酸感 → race 起跑后 30 min 内不上 TT，长平路上 TT 要警惕大腿前侧信号，一旦"酸"（不是只"紧"）立刻坐起来 — 见 [[sites/mountain-3-climb]]
- 🟡 **race 周后续课不做股四头爆发** (5/12 锁定): 5/14 race-rhythm 功率 450W 稳态 OK（不爆发）；5/15 短-强可保留 3×4min；race 前 5 天不要再做 30/30 / 起跑课 / Mountain 3 类的爆发课
- 🔴 **HARD RULE**: 功率曲线只有 ≤ 20min 是 at-max；55min 是 RPE 体感，**不可数学反推**；30+ min 全部 sub-max — 见 [[athlete]] §功率曲线数据质量
- 🔴 **HARD RULE**: 用乐观估计给用户台阶下 = sycophancy 变种 — 见 [[athlete]] § 反 sycophancy 个案

## sync 失败警告（持续）

- **2026-10-16**：基础数据已刷新；默认代理失效、功率曲线请求范围错误、空日历未覆盖旧缓存均已在本次同步中绕过，源码尚未修。自动疲劳摘要仍取最后活动日、执行评估仍引用旧计划；后续分析核对原始日期，详见本次session。

- `trend_analyzer.py` + `refresh_physiology.py` 在 streams 是 list 的活动上抛 `'list' object has no attribute 'get'`。修复前，区间分布 / 生理画像数据陈旧。
