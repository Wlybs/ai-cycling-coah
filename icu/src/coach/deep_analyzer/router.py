from .types import Features

SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]
THRESHOLD = 0.5  # exported for callers to filter activated analyzers


def route(features: Features) -> dict[str, float]:
    if features.is_race:
        return {k: 1.0 for k in SUB_ANALYZERS}

    scores = {
        "pacing": 0.9 if features.has_intervals else 0.2,
        "w_balance": 0.95 if features.has_intervals else (0.9 if features.w_prime_depleted else 0.3),
        "durability": 0.9 if features.is_endurance_long else 0.4,
        "climbing": 0.9 if features.has_climbing else 0.1,
        "target_align": 0.85 if features.target_type_claimed else 0.3,
        "historical_cmp": 0.6,  # always active — baseline comparison for every ride
    }
    return scores
