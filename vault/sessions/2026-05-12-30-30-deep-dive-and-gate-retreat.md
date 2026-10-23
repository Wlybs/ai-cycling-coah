---
date: 2026-05-12
tags: [coach-session, 30-30, deep-analysis, gate-retreat, race-specific, plain-language]
related: [[training-plan]] [[INDEX]] [[decisions]]
---

# 2026-05-12 ｜ 30/30 课深度复盘 + HRV 阀门设计撤回

## 用户原始请求

"分析的我听不懂太抽象，说人话" → "1. 阀门设计很没用 2. 我做的是 12x3 按你课表 3. 分析要更深度，每个 reps 全覆盖"

## ATL/TSB 数字纠错

之前我估 ATL→112, TSB→-8 用错了基准日（把 wellness_history 里的"2026-05-12" entry 当成早晨快照，但它实际是当日 EOD 含今日 TSS 的累计）。

正确解读：
- 5/11 EOD ATL = 99.16（全休后）
- 5/12 EOD ATL = 106.07 ✓（含今日 30/30 TSS 149 + 通勤 TSS 2）
- 5/12 EOD TSB = 102.99 - 106.07 = -3.08 ✓（ICU 显示一致）
- 用户对，我之前手算错

## 36 reps 全维度深度发现

### 结构（用 start_index 反算 stream 时间）

实际 = **2 大 set × (8+4) ascent × 3 rep**：
- 第 1 大 set: rep 1-24（8 ascents），ascent 间 145-150s descent
- set 间长休: 331s (5.5 min)
- 第 2 大 set: rep 25-36（4 ascents），ascent 间 145-150s descent

vault 原设计是"3 set × 4 ascent × 3 rep"。用户超额前 4 ascent，更 race-specific（race 中没有"每 4 个坡就给 5min Z1"奢侈）。

### 8 大深层模式

**1. 「猛踩起步 + 飞踏维持」在每个 ascent 内 100% 复现**
- ascent r1: 踏频 82-93rpm + 扭矩 48-54 Nm（低踏频高扭矩冲击式起爆）
- ascent r2-3: 踏频 96-110rpm + 扭矩 37-45 Nm（高踏频低扭矩飞踏维持）
- 12 个 ascent 100% 复现 → 比赛跟车反应的肌肉记忆已固化，**比单纯 W' burner 价值更高**

**2. 心率响应一档一档上去**
- 第 1-4 ascent r1: HR 162-170
- 第 5-8 ascent r1: HR 167-172
- 第 2 set 4 ascent r1: HR 168-175
- peak HR 185 出现在 rep36（最后一个）→ 身体最后一档油门主动打开，不是硬撑

**3. 中段最猛 + 最后一搏反弹（非衰减）**
- A1 = 403W（warmup 没踩开，rep3 = 366W 全场第二低）
- A2-A6 持续爬升到 **A6 = 480W 顶峰**
- A7-S2.A3 平稳 450W
- **S2.A4 = 500W 反弹（rep34 = 531W 全场最高）**

**4. 左右脚平衡 46-56% — ACL 旧伤无显现**
- 36 reps L/R balance 平均 50%、跨度 46-56%
- 户外猛踩极端场景下仍均衡 → ACL+半月板术后腿已融合，**长期资产证据**

**5. 12 段真山地（不是平地间歇）**
- 每个 ascent r1 海拔涨 16-20m
- r2 海拔涨 8-12m（短缓段）
- r3 海拔涨 10-14m（再次拐入坡）
- 真陡坡-缓段-再陡的混合地形 → race-specificity 比纯室内 30/30 高一档

**6. 第一组前 3 reps 是问题点 → 热身不够**
- A1: 440 / 402 / **366W**（rep3 全场第二低）
- 从 rep4 开始锁到 455W+ 再没掉
- **诊断: 热身偏短**，"热身 1 ascent + 真练 11 ascent"，5/17 比赛若用今天热身节奏，第一波脱大集团 (10-15min) 会跟丢

**7. W' 池烧到 rep36 = 6462J（73% 利用率）**
- 起始约 24000J，最低 6462J 出现在最后一个 rep → 教科书级 W' burner 完成
- ascent 内消耗模式：r1 用 4500-7000J（起爆）/ r2 用 3000-4000J（飞踏轻消耗）/ r3 用 4500-6000J（再爆）
- **r2 总是消耗最少** → 印证「猛踩起步 + 飞踏维持」两阶段模式

**8. set 间 5min Z1 vs ascent 间 2min descent 在 W' 回血层面无显著差异**
- ascent boundary (145-150s) 回血 +9961-10432J
- set boundary (331s) 回血 +12230J
- 多 186s 只多回 +2000J → W' 池主要在前 60-90s 回血，后面曲线趋平
- **结论: 8+4 结构 = 4+4+4 结构在生理 effect 上等价，race-specificity 8+4 更优**

## 阀门设计撤回

历史 hit rate：
- 5/10 OU: 阀门 HRV=64 → 减量；user 覆盖做 full → A 级 → **阀门错**
- 5/11 RED: 阀门 HRV=52 → 全休；user 也休 → 共识（但 ground truth 不可知）
- 5/12 30/30: 阀门 HRV=60 → 27 reps；user 做 36 reps → A+ → **阀门错**

3 次决策阀门对 1 次错 2 次，作为"硬性 dose 上限"失败。

**撤回方案**：
- HRV 单日数值不再硬挂 reps 上限
- reps 数由 user 体感决定
- 阀门仅作"异常趋势信号"——HRV 连续 2-3 天下滑 + RHR 比 baseline 高 5+ bpm 持续 2 天 → 教练主动 flag，但**不指定 dose**

保留的理由：极端组合信号（HRV 断崖 + RHR 持续高）超出体感察觉范围，仍值得提醒。但单日 HRV 60 vs 65 这种细分档无用。

## 处方更新

- 5/13 早 HRV/RHR 仅作参考信号 → user 体感决定是否 REST 或轻骑
- 5/14 race-rhythm 3×3×450W：功率 450W 死守，reps 数 user 体感裁定
- 5/15-5/17 不变
- race day 起跑前 **30 min 真激活 + 含 2×30s 全力**（TSB +16 鲜过头需主动激活神经系统）
- **5/17 race day 实际改进**: 起跑前热身从今天发现的"热身偏短"教训 → 延长到 12-15 min 逐级加力到 380W

## 触发器

- 5/13 早若 HRV 比 baseline 跌 >15% **AND** RHR ≥52 → 教练 flag 异常组合，user 自行决定是否减量
- 单日异常值不再触发 dose 修改

## 元教训

- HRV 单日数值挂钩 dose 是套用文献公式，不顾用户真实历史 → 教练设计本身的过度抽象问题
- 用户在 ICU 项目里 5+ 年训练数据 + 体感校准 > 教科书 HRV 模型
- coach 价值在"看用户看不到的"——长期趋势 + 多维度数据交叉 + race-specificity 评估，**不在替用户做 dose 决策**
