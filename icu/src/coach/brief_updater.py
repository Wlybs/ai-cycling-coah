import json
import re
from pathlib import Path

BEGIN = "<!-- BEGIN: phase1_coach_brief -->"
END = "<!-- END: phase1_coach_brief -->"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _recent_stimulus_trend(memory_dir: Path, n: int = 3) -> list[float]:
    da = memory_dir / "deep_analysis"
    if not da.exists():
        return []
    scores: list[float] = []
    # Read summary_latest's score as the most recent anchor
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    if summary:
        scores.append(summary.get("stimulus_score", 0.0))
    return scores


def render_brief(physiology, summary, recent_scores, response_knee) -> str:
    lines = [BEGIN]
    lines.append("## 当前画像（自动更新，勿手动编辑本段）")
    if physiology:
        delta = physiology.get("cp_vs_ftp_delta_w")
        delta_str = f"{delta:+d}W" if isinstance(delta, int) else "N/A"
        lines.append(
            f"- 个人 CP {physiology['cp_watts']}W / W' {physiology['w_prime_joules']}J"
            f"（vs 设定 FTP {physiology['athlete_ftp_set']}W，差 {delta_str}）"
        )
    if summary:
        lines.append(
            f"- 最近深度分析：{summary['headline_verdict']}"
            f"（stimulus={summary['stimulus_score']}, {summary['progression_flag']}）"
        )
    if recent_scores:
        lines.append(
            f"- 近 {len(recent_scores)} 次 stimulus 均值 = "
            f"{round(sum(recent_scores) / len(recent_scores), 2)}"
        )
    if response_knee:
        lines.append(f"- 右膝负荷标记：{response_knee}")
    lines.append(END)
    return "\n".join(lines)


def update_brief(gemini_path: Path, memory_dir: Path) -> None:
    physiology = _load(memory_dir / "physiology" / "cp_w_current.json")
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    response = _load(memory_dir / "physiology" / "response_profile.json") or {}
    knee_flag = (
        response.get("knee_loading", {}).get("flag")
        if isinstance(response, dict)
        else None
    )
    scores = _recent_stimulus_trend(memory_dir)

    block = render_brief(physiology, summary, scores, knee_flag)

    content = gemini_path.read_text(encoding="utf-8") if gemini_path.exists() else ""
    if BEGIN in content and END in content:
        new = re.sub(
            rf"{re.escape(BEGIN)}.*?{re.escape(END)}",
            block,
            content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        new = content.rstrip() + "\n\n" + block + "\n"
    gemini_path.write_text(new, encoding="utf-8")
