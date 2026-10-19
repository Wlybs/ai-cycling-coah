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
| KOM / 段目标（活跃 + 已完成） | `kom-targets.md`；当前Faber专页 `kom-targets-mount-faber.md` |
| 长期身体特质 / 装备 / 受伤史 | `athlete.md` 仅在事实变化时更新 |
| 临时 / sync 后即弃 | **不进 vault**，留在 `coach_memory/` |

## 子笔记

- [[athlete]] — 长期定性特质（Type-II / 受伤史 / 装备 / 训练偏好）
- [[decisions]] — 教练决策日志（FTP 调整、范式转向、协议变更）
- [[races]] — 比赛日历 + 历史结果
- [[kom-targets]] — 历史林峰目标；当前Faber双向见 [[kom-targets-mount-faber]]
- [[training-plan]] — 2026-05 比赛块训练框架（历史参考，非当前计划）
- [[racemap]] — 5 月 4 场赛事详细情报（GPX 路线 + 阶段功率 + 战术 + 补给 + 难度评估）
- [[sites/mountain-3-climb]] — Mountain 3 单 climb 三段地形 (r1 陡 / r2 短陡+平路 / r3 长陡到顶)、stream 实测数据、训练适配建议（2026-05-12 锁定）
- [[sites/lck-training-loop]] — 当前新加坡持续训练场地；本人记录地形及连续性边界
- `sessions/` — 每次教练对话归档（按日期）

## 最近 5 次 session

- 2026-10-19 — [[sessions/2026-10-19-workout-library-and-frontier-review]] — 课表库按A–G归类统一%FTP，补回5月OU/30/30/race-rhythm等；近三年补充：耐久性、受控大体积阈值、30/15、力量、补给。根因：5月vault文件主仓untracked，worktree缺失。
- 2026-10-19 — [[sessions/2026-10-19-workout-catalog-and-self-assessment]] — 汇总当前六类课型完整形式；自评：场地/恢复/日程定制高，强度锚点（300W工作设定、280–290W、VO2剂量）为试行未验证。无新处方。
- 2026-10-19 — [[sessions/2026-10-19-low-burden-ftp-calibration]] — 提出两次原质量位受控持续校准290→300W，不力竭；用于工作设定验证、非精准FTP认证，未改ICU。
- 2026-10-19 — [[sessions/2026-10-19-current-versus-peak-gap]] — 本人撤销CP5猜测依据、>1min未全力；短爆发强，持续记录差≠能力损失；近期两周总量已恢复，CTL不当能力百分比。
- 2026-10-18 — [[sessions/2026-10-18-vo2-dose-and-floating-quality-days]] — 认可两种VO2可调范围、区分大剂量；质量日默认周二可浮动，后移替换长骑/周日机会，不补债；本人明确睡眠/起床或实际腿乏触发。

## 当前活跃旗标

- **当前训练建议**：[[plans/2026-10-19-faber-and-drcc-eight-week]] revision8（10/19精简为7类：有氧/Faber VO2/LCK持续/耐久长骑/Crazies/PR/力量；删30/15与5月专项；PR前偏VO2、PR后偏持续耐久；rev7日期自调）；替代10/16四周稿；短期A拟报12/13 DRCC，Faber双向PR/CP3为中途检验，2027目标保留。10/17 revision3：单次≥2h、Faber固定终点/自然下坡恢复约2:40–3:00起步（非强制等4–5min）、LCK主要U-turn。10/18本人另确认计时3/3可行（少下一段/轻微荡腿），非必须到顶；10/20首选原4整坡；若10/25attack且缺持续工作，10/27优先LCK替代Faber，见最新session。revision5默认周中浮动质量（周二至周四优先）+周日，后移替换长骑/周末机会、不补债；每周约两质量，threshold lead替代周四硬课，Crazies尽量保留；关键专项/减量周必要让位。12.5h五骑两休，赛周减天数，未写ICU。
- **Faber与赛事边界**：双向映射时间不是官方PR，10/13反向端点存在匹配差异；Faber180s与生涯180s分开。DRCC主办海报列末档11/1，当前余位/资格、GPX待核，未报名；见最新session及races。

- **教练互动偏好**：给有证据的首选/理由/条件，本人按当天状态决定，不主动推ICU；只问已发生体感/真实疑点，不问未来身体状态。
- **10/18证据规则**：只引用近三年运动科学；10/19本人明确CP5只是无把握猜测、>1min未全力，不能计算损失；90d非上限；中高踏频已订正。Claude原稿在独立worktree，完整复核见最新session，未合并分支。

- **算法协作偏好**：复杂批量计算先给同项目Claude Code可执行prompt，教练复核整合；Claude已完成Cycling-lth，教练已验收；后续进度仍由bd跟踪，数据结果见最新session。

- **2026-10-16最新补充**：核心巅峰4/1–6/1、最后巅峰延至6/9且该日全力CP5必须补回；7月低量、8月复训；Crazies为主动筛选角色，计入强度。室内外同功率计，室内散热/补给与10/13主动停止原因已记；未来FTP无已证实保底数值，详见最新session。

- **2026-10-16更新**：以本次power-review session为准；目标2027 Nationals，常态10–15h，身体良好。9h示例已被新信息修正；出生/国籍/执照见athlete，勿反复问。

- **2026-10-16 当前入口**：长期目标为2027备赛；短期新增12/13 DRCC（10/17）；不喜欢天天训练，最多每周两次3.5h以上。5月比赛块的日程/状态旗标已归档至 [[archive/2026-05-race-block-flags]]，不能作为当前课表或生理结论。

> 任何"未完结"或"需要关注"的事，写在这里，解决后划掉。

## 长期规则（2026-05 锁定，仍有效）

> 下面是 5 月形成、仍适用的工作规则（原文保留）。当日状态与比赛周日程见 [[archive/2026-05-race-block-flags]]。

- 🔴 **HARD RULE 课表 single source of truth = ICU push workout_doc** (5/12 锁定)：vault 简写 ("3×3×450W") 仅做参考，引用必查 ICU push 的 workout_doc 真实 steps（之前混淆 race-rhythm = 3×3min 稳态 450W vs 真实 3 set × 6min 含 9 次 W' burst）
- 🔴 **HARD RULE 阀门设计降级 (5/12 锁定)**: HRV 单日数值不再硬挂 reps 上限（5/10 OU 与 5/12 30/30 用户两次覆盖阀门均 A 级完成，3 次决策阀门错 2 次）；reps 数由用户体感决定；阀门仅作"异常趋势信号"——HRV 连续 2-3 天下滑 **AND** RHR 比 baseline 高 5+ bpm 持续 2 天 → 教练主动 flag，但不指定 dose
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
- 🔴 **HARD RULE 课型 dose 评估标准 (5/10 锁定)**：OU/VO2max/W' burner/race-rhythm/SST 各有期望签名，不能跨用——OU "心率不到 Z5 + W' 不烧空" 是设计内的正常签名不是 bug
- 🔴 **HARD RULE HRV 闸门覆盖**：每月 ≤2 次主观覆盖，每次事后复盘；连续 2 周覆盖 → 闸门作为过载预警失效
- 🔴 **HARD RULE 课表里不出现 Z1 / <1h Z2** (5/11 锁定)：active recovery 选项 = 全休 或 ≥60min Z2，没有中间档；coach 不要安排 30-40min Z1 easy
- 🔴 **HARD RULE race-1 不开腿** (5/11 锁定)：赛前一天习惯休息或随便骑（commute），不要正式开腿课；race day morning warmup 自带激活
- 🔴 **HARD RULE race calendar 整体优先于单点 peaking** (5/11 锁定)：多场 race 块设计 plan 必须纳入整个 race block 的 adaptation 窗口（如 5/17→5/31 20 天 race block），不要只盯下一场 A 赛牺牲后续准备
- 🔴 **HARD RULE coach session 数据完整性自检** (5/12 锁定)：用户当日多次 ride 场景下 sync_data.py 默认抓取条数不够；coach session 开场必须 cross-check `ls icu_data_warehouse/5_Activities_Detail/ | grep <today>` 确认活动数量后再分析，否则会基于不完整 evidence 给出反向判定 — 比 sycophancy 更危险因为无 push-back 信号
- 🔴🔴 **HARD RULE rep 分析必须 invoke `stream-onset-detect` skill** (5/12 锁定 / 5/15 升级 R20)：Garmin 记圈 vs 真实摇车起爆有 1-3s 漂移。任何 rep/set/interval/lap/spike/race-rhythm 分析**第一步必须 invoke `stream-onset-detect` skill via Skill tool**, 不接受用 ICU lap `average_watts` 直接判定。**违反 case 2026-05-15**: 用 lap 数字判 5/15 race-rhythm "spike 5/9 达标 / 稳态刚卡 target", 重做 stream-detect 后:稳态 lap 318W→真实 338W (+20W over target), spike peak lap-avg 474W→真实 peak 579W (+99W over), 9/9 全部超 480W → 完成度从"中等达标"翻转为"明显 over-target"。**lap 系统性低估**: 稳态切前缘 ramp-up (12-17s) → 偏低 6%；spike 把恢复 tail 算进去 → 偏低 20%+。**完成度判定 (A/A+/B) 必须基于 stream-detected, 不是 lap**。例外: LSD/比赛/通勤短骑不需要。SessionStart hook 自动加载 R20 提醒 — 见 memory `feedback_lap_alignment_drift.md` + `feedback_coach_session_protocol_v2.md` R20 + skill `stream-onset-detect`
- 🔴 **HARD RULE 教练分析后必须主动互动** (5/12 锁定)：每次训练分析输出后必须主动抛 1-3 个具体问题问体感/疑点/与数据不符之处，不能单方向输出结论自以为是 — 见 memory `feedback_active_interaction.md`
- 🔴 **HARD RULE**: 功率曲线只有 ≤ 20min 是 at-max；55min 是 RPE 体感，**不可数学反推**；30+ min 全部 sub-max — 见 [[athlete]] §功率曲线数据质量
- 🔴 **HARD RULE**: 用乐观估计给用户台阶下 = sycophancy 变种 — 见 [[athlete]] § 反 sycophancy 个案

## sync 失败警告（持续）

- ✅ **2026-10-16 已修源码**（branch `claude/cycling-ai-assist-review-187e79`）：`PROXY_PORT` 不可达时自动直连；功率/心率曲线改用 `curves=90d/all` 并校验响应 id；空日历也覆盖 `events.json`；`training_analysis.json` 疲劳段改标 `last_ride_*`（当前 CTL/ATL/TSB 看 `fitness_trend.json` 的 current）；`plan_adherence.json` 不再评估 7 天前结束的旧计划（无近期计划时写 `status: no_recent_plan`）。

- 🟡 streams 为 list 的旧详情文件：`trend_analyzer.py` 已兼容（2026-10-16）；`refresh_physiology.py` 一侧（`icu_loader.normalize_streams`）有另一会话的未提交改动在处理，待其落地后再划掉。
