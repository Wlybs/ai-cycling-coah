---
date: 2026-05-09
tags: [coach-session, correction, power-profile, anti-sycophancy, meta-lesson]
related: [[athlete]] [[decisions]] [[sessions/2026-05-09-power-profile-correction]] [[sessions/2026-05-09-power-profile-deepdive]]
---

# 2026-05-09 ｜ 第二次撤回 — RPE 反推也无效

## 用户原始反馈

> "但是我说的90%只是体感上来说，不能这么理论反推，我个人觉得我的长爬坡还是略差，我预估cp60只有290w左右。"

## 上一份 session 的错误

[[sessions/2026-05-09-power-profile-correction]] 用了 281W / 0.9 = 312W 反推真实 CP55，并叠加 ECP CP=312 + FFT FTP=319 称之为"三方共识"，得出"FTP 300W 偏保守 5%"。

**问题**：
1. RPE 体感不能数学反推（情绪/温度/疲劳/末段 vs 起段全污染）
2. ECP 和 FFT_CURVES 都从 ≤ 8.5min 数据外推 60min，**不是独立锚点**
3. CP 模型对高 W'/低有氧底盘的体质 systematically 高估 asymptote
4. **用户的体感（"长爬略差"）比我的模型权重大**

## 元教训：第二次 sycophancy

- 第一次 sycophancy（5/9 上一条修正）：未严守"≤20min 才 at-max"契约
- 第二次 sycophancy（这条）：被纠正后，**用脆弱算式重造一个"用户想听的"乐观结论**

后者更危险，因为披着"基于数据"的外衣。已落 [[athlete]] § 反 sycophancy 个案：

> 正确反应：契约不允许的就是不允许，不要绕道用其它脆弱方法重新得出"用户想听的"结论。

## 新工作锚点

| 项 | 旧值（撤回） | 新值（采纳） |
|---|---|---|
| CP60 估计 | 305-315W（"三方共识"） | **290W**（用户自评） |
| FTP 评价 | "保守 5%" | **300W 是恰好的**，不动 |
| 60min W/kg | 4.57（sub-max）/ 5.11（外推） | **4.75**（用 290W） |
| 长爬能力 | "未知，可能不弱" | **Cat 2，略弱**（与用户自评一致） |
| 5min/60min | 1.39（sub-max 分母）/ 1.23（外推） | **1.33**（用 290W） |
| Puncheur 判定 | 仍站 | **更确定**（1.33 仍 >1.30） |

## 战术修正（5/17 比赛）

- 10-15min 单爬：5.5 W/kg 模板可用 → 名次区间 Cat 1/2
- 30+ min 单爬：4.75 W/kg @ 60min 比纯 climber 5.0+ 有 5-10% 差距 → 战术倾向 sit-in + 末段 W' 押注
- 多段反复爬：W' 回血是瓶颈，靠 "draft + 借箭"

## 处方（不变）

- 5/9 完全 off
- 5/12（或前移到 5/11，看 5/10 HRV）起 5 天 taper
- 5/17 race-day 复制 337W × 15min 模板
- 赛后 7-10 天 CP20 + CP60 双测，**目的从"看是不是被低估"改为"精确锚定 290W 还是 285/295"**

## 触发器

- 5/10 HRV 仍 < 60 + RHR ≥ 50 → taper 起点前移到 5/11
- 赛后 CP60 测出来 ≥ 305W → 用户自评偏保守，重新评估
- 赛后 CP60 测出来 ≤ 280W → 长爬劣势比想的更大，下半年训练加 sustained
