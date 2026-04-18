"""
训练计划生成器：调用 Gemini API 生成结构化周训练计划，并可同步到 ICU 日历。

输出两份文件：
  reports/plan_YYYYMMDD.md   — 教练分析文本（可读）
  reports/plan_YYYYMMDD.json — 结构化计划数据（供日历同步）
"""
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.common import setup_encoding, get_warehouse_dir, load_json
from src.fetcher.icu_client import ICUClient
from src.coach.phase1_injection import inject_phase1_context

load_dotenv(override=True)
setup_encoding()

WAREHOUSE = get_warehouse_dir()
MEMORY_DIR = os.path.join(os.path.dirname(WAREHOUSE), "coach_memory")
REPORTS_DIR = os.path.join(os.path.dirname(WAREHOUSE), "reports")
ICU_ROOT = os.path.dirname(WAREHOUSE)

MODEL = "gemini-2.5-flash"


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


# ─── Gemini Client ────────────────────────────────────────────────────────────

def _make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未设置，请在 .env 中填入")

    proxy_port = os.getenv("PROXY_PORT")
    if proxy_port:
        import httpx
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        transport = httpx.HTTPTransport(proxy=proxy_url)
        http_client = httpx.Client(transport=transport)
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(httpx_client=http_client),
        )
    return genai.Client(api_key=api_key)


# ─── Plan Generation ──────────────────────────────────────────────────────────

def generate_plan(week_start=None, week_end=None, push_to_icu=False) -> dict:
    """
    生成结构化周训练计划。返回计划 dict。

    week_start/week_end: date 对象，默认下周一到周日。
    push_to_icu: 是否将计划推送到 ICU 日历。
    """
    if week_start is None:
        week_start, week_end = _next_week_range()

    client = _make_client()

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
4. 考虑骑手的快肌纤维优势和 ACL 恢复史
5. 朝向5月爬坡赛目标推进
6. coaching_summary 控制在200字以内"""

    prompt = inject_phase1_context(prompt)

    print(f"\n{'='*60}")
    print(f"🗓️  生成训练计划 — {week_start} 至 {week_end}")
    print(f"{'='*60}\n")
    print("💭 [Gemini 生成中...]\n")

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WeeklyPlan,
        ),
    )

    plan = json.loads(response.text)

    # 打印摘要
    print(f"📋 本周主题: {plan.get('focus_theme', '-')}")
    print(f"🎯 周 TSS 目标: {plan.get('weekly_tss_target', '-')}")
    print(f"\n{plan.get('coaching_summary', '')}\n")
    print(f"\n{'─'*40}")

    icon_map = {
        "Rest": "😴", "Recovery": "🟢", "Aerobic": "🔵",
        "Tempo": "🟡", "Threshold": "🟠", "VO2max": "🔴",
        "Neuromuscular": "⚡", "Race": "🏆"
    }
    for day in plan.get("days", []):
        icon = icon_map.get(day["training_type"], "📅")
        print(f"{icon} {day['date']} {day['day_of_week']:3s} | {day['name']:<22} | "
              f"{day.get('duration_min', 0):>3}min TSS={day.get('target_tss', 0):>3} | "
              f"{day.get('power_range_w', '') or day.get('hr_range_bpm', '') or '-'}")

    # 保存报告
    os.makedirs(REPORTS_DIR, exist_ok=True)
    date_tag = week_start.strftime("%Y%m%d")

    json_path = os.path.join(REPORTS_DIR, f"plan_{date_tag}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(REPORTS_DIR, f"plan_{date_tag}.md")
    _save_plan_markdown(plan, md_path)

    usage = response.usage_metadata
    print(f"\n\n{'='*60}")
    print(f"✅ 计划已保存: {json_path}")
    if usage:
        print(f"📊 Token: 输入={usage.prompt_token_count} 输出={usage.candidates_token_count}")
    print(f"{'='*60}\n")

    if push_to_icu:
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
