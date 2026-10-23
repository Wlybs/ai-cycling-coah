---
date: 2026-05-10
tags: [coach-session, ride-evaluation, ou-execution, heat-adaptation, plan-validation, race-prep]
related: [[sessions/2026-05-10-ou-1-1-rationale]] [[sessions/2026-05-10-ou-ratio-comparison]] [[sessions/2026-05-10-ou-100s-3c-comparison]] [[sessions/2026-05-09-plan-v6.6-final]] [[athlete]] [[decisions]]
---

# 2026-05-10 ｜ OU 执行复盘 + 5/11-5/17 plan 验证

## 用户原始请求

> 今天的训练做完了，你同步后和我分析，并且和我互动得到我的反馈，来判断接下来的训练计划的合理性。

## 数据快照

### Ride summary (2026-05-10_i146876743.json)
- name: Mountain 2 OU 4×10min @ 110/90% 1/1（含 commute）
- 3h03min moving / 3h41min elapsed / 88.9km / 1045m elev
- IF=0.74, TSS=167（含 commute）
- W' max depletion = **9.0 kJ**（远低于真池 22-25kJ）
- icu_joules_above_ftp = 52 kJ
- decoupling = 8.66%, RPE = 7/10, feel = 3/5
- ATL=114.4, CTL=104.3 → TSB ≈ -10
- icu_rolling_ftp=**316W** (vs ftp_set=300W) ⚠️ ICU 算法估算高于设定值
- icu_rolling_w_prime = 25.6 kJ（与 vault 锁定 22-25kJ 真池一致）

### OU 工作组 set-by-set (target 330W/270W)
| Set | over avg | under avg | over HR 末 | 衰减 |
|---|---|---|---|---|
| 1 | 329.6W | 270.6W | 177 | baseline |
| 2 | 331.6W | 270.6W | 180 | 0% |
| 3 | 330.4W | 269.2W | 184 | 0% |
| 4 | 326.2W | 271.8W | 186 (max set) | -1.0% |

**Over 4 set 平均 329.5W vs target 330W = 命中到小数点级别**
**4 set 累计衰减 <1% — A+ 物理完成度**

### Wellness gate (5/10 早)
- HRV=64, RHR=47, sleep=7.2h
- Plan 闸门 60-64 → Z1 60min；用户主观判断覆盖闸门 → 完整 OU

### 用户反馈（互动得到的关键信号）
1. **OU 完成体感**: "刚好用完"（无余量无爆）
2. **当下腿感**: 疲劳 1-2 / RPE 4/10，腿微酸但不累；**主要疲劳源是热适应而非代谢负荷**
3. **HRV 决策**: 主观判断身体 OK 上 OU（知情覆盖闸门）
4. **FTP 处理**: 不动 ftp_set=300W，等 5/17 race 数据 + 5/24-5/27 双测试

## 教练判定

### OU dose 评级修正：A+ → A

物理数据看的"余量"（HR Z5=0, W' 9kJ）**是热限速假象**，不是真余量。1/1 5c × 4 set @ 110/90 = 当前正确剂量。**不升级到 112/88 或 5 cycles**——等热适应稳定后再考虑升级。

### 热适应作为隐藏负荷因子（新发现）

5/10 真实负荷 = 代谢负荷（OU）+ 散热负荷（高温 3 小时）。前者数据可见（TSS 167），后者数据不可见但限速效果显著（"刚好用完"主因）。**未来高温窗口的训练 dose 必须同时考虑两个负荷源**。Race-specific 加分：5/17 race 同样在高温窗口，今天热暴露具有 race-specificity 价值。

### 5/11-5/17 plan 验证结果

| 日 | 原 plan | 调整 |
|---|---|---|
| **5/11** | Mountain 3 30/30 12 reps | **保留 + 2 条硬约束**：早 6:30 出发避高温窗 + HRV 闸门收紧（≥66→full / 63-65→9 reps / <63→Z2 60min / <60→全休） |
| 5/12 | REST work | 不变 |
| **5/13** | Mountain 1 B race-rhythm 3×3×450W | 不变（前提：5/11 没在热端炸） |
| 5/14-15 | REST | 不变 |
| 5/16 | 本地平路 opener | 不变 |
| 5/17 | A 赛 | — |

### HRV 闸门覆盖判定

用户今天的"主观覆盖 HRV=64 → 上 OU"是知情决策、结果验证 OK。**标记为偶发可接受，不可常态化**。规则补充到 athlete.md:
- 每月最多覆盖 HRV 闸门 2 次
- 每次覆盖事后必须复盘（今天的复盘已完成）
- 连续 2 周覆盖 → 闸门作为过载预警失效，必须停止

### FTP 不动 — 决策正确

icu_rolling_ftp=316W 是基于多窗口 power record 的算法估算，不是真测试。5/24-5/27 vault 已锁定 CP20+CP60 双测试，今天升 FTP 没有真测试支撑。继续 ftp_set=300W。

## 处方

### 5/11 (Mon) Mountain 3 30/30
- **时间窗硬约束**: 6:30 出发 / 7:00-9:00 完成 work（避高温窗）
- **HRV 闸门**:
  - ≥66 → full 12 reps (4 ascents)
  - 63-65 → 9 reps (3 ascents)
  - <63 → Z2 60min
  - <60 → 全休
- 完成后 RPE/腿感 6+ 或腿酸 3+ → 自动触发 5/13 降级条件

### 5/12 (Tue)
- 完全 REST + work，不变

### 5/13 (Wed) Mountain 1 B race-rhythm
- 不变 3×3×450W
- 降级触发器: 5/12 早 HRV 仍 <63 → 改为 2×3×450W

### 5/14-15 (Thu-Fri)
- 完全 REST，不变

### 5/16 (Sat)
- 本地平路 opener，不变

### 5/17 (Sun) A 赛
- 比赛日

## 触发器（什么会改这个判断）

- 5/11 早 HRV → 决定 30/30 档位（4 档）
- 5/12 早 HRV vs 5/10 → 应恢复到 ≥66；停在 63 以下 → 5/13 减组
- 5/11 30/30 后腿感 → 跳到 RPE 6+ 或腿酸 3+ → 5/13 改 Z2 90min + taper 提前
- 5/17 race 实测功率 + 5/24-5/27 双测试 → 决定 FTP 是否上调到 305-315W（icu_rolling 给的提示先存档）
- 连续 2 周主观覆盖 HRV 闸门 → 升级闸门规则到 athlete.md hard rule

## 关键标记

1. **热适应作为隐藏负荷因子**：未来高温训练 dose 计算必须 include 热端
2. **HRV 闸门覆盖偶发可接受不可常态化**：每月 ≤2 次 + 事后复盘
3. **icu_rolling_ftp 316W 信号已存档**：等 5/17 race + 5/24 双测试再决定
4. **OU 1/1 5c × 4 set @ 110/90 = 当前 race-specific lactate clearance 正确剂量**
