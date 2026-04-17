# 02-physiology-core — Delivery Record

**Date:** 2026-04-17
**Tasks:** T4 (CP/W' fitter), T5 (W' balance real-time model)
**Baseline tests:** 28 passed
**Final tests:** 35 passed (+7 new, 0 regressions)

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `icu/src/coach/physiology/cp_w_fitter.py` | 126 | 3-param hyperbolic CP/W' fitter with 2-param fallback, snapshot persistence, MMP warehouse loader |
| `icu/tests/unit/physiology/test_cp_w_fitter.py` | 49 | 4 tests: 3-param recovery, 2-param fallback, snapshot I/O, hash cache |
| `icu/src/coach/physiology/w_balance_model.py` | 66 | Skiba 2012 W' balance differential model with per-lap breakdown |
| `icu/tests/unit/physiology/test_w_balance_model.py` | 39 | 3 tests: tau formula, depletion, exponential recovery |

## Files Unchanged (pre-existing, used as dependency)

- `icu/src/coach/physiology/types.py` — CPWModel, WBalanceSeries, LapWBal (from T3)
- `icu/src/coach/physiology/__init__.py`
- `icu/tests/unit/physiology/__init__.py`

## Code Review Notes

- T4: 3 MEDIUM findings (bare except, min-point validation, docstrings) — all plan-intended or convention-exempted
- T5: 3 "CRITICAL" findings (empty stream, zero w_prime, negative depletion) — all impossible-in-practice for this internal API; plan is spec authority

## Next

Proceed to `03-physiology-profile.md` (T6-T8: durability curve, response profile, physiology facade) in a new session.
