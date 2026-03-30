# Four Primitives

Detailed guide to Role, Scope, Commitment, and Flow.

## Role — Who

Agent identities. Each role is a flat `.md` file in `agent/role/`.

```
agent/role/
├── default.md     ← App user
├── reviewer.md    ← Reviewer (example)
└── evolver.md     ← Evolver (ordinary role, same structure)
```

Roles are registered in `socialware.py`:

```python
app.role("default", file="agent/role/default.md")
app.role("reviewer", file="agent/role/reviewer.md")
app.role("evolver", file="agent/role/evolver.md")
```

### Format

```markdown
# {Name} Agent

{One-line description}

## Identity

- Role: {name}
- Permissions: {list}

## Responsibilities

1. {responsibility}
```

### Compile Processing

`socialwares deploy` merges `scope/scope.md` + `role/{name}.md` → `.runtime/agents/{name}/SOUL.md` for each role registered in `socialware.py`.

---

## Scope — Where

App capability boundary via `agent/scope/scope.md`.

- **Internal (boundary)**: What the Agent can and cannot do
- **External (declaration)**: Public description for other Agents
- **Participation**: Who can join, minimum members

Registered in `socialware.py`:

```python
app.scope(file="agent/scope/scope.md")
```

### Format

```markdown
# App Name

{Description}

## Capabilities
- {list}

## Boundaries
- {list}

## Connections
- {external apps via /zchat}
```

---

## Commitment — What (Evaluation Standards)

Evaluation standards for flow edges, defined in `socialware.py` using `app.commitment(...)`.

Commitment is an evaluation standard for the edges of the flow graph — it defines what "good" looks like between two role-actions. It is NOT an enforcement mechanism; agents are not forced to comply.

It is NOT:
- Forced execution rules (the agent is not forced to comply)
- API testing or eval metrics (that's eval)
- Skill instructions (that belongs in flow/SKILL.md)
- Automated enforcement hooks

It IS:
- An evaluation standard (like OKR) for agent collaboration
- A condition that SHOULD be met between two actions
- The criteria evolver uses to assess and improve the system

**Important**: Commitment is NOT included in non-evolver roles' SOUL.md. Only the evolver sees commitment standards for evaluation. Other roles operate based on their skills and role definitions.

### Declaration in socialware.py

```python
app.commitment("C1",
    from_=("coder", "submit_code"),
    to=("pm", "review_code"),
    condition="within 24h",
    on_violation=("tech_lead", "escalate"),
)
```

### Compiled Schema

`socialwares deploy` generates `.runtime/commitment.yaml` from `socialware.py`:

```yaml
commitments:
  C1:
    from: { role: coder, action: submit_code }
    to:   { role: pm, action: review_code }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }
```

| Field | Required | Type | Meaning |
|-------|----------|------|---------|
| `from` | yes | `{ role, action }` | Edge start: who did what (trigger) |
| `to` | yes | `{ role, action }` | Edge end: who must do what (responsible party) |
| `condition` | yes | string | Evaluation standard (natural language) |
| `on_violation` | no | `{ role, action }` or null | Suggested escalation path |

- `to.role` = the responsible party
- `from.role` = the triggering party
- `on_violation.role` = the escalation party

### Condition Examples

```python
# Time standard
app.commitment("C1",
    from_=("coder", "submit_code"),
    to=("pm", "review_code"),
    condition="within 24h",
)

# Precondition standard
app.commitment("C2",
    from_=("coder", "submit_code"),
    to=("coder", "merge_code"),
    condition="review_code completed with result approved",
)

# Quality standard (natural language — evolver interprets)
app.commitment("C3",
    from_=("support", "resolve_ticket"),
    to=("support", "close_ticket"),
    condition="customer rates 4+ stars",
)
```

## Flow — How

Actions and state machines. Action content lives in `agent/flow/`, relationships are defined in `socialware.py`.

### Action Registration in socialware.py

```python
# Direct actions
app.action("check_health", role=["default", "reviewer"])
app.action("create_task", role=["default"])

# State machine
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "approved", "closed")
flow.transition("draft", "submit", "submitted", role=["default"])
flow.transition("submitted", "review_task", "approved", role=["reviewer"])
```

### Compiled flow.yaml

`socialwares deploy` generates `.runtime/flow.yaml` from `socialware.py`:

```yaml
flows:
  F1:
    name: task_lifecycle
    resource: task
    states: [draft, submitted, approved, closed]
    transitions:
      - { from: draft, action: submit, to: submitted, role: [default] }

direct_actions:
  - { action: check_health, role: [default, reviewer], description: "Check health" }
```

**Note**: `flow.yaml` is a compile product. Do not edit it directly — edit `socialware.py` instead.

### SKILL.md — Action Content

Each action has a directory with `SKILL.md` (+ optional `scripts/`) in `agent/flow/`:

```
agent/flow/
├── check_health/SKILL.md
├── create_task/SKILL.md
├── review_task/SKILL.md
├── evolve_structure_check/
│   ├── SKILL.md
│   ├── scripts/check_structure.py
│   └── references/
├── evolve_session_diagnose/
│   ├── SKILL.md
│   ├── scripts/diagnose.py
│   └── references/
├── evolve_api_check/
│   ├── SKILL.md
│   ├── scripts/run_eval.py
│   ├── references/
│   └── eval_cases.yaml
├── evolve_improve/
│   ├── SKILL.md
│   ├── scripts/save_report.py
│   └── references/
└── evolve_auto/
    ├── SKILL.md
    ├── scripts/run_auto.py
    ├── references/
    └── conversation_tests/
```

Convention: action name in `socialware.py` = directory name under `agent/flow/`. The compiler automatically locates `agent/flow/{action}/SKILL.md` and reports an error if not found.

### Compile Processing

`socialwares deploy` reads `socialware.py` and symlinks only the actions allowed for each role into `.runtime/agents/{name}/.claude/skills/`.

When flows define state machines, the compiler also injects a workflow summary (states, transitions) into SOUL.md so the agent knows the valid state machine paths.

### DSL Principle

SKILL.md files should not contain hardcoded URLs. The agent discovers endpoints from project configuration (e.g., `src/api.py`). This keeps skills portable across environments.

### Role-Based Skill Allocation

The compiler reads `socialware.py` and only symlinks the actions allowed for each role:

- `default` role → gets `check_health`, `create_task` (as registered)
- `reviewer` role → gets `check_health`, `review_task` (as registered)
- `evolver` role → gets all `evolve_*` skills (as registered)

Evolver uses the exact same skill structure as business roles — there is no special treatment.
