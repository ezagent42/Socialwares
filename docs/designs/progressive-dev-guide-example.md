# Progressive Growth Example — Building a Task Manager

A step-by-step example of building a Socialware App through progressive growth (P1→P5→P0).

We start with the minimal template and grow a task management app through 5 phases, each adding capabilities to the Biz layer (API + UI + DB).

---

## Setup

```bash
# From repo root
uv run scripts/create-my-socialware.py --room my-team --app taskarena --description "Task management"
cd .socialware/workspace/my-team/taskarena
```

Created structure:
```
taskarena/
├── src/app.py              ← /health endpoint only
├── agent/
│   ├── role/default/SOUL.md
│   ├── scope/SOUL.md
│   ├── commitment/eval.yaml   ← empty
│   ├── flow/
│   │   ├── flow.yaml           ← check_health + setup_claude
│   │   ├── check_health/SKILL.md
│   │   └── setup_claude/SKILL.md
│   ├── deploy.sh
│   └── start.sh
└── pyproject.toml
```

---

## Phase 1: Define Agent — Pure Chat

**Focus**: scope/SOUL.md + one role + minimal flow.
User does almost everything through chat. The only UI is the chat box.

### What we have

```bash
./agent/start.sh --role default
# Agent can: check health. That's it.
```

### What the user experiences

```
User: "What can you do?"
Agent: "I can check if the app is running. Say 'check health'."
User: "check health"
Agent: → calls GET /health → "App is healthy (status: ok)"
User: "Create a task called GPS purchase"
Agent: "I don't have a skill for creating tasks yet."
```

The agent is honest about what it can't do. This is the signal to move to P2.

---

## Phase 2: Refine Flow — Get Things Right

**Focus**: Add skills + API endpoints. Each skill you add materializes as Biz layer growth.

### Step 2.1: Add create_task skill

```bash
mkdir -p agent/flow/create_task
```

`agent/flow/create_task/SKILL.md`:
```markdown
---
name: create_task
description: "Create a new task"
---

# Create Task

## Trigger
User says "create task", "new task", "add task" etc.

## Flow
1. Extract title and description from user input
2. Call API: POST /tasks
3. Return the created task with its ID

## API
```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "description": "..."}'
```
```

### Step 2.2: Add the API endpoint

`src/app.py` — add task storage and endpoint:

```python
from datetime import datetime, timezone
from typing import Any

# In-memory store (replace with Sqlite in .runtime/data/ later)
_tasks: dict[str, dict[str, Any]] = {}
_counter = 0

@app.post("/tasks")
async def create_task(data: dict[str, Any]) -> dict[str, Any]:
    global _counter
    _counter += 1
    task_id = f"task-{_counter:03d}"
    task = {
        "id": task_id,
        "title": data.get("title", "Untitled"),
        "description": data.get("description", ""),
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task

@app.get("/tasks")
async def list_tasks() -> list[dict[str, Any]]:
    return list(_tasks.values())
```

### Step 2.3: Register in flow.yaml

```yaml
direct_actions:
  - { action: check_health,  role: [default, dev], description: "Check app health" }
  - { action: setup_claude,  role: [dev], description: "Configure Claude Code" }
  - { action: create_task,   role: [default], description: "Create a new task" }
  - { action: list_tasks,    role: [default], description: "List all tasks" }
```

### Step 2.4: Start and test

```bash
# Start backend in background
uv run uvicorn src.app:app --port 8001 &

# Start agent (auto-deploys since agent/ changed)
./agent/start.sh --role default
```

```
User: "Create a task called GPS purchase with budget 300000"
Agent: → POST /tasks → "Created task-001: GPS purchase"
User: "List tasks"
Agent: → GET /tasks → "1 task: task-001 GPS purchase (draft)"
```

**Biz layer grew**: 2 new API endpoints, 2 new skills.

### Step 2.5: Add more skills (submit, query by status)

Repeat the pattern: create SKILL.md → add API endpoint → register in flow.yaml.

By the end of P2, you might have:
```
agent/flow/
├── flow.yaml
├── check_health/SKILL.md
├── setup_claude/SKILL.md
├── create_task/SKILL.md
├── list_tasks/SKILL.md
├── submit_task/SKILL.md
└── query_task/SKILL.md
```

And `src/app.py` has grown from 1 endpoint to 6.

---

## Phase 3: Refine Commitment — Get Things Done Right

**Focus**: Add eval metrics and SLAs. The app works, but how do we know it works *well*?

### Step 3.1: Define commitments

`agent/commitment/eval.yaml`:
```yaml
commitments:
  C1:
    description: "All submitted tasks receive a review within 72 hours"
    metric: time_to_review
    threshold: "<=72h"
    debtor_role: reviewer
    creditor_role: default

  C2:
    description: "Task creation success rate >= 95%"
    metric: create_success_rate
    threshold: ">=0.95"
```

### Step 3.2: Add monitoring to the app

`src/app.py` — add review tracking:

```python
@app.post("/tasks/{task_id}/action/{action}")
async def task_action(task_id: str, action: str, data: dict = None) -> dict:
    # ... state machine logic ...
    task["last_action"] = {
        "action": action,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    return task

@app.get("/metrics")
async def metrics() -> dict:
    """Commitment metrics endpoint."""
    # Calculate time_to_review, success rates, etc.
    return {"time_to_review_avg_hours": 24, "create_success_rate": 0.98}
```

### Step 3.3: Add notification skill (P3 trigger)

The reason P3 happens: users complain "I submitted a task 3 days ago, nobody reviewed it."

```bash
mkdir -p agent/flow/remind_review
```

`agent/flow/remind_review/SKILL.md`:
```markdown
---
name: remind_review
description: "Remind reviewers about pending tasks approaching SLA deadline"
---

# Remind Review

## Trigger
Cron or user says "check overdue reviews"

## Flow
1. GET /tasks?status=submitted
2. Check created_at vs now
3. If approaching 72h → notify reviewer
```

**Biz layer grew**: metrics endpoint, notification logic, review tracking.

---

## Phase 4: Expand Scope — Go Wider

**Focus**: The app's capability boundary expands. SOUL.md gets richer.

### Step 4.1: Update scope

`agent/scope/SOUL.md`:
```markdown
# TaskArena

Task management Socialware App with team collaboration.

## Capabilities

- Task CRUD (create, read, update)
- State machine (draft → submitted → reviewed → approved → closed)
- Review workflow with SLA tracking (72h)
- Team notifications (email/slack)          ← NEW
- Task assignment across team members       ← NEW
- Priority-based task sorting               ← NEW

## Boundaries

- Task lifecycle management only (no project planning)
- Single-room scope (use /zchat for cross-room)
```

### Step 4.2: Add team-facing features

New skills:
```
agent/flow/
├── ...existing...
├── assign_task/SKILL.md        ← assign to team member
├── notify_team/SKILL.md        ← send notifications
└── prioritize_tasks/SKILL.md   ← sort by priority
```

New API endpoints:
```python
@app.post("/tasks/{task_id}/assign")
@app.post("/notifications/send")
@app.get("/tasks/prioritized")
```

**Biz layer grew**: team features, notifications, assignment logic.

---

## Phase 5: Expand Role — Add Agents

**Focus**: Multiple agent roles with different permissions and SOUL.md.

### Step 5.1: Add reviewer role

```bash
mkdir -p agent/role/reviewer
```

`agent/role/reviewer/SOUL.md`:
```markdown
# Reviewer Agent

You are a task reviewer for TaskArena.

## Identity
- Role: reviewer
- Permissions: review, approve, reject, comment

## Responsibilities
- Review submitted tasks within 72h (C1 commitment)
- Provide constructive feedback on rejected tasks
- Escalate blocked tasks to admin
```

### Step 5.2: Add admin role

```bash
mkdir -p agent/role/admin
```

`agent/role/admin/SOUL.md`:
```markdown
# Admin Agent

You are the admin for TaskArena.

## Identity
- Role: admin
- Permissions: all operations + force_resolve + audit

## Responsibilities
- Force-resolve stalled reviews (C2 commitment)
- Manage team membership
- Audit task history
```

### Step 5.3: Update flow.yaml with role-based actions

```yaml
flows:
  F1:
    name: task_lifecycle
    states: [draft, submitted, under_review, approved, rejected, closed]
    transitions:
      - { from: draft,         action: submit,   to: submitted,    role: [default] }
      - { from: submitted,     action: review,   to: under_review, role: [reviewer] }
      - { from: under_review,  action: approve,  to: approved,     role: [reviewer] }
      - { from: under_review,  action: reject,   to: rejected,     role: [reviewer] }
      - { from: rejected,      action: resubmit, to: submitted,    role: [default] }
      - { from: approved,      action: close,     to: closed,       role: [admin] }

direct_actions:
  - { action: check_health,     role: [default, dev, reviewer, admin], description: "Check health" }
  - { action: setup_claude,     role: [dev], description: "Configure Claude Code" }
  - { action: create_task,      role: [default, admin], description: "Create task" }
  - { action: list_tasks,       role: [default, dev, reviewer, admin], description: "List tasks" }
  - { action: query_task,       role: [default, dev, reviewer, admin], description: "Query task" }
  - { action: assign_task,      role: [admin], description: "Assign task" }
  - { action: remind_review,    role: [admin], description: "Remind overdue reviews" }
  - { action: notify_team,      role: [admin], description: "Send notification" }
  - { action: force_resolve,    role: [admin], description: "Force resolve stalled task" }
```

### Step 5.4: Launch multiple agents

```bash
# Three agents in tmux panes
./agent/start.sh --role default,reviewer,admin
```

Each agent gets only its allowed skills:
- `default` → create_task, list_tasks, submit, etc.
- `reviewer` → review, approve, reject, list_tasks
- `admin` → everything + force_resolve

**Biz layer grew**: role-based access control, multi-agent orchestration.

---

## Phase 0: Reach the Boundary — Go Beyond

TaskArena works great for tasks. But now the team needs calendar management.

Two options:

### Option A: Create a new Socialware App

```bash
# Back to repo root
cd ../../../../..
uv run scripts/create-my-socialware.py --room my-team --app calendar --description "Team calendar"
cd .socialware/workspace/my-team/calendar
# Start fresh P1→P5 cycle for calendar
```

### Option B: Connect via /zchat

If someone already built a calendar Socialware:
```
User (in TaskArena): "Schedule review for task-001 at 3pm tomorrow"
Agent: → /zchat → calendar.socialware.app → creates calendar event
       → links event to task-001
```

This is the network effect — Socialware Apps collaborate through agents.

---

## Summary

| Phase | What Changed | agent/ | src/ | Skills |
|-------|-------------|--------|------|--------|
| **P1** | Define agent | scope/SOUL.md, 1 role | /health | 1 |
| **P2** | Add capabilities | +flow/create_task, +flow/list_tasks... | +POST/GET /tasks | 6 |
| **P3** | Add quality metrics | +commitment/eval.yaml | +/metrics, +notifications | 8 |
| **P4** | Expand boundary | scope/SOUL.md ↑ | +/assign, +/notifications | 11 |
| **P5** | Add roles | +role/reviewer, +role/admin | +RBAC | 11 (role-filtered) |
| **P0** | New app or /zchat | — | — | — |

Each phase: edit agent/ → start (auto-deploy) → grow src/ → repeat.
