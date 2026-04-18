import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from . import feature_detector, router, report_composer
from .sub_analyzers import pacing, w_balance, durability, climbing, target_align, historical_cmp
from .types import SummaryLatest, StateFile

LOG = get_logger("deep_analyzer")
SUB_FUNCS = {
    "pacing": lambda act, streams, wbal, phys, hist: pacing.analyze(act, physiology=phys),
    "w_balance": lambda act, streams, wbal, phys, hist: w_balance.analyze(act, physiology=phys, wbal_series=wbal),
    "durability": lambda act, streams, wbal, phys, hist: durability.analyze(act, personal_curve=phys.get("durability") if phys else None),
    "climbing": lambda act, streams, wbal, phys, hist: climbing.analyze(act, streams=streams or {}, physiology=phys),
    "target_align": lambda act, streams, wbal, phys, hist: target_align.analyze(act, physiology=phys),
    "historical_cmp": lambda act, streams, wbal, phys, hist: historical_cmp.analyze(act, history=hist or []),
}


def _stimulus_score(findings_list) -> float:
    verdicts = [f.verdict for f in findings_list]
    score = 0.5
    if "命中" in verdicts:
        score += 0.15
    if "W' 管理得当" in verdicts:
        score += 0.1
    if "过度依赖 W' 债务" in verdicts or "后段崩盘" in verdicts:
        score -= 0.2
    if "进步" in verdicts:
        score += 0.1
    if "退步" in verdicts:
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 2)


def _progression_flag(findings_list) -> str:
    for f in findings_list:
        if f.analyzer == "historical_cmp":
            if f.verdict == "退步":
                return "regression_severe" if f.metrics.get("confidence") == "high" else "regression_mild"
            if f.verdict == "进步":
                return "progression"
            if f.verdict == "持平":
                return "flat"
    return "flat"


def _next_plan_hints(findings_list) -> list[str]:
    hints = []
    for f in findings_list:
        if f.verdict == "过度依赖 W' 债务":
            hints.append("下次间歇延长恢复时长至 3:1 以保护 W' 恢复")
        if f.verdict == "起步冒进":
            hints.append("下次以目标功率下限起始，前两组压住")
        if f.verdict == "刺激错配" and f.metrics.get("under_prescription_flag"):
            hints.append("连续多次未达刺激——教练需提高目标区间下限")
    return hints


def analyze_one(
    activity: dict,
    streams: Optional[dict],
    wbal_series: Optional[dict],
    physiology_bundle: dict,
    athlete: dict,
    history: list,
    output_dir: Path,
    client,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    physiology_flat = {}
    cp_w = physiology_bundle.get("cp_w") or {}
    physiology_flat.update(cp_w)
    physiology_flat["durability"] = physiology_bundle.get("durability")
    physiology_flat["response"] = physiology_bundle.get("response")
    if wbal_series:
        physiology_flat["min_w_bal_pct"] = wbal_series.get("min_w_bal_pct")

    features = feature_detector.detect_features(activity, streams, physiology_flat, athlete)
    relevance = router.route(features)
    activated = {name for name, score in relevance.items() if score >= 0.5}

    findings_list = []
    for name in activated:
        try:
            findings_list.append(SUB_FUNCS[name](activity, streams, wbal_series, physiology_flat, history))
        except Exception as e:
            LOG.event(action=f"sub_{name}", activity_id=activity["id"], status="error", error=str(e))

    try:
        md = report_composer.compose(
            activity=activity,
            findings=findings_list,
            athlete=athlete,
            physiology=physiology_flat,
            activated_set=activated,
            client=client,
        )
    except Exception as e:
        LOG.event(action="compose", activity_id=activity["id"], status="error", error=str(e))
        (output_dir / f"{activity['id']}.raw.json").write_text(
            json.dumps([f.model_dump() for f in findings_list], ensure_ascii=False, indent=2)
        )
        return {"status": "report_failed", "error": str(e)}

    (output_dir / f"{activity['id']}.md").write_text(md, encoding="utf-8")
    trace = {
        "features": features.model_dump(),
        "relevance": relevance,
        "activated": sorted(activated),
        "findings": [f.model_dump() for f in findings_list],
    }
    (output_dir / f"{activity['id']}.trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))

    headline = next((f.verdict for f in findings_list if f.analyzer in ("pacing", "target_align", "historical_cmp")), "分析完成")
    summary = SummaryLatest(
        activity_id=activity["id"],
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        sub_analyzers_run=sorted(activated),
        headline_verdict=headline,
        stimulus_score=_stimulus_score(findings_list),
        progression_flag=_progression_flag(findings_list),
        next_plan_hints=_next_plan_hints(findings_list),
        knee_flag=(physiology_bundle.get("response") or {}).get("knee_loading", {}).get("flag"),
    )
    (output_dir / "summary_latest.json").write_text(summary.model_dump_json(indent=2))

    LOG.event(action="analyze_one", activity_id=activity["id"], duration_ms=int((time.monotonic() - t0) * 1000), status="ok")
    return {"status": "ok", "activated": sorted(activated)}


def analyze_new(
    activities_iter,
    physiology_bundle: dict,
    athlete: dict,
    output_dir: Path,
    client,
    load_streams=None,
    load_wbal=None,
    history_for=None,
) -> list:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "_state.json"
    state = StateFile.model_validate_json(state_path.read_text()) if state_path.exists() else StateFile()
    last_id = state.last_analyzed_activity_id
    results = []
    last_seen = last_id
    for activity in activities_iter:
        if last_id and activity["id"] == last_id:
            continue
        streams = load_streams(activity["id"]) if load_streams else None
        wbal = load_wbal(activity["id"]) if load_wbal else None
        history = history_for(activity) if history_for else []
        res = analyze_one(
            activity=activity,
            streams=streams,
            wbal_series=wbal,
            physiology_bundle=physiology_bundle,
            athlete=athlete,
            history=history,
            output_dir=output_dir,
            client=client,
        )
        results.append({"activity_id": activity["id"], **res})
        last_seen = activity["id"]
    state.last_analyzed_activity_id = last_seen
    state.last_analyzed_at = datetime.now(timezone.utc).isoformat()
    state_path.write_text(state.model_dump_json(indent=2))
    return results
