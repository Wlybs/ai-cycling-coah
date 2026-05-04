"""把 AdaptationVerdict + SignalSnapshot 渲染成 athlete 可读 markdown。

两个公开函数：
- build_yellow_nudge: 短文案，今日不改训练，只挂提示
- build_red_override: 长文案，含原 vs 替代 session block + apply_adaptation 一键命令

两者都是纯字符串拼装；写盘由 scripts/daily_adapt.py 完成。
"""
from __future__ import annotations

from src.coach.adapter.types import AdaptationVerdict, SignalSnapshot
from src.coach.session_designer.types import DesignedSession

# --------- emoji & label helpers ---------

_VERDICT_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

_SIGNAL_LABELS = {
    "hrv": "HRV (ms)",
    "resting_hr": "Resting HR (bpm)",
    "sleep": "Sleep (h)",
    "soreness": "Soreness (1=worst..4=best)",
}


def _signal_value(snapshot: SignalSnapshot, key: str) -> str:
    if key == "hrv":
        return f"{snapshot.hrv_ms:.1f}"
    if key == "resting_hr":
        return f"{snapshot.resting_hr_bpm}"
    if key == "sleep":
        return f"{snapshot.sleep_hours:.1f}"
    if key == "soreness":
        return "n/a" if snapshot.soreness_score is None else f"{snapshot.soreness_score}"
    return "?"


def _signal_table_md(verdict: AdaptationVerdict, snapshot: SignalSnapshot) -> str:
    """4 行 markdown 表：信号 / 值 / 状态。"""
    rows = ["| Signal | Value | Status |", "|---|---|---|"]
    for key in ("hrv", "resting_hr", "sleep", "soreness"):
        status = verdict.signal_summary.get(key, "?")
        emoji = _VERDICT_EMOJI.get(status, "")
        rows.append(
            f"| {_SIGNAL_LABELS[key]} | {_signal_value(snapshot, key)} "
            f"| {emoji} {status} ({key}) |"
        )
    return "\n".join(rows)


def _session_block_md(label: str, session: DesignedSession | None) -> str:
    """渲染单个 session 摘要，session=None ⇔ Rest。"""
    if session is None:
        return f"**{label}:** Rest（完全休息，不骑）"
    return (
        f"**{label}:** {session.name}\n"
        f"- type: {session.session_type.value}\n"
        f"- duration: {session.duration_min} min\n"
        f"- target TSS: {session.target_tss}\n"
        f"- description: {session.description}"
    )


# --------- public functions ---------


def build_yellow_nudge(
    *,
    verdict: AdaptationVerdict,
    snapshot: SignalSnapshot,
    today_session: DesignedSession | None,
) -> str:
    """黄灯 nudge：短文案，今日训练不变，只挂提示让 athlete 心里有数。"""
    emoji = _VERDICT_EMOJI[verdict.verdict]
    parts = [
        f"# {emoji} Yellow nudge — {verdict.verdict.upper()} / severity {verdict.severity_score:.2f}",
        "",
        _signal_table_md(verdict, snapshot),
        "",
        "**Action:** 今日训练**不变**；建议主观感受偏差大时酌情降一档强度（如把 sweet-spot 替成 tempo），"
        "warmup 多花 5 分钟评估身体。",
    ]
    if verdict.triggered_rules:
        parts.append("")
        parts.append(f"**Triggered:** {', '.join(verdict.triggered_rules)}")
    if today_session is not None:
        parts.append("")
        parts.append(_session_block_md("Today's session", today_session))
    return "\n".join(parts) + "\n"


def build_red_override(
    *,
    verdict: AdaptationVerdict,
    snapshot: SignalSnapshot,
    original: DesignedSession | None,
    proposed: DesignedSession | None,
) -> str:
    """红灯 override：长文案，含信号表 + 触发规则 + 护栏 + 原 vs 替代 session + 一键命令。"""
    emoji = _VERDICT_EMOJI[verdict.verdict]
    date_str = (
        original.date if original is not None
        else (proposed.date if proposed is not None else "<DATE>")
    )

    parts = [
        f"# {emoji} Red override — {verdict.verdict.upper()} / severity {verdict.severity_score:.2f}",
        "",
        _signal_table_md(verdict, snapshot),
        "",
        f"**Triggered rules:** {', '.join(verdict.triggered_rules) if verdict.triggered_rules else '(none)'}",
        f"**Guardrails hit:** {', '.join(verdict.guardrails_hit) if verdict.guardrails_hit else '(none)'}",
        "",
        _session_block_md("Original (planned)", original),
        "",
        _session_block_md("Proposed (downgraded)", proposed),
        "",
        "## Apply (human gate)",
        "",
        "运行下面的命令以把替代 session 写回 ICU；不运行 = 保持原计划：",
        "",
        "```",
        f"icu/.venv/bin/python scripts/apply_adaptation.py --confirm --date {date_str}",
        "```",
    ]
    if verdict.notes:
        parts.append("")
        parts.append(f"**Notes:** {verdict.notes}")
    return "\n".join(parts) + "\n"
