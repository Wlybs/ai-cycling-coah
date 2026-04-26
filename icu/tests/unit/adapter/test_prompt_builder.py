"""Unit tests for adapter.prompt_builder — yellow nudge + red override markdown."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.coach.adapter.prompt_builder import build_red_override, build_yellow_nudge
from src.coach.adapter.session_revisor import revise_session
from src.coach.adapter.types import AdaptationVerdict, SignalSnapshot
from src.coach.periodization.types import SessionType
from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import DesignedSession, SessionIntent


# ---------- Shared fixtures ----------

@pytest.fixture
def physiology() -> dict:
    return {"cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288}


@pytest.fixture
def durability() -> dict:
    return {"decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1}}


@pytest.fixture
def response_profile() -> dict:
    return {"types": {}}


@pytest.fixture
def signal_snapshot(fixed_utc_now) -> SignalSnapshot:
    return SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=44.0,
        resting_hr_bpm=58,
        sleep_hours=5.5,
        soreness_score=2,
    )


@pytest.fixture
def yellow_verdict() -> AdaptationVerdict:
    return AdaptationVerdict(
        verdict="yellow",
        signal_summary={"hrv": "yellow", "resting_hr": "green",
                        "sleep": "yellow", "soreness": "green"},
        severity_score=0.42,
        recommended_action="nudge_only",
        triggered_rules=["hrv_yellow_band", "sleep_yellow_band"],
        guardrails_hit=[],
        notes=None,
    )


@pytest.fixture
def red_verdict() -> AdaptationVerdict:
    return AdaptationVerdict(
        verdict="red",
        signal_summary={"hrv": "red", "resting_hr": "yellow",
                        "sleep": "red", "soreness": "yellow"},
        severity_score=0.81,
        recommended_action="propose_replacement",
        triggered_rules=["hrv_red_threshold", "sleep_red_threshold"],
        guardrails_hit=["consecutive_red_2_days"],
        notes=None,
    )


@pytest.fixture
def original_threshold_session(physiology, durability, response_profile) -> DesignedSession:
    intent = SessionIntent(
        day_of_week="Sun", tier=__import__("src.coach.periodization.types",
                                           fromlist=["IntensityTier"]).IntensityTier.HARD,
        target_tss=85, session_hint="threshold 2x20",
    )
    return compose_session(
        intent=intent, date=date(2026, 4, 19), template_name="threshold_2x20",
        physiology=physiology, durability=durability, response_profile=response_profile,
    )


@pytest.fixture
def proposed_recovery_session(physiology, durability, response_profile) -> DesignedSession | None:
    return revise_session(
        original_type=SessionType.THRESHOLD, original_date=date(2026, 4, 19),
        physiology=physiology, durability=durability, response_profile=response_profile,
    )


# ---------- build_yellow_nudge ----------

def test_yellow_nudge_contains_all_signal_keys(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    for key in ("hrv", "resting_hr", "sleep", "soreness"):
        assert key in md, f"yellow nudge missing signal key: {key}"


def test_yellow_nudge_contains_severity(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    assert "0.42" in md, "yellow nudge must show severity score"


def test_yellow_nudge_marks_yellow_status(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    # Either emoji or word
    assert ("🟡" in md) or ("yellow" in md.lower())


def test_yellow_nudge_keyword_only(yellow_verdict, signal_snapshot):
    with pytest.raises(TypeError):
        build_yellow_nudge(yellow_verdict, signal_snapshot, None)  # type: ignore[misc]


def test_yellow_nudge_returns_str(yellow_verdict, signal_snapshot):
    md = build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None)
    assert isinstance(md, str) and len(md) > 0


def test_yellow_nudge_accepts_today_session_optional(
    yellow_verdict, signal_snapshot, original_threshold_session,
):
    md_with = build_yellow_nudge(
        verdict=yellow_verdict, snapshot=signal_snapshot,
        today_session=original_threshold_session,
    )
    md_without = build_yellow_nudge(
        verdict=yellow_verdict, snapshot=signal_snapshot, today_session=None,
    )
    # 两种都返回 str；带 session 的应包含 session.name
    assert original_threshold_session.name in md_with
    assert original_threshold_session.name not in md_without


# ---------- build_red_override ----------

def test_red_override_contains_apply_command(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert "apply_adaptation.py" in md
    assert "--confirm" in md
    assert "2026-04-19" in md  # date 出现在命令


def test_red_override_lists_original_and_proposed_names(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert original_threshold_session.name in md
    assert proposed_recovery_session is not None
    assert proposed_recovery_session.name in md


def test_red_override_with_proposed_none_shows_rest(
    red_verdict, signal_snapshot, original_threshold_session,
):
    """proposed=None ⇔ Rest 推荐：文案应明示完全休息且仍带 --confirm 命令。"""
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=None,
    )
    assert "Rest" in md or "rest" in md.lower()
    assert "apply_adaptation.py" in md
    assert "--confirm" in md


def test_red_override_lists_triggered_rules_and_guardrails(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    for rule in red_verdict.triggered_rules:
        assert rule in md
    for guard in red_verdict.guardrails_hit:
        assert guard in md


def test_red_override_marks_red_status(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    )
    assert ("🔴" in md) or ("red" in md.lower())


def test_red_override_keyword_only(red_verdict, signal_snapshot, original_threshold_session):
    with pytest.raises(TypeError):
        build_red_override(  # type: ignore[misc]
            red_verdict, signal_snapshot, original_threshold_session, None,
        )


def test_red_override_no_auto_escalation_language(
    red_verdict, signal_snapshot, original_threshold_session, proposed_recovery_session,
):
    """RED_NO_AUTO_ESCALATE: 文案禁出现 'auto'/'automatic'/'background' 之类自动化字样。"""
    md = build_red_override(
        verdict=red_verdict, snapshot=signal_snapshot,
        original=original_threshold_session, proposed=proposed_recovery_session,
    ).lower()
    for forbidden in ("auto-escalate", "automatic", "auto_push", "background"):
        assert forbidden not in md, f"override 文案不得含自动化字样: {forbidden}"


# ---------- Purity ----------

def test_prompt_builders_no_file_io(
    yellow_verdict, red_verdict, signal_snapshot,
    original_threshold_session, proposed_recovery_session,
    monkeypatch,
):
    """两个函数都禁止任何文件写入：替换 Path.write_text / builtins.open(写) 触发即 FAIL。"""
    from pathlib import Path

    def _fail_write(*a, **kw):
        raise AssertionError("prompt_builder must not write to disk")

    monkeypatch.setattr(Path, "write_text", _fail_write)
    monkeypatch.setattr(Path, "write_bytes", _fail_write)

    real_open = open

    def _guard_open(file, mode="r", *a, **kw):
        if any(c in mode for c in ("w", "a", "x")):
            raise AssertionError(f"prompt_builder must not open() for write: mode={mode}")
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", _guard_open)

    build_yellow_nudge(verdict=yellow_verdict, snapshot=signal_snapshot,
                      today_session=original_threshold_session)
    build_red_override(verdict=red_verdict, snapshot=signal_snapshot,
                      original=original_threshold_session, proposed=proposed_recovery_session)
