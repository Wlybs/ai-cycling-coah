# AI Coach — Phase 1 Implementation Plan (Index)

Split from the original monolithic plan (archived at `../.archived/2026-04-16-ai-coach-phase-1-implementation.md`) to keep each piece under the 600-line context-safe threshold.

## Scope

Phase 1 = physiology refresh snapshot + deep session analyzer + prompt injection.

- Source spec: [`../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`](../../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md)
- Blueprint (4-phase scheme): [`../../specs/2026-04-16-ai-coach-scheme-4-blueprint.md`](../../specs/2026-04-16-ai-coach-scheme-4-blueprint.md)

## Execution rules (read before starting any file)

1. **One file per session.** Advance 01 → 09 in order. Never chain multiple files in a single session — complete, checkpoint, end, resume.
2. **TDD required.** Every task inside every file has a RED test block. Write the test first, run it, confirm failure, then implement.
3. **Delegate big writes.** If a task requires producing >300 lines of code in one go, dispatch it via the `Agent` tool with a self-contained brief pointing at the current file and task IDs. Main conversation receives only "done + file list" back.
4. **Context hygiene.**
   - Analyze existing source files with `ctx_execute_file` (summary-only into context) — use `Read` **only** when you are about to `Edit` that exact file.
   - Do NOT re-read the archived monolith. Work from the current file only.
   - Use `ctx_batch_execute` when you need to run several exploration commands — one round trip, sandbox-indexed output.
5. **Checkpoint discipline.** After completing a file: run TDD verification, commit the code under `feat(coach-phase1):` prefix, run `save-progress`, then end the session. Next session starts cold on the next file.
6. **Never write >600 lines in a single Write operation.** If an implementation file is growing past ~500 lines, split into multiple modules up front.

## File map

| # | File | Tasks | Focus | Lines |
|---|---|---|---|---|
| 1 | [01-infrastructure.md](./01-infrastructure.md) | T1–T3 | Package scaffold, Pydantic types, JSONL logger | 417 |
| 2 | [02-physiology-core.md](./02-physiology-core.md) | T4–T5 | CP/W' fitter, W' balance real-time model | 367 |
| 3 | [03-physiology-profile.md](./03-physiology-profile.md) | T6–T8 | Durability curve, individual response profile, physiology facade | 454 |
| 4 | [04-feature-routing.md](./04-feature-routing.md) | T9–T10 | Ride feature detector, sub-analyzer relevance router | 245 |
| 5 | [05-analyzers-intra.md](./05-analyzers-intra.md) | T11–T13 | Sub-analyzers: pacing, w_balance, durability | 355 |
| 6 | [06-analyzers-context.md](./06-analyzers-context.md) | T14–T16 | Sub-analyzers: climbing, target_align, historical_cmp | 398 |
| 7 | [07-composer-orchestrator.md](./07-composer-orchestrator.md) | T17–T18 | Gemini prose report composer, deep analyzer orchestrator | 486 |
| 8 | [08-integration.md](./08-integration.md) | T19–T21 | `sync_data.py` tail, `plan_generator.py` injection, GEMINI.md Coach Brief updater | 565 |
| 9 | [09-cli-tests-acceptance.md](./09-cli-tests-acceptance.md) | T22–T24 | CLI tools (`analyze_rides`, `physiology_audit`), e2e test with mocks, real-warehouse acceptance | 490 |

Dependency order is strict: each file assumes all lower-numbered files are complete and committed.

## Self-review status (from original monolith, carried forward)

Self-review was completed inline before the split. Key fixes already applied in the task specs:

- `HR_max` pulled from `6_SportSettings/` (or `1_Profile/`) instead of being hardcoded.
- Decoupling field sourced from ICU activity summary (`decoupling` key), not recomputed per ride.
- `target_align` data source confirmed: `8_Events/` calendar events provide the planned workout to compare against.

## Handoff

**Start here:** open [`01-infrastructure.md`](./01-infrastructure.md). Apply `superpowers:subagent-driven-development`. Execute tasks T1–T3 in order. Commit. End session.

**Subagent brief template:**

> Use `docs/superpowers/plans/phase-1/<file>.md`. Follow `superpowers:subagent-driven-development`. Execute tasks in order. For each task: write the RED test first, run to confirm failure, implement, re-run to confirm pass. Report back only: (a) task IDs completed, (b) files created/modified, (c) any deviation from the plan and why. Do NOT re-read the archived monolith.

**When all 9 files are green:**
- Phase 1 is complete. Run the acceptance checklist in `09-cli-tests-acceptance.md`.
- The archived monolith can be deleted permanently once `main` is green.
- Proceed to Phase 2 brainstorming (periodization + session designer).
