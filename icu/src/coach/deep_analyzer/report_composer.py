import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .types import Findings

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "report_system.md"
SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _session_line(activity: dict) -> str:
    dur = int(activity.get("duration_s", 0) / 60)
    np = activity.get("np_watts", "-")
    tss = activity.get("tss", "-")
    if_val = activity.get("if", "-")
    kj = activity.get("total_kj", "-")
    return f"{dur} 分钟 · NP {np} W · TSS {tss} · IF {if_val} · {kj} kJ"


def _activated_checklist(activated_set: set[str]) -> str:
    lines = []
    for name in SUB_ANALYZERS:
        mark = "x" if name in activated_set else " "
        lines.append(f"- [{mark}] {name}")
    return "\n".join(lines)


_ATHLETE_COACH_KEYS = (
    "id", "icu_athlete_id", "name", "firstname", "lastname",
    "weight", "icu_weight", "weight_kg", "height",
    "sex", "icu_date_of_birth", "icu_resting_hr",
    "type", "medical",
)
_SPORT_SETTINGS_COACH_KEYS = (
    "ftp", "indoor_ftp", "w_prime", "p_max",
    "power_zones", "power_zone_names",
    "sweet_spot_min", "sweet_spot_max",
    "lthr", "max_hr", "hr_zones", "hr_zone_names", "hr_load_type",
    "mmp_model",
)


def _slim_athlete(athlete: dict) -> dict:
    """Project raw ICU athlete dict to coaching-relevant fields.

    Drops Run/Swim/Other sportSettings, strips Ride settings to key fields,
    removes ICU admin/sync/notification noise. Non-ICU caller-projected fields
    (weight_kg, type, medical, ...) pass through unchanged."""
    if not isinstance(athlete, dict):
        return athlete
    out = {k: athlete[k] for k in _ATHLETE_COACH_KEYS if k in athlete}
    settings = athlete.get("sportSettings")
    if isinstance(settings, list):
        ride_entry = next(
            (s for s in settings if isinstance(s, dict) and "Ride" in (s.get("types") or [])),
            None,
        )
        if ride_entry:
            out["sportSettings_ride"] = {
                k: ride_entry[k] for k in _SPORT_SETTINGS_COACH_KEYS if k in ride_entry
            }
    return out


def _slim_physiology(physiology: dict) -> dict:
    """Drop debug-only fields (raw MMP point list) from physiology bundle."""
    if not isinstance(physiology, dict):
        return physiology
    return {k: v for k, v in physiology.items() if k != "data_points_used"}


def _filter_findings(findings_json: list[dict]) -> list[dict]:
    """Drop findings whose verdict indicates the analyzer had no signal.

    The coach report shouldn't allocate prose to 'no-data' verdicts; trace.json
    (written separately by the orchestrator) preserves them for debugging."""
    return [f for f in findings_json if f.get("verdict") != "数据不足"]


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


def build_prompt(
    activity: dict,
    findings: Iterable[Findings],
    athlete: dict,
    physiology: dict,
    activated_set: set[str],
) -> str:
    """Build the full deep-analysis prompt (system prompt + JSON payload).

    Pure function, no I/O, no LLM call. The returned string is ready to paste
    into Gemini CLI / Claude Code coach mode; the pipeline writes it to a
    `<id>.prompt.md` file for the user to consume manually.
    """
    system_prompt = _load_system_prompt()
    findings_json = _filter_findings([f.model_dump() for f in findings])
    user_payload = {
        "activity_id": activity["id"],
        "date": activity.get("date", ""),
        "type": activity.get("type", ""),
        "session_line": _session_line(activity),
        "athlete": _slim_athlete(athlete),
        "physiology": _slim_physiology(physiology),
        "findings": findings_json,
        "activated_checklist": _activated_checklist(activated_set),
    }
    payload_text = json.dumps(user_payload, ensure_ascii=False, indent=2)

    return system_prompt + "\n\n---\n\n输入 JSON：\n```json\n" + payload_text + "\n```"
