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
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.coach.phase1_injection import inject_phase1_context
from src.fetcher.icu_client import ICUClient
from src.utils.common import get_warehouse_dir, load_json, setup_encoding

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
    power_range_w: str | None = None
    hr_range_bpm: str | None = None
    workout_text: str | None = None  # ICU 原生 workout 文本（步数定义），格式: "- 15m 55% Warmup\n3x\n- 1m 150%\n- 1m 50%\n- 10m Z2 Cooldown"


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


def generate_plan(week_start=None, week_end=None, output_path: str | None = None) -> str:
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

_ZONE_PCT = {  # 用区间中位数转 %FTP
    "Z1": 0.50, "Z2": 0.65, "Z3": 0.825,
    "Z4": 0.975, "Z5": 1.125, "Z6": 1.35, "Z7": 1.75,
}


def _parse_duration(s: str) -> int:
    """'30m' → 1800, '8s' → 8, '1h' → 3600"""
    s = s.strip().lower()
    if s.endswith("h"):
        return int(float(s[:-1]) * 3600)
    if s.endswith("m"):
        return int(float(s[:-1]) * 60)
    if s.endswith("s"):
        return int(float(s[:-1]))
    return int(s)


def _parse_intensity(s: str) -> float:
    """'150%' → 1.50, 'Z1' → 0.50, 'Z4' → 0.975

    ZWO 只支持 %FTP；其它写法（如 '200W'）直接报错，不静默当成 50%。"""
    s = s.strip()
    if s.endswith("%"):
        return float(s[:-1]) / 100.0
    if s.upper() in _ZONE_PCT:
        return _ZONE_PCT[s.upper()]
    raise ValueError(f"无法解析强度 {s!r}：workout_text 只支持 'NN%' 或 Z1–Z7")


def _workout_text_to_zwo(text: str, name: str = "Workout", description: str = "") -> str:
    """把内部 workout_text 转成 ZWO XML。

    Workout text 语法：
      - <dur> <intensity> [文字注释]      → SteadyState
      Nx                                    → 接下来 2 行作为 on/off 重复 N 次
      - <dur1> <int1>                       → on
      - <dur2> <int2>                       → off
    其它内容（空行、非 - 开头）忽略。
    """
    import re
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    parts: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        m = re.match(r"^(\d+)x\s*$", ln)
        if m:
            reps = int(m.group(1))
            on = lines[i + 1].strip() if i + 1 < len(lines) else ""
            off = lines[i + 2].strip() if i + 2 < len(lines) else ""
            on_m = re.match(r"^-\s*(\S+)\s+(\S+)", on)
            off_m = re.match(r"^-\s*(\S+)\s+(\S+)", off)
            if on_m and off_m:
                on_d = _parse_duration(on_m.group(1))
                on_p = _parse_intensity(on_m.group(2))
                off_d = _parse_duration(off_m.group(1))
                off_p = _parse_intensity(off_m.group(2))
                parts.append(
                    f'<IntervalsT Repeat="{reps}" '
                    f'OnDuration="{on_d}" OffDuration="{off_d}" '
                    f'OnPower="{on_p:.3f}" OffPower="{off_p:.3f}"/>'
                )
                i += 3
                continue
            raise ValueError(f"重复块 {ln!r} 后必须紧跟两行 '- <时长> <强度>'（on / off）")
        m = re.match(r"^-\s*(\S+)\s+(\S+)", ln)
        if m:
            d = _parse_duration(m.group(1))
            p = _parse_intensity(m.group(2))
            parts.append(f'<SteadyState Duration="{d}" Power="{p:.3f}"/>')
        i += 1

    # 把首/尾的 SteadyState 转成 explicit Warmup/Cooldown，只影响图表分段显示。
    # 不能阻止 ICU 自动加 60min Z1 phantom warmup（实测无视 <Warmup>，
    # 见 vault/athlete.md「ICU ZWO 推送陷阱」），workout_text 设计时需预留。
    if parts:
        import re as _re
        m_first = _re.match(r'<SteadyState Duration="(\d+)" Power="([\d.]+)"/>', parts[0])
        if m_first:
            d, p = m_first.groups()
            parts[0] = f'<Warmup Duration="{d}" PowerLow="{p}" PowerHigh="{p}"/>'
        if len(parts) > 1:
            m_last = _re.match(r'<SteadyState Duration="(\d+)" Power="([\d.]+)"/>', parts[-1])
            if m_last:
                d, p = m_last.groups()
                parts[-1] = f'<Cooldown Duration="{d}" PowerLow="{p}" PowerHigh="{p}"/>'

    inner = "\n        ".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<workout_file>\n"
        "    <author>AI Coach</author>\n"
        f"    <name>{_xml_escape(name)}</name>\n"
        f"    <description>{_xml_escape(description)}</description>\n"
        "    <sportType>bike</sportType>\n"
        "    <tags></tags>\n"
        "    <workout>\n"
        f"        {inner}\n"
        "    </workout>\n"
        "</workout_file>\n"
    )


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _workout_external_id(date: str, slot: int = 1) -> str:
    """同一天第 1 个训练沿用旧 id（已推送事件仍能 upsert），第 2 个起加 _2/_3 后缀。"""
    base = f"vault_plan_{date.replace('-', '')}"
    return base if slot == 1 else f"{base}_{slot}"


def _build_event_payload(day: dict, slot: int = 1) -> dict:
    """构建 ICU 事件 payload。若 day 含 workout_text，则用 ZWO 文件方式上传以触发
    `workout_doc.steps` 正确解析（ICU 不接受纯 description text 解析为 steps）。
    slot：同一天第几个训练，用来区分 external_id。"""
    import base64
    workout_text = (day.get("workout_text") or "").strip()
    notes = (day.get("description") or "").strip()
    name = day["name"]
    date = day["date"]

    # event.description 只放 notes（不 append workout_text）
    # 否则 ICU 会解析 workout_text-format 行成 phantom steps
    event: dict = {
        "category": "WORKOUT",
        "type": day.get("icu_type", "Ride"),
        "name": name,
        "start_date_local": f"{date}T09:00:00",
        "description": notes,
        "indoor": day.get("indoor", False),
        "external_id": _workout_external_id(date, slot),
    }
    if day.get("target_tss"):
        event["icu_training_load"] = day["target_tss"]

    if workout_text:
        # 关键: ICU 用 ZWO 的 <description> 作为 event.description 源 (覆盖 PUT body).
        # 但 ICU 又会把 description 内的 "Nm/Nmin/Ns" 数字+单位错认为额外 workout steps,
        # 产生 phantom (e.g., "595m 海拔" → 595 分钟 phantom step). 中文化避免双解析.
        safe_notes = _sanitize_for_zwo_description(notes)
        zwo = _workout_text_to_zwo(workout_text, name=name, description=safe_notes)
        event["filename"] = f"{date}_{name[:24]}.zwo".replace(" ", "_")
        event["file_contents_base64"] = base64.b64encode(zwo.encode("utf-8")).decode("ascii")
    return event


def _sanitize_for_zwo_description(text: str) -> str:
    """ICU 解析 ZWO <description> 时把 N(s|m|min|h) 当 workout 步数, 产生 phantom steps.
    把这些 token 中文化 (米/秒/分钟/小时), parser 不识别就不会创建 phantom.

    保留数字本身 (用户可读), 仅替换单位:
      - "595m" → "595米", "777m / 1 圈" → "777米 / 1 圈" (海拔/距离)
      - "30min" → "30分钟", "1h" → "1小时"
      - "30s 140%" → "30秒 140%" (workout 行内片段)
      - "9-10 min" → "9-10 分钟"

    workout_text 块本身不会过这里 (走 _workout_text_to_zwo 解析路径)."""
    import re
    if not text:
        return text
    # min 必须在 m 之前替换 (避免 "30min" 先匹配 "m" → "30i米")
    # 顺序: min → h → s → m
    text = re.sub(r'(\d+(?:[.\-]\d+)?)\s*min\b', r'\1分钟', text)
    text = re.sub(r'(\d+(?:[.\-]\d+)?)\s*h\b', r'\1小时', text)
    text = re.sub(r'(\d+)\s*s\b', r'\1秒', text)  # 30s, 但避开 W/kg 之类
    # m 单独使用 (海拔/距离): 数字后空格/斜杠/标点/末尾, 避免 "m@" 这种
    text = re.sub(r'(\d+(?:\.\d+)?)\s*m(?=\s|/|$|，|。|,|;|:|\)|\*|、)', r'\1米', text)
    # km 不动 (km 后面字母不会被 ICU 当 minute 单位)
    return text


def _build_rest_payload(day: dict) -> dict:
    """Rest 日推送为 NOTE 标记，让 ICU 日历显示"完全休息"标签。"""
    return {
        "category": "NOTE",
        "name": day.get("name", "完全休息"),
        "description": day.get("description", "完全休息日，主动减少训练频率"),
        "start_date_local": f"{day['date']}T09:00:00",
        # 与训练事件分开命名，避免同日 upsert 互相覆盖
        "external_id": f"vault_rest_{day['date'].replace('-', '')}",
        "color": "gray",
    }


def _push_to_icu(plan: dict):
    """两步推送 (ICU 量化 quirk workaround):
    1) bulk upsert (notes 嵌入 ZWO description) - chart + desc OK, TSS 可能 phantom-inflated
    2) 对每个 WORKOUT event re-PUT 同 ZWO + target_tss - 强制 TSS 重算到 plan target
    Rest 日推送为 NOTE category。"""
    import requests
    icu = ICUClient()
    print("\n📤 步骤 1/2: bulk upsert (chart + notes)...")
    payload = []
    payload_to_day = []  # 平行列表, 索引对齐
    slots: dict[str, int] = {}  # date → 当天已排的训练数
    for day in plan.get("days", []):
        if day.get("training_type") == "Rest":
            payload.append(_build_rest_payload(day))
            payload_to_day.append(None)  # NOTE 不需要 step 2
        else:
            slots[day["date"]] = slots.get(day["date"], 0) + 1
            payload.append(_build_event_payload(day, slots[day["date"]]))
            payload_to_day.append(day)
    if not payload:
        print("  无可推送事件")
        return
    url = f"https://intervals.icu/api/v1/athlete/{icu.athlete_id}/events/bulk?upsert=true"
    r = requests.post(url, json=payload, auth=("API_KEY", icu.api_key), timeout=30)
    r.raise_for_status()
    results = r.json()
    print(f"  ✓ ICU 返回 {len(results)} 个事件")

    # 步骤 2: 重 PUT WORKOUT events (TSS 重算到 plan target)
    workout_results = [(r_e, day) for r_e, day in zip(results, payload_to_day) if day is not None]
    if workout_results:
        print(f"\n🔄 步骤 2/2: re-PUT {len(workout_results)} workouts (TSS 校准)...")
        import base64
        for r_e, day in workout_results:
            event_id = r_e.get("id")
            if not event_id:
                continue
            workout_text = (day.get("workout_text") or "").strip()
            if not workout_text:
                continue
            notes_safe = _sanitize_for_zwo_description((day.get("description") or "").strip())
            name = day["name"]
            zwo = _workout_text_to_zwo(workout_text, name=name, description=notes_safe)
            zwo_b64 = base64.b64encode(zwo.encode("utf-8")).decode("ascii")
            put_payload = {
                "type": day.get("icu_type", "Ride"),
                "category": "WORKOUT",
                "start_date_local": r_e.get("start_date_local"),
                "name": name,
                "filename": f"{day['date']}.zwo",
                "file_contents_base64": zwo_b64,
                "external_id": r_e.get("external_id"),
            }
            if day.get("target_tss"):
                put_payload["icu_training_load"] = day["target_tss"]
            rp = requests.put(
                f"https://intervals.icu/api/v1/athlete/{icu.athlete_id}/events/{event_id}",
                json=put_payload, auth=("API_KEY", icu.api_key), timeout=15
            )
            if rp.status_code != 200:
                print(f"  ✗ {day['date']}: HTTP {rp.status_code}")

    # 最终汇报
    print("\n📊 最终状态:")
    final_events = icu.get_events(plan['days'][0]['date'], plan['days'][-1]['date'])
    for e in sorted(final_events, key=lambda x: x.get('start_date_local','')):
        wd = e.get("workout_doc") or {}
        steps = len(wd.get("steps", []))
        desc_len = len(e.get("description") or "")
        mt = (e.get('moving_time') or 0) // 60
        print(f"  - {e.get('start_date_local','?')[:10]} | TSS={e.get('icu_training_load')} | dur={mt}m | steps={steps} | desc={desc_len}c | {e.get('name','')[:35]}")
    print("\n✅ 推送完成")


def update_plan_in_icu(plan: dict, event_ids: dict) -> dict:
    """按 date → event_id 映射，PUT 更新已存在的 ICU 事件。
    用于已经推送过的 plan 改格式后回写，无需先 delete 再 create。
    """
    icu = ICUClient()
    print("\n♻️ 更新 ICU 事件...")
    updated = 0
    for day in plan.get("days", []):
        if day.get("training_type") == "Rest":
            continue
        event_id = event_ids.get(day["date"])
        if not event_id:
            print(f"  ⚠ {day['date']} 无对应 event_id，跳过")
            continue
        event = _build_event_payload(day)
        try:
            icu.update_event(event_id, event)
            print(f"  ✓ {day['date']} {day['day_of_week']} — {day['name']} (id={event_id})")
            updated += 1
        except Exception as e:
            print(f"  ✗ {day['date']} {day['day_of_week']} — 更新失败 (id={event_id}): {e}")
    print(f"\n✅ 已更新 {updated} 个训练事件")
    return {"updated": updated}


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
