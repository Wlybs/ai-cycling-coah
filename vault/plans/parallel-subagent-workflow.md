---
created: 2026-05-12
status: scaffold (not implemented, 5/17 race 后开工)
type: project-plan
related: [[INDEX]]
target_project: AI Coach Phase 5+
---

# Parallel Subagent TDD Workflow (Scaffold for 5/17 race 后)

## 触发 (insights 2026-05-12)

`/insights` 报告 "On the Horizon" 提议: 现有 AI Coach Phase 2/3 串行 subagent dispatch → 并行 worktree + merge-coordinator → 多天 collapse 到隔夜.

用户决策 2026-05-12 22:30: **race 周不动 AI Coach 项目, race 后 (5/17 后) 开工实施**.

## 目标

把 Phase 5+ 的 multi-task 实施从串行 (T-XX 一个一个跑) 变成并行 (所有独立任务同时跑) + auto-merge.

预期收益: 多天工作 → 隔夜单 PR.

## 架构 scaffold

```
┌─────────────────────────────────────────────────────┐
│ orchestration.py (主控)                             │
└──┬──────────────────────────────────────────────────┘
   │
   ├─→ spec-auditor (pre-flight)
   │   读全 phase plan, 输出: contradictions / open Qs / missing AC
   │   block until user 解决
   │
   ├─→ DAG parser
   │   解析 phase plan markdown 中的 task nodes + deps
   │
   ├─→ worktree-creator (per leaf task)
   │   git worktree add ../coach-T-XX <branch>
   │
   ├─→ parallel dispatch (max concurrency N)
   │   for each task:
   │     in its worktree:
   │       implementer subagent (TDD red-green)
   │       → spec-reviewer subagent (AC check)
   │       → code-quality-reviewer subagent
   │
   ├─→ merge-coordinator
   │   按 DAG dependency 顺序 rebase
   │   每次 merge 后跑 pytest 全 suite
   │   自动 conflict resolution (如有可处理的模式)
   │
   └─→ summary + handoff
       生成 PR 描述 + next-session prompt (用 handoff skill)
```

## 实施 phases

### Phase 1 - Spec Auditor + DAG Parser (1-2 day)
- 输入: phase plan markdown (T-IDs + deps)
- 输出: parsed DAG + audit report
- 必交付:
  - Python parser for T-XX format
  - audit prompt template (基于 spec-audit skill)
  - DAG visualization (graphviz dot)

### Phase 2 - Worktree + Sequential Dispatch (2-3 day)
- 单 task 独立 worktree
- 串行 dispatch (verify pipeline works on 1 task at a time)
- 必交付:
  - worktree lifecycle (create / cleanup)
  - subagent prompt templates (impl / spec-review / code-review)
  - state machine (pending / in-progress / done / failed)

### Phase 3 - Parallel Concurrency (2-3 day)
- max concurrency limit (default 4)
- shared state (sqlite for cross-process)
- 必交付:
  - asyncio orchestrator
  - failure isolation (1 task fail 不阻塞其他)
  - real-time progress dashboard

### Phase 4 - Merge Coordinator (3-5 day)
- DAG topological sort merge order
- 每 merge 跑 pytest
- conflict 自动 resolve (基于已知模式)
- 必交付:
  - merge pipeline
  - rollback mechanism (任一 merge 失败回滚到上 commit)
  - test gate (任一 test fail 阻塞 PR)

### Phase 5 - PR + Handoff (1 day)
- 自动 PR description (基于所有 task 的 commit messages)
- handoff prompt 用 handoff skill
- 必交付:
  - PR template
  - integration with /handoff skill

## 风险评估

### 高风险
- **Merge conflict 不可自动 resolve**: 复杂 conflict 需要人工 → 系统暂停 + 通知用户
- **Test flake**: parallel 跑可能 expose 之前没看到的 race condition → 需要 deterministic test seed

### 中风险
- **Spec audit 错过 contradiction**: pre-flight 不够严, 实施时再发现 → 需要 worktree 之间通信机制
- **资源消耗**: 4 个 worktree + 4 个 Claude session 并行 → API rate limit + 本地 disk space

### 低风险
- **Worktree cleanup**: 失败 task 留 stale worktree → cron job 清理

## 不做

- 不做"自动 fix conflict" — 复杂 conflict 让用户来
- 不做"自动 retry failed test" — flake 在 base 期就要消灭
- 不做"AI 自己写 spec" — spec 是用户责任, AI 实施

## 启动条件

5/17 race 后:
- [ ] race day 状态 review (确保 race 周 over)
- [ ] AI Coach Phase 4 M2/M3 状态 check (有没有未完成的 stub)
- [ ] decision: 是 Phase 5 之前 build orchestrator, 还是 Phase 5 一边 build 一边用

## 元学习

如果 orchestrator build 完后实测有效:
- 写 retrospective: 多天 → 隔夜 实际 collapse 比 vs 预期
- 推广到其他项目 (论文 latex 自验证循环也可用类似架构)
