---
date: 2026-05-09
tags: [coach-session, icu-push, taper-week, infra-test]
related: [[races]] [[training-plan]] [[decisions]]
---

# 2026-05-09 ｜ ICU 日历推送首次验证 — 5/17 A 赛 taper 周

## 用户原始请求

> "这个课表你是否能推送到我的icu日志里？你可以推送一个最近的训练规划作为一次尝试"

## 推送内容

5/11-5/17 一周 7 个事件（含比赛日）：

| 日 | 课程 | 时长 | TSS | ICU event ID |
|---|---|---|---|---|
| 5/11 一 | Taper Day 1 主动恢复 | 35min | 22 | 109040856 |
| 5/12 二 | Sweet Spot 减量 2×10min @ 270W | 60min | 50 | 109040859 |
| 5/13 三 | Z1 清疲劳 | 45min | 25 | 109040864 |
| 5/14 四 | 短开腿 2×6min @ 290W | 50min | 45 | 109040866 |
| 5/15 五 | Z1 储能 | 30min | 18 | 109040874 |
| 5/16 六 | 赛前开腿 2×3min@315W + 30s@450W | 55min | 38 | 109040875 |
| 5/17 日 | A 赛 Climbing Race 1 | 60min | 80 | 109040881 |

总 weekly TSS ≈ 278。Theme: 5 天 taper（TSB 目标 0~+5）+ 赛日。

## 推送机制（现已验证可用）

1. 写 JSON 到 `coach_memory/plans/plan_<date>.json`，schema = `WeeklyPlan` (Pydantic)
2. 跑 `python scripts/push_plan.py --push --plan-file <path>`
3. 脚本内部 POST `/athlete/{id}/events` 逐天创建（Rest 类型跳过）
4. 跑 `python scripts/sync_events.py` 回拉验证

**注意**：不需要 LLM API（用户无 Gemini key 不是问题），我作为 coach 直接生成 JSON 即可。

## 设计原则（符合已有决策）

- **TSB 目标 0~+5**（4/1 永久协议，A 赛对你 high TSB 反 stale）
- **5/16 强制开腿，禁纯 Z1**（4/1 永久协议）
- **5/17 race 描述按 4 段实测节奏**（5/9 race-rhythm-analysis 决策）
- **所有功率值锚 FTP=300W**（5/9 撤回"FTP 保守"后维持）
- **5/9 RED 后第一天 5/11 仅 Z1 + 神经激活**，HRV 仍低则改完全 off

## 推送前 sanity check

- ✅ JSON schema 通过 Pydantic 验证
- ✅ 7 个事件全部 POST 成功，ICU 返回 ID
- ✅ sync_events 回拉确认 7 条入库
- ✅ 无 `--delete-existing`（calendar 原本空，无冲突）
- ✅ 总周 TSS 278 << 平时 600+，符合 taper 范畴

## 触发器

- 5/10 早 HRV 仍 < 60 → taper 起点前移到 5/11，5/11 改完全 off，整周延后 1 天（脚本支持 --delete-existing 后重推）
- 用户在 ICU 端调整任何事件 → 下次 sync 自动反映，**vault 这边的 plan JSON 不会被回写**（单向推送）
