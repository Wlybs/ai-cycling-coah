from unittest.mock import MagicMock

from src.coach.deep_analyzer.report_composer import compose, validate_report
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


def test_compose_calls_gemini_and_returns_markdown():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = FAKE_REPORT
    fake_client.models.generate_content.return_value = fake_response

    activity = {"id": "i123", "date": "2026-04-15", "type": "vo2max",
                "duration_s": 3600, "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810}
    findings = [Findings(analyzer="pacing", metrics={}, verdict="起步冒进", evidence=[("x", "y")])]

    md = compose(
        activity=activity,
        findings=findings,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "right ACL post-op"},
        physiology={"cp_watts": 285, "w_prime_joules": 22000},
        activated_set={"pacing", "w_balance"},
        client=fake_client,
    )
    assert "今日结论" in md
    fake_client.models.generate_content.assert_called_once()
