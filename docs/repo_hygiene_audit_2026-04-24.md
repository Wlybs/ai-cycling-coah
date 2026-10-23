# Repo Hygiene Audit — 2026-04-24

**Scope:** `/mnt/d/Cycling` master branch working tree
**Author:** Claude (D task in parallel-work session)
**Status:** Audit only — no git state modified. Defer execution until after `ai-coach-phase-2` merges to master.

---

## Context constraints

1. Memory rule: `icu/ baseline mostly untracked; always stage specific paths, never git add . / git add icu/`.
2. `ai-coach-phase-2` branch (@ `3832327`, 11/11 files complete) already tracks `docs/superpowers/plans/phase-1/` and `phase-2/`. These appear "untracked" on master today but will resolve on merge.
3. `ai-coach-phase-3` worktree is active — any master mutation affecting shared paths risks rebase friction.

**Execution principle:** minimal, non-destructive, idempotent.

---

## Categorized inventory

### Category 1 — Will auto-resolve on phase-2 merge (DO NOT touch on master)

| Path | Reason |
|---|---|
| `docs/superpowers/plans/.archived/2026-04-16-ai-coach-phase-1-implementation.md` | Tracked on phase-2 branch |
| `docs/superpowers/plans/phase-1/00-index.md` + 10 siblings | Tracked on phase-2 branch |
| `icu/scripts/*.py` (11 new sync/build scripts) | Phase 1/2 deliverables, likely tracked on phase-2 |
| `icu/src/analyzer/`, `icu/src/coach/__init__.py`, `memory_builder.py`, `plan_evaluator.py` | Phase 1/2 deliverables |
| `icu/tests/test_trend_analyzer.py` | Phase 1 test artefact |

**Action:** none. Verify after phase-2 merge lands.

### Category 2 — Local runtime noise, should be gitignored

| Path | Size | Recommended rule |
|---|---|---|
| `icu/.claude/` | — | `icu/.claude/` |
| `icu/icu/logs/` (nested accidental dir) | — | investigate: likely script bug writing to wrong cwd |
| `icu/coach_memory_backup_20260418/` | 132K | `icu/coach_memory_backup_*/` |
| `icu/race_map/*.gpx` | varies | `icu/race_map/` (personal GPX data) |
| `.beads/dolt-monitor.pid.lock` | 0 | already deleted (shows `D` in status); bd runtime file |

**Action proposal (run AFTER phase-2 merge):**
```gitignore
# append to /mnt/d/Cycling/icu/.gitignore
.claude/
icu/           # nested accidental dir — fix root cause separately
coach_memory_backup_*/
race_map/
```

### Category 3 — Project root files needing decision

| Path | Note |
|---|---|
| `/mnt/d/Cycling/CLAUDE.md` | New, never committed. Project guidance doc — should be committed to master. |
| `/mnt/d/Cycling/AGENTS.md` | Already tracked (not in untracked list) |
| `.gitignore` (root) | Only has `.dolt/`, `*.db`. Could add `.beads/*.lock`, editor noise. |

**Action proposal:** commit `CLAUDE.md` on master as standalone commit:
```bash
git add CLAUDE.md
git commit -m "docs: add project-level CLAUDE.md for Claude Code guidance"
```

### Category 4 — Investigate root cause

| Issue | Notes |
|---|---|
| `icu/icu/logs/` exists | A script is invoking from `/mnt/d/Cycling/` instead of `/mnt/d/Cycling/icu/` and creating a nested folder. Find which script logs to `icu/logs/` and has a CWD bug. |

**Action proposal:** after phase-2 merge, grep for `Path("icu/logs")` or `"icu/logs/"` in `icu/scripts/` and `icu/src/`; fix to use repo-root-relative or pass explicit path.

---

## Recommended execution order (after phase-2 merges)

1. Verify Category 1 paths are now tracked; untracked list should shrink dramatically.
2. Append Category 2 rules to `icu/.gitignore`; commit with `chore: gitignore local runtime noise`.
3. Commit root `CLAUDE.md` as standalone.
4. Investigate nested `icu/icu/logs/` origin; patch offending script.
5. Re-run `git status -s` — remaining untracked items should be minimal and user-specific.

---

## Risks if executed NOW (before phase-2 merge)

- Adding any `docs/superpowers/plans/phase-1/` file on master → duplicate/different-content conflict at merge time
- Modifying `icu/.gitignore` on master → 3-way merge conflict with any gitignore change phase-2 branch made
- `git add icu/...` → directly violates memory rule and may stage files that phase-2 already staged differently

**Decision:** waited. Report filed. User reviews after phase-2 merge.
