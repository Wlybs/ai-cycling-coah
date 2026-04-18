"""
Phase 1 个性化体能注入：将确定性模型生成的生理数据注入到计划生成 prompt 中。

读取 coach_memory/ 下的 physiology、deep_analysis 数据，
渲染为结构化文本块，追加到 base prompt 末尾。
"""
import json
from pathlib import Path


def _load_json_safe(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tail_reports(dir_: Path, n: int = 5) -> list[str]:
    if not dir_.exists():
        return []
    md_files = sorted(dir_.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    return [f.read_text(encoding="utf-8") for f in md_files]


def render_phase1_context_block(physiology, durability, response, summary, recent_reports) -> str:
    lines = ["\n---\n## Phase 1 个性化体能注入（由确定性模型生成）\n"]

    if physiology:
        cp = physiology.get("cp_watts")
        wp = physiology.get("w_prime_joules")
        r2 = physiology.get("fit_r_squared")
        ftp = physiology.get("athlete_ftp_set")
        delta = physiology.get("cp_vs_ftp_delta_w")
        lines.append(f"- **个人 CP {cp}W / W' {wp}J**（拟合 R²={r2}）；与设定 FTP {ftp}W 偏差 {delta:+d}W。规划强度时以 **CP 而非 FTP** 作为阈值。")

    if durability and durability.get("decay_rate_pct_per_1000kj"):
        decay = durability["decay_rate_pct_per_1000kj"]
        lines.append(f"- **耐力衰减率**：60s 档 {decay.get('60s', 0)}%/1000kJ，5min 档 {decay.get('300s', 0)}%/1000kJ。长距离/赛前补能策略按此比例推。")

    if response and response.get("types"):
        parts = []
        for t, stats in response["types"].items():
            parts.append(f"{t}={stats['tolerance_class']}")
        lines.append(f"- **各类刺激耐受画像**：{', '.join(parts)}。对 `low` 类刺激延长恢复，对 `high` 类可提高频率/强度。")
        knee = response.get("knee_loading", {})
        if knee.get("flag"):
            lines.append(f"- **右膝负荷标记**：{knee['flag']}（90 日内摇车 {knee.get('standing_climb_minutes_90d', 0)} 分钟）。避免连续多天出现摇车爆发动作。")

    if summary:
        lines.append(f"- **最近一次深度分析**：{summary.get('headline_verdict', '')}（stimulus={summary.get('stimulus_score')}，progression={summary.get('progression_flag')}）。")
        if summary.get("next_plan_hints"):
            lines.append("  - 执行下列 hints：")
            for h in summary["next_plan_hints"]:
                lines.append(f"    * {h}")

    if recent_reports:
        lines.append("\n### 最近 5 篇深度分析摘要（下次怎么办段已由系统抽取）")
        for md in recent_reports:
            if "## 下次怎么办" in md:
                idx = md.index("## 下次怎么办")
                end = md.find("##", idx + 3)
                block = md[idx: end if end > 0 else len(md)].strip()
                lines.append(block + "\n")

    lines.append(
        "\n**硬规则**：若最近 3 次 stimulus_score 均 < 0.4，说明存在系统性 under-prescription — "
        "把周 TSS 目标提高到历史 90 天峰值的 90%。默认一周 1 天**完全休息**（不安排恢复骑），除非 response.high 允许。\n"
    )
    return "\n".join(lines)


def inject_phase1_context(base_prompt: str, base_dir: Path | None = None) -> str:
    base_dir = Path(base_dir) if base_dir else Path.cwd()
    physiology = _load_json_safe(base_dir / "coach_memory" / "physiology" / "cp_w_current.json")
    durability = _load_json_safe(base_dir / "coach_memory" / "physiology" / "durability.json")
    response = _load_json_safe(base_dir / "coach_memory" / "physiology" / "response_profile.json")
    summary = _load_json_safe(base_dir / "coach_memory" / "deep_analysis" / "summary_latest.json")
    recent = _tail_reports(base_dir / "coach_memory" / "deep_analysis", n=5)

    if not any([physiology, durability, response, summary]):
        return base_prompt

    return base_prompt + render_phase1_context_block(physiology, durability, response, summary, recent)
