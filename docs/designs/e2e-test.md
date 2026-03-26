# End-to-End Test Plan — Task Review App

A developer builds a Task Review App from scratch, testing every Socialwares feature along the way.

## Prerequisites

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

## Convention

App port is configured in `src/app.py` (`APP_PORT`, default 8001, overridable via `APP_PORT` env var). All commands below use port 8001. To change:

```bash
export APP_PORT=8002  # optional — changes default for app + eval scripts
```

---

## Phase 1: Template & Workspace

### 1.1 Root Makefile guards

| | |
|---|---|
| **Action** | Run `make deploy` and `./agent/deploy.sh` at repo root |
| **Purpose** | Verify deploy/start are blocked at template root |
| **Expected** | Error message: "deploy.sh should not run at the template root" |

```bash
make deploy      # Error: workspace command
./agent/deploy.sh   # Error: should not run at template root
```

### 1.2 Create workspace

| | |
|---|---|
| **Action** | `make create ROOM=demo APP=task-review DESC="Task review workflow"` |
| **Purpose** | Create self-contained app workspace |
| **Expected** | Directory at .socialware/workspace/demo/task-review/ with agent/, src/, Makefile, pyproject.toml |

```bash
make create ROOM=demo APP=task-review DESC="Task review workflow"
cd .socialware/workspace/demo/task-review
uv sync

ls -a          # .  ..  agent  app  Makefile  pyproject.toml  src  .runtime
ls agent/role/ # default.md  dev.md  evolver.md  (README.md excluded during create)
cat agent/scope/scope.md    # Contains "task-review"
cat Makefile | head -2       # "Socialware App — Workspace Makefile"
```

### 1.3 Verify initial deploy

| | |
|---|---|
| **Action** | Check .runtime/ created by make create |
| **Purpose** | Verify auto-deploy on create |
| **Expected** | .runtime/agents/ with 3 roles, skills symlinked, hooks generated |

```bash
ls .runtime/agents/          # default  dev  evolver

# Skills are symlinks within workspace
ls -la .runtime/agents/default/.claude/skills/check_health
# Should show -> (symlink arrow pointing to agent/flow/check_health)

# Workspace root marker
cat .runtime/agents/default/.workspace_root
# Should show full path to workspace

# Hooks generated (claude adapter default)
ls .runtime/agents/default/.claude/hooks/
# Expected: log_prompt.sh  log_tool.sh

# Hooks registered
cat .runtime/agents/default/.claude/settings.local.json | python3 -m json.tool
# Should show UserPromptSubmit + PreToolUse (NOT PostToolUse or SessionStart)

# Prompt file for claude
cat .runtime/agents/default/SOUL.md | head -5
# Should contain merged scope + role content
```

### 1.4 Skill filtering by role

| | |
|---|---|
| **Action** | Compare skills across roles |
| **Purpose** | Verify flow.yaml role filtering |
| **Expected** | default=1, dev=3, evolver=7 |

```bash
ls .runtime/agents/default/.claude/skills/ | wc -l    # 1 (check_health)
ls .runtime/agents/dev/.claude/skills/ | wc -l         # 3 (check_health, setup_claude, inspect)
ls .runtime/agents/evolver/.claude/skills/ | wc -l      # 7 (check_health, inspect, evolve_structure_check, evolve_session_diagnose, evolve_api_check, evolve_improve, evolve_auto)
```

### 1.5 Make idempotency

| | |
|---|---|
| **Action** | Run `make deploy` twice |
| **Purpose** | Verify Make timestamp-based idempotency |
| **Expected** | Both show "Nothing to be done" (create already deployed) |

```bash
make deploy    # Nothing to be done
make deploy    # Nothing to be done
```

### 1.6 Make change detection

| | |
|---|---|
| **Action** | Edit a file, run `make deploy` |
| **Purpose** | Verify Make detects source changes |
| **Expected** | Redeploys after edit |

```bash
echo "# test change" >> agent/scope/scope.md
make deploy    # Should rebuild
sed -i '$ d' agent/scope/scope.md   # Restore
```

### 1.7 Duplicate workspace fails

| | |
|---|---|
| **Action** | Run create with same room/app |
| **Purpose** | Verify won't overwrite |
| **Expected** | Error message |

```bash
cd ../../../..   # back to repo root
make create ROOM=demo APP=task-review DESC="duplicate"   # Should fail
cd .socialware/workspace/demo/task-review
```

---

## Phase 2: Build the App

### 2.1 Add backend API

| | |
|---|---|
| **Action** | Write task review endpoints in src/app.py |
| **Purpose** | Build the Biz layer |
| **Expected** | CRUD endpoints work |

```bash
cat > src/app.py << 'PYEOF'
"""Task Review App backend."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Task Review App", version="0.1.0")

_tasks: dict[str, dict] = {}
_counter = 0
VIOLATIONS_DIR = Path(".runtime/data/evolve/violations")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/tasks")
async def create_task(data: dict[str, Any]):
    global _counter
    _counter += 1
    task_id = f"task-{_counter:03d}"
    task = {
        "id": task_id,
        "title": data.get("title", "Untitled"),
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task

@app.post("/tasks/{task_id}/submit")
async def submit_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(404)
    _tasks[task_id]["status"] = "submitted"
    _tasks[task_id]["submitted_at"] = datetime.now(timezone.utc).isoformat()
    return _tasks[task_id]

@app.post("/tasks/{task_id}/review")
async def review_task(task_id: str, data: dict[str, Any]):
    if task_id not in _tasks:
        raise HTTPException(404)
    _tasks[task_id]["status"] = data.get("decision", "reviewed")
    _tasks[task_id]["review_comment"] = data.get("comment", "")
    _tasks[task_id]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    return _tasks[task_id]

@app.get("/tasks")
async def list_tasks():
    return list(_tasks.values())

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(404)
    return _tasks[task_id]

@app.get("/violations")
async def list_violations():
    violations = []
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                if not v.get("resolved", False):
                    violations.append(v)
    return violations

@app.post("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: str):
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        lines = f.read_text().splitlines()
        updated = []
        found = False
        for line in lines:
            if line.strip():
                v = json.loads(line)
                if v.get("id") == violation_id:
                    v["resolved"] = True
                    v["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    found = True
                updated.append(json.dumps(v, ensure_ascii=False))
        if found:
            f.write_text("\n".join(updated) + "\n")
            return {"status": "resolved", "id": violation_id}
    raise HTTPException(404, f"Violation {violation_id} not found")
PYEOF

# Test
uv run uvicorn src.app:app --port 8001 &
sleep 2
curl -s http://localhost:8001/health
# {"status":"ok"}
curl -s -X POST http://localhost:8001/tasks -H "Content-Type: application/json" -d '{"title":"Fix bug #42"}'
# {"id":"task-001","title":"Fix bug #42","status":"draft",...}
curl -s -X POST http://localhost:8001/tasks/task-001/submit
# {"id":"task-001","status":"submitted",...}
curl -s -X POST http://localhost:8001/tasks/task-001/review -H "Content-Type: application/json" -d '{"decision":"approved","comment":"LGTM"}'
# {"id":"task-001","status":"approved","review_comment":"LGTM",...}
kill %1
```

### 2.2 Add flow skills

| | |
|---|---|
| **Action** | Create skills for task workflow |
| **Purpose** | Agent can manage tasks |
| **Expected** | Skills deployed for correct roles |

```bash
# Create skills
for skill in create_task submit_task review_task list_tasks; do
    mkdir -p agent/flow/$skill
done

cat > agent/flow/create_task/SKILL.md << 'EOF'
---
name: create_task
description: "Create a new task"
---
# Create Task
## Trigger
User says "create task", "new task" etc.
## Flow
1. Extract title -> POST /tasks -> return result
EOF

cat > agent/flow/submit_task/SKILL.md << 'EOF'
---
name: submit_task
description: "Submit a task for review"
---
# Submit Task
## Trigger
User says "submit task-xxx" etc.
## Flow
1. Get ID -> POST /tasks/{id}/submit -> confirm
EOF

cat > agent/flow/review_task/SKILL.md << 'EOF'
---
name: review_task
description: "Review a submitted task"
---
# Review Task
## Trigger
User says "review task-xxx", "approve", "reject" etc.
## Flow
1. Get ID + decision -> POST /tasks/{id}/review -> confirm
EOF

cat > agent/flow/list_tasks/SKILL.md << 'EOF'
---
name: list_tasks
description: "List all tasks"
---
# List Tasks
## Trigger
User says "list tasks", "show tasks" etc.
## Flow
1. GET /tasks -> format and display
EOF

# Update flow.yaml
cat > agent/flow/flow.yaml << 'EOF'
flows: {}
direct_actions:
  - { action: check_health,     role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude,     role: [dev], description: "Configure Claude Code" }
  - { action: inspect,          role: [dev, evolver], description: "Show project structure" }
  - { action: create_task,      role: [default], description: "Create a new task" }
  - { action: submit_task,      role: [default], description: "Submit task for review" }
  - { action: review_task,      role: [reviewer], description: "Review a submitted task" }
  - { action: list_tasks,       role: [default, reviewer], description: "List all tasks" }
  - { action: evolve_structure_check,     role: [evolver], description: "Check structural consistency" }
  - { action: evolve_session_diagnose,  role: [evolver], description: "Diagnose from runtime data" }
  - { action: evolve_api_check,      role: [evolver], description: "Run eval cases" }
  - { action: evolve_improve,   role: [evolver], description: "Apply improvements" }
  - { action: evolve_auto,      role: [evolver], description: "Automated conversation testing" }
EOF

make deploy

# Verify
ls .runtime/agents/default/.claude/skills/
# Expected: check_health  create_task  list_tasks  submit_task
```

### 2.3 Add reviewer role

| | |
|---|---|
| **Action** | Create reviewer role |
| **Purpose** | Multi-role collaboration |
| **Expected** | Reviewer gets only review_task + list_tasks + check_health |

```bash
cat > agent/role/reviewer.md << 'EOF'
# Reviewer Agent

Reviews submitted tasks.

## Identity

- Role: reviewer
- Permissions: review and list tasks

## Responsibilities

1. Review submitted tasks (approve/reject with comment)
2. List tasks to see what needs review
EOF

make deploy

ls .runtime/agents/reviewer/.claude/skills/
# Expected: list_tasks  review_task
# NOT: create_task, submit_task, check_health (reviewer not in check_health role list)
```

### 2.4 Deploy cleans removed roles

| | |
|---|---|
| **Action** | Delete a role file and redeploy |
| **Purpose** | Verify deploy removes stale roles from .runtime/ |
| **Expected** | Deleted role's .runtime/agents/ directory disappears |

```bash
cp agent/role/reviewer.md agent/role/reviewer.md.bak
rm agent/role/reviewer.md
make deploy
ls .runtime/agents/
# Expected: default  dev  evolver  (no reviewer)

# Restore for later phases
mv agent/role/reviewer.md.bak agent/role/reviewer.md
make deploy
ls .runtime/agents/
# Expected: default  dev  evolver  reviewer
```

### 2.5 TUI mode — start agent

| | |
|---|---|
| **Action** | Start default role in TUI |
| **Purpose** | Verify agent launches with correct skills |
| **Expected** | Claude Code opens, SOUL.md loaded, skills available |

```bash
make start
# In Claude Code:
#   "/" -> should see: check_health, create_task, submit_task, list_tasks
#   "create a task: fix login bug"
#   "list tasks"
#   Exit: Ctrl+C
```

### 2.6 Test hooks capture data

| | |
|---|---|
| **Action** | Check if hooks captured prompts during TUI session |
| **Purpose** | Verify UserPromptSubmit + PreToolUse hooks work |
| **Expected** | .runtime/data/prompts/current.jsonl has entries |

```bash
cat .runtime/data/prompts/current.jsonl
# Should have entries like:
# {"type":"user_prompt","content":"create a task: fix login bug",...}
# {"type":"tool_call","tool":"Bash","input":{...},...}
```

### 2.7 Test hooks manually

| | |
|---|---|
| **Action** | Run hook scripts with test data to verify execution |
| **Purpose** | Verify hooks actually execute, are executable, and produce JSONL output |
| **Expected** | JSONL entries written to .runtime/data/prompts/current.jsonl |

```bash
# Check hooks are executable
ls -la .runtime/agents/default/.claude/hooks/log_prompt.sh
# Expected: -rwxr-xr-x
ls -la .runtime/agents/default/.claude/hooks/log_tool.sh
# Expected: -rwxr-xr-x

# Test prompt logging hook (UserPromptSubmit)
mkdir -p .runtime/data/prompts
echo '{"prompt":"hello"}' | \
  bash .runtime/agents/default/.claude/hooks/log_prompt.sh
cat .runtime/data/prompts/current.jsonl
# Should have a JSONL entry with timestamp + type "user_prompt"

# Test tool logging hook (PreToolUse)
echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | \
  bash .runtime/agents/default/.claude/hooks/log_tool.sh
cat .runtime/data/prompts/current.jsonl
# Should have a JSONL entry with timestamp + type "tool_call"

# Clean up test data
rm -f .runtime/data/prompts/current.jsonl
```

---

## Phase 3: Commitment — Evaluation Standards

### 3.1 Define commitment

| | |
|---|---|
| **Action** | Write commitment.yaml with evaluation standards |
| **Purpose** | Define what "good" looks like for the task review workflow |
| **Expected** | commitment.yaml deployed to all roles |

```bash
cat > agent/commitment/commitment.yaml << 'EOF'
commitments:
  C1:
    from: { role: default, action: submit_task }
    to: { role: reviewer, action: review_task }
    condition: "review should happen within 24h of submission"
    on_violation: null

  C2:
    from: { role: default, action: create_task }
    to: { role: default, action: submit_task }
    condition: "task should be submitted within 48h of creation"
    on_violation: null
EOF

make deploy
cat .runtime/agents/default/commitment.yaml
# Should match
cat .runtime/agents/evolver/commitment.yaml
# Should also match (deployed to all roles)
```

### 3.2 Write API eval cases

| | |
|---|---|
| **Action** | Write eval_cases.yaml (API checks only) |
| **Purpose** | Define backend API correctness benchmarks |
| **Expected** | File created, used by run_eval.py |

```bash
cat > agent/flow/evolve_api_check/eval_cases.yaml << 'EOF'
api_checks:
  - description: "Health check"
    method: GET
    endpoint: /health
    expected_status: 200
    expected_body: '{"status":"ok"}'
  - description: "Create task"
    method: POST
    endpoint: /tasks
    body: '{"title":"eval test"}'
    expected_status: 200
  - description: "List tasks"
    method: GET
    endpoint: /tasks
    expected_status: 200
  - description: "Non-existent task 404"
    method: GET
    endpoint: /tasks/task-000
    expected_status: 404
EOF
```

### 3.3 Write conversation test cases

| | |
|---|---|
| **Action** | Write conversation test cases per role (separate from API checks) |
| **Purpose** | Define expected agent behavior on user inputs |
| **Expected** | Files in conversation_tests/ directory, used by run_auto.py |

```bash
mkdir -p agent/flow/evolve_auto/conversation_tests

cat > agent/flow/evolve_auto/conversation_tests/default.yaml << 'EOF'
# Fields:
#   input:                 what to say to the agent
#   expected_skill:        skill the agent should invoke (checked in trace)
#   expected_contains:     keywords that MUST appear in agent's reply (list)
#   expected_not_contains: keywords that must NOT appear in agent's reply (list)
#   description:           human-readable test name
role: default
cases:
  - input: "create a task: write docs"
    expected_skill: create_task
    expected_contains:
      - "task"
      - "write docs"
    expected_not_contains:
      - "error"
    description: "Agent uses create_task skill"
  - input: "list tasks"
    expected_skill: list_tasks
    expected_contains:
      - "task"
    description: "Agent uses list_tasks skill"
  - input: "check health"
    expected_skill: check_health
    expected_contains:
      - "ok"
    expected_not_contains:
      - "error"
      - "not found"
    description: "Agent checks health and reports ok"
  - input: "submit task-001"
    expected_skill: submit_task
    expected_contains:
      - "submitted"
    description: "Agent uses submit_task skill"
EOF

cat > agent/flow/evolve_auto/conversation_tests/reviewer.yaml << 'EOF'
role: reviewer
cases:
  - input: "review task-001, approved, looks good"
    expected_skill: review_task
    expected_contains:
      - "approved"
    description: "Reviewer uses review_task skill"
  - input: "list tasks"
    expected_skill: list_tasks
    expected_contains:
      - "task"
    description: "Reviewer can list tasks"
EOF

make deploy
```

---

## Phase 4: Evolver — Verify All Functions

All evolver reports save to `.runtime/data/evolve/reports/` in unified JSON format.

Scripts do mechanical work (extract data, run tests). The evolver LLM does reasoning (judge conditions, analyze failures, suggest improvements).

### 4.1 Verify scripts work standalone

| | |
|---|---|
| **Action** | Run each evolver script directly to verify they produce output |
| **Purpose** | Verify scripts themselves work before using through evolver TUI |
| **Expected** | Each script produces output + saves report JSON |

```bash
# 4.1a check_structure (no app needed)
uv run agent/flow/evolve_structure_check/scripts/check_structure.py --agent-dir agent
# Expected: STRUCTURE CHECK REPORT with ✓/✗ per check
# Includes flow graph validation when flows are defined (reachable states, terminal states, no isolation)
# Report saved to .runtime/data/evolve/reports/check_*.json

# 4.1b run_eval (needs app)
lsof -ti:8001 | xargs kill -9 2>/dev/null
uv run uvicorn src.app:app --port 8001 &
sleep 2
uv run agent/flow/evolve_api_check/scripts/run_eval.py \
  --cases agent/flow/evolve_api_check/eval_cases.yaml \
  --base-url http://localhost:8001
# Expected: API Score: 4/4 (100%)
# Report saved to .runtime/data/evolve/reports/eval_*.json
kill %1

# 4.1c diagnose (needs hook data from Phase 2.5)
uv run agent/flow/evolve_session_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --commitment agent/commitment/commitment.yaml
# Expected: DIAGNOSTIC DATA EXTRACTION
#   Lists from/to events per commitment with timestamps
#   NOTE: "Fulfillment NOT judged" — that's correct, evolver LLM judges
# Report saved to .runtime/data/evolve/reports/diagnose_*.json

# 4.1d run_auto (needs SDK — may not be installed)
lsof -ti:8001 | xargs kill -9 2>/dev/null
uv run uvicorn src.app:app --port 8001 &
sleep 2
uv run agent/flow/evolve_auto/scripts/run_auto.py \
  --tests-dir agent/flow/evolve_auto/conversation_tests \
  --adapter claude
# If SDK installed: Conversation Score: x/N
#   Per case: checks expected_skill + expected_contains + expected_not_contains
#   Failures show fail_reason (e.g. "missing keywords: ['ok']")
# If not: "claude-agent-sdk not installed" (exact message may vary by version)
kill %1

# Verify reports exist
ls .runtime/data/evolve/reports/
```

### 4.2 Evolver TUI — full cycle

| | |
|---|---|
| **Action** | Start evolver, run all 5 skills through conversation |
| **Purpose** | Verify evolver understands skills, reads references, makes judgments |
| **Expected** | Evolver runs scripts + interprets results + judges commitments + proposes improvements |

This is the CORE test — the evolver LLM must:
- Use scripts as tools (run them, read output)
- Read references/ for guidance on how to interpret results
- Judge commitment conditions (natural language → LLM reasoning)
- Map problems to four primitives
- Propose specific improvements

```bash
# Start backend first (evolver needs it for eval)
lsof -ti:8001 | xargs kill -9 2>/dev/null
uv run uvicorn src.app:app --port 8001 &
sleep 2

make start ROLE=evolver
# In Claude Code, do the full cycle:

# Step 1: "check structure"
#   → evolver runs check_structure.py
#   → reads output → explains results
#   → Expected: "All 4 checks passed" or lists specific gaps

# Step 2: "evaluate" (app must be running)
#   → evolver runs run_eval.py
#   → reads output → maps any failures to primitives
#   → Expected: "API Score 4/4" or "X failed — the /tasks endpoint..."

# Step 3: "diagnose"
#   → evolver runs diagnose.py → gets DATA EXTRACTION (events + timestamps)
#   → reads commitment.yaml → understands each condition
#   → JUDGES each commitment:
#     C1: "submit_task at 02:33, review_task never happened → VIOLATED"
#     C2: "create_task at 02:31, submit_task at 02:33 — only 2 minutes, well within 48h → FULFILLED"
#   → Maps violations to primitives
#   → Expected: evolver correctly identifies violations with time calculations

# Step 4: "improve" (based on all above)
#   → evolver reads evolve/reports/*.json
#   → thinks in order: Flow → Commitment → Scope → Role
#   → proposes specific changes (primitive + backend if needed):
#     "C1 violated — review_task never happens because no reviewer is using the app.
#      Suggestion: adjust commitment condition or add reminder skill.
#      Note: adding reminder skill requires implementing reminder endpoint in src/app.py."
#     "C2 fulfilled — 2 minutes well within 48h. No action needed."
#   → developer approves → evolver edits files → runs deploy
#   → evolver saves improve_*.json report to evolve/reports/
#   → Expected: evolver only modifies workspace files, NOT template

# Exit: Ctrl+C
kill %1  # stop uvicorn

# Verify template untouched:
cd ../../../..
git diff agent/
# Should show NO changes
cd .socialware/workspace/demo/task-review
```

### 4.3 Verify reports after evolver session

| | |
|---|---|
| **Action** | Check all reports and evolve directory |
| **Purpose** | Verify complete evolve output structure |
| **Expected** | Reports from each script, cursor updated |

```bash
# All reports
ls .runtime/data/evolve/reports/
# Should have: check_*.json, eval_*.json, diagnose_*.json
# (auto_test_*.json only if SDK installed)
# Note: improve_*.json is saved by evolver LLM after applying changes

# Cursor
cat .runtime/data/evolve/state.yaml
# Should have last_extraction timestamp + cursor

# Data dirs
ls .runtime/data/evolve/
# Expected: auto_sessions  reports  state.yaml  violations
```

**Note on report contents:**

Scripts produce mechanical reports (pass/fail counts, event extraction). The evolver LLM adds judgment and analysis **in conversation**, not in the JSON reports. Specifically:

| Report | Script provides | Evolver LLM adds (in conversation) |
|--------|----------------|-------------------------------------|
| check_*.json | Structural issues list | Priority ranking, fix suggestions |
| eval_*.json | API pass/fail per case | Failure-to-primitive mapping |
| diagnose_*.json | Extracted events + timestamps | Commitment fulfillment judgment |
| auto_test_*.json | Skill/content check results | Root cause analysis |
| improve_*.json | (none — evolver saves this) | What changed, why, what to re-test |

Flow transition events in diagnose reports only appear when `flows` are defined in flow.yaml (see Phase 7.12). At this phase, flows are empty (`flows: {}`), so only commitment events appear.

### 4.4 Violations API

| | |
|---|---|
| **Action** | Check violations API (evolve/violations/) |
| **Purpose** | Verify violations readable + resolvable via API |
| **Expected** | API returns violations, resolve works |

```bash
# Write a test violation (simulating diagnose output)
mkdir -p .runtime/data/evolve/violations
echo '{"id":"v-001","commitment":"C1","description":"review overdue","role":"reviewer","resolved":false}' \
  > .runtime/data/evolve/violations/current.jsonl

lsof -ti:8001 | xargs kill -9 2>/dev/null
uv run uvicorn src.app:app --port 8001 &
sleep 2
curl -s http://localhost:8001/violations
# Expected: [{"id":"v-001",...}]

curl -s -X POST http://localhost:8001/violations/v-001/resolve
# Expected: {"status":"resolved","id":"v-001"}
kill %1
rm .runtime/data/evolve/violations/current.jsonl
```

---

## Phase 5: Adapter Awareness

### 5.1 Deploy with codex adapter

| | |
|---|---|
| **Action** | Deploy with --adapter codex |
| **Purpose** | Verify adapter-specific output: .agents/skills (not .claude/), AGENTS.md (not SOUL.md) |
| **Expected** | Codex structure with .codex/hooks.json + config.toml |

```bash
make clean
make deploy ADAPTER=codex

# Check structure
ls .runtime/agents/default/.agents/skills/    # skills here
cat .runtime/agents/default/AGENTS.md | head -5  # not SOUL.md
cat .runtime/agents/default/.codex/hooks.json | python3 -m json.tool
# Should have UserPromptSubmit + PreToolUse
cat .runtime/agents/default/.codex/config.toml
# Should have codex_hooks = true

# Verify NO .claude/ directory
ls .runtime/agents/default/.claude/ 2>/dev/null
# Should not exist
```

### 5.2 Deploy with kimi adapter

| | |
|---|---|
| **Action** | Deploy with --adapter kimi |
| **Purpose** | Verify kimi output: .agents/skills/, AGENTS.md, NO hooks at all |
| **Expected** | No hooks directory for any adapter |

```bash
make clean
make deploy ADAPTER=kimi

ls .runtime/agents/default/.agents/skills/    # skills here
cat .runtime/agents/default/AGENTS.md | head -5  # not SOUL.md
ls .runtime/agents/default/.kimi/ 2>/dev/null  # should not exist (no hooks)
ls .runtime/agents/default/.codex/ 2>/dev/null # should not exist
ls .runtime/agents/default/.claude/ 2>/dev/null # should not exist
```

### 5.3 Restore claude adapter

| | |
|---|---|
| **Action** | Clean and redeploy with default claude adapter |
| **Purpose** | Restore to claude for remaining tests |
| **Expected** | Back to SOUL.md + .claude/ structure |

```bash
make clean
make deploy ADAPTER=claude

# Verify restored
cat .runtime/agents/default/SOUL.md | head -5
ls .runtime/agents/default/.claude/skills/
ls .runtime/agents/default/.claude/hooks/
```

---

## Phase 6: SDK Mode

### 6.1 SDK launch

| | |
|---|---|
| **Action** | Run start_agent.py |
| **Purpose** | Verify SDK mode launches, sends prompt, and saves session |
| **Expected** | Session JSON saved to .runtime/data/sessions/ |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2
uv run src/start_agent.py --role default --adapter claude --prompt "check health"
# Expected (if claude-agent-sdk installed):
#   [SDK] Sending prompt to default via claude...
#   Messages printed
#   Session saved to .runtime/data/sessions/default_session_*.json
# Expected (if SDK not installed):
#   [Claude SDK] claude-agent-sdk not installed.

ls .runtime/data/sessions/
# Should have session file (if SDK worked)
kill %1
```

### 6.2 SDK via Makefile

| | |
|---|---|
| **Action** | Run `make run` which invokes start_agent.py |
| **Purpose** | Verify Makefile `run` target works (auto-deploys + launches SDK) |
| **Expected** | Same as 6.1 but through Makefile |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2
make run ROLE=default PROMPT="check health"
# Same behavior as 6.1 (Makefile calls: uv run src/start_agent.py --role default --prompt "check health")
# Without PROMPT, make run shows error: "PROMPT is required"
kill %1
```

---

## Phase 7: Cross-Feature Verification

### 7.1 Multi-role startup

| | |
|---|---|
| **Action** | Start multiple roles in tmux |
| **Purpose** | Verify multi-role works via start.sh comma-separated roles |
| **Expected** | Two tmux panes with different skills |

```bash
./agent/start.sh --role default,reviewer
# Expected: tmux session "socialware-*", 2 panes
# Pane 1 (default): check_health, create_task, submit_task, list_tasks
# Pane 2 (reviewer): check_health, review_task, list_tasks
# Exit: tmux kill-session
```

### 7.2 Platform adapters exist

| | |
|---|---|
| **Action** | Check adapter files: base.py + 3 adapters each with shell.sh + sdk.py |
| **Purpose** | Verify all adapters present with correct structure |
| **Expected** | 3 adapters, each with shell.sh + sdk.py, plus base.py |

```bash
ls agent/adapters/base.py          # BaseAdapter + RoleConfig + save_session
ls agent/adapters/claude/          # shell.sh  sdk.py
ls agent/adapters/codex/           # shell.sh  sdk.py
ls agent/adapters/kimicode/        # shell.sh  sdk.py

# Verify shell scripts are executable
test -x agent/adapters/claude/shell.sh && echo "claude OK"
test -x agent/adapters/codex/shell.sh && echo "codex OK"
test -x agent/adapters/kimicode/shell.sh && echo "kimicode OK"
```

### 7.3 Dev role — inspect + setup_claude

| | |
|---|---|
| **Action** | Start dev role |
| **Purpose** | Verify dev skills work (inspect shows structure, setup_claude available) |
| **Expected** | inspect shows four primitives layout, setup_claude skill present |

```bash
make start ROLE=dev
# In Claude Code:
#   "inspect" -> shows project structure (four primitives, dev workflow, key commands)
#   "/" -> should see: check_health, setup_claude, inspect
#   Exit: Ctrl+C
```

### 7.4 SOUL.md merge correctness

| | |
|---|---|
| **Action** | Read merged SOUL.md for each role |
| **Purpose** | Verify scope.md + role.md merged correctly with separator |
| **Expected** | Each SOUL.md contains scope content + "---" + role content |

```bash
cat .runtime/agents/default/SOUL.md
# Should contain scope content ("task-review") at top
# Then "---" separator
# Then role content ("Default Agent")

cat .runtime/agents/evolver/SOUL.md
# Should contain scope content at top
# Then "---" separator
# Then evolver role content ("Evolution role")
```

### 7.5 Flow.yaml deployed to all roles

| | |
|---|---|
| **Action** | Check flow.yaml copied to each role's .runtime/ |
| **Purpose** | Verify deploy copies flow.yaml for reference |
| **Expected** | Each role has flow.yaml matching agent/flow/flow.yaml |

```bash
diff agent/flow/flow.yaml .runtime/agents/default/flow.yaml
# No differences
diff agent/flow/flow.yaml .runtime/agents/evolver/flow.yaml
# No differences
```

### 7.6 Workspace self-contained

| | |
|---|---|
| **Action** | Run deploy.sh and start.sh directly from workspace |
| **Purpose** | Verify workspace works independently from repo root Makefile |
| **Expected** | Both scripts work using workspace's local agent/ |

```bash
./agent/deploy.sh        # should work (reads local agent/)
./agent/start.sh --role default
# Claude Code opens, skills available
# Exit: Ctrl+C
```

### 7.7 start.sh without --role lists available roles

| | |
|---|---|
| **Action** | Run start.sh without --role argument |
| **Purpose** | Verify start.sh shows available roles when no role specified |
| **Expected** | Lists all deployed roles |

```bash
./agent/start.sh
# Expected:
#   Available roles:
#     - default
#     - dev
#     - evolver
#     - reviewer
#   Usage: ./agent/start.sh --role <name>[,name2]
```

### 7.8 Independent pyproject.toml

| | |
|---|---|
| **Action** | Check workspace has its own pyproject.toml with app name |
| **Purpose** | Verify dependency independence |
| **Expected** | pyproject.toml exists with name = "task-review" |

```bash
cat pyproject.toml | grep "name ="
# Should contain: name = "task-review"
```

### 7.9 .runtime/data directory structure

| | |
|---|---|
| **Action** | Check .runtime/data/ directories created by deploy |
| **Purpose** | Verify data directories for Files, Sqlite, prompts, sessions exist |
| **Expected** | All four data directories present |

```bash
ls .runtime/data/
# Expected: Files  Sqlite  evolve  prompts  sessions
ls .runtime/data/evolve/
# Expected: auto_sessions  reports  violations
```

### 7.10 Automated tests pass

| | |
|---|---|
| **Action** | Run template tests from repo root |
| **Purpose** | Verify template tests still pass |
| **Expected** | All tests pass |

```bash
cd ../../../..    # back to repo root
make test
# Expected: all tests passed
cd .socialware/workspace/demo/task-review
```

### 7.11 make sync

| | |
|---|---|
| **Action** | Test sync from template |
| **Purpose** | Verify make sync copies latest scripts from template root |
| **Expected** | Adapters, deploy.sh, start.sh, Makefile, start_agent.py, evolver scripts updated |

```bash
make sync
# Expected: "Syncing from template: /home/yaosh/projects/Socialwares"
#           "Synced. Run 'make clean && make deploy' to rebuild."

# Verify a synced file matches template
diff agent/adapters/claude/sdk.py $(git rev-parse --show-toplevel)/agent/adapters/claude/sdk.py
# Should show no differences
```

### 7.12 Flow state machine with resource

| | |
|---|---|
| **Action** | Add a state machine to flow.yaml with resource field |
| **Purpose** | Verify flows DSL works: resource, states, transitions |
| **Expected** | Deploy injects workflow into SOUL.md, check validates graph |

```bash
# Add a state machine to flow.yaml (append before direct_actions)
cat > agent/flow/flow.yaml << 'EOF'
flows:
  task_lifecycle:
    name: task_lifecycle
    resource: task
    states: [draft, submitted, reviewed, closed]
    transitions:
      - { from: draft, action: submit_task, to: submitted, role: [default] }
      - { from: submitted, action: review_task, to: reviewed, role: [reviewer] }
      - { from: reviewed, action: close_task, to: closed, role: [default] }

direct_actions:
  - { action: check_health,     role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude,     role: [dev], description: "Configure Claude Code" }
  - { action: inspect,          role: [dev, evolver], description: "Show project structure" }
  - { action: create_task,      role: [default], description: "Create a new task" }
  - { action: submit_task,      role: [default], description: "Submit task for review" }
  - { action: review_task,      role: [reviewer], description: "Review a submitted task" }
  - { action: close_task,       role: [default], description: "Close a reviewed task" }
  - { action: list_tasks,       role: [default, reviewer], description: "List all tasks" }
  - { action: evolve_structure_check,     role: [evolver], description: "Check structural consistency" }
  - { action: evolve_session_diagnose,  role: [evolver], description: "Diagnose from runtime data" }
  - { action: evolve_api_check,      role: [evolver], description: "Run eval cases" }
  - { action: evolve_improve,   role: [evolver], description: "Apply improvements" }
  - { action: evolve_auto,      role: [evolver], description: "Automated conversation testing" }
EOF

# Note: close_task needs a SKILL.md for check_structure to pass
mkdir -p agent/flow/close_task
cat > agent/flow/close_task/SKILL.md << 'SKILL_EOF'
---
name: close_task
description: "Close a reviewed task"
---
# Close Task
## Trigger
User says "close task-xxx" etc.
## Flow
1. Get ID -> POST /tasks/{id}/close -> confirm
SKILL_EOF

make deploy

# Verify workflow injected into SOUL.md
grep "Workflows" .runtime/agents/default/SOUL.md
# Should contain "## Workflows" section

grep "task_lifecycle" .runtime/agents/default/SOUL.md
# Should contain "### task_lifecycle (resource: task)"

grep "draft → submit_task" .runtime/agents/default/SOUL.md
# Should show transition chain

# Verify check validates the graph
uv run agent/flow/evolve_structure_check/scripts/check_structure.py --agent-dir agent
# Expected: Flow State Machine Graph: ✓ All state machine graphs valid
```

---

## Phase 8: Scope Update

### 8.1 Update scope

| | |
|---|---|
| **Action** | Update scope.md to reflect actual capabilities |
| **Purpose** | Scope should match what the app can do |
| **Expected** | scope.md has task workflow capabilities, deployed to all roles |

```bash
cat > agent/scope/scope.md << 'EOF'
# Task Review App

A task review workflow app.

## Capabilities

- Health check (/health)
- Create tasks (POST /tasks)
- Submit tasks for review (POST /tasks/{id}/submit)
- Review tasks with decision (POST /tasks/{id}/review)
- List all tasks (GET /tasks)
- View violations (GET /violations)
- Resolve violations (POST /violations/{id}/resolve)

## Boundaries

- No authentication (single user)
- No persistence across restarts (in-memory)
- No task deletion or editing
EOF

make deploy

# Verify scope reflected in SOUL.md
cat .runtime/agents/default/SOUL.md | head -15
# Should contain "Task Review App" and capabilities list
```

### 8.2 Verify evolve_structure_check passes after scope update

| | |
|---|---|
| **Action** | Re-run check_structure.py with updated scope |
| **Purpose** | Verify four-primitive consistency after scope + commitment + flow changes |
| **Expected** | PASS with updated scope capabilities listed |

```bash
uv run agent/flow/evolve_structure_check/scripts/check_structure.py --agent-dir agent
# Expected: STRUCTURE CHECK REPORT
#   Flow Actions -> SKILL.md: All actions have SKILL.md
#   Flow State Machine Graph: All state machine graphs valid (if flows defined)
#   Commitment References: All commitment references valid
#   Scope Capabilities:
#     SCOPE: - Health check (/health)
#     SCOPE: - Create tasks (POST /tasks)
#     ...
#   PASS: No structural issues found.
#
# Note: SKILL.md files should not contain hardcoded URLs.
# The agent discovers endpoints from project configuration.
```

---

## Phase 9: Make clean and rebuild

### 9.1 Clean removes .runtime/

| | |
|---|---|
| **Action** | Run `make clean` |
| **Purpose** | Verify clean removes entire .runtime/ directory |
| **Expected** | .runtime/ gone, agent/ untouched |

```bash
make clean
ls .runtime/ 2>/dev/null
# Should not exist

ls agent/role/
# Still present: default.md  dev.md  evolver.md  reviewer.md
ls agent/flow/flow.yaml
# Still present
```

### 9.2 Full rebuild from clean state

| | |
|---|---|
| **Action** | Deploy from scratch after clean |
| **Purpose** | Verify full rebuild works |
| **Expected** | All roles, skills, hooks restored |

```bash
make deploy

ls .runtime/agents/
# Expected: default  dev  evolver  reviewer

ls .runtime/agents/default/.claude/skills/
# Expected: check_health  create_task  list_tasks  submit_task

ls .runtime/agents/evolver/.claude/skills/ | wc -l
# Expected: 7
```

---

## Cleanup

```bash
cd ../../../..
rm -rf .socialware/workspace/demo
```
