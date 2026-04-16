from src.coach.physiology.types import CPWModel, DurabilityCurve, ResponseProfile, PhysiologyBundle


def test_cpw_model_roundtrip():
    m = CPWModel(
        generated_at="2026-04-16T00:00:00Z",
        window_days=90,
        cp_watts=280,
        w_prime_joules=22000,
        t_k_seconds=-10.0,
        model="3-param-hyperbolic",
        fit_r_squared=0.97,
        data_points_used=[[60, 420], [300, 340], [1200, 290]],
        athlete_ftp_set=288,
        cp_vs_ftp_delta_w=-8,
    )
    restored = CPWModel.model_validate_json(m.model_dump_json())
    assert restored.cp_watts == 280
    assert restored.model == "3-param-hyperbolic"


def test_physiology_bundle_all_optional():
    bundle = PhysiologyBundle()
    assert bundle.cp_w is None and bundle.durability is None and bundle.response is None
