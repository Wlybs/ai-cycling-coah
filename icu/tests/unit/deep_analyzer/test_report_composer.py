from src.coach.deep_analyzer.report_composer import build_prompt, validate_report
from src.coach.deep_analyzer.types import Findings


FAKE_REPORT = """# 活动 i123 深度分析 — 2026-04-15 vo2max

**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ

## 今日结论
刺激对位但 W' 管理偏激进，下周建议延长恢复区间。

## 关键发现

### 1. 节奏稳定但末段略掉
> 证据: 前1/3 320W 对比后1/3 280W，差值 +12.5%
- 结论: 典型起步冒进，可能吃掉后段储备
- 联系画像: Type II 占优，起步爆点是优势但需要配速控制

### 2. W' 债务过度
> 证据: 最低 W'bal 8%，低于15%累计 240s
- 结论: 已越过安全线，累积恢复不充分
- 联系画像: 62kg轻量运动员，W' 池小，债务管理对抗周容错率更低

## 下次怎么办
1. 将 VO2max 间歇组间休息延长到 3:1
2. 每周一次纯休息替代恢复骑

## 附:本次激活的分析维度
- [x] pacing
- [x] w_balance
- [ ] durability
- [ ] climbing
- [x] target_align
- [x] historical_cmp
"""


def test_validate_accepts_well_formed_report():
    ok, reasons = validate_report(FAKE_REPORT)
    assert ok, reasons


def test_validate_rejects_missing_evidence():
    bad = FAKE_REPORT.replace("> 证据:", "> Not evidence:", 1)
    ok, reasons = validate_report(bad)
    assert not ok


def test_build_prompt_contains_system_prompt_and_payload():
    activity = {"id": "i123", "date": "2026-04-15", "type": "vo2max",
                "duration_s": 3600, "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810}
    findings = [Findings(analyzer="pacing", metrics={"front_third_w": 320}, verdict="起步冒进", evidence=[("x", "y")])]

    prompt = build_prompt(
        activity=activity,
        findings=findings,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "right ACL post-op"},
        physiology={"cp_watts": 285, "w_prime_joules": 22000},
        activated_set={"pacing", "w_balance"},
    )

    # System-prompt section (loaded from prompts/report_system.md) must be present.
    # We only assert the static bridge markers injected by build_prompt itself,
    # plus characteristic payload content.
    assert "输入 JSON：" in prompt
    assert "```json" in prompt
    assert '"activity_id": "i123"' in prompt
    assert '"type": "vo2max"' in prompt
    assert '"activated_checklist"' in prompt
    # activated_set → checklist lines
    assert "[x] pacing" in prompt
    assert "[x] w_balance" in prompt
    assert "[ ] durability" in prompt
    # finding serialized
    assert '"analyzer": "pacing"' in prompt
    assert '"verdict": "起步冒进"' in prompt


def test_build_prompt_strips_athlete_noise():
    """Run/Swim/Other sportSettings and ICU admin fields must not bleed into payload."""
    noisy_athlete = {
        "id": "i1",
        "icu_weight": 62.0,
        "sex": "M",
        "icu_date_of_birth": "2003-12-02",
        "icu_api_key": "SECRET_KEY",
        "icu_send_activity_msg": True,
        "wahoo_user_id": "4417720",
        "sportSettings": [
            {"types": ["Ride"], "ftp": 300, "max_hr": 205, "lthr": 188,
             "mmp_model": {"criticalPower": 312, "wPrime": 21600},
             "activity_charts": {"home": None}},
            {"types": ["Run"], "ftp": None, "best_effort_distances": [400.0, 800.0]},
            {"types": ["Swim"], "threshold_pace": 0.83},
        ],
    }
    prompt = build_prompt(
        activity={"id": "i1", "duration_s": 100, "np_watts": 200, "tss": 10,
                  "if": 0.7, "total_kj": 50, "date": "2026-04-18", "type": "ride"},
        findings=[], athlete=noisy_athlete,
        physiology={"cp_watts": 300, "w_prime_joules": 20000},
        activated_set=set(),
    )
    assert "icu_api_key" not in prompt
    assert "SECRET_KEY" not in prompt
    assert "wahoo_user_id" not in prompt
    assert "icu_send_activity_msg" not in prompt
    assert "best_effort_distances" not in prompt
    assert "threshold_pace" not in prompt
    assert "activity_charts" not in prompt
    assert "sportSettings_ride" in prompt
    assert "mmp_model" in prompt
    assert '"ftp": 300' in prompt
    assert '"lthr": 188' in prompt


def test_build_prompt_drops_physiology_data_points_used():
    """data_points_used (raw MMP fit input) must not be embedded in the prompt.

    It's ~1800 lines of noise the LLM doesn't need; trace.json still has it."""
    physiology = {
        "cp_watts": 306,
        "w_prime_joules": 20870,
        "fit_r_squared": 0.916,
        "model": "3-param-hyperbolic",
        "data_points_used": [[1.0, 1296.0], [2.0, 1269.0], [3.0, 1243.0]],
        "durability": {"decay_rate_pct_per_1000kj": {"60s": 14.75}},
    }
    prompt = build_prompt(
        activity={"id": "i1", "duration_s": 100, "np_watts": 200, "tss": 10,
                  "if": 0.7, "total_kj": 50, "date": "2026-04-18", "type": "ride"},
        findings=[], athlete={}, physiology=physiology,
        activated_set=set(),
    )
    assert "data_points_used" not in prompt
    assert "1296.0" not in prompt
    # Keep result fields
    assert '"cp_watts": 306' in prompt
    assert '"fit_r_squared": 0.916' in prompt
    assert "decay_rate_pct_per_1000kj" in prompt


def test_build_prompt_filters_insufficient_data_findings():
    """Findings with verdict='数据不足' must not pollute the prompt — only
    substantive verdicts reach the LLM. Trace.json keeps everything."""
    findings = [
        Findings(analyzer="pacing", metrics={"vi_mean": 2.77}, verdict="后段崩盘",
                 evidence=[("front vs back", "x")]),
        Findings(analyzer="climbing", metrics={"reason": "no sustained climb"},
                 verdict="数据不足", evidence=[]),
        Findings(analyzer="historical_cmp", metrics={"reason": "no comparables"},
                 verdict="数据不足", evidence=[]),
    ]
    prompt = build_prompt(
        activity={"id": "i1", "duration_s": 100, "np_watts": 200, "tss": 10,
                  "if": 0.7, "total_kj": 50, "date": "2026-04-18", "type": "ride"},
        findings=findings, athlete={}, physiology={},
        activated_set={"pacing", "climbing", "historical_cmp"},
    )
    assert '"verdict": "后段崩盘"' in prompt
    assert '"verdict": "数据不足"' not in prompt
    assert '"analyzer": "climbing"' not in prompt
    assert '"analyzer": "historical_cmp"' not in prompt
    # Checklist (activation status) should still show all 3 as activated
    assert "[x] pacing" in prompt
    assert "[x] climbing" in prompt
    assert "[x] historical_cmp" in prompt


def test_build_prompt_is_pure_no_client_dependency():
    """build_prompt must not reach out to any network client. Passing no client
    argument is the API; this test just exercises it twice to confirm
    determinism / idempotence."""
    activity = {"id": "i1", "date": "2026-04-15", "type": "vo2max",
                "duration_s": 1800, "np_watts": 250, "tss": 40, "if": 0.87, "total_kj": 450}
    p1 = build_prompt(
        activity=activity, findings=[], athlete={}, physiology={},
        activated_set=set(),
    )
    p2 = build_prompt(
        activity=activity, findings=[], athlete={}, physiology={},
        activated_set=set(),
    )
    assert p1 == p2
