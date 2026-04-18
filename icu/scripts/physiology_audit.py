"""Prints current physiology snapshot vs last-available prior snapshot."""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def main():
    argparse.ArgumentParser(description="Physiology audit — current CP/W', durability, response").parse_args()
    physiology = REPO / "coach_memory" / "physiology"
    current = _read(physiology / "cp_w_current.json")
    history_dir = physiology / "history"
    prior = None
    if history_dir.exists():
        files = sorted(history_dir.glob("cp_w_*.json"))
        if files:
            prior = _read(files[-2]) if len(files) >= 2 else _read(files[-1])

    def line(label, cur, pri):
        if cur is None:
            return f"{label}: n/a"
        if pri is None:
            return f"{label}: {cur} (no prior)"
        delta = cur - pri
        return f"{label}: {cur}  (Δ {delta:+})"

    if current:
        p_cp = prior["cp_watts"] if prior else None
        p_wp = prior["w_prime_joules"] if prior else None
        print(line("CP(W)", current["cp_watts"], p_cp))
        print(line("W'(J)", current["w_prime_joules"], p_wp))
        print(f"fit R\u00b2: {current.get('fit_r_squared')}")
        print(f"model: {current.get('model')}")
    else:
        print("no cp_w_current.json yet — run refresh_physiology.py")

    durability = _read(physiology / "durability.json")
    if durability:
        print("\nDurability decay (%/1000kJ):", durability.get("decay_rate_pct_per_1000kj"))

    response = _read(physiology / "response_profile.json")
    if response:
        print("\nTolerance classes:")
        for t, stats in (response.get("types") or {}).items():
            print(f"  {t}: {stats['tolerance_class']}  (n={stats['sessions_n']}, avg TSS {stats['avg_tss']})")
        knee = response.get("knee_loading") or {}
        if knee.get("flag"):
            print(f"\n\u26a0\ufe0f knee flag: {knee['flag']} (standing minutes 90d: {knee.get('standing_climb_minutes_90d')})")


if __name__ == "__main__":
    main()
