---
date: 2026-05-09
tags: [coach-session, training-plan, race-week, multi-race, correction]
related: [[races]] [[training-plan]] [[decisions]] [[sessions/2026-05-09-icu-push-zwo-upgrade]]
---

# 2026-05-09 ｜ 重写 5/10-5/17 plan — 多赛季尾段维持周

## 用户原始反馈（3 条）

> "1，我的赛季要一直到5月最后一天才结束，你这么早就减量的话，后面的比赛怎么办？这一周tss才250？2，你没有考虑到明天的课程。3，我不喜欢天天练，主动恢复日减少，除非必不可少的话。其他情况我选择当日全休"

## 我的错误（撤回）

1. **过度按"4/1 单 A 赛 taper 协议"**：把 5/17 当成孤立 A 赛深 taper（TSB 0~+5），但实际后面还有 5/23, 5/24 (B), 5/31 (A) — multi-race tail 不能深 taper
2. **5/10 漏排** — 只做 5/11-5/17 七天，没考虑明天
3. **过多 active recovery**：原 plan 5/11/13/15 都是 Z1 短骑，违反用户"不喜欢天天练 + recovery 改全休"偏好

## 修正原则

- **维持训练负荷 ~常规 65-75%**（不深 taper），保留 CTL 给 5/23-24 + 5/31
- 5/16 短开腿做 5/17 临场 sharpen（不是深 taper）
- 结构 = **4 ride + 1 race + 3 全休**（用户偏好）
- Rest 日推 NOTE category（灰色），用户日历能看见"今天全休"标签
- 5/10 加 HRV-gated Z2 维持骑（5/9 RED 后 conditional）

## 新 plan 8 天

| 日期 | 类型 | 内容 | ICU TSS |
|---|---|---|---|
| 5/10 Sun | WORKOUT | Z2 90min 维持（HRV 决定强度） | 63 |
| 5/11 Mon | NOTE 灰 | 完全休息 | 0 |
| 5/12 Tue | WORKOUT | 稳态加速课 完整 4set × 8min（含 16 次 500W 冲刺） | **149** |
| 5/13 Wed | NOTE 灰 | 完全休息 | 0 |
| 5/14 Thu | WORKOUT | 30 秒爆破 3set × 12 reps + Z2 30min cooldown | **104** |
| 5/15 Fri | NOTE 灰 | 完全休息 | 0 |
| 5/16 Sat | WORKOUT | 赛前开腿（强制 — 4/1 协议） | 50 |
| 5/17 Sun | RACE | A 赛 Climbing Race 1 | 80 |

**总 TSS 446**（5/11-5/17 = 383），≈ 常规 600 的 74%。

## 关键 session 设计意图

### 5/12 稳态加速课 完整版 (149 TSS)
- 4 set × 8min 主体，每 set 内 4 次 (90s @ 110% + 30s @ 167%)
- 共 16 次 500W 冲刺 — 模拟 5/17 比赛全程的 W' 反复 burn-recover
- ICU TSS 比 coach 估算高 50% (149 vs 95)，因为 16 次 sprint @ 500W 的 NP 拉得很高
- **如周二完全踩不动到第 4 set → 当场降到 3 set (~120 TSS)，不要硬上**

### 5/14 30 秒爆破 + Z2 base (104 TSS)
- 3 set × 12 reps (30s @ 130% + 30s @ 50%)
- 末尾 30min Z2 长 base 补有氧底量
- 训练 W' 池快速重建（attack 后能再 attack 的能力）
- 如某 set 第 12 reps 踩不到 390W → 降到 360W 但完成 12 reps，**不要降组数**

### 5/16 赛前开腿
- 沿用 4/1 协议，强制不准纯 Z1
- 2×3min @ 315W + 1×30s @ 450W → 打开 anaerobic 通道，第二天 HR 才不会从第 1 分钟飙到 200

## 代码改动

`plan_generator.py` 加 `_build_rest_payload`：Rest 日 → NOTE category，灰色标签，无 workout chart。

## 5/18-5/31 节奏模板（暂存）

详见 [[decisions]] 5/9 "季内 multi-race 周节奏模板"，待 5/17 race 完成后正式生成 + 推送。

## 触发器

- 5/12 周二实战完成度 → 决定 5/14 是否调整
- 5/17 race HR 数据 → 调整 5/18-5/24 plan 的强度
- 5/16 早 HRV → 决定 5/16 开腿是否减组
- 5/10 早 HRV → 决定当日是 90min Z2 还是 60min Z1 或全休
