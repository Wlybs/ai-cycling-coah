---
date: 2026-05-10
tags: [coach-session, ou-design, methodology, mountain-2, vo2-time-constant]
related: [[sessions/2026-05-10-ou-ratio-comparison]] [[sessions/2026-05-10-ou-1-1-rationale]] [[training-plan]]
---

# 2026-05-10 ｜ OU 100s/100s 3 cycle vs 60s/60s 5 cycle

## 用户原始请求

> 那如果100s:100s,完成3cycle？这个和现在的4cycle哪个好

（注：用户说 4 cycle 应该是 5 cycle，因为当前 1/1 是 5×(1min+1min)=10min。已按当前方案 5 cycle 解读）

## 数据快照（使用的证据）

- FTP=300W, CP=300W, W' 总池 35-36kJ
- VO2 慢响应时间常数 60-90s（教科书）
- W' recovery tau @ 270W (CP-30W) ≈ 90s（Skiba 经验式）
- 当前 1/1: 60s/60s × 5 cycles × 4 set = 10min set, 4×10=40min total work
- 候选 100/100: 100s/100s × 3 cycles × 4 set = 10min set, 4×10=40min total work
- race 中段拉锯节奏: 稳态 8-10min + 短 attack 25-30s（不是 100s 长压制）

## sync 警告

无（方法论 + 物理核算）

## 教练判定

关键洞察：**set 时长一致（10min），单 set 总 over time 一致（5min），差别是单段 over 长度和 cycle 数**：

| 方案 | cycle/set | over 时长 | W'/cycle | per cycle | set 时长 | 4 set 净 W' | 刺激 |
|---|---|---|---|---|---|---|---|
| 1/1 5c | 5 | 60s | 1.8 kJ | 2min | 10min | ~22 kJ | Lactate clearance ⭐ |
| 100/100 3c | 3 | 100s | 3.0 kJ | 200s | 10min | ~18 kJ | VO2max 偏移 |

**核心差别**:

1. **VO2 时间常数临界点**：60s @ 110% 刚摸到 VO2max 边缘；100s @ 110% **已经跨过 VO2 慢响应时间常数 (60-90s)**，VO2 接近 max，刺激主导从乳酸清除偏向 VO2max。

2. **乳酸 spike 频次**: 5 spikes/set vs 3 spikes/set —— 肌肉清乳酸的训练机会减少 40%。

3. **race-specificity**: race 中段拉锯 attack 是 25-30s 短突击，不是 100s 长压制。1/1 高频小震荡更贴近 race 实际节奏。

4. **训练目标重叠**: 100/100 3c 偏 VO2max → 与 5/13 Mountain 1 B race-rhythm 形成重叠（5/13 已覆盖 VO2max + W' burst）。

## 处方

- **5/10 优先维持 1/1 5c 不改**（race-specificity 最优）
- **状态判断窗口**:
  - HRV ≥65 状态满 → 1/1 5c 吃满 race-specific
  - HRV 60-64 边缘 → 100/100 3c 作为减量替代（W' 消耗 18 < 22 kJ）
  - HRV <60 → 两个都不做，按 v6.6 闸门走 Z2 60min
- 100/100 3c 作为"减量版本"是合理选项，但不应作为"race-specific 优化"理由替换 1/1

## 触发器

- 5/10 早 HRV 测量 → 决定 1/1 vs 100/100 vs Z2
- 5/10 实测完成度 → 验证哪个版本与 Mountain 2 实际地形最匹配
- 5/13 Mountain 1 B 完成度 → 反推 5/10 是否需要调整 race-specific dose
- 5/17 race 中段拉锯感受 → 决定 6 月块 OU 范式（1/1 dose 是否够）
