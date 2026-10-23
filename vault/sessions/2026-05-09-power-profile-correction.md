---
date: 2026-05-09
tags: [coach-session, correction, power-profile, data-quality]
related: [[athlete]] [[decisions]] [[sessions/2026-05-09-power-profile-deepdive]]
---

# 2026-05-09 ｜ 功率分析撤回 + 数据契约修正

## 用户原始反馈

> "关于功率分析，我只有cp20以下的数据是全力测试的，其他的都不算全力，所以没有测试参考价值。（除了cp55min我当时用了90%的力气测试，有一定参考价值）"

## 上一份 session 的错误

[[sessions/2026-05-09-power-profile-deepdive]] 用了 60min PB 279W 推出"4.57 W/kg = Cat 2/3 弱"和"5min/60min = 1.39 = Puncheur"，**分母（60min）是训练 ride 切片，不是 all-out 测试**，整套长 duration 的论据无效。

## 数据质量契约

| 时长 | 质量 | 可用 |
|---|---|---|
| ≤ 20min | at-max | CP/W'/类型 |
| 55min | 90% effort | soft floor 反推 |
| 30+ min（除 55min） | sub-max | ❌ 不可用 |

## 撤回的结论

- ❌ "60min 4.57 W/kg 不够顶级"
- ❌ "5min/60min = 1.39 验证 Puncheur"
- ❌ "30+ min 长爬你劣势"
- ❌ "4.86 W/kg @ 30min 不够顶级"

## 仍站的结论

- ✅ Sprinter 世界级（5s 19.70 W/kg @ 4/9 全力）
- ✅ 5min Cat 1（387W @ 3/31 全力）
- ✅ 5min/20min = 1.24 → anaerobic-dominant（两端都 at-max）
- ✅ 今天 16min 平台 337W = 真 PB
- ✅ ECP CP=312W / W'=25.4kJ（仅用 ≤20min 数据拟合）
- ✅ 5/8 真实总无氧池 36kJ（实测放电）
- ✅ Sprinter + Puncheur 类型（基于 sprint 锚 + 5/20 比例 + 自分类）

## 关键新发现

55min @ 90% effort = 281W → 真实 CP55 ≈ **281 / 0.9 = 312W**

- 与 ECP 模型 CP=312W **完全吻合**
- 与 FFT_CURVES FTP=319W 接近
- 比当前 FTP set 300W 高 **12W (4%)**
- 即 **当前 FTP 偏保守，训练区间低 4-5%**

含义：**真实长爬能力可能比 60min PB 看上去强很多**，可能不是"climber 弱"，而是**没正式测过**。

## 修正后的类型描述

- 神经肌肉：World Class
- 无氧：Exceptional
- 5min: Cat 1
- 5-20min 过渡：陡（anaerobic-dominant 确认）
- 30+ min：**未知，需要正式测试才能下结论**

## 处方

- **5/17 之前**：不测任何 CP — taper 期不能染疲劳
- **5/17 赛后 7-10 天**：安排 CP20 + CP60 双测试（同周不同天）
  - CP20 全力 → 重锚 FTP，可能从 300 → 312-318
  - CP60 全力 → 拿到首份真实长爬数据
  - 决定下半年是补长 sustained 还是继续打 puncheur

## 触发器

- 赛后 CP60 测出来如果 ≥ 5.0 W/kg（≥305W）→ 类型描述改为 "Puncheur + 未充分发挥的 climber"，长期目标加 sustained 大容量
- CP60 测出来 ≤ 4.7 W/kg（≤287W）→ 确认 climber 倾向弱，专注 puncheur 路线

## 元事件

这是 cycling-coach skill 加 Step 5 后的**第一次教训**：分析时未严守"数据来源契约"假设，造成错读。已写 HARD RULE 进 [[athlete]] §功率曲线数据质量，下次违规 = bug。
