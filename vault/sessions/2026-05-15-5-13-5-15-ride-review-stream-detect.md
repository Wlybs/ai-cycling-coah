---
date: 2026-05-15
tags: [coach-session, ride-review, stream-onset-detect, hard-rule, race-week]
related: [[INDEX]] [[training-plan]] [[races]] [[decisions]] [[2026-05-12-30-30-overgated-execution]]
---

# 2026-05-15 ｜ 5/13 平王 + 5/15 龙井 race-rhythm 双骑分析(stream-detect 校正 + HARD RULE 升级)

## 用户原始请求
"同步我最近两次的骑行,并且分析" → 后续校正为 5/13 + 5/15。

## 数据快照（使用的证据）

```
[evidence: ftp_set=300W from athlete_snapshot.json updated 2026-05-15T12:49]
[evidence: 5/13 i147761142 平王环线休闲骑 — 106km / 1356m / 4h moving /
           AP 147W / NP 164W / IF 0.547 / TL 120 / HR 130-155 / W-bal 几乎没动]
[evidence: 5/15 i148355063 龙井 race-rhythm — 62km / 553m / 2h14min /
           AP 145W / NP 223W / IF 0.74 / TL 124 / HR avg 132 max 188 / W-bal min 6.9kJ]
[evidence: live wellness 2026-05-15: CTL=101.5 / ATL=97.6 / TSB=+3.9 / HRV=70 / RHR=46]
```

## sync 警告
trend_analyzer.py + refresh_physiology.py 持续失败(streams=list bug,既有警告);主数据正常。

## 教练判定

**5/13 平王环线休闲骑 (LSD 性质):**
- Plan: 100-120km/1000-1500m/AP 170-180W/190 TSS。Actual: 106km/1356m/AP 147W/120 TSS。
- 用户主动控速: 爬坡+平路 170-180W,下坡 0W → AP 被下坡比例稀释到 147W(NP 164W 印证 11.5% coast)
- 训练目标(长有氧+爬升+腿留血)达成,不是执行偏低,是 plan AP target 没扣下坡时间
- race week 这样做正确: 5/12 30/30 后 TSB -4.5,5/13 不再累 ATL,留腿给 5/15 race-rhythm

**5/15 龙井 race-rhythm opener (3 set × 3 reps):**

stream-onset-detect 校正后的真实输出(lap-based 看到的低估):

| Set | 稳态 lap → 真实 | spike lap-avg → 真实 peak | W' 烧 |
|---|---|---|---|
| Set 1 | 319W → **341W (+22W)** | 468W lap → **576W peak** | 15.6 kJ (65%) |
| Set 2 | 315W → **336W (+21W)** | 495W lap → **602W peak** | 16.5 kJ (70%) |
| Set 3 | 319W → **337W (+18W)** | 457W lap → **559W peak** | 14.4 kJ (61%) |
| 综合 | 318W → **338W** | 474W lap → **579W peak** | — |

- 稳态: target 315W,真实平均 **338W (+23W over target,9/9 命中)**
- spike: target peak 480W,真实 peak avg **579W (+99W over),9/9 超 480W**
- 完成度: **明显 over-target**(不是 lap-based 误判的"中等达标")
- W' 池每 set 烧 61-70%,5min 全休几乎回满 = race-rhythm 标准签名

**spike peak 形态:**
- Set 1: 639/597/491 (递减,末段 W' 烧到 8.3kJ 信号)
- Set 2: 562/613/630 (递增,全场最高 set)
- Set 3: 536/487/653 (V 形,487 是用户摇车踏频未拉,653 是末段冲刺保留)

**HR max 188 ≈ 个人 max,心血管端拉满。** "高湿度"是 ride 名字,但今日实际是 race-rhythm 训练 dose 完整交付。

## 处方

**5/16 commute 目标:**
- 目标 ~20 TSS,上限 25 TSS
- 单程 25km @ AP 130W,~50min ≈ 15 TSS
- 死守 AP < 150W
- 踩不到 10 TSS 也无所谓,只是 race day TSB 会再高 1-2 点
- 不要超 30 TSS

**race day 不安排**(用户明确不需要 coach 介入,他自己有节奏)。

## 触发器
- HRV 5/16 早 <55 或 RHR ≥52 → flag 异常,但不指定 dose(R18 阀门降级 hard rule)
- 5/16 不要超 30 TSS(race-1 hard rule)

## 元教训(写入 hard rule)

**违反 case 2026-05-15:** 直接用 ICU lap intervals.average_watts 做 5/15 spike 完成度判定,被用户当场指正。
- lap-based: spike 5/9 达 480W,稳态刚卡 315W
- stream-detect 校正: spike 9/9 超 peak 480W (+99W over),稳态 +23W over target
- 完成度判定从"中等达标"→"明显 over-target",量级翻转

**已落 hard rule:**
- `~/.claude/projects/-mnt-d-Cycling/memory/feedback_lap_alignment_drift.md` — 强化为"任何 rep 分析必须 invoke stream-onset-detect skill"
- `~/.claude/projects/-mnt-d-Cycling/memory/feedback_coach_session_protocol_v2.md` — 新增 R20 (stream-onset-detect mandatory),SessionStart hook 自动加载到每次 coach session 开场
- vault/INDEX.md 当前活跃旗标新增 HARD RULE 条目

**自检清单(出回复前问自己):**
1. 这次分析涉及 rep/set/interval 吗?
2. 我 invoke 了 stream-onset-detect skill 吗?
3. 我的 power 数字来源是 stream-detected 还是 lap-based?
4. 完成度判定基于 stream-detected 数字吗?
任何一项 No → STOP, restart from skill invocation.

## 也学到的次要点

- 5/13 LSD plan 写法应区分"爬坡+平路 target W" vs "整骑 AP",AP target 必须扣下坡比例
- Set 内 spike peak 形态(递减/递增/V 形)比 spike avg 更能反映身体状态
- race-rhythm 课 spike duration 在 lap-detected 13-22s 区间是正常的(户外摇车节奏)
