# End-to-End Test Plan

Manual test plan covering every feature. Run from a clean state.

## Prerequisites

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

---

## 1. Template Deploy via Workspace

Deploy and start only happen inside workspaces — never at the repo root. `.runtime/` never exists at repo root.

### 1.1 Create a workspace and verify deploy

| | |
|---|---|
| **Action** | `make create` then verify .runtime/ inside workspace |
| **Purpose** | Verify create copies template, deploys into workspace |
| **Verify** | Workspace has `.runtime/agents/default/`, `dev/`, `evolver/` |

```bash
make create ROOM=test APP=template-check DESC="Template verification"
cd .socialware/workspace/test/template-check

ls .runtime/agents/
# Expected: default  dev  evolver
```

### 1.2 Check .runtime/ structure (inside workspace)

| | |
|---|---|
| **Action** | Inspect .runtime/ contents inside workspace |
| **Purpose** | Verify deploy generates correct structure per role |
| **Verify** | Each role has: .claude/skills/, .claude/hooks/, SOUL.md, constraints.yaml, flow.yaml |

```bash
# From within workspace:
ls .runtime/agents/default/
# Expected: .claude  SOUL.md  constraints.yaml  flow.yaml

ls .runtime/agents/default/.claude/skills/
# Expected: check_health (symlink)
# NOT: setup_claude, evolve_* (those are for dev/evolver only)

ls .runtime/agents/evolver/.claude/skills/
# Expected: check_health, evolve_auto, evolve_diagnose, evolve_eval, evolve_improve, inspect

ls .runtime/agents/default/.claude/hooks/
# Expected: check_violations.sh  log_action.sh
```

### 1.3 Check SOUL.md merge

| | |
|---|---|
| **Action** | Read merged SOUL.md |
| **Purpose** | Verify scope.md + role.md merged correctly |
| **Verify** | Contains content from both scope/scope.md and role/default.md |

```bash
# From within workspace:
cat .runtime/agents/default/SOUL.md
# Should contain scope content ("Socialware App") AND role content ("Default Agent")
```

### 1.4 Skill filtering by role

| | |
|---|---|
| **Action** | Compare skills across roles |
| **Purpose** | Verify flow.yaml role filtering works |
| **Verify** | default has fewer skills than evolver |

```bash
# From within workspace:
ls .runtime/agents/default/.claude/skills/ | wc -l   # Expected: 1 (check_health)
ls .runtime/agents/dev/.claude/skills/ | wc -l        # Expected: 3 (check_health, setup_claude, inspect)
ls .runtime/agents/evolver/.claude/skills/ | wc -l     # Expected: 6 (check_health, inspect, evolve_diagnose/eval/improve/auto)
```

### 1.5 Make start (from workspace)

| | |
|---|---|
| **Action** | `make start` from within workspace |
| **Purpose** | Verify agent launches in default role |
| **Verify** | Claude Code TUI opens, SOUL.md loaded, skills available |

```bash
# From within workspace:
make start
# In Claude Code:
#   - Type "/" → should see "check_health" in skill list
#   - Say "check health" → should attempt to call GET /health
#   - Exit: Ctrl+C
```

### 1.6 Make idempotency

| | |
|---|---|
| **Action** | Run `make deploy` twice from within workspace |
| **Purpose** | Verify Make skips rebuild when nothing changed |
| **Verify** | Both runs say "nothing to be done" (create already deployed) |

```bash
# From within workspace (create already deployed, so both show up-to-date):
make deploy    # "Nothing to be done for 'deploy'." (create already deployed)
make deploy    # same result
```

### 1.7 Make change detection

| | |
|---|---|
| **Action** | Edit a file, run `make deploy` from within workspace |
| **Purpose** | Verify Make detects source changes |
| **Verify** | Redeploys after edit |

```bash
# From within workspace:
echo "# test" >> agent/scope/scope.md
make deploy    # should rebuild (runs deploy.sh)
# Restore: remove the line we added
sed -i '$ d' agent/scope/scope.md
```

---

## 2. Create Workspace

### 2.1 Create workspace

| | |
|---|---|
| **Action** | `make create ROOM=test APP=hello DESC="Test App"` |
| **Purpose** | Verify workspace creation with room/app structure |
| **Verify** | Directory created, files copied, SOUL files customized, auto-deployed |

```bash
make create ROOM=test APP=hello DESC="Test App"

# Check structure
ls .socialware/workspace/test/hello/
# Expected: agent  app  pyproject.toml  src  .runtime

# Check customization
cat .socialware/workspace/test/hello/agent/scope/scope.md
# Should contain "hello" and "Test App"

cat .socialware/workspace/test/hello/agent/role/default.md
# Should contain "hello"

# Check auto-deploy
ls .socialware/workspace/test/hello/.runtime/agents/
# Expected: default  dev  evolver
```

### 2.2 Duplicate workspace fails

| | |
|---|---|
| **Action** | Run create again with same room/app |
| **Purpose** | Verify won't overwrite existing workspace |
| **Verify** | Exits with error |

```bash
make create ROOM=test APP=hello DESC="Test"
# Expected: error message, non-zero exit code
```

### 2.3 Workspace self-contained

| | |
|---|---|
| **Action** | Deploy and start from within workspace |
| **Purpose** | Verify workspace works independently from repo root |
| **Verify** | deploy.sh and start.sh work using workspace's local agent/ |

```bash
cd .socialware/workspace/test/hello
./agent/deploy.sh        # should work (reads local agent/)
./agent/start.sh --role default
# Claude Code opens, check_health skill available
# Exit: Ctrl+C
cd ../../../..            # back to repo root
```

### 2.4 Independent pyproject.toml

| | |
|---|---|
| **Action** | Check workspace has its own pyproject.toml |
| **Purpose** | Verify dependency independence |
| **Verify** | pyproject.toml exists with app name |

```bash
cat .socialware/workspace/test/hello/pyproject.toml
# Should contain: name = "hello"
```

---

## 3. Four Primitives

### 3.1 Add a new skill

| | |
|---|---|
| **Action** | Create a new flow action in workspace |
| **Purpose** | Verify custom skills work |
| **Verify** | New skill appears in deployed .runtime/ |

```bash
cd .socialware/workspace/test/hello

mkdir -p agent/flow/greet
cat > agent/flow/greet/SKILL.md << 'EOF'
---
name: greet
description: "Say hello"
---
# Greet
## Trigger
User says "hello" or "greet"
## Flow
Respond with a greeting.
EOF

# Register in flow.yaml
echo '  - { action: greet, role: [default], description: "Say hello" }' >> agent/flow/flow.yaml

./agent/deploy.sh
ls .runtime/agents/default/.claude/skills/
# Expected: check_health  greet

cd ../../../..
```

### 3.2 Add a new role

| | |
|---|---|
| **Action** | Create a new role in workspace |
| **Purpose** | Verify new roles are deployed |
| **Verify** | New role directory in .runtime/agents/ |

```bash
cd .socialware/workspace/test/hello

cat > agent/role/admin.md << 'EOF'
# Admin Agent
Admin role.
## Identity
- Role: admin
- Permissions: all
## Responsibilities
1. Manage the app
EOF

./agent/deploy.sh
ls .runtime/agents/
# Expected: admin  default  dev  evolver

cd ../../../..
```

### 3.3 Remove a role

| | |
|---|---|
| **Action** | Delete a role file, redeploy |
| **Purpose** | Verify deploy cleans up removed roles |
| **Verify** | Removed role's .runtime/ directory is gone |

```bash
cd .socialware/workspace/test/hello

rm agent/role/admin.md
./agent/deploy.sh
ls .runtime/agents/
# Expected: default  dev  evolver  (no admin)

cd ../../../..
```

---

## 4. Constraints + Violations

### 4.1 Constraints copied to .runtime/

| | |
|---|---|
| **Action** | Check constraints.yaml in deployed roles |
| **Purpose** | Verify deploy copies constraints |
| **Verify** | constraints.yaml exists in each role's .runtime/ |

```bash
# From within workspace:
cat .runtime/agents/default/constraints.yaml
# Should match agent/commitment/constraints.yaml
```

### 4.2 Violations API

| | |
|---|---|
| **Action** | Start backend, call violations endpoints |
| **Purpose** | Verify violations API works |
| **Verify** | GET /violations returns list, POST resolve works |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

curl http://localhost:8001/violations
# Expected: []

curl http://localhost:8001/health
# Expected: {"status":"ok"}

kill %1
```

### 4.3 Violations hook

| | |
|---|---|
| **Action** | Check hook exists and is executable |
| **Purpose** | Verify deploy generates violations hook |
| **Verify** | check_violations.sh is executable |

```bash
# From within workspace:
ls -la .runtime/agents/default/.claude/hooks/check_violations.sh
# Expected: -rwxr-xr-x
```

---

## 5. Conversation Logging

### 5.1 Logging hook exists

| | |
|---|---|
| **Action** | Check log_action.sh hook |
| **Purpose** | Verify deploy generates logging hook |
| **Verify** | log_action.sh is executable |

```bash
# From within workspace:
ls -la .runtime/agents/default/.claude/hooks/log_action.sh
# Expected: -rwxr-xr-x
```

---

## 6. Evolver

### 6.1 Start evolver

| | |
|---|---|
| **Action** | `make start ROLE=evolver` from within workspace |
| **Purpose** | Verify evolver role launches with correct skills |
| **Verify** | Claude Code opens, evolve skills available |

```bash
# From within workspace:
make start ROLE=evolver
# In Claude Code:
#   Type "/" → should see: evolve_diagnose, evolve_eval, evolve_improve, evolve_auto, inspect
#   Exit: Ctrl+C
```

### 6.2 Run diagnose

| | |
|---|---|
| **Action** | Run diagnose.py directly |
| **Purpose** | Verify diagnose works with no data |
| **Verify** | Produces report without errors |

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --constraints agent/commitment/constraints.yaml
# Expected: DIAGNOSTIC REPORT with "No conversation data yet"
```

### 6.3 Run eval

| | |
|---|---|
| **Action** | Run eval against live app |
| **Purpose** | Verify eval cases work |
| **Verify** | Reports score |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

uv run agent/flow/evolve_eval/scripts/run_eval.py \
  --cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001
# Expected: [PASS] Health check returns ok
#           Score: 1/1 (100%)

kill %1
```

---

## 7. Dev Role

### 7.1 Start dev

| | |
|---|---|
| **Action** | `./agent/start.sh --role dev` |
| **Purpose** | Verify dev role has correct skills |
| **Verify** | Claude Code opens with setup_claude + inspect skills |

```bash
./agent/start.sh --role dev
# In Claude Code:
#   Type "/" → should see: check_health, setup_claude, inspect
#   Say "inspect" → should show project structure
#   Exit: Ctrl+C
```

---

## 8. Platform Adapters

### 8.1 Adapter exists

| | |
|---|---|
| **Action** | Check adapter files |
| **Purpose** | Verify all 3 adapters are present |
| **Verify** | shell.sh executable for each |

```bash
ls -la agent/adapters/claude/shell.sh   # executable
ls -la agent/adapters/codex/shell.sh    # executable
ls -la agent/adapters/kimicode/shell.sh # executable
```

---

## 9. Automated Tests

### 9.1 Run pytest

| | |
|---|---|
| **Action** | `make test` (from repo root) |
| **Purpose** | Verify all automated tests pass |
| **Verify** | 36 tests pass |

```bash
# From repo root:
make test
# Expected: 36 passed
```

---

## 10. Full App Development Scenario — Todo App

Build a complete Todo app from scratch, testing every feature along the way.

### 10.1 Create the workspace

| | |
|---|---|
| **Action** | Create a Todo app workspace |
| **Purpose** | Start from template, get a self-contained workspace |
| **Verify** | Workspace created, auto-deployed, all files present |

```bash
make create ROOM=demo APP=todo DESC="Simple todo list"
cd .socialware/workspace/demo/todo

ls agent/role/        # default.md  dev.md  evolver.md  README.md
ls agent/scope/       # scope.md  README.md
ls .runtime/agents/   # default  dev  evolver
cat agent/scope/scope.md  # Should contain "todo"
```

### 10.2 Define scope

| | |
|---|---|
| **Action** | Edit scope.md for the Todo app |
| **Purpose** | Define what the app can do |
| **Verify** | scope.md has Todo-specific content |

```bash
cat > agent/scope/scope.md << 'EOF'
# Todo App

Simple todo list manager.

## Capabilities

- Health check (/health)
- Create todo items
- List todo items
- Mark todos as done

## Boundaries

- No user authentication (single user)
- No persistence across restarts (in-memory)
- No priority/tags (keep it simple)
EOF
```

### 10.3 Add backend API

| | |
|---|---|
| **Action** | Add todo CRUD endpoints to src/app.py |
| **Purpose** | Build the Biz layer |
| **Verify** | API endpoints work |

```bash
cat > src/app.py << 'PYEOF'
"""Todo App backend."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Todo App", version="0.1.0")

_todos: dict[str, dict] = {}
_counter = 0

VIOLATIONS_DIR = Path(".runtime/data/violations")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/todos")
async def create_todo(data: dict[str, Any]):
    global _counter
    _counter += 1
    todo_id = f"todo-{_counter:03d}"
    todo = {
        "id": todo_id,
        "title": data.get("title", "Untitled"),
        "done": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _todos[todo_id] = todo
    return todo

@app.get("/todos")
async def list_todos():
    return list(_todos.values())

@app.get("/todos/{todo_id}")
async def get_todo(todo_id: str):
    if todo_id not in _todos:
        raise HTTPException(404, f"Todo {todo_id} not found")
    return _todos[todo_id]

@app.post("/todos/{todo_id}/done")
async def mark_done(todo_id: str):
    if todo_id not in _todos:
        raise HTTPException(404, f"Todo {todo_id} not found")
    _todos[todo_id]["done"] = True
    return _todos[todo_id]

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
PYEOF
```

Test the API:

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

# Health
curl -s http://localhost:8001/health
# Expected: {"status":"ok"}

# Create
curl -s -X POST http://localhost:8001/todos -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
# Expected: {"id":"todo-001","title":"Buy milk","done":false,...}

# List
curl -s http://localhost:8001/todos
# Expected: [{"id":"todo-001",...}]

# Mark done
curl -s -X POST http://localhost:8001/todos/todo-001/done
# Expected: {"id":"todo-001","done":true,...}

kill %1
```

### 10.4 Add flow skills (P2: Refine Flow)

| | |
|---|---|
| **Action** | Create CRUD skills and register in flow.yaml |
| **Purpose** | Agent can now manage todos |
| **Verify** | Skills deployed, agent can use them |

```bash
# Create todo skill
mkdir -p agent/flow/create_todo
cat > agent/flow/create_todo/SKILL.md << 'EOF'
---
name: create_todo
description: "Create a new todo item"
---
# Create Todo
## Trigger
User says "add todo", "new task", "create todo" etc.
## Flow
1. Extract title from user input
2. POST /todos with title
3. Return created todo
## API
```bash
curl -X POST http://localhost:8001/todos -H "Content-Type: application/json" -d '{"title":"..."}'
```
EOF

# List todos skill
mkdir -p agent/flow/list_todos
cat > agent/flow/list_todos/SKILL.md << 'EOF'
---
name: list_todos
description: "List all todo items"
---
# List Todos
## Trigger
User says "list todos", "show tasks", "what needs doing" etc.
## Flow
1. GET /todos
2. Format and display results
## API
```bash
curl http://localhost:8001/todos
```
EOF

# Mark done skill
mkdir -p agent/flow/mark_done
cat > agent/flow/mark_done/SKILL.md << 'EOF'
---
name: mark_done
description: "Mark a todo as done"
---
# Mark Done
## Trigger
User says "done", "complete", "finish todo-xxx" etc.
## Flow
1. Get todo ID from user
2. POST /todos/{id}/done
3. Confirm completion
## API
```bash
curl -X POST http://localhost:8001/todos/todo-001/done
```
EOF

# Register in flow.yaml — replace the entire file
cat > agent/flow/flow.yaml << 'EOF'
flows: {}

direct_actions:
  - { action: check_health,  role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude,  role: [dev], description: "Configure Claude Code" }
  - { action: inspect,       role: [dev, evolver], description: "Show project structure" }
  - { action: create_todo,   role: [default], description: "Create a todo item" }
  - { action: list_todos,    role: [default], description: "List todo items" }
  - { action: mark_done,     role: [default], description: "Mark todo as done" }
  - { action: evolve_diagnose, role: [evolver], description: "Diagnose issues" }
  - { action: evolve_eval,     role: [evolver], description: "Run eval cases" }
  - { action: evolve_improve,  role: [evolver], description: "Apply improvements" }
  - { action: evolve_auto,     role: [evolver], description: "Automated evolution" }
EOF

# Deploy
./agent/deploy.sh

# Verify
ls .runtime/agents/default/.claude/skills/
# Expected: check_health  create_todo  list_todos  mark_done
```

### 10.5 Test agent with skills

| | |
|---|---|
| **Action** | Start agent and use todo skills |
| **Purpose** | Verify agent can manage todos via skills |
| **Verify** | Agent creates, lists, and completes todos |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

./agent/start.sh --role default
# In Claude Code:
#   "add a todo: buy groceries"   → should call POST /todos
#   "list todos"                  → should call GET /todos
#   "mark todo-001 as done"      → should call POST /todos/todo-001/done
#   Exit: Ctrl+C

kill %1
```

### 10.6 Add eval cases (P3: Refine Commitment)

| | |
|---|---|
| **Action** | Write eval cases for the Todo app |
| **Purpose** | Establish "correct answer set" |
| **Verify** | Eval passes against running app |

```bash
cat > agent/flow/evolve_eval/eval_cases.yaml << 'EOF'
cases:
  - description: "Health check returns ok"
    method: GET
    endpoint: /health
    expected_status: 200
    expected_body: '{"status":"ok"}'

  - description: "Create todo returns 200"
    method: POST
    endpoint: /todos
    body: '{"title":"test item"}'
    expected_status: 200

  - description: "List todos returns array"
    method: GET
    endpoint: /todos
    expected_status: 200
EOF

# Run eval
uv run uvicorn src.app:app --port 8001 &
sleep 2

uv run agent/flow/evolve_eval/scripts/run_eval.py \
  --cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001
# Expected: Score: 3/3 (100%)

kill %1
```

### 10.7 Add constraints

| | |
|---|---|
| **Action** | Define a postcondition constraint |
| **Purpose** | Test constraints work with the app |
| **Verify** | constraints.yaml deployed correctly |

```bash
cat > agent/commitment/constraints.yaml << 'EOF'
transition_constraints: {}

action_constraints:
  C1:
    description: "Health check returns ok"
    on: { action: check_health }
    type: postcondition
    expected: '{"status":"ok"}'

  C2:
    description: "Create todo returns valid JSON"
    on: { action: create_todo }
    type: postcondition
    expected_status: 200
EOF

./agent/deploy.sh
cat .runtime/agents/default/constraints.yaml
# Should match what we wrote
```

### 10.8 Run evolver diagnose

| | |
|---|---|
| **Action** | Run diagnose against the Todo app |
| **Purpose** | Verify evolver can analyze the app |
| **Verify** | Report shows constraints and no issues |

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --constraints agent/commitment/constraints.yaml
# Expected: DIAGNOSTIC REPORT
#   Active Constraints: 2 (action constraints)
#   No conversation data (haven't used the app yet)
```

### 10.9 Add a reviewer role (P5: Expand Role)

| | |
|---|---|
| **Action** | Add a reviewer role with limited skills |
| **Purpose** | Test multi-role setup |
| **Verify** | Reviewer gets only list_todos, not create_todo |

```bash
cat > agent/role/reviewer.md << 'EOF'
# Reviewer Agent

Reviews todo items.

## Identity

- Role: reviewer
- Permissions: read-only access

## Responsibilities

1. List and review todo items
EOF

# Update flow.yaml — add reviewer to list_todos only
# Edit the list_todos line:
sed -i 's/action: list_todos,    role: \[default\]/action: list_todos,    role: [default, reviewer]/' agent/flow/flow.yaml

./agent/deploy.sh

ls .runtime/agents/reviewer/.claude/skills/
# Expected: check_health  list_todos  (NOT create_todo, mark_done)
```

### 10.10 Multi-role startup

| | |
|---|---|
| **Action** | Start default + reviewer in tmux |
| **Purpose** | Verify multi-role works |
| **Verify** | Two tmux panes, different skills |

```bash
./agent/start.sh --role default,reviewer
# Expected: tmux session with 2 panes
# Pane 1 (default): has create_todo, list_todos, mark_done
# Pane 2 (reviewer): has only list_todos, check_health
# Exit: Ctrl+b then d (detach), then tmux kill-session
```

### 10.11 Test evolve_improve (manual mode)

| | |
|---|---|
| **Action** | Start evolver, do a full diagnose → improve cycle |
| **Purpose** | Verify conversational improvement workflow |
| **Verify** | Evolver reads diagnostic data, proposes changes, applies them |

```bash
./agent/start.sh --role evolver
# In Claude Code:
#   "diagnose"
#   → Evolver runs diagnose.py → shows report
#   → "No conversation data yet" (normal for new app)
#
#   "evaluate"
#   → Evolver runs run_eval.py → "Score: 3/3 (100%)"
#
#   "The check_health skill description is too brief. Improve it."
#   → Evolver should:
#     1. Read agent/flow/check_health/SKILL.md
#     2. Propose an improvement
#     3. Ask for approval
#     4. On "yes" → edit the file → run deploy.sh
#
#   "evaluate" again
#   → Should still be 3/3 (improvement didn't break anything)
#
#   Exit: Ctrl+C

# Verify the file was actually changed:
cat agent/flow/check_health/SKILL.md
# Should show the improvement evolver made
git diff agent/flow/check_health/SKILL.md
# Should show the diff
git checkout agent/flow/check_health/SKILL.md  # restore original
```

### 10.12 Test evolve_auto (automated loop)

| | |
|---|---|
| **Action** | Run the automated evolution loop |
| **Purpose** | Verify EvoSkill-based auto-optimization works |
| **Verify** | Loop runs, reports score, creates backup |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

# Run auto loop directly (outside of agent, to verify script)
uv run agent/flow/evolve_auto/scripts/run_loop.py \
  --eval-cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001 \
  --iterations 2
# Expected:
#   Initial score: 100% (all cases pass)
#   No failures — nothing to improve
#   (This is correct — app already passes all eval cases)

kill %1

# Also test via evolver conversation:
./agent/start.sh --role evolver
# "auto-optimize, run 2 iterations"
# → Evolver should run the loop script and report results
# Exit: Ctrl+C
```

### 10.13 Use evolver to inspect the app

| | |
|---|---|
| **Action** | Start evolver, use inspect skill |
| **Purpose** | Verify evolver can navigate the project |
| **Verify** | Inspect shows correct structure including new todo skills |

```bash
./agent/start.sh --role evolver
# In Claude Code:
#   "inspect" → should show project structure with create_todo, list_todos, mark_done skills
#   "evaluate" → should run eval cases (need backend running)
#   Exit: Ctrl+C
```

---

## 12. Cleanup

```bash
cd ../../../..     # back to repo root
rm -rf .socialware/workspace/demo
rm -rf .socialware/workspace/test
```
