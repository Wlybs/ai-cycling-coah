---
date: 2026-05-25
tags: [coach-session, race-analysis, climbing-race, pingwang]
related: [[races]] [[athlete]] [[sessions/2026-05-09-race-rhythm-analysis]]
---

# 2026-05-25 ｜ 5/23 平王爬坡赛 (8th) 复盘 — 初轮分析待用户确认

## 用户原始请求
"分析我5/23的平王爬坡赛"

## 数据快照（使用的证据）
- ride id=150694988 "平王8th.." `icu_data_warehouse/5_Activities_Detail/2026-05-23_i150694988.json`
- 全程: 39.25km / 827m / 71min moving (elapsed 84min), NP 277W / IF 0.92 / TSS 101
- HR avg 177 / max 200; cad avg 98
- icu_pm_cp=291 / icu_pm_w_prime=24946 / icu_ftp=300

赛段拆分（4 个 icu_intervals）:
| # | 段 | 时长 | 距离 | 爬升 | AP | max W | HR avg/max | 备注 |
|---|---|---|---|---|---|---|---|---|
| 0 | 起步段 | 10:04 moving (23min elapsed, 等了 13min) | 3.97km | 187m | 287 | 577 | 179/189 | 4.7% 平均坡 |
| 1 | 中段平路 | 35:45 | 24.37km | 144m | 193 | 837 | 170/190 | rolling + surges |
| 2 | 主爬段 | 24:38 | 10.83km | 476m | **303** | 697 | **186/200** | **4.4% 平均坡** |
| 3 | 终点 | 0:31 | 78m | 2m | 38 | 67 | 193/199 | 滚过线 |

W' 池估算：
- 主爬 24:38 @ 303W (CP+12W) → W' 烧 ≈ 17.7 kJ (71% 池)
- 起步 10min @ 287W (CP-4W 但接近) + 577W spike → 额外 5-8 kJ
- 总池消耗 ≈ 23-26 kJ / 24.9 kJ pool → 基本榨干，与 HR max 200 一致

## sync 警告
无（5/23 detail 文件已存在，未触发 re-sync）

## 深度 stream 分析（第二轮，主体）

### 起步段 INT0 (10:04 moving)
- AP 288 / NP30 299 ≈ FTP / max 577 / CV 0.36
- HR avg 179 / max 189
- **W_bal 24.0 → 12.6 kJ (-47% in 10min)**
- 用户主观 RPE 4-5（满血时 FTP 强度感知就这样）
- **判定**：结构性烧池，不是 W' 管理失误。"位置靠前 + 缓坡 + 集团抢位"=爬坡起点赛的 architecture constant。不可训练、不可技术化。

### 中段 INT1 平路 (35:45)
- AP 193 / CV **0.76** / max **837W**
- **28 个 ≥400W surge**（前 10 大里 6 个 ≥700W：837/743/716/715/710/701）
- **W_bal 净回血 +9.5 kJ** (12.6→22.0)
- → 集团 rolling 中 surge 间隙够长 + draft 收益让你池子被填回去

### 主爬 INT2 (24:38, 10.83km / 476m / 4.4%)
- AP 303 / NP30 317 / max 697 / CV 全程 0.32
- **22 个 ≥400W surge**（平均每 67s 一个，dur 3-24s）
- **13 个 <200W ≥5s micro-recovery**
- 5 桶 negative split: 274 → 297 → 306 → 305 → **334W** (b5)
- CV: 0.41 → 0.33 → **0.26** → 0.25 → 0.33 (b3-b4 集团 paceline 最稳)
- HR 漂移 175→184→185→186→188→**191**→189 (200 max only in final sprint)
- **EF 反向 decoupling -5.8%**（上半 1.58 下半 1.67）— 但用户确认这不是"aerobic 富余"，是"已经在心率天花板，aerobic 池见顶"
- W_bal: 21.9 → 15.2 → 10.6 → 6.3 → 3.9 → **-7.1 kJ**（AWC 透支 7 kJ）

### 末段 counter at t+23:34
- 24s × avg 561W / max 697W
- 启动时 W_bal = **-36 J ≈ 0**
- 单次透支 6.5 kJ AWC（用户 AWC 池 ~10-12 kJ）
- 携能 200m 后衰减
- **数学校准的 counter 距离上限 = 200m**（W_bal=0 状态下 AWC 池只够 12-15s 全开）

## 教练判定（用户确认后落锁）

**初判被推翻 2 项，确认 1 项**：
- ❌ "缓坡赛相对弱"假说 **撤回** — 用户全程跟住 2-11 第一集团到线
- ❌ "起步 W' 提前破口"假说 **撤回** — interval 0 的 elapsed/moving 差是码表提前按的检录时间误差；moving 10min @ 287W 是站位靠前 + 集团出发节奏，不是被拉
- ❌ "5/24 race-3 留力"假说 **撤回** — 用户自评 5/23 = 90 分，按 A 级状态打的
- ✅ "功率不是名次原因" 确认 — 303W = FTP race-day 交付 + W' 71% 是合理集团节奏消耗

**真正原因 = counter 距离判断错** + **结构性 race-class ceiling**：
- 用户末段 500m counter，单飞实际携能 200m（W_bal=0 启动 + AWC 6.5 kJ 透支后衰减，数学上 500m 不可能成立）
- "看前面减速"判断 = 实际是 sprint 集结的 bunching，不是疲劳信号；用户在集团尾部读不到前组真实状态（结构性盲区）
- **race-class ceiling 5-10 名**: 用户确认"苟住第一集团 = allout"，没有 move-up 选项；爬坡起点缓坡赛 draft 收益巨大前组很难被打散
- 8th = race-class ceiling 中位置，发挥已经符合画像
- 真正可改 = 单一一条 race-day rule：**W_bal 见底状态 counter 距离上限 200m**

**自评打分校准（新增 athlete 信号）**：
- 3/28 = 75 / 4/25 = 80 / 5/17 = 5/23 = 5/24 = **90**
- 三场 5 月 race 同分 → race-day 体能/状态稳定上了一个台阶
- A/B race-day 切换无差异化（5/17 A = 5/23 B = 5/24 B 都按 90 打）
- 5/31 A 赛目标：在 90 分基线上加 5 分

## 处方

**训练框架不动**。5/26 taper 起点保持。

**唯一 race-day rule (新增到 athlete tactical)**:
> W_bal 见底状态的 counter，距离上限 200m。看到终点牌再开，看到 500m 牌等。不解读"前面对手减速"——在 climb-start 缓坡集团赛里减速 = sprint 集结，不是疲劳。

**move-up 选项不可用**：用户确认"苟住第一集团 = allout"，无主动驱动配速能力，counter 是唯一武器。

**5/24 单独建模**：用户确认 5/24 ≠ 同性质赛，今天的 counter ≤ 200m 数字只锁这类 climb-start 缓坡集团赛。5/24 待复盘时单独 stream 分析。

## 触发器
- 5/24 复盘 → 校准其他 race-class 的 counter 距离
- 5/31 race 性质 → 决定 counter rule 是否适用
- 若 race-class ceiling 5-10 名要突破 → 唯一方向是 AWC 池容量训练（10→12 kJ 上限），可推迟到 race 块结束后讨论
