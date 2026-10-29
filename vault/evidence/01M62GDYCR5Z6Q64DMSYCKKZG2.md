+++
ulid = "01M62GDYCR5Z6Q64DMSYCKKZG2"
title = "说法核查：阈值间歇约等于 FTP 的 93–105%——区间无出处，用它反推 FTP 无依据"
authors = ["本项目说法核查"]
year = 2026
source = "说法核查卡，出处见正文"
tags = ["claim_check", "ftp", "threshold_intervals", "power_zones", "back_calculation"]
phase = ["base", "build", "peak", "competitive"]
applies_to = []
finding = "本轮核对的来源里都没有“93–105%”；最接近的是 Coggan 分区 Level 4（乳酸阈）平均功率 91–105% FTP、每组 10–30 min，IF 表中 lactate threshold intervals 0.95–1.05，以及 TrainerRoad 的 Threshold 95–105% FTP——都是教练分区约定，没有给出数据；本轮核对的来源都没有提出用阈值间歇的功率除以这个区间来反推 FTP。研究显示 FTP 与 MLSS、与可维持时长的关系都因人而异。"
dosing_hint = "可以说“阈值区按 Coggan 的约定是 91–105% FTP（或 TrainerRoad 的 95–105%），这是分区约定、不是实验结论”；不得用间歇功率反推 FTP，也不得把任何百分比当作本人的阈值换算系数。"
contraindications = []
status = "active"
superseded_by = ""
topic = "t1"
card_kind = "claim_check"
doi = "-"
pmid = "-"
study_type = "说法核查"
evidence_level = "专家意见"
read_level = "摘要级"
verified = "2026-10-29 对抗核查：已修改 6 处（“没有任何来源”限定为本轮核对范围 3 处、TrainerRoad 标题与审阅人和日期、F04 合并推论标［推断］、F08 补注 120% 的 4/2 min 间歇方案）"
+++

# 说法核查：阈值间歇约等于 FTP 的 93–105%

## 说法

“阈值间歇课约等于 FTP 的 93–105%”，并据此由阈值间歇的功率反推 FTP。2026-10-28 教练把“3×10–12 min ≈ FTP 的 100–105%、4×15 min ≈ 93–97%”标成［经验换算］用来反推 FTP，本人质疑后承认没有来源并作废（vault/sessions/2026-10-28-indoor-lsd-review.md）。

## 判定

**区间本身无出处；用它反推 FTP 无依据。** 有出处的只是相近的教练分区约定（91–105% 或 95–105%），这些约定没有给出实验数据；本轮核对的来源（包括 Coggan 的两篇文章）都没有提出用间歇功率除以区间来反推 FTP。

## 出处追查

以下网页均于 2026-10-29 直接抓取原文逐字核对，原文存于 icu/icu_data_warehouse/9_Coach_Raw/2026-10-28-evidence-t1-search/web/（git 忽略）。

| 来源 | 写了什么 | 它给的依据 |
|---|---|---|
| Andrew Coggan，“Cycling Power Zones Explained”，TrainingPeaks，2016-04-29 发布 | Level 4 Lactate Threshold：平均功率 91–105% FTP；训练中通常做成多组 10–30 min | 未给数据；分区数量 somewhat arbitrary |
| Andrew Coggan，“Normalized Power, Intensity Factor and Training Stress Score”，TrainingPeaks，2016-02-10 发布 | 典型 IF 0.95–1.05：lactate threshold intervals（只算工作段）、较短（<2.5 h）公路赛等 | 只写 “Typical IF values”，无来源 |
| 同上 | 唯一的“反向”用法：约 1 h 的比赛 IF 超过 1.05，往往说明软件里设的阈值功率偏低 | 经验提示，单向，只针对约 1 h 的比赛 |
| TrainerRoad，“Cycling Power Zones: Training Zones Explained”（博客；Coach Jonathan Lee 审阅，2021-05-14，2026-07-22 更新） | Threshold 95–105% FTP；Sweet Spot 88–94% FTP；称分区“基于 Coggan 的研究” | 参考文献只列 Allen & Coggan《Training and Racing With a Power Meter》第 2 版（2010），未指明哪项研究给出哪个百分比 |

要点：网页里没有出现 93 这个下限；91–105% 与 95–105% 都是分区约定。

## 研究证据

- F02（01M62GDYC898KPJFV0DGG8X1QT，Sitko 2022）：在估计的 FTP 上骑到力竭，中位数 35–51 min，随水平变化——同样“100% FTP”对不同人能维持的时间不同。
- F03（01M62GDYC9KT928FDXD3PNZS46，Inglis 2020）：MLSS 平均只有 FTP95% 的 93.1%，个体差可达数十瓦，训练后 MLSS 升高而 FTP 测试没反映。
- F04（01M62GDYCAVA7ND2NC35K8HHRV，Borszcz 2019）：FTP 与 MLSS 平均只差 1.4%，但 95% 一致性界限 ±9.2%；作者结论与 F03 相反。［推断］两篇合起来看：即使平均接近，个体误差也可达约 ±10%（F04 的 95% 一致性界限为 ±9.2%）。
- F08（01M62GDYCERWYEN6A4CPB00ZGJ，Bossi 2023）：按 20 min 计时功率的 120% 做 4 min 工作、2 min 恢复的间歇到力竭（强度高于阈值区），力竭时间的个体间变异系数 59.1%；四种按百分比定强度的方法在 44.2–59.1% 之间，都不能让个体反应一致。
- F01（01M62GDYC7QX98EX03J8W8EFK4，Sitko 2023）：连“20 min × 0.95 = 60 min 功率”的系数都随水平在 0.88–0.96 之间变化。
- 能坚持多久取决于组长、组数、恢复和个人特点；一个固定区间无法把间歇功率还原成 FTP［推断，基于以上各卡］。

## 教练以后应该怎么说

- “阈值区 91–105%（或 95–105%）是 Coggan 等人的分区约定，不是实验结论；我不用间歇功率反推 FTP。”
- “判断阈值附近的能力，比较你自己同类课（同样组长、同样恢复）的功率和 RPE 走势。”
- “本项目不做全力 FTP 测试、定强度不按 FTP 百分比（vault/athlete-quick-facts.md）；需要估阈值时，说明用的是哪种方法和它的误差。”

## 核查记录

- 2026-10-29 写卡：教练资料于 2026-10-29 直接抓取网页原文逐字核对；研究证据引自 F01–F04、F08。read_level 记为摘要级，因 F01、F02、F04 只读到摘要。
- 2026-10-29 对抗核查（独立复核）：Coggan 两篇和 TrainerRoad 原文的数字、日期逐条核对，无误，网页都没有 93；session 原句对得上。订正：finding/判定中“没有任何来源”改为“本轮核对的来源”；TrainerRoad 标题改为原页标题，补审阅人和日期；F04 合并推论标［推断］；F08 注明 59.1% 来自 120% 的 4/2 min 间歇（高于阈值区）。
