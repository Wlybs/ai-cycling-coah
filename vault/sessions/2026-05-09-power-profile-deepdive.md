---
date: 2026-05-09
tags: [coach-session, power-profile, classification, cp-wprime, race-prep]
related: [[athlete]] [[decisions]] [[races]] [[kom-targets]] [[sessions/2026-05-08-林峰KOM分析]]
---

# 2026-05-09 ｜ 全方位功率类型分析（90d + 1y） + 今天 RED alert

## 用户原始请求

> "你昨天和我说我的16min的power不可能到330w，但是我今天打脸你了。你现在作为教练，来全方位仔细的分析一下我的90天的功率类型和全部时间的功率类型"

## 关于"昨天 330W 不可能"

4 个记忆系统全空，无该言论的记录。可能是其它入口（claude.ai 网页 / 别的 AI）说的。**不替任何人认领。** 但今天 337W × 15:51 数据是新锚点，分析以此重做。

## 数据契约 / 警告

- **`power_curves_all_time.json` 实际是 1-year 窗口**（days=366, start=2025-05-10），与 90d 文件内容完全相同。**没有真全生涯数据**。要真全生涯需改 sync 脚本。
- **5min PB 387W (3/31) ≠ 10/16min PB 来源**。今天的效果在 10-16min 区间，5min slot 没动（今天 5min 切片只 342W = 87% of 387W）。
- 体重锚点 61.0kg，FTP_set 300W

## 关键 PB 来源 ride 索引

| 时长 slot | 来源活动 | 日期 |
|---|---|---|
| 1-40s 全部 sprint PB | i138344084 三江两岸 | 4/9 |
| 41-60s | i137513392 / i79587382 | 4/6 / 老 |
| 1-2min 无氧 | i132098490 / i136626300 | 老 / 4/2 |
| 4-9min | i136065211 | 3/31 |
| 5min PB 387W | i136065211 | 3/31 |
| **10-16min PBs (新)** | **i146416029 林峰 KOM** | **5/8 今天** |
| 17-22min | i133632565 | 3/21 |
| 23min-90min 大部分 | i133847457 | 3/22 |
| 90min-2h | i111517861 | 老 |
| 4h+ | i118719066 | 1/18 长拉 |

## 完整功率曲线（W / W·kg⁻¹）

| 时长 | W | W/kg | Coggan 等级 |
|---|---|---|---|
| 1s | 1296 | 21.25 | World Class |
| 5s | 1202 | 19.70 | Exceptional / WC 边界 |
| 30s | 750 | 12.30 | Exceptional |
| 1min | 557 | 9.13 | Exceptional / WC 边界 |
| 5min | 387 | 6.34 | Cat 1 |
| 10min | 342 | 5.61 | Cat 1 / Cat 2 |
| 16min | 337 | 5.52 | Cat 2 |
| 20min | 313 | 5.13 | Cat 2 |
| 30min | 296 | 4.86 | Cat 2 |
| 60min | 279 | 4.57 | Cat 2 / Cat 3 |
| 2h | 245 | 4.02 | — |
| 4h | 189 | 3.10 | — |

## 类型判定

| 比例 | 数值 | 含义 |
|---|---|---|
| 5s/60min | 4.31 | Sprinter（>4 冲刺型） |
| 5min/60min | **1.39** | Puncheur / Ardennes（>1.30 anaerobic-dominant） |
| 5min/20min | 1.24 | 下滑陡（>1.20 = 不擅长长爬） |
| 1min/5min | 1.44 | 无氧远强于 VO2 |

**判定：Sprinter + Puncheur 复合型**。绝对值上 sprint 是世界级（19.70 W/kg @5s），无氧池大，5min 以下能打 Cat 1。但 **60min 4.57 W/kg 不够顶级长爬**。

## CP / W' 模型（4 套）

| 模型 | CP | W' | FTP | 备注 |
|---|---|---|---|---|
| MS_2P | 299 | 18.5kJ | 299 | 保守 |
| MORTON_3P | 281 | 42.0kJ | 281 | 过拟合，不采信 |
| FFT_CURVES | 312 | 21.6kJ | 319 | ICU eFTP 来源，战术天花板 |
| ECP | 312 | 25.4kJ | 312 | **最佳综合** |

**采用值**：CP=300-312W、W'=22-25kJ、FTP=300W (set, 保守 12W)

## 今天 KOM 物理解释

- 337W × 960s = (337-312)×960 = 24kJ 理论 W' 消耗
- 实测 W' 24000→-12023 = **36kJ 总放电**
- 多出 12kJ 来自 **AWC（无氧能量缓冲）**
- **真实总无氧池 ≈ 36kJ**，比 ECP 估计高 ~40%

## 5/17 比赛战术含义

- 路线 10-15min 单爬：可复制 5.5 W/kg 模板，能打 Cat 1/2 名次
- 路线 > 25min 单爬：4.86 W/kg @ 30min 偏弱，需 sit-in + 末段 W' 押注
- 反复多爬（3+ 段）：W' 回血是瓶颈，相对劣势

## 5/9 RED alert（今天 sync 后）

- daily_adapt verdict=**RED** / severity=0.4
- triggered: hrv_red_threshold
- recommended_action: propose_replacement
- 处方：今天 **强制完全 off**（不是 ≤60min Z1）

## 处方

- **5/9**: 完全 off
- **5/10**: 早测 HRV — 若 < 60，taper 起点前移到 5/11；若 ≥ 65，照原计划 5/12 起 taper
- **5/12-5/17**: 5 天 taper（已记录的 4/1 决策：目标 TSB +0~+5）
- **5/17 Race-day pacing**: 复制 337W × 15min 模板 + 末段 W' 押注

## 触发器

- 5/10 HRV 仍 < 60 + RHR ≥ 50 同时 → 48h 强制 Z1 + mobility，taper 起点前移
