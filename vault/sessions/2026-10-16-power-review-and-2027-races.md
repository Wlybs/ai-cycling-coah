---
date: 2026-10-16
tags: [coach-session, power-profile, recovery-return, race-calendar]
related: [[athlete]] [[decisions]] [[races]]
---
# 2026-10-16 ｜ 功率曲线、复训表现与2027赛事候选

## 用户确认的新事实
9月24日摔车，10月2日恢复训练；此前减量不是常态训练量。当前身体状况良好。每周至少10h、最多15h，不喜欢天天练，最多两次3.5h以上；有室内骑行台，可室内外结合。近期只有约45秒全力骑行，主观FTP仍约300W。目标2027年6月Singapore national race（用户目标月份，2027官方日程尚未查到）。希望非crit、周末、从新加坡交通方便、有爬坡筛选的比赛。
用户明确要求记住：2003-12-02出生，中国籍，截至2026-10-16无UCI执照。已写入mempalace drawer_cycling_athlete_30c14d6f8a89a29f；搜索工具报NoneType异常，但add_drawer返回success=true。

## 数据与方法
继续使用同会话约12分钟前完成的同步，未重复运行有已知缺陷的默认同步；补拉3–6月、8月、9月上/下半月、10/1–16的ICU power-curves，并验证响应id/start/end。原始及比较表：icu/analysis/2026-10-16-power-curve-*.json、2026-10-16-power-period-comparison.json。
补齐9/8、9/9和10/1活动详情。逐秒分析及完整rep表：icu/analysis/2026-10-16-ride-trends.json、.md；图2026-10-16-power-and-intervals.png。
9/8、10/6、10/13的FIT duration累计生成索引会因暂停产生数百样本偏差；分析改用ICU真stream索引，timestamp核对，工作/恢复边界±8样本内检测，保留内部全部功率。前两次全部工作段逐秒连续，检测边界变化-3至+1秒，平均功率改变量不足1W。10/13后段需单独解释，见附表。

## 关键证据
- 春季3–6月 / 9/1–15 / 10/1–16：30s 750/704/781W；60s 551/585/637W；3min420/360/354W；5min397/345/335W；10min342/304/311W；20min336/288/295W。各点来自不同活动与不同长短窗口，不是等条件极限测试。
- 10/10 i195605523原始stream最佳45秒723.8W、30秒781.5W、60秒637.4W，均无缺样、峰值998W。30/60s为当前全生涯曲线纪录。用户确认45s全力；60s只是滚动窗，不能当独立60s全力测试。
- 9/8 5×约4min检测均W：357.2/353.7/333.2/342.2/336.6；工作总1257秒，加权344.4W、HR172.8。
- 10/6：340.7/341.5/327.6/333.7/350.2；工作总1274秒，加权338.6W、HR176.3。两次RPE均5；设备均温29.5/29.1°C仅辅助，不能替代真实环境或控制前序负荷。差5.8W约1.7%，不能外推VO2max下降。
- 10/13前四段352.7/343.5/323.4/345.8W。约36.5分钟后另有196秒354.3W，不称完整连续5×4。车表平均温度32.4°C、标题高湿热/烟霾；热贡献合理待确认，未测核心温度/湿度，不宣称单一病因。
- 10/14室内3.349h AP204W，HR137。去前15与末5分钟后两半：205.5W/133.9bpm与205.4W/142.4bpm；P/HR下降6.06%。明确心率漂移，不能单独诊断有氧不足、脱水或FTP错误。
- 10/2室内3.170h AP190W、HR141；10/5 2.172h AP215W、HR144。只说明已完成这些时长和功率，不跨条件宣称量化能力提升。
- 当前ftp_set300W（账号），用户体感约300W；仍缺近期连续全力长输出测试，不用PD曲线拟合CP/W'或改FTP。
- 10/16fitness current CTL70.8 ATL77.9 TSB-7；当天HRV77 RHR45 sleep8h01。主观健康由用户本轮确认。

## 教练判断与修正
撤回上一轮以摔车恢复期周量当常态、给9h示例的依据。后续按10–15h、室内外结合、完整休息日来设计。
证据支持短时成绩创新高、复训后可完成接近9月前期水平的5×4训练和长有氧；不支持整体能力崩塌，也不能确认中长时已回到春季上限。
近期中长时功率曲线是训练采样，不是能力上限；不把缺少测试误判为退步。
训练方向为持续有氧、长骑后程表现、重复爬坡输出；短时爆发保持接触。此为结合目标的教练选择，不宣称已证实单一生理短板。骑行台用于可重复的稳态与质量训练，室外用于长骑、地形与团骑。未推送课表，暂不新定FTP。

## 赛事核查（截至2026-10-16）
2027尚不能列为确认赛历。Singapore Nationals六月是用户目标窗口；2026实际6/26–28在Bintan，6/28周日IRR。2026 guide外国人可参赛、需当年UCI执照；国家冠军衫/积分资格另行限制。2027须核当年规程。用户按2027减2003=24岁赛历年龄，不按U23规划。
SCF官方赛事页：https://www.scf-reg.com/events/ocbc-singapore-national-road-champs-2026
2026 rider guide（赛事研究代理核页4–5/9/25–28，父代理直连403）：https://scf.cdnmonstre.xyz/event-documents/6ad6d049-1f58-46e6-9430-d157023536e7.pdf
现行license页：https://singaporecycling.org.sg/pages/race-license
2025 guide可交叉核对外国参赛与国家衫区别：https://scf.cdnmonstre.xyz/event-guides/2025.RIDERsGUIDE_OCBCNatChamps_Road_v8_16Apr25.pdf

优先候选（路线数字均往届，不冒充2027）：
1. Selangor KOM：2026-09-13周日；40km约1200m，KKB→Fraser Hill；适合长爬筛选[推断]。2027未查到公告；若九月继续则在Nationals之后。SIN飞KUL后仍需地面转场。
https://www.mep21-online.com/event-info.php?eid=91276
https://www.mep21-online.com/doc/Selangor-KOM-2026-Terms-and-Conditions.pdf
https://www.singaporeair.com/sg/en/plan-travel/destinations/flights-to-malaysia/
2. Tour de Bintan Classic：2026-08-23周日，150km/1917m competitive丘陵大组；Century100km8/22周六亦competitive，排除70/45km非竞赛组。2027未公告。BRF Tanah Merah渡轮约1h10加转场。
https://tourdebintan.id/categories/
https://tourdebintan.id/
https://www.brf.com.sg/our-story/
3. Masters Tour Andaman：官网2027仅February/March意向，尚未具体日期。2026-04-25/26周末，3.9kmITT+52km/670m与85km/600m两场road，约1km陡坡，有坡后平路，非纯爬坡赛。SIN直飞HKT后转Natai，2026有含bike-box机场接送套餐；2027以公告为准。
https://masterstourofchiangmai.com/about/
https://masterstourofchiangmai.com/masters-tour-of-andaman-2026/
https://www.flyscoot.com/flights/en/flights-from-singapore-to-phuket
次选阳明山王2026-03-07周六21km；2027未公告且中国籍赴台入境手续尚未核实，当前不列交通最便利首选。

## 触发器与待澄清
10/13中断训练的实际原因、10/14室内风扇/温度/补给、室内外功率是否同源，会影响对心率变化解释。新长时全力/标准化输出证据才支持修订真实持续能力；2027路线公布后再确定比赛专项和峰值窗口。

## Integrity pass
个体功率/HR/时长均可回溯上述JSON字段或原始stream索引；所有趋势解读区分实际记录与能力推断。无W/kg（当前实测体重未确认）、无CP/W'拟合、无过训诊断、无捏造赛事日期、无预估名次。图是原始curve取5–3600秒展示和两次逐rep均W，曲线非全力测试已注明。赛事交通是现有航线/渡轮，不保证2027具体班次、车位或资格。
