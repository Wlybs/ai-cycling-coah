---
date: 2026-06-22
tags: [coach-session, bike-fit, posture-video]
related: [[athlete]]
---

# 2026-06-22 ｜ 骑行姿态视频肉眼 fitting 分析

## 用户原始请求
用户当前目录有多段骑行姿态视频，希望按专业肉眼 fitter 视角检查不同姿势并给出 fitting 建议。

## 数据快照（使用的证据）
- [evidence: video_set=IMG_7959.MOV 至 IMG_7963.MOV, 5 段当前目录 MOV, 每段约 15.8s, 1920x1080, 约 30fps, 同一左侧 trainer 视角]
- [evidence: athlete_snapshot.json updated 2026-06-22T15:56:00.297689, ftp_set=300W；本次不依赖 FTP 推导 fitting]
- [evidence: wellness_history.json 2026-06-22 updated 2026-06-22T07:26:38.311+00:00, weight=62.0kg, HRV=66, RHR=48, sleep=26400s]
- [evidence: fitness_trend.json updated 2026-06-22T15:56:00.322613, CTL=85.6, ATL=72.6, TSB=+13.0]
- [evidence: athlete.md, right ACL reconstructed/healed; quad-dominant power pattern; TT/very closed hip posture can amplify quadriceps soreness]

## sync 警告
全量同步完成；期间 events 同步出现 `'<'' not supported between instances of 'NoneType' and 'str'`，但 coach_memory 构建、fitness_trend、wellness 和 athlete_snapshot 均已更新。本次 fitting 主要依赖视频和 athlete.md，events 异常不影响判定。

## 教练判定
5 段的鞍高和骨盆高度没有显示明显错误，骨盆也没有明显上下弹跳。主要问题集中在前端：非极低姿势中手臂偏直、肩胛被顶住，提示有效 reach/前端支撑偏硬；IMG_7962 的极低趴伏姿势髋角明显过闭，适合短时间空气动力学取舍，不适合长时间爬坡或高扭矩输出。

## 处方
保留当前鞍高作为基准，不先做大改。把 IMG_7960 或 IMG_7961 这类 hoods/aero-hoods 姿势作为比赛主姿势，目标是软肘、肩下沉、手腕中立。若自然踩 10 分钟仍锁肘或手掌压迫，优先测试 hoods 后移/上扬 3-5mm 或把立缩短 10mm。IMG_7962 只作为短平路/顺风/高速段姿势，爬坡和股四头疲劳日不建议使用。

## 触发器（什么会改这个判断）
如果出现右膝痛、手麻/颈肩痛、会阴压迫，或正后/正前视频显示膝盖内扣/外甩，则需要重新判定 saddle setback、cleat stance/Q-factor 和前端 reach。
