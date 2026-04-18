from src.coach.periodization.types import Phase, IntensityTier, SessionType

def test_phase_enum_values():
    expected = {"BASE", "BUILD", "PEAK", "TAPER", "RACE", "TRANSITION"}
    assert {p.value for p in Phase} == expected

def test_intensity_tier_ordering():
    tiers = [IntensityTier.REST, IntensityTier.EASY, IntensityTier.MEDIUM,
             IntensityTier.HARD, IntensityTier.RACE_SIM]
    # 约定：order 由 ordinal 属性保证
    ordinals = [t.ordinal for t in tiers]
    assert ordinals == sorted(ordinals)

def test_session_type_matches_legacy_training_type():
    # 必须与 plan_generator.DayPlan.training_type Literal 一致，ICU 日历同步依赖
    expected = {"Rest", "Recovery", "Aerobic", "Tempo",
                "Threshold", "VO2max", "Neuromuscular", "Race"}
    assert {s.value for s in SessionType} == expected
