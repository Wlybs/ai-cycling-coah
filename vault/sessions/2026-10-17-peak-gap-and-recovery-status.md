---
date: 2026-10-17
tags: [coach-session, peak-gap, recovery-status, fitness]
related: [[decisions]] [[athlete]]
---

# 2026-10-17 ｜ 当前状态 vs 巅峰期差距与恢复评估

## 用户原始请求
“和我分析一下我现在和我的巅峰状态时候的差距，我想知道我现在恢复的怎么样了”

## 数据快照（使用的证据）
- sync：`sync_data.py 1 90` 2026-10-17 21:20 完成（WSL，log `/tmp/cycling_sync_peakgap_20261017.log`），snapshot updated_at 2026-10-17T21:20:06，ftp_set 300W。
- 巅峰窗口按 [[sessions/2026-10-16-june9-peak-and-attack-role]] 定为 4/1–6/9。wellness 来自 `analysis/2026-10-16-training-history-context.json` 的 wellness_selected + live `wellness_history.json` 合并。
- ICU 记录的 FTP 4–10 月一直是 300（活动 icu_ftp），故 4 月以来负荷/CTL 口径一致，可直接比较。
- CTL：巅峰期均值 99.6（90–106）；10/17 为 73.9（约 74%）；8/1 低点 50.8；ramp 4.47/周。
- TSB：巅峰期均值 −0.6；10/17 −18.6；近 7 天均值 −21.4。
- HRV/RHR：巅峰期均值 63.4 / 47.6；近 7 天 73.7 / 46.3；9 月 79.5 / 43.7。snapshot alert_level green。
- 功率 90d vs 生涯（snapshot.recent_pbs，滚动窗口）：5s 1137/1202；30s 781/781；1min 637/637；5min 345/397；10min 311/342；20min 295/336；60min 273/274（60min 非全力，不比较）。
- 10 月曲线（`2026-10-16-power-period-comparison.json`）：30s 781、1min 637 均为 10/10；5min 335（10/8 阈值课）；20min 295（10/4 “fitness zero”）。
- 月量：4 月 56.1h、5 月 62.8h；10/1–10/16 共 31.0h（约 12.7h/周，巅峰核心窗口 13.42h/周）。

## sync 警告
无。sync 全部模块完成。

## 教练判定
恢复面良好：HRV 高于巅峰期、RHR 不高、无报警，与本人“次日基本恢复”一致；当前 TSB 偏负是在练的状态，不是恢复不良。
差距集中在 3–20min 持续能力：滚动窗口 PB 为生涯的 87–91%；≤1min 已追平或新纪录。主因是负荷储备：CTL 只有巅峰期约 74%，8/1 起仅重建约 11 周，巅峰前是 1–5 月每月 50–63h 连续堆出的。
近期 5/10/20min 多为训练片段、非已确认全力，87–91% 是差距的上限估计，非已测能力。HRV 跨期比较不证明体能更好。

## 处方
不改 [[plans/2026-10-19-faber-and-drcc-eight-week]]；Faber CP3/双向 PR 仍是中途检验点，可作为第一个全力锚点。

## 触发器（什么会改这个判断）
用户确认 10/4 20min 295W 为全力 → 作为当前 20min 锚点（88%）；若否，则当前持续能力无全力锚点。HRV 连续 2–3 天下滑且 RHR 高 baseline 5+ 持续 2 天 → 改判恢复不足。

## 待用户回答
1. 10/4 20min 295W 是否全力？ 2. 爬 Faber 时先顶不住的是腿还是呼吸？ 3. “回到巅峰”指功率数字还是比赛跟车能力？
