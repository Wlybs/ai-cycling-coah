---
date: 2026-10-26
tags: [knowledge-base, coaching-practice]
related: [[knowledge/README]]
---

# 教练方法（coaching-practice）

> 来源档位、可靠性判断和对本人的适用性见每条；只有 [研究] 能单独作为定剂量的依据。格式与更新方式见 [[knowledge/README]]。
### 自动阈值估算之间有分歧很正常，用能实际持续的那个；新手先偏保守再逐步上调（收录 2026-10-26）
- 来源: [社区] intervals.icu「Correct setting of zone」#2 @JamN（Supporter）2026-10-16，点赞 3，https://forum.intervals.icu/t/correct-setting-of-zone/133054
- 依据: 观点（讨论的是跑步阈值配速，原则通用）：不同平台的数据和算法不同，估算值有分歧正常；该问哪个值与你实际能持续的强度相符（新鲜状态下约 45–60 分钟）；先用保守值做几次阈值课，看配速、心率、主观吃力，太轻再逐步上调；目的不是让两个平台一致。
- 我的判断: 可靠性 中。实用原则，与"用实测表现校准估算值"的通行做法一致。与研究：一致。
- 对本人: 适用（原则层面）。本人已经按近期同类课实测和 90 天滚动最好值定强度，不按算法估算的 FTP；这条是旁证。

### 一位教练的周结构示例：每周 5–6 练，2 硬 2 易，周末 1–2 次长耐力；阈值课如 4–5×8min（收录 2026-10-26）
- 来源: [社区] intervals.icu「FITNESS PAGE - a guide to getting started」#6 @Gerald（staff, moderator，自述带运动员）2022-08-20，点赞 18，https://forum.intervals.icu/t/fitness-page-a-guide-to-getting-started/17702
- 依据: 自己和所带运动员的做法；先定已知要做的课，再倒推负荷。示例：一周 490 = 4h 耐力（220）+ 2 次阈值课各 4–5×8min（各 75）+ 2h 耐力（115）。
- 我的判断: 可靠性 中（教练实践，不是研究）。与研究：大体一致（每周约 2 次高强度、其余低强度是常见做法）。
- 对本人: 适用。与本人"每周硬课 ≤2、Crazies 算 1、其余 Z2"的结构一致。

### LLM 更适合做数据分析而不是开训练处方，需要懂原理的人把关（收录 2026-10-26）
- 来源: [社区] intervals.icu「Integrated LLMs vs. Algorithmic Coaching: Utility, Guardrails, and Safety」#2/#5 @WindWarrior（Supporter）2026-10-09 / 10-10，点赞 4/2；#7 @JamN（Supporter）2026-10-10，点赞 4；反方 #4 @Andreas_Schnederle-W（Supporter）2026-10-10，点赞 3，https://forum.intervals.icu/t/integrated-llms-vs-algorithmic-coaching-utility-guardrails-and-safety/132885
- 依据: 观点。#2/#5：用基本原理和常识，有效训练看似简单，容易想复杂。#7：KISS，简单的课、持续地做、目的明确。反方 #4（个人经验）：用 ChatGPT 通过 MCP 读 intervals 数据（CTL/ATL、HRV、RHR、睡眠、主观反馈）做了 4–6 周跑步准备，效果满意；他承认 AI 会犯错，需要质疑和纠正，认为理想形态是可靠数据 + 确定性计算 + 安全上限 + 有判断力的人。
- 我的判断: 可靠性 中（双方都基于经验；#4 自己也承认单次比赛不能证明什么）。与研究：没有研究。
- 对本人: 适用。本项目的 AI 教练应继续让本人参与课表决策，给出依据，不自动推送。
- 补充（2026-10-27）：TrainerRoad「Incorporating Garmin Training Readiness Data into TR」#3 @PhilipK（普通用户）2026-10-26，点赞 0：让 Claude 读自己的 Garmin HRV 和睡眠分，它总是建议休息或改轻松课；而 Garmin 会把半夜醒着记成睡着。#10 @JoeX（点赞 1）：试过写"x>n 且 y<m 就做 z"的确定性规则，结论是生理不按这种规则走，指标是"提示"不是"指令"。可靠性 低-中（个人经验）。对本人：提醒本项目的 AI 教练不要把单日可穿戴数据翻译成"减量/休息"，与 INDEX 5/12"阀门降级"规则一致。

### 让 LLM 只调用确定性代码算数，并单独设一道"每个数字都要标出处"的证据关（收录 2026-10-26）
- 来源: [社区] intervals.icu「Integrated LLMs vs. Algorithmic Coaching: Utility, Guardrails, and Safety」#3 @GarageLab（Supporter，自述用于工程与运动生理工作流）2026-10-10，点赞 0；#8 @Jaap_van_Ekris（普通用户）2026-10-11，点赞 0，https://forum.intervals.icu/t/integrated-llms-vs-algorithmic-coaching-utility-guardrails-and-safety/132885
- 依据: 个人实践。#3：Banister、PMC、CP、预测、比赛规划等模型用 Python 写好，经 API 给 LLM 调用；资料走自己整理的 RAG；专门做一个 agent 负责给所有数值和信息标出处，未核实的地方加注释；即便如此，LLM 也做不到 100% 准确。#8：数据计算放在 MCP 一侧，做合理性检查和基本规则约束，减少大段数据在模型里来回。
- 我的判断: 可靠性 中（实践经验，与通行的工程做法一致）。与研究：没有研究。
- 对本人: 适用。与本项目"每条结论带证据块、禁止硬编码运动员数值"的规则同方向。

### 脏数据是教练工作的大头：数据显示来源、缺数据不要静默补默认值、发布前有人审、同样输入得同样输出（收录 2026-10-26）
- 来源: [社区] intervals.icu「Integrated LLMs vs. Algorithmic Coaching: Utility, Guardrails, and Safety」#6 @Gabriel_Vargas（普通用户，从语境看是教练）2026-10-10，点赞 4；#9 @Vincent_Barbaix（自述教练，并声明在做基于 intervals 的确定性规划工具、有利益相关）2026-10-16，点赞 2，https://forum.intervals.icu/t/integrated-llms-vs-algorithmic-coaching-utility-guardrails-and-safety/132885
- 依据: 实践经验。#6：大量工作花在识别和修正错误心率、功率计掉线/校准漂移、同一活动来自码表/手表/Whoop 的重复文件，以及手动补录。#9：实验室测的阈值、场地测试算的阈值、eFTP 估算出的阈值不应显示得一样；缺体重或测试时要明说，不要补默认值；教练或运动员审核后才发布到日历；同样输入得同样输出，便于追溯异常的一周。
- 我的判断: 可靠性 中高（实践共识；#9 有利益相关，但所述原则本身中立）。与研究：没有研究。
- 对本人: 适用。分析前先核对活动是否完整、重复，功率/心率是否异常（本项目已有"当日多骑先核对活动数量"的规则）；阈值来源要标清楚。

### 错过关键课：时间原因就有空再补；疲劳、睡差、喉咙不适就作废，不欠；不要把错过的课叠到剩下几天（收录 2026-10-26）
- 来源: [社区] intervals.icu「Research & Discussion: How do you adjust your training when life gets in the way?」#2 @R2Tom（staff, moderator）2026-08-26，点赞 5；#4 @Eugene_S（Supporter，自述在做相关连接器、有偏向）2026-08-28，点赞 0；#10 @Viruela（普通用户）2026-08-31，点赞 0，https://forum.intervals.icu/t/research-discussion-how-do-you-adjust-your-training-when-life-gets-in-the-way-short-survey-for-self-coached-riders/132093
- 依据: 经验规则。#2：关键课错过就重排，轻松课错过就跳过，排不进去也不是世界末日。#4：真正的约束是全周的强度总量，不是单堂课；周末那次骑往往才是主要适应来源，保护它，舍弃周中的课；一次高强度团骑就可能占到半周 TSS。#10：挪还是跳要看错过的原因和训练块目标，挪课的前提是不影响下一堂关键课的恢复。
- 我的判断: 可靠性 中（实践共识，没有研究）。与研究：没有研究。
- 对本人: 适用。本人周日 Crazies 算一堂硬课；周中硬课若因疲劳或睡差错过就作废，不挤到周六，保护 Crazies 和每周硬课 ≤2 的上限。

### 一周被打乱时先砍硬课，保留轻松量（收录 2026-10-26）
- 来源: [社区] intervals.icu「Research & Discussion: How do you adjust your training when life gets in the way?」#5 @Kerry22（普通用户）2026-08-29，点赞 1，https://forum.intervals.icu/t/research-discussion-how-do-you-adjust-your-training-when-life-gets-in-the-way-short-survey-for-self-coached-riders/132093
- 依据: 个人经验：睡眠差或状态很差就跳过间歇课，腿还行就保留轻松量；硬课推迟不等于这一周白费。
- 我的判断: 可靠性 中低（个人经验）。与研究：没有研究。
- 对本人: 适用（有条件）。与本人"不用 <1h Z2，恢复选项只有全休或 ≥60min Z2"的规则结合使用：保留的轻松量也要满足 ≥60min。

### 不同的准备度信号回答的是不同问题，信号矛盾时做小调整或直接问，最差的做法是给一个很自信的新课（收录 2026-10-26）
- 来源: [社区] intervals.icu「Research & Discussion: How do you adjust your training when life gets in the way?」#8 @RideReviewer（普通用户）2026-08-31，点赞 0，https://forum.intervals.icu/t/research-discussion-how-do-you-adjust-your-training-when-life-gets-in-the-way-short-survey-for-self-coached-riders/132093
- 依据: 观点：Garmin 准备度、intervals Form、睡眠、"我觉得累坏了"各自回答略有不同的问题，更新时间也不同；应把信号分开展示、标明数据有多新，矛盾时改动幅度要小或者先问。
- 我的判断: 可靠性 中（合理的决策原则，没有数据）。与研究：没有研究。
- 对本人: 适用。对 AI 教练有直接意义：HRV/RHR、TSB 和本人体感冲突时，按本人"只问体感/状态"的偏好去问，不擅自大改课。

### TR 的 74% 耐力默认值来自以低训练量用户为主的数据，是相关性不是因果，不一定适合高训练量者（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Endurance vs. Easy: Does TR Treat Them Differently?」#3 / #11 @KonaSS（普通用户）2026-10-18~19，点赞 14 / 13；#9 @jmnourse（普通用户）2026-10-18，点赞 10，https://www.trainerroad.com/forum/t/endurance-vs-easy-does-tr-treat-them-differently/115303
- 依据: 推理；引 TR 自称多数用户每周 3–8h。
- 我的判断: 可靠性 中——"训练数据里出现最多 ≠ 最优"的论证在方法学上成立；与研究: 没有研究（关于 TR 模型本身）。
- 对本人: 适用——任何基于群体数据的处方（含 ICU 指标）都要核对是否适合本人 15–16h/周的量级。

### 反方：TR AI 已算出 74% 最优，偏离必然导致更差结果（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Endurance vs. Easy: Does TR Treat Them Differently?」#8 / #10 @SparkTrain（普通用户）2026-10-18，点赞 0 / 0，https://www.trainerroad.com/forum/t/endurance-vs-easy-does-tr-treat-them-differently/115303
- 依据: 对产品的信任，无数据；#14 JMGant 反驳"训练适应没精确到这种程度"。
- 我的判断: 可靠性 低——绝对化论断、零点赞、无证据；与研究: 冲突（个体反应差异大，见本批次"可重复性"帖）。
- 对本人: 不适用。

### 同一人重复同一耐力训练干预，个体适应幅度的可重复性有限；应多次干预、追踪个人反应再调整（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Limited reproducibility of individual physiological adaptations to repeated endurance exercise training」#1 / #3 @Twowkg（自述有带人训练经验）2026-10-15，点赞 1 / 1，https://www.trainerroad.com/forum/t/limited-reproducibility-of-individual-physiological-adaptations-to-repeated-endurance-exercise-training/115283
- 依据: 发帖人给出的论文链接 https://journals.physiology.org/doi/full/10.1152/japplphysiol.00154.2026（帖子标题即论文题名，发帖人未写作者/年份）；加本人带训经验。#4 @Helvellyn 解读为"训练反应是概率游戏，只有两次干预无法区分"。
- 我的判断: 可靠性 中高。**教练核查（2026-10-26，Europe PMC 摘要）：Odden 等 2026 J Appl Physiol，42 名未训练的中年男女，做了两段相同的 8 周耐力训练，中间停训 8 周；同一个人两次的适应幅度几乎不可重复（VO2max 的组内相关系数 0.19，15 分钟最大平均功率 0.20，血红蛋白量 0.00）。** 与研究: 已核（[研究]）；受试者未训练，推到有训练者要谨慎。
- 对本人: 适用——不能从单个训练块的结果断定"某课型对本人有效/无效"，需要多次重复并结合 ICU 数据追踪。

### 反方/限定：该研究受试者为未训练者，对有训练者的外推有限；训练有素者睡眠、营养、疾病管理更稳定（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Limited reproducibility…」#7 @cartsman（普通用户）2026-10-17，点赞 0，https://www.trainerroad.com/forum/t/limited-reproducibility-of-individual-physiological-adaptations-to-repeated-endurance-exercise-training/115283
- 依据: 对论文方法的转述（称作者在文中也承认此局限）+ "训练计划普遍有效"的经验论证；#11 @psmith 质疑其"赛季间差异不大"的说法缺依据。
- 我的判断: 可靠性 中——受试者类型的转述 [未核实]；"经验上计划有效"不能反驳个体可重复性问题；与研究: 不确定。
- 对本人: 待验证——本人是有训练者，外推需谨慎，但"单块结论不可靠"的提醒仍有用。

### 限定：研究中两次训练阶段所有人都有进步，差异只在幅度；只看短期训练；两阶段处于一年中不同时间（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Limited reproducibility…」#9 @GoLongThenGoHome（普通用户）2026-10-17，点赞 0，https://www.trainerroad.com/forum/t/limited-reproducibility-of-individual-physiological-adaptations-to-repeated-endurance-exercise-training/115283
- 依据: 对论文内容的转述；#8 提到 Scientific Triathlon 播客讨论过此研究，#12 提到 Empirical Cycling "Watts Doc #65: Measuring Training Responsiveness"。
- 我的判断: 可靠性 中——转述 [未核实]；季节混杂的质疑合理；与研究: 不确定。
- 对本人: 适用——"都有进步、幅度不同"意味着坚持有效训练本身可靠，不必因某块进步小就推翻方案。

### 停训/生病后，基于历史数据的处方系统不知道停训情况，会给出偏高的强度；需手动选更容易的课逐步回归（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Hard workouts after training break」#1 @Daninplymouth（普通用户）2026-10-16，点赞 0；#4 @lee82（普通用户）2026-10-21，点赞 0；#5 @ntisdell（普通用户）2026-10-23，点赞 0，https://www.trainerroad.com/forum/t/hard-workouts-after-training-break/115291
- 依据: 个人经历（6 周仅 5–6 次骑行后系统仍给出 SST 高级别课）；其余为 TR 软件操作建议。
- 我的判断: 可靠性 中（原则层面）——历史驱动的模型对场外中断不敏感是普遍问题；与研究: 没有研究。
- 对本人: 适用——本人 6–7 月有过低量与身体不适期，回归时不能直接按停训前的同类课瓦数定处方。
- 补充（2026-11-03）：同帖 #8 @JoeX（普通用户）2026-10-29，点赞 1：不要靠手动调低 FTP 换更轻松的课，应改选更保守的计划档位、短的耐力课或维持计划，户外轻松骑几周。另见 TrainerRoad「How it started, how it's going aka predictions vs reality」#323/#328 @Bones（普通用户，51 岁）2026-10-31：一整个冬天没做结构化训练、只有不带功率和心率的骑行，系统预测 4 周后的 FTP 比他过去 12 个月最好的 20 分钟功率还高 15W；TR 员工 @eddie #329 说只有他掌握完整情况，讨论还没有结论，https://www.trainerroad.com/forum/t/how-it-started-how-its-going-aka-predictions-vs-reality/110892。可靠性 低-中（个案，没有结论）。对本人：再次说明定瓦数看本人实际同类课和近期最好值，不看模型的预测值。
- 补充（2026-11-10）：TrainerRoad「What workout did you do today? (2026)」#643 @McFly（普通用户）2026-11-05，点赞 6，https://www.trainerroad.com/forum/t/what-workout-did-you-do-today-2026/108570 。停了约一个月、只骑 4 次后，AI FTP 检测从 289 W 降到 269 W；按新数做 VO2 课"刚好"、评为 Very Hard，自称按旧数再加 25 W 会撑不住。另见「Hard workouts after training break」#8 @JoeX（普通用户）2026-10-29：要更容易的课，改选保守训练方式、短耐力课或维持计划，不要靠手动压低 FTP。可靠性 中（N=1 自有数据）。对本人：本人不按 FTP 百分比定强度；停训后回归按近期实际同类课重新起步，与本条原意一致。

### 训练日状态差时允许"做完部分组就改成低强度 Z2"，接受部分完成，好于完全不练或硬撑（收录 2026-10-26）
- 来源: [社区] TrainerRoad「Anxiety, depression and structured training」#16 @ELIKESBIKES 2026-06-23 点赞 4；#18 @Neil_Partridge 2026-06-30 点赞 2（"30 分钟 Z2 好过不练"）（均为普通用户）。反方 #17 / #19 @Trix8806 2026-06-24 / 06-30 点赞 0 / 2：不达标可以，但不可"不尽全力"；只有伤病/重大事务才跳课，https://www.trainerroad.com/forum/t/anxiety-depression-and-structured-training/77010
- 依据: 个人经验，双方都是自我管理方式，未引用研究。
- 我的判断: 可靠性 中——两种都是个人心理策略，没有对错。与研究: 没有研究。
- 对本人: 适用（前一种）——与本人"后置训练按体感调整、周六可按反应撤课"一致；但本人的"<1h Z2 不排"规则仍有效，降级时用 ≥60min Z2 而不是 30 分钟。

### 让 LLM "审核这份计划"时，它倾向于顺着计划小修小补，可能看不出明显错误的进阶（收录 2026-11-03）
- 来源: [社区] intervals.icu「AI generated plans and and age」#2/#10 @R2Tom（staff, moderator）2026-06-12 / 06-17，点赞 5/2；#5 @Another_Intervaler（Supporter）2026-06-13，点赞 3；#4 @Gerald M（staff, moderator）2026-06-12，点赞 2，https://forum.intervals.icu/t/ai-generated-plans-and-and-age/130374
- 依据: #10 版主自测（一次，输入未公开）：给模型一份 4 周计划，里面有错误的 VO2 进阶、额外的 9 小时耐力骑，还有一次 3 小时 @90%FTP 的"耐力骑"；模型只建议把这次 3 小时骑改成两周一次，没指出没有恢复、进阶错误。#5：靠谱的 AI 训练产品让 AI 负责交流，计划本身仍用常规算法排。#4：会提问的用户本来就知道自己要什么，AI 基本是给出被问到的东西；新手问不出好问题，拿到错的也看不出来。#2 另提：Fitness 图只是模型，不知道你累不累，累了就休息。
- 我的判断: 可靠性 中——单次自测、细节未公开，但"被要求审核时倾向于确认原方案"和对 LLM 讨好倾向的一般认识一致。与研究：没有研究（帖中未引用）。
- 对本人: 适用（对本项目的 AI 教练）——本项目已有反讨好和"先写依据再出课"的规则；排课的硬约束（每周硬课 ≤2、Crazies 算 1 堂、减量周安排）应由确定性检查把关，不能靠模型自己审自己。不改课表。

### 反方：给模型足够的运动员背景，让它在多份候选里排对错并说出理由，它能认出错误的进阶（收录 2026-11-03）
- 来源: [社区] intervals.icu「AI generated plans and and age」#9 @Ricardo_N_Cabral（Supporter）2026-06-17，点赞 0；#12 @Mustafa742（普通用户）2026-10-30，点赞 1，https://forum.intervals.icu/t/ai-generated-plans-and-and-age/130374
- 依据: 个人经验，没有给测试数据。#9：拿 9 份错误进阶和 1 份正确进阶，让 GPT-5.5、Claude Opus 4.5+ 按正确性打分并解释，模型判断得很好。#12：两人做的其实是两种任务——"审核这份计划"会把计划当作基线，在里面找改进；"结合运动员背景给十份计划排对错"更容易暴露错误；年龄、训练史、目标都会改变什么才算正确的进阶。
- 我的判断: 可靠性 低-中——双方都没有公开测试；#12 帖内夹带一个与话题无关的网站链接，像推广。但"任务的问法会影响模型能不能发现错误"这个区分有道理。与研究：没有研究。
- 对本人: 适用（对本项目）——让 AI 教练复核课表时，问"这份课表违反了哪几条规则或证据"，而不是"这份课表行不行"，同时把本人的背景（DRCC 需求、硬课上限、ACL 史）一起给出。

### 先想清楚要提高什么，再定强度分布：从目标赛事和弱项倒推，不要先选"金字塔/极化/甜点"再套进去（收录 2026-11-10）
- 来源: [社区] TrainerRoad「Suggested Off-Season Winter Training - Pyramidal, Polarized or Sweet Spot?」#4 @Helvellyn（普通用户）2026-11-09，点赞 1；#2/#6 @Twowkg（普通用户）2026-11-09 / 11-10，点赞 2/0，https://www.trainerroad.com/forum/t/suggested-off-season-winter-training-pyramidal-polarized-or-sweet-spot/115651
- 依据: 观点，未引用研究。#4：先回答"现在在哪、要到哪、什么时候、短板是什么"，这些决定总量怎么起伏、什么时候拉哪个强度杠杆；#6：先定要提高的生理能力，再选能带来这些适应的课，从目标赛事倒推大周期和小周期；还要有反馈回路，确认课真的产生了预期效果。
- 我的判断: 可靠性 中——属于常见教练原则，与 [[coach-standard]] 第 1 条"比赛需求模型"一致；强度分布作为结果而不是出发点，这一点本身没有研究在帖中支撑。与研究：没有研究（帖中未引用）。
- 对本人: 适用（已在执行）——当前课表按 DRCC 需求（长坡持续、团里拉扯、终点坡）倒推，"反馈回路"对应每堂课后的复盘。不改课表。

### 时间表不规则时，按 4 周为单位排：先数出 4 周内的硬课、轻松课、耐力骑总量，再按可用日摆放；硬课不要挤在 10 天内，找一段 4–5 天没有硬课的作为恢复（收录 2026-11-10）
- 来源: [社区] TrainerRoad「Varied schedule」#6 @Helvellyn（普通用户）2026-11-06，点赞 2；#3 @McFly（普通用户）2026-11-06，点赞 0，https://www.trainerroad.com/forum/t/varied-schedule/115526
- 依据: 个人做法（本人也是轮班工作者）。#6：不要按单周排，4 周内的总量摆好就行；可用日不够时把两次耐力骑合成一次更长的（两次 90 分钟 → 一次 2.5–3 小时，功率大致不变）；"最重要的是累计做功量，而且要渐进"。#3：按"比较好的一周"能做的量来设，不按最好或最差的一周；工作很累的那周训练让路，"负荷就是负荷"。
- 我的判断: 可靠性 中——经验做法，逻辑合理；"两次短骑合并成一次长骑效果相当"没有给依据[未核实]。与研究：没有研究（帖中未引用）。
- 对本人: 部分适用——本人周一周二晚上有课、有时朋友来访，打乱的周可以按 2–4 周总量来平衡，不必每周凑齐同样结构。与本库"一周被打乱时先砍硬课，保留轻松量"一致。不改课表。

### 只有连续 5 天能骑：硬课放第 2 天和第 4 天，中间那天短而真正轻松或不骑；周末两天休息不一定能清空 5 天累积的疲劳（收录 2026-11-10）
- 来源: [社区] TrainerRoad「How should I structure my training with 5 consecutive weekdays available?」#3 @Smart_Era（普通用户）2026-11-06，点赞 1；#6 @lee82（普通用户）2026-11-07，点赞 2；#2 @Trix8806（普通用户）2026-11-06，点赞 1，https://www.trainerroad.com/forum/t/how-should-i-structure-my-training-with-5-consecutive-weekdays-available/115550
- 依据: 个人经验。#3：周一耐力、周二硬、周三很轻或休、周四硬、周五耐力；如果周四质量下降或疲劳带进下一周，先缩短/取消周三、缩短周五，或当周只留一堂硬课。#6（反方向的体验）：5 天练、2 天连休反而方便扛高负荷，因为连休两天后能放开练；先只骑耐力 1–2 周，证明扛得住量再加强度。#2：自己多数周只练 4 天（2 堂 90 分钟间歇 + 1 次耐力 + 1 次 3.5–5 小时长骑），到顶了再加一次耐力骑。
- 我的判断: 可靠性 中——几位都是经验，彼此有分歧（连休两天够不够恢复），没有数据。与研究：没有研究（帖中未引用）。
- 对本人: 参考——本人是"五骑两休"（周一、周五休），每周硬课 ≤2 且 Crazies 算 1 堂，已经是两硬之间隔开的结构。"质量下降先砍中间的轻松骑和次长骑"可作为执行时的调整顺序。不改课表。
