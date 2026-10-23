---
date: 2026-05-09
tags: [coach-session, wprime-calc, hard-rule, anchor]
related: [[athlete]] [[decisions]] [[sessions/2026-05-09-plan-v6.1-feasibility-fix]]
---

# 2026-05-09 ｜ W' 全源核算 + 锚点锁定

## 用户原始请求

> "关于我的 W' 的能力，你先详细计算一下，结合我的详细功率数据，多个平台给我估计的这个值也不一样。"

## 9 个 W' 估计源

| 来源 | W' (kJ) | CP (W) | 备注 |
|---|---|---|---|
| ICU MS_2P | 18.5 | 299 | 2-point fit |
| ICU MORTON_3P | 42.0 | 281 | overfit 异常点 |
| ICU FFT_CURVES | 21.6 | 312 | 单 8.5min 外推 |
| ICU ECP | 25.4 | 312 | **综合最佳** |
| ICU wellness sportInfo | 25.6 | — | 与 ECP 一致 |
| 自算 1+20min Monod | 15 | 300 | 短锚低估 |
| 自算 3+20min Monod | 21 | 295 | 中段 |
| 自算 5+20min Monod | 29 | 288 | 长锚高估 |
| 自算 10+20min Monod | 34 | 284 | 最长两点 |

**spread 跨 12-42 kJ = 3 倍**，不是 bug，是 CP 2-参数模型的局限。

## 5/8 KOM 黄金锚（决定性）

5/8 的 957s @ 337W 实战：
- W' bal: 23.4 kJ 起 → -12.0 kJ 终 = 净放电 **35.4 kJ**（含 AWC）
- 反推 CP：
  - CP=300W → 高于 CP 工作 = 35.4 kJ ✓ **完美匹配**
  - CP=290W → 45.0 kJ ✗ 高估
  - CP=310W → 25.8 kJ ✗ 低估

**CP=300W 被 KOM 实测锁死**。

## 双层池真相

```
真 W' (工作池):    22-25 kJ  ← ECP / Wellness / 4×20min 共识
AWC (应急池):     +10-12 kJ  ← 5/8 KOM 借出
总池上限:          35-36 kJ  ← KOM 实测，绝对不可超
```

## 3 个工作锚（HARD RULE 落 [[athlete]]）

| 用途 | W' 上限 | 出处 |
|---|---|---|
| 训练 session（不开 AWC） | **22 kJ/set** | 多源共识，留 reload 缓冲 |
| race-day 一次性 max | **30 kJ** | 真 W' + 部分 AWC |
| 绝对天花板 | **36 kJ** | 5/8 KOM 实测 |
| CP | **300 W** | 5/8 反推 + FTP set |

## 5/10 v6.1 重核算（用 22 kJ/set 工作上限）

3 set × 3 cycles × (90s 330W + 30s 450W):
- 每 cycle = 7.2 kJ
- 每 set = **21.6 kJ ← 几乎榨干 22 kJ 工作池**
- 累积 3 sets（5min reload @ 80% 重建率）：
  - Set 1: 22 → 0.4 → 5min reload → ~17 kJ
  - Set 2: 17 → -4.6 (**借 AWC 4.6**) → 5min → ~10 kJ
  - Set 3: 10 → -11.6 (**总 AWC 16 kJ，超 12 kJ AWC 池**)
- **结论**：v6.1 set 3 大概率完成不了或代价大

## 修正方案

| 方案 | 设计 | W'/set | TSS | 评价 |
|---|---|---|---|---|
| A 保守 | 3 set × 2 cycles × 450W | 14.4 kJ | ~75 | ✓ 完全可行 |
| **B 中等推荐** | 3 set × 3 cycles × **400W** | **17.1 kJ** | **~90** | **✓ 在池内 + 训练 race 节奏** |
| C 极限 (v6.1 维持) | 3 set × 3 cycles × 450W | 21.6 kJ + 借 AWC | 92 名义 | ⚠ set 3 难完成 |

待用户决定。默认推荐 B。

## 元教训：第 7 种盲区 / 不做核算就引用

之前已识别 6 种 sycophancy / 失误：
1. 顺着用户说
2. 乐观估计给台阶
3. "你在变好"叙事
4. 均值代替常规
5. 过时数据源
6. 不做物理核算

**第 7 种**：**多源数据冲突时不做调和，挑一个就用**。9 个 W' 估计跨 3 倍，我之前一直用 25 kJ（ECP）当唯一值，没说清楚来源 + 没核 5/8 实测。结果设计 session 时漏掉 AWC 应急层 vs 工作池的区分。

新规则：所有"参数引用"如有 spread > 1.5x，必须列全源 + 给共识 + 标注哪种用法用哪个值。

## 触发器

- 后续 PB 测试更新 → 重核 9 源 W' 估计
- 5/8 类型的 race-day max effort 实测 → 更新 AWC 上限
- 用户选方案 A/B → 重推 5/10
