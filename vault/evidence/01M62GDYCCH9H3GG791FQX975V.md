+++
ulid = "01M62GDYCCH9H3GG791FQX975V"
title = "CP 与 MLSS 的差距：只在功率上 CP 平均高约 12 W，个体差值范围宽"
authors = ["Micheli L", "Lucertini F", "Grossi T", "Pogliaghi S", "Keir DA", "Ferri Marini C"]
year = 2025
source = "PeerJ 13:e19060; doi:10.7717/peerj.19060"
tags = ["critical_power", "maximal_lactate_steady_state", "heavy_severe_boundary", "intensity_domains", "limits_of_agreement", "individual_variability", "meta_analysis", "threshold_agreement"]
phase = ["base", "build", "peak", "competitive"]
applies_to = []
finding = "10 项研究（111 人，除 1 项跑台外均为功率车）的 meta 分析：只有以功率表示时 CP 显著高于 MLSS（平均差 12.42 W，95% 一致性界限 −19.23 至 44.08 W），以摄氧量、心率、血乳酸表示时差异不显著；个体差值离散大，作者认为二者在个人层面不宜互换。"
dosing_hint = "可用来说明：群体平均上 CP 略高于 MLSS 功率，但单个人的差值可正可负、跨度达数十瓦。不能用一个固定瓦数把 CP 换算成 MLSS；不能把本文实验室多次力竭测试拟合的 CP 直接等同于平台从日常功率曲线估出的 CP 或 FTP；不能把其他指标「差异不显著」当作二者等价的证据。"
contraindications = []
status = "active"
superseded_by = ""
topic = "t1"
card_kind = "finding"
doi = "10.7717/peerj.19060"
pmid = "40124604"
study_type = "系统综述与 meta 分析（随机效应模型、Bland–Altman meta 分析、meta 回归）"
evidence_level = "中"
read_level = "全文"
verified = "2026-10-29 对抗核查：已修改 3 处（meta 回归 10 个点来自 9 项研究；方法依赖一句补［推断］；删去无来源的本人水平描述）"
+++

# CP 与 MLSS 的差距：只在功率上 CP 平均高约 12 W，个体差值范围宽

## 结论

- 研究问题：CP（临界功率，由多次力竭测试的功率–时间关系拟合）和 MLSS（最大乳酸稳态，30 min 恒功率下血乳酸不持续上升的最高强度）都被用来标定 heavy 与 severe 强度域的分界。本文用 meta 分析比较二者的平均差和个体一致性。
- 测得（原文结果）：
  - 以功率表示：CP 平均比 MLSS 高 12.42 W，差异显著，研究间异质性也显著。摘要原话：「solely when expressed in PO, CP was higher than MLSS」。
  - 以摄氧量、心率、血乳酸表示：平均差都不显著；其中心率和血乳酸各只有 3 项研究。
  - 一致性：四种指标的 95% 一致性界限都很宽，功率为 −19.23 至 44.08 W。作者据此认为个体间差异大，在个人层面用一个预测另一个可能误差很大。
  - meta 回归：研究平均 CP 或 MLSS 功率越高，该研究的 CP−MLSS 功率差越大。这是研究层面（10 个组均值点，来自 9 项研究，Caen 2022 分两组；Puga 2009 不在功率分析内）的关系。
- 作者的解释（假说，本文没有检验）：CP 测试要求真正力竭，体能更好、更熟悉极限用力的人可能测出更高的 CP，而 MLSS 测试不需要力竭，于是差值变大。
- 作者在 Discussion 引述 Caen 2022、Iannetta 2022 等认为：CP 与 MLSS 的测定方法更严格时，二者差值可以小到实际可忽略。［推断］所以 12.42 W 这个平均值很可能随各研究的测定方法而变；本文未能用方法类调节变量检验这一点（Discussion 限制段）。
- ［推断］其他指标「差异不显著」不等于「二者相同」：摄氧量和血乳酸平均差的 95% CI 都较宽；作者也指出，提供这些内部负荷数据的研究恰好是功率差值较小的几项。
- 摘要和结论写了「更年轻者差值更大」，但正文结果只报告了以 CP、MLSS 功率为调节变量的 meta 回归，没有年龄的 meta 回归；纳入研究的平均年龄都在 21.5–28 岁之间。「更年轻」这一点在本文中无法核实。

## 数字与原文位置

| 数字 | 原文位置 | 备注 |
|---|---|---|
| PROSPERO 注册号 CRD42021261155 | Methods「Protocol and registration」 | 按 PRISMA 报告 |
| 检索截至 2023 年 3 月 | Methods「Search strategy」 | PubMed、Web of Science、Scopus |
| 纳入标准：18–65 岁健康成人 | Table 1；Methods「Inclusion and exclusion criteria」 | 须在 CP 与 MLSS 两个强度下都做过恒定强度试验 |
| 检出 782 篇，全文筛选 337 篇，纳入 10 篇 | Results「Studies and participants characteristics」；Fig. 1 | |
| 共 111 名受试者，其中女性 19 名 | Results「Studies and participants characteristics」；Discussion | 女性人数见 Discussion |
| 各研究平均年龄 21.5–28 岁 | Table 2 | 各研究均值中的最小与最大 |
| CP 力竭测试时长 1–20 min（各研究不同）；MLSS 稳态判定窗口 10–30 min（Iannetta 2019 为 15–30 min） | Table 2 | CP 模型有 2 参数、3 参数双曲线和 best fit |
| 各研究 CP−MLSS 功率平均差 1.0–30.0 W | Table 3 | 不含以跑台速度百分比表示的 Puga 2009 |
| Ozkaya 2022（Well-trained cyclist，10 人）30.0 ± 10.9 W；Caritá 2009（Cyclist，6 人）26.5 ± 7.4 W；Iannetta 2022（Recreationally cyclists，10 人）15.0 ± 13.2 W | Table 2、Table 3 | 研究层面数值 |
| 功率平均差 12.42 W（95% CI 4.69–20.16，p = 0.005；预测区间 −11.62 至 36.47） | Results「Meta-analyses of the mean differences」；Fig. 3；摘要 | 异质性 Q(9) = 96.490，τ = 10.065 W，p < 0.001 |
| 敏感性分析（同时报告功率与摄氧量的研究）：10.59 W（95% CI −4.34 至 25.51；预测区间 −24.15 至 45.32） | Results「Meta-analyses of the mean differences」（引补充材料 SDC2） | 该子集 CI 跨 0 |
| 摄氧量平均差 0.09 L·min⁻¹（95% CI −0.02 至 0.21，p = 0.097） | Results「Meta-analyses of the mean differences」；Fig. 4；摘要 | Q(5) = 15.238，p = 0.009 |
| 心率平均差 0.61 bpm（95% CI −7.70 至 8.91，p = 0.784） | Results「Meta-analyses of the mean differences」；Fig. 5；摘要 | 3 项研究 |
| 血乳酸平均差 1.63 mM（95% CI −2.61 至 5.86，p = 0.240） | Results「Meta-analyses of the mean differences」；Fig. 6；摘要 | 3 项研究；Q(2) = 24.352，p < 0.001 |
| 95% 一致性界限：功率 −19.23 至 44.08 W（界限的外侧 95% CI −30.91 至 55.76） | Results「Analysis of agreement」；Fig. 8；摘要 | 差值方向为 CP 减 MLSS |
| 95% 一致性界限：摄氧量 −0.34 至 0.52 L·min⁻¹；心率 −15.84 至 17.05 bpm；血乳酸 −2.85 至 6.11 mM | Results「Analysis of agreement」；Fig. 8；摘要 | |
| meta 回归斜率：CP（W）B = 0.21（95% CI 0.107–0.314，p = 0.002）；MLSS（W）B = 0.243（95% CI 0.078–0.408，p = 0.009） | Table 5 | 调节变量检验：CP F(1,8) = 21.091，p = 0.002；MLSS F(1,8) = 11.114，p = 0.010（Results「Meta-regressions analysis on the mean difference」；摘要用的是后者） |
| ［换算］研究平均 CP 每高 10 W，研究平均 CP−MLSS 差约大 2.1 W | 由 Table 5 斜率计算 | 0.21 × 10 W = 2.1 W；研究层面关系，不能代入个人 CP |
| 标准化均数差：功率 0.648（95% CI −0.189 至 1.485，p = 0.098）；摄氧量 0.482（95% CI −0.044 至 1.007，p = 0.064） | Results「Meta-analyses and comparisons of the standardized mean differences expressed in W and L⋅min−1」 | 只用 4 项研究、5 个效应量（Discussion） |
| 偏倚风险：「分配隐藏」10 项全为 high；「随机顺序」7 项 high、3 项 unclear | Table 4 | 自 Table 4 逐项计数 |
| 引述 Caen et al. (2022)：42 次比较中只有 3 次 CP 与 MLSS 相差超过 10 W | Discussion | 二手引述，不是本 meta 分析的结果 |
| 引述 Maturana et al. (2016)：13 人中只有 1 人在 CP 功率骑行时血乳酸稳定 | Discussion | 二手引述 |

## 研究对象

- 10 项交叉或受试者内设计研究，纳入条件是在 CP 与 MLSS 两个强度下都做过恒定强度的长时间运动（指标直接测得，不从递增测试外推）。
- 111 名健康成人，纳入标准 18–65 岁，实际各研究平均年龄 21.5–28 岁；女性 19 名。受试者描述包括健康年轻人、大学生、体育专业学生、休闲训练者、自行车手（Table 2）。
- 除 Puga 2009 用跑台外，都在功率车上测。CP 由 2 参数、3 参数双曲线或 best fit 模型拟合；MLSS 用多次 30 min 恒功率试验判定（Table 2）。
- 全文没有讨论环境温度或热环境。

## 证据强度

中。理由：

- 有 PROSPERO 注册、按 PRISMA 报告的系统综述与 meta 分析，但只有 10 项研究、111 人，以年轻人为主，女性只有 19 名。
- 各研究的 CP 模型、力竭测试时长、MLSS 判定标准不一致，功率差的异质性显著（τ = 10.065 W）；作者自己提示结果需要谨慎解读。
- 心率和血乳酸的结论各只来自 3 项研究；作者指出提供这些数据的研究恰是功率差值较小的研究。
- 偏倚风险表中 10 项研究的「分配隐藏」都评为 high。
- 平均差值的大小随测定方法变化（Discussion 引述的严格方法研究差值很小），不满足「与近三年研究一致」的强证据条件。
- 相对可靠的部分：功率平均差为正、个体一致性界限宽。较弱的部分：「其他指标无差异」和「更年轻者差值更大」。

## 对本人适用性

- 本人自分类爬坡手（vault/athlete.md），在新加坡湿热户外训练。本文受试者以年轻人、实验室功率车测试为主。受试者被描述为自行车手的三项研究平均差值为 30.0 W（Ozkaya 2022，10 人）、26.5 W（Caritá 2009，6 人）和 15.0 W（Iannetta 2022，10 人），都是研究层面的数，不能当作本人的差值。
- 本文用研究平均 CP、MLSS 的绝对功率（W）代表体能，没有按体重换算（Discussion）。［推断］用到本人时，「体能更好、差值更大」该按绝对功率还是相对功率理解，本文无法回答。
- 本文的 CP 来自实验室多次力竭恒功率测试拟合。平台从日常骑行功率曲线估出的 CP 或 eFTP 与 MLSS 的关系，本文没有检验［推断：测定方法不同，12.42 W 和一致性界限都不能直接套用］。本人的 CP 估计值读 coach_memory/athlete_snapshot.json；本文不能用来由它推算本人的 MLSS。
- 心率：CP 与 MLSS 的平均心率差接近 0（0.61 bpm），但一致性界限为 −15.84 至 17.05 bpm，且只基于 3 项研究。［推断］不能用一个心率数值替本人定位 heavy/severe 边界。
- 本文结论对应实验室测功车条件，没有涉及热环境；户外湿热条件下 CP、MLSS 的位置是否改变，本文不能回答（热环境另见 01M62GDYCJMT5C5PHZ0X1G7PF5）。
- 教练讲到「CP 就是最高可持续稳态」时，按本卡应改说：群体平均上 CP 比 MLSS 高约 12 W，个人差值不确定、可正可负。

## 与其他卡片的关系

- 支持 01M62GDYCD89WECKXWHZXYCCVF（Iannetta 2020）：方向一致，用单一标尺（最大值的固定百分比，或 CP）定位个人强度域边界，个体误差都大。本文引用了 Iannetta 2020（2026-10-29 用 Europe PMC 引用索引核对：CITES:31479001_MED 的结果包含 PMID 40124604）。
- 部分支持 01M62GDYCERWYEN6A4CPB00ZGJ（Bossi 2023）：方向一致，以 CP/W′ 为基准的处方在个体间也不稳定；但该研究的 CP 来自 3 min 全力测试，研究对象是 CP 以上的力竭间歇，不是 CP 与 MLSS 的比较。

## 核查记录

2026-10-29 写卡：依据全文（Europe PMC fullTextXML，PMC11927562，本地文本 D:/Cycling/icu/icu_data_warehouse/9_Coach_Raw/2026-10-28-evidence-t1-search/fulltext/PMC11927562_Micheli2025.txt；补充材料 SDC1–SDC3 与图片未读，文本中无参考文献表）
- 2026-10-29 对抗核查（独立复核；PubMed 40124604 书目一致；Europe PMC 全文逐项核对；lit.py refs 确认参考文献含 Iannetta 2020 MED:31479001；全文无温度或热环境字样）：其余数字与位置核对无误；改 3 处——meta 回归 10 个点来自 9 项研究（Caen 2022 两组，Puga 2009 不在功率分析内）；「12.42 W 依赖测定方法」补［推断］并注明本文无法检验方法类调节变量；删去 vault 无记录的「业余高水平」。
