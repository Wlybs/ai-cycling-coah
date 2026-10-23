---
date: 2026-05-09
tags: [coach-session, icu-push, infra, zwo, debugging]
related: [[sessions/2026-05-09-icu-push-test]] [[decisions]]
---

# 2026-05-09 ｜ ICU 推送通道升级 — 加 ZWO 文件让 workout chart 正确渲染

## 用户原始请求

> "我在 icu 上无法看到你的每一天课表的具体详细课程"

## 根因

第一次推送只塞了 `description` 文本 + `category=WORKOUT`，缺 `workout_doc.steps` → ICU 只显示文字描述，无 workout 图。

## 排查路径（关键发现）

1. ICU API 返回的 `workout_doc.steps` 总是 `[]` 即使 description 里有 `- 30m 50%` 格式
2. 社区例子用纯 description text 自称能 render，**实测不行** — `icu_intensity` 是从 `target_tss + moving_time + FTP` 反推（NP² × t / FTP² × 3600 × 100），不是从 description 解析
3. 真正触发 workout chart 的方式 = 上传 ZWO/FIT 文件 (base64) 走 `/events/bulk?upsert=true` 端点
4. ZWO 上传后 ICU 服务器解析为结构化 steps + 自动重算 TSS（更准）

## 修复

### plan_generator.py 新增函数
- `_parse_duration` / `_parse_intensity` — 解析内部 `30m`/`Z1`/`150%` 语法
- `_workout_text_to_zwo` — 内部 workout_text → ZWO XML
- `_xml_escape` — XML 实体转义
- 重写 `_build_event_payload` — 自动生成 ZWO 并 base64 编码
- 重写 `_push_to_icu` — 改用 bulk upsert 端点 + external_id 去重

### DayPlan schema 加字段
- `workout_text: Optional[str]` — ICU 原生 workout 文本（步数定义）

### Workout text 语法（内部约定）
```
- <duration> <intensity> [文字]      → SteadyState
Nx                                     → 接下来 2 行作为 on/off 重复 N 次
- <on_dur> <on_intensity>
- <off_dur> <off_intensity>
```
- 时长: `30m`/`8s`/`1h`
- 强度: `50%`(=0.50 FTP) 或 `Z1-Z7`(取区间中位数)

## 推送验证（5/11-5/17 重推后）

| 日期 | 名称 | steps | TSS（ICU 重算） | IF |
|---|---|---|---|---|
| 5/11 | Taper Day 1 主动恢复 | 2 (warmup + 3x sprint) | 15 | 51.9% |
| 5/12 | Sweet Spot 减量 | 3 | 51 | — |
| 5/13 | Z1 清疲劳 | 1 | 19 | — |
| 5/14 | 短开腿激活 | 3 | 43 | — |
| 5/15 | Z1 储能 | 1 | 13 | — |
| 5/16 | 赛前开腿 | 6 (warmup+build+2x+sprint+CD) | 44 | 69.6% |
| 5/17 | A 赛 | 0 (无 workout text，纯文字) | 80 | — |

ICU 端 description 自动剥离 workout text 行（已被 chart 渲染），保留中文 coach 注释 → 最干净 UX。

## 后续 plan 推送惯例

1. coach 设计 plan 时，每个 day 必须有 `workout_text` 字段（race 日除外）
2. `external_id` 用 `vault_plan_<YYYYMMDD>` 自动去重
3. 重推同周自动 upsert，无需 `--delete-existing`
4. ICU 重算的 TSS 比 coach 估的更准，以 ICU 为准

## 触发器（什么会改这套）

- ICU 改 API → 重新走排查路径
- 用户报"workout chart 看到一半就没了" → 检查 ZWO XML 是否合法
- 用户报"TSS 算高/低" → 调 workout_text 强度数字
