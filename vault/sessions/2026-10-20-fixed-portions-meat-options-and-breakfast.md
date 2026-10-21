---
date: 2026-10-20
tags: [coach-session, nutrition, breakfast, athlete-preferences]
related: [[athlete]] [[plans/2026-10-21-fueling-and-body-composition]]
---
# 2026-10-20 ｜ 保留固定肉蛋份量、牛肉牛肝与两种早餐

## 用户原始请求与新确认
本人每次吃蛋至少2个、一般3个，不要打乱；鸡胸生重200g已分装，不接受拆份。问为何不让吃牛肉/牛肝、是否比鸡胸好；早餐100g燕麦+2蛋+75g蓝莓+300ml脱脂酸奶是否可，白面包更方便、也愿加蓝莓。
追问确认燕麦100g为干重；酸奶标签P4g/C7g每100g或ml（用户回答未进一步区分单位），不沿用脱脂牛奶数值。

## Fresh evidence
全量sync成功退出0、无失败模块，日志/tmp/cycling-coach-20261020-fixed-portions-breakfast-sync.log。
snapshot.updated_at2026-10-20T23:20:56.301677 ftp_set300W；fitness.current2026-10-20 CTL75.4 ATL93.7 TSB−18.3；wellness同日ctlLoad141、HRV86/RHR43；当日详情仅i199292147，events=[]。本轮不改训练剂量/FTP、不分析rep或PB。最近5session相关段/INDEX/athlete/diet plan已读。

## 教练纠正与安排
上次把鸡胸拆150/100g、鸡蛋改1个/餐不符合实际分装与习惯，本轮明确撤销。保留每餐2–3蛋、鸡胸生重200g整包；参考蛋白量不是150g硬上限。未来按真实全日能量/腰围/体重/训练表现调可变部分，不强拆固定食物；也不凭蛋白高于参考量诊断总能量过剩。
牛肉可轮换，之前鸡胸只是为已知食材算模板，不能变为禁止牛肉；瘦牛肉提供优质蛋白和铁/锌/B族，脂肪能量取决部位，250g生牛肉与200g鸡胸不当等宏量。鸡胸并非增肌效果已证更优。牛肝可偶尔吃，微量营养密度高，但不等于天天吃更有益；维A高，保留NHS最多每周一次的通用建议，不保证本人150g每周一次在所有情境下已证安全、不诊断维A过量或缺铁。
明早两套都可，按本人便利性首选200g白面包+2蛋+75g蓝莓+300ml脱脂酸奶，约120g碳水/40g蛋白，提前约60–90min可按熟悉耐受调整。酸奶300ml若标签按100g先近似300g，得21gC/12gP；其能量/脂肪未提供，不算精确早餐热量。
干燕麦100g+2蛋+75g蓝莓+酸奶300ml可保留，参考约90–100gC，纤维较多，建议预留约1.5–2h更从容；不是本人必须等满时长或已知有GI问题。100g干燕麦与200g面包不是精确等碳水替换，但搭配正常骑中补给都可用，不必为凑数强加。蓝莓可加入，不把75g普通水果当高剂量抗氧化补剂。
明日训练仍若200实际轻松则室内共3.5h，5+3h20+5、不补threshold；骑中350g面包+2香蕉约180–200gC及清水不默认盐不变，不因为早餐变大就自行撤骑中补给。两顿正餐保500g熟饭+每次2–3蛋+鸡胸200g或本人其他主肉轮换。

## 原始来源及算术
USDA公开API读取并保存icu/icu_data_warehouse/9_Coach_Raw/2026-10-20-fixed-portions-breakfast/：usda_oat_search.json、usda_173904.json（普通干燕麦）、usda_171711.json（生蓝莓）、breakfast_comparison.json。
173904每100g C67.7/P13.15/F6.52/纤维10.1，171711每100g C14.49/P0.74/纤维2.4。均标准成分，非本人品牌；总碳水字段包含纤维，不伪称全部为实测可吸收量，燕麦品牌标法可能不同，所以给约90–100而不精确到个位数。
2蛋假设100g可食按MEXT12005 C0.3/P12.5；200g本人面包C88.8/P16；75g蓝莓参考C10.8675/P0.555；酸奶约C21/P12，面包整套约C120.9675/P41.055，只展示120/40；燕麦整套参考C99.8675，仍给范围。
MEXT11092原文已核生牛肝P19.6g/100g、铁4mg、锌3.8mg、维A1100µgRAE/B12 53µg；只用作营养差异说明，不当本人所买牛肝的逐批化验或疗效证明。https://fooddb.mext.go.jp/details/details.pl?ITEM_NO=11_11092_7
NHS Meat in your diet支持红肉铁锌B族及脂肪按部位，https://www.nhs.uk/live-well/eat-well/food-types/meat-nutrition/；NHS Vitamin A第66行每周不超过一次肝，https://www.nhs.uk/conditions/vitamins-and-minerals/vitamin-a/。属于常规食物指导，本轮未引用旧运动科学试验替代个体数据。
AIS Sports drink/how-and-when与mixed macronutrient官方页支持普通食物及按胃耐受/具体场景选择；不证明本人必须低纤维或两套早餐的长期训练优劣。https://www.ausport.gov.au/ais/nutrition/supplements/group_a/sports-foods2/sports-drink/how-and-when-do-i-use-it

## 触发器与范围
若早餐实际胃胀，先调整进食间隔/份量分配而不是定性食物不能吃；全日能量/体成分依据真实后续趋势调整，不再为估算蛋白目标拆包。同步修改diet模板、athlete、INDEX及训练plan早餐一句；无代码/ICU写入，不动其他会话源码或beads锁文件。
