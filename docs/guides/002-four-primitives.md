# Four Primitives

## Why Four Primitives?

Socialware Apps are **Agent-facing**: the AI Agent is a first-class citizen alongside human users. Both need a shared language to coordinate. The four primitives form a minimal DSL that bridges human intent and Agent behavior:

```
Human intent         Four Primitives        Agent behavior
──────────          ────────────────        ──────────────
"Who does what"  →   Role + Flow        →  SOUL.md + SKILL.md
"What's allowed" →   Scope              →  Capability boundary
"What's expected"→   Commitment          →  Evaluation criteria
```

Without this DSL, developers write free-form prompts that drift, break, and can't be tested. The four primitives provide structure that both humans and Agents can reason about.

---

## Role — Who

A Role defines an Agent's identity, personality, and permissions.

### Declaration (socialware.py)

```python
app.role("default", file="agent/role/default.md")
app.role("reviewer", file="agent/role/reviewer.md")
```

Accepts either `file=` (path to .md) or `content=` (inline string), not both.

### Content (agent/role/*.md)

```markdown
# Default User

You are the primary user of the task management system.

## Responsibilities
- Create and manage tasks
- Submit tasks for review
```

### Compilation

Each role gets its own `.runtime/agents/{role}/SOUL.md` with the role description merged with scope.

### Key Design

- One .md file per role
- Roles are registered with actions via `app.action(..., role=[...])`
- The compiler generates per-role Agent configurations — each role only sees its own actions

---

## Scope — Where

Scope defines the App's capability boundary — what the App can and cannot do.

### Declaration (socialware.py)

```python
app.scope(file="agent/scope/scope.md")
```

### Content (agent/scope/scope.md)

```markdown
# Task Review App

## Capabilities
- Health check (/health)
- Task CRUD operations (/tasks)
- Task state management (submit, review, close)

## Boundaries
- Does not handle user authentication
- Does not send external notifications
```

### Compilation

Scope is merged into every role's SOUL.md. All roles share the same scope — it defines the App-level boundary, not role-level.

### Key Design

- One scope per App (shared across all roles)
- Only two sections: `## Capabilities` and `## Boundaries`
- Keeps the Agent focused — prevents hallucinating features outside scope

---

## Flow — How

Flow defines what actions the Agent can execute, and optionally, the state machine governing transitions between actions.

### Actions

An action maps to a skill directory (`agent/flow/{action}/SKILL.md`):

```python
app.action("check_health", role=["default"])
app.action("create_task", role=["default"])
app.action("review_task", role=["reviewer"])
```

Each action must have a corresponding `agent/flow/{action}/SKILL.md`. The compiler validates this.

### Skill Directory Structure

```
agent/flow/create_task/
├── SKILL.md            ← Agent execution instructions (required)
├── scripts/            ← Automation scripts (optional)
└── references/         ← Reference materials (optional)
```

### State Machine (optional)

For actions that follow a fixed transition order:

```python
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
flow.transition("reviewed", "close_task", "closed", role=["default"])
```

State machine transitions are injected into SOUL.md as a `## Workflows` section. The Agent sees the allowed transitions for its role.

### Compilation

- Actions → skill symlinks in `.runtime/agents/{role}/.claude/skills/`
- State machines → `## Workflows` in SOUL.md + `.runtime/flow.yaml`

### Key Design

- One directory per action, uniform structure
- Flow transitions create implicit actions (registered to their roles)
- `actions_for_role()` returns both direct actions and flow transition actions

---

## Commitment — What Standard

Commitment defines evaluation criteria on flow edges — what "good" looks like between two role-actions. It is **not** an enforcement mechanism; it is an assessment standard used by the evolver.

### Declaration (socialware.py)

```python
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("tech_lead", "escalate"),  # optional
)
```

### Compiled Schema (.runtime/commitment.yaml)

```yaml
commitments:
  C1:
    from: { role: default, action: submit_task }
    to:   { role: reviewer, action: review_task }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }
```

| Field | Required | Description |
|-------|----------|-------------|
| `from` | yes | Edge start: who did what (trigger) |
| `to` | yes | Edge end: who must do what (response) |
| `condition` | yes | Evaluation standard (natural language) |
| `on_violation` | no | Suggested escalation path |

### Key Design

- Commitment is **invisible** to non-evolver roles — only the evolver reads `commitment.yaml`
- Other roles operate based on SOUL.md (scope + role) and skills
- The evolver's `diagnose.py` matches hook log events to commitment actions, then computes fulfillment rates
- This separation keeps the Agent natural while enabling systematic evaluation

---

## How They Connect

```
socialware.py                        .runtime/
─────────────                        ─────────
app.scope(file=...)      ──────→     agents/{role}/SOUL.md  (scope section)
app.role("x", file=...)  ──────→     agents/{role}/SOUL.md  (role section)
app.action("a", role=[]) ──────→     agents/{role}/.claude/skills/a → agent/flow/a/
app.flow().transition()  ──────→     agents/{role}/SOUL.md  (## Workflows)
                                     flow.yaml
app.commitment(...)      ──────→     commitment.yaml  (evolver reads)
```

The four primitives form a complete specification:
- **Role** answers "who" → identity in SOUL.md
- **Scope** answers "where" → boundary in SOUL.md
- **Flow** answers "how" → skills + state machine
- **Commitment** answers "what standard" → evolver assessment criteria
