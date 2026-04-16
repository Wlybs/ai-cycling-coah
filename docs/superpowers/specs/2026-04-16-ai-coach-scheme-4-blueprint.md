# AI Coach — Scheme 4 Blueprint ("Deep Professional Coach Architecture")

**Date**: 2026-04-16
**Status**: Blueprint (top-level architecture reference; Phase specs reference this doc)
**Scope**: Top-level architecture for the AI cycling coach at `/mnt/d/Cycling/icu/`. This document is the shared north star; each Phase spec details one slice.

## Motivation

The existing coach — even after the 2026-04-15 pass — suffers from two systemic problems the user articulated concretely:

1. **Plan quality: conservative undertraining bias.** The coach defaults to "recovery rides" over rest, assigns weekly TSS below the athlete's demonstrated capacity, and cuts too much load during race-week taper. The user's last race following this coach resulted in "high HR, legs unable to produce power" — a textbook detraining outcome. Verbatim: "训练量过少或者停训太长,导致比赛的时候心率很高,腿踩不出来功率。"
2. **Analysis depth: surface-only metric repetition.** When asked for detailed lap / interval analysis, the coach only restates the metrics visible in ICU itself. Verbatim: "如果分析出来的数据我自己都能看出来的话,我还要这个教练有什么用?"

Root cause: the current system is fundamentally **"give Gemini a pile of JSON and let it guess a reasonable weekly plan."** There is no individualized physiological model, no persistent decision reasoning, no periodization framework, no forensic session interpretation, and no feedback loop that closes plan → execution → adjustment. The ceiling is prompt engineering.

## Design Principles

1. **Numeric reasoning stays in Python; LLMs only render prose.** Critical Power, W' balance, durability — all deterministic models. Gemini is never trusted to do math.
2. **Every decision is traceable.** A decision ledger records rationale + evidence + confidence for every plan change and interpretation.
3. **Modules are independently testable and independently shippable.** The architecture decomposes into phases that each ship a usable improvement on top of the previous state — no six-month "big bang" risk.
4. **Athlete-specific, not generic.** Every recommendation must be anchored in this athlete's physiology, response profile, and medical constraints (right-knee ACL/meniscus post-op, Type II fast-twitch dominance, 62 kg, hill-climb race specialty).
5. **Evidence-grounded.** Major planning decisions cite published protocol literature (Mujika taper, Seiler polarization, Skiba W', Allen-Coggan).

## Architecture — 11 Components

### 1. Physiology Model Layer — `icu/src/coach/physiology/`
Personalized deterministic models. Inputs: raw warehouse data. Outputs: snapshot JSONs in `coach_memory/physiology/`.
- **CP/W' fitter** — 3-parameter hyperbolic fit across athlete's own power-duration curve
- **W' balance real-time model** — Skiba-Clarke reversible integral, per-second across every activity
- **Durability curve** — power decay as function of cumulative kJ
- **Individual response profile** — athlete's response signature to each session type

### 2. Periodization Engine — `icu/src/coach/periodization/`
Three-layer structure (macro → meso → micro) with automatic phase detection (Base/Build/Peak/Taper/Race/Transition) from CTL slope and race calendar. Each phase has explicit physiological intent.

### 3. Session Designer (refactor of `plan_generator.py`)
Receives the current micro-cycle's physiological intent from the periodization engine; designs session structure from the physiology model rather than guessing. Hard Pydantic validation. Default rest > recovery ride unless explicit signal.

### 4. Deep Analyzer — `icu/src/coach/deep_analyzer/`
Feature-detector → relevance-router → six sub-analyzers (pacing, w_balance, durability, climbing, target_align, historical_cmp) → report composer (single Gemini call to render findings as coach-level Chinese prose).

### 5. Adaptation Engine — `icu/src/coach/adapter.py`
Daily post-sync check. Compares yesterday's actual execution + today's wellness against active plan. Three traffic-light outcomes (green / yellow nudge / red override-and-push-to-ICU).

### 6. Multi-Expert Consensus — `icu/src/coach/consensus/`
Parallel Planner + Critic + Physiologist personas, followed by an Arbiter on disagreement. Higher token cost, higher quality ceiling.

### 7. Decision Ledger — `coach_memory/decisions.jsonl`
Append-only record of every plan change, override, and analysis conclusion with rationale, supporting data, and confidence score.

### 8. Evidence Library (RAG) — `icu/src/coach/evidence/`
Embedded sports-science literature. Major decisions cite sources (e.g., "Per Mujika 2009 taper meta-analysis, volume −41–60% with intensity preserved is optimal").

### 9. Race-Specific Module — `icu/src/coach/race_specific/`
Race course modeling, race-simulation ride generator, openers generator, automatic nutrition-protocol integration with `/mnt/d/Cycling/problem.md`.

### 10. Unified Coach Persona — `icu/coach_persona/`
Merges GEMINI.md (CLI) and module-level prompts into a single base persona with context-depth control. Removes CLI-vs-API personality split.

### 11. Observability Layer
Structured JSONL logging per module, full Gemini request/response capture (under `--debug`), decision replay tooling, diff/compare utilities.

## Phased Delivery

Each phase leaves the system in a strictly better state than before. No phase depends on a future phase.

| Phase | Scope | Components | Est. |
|---|---|---|---|
| **Phase 1** | Physiology model + Deep analyzer | 1, 4, partial 11 | 2–3 weeks |
| **Phase 2** | Periodization + Session Designer rewrite | 2, 3 | 2–3 weeks |
| **Phase 3** | Multi-expert consensus + Adaptation engine + Decision ledger | 5, 6, 7 | 2 weeks |
| **Phase 4** | Evidence RAG + Race-specific + Unified persona | 8, 9, 10 | 2–3 weeks |

Each phase has its own detailed spec document referencing this blueprint.

## End-State Vision

After all 4 phases, the coach:
- Knows **this athlete's** CP, W', durability curve, response profile, and medical constraints
- Identifies the current periodization phase autonomously and plans accordingly
- Generates each session from physiological intent, not from LLM guesswork
- Interprets every session the day it happens, surfacing the forensic "why" behind the numbers
- Closes the loop: analysis findings → next plan adjustments automatically
- Passes every major plan decision through a multi-expert review with cited literature
- Records a full audit trail; any decision can be replayed and explained
- Race-prep aligns automatically with the written nutrition protocol in `problem.md`

## Related Documents

- [Phase 1 detailed spec](./2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md)
- Phase 2 spec — TBD after Phase 1 implementation
- Phase 3 spec — TBD
- Phase 4 spec — TBD

## Non-Goals

- Web dashboard or custom UI (CLI + markdown reports are sufficient)
- Real-time device integration (still ICU-mediated)
- Self-hosted LLM — continues to use Gemini API
- Sensor fusion beyond ICU-provided data
