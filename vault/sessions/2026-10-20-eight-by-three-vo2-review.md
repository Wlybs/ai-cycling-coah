---
date: 2026-10-20
tags: [coach-session, ride-review, vo2, faber]
related: [[plans/2026-10-19-faber-and-drcc-eight-week]]
---

# 2026-10-20 ｜ 8×3min VO2 课复盘（替代原定30min持续校准）

## 用户原始请求
完成今天训练，要深度数据分析，强度判断可问体感。

## 数据快照
- ftp_set 300W（snapshot 2026-10-20 11:17 sync）；wellness 10/20 HRV86（7日76）RHR43（7日45）睡7.4h；CTL75.4 ATL93.7 TSB−18.3。
- i199292147：2h08、62.8km、738m、31.2°C、ICU RPE7 feel4；本人标题“harder than 5x4min”，备注“总容量一定，做功组越短越累”。
- stream onset校准（阈值320/290/270，offset280）：8组178–186s，均357W（lap 356W，偏差≤2s）；逐组349→363W，踏频95→97；每组约57m/≈5%。
- 组末HR 178→190，后4组186–190（LTHR设定188）；恢复183–215s、55–92W，恢复末HR 127→141。HR≥185共463s。
- 后4组前30s 385–396W，比整组均高约30–40W。
- 对照10/6 5×4：lap工作1271s，onset加权338.6W（plan引ride-trends），HR≥185 333s，29.1°C，RPE5 feel3。

## sync 警告
无；MCP icu_activity_detail 报未同步，实际文件已在 warehouse，直接读文件。

## 教练判定
完成质量好、无掉功率。“比5×4累”不能归因于组更短：今天工作时间+14%、功率+5%、高心率时间+40%、更热，总量并不相同。功率357W高于计划3min版上沿351W，组数8在6–10中段。前30s偏高可能贡献疲劳[推断]。

## 处方
原30min持续校准按浮动规则取消不补；本周质量=今天+周日Crazies。明天LSD按起床/出门腿状态选3.5–4h或缩短/休。

## 触发器
若本人说主要是腿烧且前30s是有意冲的，下次先控起步再比较；要检验“组短更累”需同功率同总时长对比。

## 数据与复算
原始流：`icu/icu_data_warehouse/9_Coach_Raw/2026-10-20-eight-by-three-vo2/`（4个活动）；脚本与输出：`icu/analysis/2026-10-20-eight-by-three-vo2-review-{reps,compare}.py` 与 `.txt`。本会话3个体感问题未在此会话回答，后续见同日 [[sessions/2026-10-20-codex-vo2-fast-start-followup]]。
