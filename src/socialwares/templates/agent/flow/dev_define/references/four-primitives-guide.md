# Four Primitives Reference Guide

Socialware uses four primitives to describe the complete structure of an Agent App. Each primitive answers a core question.

---

## 1. Scope (Capability Boundary) — "What can this App do?"

**Why it's needed**: Scope is the App's contractual boundary. The Agent only does what scope declares, and nothing it doesn't. This ensures the App's predictability and safety.

**File**: `agent/scope/scope.md`

**Writing guidelines**:
- Capabilities: what the App can do (maps to API endpoints)
- Boundaries: what the App does NOT do

```markdown
# Task Review App

Manages task creation, submission, and review workflow.

## Capabilities
- Create tasks (POST /api/tasks)
- List tasks (GET /api/tasks)
- Review tasks (POST /api/tasks/{id}/review)
- Health check (GET /health)

## Boundaries
- Does not send notifications
- Does not manage user permissions
```

---

## 2. Role — "Who uses this App?"

**Why it's needed**: Different roles have different permissions and perspectives. The Agent decides which skills to use and what identity to interact with the user based on its role.

**File**: `agent/role/{name}.md` (one file per role)

**Writing guidelines**:
- Identity: who the role is, in one sentence
- Responsibilities: what this role is responsible for
- Tone and style: technical? friendly? strict?

```markdown
# Reviewer Agent

Responsible for reviewing and approving tasks submitted by the team.

## Identity
- Role: Task Reviewer
- Permissions: view tasks, review tasks, reject tasks

## Responsibilities
1. Review submitted tasks promptly (within 24h)
2. Provide clear review feedback
3. Reject unqualified tasks with reasons

## Style
- Rigorous but friendly
- Review comments should be specific, not just "rejected"
```

**Built-in roles** (included in template, no need to create manually):
- `default` — default business role
- `dev` — development assistant role (inspect, build, iterate, release)
- `evolver` — analysis and improvement role (structure check, evaluate, diagnose, improve)

---

## 3. Flow (Actions) — "What can each role do? How?"

**Why it's needed**: Flow defines the Agent's behavior — what steps to execute when receiving a given command. Each action corresponds to a SKILL.md file.

**Directory structure**:
```
agent/flow/{action}/
├── SKILL.md           ← required: trigger conditions + execution steps
├── scripts/           ← optional: automation scripts
└── references/        ← optional: reference documents
```

**SKILL.md writing guidelines**:
- Trigger: what the user says to trigger it (include both English and Chinese if applicable)
- Flow: step-by-step execution process, specifying which APIs to call
- Error Handling: how to handle errors

```markdown
---
name: create_task
description: "Create a new task"
---

# Create Task

## Trigger
User says "create task", "add task" etc.

## Flow
1. Ask user for task title and description
2. Call API: POST /api/tasks {"title": "...", "description": "..."}
3. If success: show task ID and confirm
4. If error: explain what went wrong

## Error Handling
- 400: "Task title is required"
- 500: "Server error, please try again"
```

**Registration**: In `socialware.py`, use `app.action("create_task", role=["default"])`

**Transitions (optional)**: If actions have a fixed state flow between them:
```python
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
```

---

## 4. Commitment — "How do roles collaborate?"

**Why it's needed**: When multiple roles collaborate, commitments are needed to ensure service quality. For example, "must review within 24h after submission" — without a commitment, the evolver cannot detect review delays.

**Definition location**: Declared in `socialware.py` (not a separate file)

**Writing guidelines**:
- from_: the trigger party (which role's which action)
- to: the responder (which role should do what)
- condition: natural language condition (evolver uses LLM to evaluate whether it's met)
- on_violation: remediation action when violated

```python
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

**Meaning**: After the default role executes submit_task, the reviewer role should execute review_task within 24 hours. If not, the remind_review action is triggered.

**Notes**:
- Commitments are only visible to and evaluated by the evolver
- condition is natural language; the evolver (LLM) is responsible for evaluation
- If the App has only one role, commitments can be omitted

---

## Relationship Between the Four Primitives

```
Scope    → Capability boundary (what the App does)
  ↓
Role     → Role definitions (who does it)
  ↓
Flow     → Action definitions (how to do it) + Transitions (in what order)
  ↓
Commitment → Collaboration constraints (what's expected after an action)
```

Scope constrains Flow (features not in scope should not have corresponding actions).
Role determines Flow (each action is assigned to specific roles).
Commitment connects Roles (after Role A does something, how Role B should respond).
