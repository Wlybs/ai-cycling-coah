---
date: 2026-10-22
tags: [coach-session, nutrition, supplements]
related: [[athlete]] [[races]] [[athlete-quick-facts]] [[sessions/2026-10-21-supplements-and-condiment-storage]]
---

# 2026-10-22 ｜ 12/13前补剂要不要不停；库存更新

## 用户原始请求
为12/13 DRCC状态最佳，现在有必要保持补剂剂量吗，还是可停、晚点再吃？β-丙氨酸无刺痛，习惯一次4g。五月库存有变化（见下）。没有其他补剂。

## 数据快照
- sync_data.py 全量完成；athlete_snapshot.updated_at=2026-10-22T20:57:50，weight_kg=null。本次不用FTP/体重计算。
- 本人10/21报告：肌酸、β-丙氨酸均3–5g/day约1个月（约9月下旬起，起始日为推算）。今天到12/13为52天（约7.4周）。

## 教练判定与处方
- 肌酸：可停，但不必。停后体内储量4–6周回落（AIS concerns）；以3–5g/d重新吃约4周饱和（AIS how-and-when）。若停，最迟11/15恢复；赛前5天每天约20g加载可补救但不首选（加载期增重/胃肠不适风险）。默认继续3g/d随餐最简单。
- β-丙氨酸：不停，继续4g/d到比赛。AIS：至少4周才有作用，6.4g/d达最高肌肽平均需18周（4–24周）；继续吃，赛日累计约12周。停用后肌肽每周约降2–4%，6–15周回到基线（Baguet 2009；Yamaguchi 2020，均超3年，近3年未找到更新的停用数据）。
- 一次4g：AIS建议分次主要为减少刺痛，且随餐吃可最大化肌肽合成。本人无刺痛→接受一次4g，建议随餐。修正10/21的“1g×4”，依据为本人新报告+AIS原文，非仅因本人偏好。

## 库存更新（覆盖athlete.md五月表）
无电解质粉；100PLUS原味1.5L装储备；乳清蛋白为Myprotein whey；碳水粉改为FairPrice 3kg细白糖；咖啡因粉200mg有；甜菜根粉有（未标硝酸盐，暂不开剂量）。无其他补剂。

## 来源
- AIS β-alanine how and when: https://www.ausport.gov.au/ais/nutrition/supplements/group_a/performance-supplements2/b-alanine/how-and-when-do-i-use-it
- AIS creatine how and when: https://www.ausport.gov.au/ais/nutrition/supplements/group_a/performance-supplements2/creatine/how-and-when-do-i-use-it ；停用4–6周见10/21 session所引concerns页。
- Baguet 2009 J Appl Physiol: https://nutrition-evidence.com/article/124253/carnosine-loading-and-washout-in-human-skeletal-muscles ；Yamaguchi 2020 16周停用: https://irep.ntu.ac.uk/id/eprint/41679

## 触发器
晨重明显上升且影响爬坡体感→重新讨论肌酸；出现刺痛→β-丙氨酸改分次。

## 追问：一水肌酸、体重61→63（覆盖上段“默认继续3g”）
- 本人：是一水肌酸；体重从稳定约61kg到稳定约63kg，自觉不明显。ICU wellness_history 91条无体重记录，无法核时间线；snapshot weight_kg=null。
- AIS concerns：肌酸增重“最多1–2kg”，主要是体水；停用后肌酸与体重4–6周慢慢回落。AIS what-is-it：益处为短时高强度（肌酸储量约够8–10s最大用力），未提长时间耐力。
- 推算[未实测]：人+车约67.3→69.3kg，重3%；陡坡上同速度约需多3%功率（忽略风阻）。+2kg也可能部分来自饮食/肌肉，无法区分。
- 处方：从今天起停肌酸，β-丙氨酸照常4g/d随餐。停用后4–6周（约12/3前）即赛前，正好检验：若体重回到约61说明主要是肌酸水分；若不回落则不是肌酸造成。每周固定一天晨起空腹称重，写进ICU。
- 改变依据：新数据（+2kg、比赛是61km/+1462m长爬坡），非仅因本人意愿。

## 第三轮：本人反驳停肌酸（覆盖上段“停肌酸”）
本人论点：①肌肉含水→更有力→FTP升；②爆发/无氧更强，拉扯不掉队；③长坡缓、draft重要，更高功率可抵体重。本人决定不停。
- ①不成立：Fernández-Landa 2023 Sports Med（13个RCT、训练人群）耐力表现合并无变化 SMD −0.07（p=0.47）（2023-03发表，略超3年；近3年未找到推翻的新综述，2026 Nutrients 综述 doi 10.3390/nu18111677 全文未取得）。Meixner 2025 Curr Dev Nutr（25名训练车手）：15s冲刺做功提升，糖酵解贡献无变化。没有证据支持肌酸提高FTP。
- ②部分成立：≤15s短冲刺有直接证据（Meixner 2025）；1min以上的持续加速未见证据。
- ③部分成立，订正上轮：上轮“重3%即多3%功率”忽略了风阻，高估了缓坡代价。用10/19 session的3.8%、25km/h模型[推算]：重力+滚阻约200W，多2kg约+6W；跟车总功率约257W时约占2%；7.7%陡墙约3%。另外2kg未必全是肌酸（AIS上限1–2kg）。
- 结论：利弊接近，证据不偏向任一方。接受本人继续：一水肌酸3g/d随餐，不加量、不赛前加载。β-丙氨酸4g/d照常。
- 称重：同意单日波动大（盐/碳水/水）。改为每周固定3个早晨空腹称，看周平均，不看单日。
- Sources: https://pubmed.ncbi.nlm.nih.gov/36877404/ ；https://pmc.ncbi.nlm.nih.gov/articles/PMC11876829/

## 第四轮：肌酸“肌肉更好、恢复更好”对不对
- 判定：不算错，但说大了。
- 肌肉：Desai 2024 JSCR（12项、<50岁）肌酸+力量训练比单练力量多约1.14kg瘦体重、体脂−0.73kg；证据针对力量训练，不是单纯骑车。本人每周健身房约1次（quick-facts）。瘦体重增量中水分占比本次未核。
- 恢复：2021 IJSNEM meta（13 RCT，超3年）肌力/酸痛恢复不加快，仅48h CK更低；Kerksick 2026 JISSN叙述性综述称可能利于恢复和糖原再合成，但为叙述综述、“新兴证据”。
- 对骑车：间接益处（力量课、短冲刺），不提FTP。维持继续3g/d的决定不变。
- Sources: Desai 2024 doi 10.1519/JSC.0000000000004862；Kerksick 2026 https://pubmed.ncbi.nlm.nih.gov/41870601/

## 2026-10-25追问：忘吃一天影响大吗、停多久才有影响
- 漏一天：两者都几乎无影响，第二天照常吃，不补双份（β-丙氨酸一次8g刺痛风险更高，AIS分次理由）。
- 肌酸：停用后4–6周才慢慢回到原水平（AIS concerns）；漏几天到一周影响小[推断，无逐日数据]。
- β-丙氨酸：停用后3周只掉了增加量的约1/3，约9周回基线（Baguet 2009，超3年，近3年未找到更新数据）。
- 本次不依赖训练数据，未重新sync（沿用10/24 08:58同步）。
