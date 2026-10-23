---
date: 2026-10-21
tags: [coach-session, nutrition, vitamin-a, food-storage]
related: [[athlete]] [[sessions/2026-10-21-supplements-and-condiment-storage]]
---

# 2026-10-21 ｜ 澳洲牛肝150g每周与500g一周的实际食谱估算

## 用户请求与新增事实
用户质疑从每周一次改为每月一次未按本人食谱计算，要求算150g牛肝每周一次长期是否过量、加工能否减轻、若一周吃完500g有何反应。
本人确认：500g为冷冻重量，尚未解冻，怀疑冷冻室不到−18°C；澳洲产、FairPrice购约SGD5、品牌al开头。常见餐单仅参考，日常不完全相同；训练日两顿各2–3蛋、早餐2蛋及约300ml脱脂酸奶，不能当作已记录的完整7日摄入。
FairPrice有匹配产品Al-Baqa Frozen Beef Liver Cubes 500g、澳洲产，但未获本人最终确认具体品牌；网页未提供该批次维A化验。商品链接：https://www.fairprice.com.sg/product/al-baqa-frozen-beef-liver-cubes-500g-11218988 。未把网页价格当本人实付价。

## 数据证据与出处
本轮为同一营养会话续问，沿用本会话成功sync，未使用FTP/体重/PB作维A计算。先读现行饮食plan，后以新获取的澳洲官方食品数据计算，不依据主观耐受上调UL。

官方AUSNUT 2023下载页（页尾更新2026-03-25）：https://www.foodstandards.gov.au/science-data/food-nutrient-databases/ausnut/data-files
原始Excel和算术JSON：`/mnt/d/Cycling/icu/analysis/2026-10-21-liver-vitamin-a/`。

### Food nutrient profiles（每100g可食部）
文件：ausnut-food-nutrients.xlsx，工作表Food nutrient profiles，标题第3行，AB列为Preformed vitamin A (retinol) (ug)。
- 第2003行，Survey ID18401001 / F000619，Beef, liver, raw：视黄醇13600µg/100g，蛋白20g/100g。
- 第2004行，18401002 / F000620，Beef, liver, cooked：视黄醇19200µg/100g。不同生熟条目的每100g浓度不可直接当加热损失率，烹调失水会改变重量。
- 第1645行，17101003 / F003721，Egg, chicken, whole, hard-boiled：视黄醇130µg/100g。
- 第2271行，19202005 / F009688，Yoghurt, natural, low fat (<0.5%)：视黄醇0µg/100g。仅作未强化脱脂酸奶参照，不认证本人品牌等于零；本人维A强化标签未知。

原始下载：https://www.foodstandards.gov.au/sites/default/files/2025-09/AUSNUT%202023%20-%20Food%20nutrient%20profiles.xlsx?v=20250903

### 采样与外推限制
ausnut-food-details.xlsx / Food details，第2004行F000619：多数营养数据来自1985年悉尼超市/肉铺购买的7个生牛肝样本；部分其他营养素借用USDA。维A数据为官方现行参考，但不是当前Al-Baqa产品检测，不因数据库名称2023而声称采样发生于2023。
原始下载：https://www.foodstandards.gov.au/sites/default/files/2026-03/AUSNUT-2023-Food-details-4.xlsx

### Nutrient retention factors
ausnut-retention.xlsx / Nutrient retention factors，标题第3行。
- 第3558行，factor116 Liver, fried，Preformed vitamin A (retinol)：0.75。
- 第3622行，factor118 Liver, simmered, with drippings：0.80。
- 第3654行，factor119 Liver, simmered, without drippings：0.75。
- 第3590行，factor117 Liver, reheated：1.00。
这些是食谱估算系数，不是用户烹饪的实测去除率。另列100%保留为不计损失的敏感性情景；75–100%不是统计置信区间或保证范围。
原始下载：https://www.foodstandards.gov.au/sites/default/files/2025-08/AUSNUT%202023%20-%20Nutrient%20retention%20factors.xlsx?v=20250829

## 算术与完整性边界
按每蛋50g可食部的假设，每天6–8蛋→视黄醇390–520µg/day；是常见日的假设，不是实测周均。冷冻净肉重近似生重，未计冰衣、修整或包装误差。饭、蔬果类胡萝卜素不计入预成维A UL；其他肉类、本人酸奶与面包强化成分等未完整实测。

公式：周均视黄醇＝牛肝生重g/100×13600×保留系数/7＋鸡蛋背景。

| 食用安排 | 牛肝保留系数 | 牛肝每周视黄醇µg | 牛肝＋蛋周均µg/day |
|---|---:|---:|---:|
| 150g/周 | 0.75 | 15300 | 2576–2706 |
| 150g/周 | 0.80 | 16320 | 2721–2851 |
| 150g/周 | 1.00 | 20400 | 3304–3434 |
| 500g/周 | 0.75 | 51000 | 7676–7806 |
| 500g/周 | 0.80 | 54400 | 8161–8291 |
| 500g/周 | 1.00 | 68000 | 10104–10234 |

周均是长期摄入筛查工具，不是允许把7天UL集中吃下的安全认证。成人预成维A UL为3000µg/day。NIH ODS Vitamin A专业版，Table3及Health Risks段：https://ods.od.nih.gov/factsheets/VitaminA-HealthProfessional/

## 本轮判断与处方（覆盖之前机械“每月一次”）
- 150g生牛肝/周按澳洲平均值及常规烹调模型，已知食物周均接近UL，未必超；不计损失则略超。无法保证其实际长期低于UL，也不能直接断言必然中毒。明确撤回“没有计算就把每月一次作为唯一默认”的做法，改为基于本人食谱的边界。
- 若希望给批次/其他食物留余量，可选100g/周，或保留150g单份、隔10–14天一次。这是按平均值的较有余量操作选择，不是实测个人安全剂量。100g/周即便不计损失，加上述蛋背景约2333–2463µg/day；150g每10天不计损失+蛋约2430–2560µg/day。
- 500g一周分几餐吃完，不等于一定出现急性维A中毒。按澳洲平均及保留系数，摄入约51–68mg预成维A/周，明显高于长期建议水平。不能给出个人症状发生概率，不推荐以此解决库存。没有症状不证明可长期重复。
- NIH描述急性维A毒性常见于一次或少数几次极大剂量（通常>100×RDA），慢性毒性与持续高摄入有关。此为典型模式，不是低于某个数字就绝对安全的阈值。明显头痛、视力异常、反复呕吐等应停食并及时就医。
- 牛肝还富铜。NIH Copper / Health Risks指出过高摄入可致腹痛、恶心、腹泻、呕吐；健康人铜中毒少见。不把用户必然胃肠不适或中毒当预测。https://ods.od.nih.gov/factsheets/Copper-HealthProfessional/
- 加工可损失一部分维A，但仍保留大部分。不能保证浸泡、焯水、长煮能大幅定量去除；反复加热的食谱保留系数并不支持持续去A。当普通蛋白吃或混入其他肉不会减少吃下的牛肝总量；500g约100g蛋白也伴随原有微量营养负荷。
- 尚未解冻：先保持冷冻并测实际温度，不因怀疑不到−18°C就赶在一周吃完。若实际可持续≤−18°C，分100–150g冻存数周可行；USDA生牛肝质量建议3–4个月。若无法达到合适长期冷冻条件，转可靠冷冻或分食。生肝冷藏1–2天、熟肉冷藏3–4天，不能靠煮熟后冷藏一周。https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/meat-catfish/beef-farm-table
- 已冷冻块可直接分袋；若需冷藏解冻分装，≤4°C且及时处理后可重新冷冻，可能损失口感。先核实冷冻条件，再采用该操作。https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/freezing-and-food-safety

## Integrity pass与触发器
关键数值全部来自上列官方原始Excel及NIH；计算在calculation.json可复算。份量/蛋数/温度为本人报告或明确假设。加工保留率及跨日平均均标作估算，未伪称品牌检验、本人吸收率或个人毒性概率。品牌维A含量、完整7日蛋奶/强化食品摄入、冷冻温度或已有症状会改变具体判断。
