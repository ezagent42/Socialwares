# Evolve V2 Implementation Plan

> Branch: feat/evolve-v2
> Prerequisite: main branch up to date

## Overview

Four interconnected changes:
1. **Commitment refactor**: eval.yaml → constraints.yaml (bind to flow edges)
2. **Runtime data**: conversation logging + violations queue
3. **Evolver role**: manual skills (diagnose/eval/improve) + auto skill (EvoSkill loop)
4. **EvoSkill integration**: use EvoSkill library for automated evolution

## Design Decisions (from discussion)

- Commitment = constraints on flow edges (time/quality/certainty), NOT performance KPIs
- Violations = async queue, written by app backend, read by SessionStart hook
- **Violation detection is the app developer's responsibility** — template provides format + examples + guidance, not the detection logic itself (each app has different state machines and storage)
- Evolver = user-facing role (login and chat), NOT background process
- Manual mode: developer directs improvements through conversation
- Auto mode: developer says "auto-optimize" → EvoSkill loop runs → reports results
- Both modes share same scripts/infrastructure
- SDK mode: adapter logs conversations; Shell mode: PostToolUse hook logs
- **Evolver analyzes multiple data sources** (not just conversations):
  conversations, violations, eval cases, API errors, scope boundary hits
- **eval_cases.yaml = correct answer set**, grows with the app through P1→P5

---

## Task 1: Commitment refactor

**Goal**: eval.yaml → constraints.yaml, bind constraints to flow edges

**Files:**
- Rename: `agent/commitment/eval.yaml` → `agent/commitment/constraints.yaml`
- Rewrite: `agent/commitment/README.md`
- Update: `agent/deploy.sh` (copy constraints.yaml instead of eval.yaml)
- Update: `scripts/create-my-socialware.py` (copy constraints.yaml)
- Update: tests

**constraints.yaml template:**
```yaml
# Transition constraints — bind to flow.yaml state machine edges
# When a transition is triggered, these constraints must be satisfied.
# Violations are queued in .runtime/data/violations/ for the trigger_role to handle.
transition_constraints: {}
  # C1:
  #   description: "Review within 72h"
  #   on: { flow: F1, from: submitted, action: review }
  #   type: time
  #   deadline: 72h
  #   on_violation:
  #     trigger_action: force_resolve
  #     trigger_role: admin

# Action constraints — postconditions on direct actions
action_constraints:
  C1:
    description: "Health check returns ok"
    on: { action: check_health }
    type: postcondition
    expected: '{"status": "ok"}'
```

**commitment/README.md must document:**

1. Constraint format and binding rules
2. **App developer responsibilities for violation detection:**
   - Record timestamps on state transitions (app's DB/data layer)
   - Implement detection mechanism (one or more of):
     - API middleware: check pending constraints on every request (passive)
     - Background task: asyncio periodic check (active)
     - Cron endpoint: external cron calls `/check-constraints` (external)
   - Write violations to `.runtime/data/violations/current.jsonl` when detected
3. Violation JSONL format
4. SessionStart hook reads violations and notifies the responsible role
5. Example: how to implement a time-based constraint check in src/app.py

**Verify:** deploy.sh copies constraints.yaml to .runtime/agents/{role}/

---

## Task 2: Violations queue + SessionStart hook

**Goal**: constraint violations written to queue, notified on session start

**Files:**
- Update: `agent/deploy.sh` — generate check_violations.sh hook per role
- Update: `src/app.py` — add /violations endpoint (read/resolve)
- Add: violation write example in src/app.py (commented, as guidance)

**Violation JSONL format** (.runtime/data/violations/current.jsonl):
```json
{"id": "v-001", "constraint": "C1", "description": "review overdue 72h", "trigger_action": "force_resolve", "trigger_role": "admin", "detected_at": "2026-03-20T10:00:00Z", "resolved": false}
```

**deploy.sh generates** for each role:
```
.runtime/agents/{role}/.claude/hooks/check_violations.sh
```
SessionStart hook:
- Reads .runtime/data/violations/*.jsonl
- Filters for unresolved violations where trigger_role matches current role
- Reports them as additional context

**src/app.py adds:**
```python
@app.get("/violations")
async def list_violations(): ...

@app.post("/violations/{id}/resolve")
async def resolve_violation(id: str): ...
```

**Verify:** deploy creates hook, hook is executable, API endpoints work

---

## Task 3: Conversation logging

**Goal**: all agent interactions logged to .runtime/data/conversations/

**Shell mode** — deploy.sh generates PostToolUse hook:
```
.runtime/agents/{role}/.claude/hooks/log_action.sh
```
Writes tool call data to `.runtime/data/conversations/current.jsonl`

**SDK mode** — adapter logging mixin:
```python
# agent/adapters/base.py — add log_conversation()
def log_conversation(project_dir: Path, data: dict):
    log_dir = project_dir.parent.parent / "data" / "conversations"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "current.jsonl", "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
```
Each adapter's launch_sdk() calls log_conversation() on agent interactions.

**JSONL format:**
```json
{"timestamp": "...", "session_id": "...", "role": "default", "type": "tool_call", "action": "create_task", "input": {...}, "output": {...}, "success": true}
```

**Verify:** deploy creates hook, SDK adapter logs

---

## Task 4: Evolver role + flow registration

**Goal**: evolver role with 4 skills registered in flow.yaml

**Files:**
- Create: `agent/role/evolver/SOUL.md`
- Update: `agent/flow/flow.yaml`

**flow.yaml additions:**
```yaml
direct_actions:
  # ... existing ...
  - { action: evolve_diagnose, role: [evolver], description: "Diagnose issues from runtime data" }
  - { action: evolve_eval,     role: [evolver], description: "Run eval cases and report score" }
  - { action: evolve_improve,  role: [evolver], description: "Propose and apply four-primitive changes" }
  - { action: evolve_auto,     role: [evolver], description: "Run automated evolution loop (EvoSkill)" }
```

---

## Task 5: evolve_diagnose skill

**Goal**: read ALL runtime data sources → output diagnostic report

**Files:**
- Create: `agent/flow/evolve_diagnose/SKILL.md`
- Create: `agent/flow/evolve_diagnose/scripts/diagnose.py`

**diagnose.py scans multiple data sources:**

| Data source | What it finds | Progressive phase |
|-------------|--------------|-------------------|
| conversations/*.jsonl | Failed requests, missing capabilities ("I can't do that") | P2 (need new Flow skills) |
| violations/*.jsonl | Which constraints are violated, how often | P3 (need better Commitment) |
| conversations/*.jsonl | Requests outside scope boundaries | P4 (need wider Scope) |
| conversations/*.jsonl | Permission denials, role mismatches | P5 (need new Roles) |
| API call results | 500/404 errors, slow responses | P2 (code bugs) |
| constraints.yaml | Active constraints summary | Context |

**Output:** structured diagnostic report (text) that evolver agent reads and interprets.

**Verify:** script runs with sample data, produces readable output

---

## Task 6: evolve_eval skill

**Goal**: run eval cases against live app → report score

**Files:**
- Create: `agent/flow/evolve_eval/SKILL.md`
- Create: `agent/flow/evolve_eval/scripts/run_eval.py`
- Create: `agent/flow/evolve_eval/eval_cases.yaml`

**run_eval.py:**
- Read eval_cases.yaml
- For each case: HTTP call to app endpoint, compare response
- Output: pass/fail per case, overall score, trend (if previous scores exist)

**eval_cases.yaml grows with the app:**
```yaml
# P1: basic health
cases:
  - description: "Health check returns ok"
    method: GET
    endpoint: /health
    expected_status: 200
    expected_body: '{"status": "ok"}'

# P2: add task CRUD cases as you build them
# - description: "Create task returns 200"
#   method: POST
#   endpoint: /tasks
#   body: '{"title": "test"}'
#   expected_status: 200

# P5: add role-based cases
# - description: "Reviewer cannot create task"
#   method: POST
#   endpoint: /tasks
#   headers: {"X-Identity": "reviewer"}
#   expected_status: 403
```

**Verify:** script runs against live app, reports score

---

## Task 7: evolve_improve skill

**Goal**: conversational — evolver reads diagnose+eval, proposes changes, applies

**Files:**
- Create: `agent/flow/evolve_improve/SKILL.md`

**No scripts** — agent-driven. SKILL.md guides the evolver to:
1. Read diagnose report + eval score
2. Map problems to four primitives:
   - Missing capability → add flow/ skill
   - Constraint violations → adjust constraints or improve skill quality
   - Scope boundary hits → expand scope/SOUL.md
   - Permission issues → add/adjust role/
3. Propose changes in conversation
4. Developer approves → evolver edits files → runs deploy.sh

---

## Task 8: evolve_auto skill (EvoSkill integration)

**Goal**: automated evolution loop, triggered by conversation

**Files:**
- Create: `agent/flow/evolve_auto/SKILL.md`
- Create: `agent/flow/evolve_auto/scripts/run_loop.py`
- Add dependency: EvoSkill (or vendor core modules)

**run_loop.py wraps EvoSkill:**
- Uses EvoSkill's evaluation (evaluate_agent_parallel)
- Uses EvoSkill's proposer (skill_proposer prompt for failure analysis)
- Uses EvoSkill's frontier (git branch management)
- Reads eval_cases.yaml as benchmark data
- Reads .runtime/data/ for failure evidence

**Conversational flow:**
```
Developer: "auto-optimize, run 5 iterations"
Evolver:   → runs run_loop.py --iterations 5
           → EvoSkill loop: evaluate → propose → generate → evaluate → keep/discard
           → "Completed 5 iterations. Best score: 0.6 → 0.85.
              Changes: added handle_error skill, updated scope/SOUL.md.
              Apply these changes?"
Developer: "show me what changed"
Evolver:   → shows diff
Developer: "apply"
Evolver:   → deploys
```

**EvoSkill integration approach:**
- If pip installable: `pip install evoskill` and import
- If not: vendor core modules (evaluation, proposer, frontier) into src/evolve/

---

## Task 9: Documentation

**Files:**
- Create: `docs/guides/using-evolver.md`
  - Manual mode: diagnose → eval → improve workflow
  - Auto mode: evolve_auto conversation flow
  - When to use which
  - How to grow eval_cases.yaml through P1→P5
- Rewrite: `agent/commitment/README.md`
  - Constraints format and binding rules
  - App developer responsibilities (timestamp recording, detection, violation writing)
  - Detection mechanism options (passive/active/external) with example code
  - Violation JSONL format
- Update: `README.md` — add constraints + evolver sections
- Update: `docs/QUICKSTART.md` — add evolver step

---

## Task 10: Tests

| For task | Test file | What to test |
|----------|-----------|--------------|
| Task 1 | update `tests/test_deploy.py` | constraints.yaml copied to .runtime/ |
| Task 1 | update `tests/test_create_workspace.py` | constraints.yaml in workspace |
| Task 2 | create `tests/test_violations.py` | violation JSONL write/read, hook exists, API endpoints |
| Task 3 | create `tests/test_logging.py` | hook exists, JSONL format valid |
| Task 5 | create `tests/test_diagnose.py` | diagnose.py with sample data produces report |
| Task 6 | create `tests/test_eval.py` | run_eval.py against health endpoint |
| Task 8 | create `tests/test_evolve_auto.py` | EvoSkill integration smoke test |

---

## Execution Order

```
Parallel batch 1:
  Task 1 (commitment refactor)
  Task 3 (conversation logging)
  Task 4 (evolver role)

Sequential after batch 1:
  Task 2 (violations — depends on Task 1)

Parallel batch 2:
  Task 5 (diagnose — depends on Task 2, 3)
  Task 6 (eval — independent)

Sequential after batch 2:
  Task 7 (improve — depends on Task 5, 6)
  Task 8 (auto — depends on Task 6, EvoSkill)

Final:
  Task 9 (documentation — depends on all)
  Task 10 (tests — parallel with each task)
```
