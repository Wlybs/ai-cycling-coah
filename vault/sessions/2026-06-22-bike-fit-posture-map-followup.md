---
date: 2026-06-22
tags: [coach-session, bike-fit, posture-video]
related: [[athlete]]
---

# 2026-06-22 ｜ 骑行姿态功能定义 follow-up

## 用户原始请求
用户补充 5 段视频的真实姿态定义：59 中坐上把，60 后坐平路，61 前坐高强度爬坡，62 模拟 TT 低趴，63 下把巡航缓解 62；并反馈各姿态无明显即时不适，只有 62/63 长时间会腰疼。

## 数据快照（使用的证据）
- [evidence: athlete_snapshot.json updated 2026-06-22T15:56:00.297689, ftp_set=300W；本次 fitting 不依赖 FTP 计算]
- [evidence: fitness_trend.json updated 2026-06-22T15:56:00.322613, CTL=85.6, ATL=72.6, TSB=+13.0]
- [evidence: wellness_history.json 2026-06-22 updated 2026-06-22T07:26:38.311+00:00, weight=62.0kg, HRV=66, RHR=48, sleepSecs=26400]
- [evidence: user posture map 2026-06-22: 7959 mid-saddle hoods, 7960 rear-saddle flat, 7961 front-saddle high-intensity climb, 7962 TT tuck, 7963 drops cruise]
- [evidence: user symptom report 2026-06-22: no obvious discomfort in all positions; prolonged 7962/7963 causes low-back pain]
- [evidence: athlete.md: quad-dominant pattern; TT/closed hip posture can amplify quadriceps soreness; right ACL healed but new knee pain must be flagged]

## sync 警告
本轮 sync 在 `sync_activity_detail.py` 拉取今日活动 streams 时挂住并被中断。健康数据、功率曲线和活动清单已刷新；上一轮完整同步在 2026-06-22T15:56 构建 coach_memory。本次 fitting 主要依赖视频与用户姿态/症状反馈，不依赖今日 streams。

## 教练判定
补充信息后，上一轮“62 不适合长时间”判断维持，但原因更明确：不是因为姿势立即不可用，而是 62/63 的腰背耐受窗口有限。61 作为前坐爬坡姿态合理，不应因为前坐就判定座垫过前；60 后坐也合理，是平路扩髋和降肌肉压力的可用姿态。

## 处方
保留当前鞍位作为基准。比赛/训练中按功能分工：61 用于高强度爬坡，60 用于平路稳态/后坐放松，62 只在高速追求 aero 时短时间使用，63 作为 62 的腰背/股四头压力缓解位但不做长期主姿势。若要延长 62/63 耐受，优先练核心抗伸展和髋铰链耐受，并检查前轮垫高/整车水平，不先大幅改 saddle。

## 触发器（什么会改这个判断）
如果 62/63 的腰疼变成 20 分钟内出现，或 61 高强度爬坡出现前膝痛/右膝不稳，则重新检查 saddle setback、hood/drop reach 和 cleat stance。
