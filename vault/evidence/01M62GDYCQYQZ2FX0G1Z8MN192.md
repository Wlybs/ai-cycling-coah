+++
ulid = "01M62GDYCQYQZ2FX0G1Z8MN192"
title = "说法核查：4 小时稳态约等于 FTP 的 70–78%——无来源"
authors = ["本项目说法核查"]
year = 2026
source = "说法核查卡，出处见正文"
tags = ["claim_check", "ftp", "long_ride", "endurance_intensity", "durability", "no_source"]
phase = ["base", "build", "peak", "competitive"]
applies_to = []
finding = "本轮检索到的研究文献和逐字核对的教练资料里，都没有“4 小时稳态 = FTP 的 70–78%”这个说法；数字上最接近的是铁人三项全程比赛骑段的 IF 建议（如 0.68–0.78，IF = NP/FTP，且是比赛配速）、Coggan 耐力区的平均功率 56–75% FTP（不按时长定义）和 Coggan 列出的耐力训练骑典型 IF 0.75–0.85，都没有给出数据来源，也都不是“4 小时训练骑的可持续功率”。"
dosing_hint = "不得再用这个比例计算或反推 FTP；长骑强度以本人同类长骑的实际数据为准。可以引用的是：长骑中 VT1 功率会下降、同功率心率会上升（F09、F10），以及固定百分比对不上个人阈值（F07）。"
contraindications = []
status = "active"
superseded_by = ""
topic = "t1"
card_kind = "claim_check"
doi = "-"
pmid = "-"
study_type = "说法核查"
evidence_level = "无来源"
read_level = "摘要级"
verified = "2026-10-29 对抗核查：已修改 7 处（检索范围措辞 3 处、finding 补列 Coggan 耐力骑 IF 0.75–0.85、F09 方案订正并把 FTP 结论标［推断］、F01/F02 外推标［推断］、Rothschild 说法降为递增测试中的相关）"
+++

# 说法核查：4 小时稳态约等于 FTP 的 70–78%

## 说法

“4 小时稳态（匀速长骑）约等于 FTP 的 70–78%。”2026-10-28 教练曾标成［经验换算］用来由长骑功率反推 FTP，本人质疑后当场承认没有来源并作废（vault/sessions/2026-10-28-indoor-lsd-review.md）。

## 判定

**无来源。** 本轮检索到的研究和核对的教练资料里，都没有把“4 小时稳态训练骑”和“FTP 的 70–78%”配在一起。数字上相近的几个来源说的是别的东西（见下），而且都没给数据依据。

## 出处追查

以下网页均于 2026-10-29 直接抓取原文逐字核对，原文存于 icu/icu_data_warehouse/9_Coach_Raw/2026-10-28-evidence-t1-search/web/（git 忽略）。

| 来源 | 写了什么 | 它给的依据 |
|---|---|---|
| Andrew Coggan，“Cycling Power Zones Explained”，TrainingPeaks，2016-04-29 发布（2026-07-18 更新） | Level 2 Endurance：平均功率 56–75% FTP，描述为 “All day” pace / 经典长距离慢骑（LSD）；没有按 4 h 给出数字 | 未给数据；文中说分区数量的划分 somewhat arbitrary |
| Andrew Coggan，“Normalized Power, Intensity Factor and Training Stress Score”，TrainingPeaks，2016-02-10 发布 | 典型 IF：0.75–0.85 为 endurance-paced training rides；0.85–0.95 含 longer (>2.5 h) road races | 只写 “Typical IF values”，无来源；IF = NP / FTP，不是平均功率占 FTP 的比例 |
| Joe Friel，“How to ‘Cheat’ by Using a Power Meter in an Ironman”，TrainingPeaks，2012-10-30 发布 | 用 Rick Ashburn 的表：准备充分的年龄组运动员 6 h 骑段 IF 67–69%；职业男子冠军骑段 IF 约 80% | Ashburn 的表（未公开数据来源）和作者经验 |
| Anthony Walsh，“What Wattage Should You Ride in an Ironman?”，Roadman Cycling，2026-04-16 发布 | 多数年龄组铁三全程 180 km 骑段 IF 0.68–0.78（按 NP 计） | 未引研究 |
| Dave Schell，“IRONMAN Bike Pacing: Dialing In Your Intensity Factor and TSS Targets”，Best Bike Split，2026-08-31 | 全程铁三年龄组骑段 IF 0.65–0.75，多数人 0.68–0.72 | TSS 区间来自 Rick Ashburn 的表（Copyright 2008） |

要点：
- 与 70–78% 最接近的是铁三全程**比赛**骑段的 IF 建议。那是骑完还要跑马拉松的比赛配速，用的是 IF（标准化功率 NP 除以 FTP），不是平均功率，也不是“4 小时能稳住的最高功率”。
- Coggan 的耐力区（56–75%）是一个训练分区，不是“4 小时可持续功率”的定义。

## 研究证据

- 本主题检索（PubMed、Europe PMC，2026-10-28/29）未找到测过“4 小时可持续功率占 FTP 的比例”的研究。
- F09（01M62GDYCFCD95QVVJW9EXA792，Gallo 2024）：12 名受训车手按首访测得 VT1 功率的 90% 反复骑 30 min 段（每小时穿插一次递增测试，上限 6 h），力竭时间 234 ± 66 min；VT1 功率 1 h 时不变、力竭前显著下降，11/12 人呈非线性（二次曲线）。［推断］长时间能维持的强度与 VT1 及其下移有关；该研究没有测 FTP，不能由它得出任何 FTP 比例。
- F10（01M62GDYCG42SGPFDFX4SJ5414，Rothschild 2025）：约 2.5 h 骑行后 VT1 功率下降，且下降幅度与同功率心率上升强相关。
- F07（01M62GDYCD89WECKXWHZXYCCVF，Iannetta 2020）：最大值的固定百分比与个人阈值对应很差。
- F01（01M62GDYC7QX98EX03J8W8EFK4，Sitko 2023）与 F02（01M62GDYC898KPJFV0DGG8X1QT，Sitko 2022）：连 FTP 本身与 60 min 功率的关系、在 FTP 上能骑多久都因人、因水平而异，［推断］更谈不上一个通用的“4 h ≈ FTP × 系数”。

## 教练以后应该怎么说

- “我没有‘4 小时 = FTP 的某个百分比’的来源，不用它推 FTP，也不用它定长骑功率。”
- “长骑强度看你自己同类长骑的数据：同一功率下心率怎么走、补给和环境条件是否相同。”
- “研究发现，长骑后的递增测试里同一功率下心率升高越多，VT1 功率下降越多（Rothschild 2025）；骑行中软件算的前后半程脱钩是否同样对应，作者说此前没人检验过。”

## 核查记录

- 2026-10-29 写卡：教练资料于 2026-10-29 直接抓取网页原文逐字核对；研究证据引自 F01、F02、F07、F09、F10。read_level 记为摘要级，因 F07 只读到摘要。
- 2026-10-29 对抗核查（独立复核）：5 个网页的作者、日期、数字逐条对照保存原文，无误；session 原句与作废记录对得上。订正：finding/判定/研究证据里“研究没有”改为“本轮检索未找到”；finding 补列 Coggan 耐力训练骑典型 IF 0.75–0.85；F09 方案改为首访 VT1 的 90%，并把 FTP 结论标［推断］；F01/F02 外推标［推断］；Rothschild 说法改为递增测试中的相关，注明软件脱钩未检验。另：read_level 为摘要级的理由应是 F01、F02、F07 都只读到摘要。
