---
date: 2026-10-26
tags: [knowledge-base, load-metrics-and-tools]
related: [[knowledge/README]]
---

# 负荷指标与工具（load-metrics-and-tools）

> 来源档位、可靠性判断和对本人的适用性见每条；只有 [研究] 能单独作为定剂量的依据。格式与更新方式见 [[knowledge/README]]。
### CTL 区分不了"6 天各 163 + 1 天全休"和"7 天各 140"；固定休息日还可以作为缓冲（收录 2026-10-26）
- 来源: [社区] intervals.icu「Why Overtraining for me was the best thing I ever did」#9 @demogar（Supporter）2026-10-03，点赞 0；#7/#12 @ivegotabike（Supporter）2026-10-03 / 10-04，点赞 0/0；反方 #11 @Steve_Balboni（普通用户）2026-10-04，点赞 0，https://forum.intervals.icu/t/why-overtraining-for-me-was-the-best-thing-i-ever-did/132683
- 依据: #9 是 CTL 计算本身（约 42 天加权平均），并给出检验方法：固定休息日跑 3–4 周，比较休息日当晚的睡眠和下一课同功率的主观吃力度；固定休息日也是生活冲掉课时的挪课缓冲。#12 转引 roadmancycling 文章中 Friel、Lorang 的话（"没有明确设计恢复日的计划只是累积表"）。反方 #11 认为长期系统层面身体不在乎负荷在一周内怎么分布。
- 我的判断: 可靠性 中。数学部分正确；"分布无所谓"缺乏依据，同等总量下单次剂量大小和恢复窗口对质量课有影响[未核实]。与研究：CTL 部分一致，分布效应不确定。
- 对本人: 适用。本人周一、周五固定休息，这条支持保留；生活冲掉的课优先挪到休息日附近，不叠加到 Crazies 前。

### PMC 只在"直接测外部负荷 + 阈值定义准确"时可靠；功率、配速、心率算出的负荷不要混用（收录 2026-10-26）
- 来源: [社区] intervals.icu「What use does the PMC actually have for a hybrid coach/athlete?」#2 @MedTechCD（staff, moderator）2026-10-17，点赞 2，https://forum.intervals.icu/t/what-use-does-the-pmc-actually-have-for-a-hybrid-coach-athlete/133080
- 依据: 对 TSS/PMC 来历的解释：TSS 以 FTP 为参照，FTP 需要定期测准；如果某项活动用 TRIMP/心率负荷，就所有活动都用它，不要和功率/配速 TSS 混用；心率负荷以阈值心率为锚，量纲与功率 TSS 不同。
- 我的判断: 可靠性 中高（逻辑正确，来自工具资深版主）。与研究：一致（TSS 定义本身就依赖阈值）。
- 对本人: 适用。本人的 TSS 以 ICU 里设定的 FTP 为参照，FTP 历史改写后 CTL 整体平移，所以 CTL 只能当参考区间；同一时期内的比较才有意义。

### intervals.icu 的 HRRc 怎么算：心率越过阈值后，60 秒内的最大降幅；恢复段功率太高会被忽略，最好停踩滑行（收录 2026-10-26）
- 来源: [社区] intervals.icu「Heart rate recovery HRRc」#76 @Gerald（staff, moderator）2025-07-30 转引开发者 David 的公告，点赞 0；#67 同一用户 2025-04-24；#79 @R2Tom（staff, moderator）2025-07-30，点赞 2，https://forum.intervals.icu/t/heart-rate-recovery-hrrc/387
- 依据: 开发者公告：从至少达到阈值（Z5/LTHR，触发值可在设置里调）的心率开始，取 60 秒内的最大心率降幅；有功率的活动中，若恢复段平均功率超过 FTP 的 1/3 或 5 秒功率超过 FTP 的 1/2，该段被忽略，所以最好滑行。HRRc 取全次活动中最好的一段，不同于 Garmin 停止后 2 分钟的算法。#79：心率滞后于功率，从努力结束那一刻起算本来就不对；想"测"这个指标，可以在课末做一次狠的，然后停踩并继续记录。
- 我的判断: 可靠性 高（工具定义来自开发者）。与研究：不适用（属于工具口径）。
- 对本人: 待验证。只有在课末用同一套做法（同一段坡、停踩、继续记录）时，这个数才有可比性。

### 运动中的 rMSSD 必然被压低，用处不大；DFA a1 的固定阈值（0.75/0.5）类似"2/4 mmol"，因人而异（收录 2026-10-26）
- 来源: [社区] intervals.icu「Activity HRV (not Wellness)」#9/#11 @Luisma_Gallego_Soy_P（staff, moderator，自述分析 DFA 3 年）2024-08-05，点赞 1/3；#10 @miguelpais（Supporter）2024-08-05，点赞 1，https://forum.intervals.icu/t/activity-hrv-not-wellness/73153
- 依据: 经验加观点。#9：运动时交感激活，rMSSD 必然下降，分析价值低，可用于看运动后的恢复。#11：DFA 阈值研究多用固定的 0.75 和 0.5，就像把 2 mmol 当 LT1、4 mmol 当 LT2；DFA 受自主神经状态等很多因素影响，不懂控制就价值很低；他提到的 RRa1 指标尚无已发表研究（他们在收集数据）。#10 总结：大家仍靠静息/晨起 HRV 看训练反应，用运动中的 DFA1 定 VT1/VT2 没有成为"圣杯"。
- 我的判断: 可靠性 中。DFA a1≈0.75 对应 VT1 有验证研究，但个体偏差可观，这与他的说法方向一致[未核实]；RRa1 没有研究支持，是他的自研指标。与研究：大体一致，RRa1 部分没有研究。
- 对本人: 不适用（当前）。本人按功率锚点定强度，不需要引入 DFA a1。

### CTL 是指数加权平均，不是 42 天滑动窗口；要维持 CTL = X，每周负荷约等于 7×X（收录 2026-10-26）
- 来源: [社区] intervals.icu「FITNESS PAGE - a guide to getting started」#2 @MedTechCD（staff, moderator）2022-08-13，点赞 19；#6 @Gerald（staff, moderator，自述带运动员）2022-08-20，点赞 18；#103 @tennisninja（普通用户）2025-06-25，https://forum.intervals.icu/t/fitness-page-a-guide-to-getting-started/17702
- 依据: 模型定义：Fitness 默认时间常数 42 天，Fatigue 默认 7 天；约 6 周规律训练后曲线才有意义。#6：维持 70 需要每周约 490（70×7），可以每天 70，也可以隔天 140。#103：此前误以为超过 42 天的负荷不再计入，其实是指数加权，更早的负荷权重变小但仍有贡献。
- 我的判断: 可靠性 高（属于模型数学）。与研究：不适用（模型定义本身）。
- 对本人: 适用。估算周负荷对 CTL 的影响时用这条：周负荷高于约 7×当前 CTL，CTL 才会上升；具体数值读当前的 fitness_trend，不在这里写死。

### Form（TSB）用绝对值还是百分比，对 CTL 很低或很高的人差别很大；有人把自己的下限定在 −22 而不是默认 −30（收录 2026-10-26）
- 来源: [社区] intervals.icu「FITNESS PAGE - a guide to getting started」#3 @MedTechCD（staff, moderator）2022-08-13，点赞 27，https://forum.intervals.icu/t/fitness-page-a-guide-to-getting-started/17702
- 依据: 算例：CTL 100、ATL 130 时两种显示都是 −30；CTL 15、ATL 19.5 时，绝对值为 −4.5，百分比为 −30%。建议低 CTL 用绝对值，长期高 CTL（>100）可考虑百分比，中间人群两种都试，看哪个更贴合主观感受。个人做法：几乎不让 Form 低于 −22。
- 我的判断: 可靠性 中（算例正确，阈值是个人经验）。与研究：没有研究（色区阈值是工具约定）。
- 对本人: 待验证。本人的 CTL 在两种显示差别不大的区间；本人已有"单日 >200 TSS 且 TSB <−20 次日强制休"的规则，这条不改变它。

### 年龄主要影响恢复：年长者调大 Fatigue 时间常数（9–10 天），不要动 Fitness 常数（收录 2026-10-26）
- 来源: [社区] intervals.icu「FITNESS PAGE - a guide to getting started」#107 @MedTechCD（staff, moderator）2025-10-14，点赞 0，https://forum.intervals.icu/t/fitness-page-a-guide-to-getting-started/17702
- 依据: 经验观点（针对一位 70 岁用户的提问）。
- 我的判断: 可靠性 中低（没有给依据，年龄与恢复速度的关系是否能用改常数来表达未经验证）[未核实]。与研究：不确定。
- 对本人: 不适用（本人年轻，默认常数即可）。

### 把 eFTP 的"最短时长"设在个人功率曲线开始变平的位置（如约 10 分钟），以免短时间无氧成分把 eFTP 推高（收录 2026-10-26）
- 来源: [社区] intervals.icu「What time and settings to set for realistic automatic FTP detection?」#2 @R2Tom（staff, moderator）2026-10-21，点赞 5，https://forum.intervals.icu/t/what-time-and-settings-to-set-for-realistic-automatic-ftp-detection/133187
- 依据: 经验建议：看 Best Efforts 页的 Power Profile 表，曲线在短时长处下降、到某一点后变平（示例约 10 分钟）；比这更短的努力无氧占比可能更大，会把 eFTP 推高。
- 我的判断: 可靠性 中。与临界功率模型的常识一致：只用短时长努力拟合时，无氧贡献会让有氧上限被高估[未核实具体时长界限]。与研究：一致。
- 对本人: 适用。本人快肌主导、冲刺强，短时努力很容易抬高 eFTP，这也解释了"ICU eFTP 不作准"；若还要参考 eFTP，应把最短时长设到曲线变平的位置。

### RPE 只按"这一堂实际感觉"打分，不要与别的课比较；把实际中等的课报成轻松，系统会以为你能承受更多（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Endurance vs. Easy: Does TR Treat Them Differently?」#62 / #68 @eddie（TrainerRoad Team, staff/admin）2026-10-25~26，点赞 3 / 0，https://www.trainerroad.com/forum/t/endurance-vs-easy-does-tr-treat-them-differently/115303
- 依据: TR 官方 RPE 量表（1 轻松 ~ 5 极限，以"能否再加一组"界定）；#64 @OatyPedaller 同意"只评这一堂这一天"。
- 我的判断: 可靠性 中——针对 TR 产品的打分口径，但"按实际感觉记录"作为数据卫生原则通用；与研究: 一致（sRPE 依赖真实主观报告）。
- 对本人: 适用（原则）——本人记录 RPE 时也应按当次实际感觉，避免与 VO2 课比较后把长 Z2 报低。

### TR 内部数据（播客转述）：大训练量冲击（如训练营式猛加量）对进步的伤害可能与零训练周相当甚至更大；用 12 周周时数的变异系数（CV=标准差/均值）衡量一致性（收录 2026-10-26）
- 来源: [社区] TrainerRoad「TrainerRoad Ask a Cycling Coach #600 is driving me crazy」#1 / #37 @Brennus（普通用户）2026-09-20~22，点赞 2 / 1，https://www.trainerroad.com/forum/t/trainerroad-ask-a-cycling-coach-600-is-driving-me-crazy/115015
- 依据: 转述 TR 播客 AACC #599/#600 的"Big Data"图表；同时指出 TR 给出的计算方法算不出 TR 幻灯片上的示例分数（疑似用了 13 周等不同方法）。
- 我的判断: 可靠性 低-中——TR 自有观察性数据、未经同行评审、方法与展示数字不自洽，且有产品立场；与研究: 不确定（"负荷突增有害"与急慢性负荷相关讨论方向一致 [未核实]）。
- 对本人: 适用（方向）——与本人 6 月底"低量后突然猛加量"的教训一致；可在 ICU 里算 12 周周时数/周负荷 CV 作为辅助观察，不当硬指标。

### CV 低不等于好：负荷完全不变 CV=0 但没有渐进超负荷；有规律的减量周本身会把 CV 拉到约 20%（收录 2026-10-26）
- 来源: [社区] TrainerRoad「…#600 is driving me crazy」#7 / #34 / #36 @GoLongThenGoHome（普通用户）2026-09-20~22，点赞 4 / 0 / 0，https://www.trainerroad.com/forum/t/trainerroad-ask-a-cycling-coach-600-is-driving-me-crazy/115015
- 依据: 统计定义 + 自己的示例计算（起始周 TSS 300、每周 +8% 或 +5%、每第 4 周减 40%，12 周 CV 约 21.9% / 19.7%）。
- 我的判断: 可靠性 高——统计推理正确，示例数字为发帖人计算、量级合理 [未逐一复算]；与研究: 没有研究（属指标解读）。
- 对本人: 适用——若用 CV 评估本人，应先剔除计划内的减量周或分开看建设周，否则会误判。

### Hexis 一类"按训练计划自动分配每餐碳水"的 App：概念受认可，但食物库/可用性差，多人退款；有人改用 MyFitnessPal + 从 intervals.icu 同步训练来自己算（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Anyone with experience using nutrition app Hexis?」#16 @Jo_McAleer 2023-11-23 点赞 2；#19 @MarekBns 2024-04-29 点赞 0；#28 @jplucas14 2026-09-27 点赞 2（均为普通用户）；#13 @David_Dunne（自称 Hexis 创始人，利益相关）2023-10-17 点赞 5，https://www.trainerroad.com/forum/t/anyone-with-experience-using-nutrition-app-hexis/85624
- 依据: 用户使用体验；创始人回复属于厂商宣传。#25 @SJ_Estrada 2024-12-15 称多数问题已修复。
- 我的判断: 可靠性 中（工具体验，时效性强）。与研究: 没有研究（帖内提到的厂商资助研究无具体信息）。
- 对本人: 不适用——本人用固定份量 + 训练日/休息日两档足够；不值得为此付费订阅。

### intervals.icu 有社区自定义活动字段 AeT、AeT HR、MSS、pVO2max，靠功率曲线估算；作者对算法的描述前后不一，属于黑箱，只能当参考（收录 2026-10-27）
- 来源: [社区] intervals.icu「New Test of calculated fields」#1/#106/#114/#118 @Luisma Gallego（Supporter, staff, moderator）2024-08-09 ~ 2026-02-07；#19 @david（intervals.icu 开发者）2024-08-10，点赞 3；#18 @WindWarrior（Supporter）2024-08-09；#113 @R2Tom（staff, moderator）2026-02-06；#120/#121 2026-08，https://forum.intervals.icu/t/new-test-of-calculated-fields/73968
- 依据: 版主自建字段与用户试用反馈。#1：基于近 30 天数据和功率曲线，当时不用 DFA a1；#114：结合代谢车数据、WKO5 的有氧/无氧贡献和功率曲线；#118：又说基于 DFA a1、呼吸率和 rrA1——三处说法不一致。#106：功率曲线不新鲜，估值就不准。#19：一天多骑时字段的聚合方式要从 Sum 改成 Max，否则图上出现尖峰。#120/#121：加字段后要 Re-analyse 活动，有人要 Reprocess（先备份）。#18：AeT HR 133bpm 与自己感觉呼吸变化的 135–137bpm 接近；pVO2max 估 351–354W，对应他功率曲线约 150–160s 的功率，比 WKO5 的 335W 高；MSS 大约等于他 50–120 分钟的功率。#113：MSS 应在 FTP 与 AeT 中间。#122（2026-10-26）：有人觉得"准得吓人"。
- 我的判断: 可靠性 低-中——作者是版主，但算法未公开且描述自相矛盾；只有少数用户的个案对照，没有与实验室乳酸/气体测试的比对。与研究：没有研究（帖中未引用）。
- 对本人: 待验证，不用于处方。本人 10/19 说明当时 >1 分钟的时长没有做过全力、CP5 只是猜测，功率曲线"喂料"不足，MSS、pVO2max 估值在 11/6 Faber 测试前大概率不可信；定强度仍按近期实际同类课和 90 天滚动最好值。若本人想试，可自己在 ICU 加字段只看 AeT HR 是否与其 Z2 体感一致；教练不改 ICU 设置。

### 模型类估值（eFTP、MSS、pVO2max 等）要靠功率曲线"喂料"：定期在 1、5、10–20 分钟等时长做全力或接近全力；用 Strava 路段比赛代替"测试"更容易做到（收录 2026-10-27）
- 来源: [社区] intervals.icu「New Test of calculated fields」#108/#111 @Luisma Gallego（staff, moderator）2025-11-20/21，点赞 0/1；#103/#110 @Gerald M（staff, moderator）2024-11-23 / 2025-11-20，点赞 6/2，https://forum.intervals.icu/t/new-test-of-calculated-fields/73968
- 依据: 版主经验。#103 转述 WKO 的 Tim Cusick 视频："不喂模型，它就预测不了你能做什么"（视频未核）。#110：很多人一听"测试"就怕，换成"刷路段"就愿意做，路段是"伪装的测试"。
- 我的判断: 可靠性 中——功率—时长模型依赖各时长的最大努力，这是模型本身的前提，逻辑上成立；与研究：没有研究（帖中未引用）。
- 对本人: 适用。本人不做全力 FTP 测试；Faber 双向、Crazies 终点坡这类自然出现的全力努力就是"伪装测试"，也是 90 天滚动最好值的来源。功率曲线某个时长长期没有全力时，该时长的数只能当下限，不能反推能力下降。不改课表。
