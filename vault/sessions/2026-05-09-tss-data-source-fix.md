---
date: 2026-05-09
tags: [coach-session, data-correction, tss-baseline, hard-rule]
related: [[athlete]] [[decisions]] [[sessions/2026-05-09-load-analysis-har-pattern]]
---

# 2026-05-09 ｜ TSS 数据源契约 HARD RULE — 用 wellness 不是活动表

## 用户原始反馈

> "关于你读取的数据的准确性有待商榷，我查看后发现4.13-4.19这一周的周tss是468，不是你说的265"

## 我的错误

用 `activity_list_clean.json` 的 `icu_training_load` 求和算周 TSS。这会漏：
- 手动登记 TSS（如 4/14 wellness ctlLoad=203 但活动 API 返回 type=None / name=None / TSS=None）
- 力量训练 / 室内骑没数据上传
- 任何只在 wellness 表有记录但活动 API 无返回的训练

差异规模：W16 实际 468，我算 265 — **少 203 TSS**（约 43% 误差）。

## 正确数据源（HARD RULE）

```python
# RIGHT
weekly_tss = sum(w['atlLoad'] for w in wellness_history if w['date'] in week_range)

# WRONG
weekly_tss = sum(a['icu_training_load'] for a in activity_list if a['date'] in week_range)
```

落 [[athlete]] § 数据源契约。

## 修正后近 10 周数据

| 周 | 旧（错） | 新（wellness 真值） |
|---|---|---|
| W08 | 702 | **876** (+174) |
| W14 | 885 | **994** (+109，升高负荷) |
| W16 | 265 | **468** (+203，用户原始 flag) |
| 其余 | 同 | 同 |

近 10 周统计修正：
- 均值: 708 → **739**
- 高负荷周频次: 2/10 → **3/10**
- 月均: 3066 → **3201**

## 最大承受预测修正

| 维度 | 旧值 | 新值 |
|---|---|---|
| 单日峰值 | 280-285 | **300** (W14 4/1) |
| 持续高负荷 | 800-900 × 3 周 | **900-1000 × 3-4 周** |
| 4 周块 | 3200-3400 | **3400-3700** |
| 月均上限 | ~800/周 | **~850/周** |

**含义**：
- 你目前已经在最大可持续训练负荷区间运转（月均 3200 接近上限 3500）
- 想突破到月均 3700+ 需要先把 CTL 从 105 推到 110+
- 5/10-5/17 race week 440 TSS = 真常规 (700+) 的 63%，符合 race week 减量

## Race week plan v4 评估

旧错误 baseline 下 440 TSS 看起来"低"。新真 baseline 下 440 TSS = 63% of normal，**race week 标准减量**。

如果用户仍想冲到 600 TSS，3 个方案待选（[[INDEX]] 活跃旗标）：
- 当前 v4: 440 TSS（race readiness 最佳）
- 方案 B: 5/15 加 Z2 90min → 510 TSS
- 方案 C: 5/12 H 加 1 set → 480 TSS

## 元教训：第 5 种 sycophancy 风险

不是 sycophancy 但同源问题 — **数据源选错的偏差方向**。我选了"看起来更结构化"的 activity_list_clean.json，但它过滤丢了非常规活动。**正确做法**：当 ICU 自己计算的 metric (CTL/ATL) 和我手算的不一致时，**信 ICU 的**，反向追溯哪里漏了。

新规则：任何"我算出来 X" 与 ICU 显示的 X' 不一致 → 不要 silently 用我的，停下来 grep ICU 字段名找出真源。

## 触发器

- 后续任何 plan 设计涉及"周 TSS 目标" → 必须用 wellness ctlLoad 算 baseline
- 用户报告"我看 ICU 是 X 但你说 Y" → 立刻数据源审查
