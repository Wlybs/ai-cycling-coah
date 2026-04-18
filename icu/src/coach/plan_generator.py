"""
训练计划生成器（API-free）：构建结构化周训练计划的 **完整 prompt**，
供用户手动粘贴到 Gemini CLI / Claude Code 教练模式。

职责：
  1. 汇总 coach_memory/ 与近期赛事，构建上下文
  2. 注入 Phase 1 生理档案（phase1_injection）
  3. 将最终 prompt 写到文件（默认 coach_memory/plans/<week>_prompt.md）

推送 ICU 日历的逻辑保留在 _push_to_icu()，由 scripts/push_plan.py 在
`--push --plan-file <path>` 时读取用户保存的 LLM 响应并推送。
"""
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Literal
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.common import setup_encoding, get_warehouse_dir, load_json
from src.fetcher.icu_client import ICUClient
from src.coach.phase1_injection import inject_phase1_context

setup_encoding()

WAREHOUSE = get_warehouse_dir()
MEMORY_DIR = os.path.join(os.path.dirname(WAREHOUSE), "coach_memory")
PLANS_DIR = os.path.join(MEMORY_DIR, "plans")
REPORTS_DIR = os.path.join(os.path.dirname(WAREHOUSE), "reports")
ICU_ROOT = os.path.dirname(WAREHOUSE)


# ─── Pydantic Schema ──────────────────────────────────────────────────────────

class DayPlan(BaseModel):
    date: str
    day_of_week: str
    training_type: Literal["Rest", "Recovery", "Aerobic", "Tempo",
                            "Threshold", "VO2max", "Neuromuscular", "Race"]
    icu_type: Literal["Ride", "WeightTraining", "Walk", "Run", "Rest"]
    name: str
    description: str
    duration_min: int
    target_tss: int
    indoor: bool
    power_range_w: Optional[str] = None
    hr_range_bpm: Optional[str] = None


class WeeklyPlan(BaseModel):
    week_start: str
    week_end: str
    coaching_summary: str
    focus_theme: str
    weekly_tss_target: int
    days: list[DayPlan]


# ─── 日期工具 ─────────────────────────────────────────────────────────────────

def _next_week_range():
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    monday = today + timedelta(days=days_until_monday)
    return monday, monday + timedelta(days=6)


# ─── 上下文构建 ───────────────────────────────────────────────────────────────

def _load_memory_context() -> str:
    """将 coach_memory/ 所有文件合并为文本。"""
    parts = []

    snapshot = load_json(os.path.join(MEMORY_DIR, "athlete_snapshot.json"))
    if snapshot:
        w_per_kg = snapshot.get('w_per_kg_ftp')
        wkg_str = f" ({w_per_kg} W/kg)" if w_per_kg else ""
        parts.append(f"""## 运动员当前状态
- FTP设定: {snapshot.get('ftp_set')}W{wkg_str}
- LTHR: {snapshot.get('lthr')}bpm | W': {snapshot.get('w_prime')}J
- 体重: {snapshot.get('weight_kg')}kg
- 更新时间: {snapshot.get('updated_at', '')[:10]}""")

        recovery = snapshot.get('recovery_signals') or {}
        if recovery.get('alerts'):
            alerts = "; ".join(recovery['alerts'])
            parts.append(f"""## ⚠️ 恢复告警 ({recovery.get('alert_level', 'yellow')})
- HRV 7d {recovery.get('hrv_7d_avg')} vs 30d {recovery.get('hrv_30d_baseline')}
- RHR 7d {recovery.get('rhr_7d_avg')} vs baseline {recovery.get('rhr_configured_baseline')}
- 触发: {alerts}
- 处理：下一节强度上限 IF ≤ 0.75；≥2 条同时触发，改为 48h Z1 + 活动恢复。""")

    fitness = load_json(os.path.join(MEMORY_DIR, "fitness_trend.json"))
    if fitness and fitness.get('current'):
        c = fitness['current']
        peak = fitness.get('peak_ctl_in_period')
        parts.append(f"""## 当前体能状态 (CTL/ATL/TSB)
- CTL: {c.get('ctl')} | ATL: {c.get('atl')} | TSB: {c.get('tsb')}
- Ramp Rate: {c.get('ramp_rate')}/周 | 近90天峰值CTL: {peak}
- 数据日期: {c.get('date')}""")

    history = load_json(os.path.join(MEMORY_DIR, "training_history.json"))
    if history:
        weeks = history.get('weekly_summary', [])[-6:]
        week_lines = "\n".join(
            f"  {w['week']}: TSS={w['tss']:>6.1f} | {w['rides']}次 | {w['distance_km']}km"
            for w in weeks
        )
        recent = history.get('recent_activities', [])[:10]
        ride_lines = "\n".join(
            f"  {r['date']} | {r['name'][:20]:<20} | TSS={r.get('tss') or '-':>5} | NP={r.get('np_watts') or '-':>4}W"
            for r in recent
        )
        parts.append(f"""## 近期训练历史
- 总骑行次数: {history.get('total_rides')} | 近4周均周TSS: {history.get('avg_weekly_tss')}

### 近6周TSS趋势
{week_lines}

### 最近10次骑行
{ride_lines}""")

    analysis = load_json(os.path.join(MEMORY_DIR, "training_analysis.json"))
    if analysis:
        intensity = analysis.get('intensity_distribution')
        if intensity:
            pol = intensity.get('polarization', {})
            parts.append(f"""## 训练强度分布 (近8周)
- 低强度: {pol.get('low_intensity_pct')}% | 中强度: {pol.get('medium_intensity_pct')}% | 高强度: {pol.get('high_intensity_pct')}%
- 极化指数: {pol.get('polarization_index')}%""")

        pc = analysis.get('power_curve_comparison', {}).get('comparison', {})
        if pc:
            kp = {k: pc[k] for k in ['5min', '20min', '60min'] if k in pc}
            curve_str = " | ".join(
                f"{k}: {v.get('90d_watts')}W ({v.get('pct_of_alltime')}%全生涯)"
                for k, v in kp.items()
            )
            parts.append(f"## 功率曲线 (90天 vs 全生涯)\n- {curve_str}")

        rr = analysis.get('race_readiness') or {}
        races = rr.get('races_within_window') or []
        if races:
            race_lines = "\n".join(
                f"- {r['date']} {r['name']} ({r['priority']}, {r['days_away']}d away)"
                for r in races
            )
            recs = rr.get('recommendation') or []
            rec_str = ("\n**教练指令:**\n" + "\n".join(f"- {r}" for r in recs)) if recs else ""
            parts.append(
                f"## 赛事准备度 (10 日窗口内)\n{race_lines}\n"
                f"- 目标 TSB: {rr.get('target_tsb_for_next_race', '未定')}{rec_str}"
            )

    adherence = load_json(os.path.join(MEMORY_DIR, "plan_adherence.json"))
    if adherence and adherence.get('summary'):
        s = adherence['summary']
        missed = ", ".join(s.get('missed_types') or []) or "无"
        parts.append(f"""## 上周计划执行情况
- 完成 {s.get('completed_days')}/{s.get('planned_days')} 天 | 合规率 {s.get('compliance_pct')}%
- TSS 实际/目标 = {s.get('tss_actual')}/{s.get('tss_target')} ({s.get('bias')})
- 漏掉类型: {missed}  → 本周若合理应优先补偿这些刺激""")

    for fname, label in [
        ("body_status.md",       "身体状况"),
        ("race_calendar.md",     "赛事日历"),
        ("nutrition_strategy.md","补给策略"),
        ("coach_log.md",         "教练日志"),
        ("periodization_2026.md","赛季宏观分期"),
        ("pb_reference.md",      "PB 与目标功率表"),
        ("workout_library.md",   "核心课表库"),
    ]:
        fpath = os.path.join(MEMORY_DIR, fname)
        if os.path.exists(fpath):
            content = open(fpath, encoding='utf-8').read().strip()
            if content:
                parts.append(f"## {label}\n{content}")

    return "\n\n".join(parts)


def _load_upcoming_races() -> str:
    events_path = os.path.join(WAREHOUSE, "8_Events", "events.json")
    events = load_json(events_path)
    if not events:
        return ""
    today = datetime.now().date()
    cutoff = today + timedelta(days=90)
    races = []
    for e in events:
        if e.get("category") not in ("RACE_A", "RACE_B", "RACE_C"):
            continue
        try:
            race_date = datetime.strptime(e.get("start_date_local", "")[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= race_date <= cutoff:
            races.append(f"  {race_date} | {e.get('name', '')} ({e['category']}) | 距今 {(race_date - today).days} 天")
    return ("## 近期目标赛事\n" + "\n".join(races)) if races else ""


def _load_system_prompt() -> str:
    gemini_md = os.path.join(ICU_ROOT, "GEMINI.md")
    if os.path.exists(gemini_md):
        return open(gemini_md, encoding='utf-8').read()
    return "You are an elite cycling coach. Data-driven, tactically ruthless. Respond in Chinese."


# ─── Prompt Building (API-free) ───────────────────────────────────────────────

def build_plan_prompt(week_start=None, week_end=None) -> str:
    """构建训练计划 prompt（不调用 LLM）。返回最终 prompt 字符串。

    week_start/week_end: date 对象，默认下周一到周日。
    """
    if week_start is None:
        week_start, week_end = _next_week_range()

    memory_ctx = _load_memory_context()
    races_ctx = _load_upcoming_races()
    system_prompt = _load_system_prompt()

    week_days_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days_list = "\n".join(
        f"  {(week_start + timedelta(days=i)).strftime('%Y-%m-%d')} ({week_days_cn[i]})"
        for i in range(7)
    )

    prompt = f"""{system_prompt}

---

{memory_ctx}

{races_ctx}

---

## 计划周期
{days_list}

请根据当前 CTL/ATL/TSB 状态、近期训练负荷和目标赛事，制定一份科学且可执行的7天训练计划。

要求：
1. 与当前体能状态（TSB）匹配，高疲劳时降负荷
2. 体现训练极化原则，避免垃圾里程
3. 每天给出具体可执行的功率/心率目标（不能模糊）
4. 考虑骑手的快肌纤维优势；ACL 属既往病史，除非 physiology knee_loading flag 非空或骑手明确反馈膝痛，**不要**在计划里提及膝盖/ACL
5. 朝向5月爬坡赛目标推进
6. coaching_summary 控制在200字以内

## 输出格式要求
请以符合以下 JSON schema 的 JSON 返回结构化计划（便于后续 push 到 ICU 日历）：

```
WeeklyPlan:
  week_start: str (YYYY-MM-DD)
  week_end:   str (YYYY-MM-DD)
  coaching_summary: str (<=200 字)
  focus_theme: str
  weekly_tss_target: int
  days: list[DayPlan]

DayPlan:
  date: str (YYYY-MM-DD)
  day_of_week: str (周一/周二/...)
  training_type: Rest | Recovery | Aerobic | Tempo | Threshold | VO2max | Neuromuscular | Race
  icu_type: Ride | WeightTraining | Walk | Run | Rest
  name: str
  description: str
  duration_min: int
  target_tss: int
  indoor: bool
  power_range_w: str | null   # 例：\"250-280W\"
  hr_range_bpm: str | null    # 例：\"155-170bpm\"
```
"""

    return inject_phase1_context(prompt)


def generate_plan(week_start=None, week_end=None, output_path: Optional[str] = None) -> str:
    """构建 prompt 并保存到 `coach_memory/plans/<week>_prompt.md`（或显式路径）。
    返回写入文件的绝对路径。用户再手动粘贴到 Gemini CLI / Claude Code 教练模式。
    """
    if week_start is None:
        week_start, week_end = _next_week_range()

    prompt = build_plan_prompt(week_start=week_start, week_end=week_end)

    if output_path is None:
        os.makedirs(PLANS_DIR, exist_ok=True)
        date_tag = week_start.strftime("%Y-%m-%d")
        output_path = os.path.join(PLANS_DIR, f"{date_tag}_prompt.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n{'='*60}")
    print(f"🗓️  训练计划 prompt 已生成 — {week_start} 至 {week_end}")
    print(f"{'='*60}")
    print(f"\n📄 Prompt 文件: {output_path}")
    print("\n下一步：复制该文件内容粘贴到 Gemini CLI 或 Claude Code 教练模式，")
    print("获取结构化计划 JSON，保存为文本文件，再用 --push --plan-file 推送 ICU 日历。")
    print(f"{'='*60}\n")

    return output_path


def push_plan_from_file(plan_file: str) -> dict:
    """读取用户保存的 LLM 响应（JSON），解析为 WeeklyPlan，推送到 ICU 日历。"""
    with open(plan_file, encoding="utf-8") as f:
        raw = f.read()
    # 容错：可能包含 ```json 代码块围栏
    text = raw.strip()
    if text.startswith("```"):
        # 移除首行围栏
        text = "\n".join(text.splitlines()[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    plan = json.loads(text)
    # 存一份标准化 JSON 便于追溯
    os.makedirs(REPORTS_DIR, exist_ok=True)
    date_tag = plan.get("week_start", datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    json_path = os.path.join(REPORTS_DIR, f"plan_{date_tag}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    md_path = os.path.join(REPORTS_DIR, f"plan_{date_tag}.md")
    _save_plan_markdown(plan, md_path)
    print(f"\n✅ 计划已归档: {json_path}")
    _push_to_icu(plan)
    return plan


# ─── Markdown 报告 ────────────────────────────────────────────────────────────

def _save_plan_markdown(plan: dict, path: str):
    lines = [
        f"# 训练计划 — {plan['week_start']} 至 {plan['week_end']}\n",
        f"**主题**: {plan.get('focus_theme', '')}",
        f"**周 TSS 目标**: {plan.get('weekly_tss_target', '')}\n",
        f"## 教练说\n\n{plan.get('coaching_summary', '')}\n",
        "## 7天计划\n",
        "| 日期 | 星期 | 类型 | 训练 | 时长 | TSS | 功率/心率 |",
        "|------|------|------|------|------|-----|----------|",
    ]
    for day in plan.get("days", []):
        power = day.get("power_range_w") or day.get("hr_range_bpm") or "-"
        lines.append(
            f"| {day['date']} | {day['day_of_week']} | {day['training_type']} | "
            f"{day['name']} | {day.get('duration_min', 0)}min | "
            f"{day.get('target_tss', 0)} | {power} |"
        )
    lines.append("\n## 详细说明\n")
    for day in plan.get("days", []):
        lines.append(f"### {day['date']} {day['day_of_week']} — {day['name']}\n")
        lines.append(day.get("description", "") + "\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─── ICU 日历同步 ─────────────────────────────────────────────────────────────

def _push_to_icu(plan: dict):
    icu = ICUClient()
    print("\n📤 推送到 ICU 日历...")
    created = 0
    for day in plan.get("days", []):
        if day.get("training_type") == "Rest":
            continue
        event = {
            "start_date_local": f"{day['date']}T09:00:00",
            "type": day.get("icu_type", "Ride"),
            "category": "WORKOUT",
            "name": day["name"],
            "description": day.get("description", ""),
            "indoor": day.get("indoor", False),
        }
        if day.get("target_tss"):
            event["icu_training_load"] = day["target_tss"]
        try:
            result = icu.create_event(event)
            print(f"  ✓ {day['date']} {day['day_of_week']} — {day['name']} (id={result.get('id', '?')})")
            created += 1
        except Exception as e:
            print(f"  ✗ {day['date']} {day['day_of_week']} — 推送失败: {e}")
    print(f"\n✅ 已创建 {created} 个训练事件")


def delete_plan_events(week_start, week_end):
    """删除指定周内所有 WORKOUT 类型事件（用于重新推送）。"""
    icu = ICUClient()
    events = icu.get_events(week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"))
    deleted = 0
    for e in events:
        if e.get("category") == "WORKOUT":
            try:
                icu.delete_event(e["id"])
                print(f"  🗑️  已删除: {e.get('name', e['id'])}")
                deleted += 1
            except Exception as ex:
                print(f"  ✗ 删除失败 {e['id']}: {ex}")
    print(f"已删除 {deleted} 个计划事件")
