---
date: 2026-10-16
tags: [coach-session, peak-baseline, training-history, crazies, ftp-uncertainty, indoor-outdoor]
related: [[athlete]] [[decisions]]
---
# 2026-10-16 ｜ 巅峰期基准、Crazies反复输出与未来FTP边界

## 用户本轮事实（高于旧笔记推断）
用户确认生涯最佳爬坡与FTP状态窗口为2026-04-01至2026-06-01，要求长期以此为历史能力基准，不把当前恢复期采样当作天花板。六月底、七月及八月初为停训/恢复阶段，约八月开始复训；九月24日另一次摔车，十月2日恢复正常训练。
9/8自觉状态比10/6好。10/14室内长骑自觉状态不错。来新加坡后室内Z2功率/心率表现优于室外；在中国阶段主观体验相反。
每周日参加Crazies，认为新加坡团骑与比赛重视短爆发。10/13因高温、高湿、严重烟霾造成体感差，自主不坚持第5组；这是用户报告的停止原因，不归为意志/能力失败。
固定室内条件：空调设22°C、最大风扇，实际约26°C、RH70%；LSD通常45–60g碳水/小时、500–700mL水/小时。室内与室外使用同一个功率计。
补充锚点：用户确认5/27第一段爬坡（用户称lap1）22:36、336W最接近正式全力FTP测试。FIT中是第2圈，第一圈为出发热身；教练使用“第一段爬坡”避免命名混淆。没有确认真实30–60分钟全力测试。
上述7条原话已存mempalace drawer_cycling_athlete_f6376d6498ef9e53，后两条锚点与功率计补充另保存。

## 新鲜同步与警告
本轮再次运行sync_data.py，通过仅限进程的requests.Session(trust_env=False)绕过失效本地代理，并仅在进程修正power-curves为curves=90d/all，未修改生产源码。同步基础profile、wellness、曲线、活动和最新详情、events；主流程ingest_ledger.py正常SystemExit(0)使runpy编排未执行尾部daily_adapt/suggester，不将其称为全链路成功。
默认活动列表只取30天，随后GET 2026-01-01至10-16做历史分析，并恢复共享清单为7/18至10/16的64条；events独立GET复核=[]后保存；随后重新build_memory.py成功。
基础证据以原始活动/流和相应日期wellness为准。自动fatigue与旧计划adherence的生理解释仍不使用；本轮未使用自动CP/W'、Type-II、双层池或其他未独立验证旧模型推断遗传潜力。
本次同步新发现10/16活动i197967435“2h z2 top”：2h01m45s，AP221W、NP225W、HR147、RPE2；类型Ride且trainer字段空，不擅自断言室内外。当前snapshot ftp_set300W、weight缺失；10/16 wellness CTL73.52、ATL93.05、HRV77ms、RHR45、睡眠8h01。当日负荷纳入后TSB为-19.53，不能以此诊断过训；不沿用前一轮尚未纳入此活动的负荷状态。

## 已证实历史基准
来源：icu/analysis/2026-10-16-peak-season-review.{md,json}；独立完整段核验2026-10-16-verified-peak-anchor.json。
- 精确4/1–6/1窗口，52条有功率活动流扫描；已知骑行118.90h、41天，62日折算13.42h/周。4月56.12h、5月62.78h；峰周4/27–5/3为21.14h；5/17–31四场比赛。4/14有不可取回Strava-only条目，因此总量是可访问记录下限。
- 5min387.58W（4/2）；此前397W在6/9，排除该巅峰窗口。
- 5/27第一爬坡完整1356秒、AP336.2987W、HR177.07，stream索引[1659,3015)，elapsed1692–3047，逐秒连续maxgap1。用户确认接近全力，不能把标题“甜区”误判其实际强度。
- 同一活动严格最佳20min336.46W、22min335.85W、24min329.67W、25min323.82W；彼此为重叠窗口，不算独立多次测试。
- 严格连续30/40/60min记录286.99/285.20/270.41W，来自其他赛事/路段并非确认全力；不能当FTP或天赋上界。API30min295W压缩暂停，不能写“连续30分钟295W”。
- 7月骑行15.16h、8月43.41h，对比5月62.78h，支持减量后重建背景；并非整个7月完全无骑行。原始月份汇总见2026-10-16-training-history-context.json。

## Crazies需求
来源2026-10-16-crazies-demands.{md,json}及crazies-raw目录。仅8/23标题直接命名，其他周日依据用户每周参加说明，仍不将每次名称当独立确认。
主体分析以剔除初段接近30min低功率与末段低功率lap为代理，非GPS确认集结边界。≥360W段定义：5秒居中平滑、至少5秒、合并≤3秒下探、保留原始均值≥阈值；是描述性检测，非战术进攻次数、非无氧段或W'耗竭计数。
- 8/23主体86.2分钟、AP233.2W，50个≥360W段，中位9秒、段间隔中位58秒；主段raw>300W27m40、>360W16m37、>450W5m51。
- 10/11主体88.6分钟、AP252.4W，40个≥360W段；后程3个较长高功率检测段43s644.5W、22s718W、34s669.3W。前两者间隔279秒，间隔仍均247.4W。
- 六次完整周日样本主体83.8–92.4min、AP233–266W，34–59个≥360W检测段。不能把间隔当完全恢复，不能把整次低AP当作纯有氧。

## 解释、训练方向与本轮修正
1. 把4/1–6/1已经实现的能力作为长期比较基准。恢复历史输出是一阶段目标，不承诺必然恢复，更不把当前滚动曲线锁成终身上限。
2. 无法从既往表现推出“最科学训练饮食下未来FTP至少某瓦数”。本轮不提供遗传上限、未来保底或未经校准的窄置信区间，不以95%×20分钟或22:36换算作未来预测。当前300W是工作设定，不是已测上限。即使把约320W称为下一测试负荷，也不能冒充生理预测，因此主结论不引入该数。
3. 巅峰期已有约13.4h/周及密集比赛刺激，不能假定此前基本未练/营养很差，再许诺巨大优化收益；同样不意味着此前训练已优化或潜力耗尽。过去饮食记录不足。
4. 9/8约5×4min工作344.4W/HR172.8，10/6为338.6W/176.3；用户感觉9/8更好与数据一致。“可完成接近输出”不等于状态相同，不以差值1.7%否认其体感，也不换算VO2max损失。
5. 同一功率计减少设备差异，SG室内稳定散热与户外热湿/变速是解释P/HR差异的合理假设，不证明代谢效率变化；10/14稳定3h21、用户体感良好，约6%前后半P/HR变化不能单独诊断耐久性差、脱水或补给不足。10/13按用户报告记为环境下主动停止。
6. 当前团骑应作为反复高强度的训练暴露纳入周结构。训练方向强调重复5–15秒加速、偶尔30–60秒强输出及后程兑现，同时保留持续有氧/阈值发展；不由此断言阈值不重要或给周内额外叠加多次高强度。用户未要求正式课表，本轮不生成/推送。
7. 保留当前LSD补给实践作为基线，未见证据要求所有LSD加量。更长、更强团骑可按胃肠耐受尝试提高碳水支持，但不能从一小时摄入或6%漂移诊断摄入不足；饮水是否足够仍缺体重变化/出汗量。
8. 下一步用相同功率源、近似散热和补给、明确全力意图的持续测试/训练记录，比较恢复历史22:36@336的进展，并补齐较长持续能力。多个训练块的反应帮助调整目标，不直接识别终身天花板。

## 外部证据（已核对原文摘要/全文）
- Borszcz et al.,2018, Functional Threshold Power in Cyclists: Validity of the Concept and Physiological Responses. 23 trained men,FTP20与FTP60个体一致性范围宽；不宜互换：https://pubmed.ncbi.nlm.nih.gov/29801189/ （Abstract/Conclusion）。不将群体误差转换成个人置信区间。
- Jenkins et al.,2023, Delineating the impacts of air temperature and humidity for endurance exercise. 14 trained participants, randomized crossover;空气温度/湿度影响生理、体感与TT表现：https://physoc.onlinelibrary.wiley.com/doi/10.1113/EP090969 （Abstract, Methods2.2）。只支持机制合理，不归因用户差值。
- Almquist et al.,2021, The Aerobic and Anaerobic Contribution During Repeated30-s Sprints in Elite Cyclists：https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2021.692622/full （Abstract,Introduction,Conclusion）；反复短输出包含有氧和无氧贡献，不由用户功率分解能量系统。
- Smith et al.,2010, Fuel selection and cycling endurance performance with ingestion of[13C]glucose: evidence for a carbohydrate dose response：https://pubmed.ncbi.nlm.nih.gov/20299609/ （Abstract）。用于补给影响表现的普遍依据，不能承诺个人FTP收益。
- Bonafiglia et al.,2019, The application of repeated testing and monoexponential regressions to classify individual cardiorespiratory fitness responses：https://pubmed.ncbi.nlm.nih.gov/30666410/ （Abstract）；提示个体反应估计与误差/模型相关，本轮未拟合个人未来FTP。

## 审核与留存
独立critique PASS：主结论不引入320W；保留已证实336W22:36，区分当时输出、当前工作设置及未知未来上限。所有关键数字可回溯实际JSON/原始流；没有使用体重缺失时的W/kg、CP/W'拟合、纤维类型或群体平均训练收益预测个人最低潜力。
图：icu/analysis/2026-10-16-peak-reference-and-crazies.png；已肉眼检查。图中两阶段记录不等同同条件全力测试，Crazies图为选取主段的逐秒流5秒平滑。
本轮仅生成分析数据、图和教练记录，无生产代码改动；保留原先已有源码修改和未跟踪文件。bd任务Cycling-9ta。已获用户本会话对该仓库训练/健康记录上传授权，按范围提交并推送。
