---
date: 2026-05-12
tags: [coach-session, plan-execution, race-week, 30-30, w-prime-burner, hrv-gate, over-execution]
related: [[training-plan]] [[races]] [[decisions]] [[INDEX]]
---

# 2026-05-12 ｜ 5/12 30/30 超闸门 1.33×执行 A+ — race day TSB 投射偏高 +10~+13

## 用户原始请求

"训练结束，分析今日的训练" → 第一轮误判 12:01 通勤为唯一记录；用户纠正"今天两次骑行"后重 sync 抓到 09:40 30/30 课。

## 数据快照（使用的证据）

**今日两次活动：**

1. **i147394122 真正 30/30 课**（09:40-11:46）
   - moving 7542s / 53.8km / 爬升 817m / **户外** 山地路线
   - 名称: "答辩结束后Morning 无氧刺激 Ride"
   - NP 253W / IF 84% / TSS 149 / icu_joules_above_ftp 201kJ
   - 36 真 30s work reps (avg≥350W 筛出): 完成 36/36 = full plan dose
   - rep avg = 459W (target 145% = 435W) → 完成度 105.5% (超 24W)
   - rep max 平均 615W peak 821W / HR max 平均 175 peak 187 (≈ max HR)
   - rep cadence 98rpm / recovery 段 27.6s @ 106W (合规 Z1)
   - W'_bal: start 18046J → end 13520J (mean); 单 rep 最低烧到 6462J (剩 28.6% / 烧 71.4% — 正中 W' burner target 区间 70-85%)
   - 4 分段衰减 Q1=441W Q2=471W Q3=454W Q4=470W → **negative split**，后三段全部高于 Q1

2. **i147394394 答辩后通勤** (12:01-12:15)
   - 13:52 / 5.46km / 平地 / NP 97W / TSS 2 / ICU 自动标 RECOVERY
   - 2 个 ≥400W spike 大概率红绿灯/路口起步

**早晨 wellness：**
- HRV=60 / RHR=47 / 睡眠 6.35h (欠睡)
- 闸门规则 60-65 → 27 reps (减量版); 用户超闸门做 36 reps (1.33×)
- TSB 5/12 早 -3.1 → 课后估算 -8~-10
- 单日 151 TSS / HARD RULE 200 内安全 / TSB > -20 安全

## sync 警告

- 第一轮 sync_data.py 只拉了 12:01 一条 detail，**漏了 09:40 30/30 课**
- 用户主动纠正后用 `sync_activity_detail.py 5 2` 重抓最近 5 个 / 2 天，才捕获完整执行
- **lesson**: 一天两次活动场景下 sync_data.py 的默认抓取条数不够，需要 confirm "今天还有别的 ride 吗?" 再继续
- 已知 streams list-vs-dict bug（trend_analyzer / refresh_physiology）不影响 summary

## 教练判定

这是 **超闸门 1.33× 执行的成功兑现**——闸门要 27 reps，用户做 36 reps，且单 rep 平均 459W 超 target 435W 整 24W (105.5%)。判定 A+ 的三条硬证据：
1. **negative split** (Q1→Q4 后三段都高于 Q1) — 节奏没崩、神经-代谢系统持续打开
2. **W' 池利用率 71.4%** — 正中 W' burner target 区间 (70-85%)
3. **HR max 187 ≈ max HR** — VO2 ceiling 真打到了

这是 race 前 race-specific lactate clearance + W' burner 完整剂量传递的**最后机会**且兑现了。配上 5/8 林峰 PR15 KOM (CP=300W 锚定) + 5/10 OU 4 set A 级 + 今日 30/30 A+ → race-specific 准备 5 月块**完整成型**。

**但要严肃指出代价**：
- 闸门是 forward-looking 风险管理，今天 ex-post 数据兑现不等于闸门规则错
- 答辩刚结束 + 睡眠 6.35h + 户外 53km/817m 爬升 + 36 reps super-145% → 心理-生理叠加压力比纯 TSS 显示的要重
- 5/13 早 HRV 是最直接 reality check
- race day TSB 投射偏高 (+10~+13, vs races.md 原目标 +0~+5) → 可能 "鲜过头"，起跑前主动开腿要做

## 处方

- **5/13 REST 不动**（确认 HRV 闸门第一道）
- **5/14 race-rhythm 3×3×450W 回到原计划**（不再升级为必做项，专项 dose 已凑齐）
  - HRV ≥60 → 完整 3×3×450W
  - HRV 55-59 → 砍 2×3 但功率守 450W 不打折
  - HRV <55 → 改 30min Z2 + 2×30s（信号 over-dose 没接住）
- 5/15 短-强 56 TSS 不变
- 5/16 commute <150W 不变
- 5/17 race day **起跑前 20-30 分钟主动开腿** (TSB 偏 +13 神经反应可能迟钝)
- **今晚睡眠睡回 7.5h+ 是头号优先**

## 触发器（什么会改这个判断）

- **5/13 早 HRV** 是最关键 reading
  - ≥60 → 一切按计划，今日 over-dose 身体接住了
  - 55-59 → 5/14 提前预备砍 2×3
  - <55 → 今日 over-dose 超出回血能力，5/14 改 30min Z2 + 2×30s，race day 战术降一档到 "守 podium 区"
- 5/13 早 RHR 若反弹回 52+ → 同上 <55 处理
- 5/14 race-rhythm 执行后 wbal_end mean 若 <8kJ → 5/15 短-强 砍掉冲刺段只留 3×4min

## 元教训

- **sync_data.py 不抓全当日活动**：一天多次 ride 默认只拉最近一条 detail，第一轮分析在错的数据上跑了 4 步才被用户纠正。下次 coach session 开场要先 `ls icu_data_warehouse/5_Activities_Detail/ | grep <today>` 确认条数，再 cross-check `4_Activities_List/`
- **第一轮基于 12:01 通勤评估，差点给用户写"超保守跳过 30/30"的反向判定**。Anti-sycophancy 防的是"用户 push back 我变心"，但 evidence 缺失下我会主动写错误判定——这种 false-evidence-leading 的失败比 sycophancy 还危险，因为没有 push-back 信号
- **HARD RULE 数据完整性**：coach session 不能信任 sync_data.py 默认输出，必须 cross-check 活动数量
