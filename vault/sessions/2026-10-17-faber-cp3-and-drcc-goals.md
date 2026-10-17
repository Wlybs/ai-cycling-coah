---
date: 2026-10-17
tags: [coach-session, mount-faber, cp3, drcc, periodization]
related: [[kom-targets-mount-faber]] [[races]] [[decisions]]
---
# 2026-10-17 ｜ Faber双向/三分钟与DRCC新增目标

## 用户原始请求
“刷新我自己的mount faber的strava segment的pr，同时刷新我的cp3”；拟报名12.13 DRCC KOM，提供官方链接。追问链接时用户答：“你自己到我的骑行记录里面找，有数据。cp3就是在这个爬坡，有两个方向，你都看一下”。因此自行搜索，不再要求其提供已有数据。

## 数据快照（使用的证据）
- snapshot.updated_at2026-10-17T19:22:10：ftp_set300W，未重测FTP；fitness_trend.current10/17 CTL73.9 ATL92.5 TSB−18.6。
- wellness_history最后10/17：HRV71、RHR47、睡27060s=7h31、睡眠评分83；先前同步控制台显示HRVnull，后续落盘已有71；七日HRV均线缺失，不由单日锁组数。
- 10/17已完成i198249990 Zwift easy ride：9120s=2h32、icu_average_watts177、HR128、load89。今日不是尚未骑的空白日。
- 170条2026 has_segments Ride，7次Faber，API扫描无报错。633867最快映射8/8 223s373.20W；6661458最快映射9/8 226s350.52W；不是Strava官方认证PR。
- Faber8/8 raw连续180s395.05W，比633867起点早4秒；该路段内best180392.11W。生涯all源6/10中国骑行raw180420.88W（ICU整数420）。都不冒充正式全力测试，不拟合CP/FTP。
- 10/13反向映射1652–1668m而9/8/10/6约1474–1481m，不能拿时间差定能力下降。
- 本人确认的历史全力锚点6/9 CP5约397.6W、5/27首爬22:36约336.3W保留。

## sync 警告
原生scripts/sync_data.py 1 90本轮完成（/tmp/cycling_sync_native_20261017.log）。不可用代理已自动直连。早先旧临时wrapper与已修正client签名不兼容失败，已由原生成功运行替代。今日活动详情数量1已核。HRV日志/稍后文件变化已明确，不伪造基线。
官方Checkpointspot页面空白/403，不能确认完整规程、GPX、外籍无执照条件；computer-use初始化失败，未代报名、付款或联系。主办方设计海报在第三方站可视核对；转载汇总的早鸟日期与海报冲突已标记。元数据与地理端点精度也列为限制。

## 教练判定
新增目标足以改变原计划优先级：DRCC为建议短期A（拟报名），Faber为中途检验，2027长期发展保留。以三分钟重复课支持近期目标，随后提高持续爬坡工作时间。保留长有氧和休息；PR、测试、Crazies都占质量预算。路线PR与CP3不是同一指标，不保证同时刷新或八周超越历史。

## 处方
当前唯一建议稿[[plans/2026-10-19-faber-and-drcc-eight-week]]：五天骑、周一/五休。首周Tue4×3min345–360W从345起、5min恢复，Sun Crazies第二质量；次周有条件5×3与Thu2×15min280–290，Sun改有氧。11/2–8减量加一次PR/180s检验；后续3×15→2×20→2×25持续工作。正常约12–13h，减量低于10h可以；12/7赛周减量，12/6不全力团骑，12/1可选第二方向/CP3仅替代质量课。未写入ICU日历。第6周后未恢复则取消第7周测试，不推赛周。

## 触发器（什么会改这个判断）
工作段前两组已近全力、后续恢复变差，先降功率/减组，不补第三硬日。官方资格/路线与暂定描述不符则重设优先级与赛道专项。Faber边界对齐或官方effort若改变映射时间，更新目标基准而不影响已核180秒功率。下次关键课宜反馈“主要限制是呼吸还是腿，以及末组余量”用于校准，不再追问可从记录找的链接。

## 文件与审核
icu/analysis/2026-10-17-faber-pr-and-cp3-review.{md,json}、2026-10-17-drcc-event-verification.md；活跃段独立记[[kom-targets-mount-faber]]，避免把旧未跟踪林峰笔记误作本轮审核产物。原始GPS只存Git忽略仓库，本轮共享仅去位置摘要。独立critique PASS，端点误差与末期取消测试建议已修正。

## 交接
bd Cycling-k7q为本轮整合；后续Cycling-2v4核DRCC规则/GPX，Cycling-6pj核Faber地理端点。Claude算法提示词`icu/prompts/2026-10-17-faber-boundary-verification.md`已准备，尚未执行，不把提示词交付说成分析已完成。
