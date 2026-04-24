# Phase 2 Acceptance Checklist

**Prerequisites**
- [ ] Phase 1 全部 T1–T24 已合并 master 且绿
- [ ] Phase 2 所有单元测试 + 集成测试 `pytest tests/ -v` 全绿
- [ ] `.env` 中 `GEMINI_API_KEY` 可用
- [ ] 当前 `coach_memory/physiology/cp_w_current.json` 最新（运行过 `refresh_physiology.py`）
- [ ] 当前 `coach_memory/deep_analysis/summary_latest.json` 最新（运行过 `run_deep_analysis.py`）

**Structural checks**
- [ ] `python scripts/periodization_audit.py` 打印当前 phase 合理（与本周实际情况对应）
- [ ] 输出列出 macro 窗口、meso pattern、micro 7 日；每日 tier 和 TSS 的模式与 phase 匹配
  - BASE 周：no HARD days, ≥80% low intensity
  - BUILD 周：至少 2 个 HARD day，间隔 ≥48h
  - TAPER 周：总 TSS 相对 BUILD 降 40%+，仍保留 HARD 短刺激
  - RACE 周：赛前 2 天必须 REST
- [ ] 若最近有 A 级赛在 ≤10 天，audit 显示 `Phase: TAPER`

**Quality checks vs legacy plan_generator**
运行对比：
```
python scripts/plan_preview.py --week 2026-04-27      # v2
python scripts/push_plan.py --week 2026-04-27          # v1 legacy (without --push)
```
- [ ] 两份 `reports/plan_YYYYMMDD_v1.json` / `_v2.json`（手工重命名对比）
- [ ] v2 的 power_range_w **使用 CP 而非 set FTP**（取 threshold 日对比，差异应 ≈ `cp_vs_ftp_delta_w`）
- [ ] v2 的 weekly_tss_target 与当前 CTL 成比例（Build: CTL × 5.8 ± 10%）
- [ ] v2 有 trace.json 记录每日 template_name 和 CP 来源；v1 没有
- [ ] v2 的 description 文本（prose 启用时）引用具体 CP/W'/kJ 数字，不是通用 "保持强度" 之类的空话

**Safety checks**
- [ ] 若 `response_profile.json` 的 `knee_loading.flag == 'caution'`，当周不含两个连续 standing climb 日
- [ ] 若 response_profile 某个 tolerance_class == 'low'，当周对应 session type 不做连续 HARD
- [ ] 周 REST 日 ≥ `intent.rest_days_per_week`

**Fallback test**
- [ ] 临时 rename `coach_memory/physiology/` → `physiology.bak`，跑 `push_plan.py --engine v2`，期望 v2 报 error 并自动回退 v1，不中断用户
- [ ] 恢复后再跑一次，v2 正常

**Performance**
- [ ] `generate_plan_v2(push=False)` 本地全程 < 10 秒（未调 Gemini）
- [ ] `generate_plan_v2(push=True)` 全程 < 30 秒（含 1 次 Gemini 调用 + ICU push）

**Observability**
- [ ] `logs/periodization_engine.log` 有 `action: refresh_periodization` 条目
- [ ] `logs/generate_plan_v2.log` 有 `action: generate_plan_v2 status: ok` 条目
- [ ] `logs/session_designer_prose.log` 有 prose_generate 条目（若启用）

**Regression**
- [ ] `scripts/push_plan.py`（不带 `--engine`）依然走 legacy，输出和 Phase 1 状态一致
- [ ] Phase 1 CLI：`analyze_rides`、`physiology_audit` 不受影响
- [ ] ICU 日历推送在 `--engine v2 --push` 下产生正确的 events（手工在 ICU 网页上确认 7 条 event 包含描述）

**Sign-off**
- [ ] 操作者：__________ 日期：__________
- [ ] 确认所有上述项全部通过；否则列出未通过项并开 bd issue。
