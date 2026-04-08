---
name: e2e-test
description: Run the full Socialwares v0.2.0 E2E test plan and generate a report
user_invocable: true
---

# Socialwares E2E Test Runner

Execute the full release E2E test plan from `docs/designs/release-e2e-test.md` and generate a detailed report.

## Overview

You are the **tester agent**. Execute each phase of the E2E plan step by step. For CLI-only steps, run commands directly. For LLM-interaction steps, use tmux to drive agent conversations.

**Critical rule: Do NOT modify any source code, templates, or framework files.** You are testing the existing code as-is.

## Execution Flow

### Setup

```bash
cd /home/yaosh/projects/Socialwares
source .venv/bin/activate
rm -rf task-review my-fork .socialware/workspace/
```

### Phase 1: Project Creation (CLI only)

Execute each step from the plan. For each test item:
1. Run the command
2. Check the expected output/files
3. Record PASS or FAIL with evidence

Test items:
- 1.1 `socialwares new task-review` — verify project structure
- 1.2 Template rendering — grep for expected patterns
- 1.3 Duplicate creation blocked
- 1.4 `new --from` — verify name replacement, .git removal
- 1.5 `eject` — verify copy, deploy priority, duplicate error

### Phase 2: Define Four Primitives (LLM interaction via tmux)

This phase requires multi-turn conversation with the dev agent.

**Step 1: Deploy defaults and start dev agent in tmux**
```bash
cd task-review
socialwares deploy
tmux new-session -d -s e2e-dev "socialwares start --role dev"
sleep 15  # wait for agent to initialize
```

**Step 2: Send "define" and interact**

Use `tmux send-keys` to type prompts, `tmux capture-pane` to read output:
```bash
tmux send-keys -t e2e-dev "define" Enter
sleep 60  # wait for agent response

# Capture and read output
tmux capture-pane -t e2e-dev -p -S -100
```

When the agent asks about Scope, respond:
```bash
tmux send-keys -t e2e-dev "Task review app. Capabilities: task CRUD, submit for review, approve/reject. Boundaries: no auth, no notifications." Enter
```

Continue for each primitive:
- **Role**: "default creates and submits tasks, reviewer reviews and approves/rejects tasks"
- **Flow**: "default: create_task, list_tasks, submit_task, close_task. reviewer: review_task, list_tasks. Both: check_health. State machine: draft → submit_task → submitted → review_task → reviewed → close_task → closed"
- **Commitment**: "After submit, reviewer must review within 24 hours"

Wait for the agent to write files and deploy. Monitor file changes:
```bash
# Poll for files to appear
ls agent/scope/scope.md agent/role/reviewer.md agent/flow/create_task/SKILL.md 2>/dev/null
```

**Step 3: Exit and verify**
```bash
tmux kill-session -t e2e-dev
```

Verify results per plan section 2.3. If agent didn't create all files, run section 2.4 (manual补齐).

### Phase 3: Compilation Verification (CLI only)

Run all checks from plan sections 3.1–3.8. These are pure CLI commands with file/output assertions.

### Phase 4: Development (LLM interaction)

**4.1 Dev build** — Start dev agent in tmux, say "build", observe TDD guidance:
```bash
fuser -k 8001/tcp 2>/dev/null || true
uv run uvicorn src.api:app --port 8001 &
tmux new-session -d -s e2e-dev "socialwares start --role dev"
sleep 15
tmux send-keys -t e2e-dev "build" Enter
sleep 60
tmux capture-pane -t e2e-dev -p -S -200
tmux kill-session -t e2e-dev
```

**4.2 Default role** — Use SDK mode for single-turn:
```bash
socialwares start --role default --prompt "check health"
```

**4.3 Multi-role** — Verify tmux starts:
```bash
timeout 20 socialwares start --role default,reviewer,evolver || true
tmux kill-session -t socialwares 2>/dev/null || true
```

**4.4 SDK mode** — verify session data:
```bash
socialwares start --role default --prompt "check health"
ls .runtime/data/prompts/
```

### Phase 5: Evolve Tests (LLM interaction)

For each evolve action, use SDK mode with `--prompt`:
```bash
# 5.1 structure_check
socialwares start --role evolver --prompt "check structure"

# 5.2 api_check (backend must be running)
socialwares start --role evolver --prompt "evaluate"

# 5.3 session_diagnose
socialwares start --role evolver --prompt "diagnose"

# 5.4 improve
socialwares start --role evolver --prompt "improve"
```

After each, check for report files in `.runtime/data/evolve/reports/`.

**5.5 Data chain**: verify all report types exist.
**5.6 Dev reads reports**: tmux session with dev agent, say "build".
**5.7 Custom evolve skill**: create directory, register, deploy, verify.

### Phase 6: IRC Channel Install (CLI only)

Execute all steps from plan sections 6.1–6.5:
- install from local git repo
- assign single role, verify SOUL.md markers
- assign multi-role to same agent, verify merge
- assign idempotency
- uninstall cleanup

### Phase 7: Package Build (CLI only)

```bash
cd /home/yaosh/projects/Socialwares
uv build
ls dist/socialwares-*.whl
```

### Phase 8: Configuration (CLI only)

Test adapter and agent_dir config overrides per plan.

## Report Generation

After all phases, generate a markdown report at `docs/reports/e2e-report-{YYYY-MM-DD}.md`:

```markdown
# E2E Test Report — Socialwares v0.2.0
Date: {date}
Branch: {branch}
Commit: {commit}

## Summary
- Total: {n} test items
- Pass: {pass}
- Fail: {fail}
- Skip: {skip}

## Phase 1: Project Creation
| # | Test Item | Status | Notes |
|---|-----------|--------|-------|
| 1.1 | socialwares new | PASS | ... |
| 1.2 | Template rendering | PASS | ... |
...

## Phase 2: Define Four Primitives
...
(repeat for each phase)

## Issues Found
- (list any failures or unexpected behavior)
```

## Timeout Policy

- CLI commands: 10s timeout
- SDK mode (`--prompt`): 120s timeout
- tmux agent interaction: 90s per prompt, 5min per phase
- If timeout: record as SKIP with reason

## Error Handling

- If a phase fails, continue to the next phase (don't abort)
- Record the failure with full error output
- If phase 2 (define) fails to create files, use manual补齐 (section 2.4) and continue

## Cleanup

After all phases:
```bash
fuser -k 8001/tcp 2>/dev/null || true
tmux kill-server 2>/dev/null || true
# Do NOT delete task-review/ — keep for inspection
```
