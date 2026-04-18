import re
from pathlib import Path
from typing import Iterable

from .types import Findings

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "report_system.md"
SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _session_line(activity: dict) -> str:
    dur = int(activity.get("duration_s", 0) / 60)
    np = activity.get("np_watts", "-")
    tss = activity.get("tss", "-")
    if_val = activity.get("if", "-")
    kj = activity.get("total_kj", "-")
    return f"{dur} 分钟 · NP {np} W · TSS {tss} · IF {if_val} · {kj} kJ"


def _activated_checklist(activated_set) -> str:
    lines = []
    for name in SUB_ANALYZERS:
        mark = "x" if name in activated_set else " "
        lines.append(f"- [{mark}] {name}")
    return "\n".join(lines)


def validate_report(md: str) -> tuple[bool, list[str]]:
    reasons = []
    required_sections = ["## 今日结论", "## 关键发现", "## 下次怎么办"]
    for sec in required_sections:
        if sec not in md:
            reasons.append(f"missing section {sec}")
    findings_block = md.split("## 关键发现", 1)[-1].split("## 下次怎么办", 1)[0]
    subsections = re.findall(r"###\s+\d+\.", findings_block)
    for i, _ in enumerate(subsections):
        start = findings_block.find(f"### {i+1}.")
        end = findings_block.find(f"### {i+2}.") if i + 2 <= len(subsections) else len(findings_block)
        block = findings_block[start:end]
        if "> 证据:" not in block:
            reasons.append(f"finding {i+1} missing 证据 line")
    banned = re.search(r"NP 为 \d+W|IF 为 \d\.\d+", md)
    if banned:
        reasons.append(f"banned raw-metric restatement: {banned.group(0)}")
    return (len(reasons) == 0), reasons


def compose(
    activity: dict,
    findings: Iterable[Findings],
    athlete: dict,
    physiology: dict,
    activated_set: set[str],
    client,
    model: str = "gemini-2.5-flash",
) -> str:
    system_prompt = _load_system_prompt()
    findings_json = [f.model_dump() for f in findings]
    user_payload = {
        "activity_id": activity["id"],
        "date": activity.get("date", ""),
        "type": activity.get("type", ""),
        "session_line": _session_line(activity),
        "athlete": athlete,
        "physiology": physiology,
        "findings": findings_json,
        "activated_checklist": _activated_checklist(activated_set),
    }
    import json as _json
    payload_text = _json.dumps(user_payload, ensure_ascii=False, indent=2)

    prompt = system_prompt + "\n\n---\n\n输入 JSON：\n```json\n" + payload_text + "\n```"

    response = client.models.generate_content(model=model, contents=prompt)
    md = response.text
    return md
