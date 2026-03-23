# Four Primitives

Detailed guide to Role, Scope, Commitment, and Flow.

## Role — Who

Agent identities. Each role is a `.md` file in `agent/role/`.

```
agent/role/
├── default.md     ← App user
├── dev.md         ← Developer
└── evolver.md     ← Evolver
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

### deploy.sh Processing

For each `role/*.md`, deploy.sh merges `scope/scope.md` + `role/{name}.md` → `.runtime/agents/{name}/SOUL.md`

---

## Scope — Where

App capability boundary via `agent/scope/scope.md`.

- **Internal (boundary)**: What the Agent can and cannot do
- **External (declaration)**: Public description for other Agents
- **Participation**: Who can join, minimum members

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

## Commitment — What (Constraints)

Constraints bind to flow edges in `agent/commitment/constraints.yaml`.

### Constraint Types

| Type | Constrains | Example |
|------|-----------|---------|
| `time` | Transition deadline | "Review within 72h" |
| `quality` | Action output standard | "Must include justification" |
| `certainty` | State must not get stuck | "Must leave 'pending' within 48h" |
| `postcondition` | Action result | "Health returns ok" |

### Format

```yaml
transition_constraints:
  C1:
    description: "Review within 72h"
    on: { flow: F1, from: submitted, action: review }
    type: time
    deadline: 72h
    on_violation:
      trigger_action: force_resolve
      trigger_role: admin

action_constraints:
  C1:
    description: "Health check returns ok"
    on: { action: check_health }
    type: postcondition
    expected: '{"status": "ok"}'
```

### Violation Lifecycle

1. App backend detects violation → writes to `.runtime/data/violations/current.jsonl`
2. SessionStart hook notifies the responsible role
3. Role handles it (e.g., admin force_resolves)

Detection is the app developer's responsibility. See [agent/commitment/README.md](../../agent/commitment/README.md) for implementation guide.

---

## Flow — How

Actions and state machines in `agent/flow/`.

### flow.yaml — Action Registry

```yaml
# State machine transitions
flows:
  F1:
    name: task_lifecycle
    states: [draft, submitted, approved, closed]
    transitions:
      - { from: draft, action: submit, to: submitted, role: [default] }

# Direct actions (no state machine)
direct_actions:
  - { action: check_health, role: [default, dev, evolver], description: "Check health" }
```

### SKILL.md — Action Definition

Each action has a directory with `SKILL.md` (+ optional `scripts/`):

```
agent/flow/
├── flow.yaml
├── check_health/SKILL.md
├── create_task/
│   ├── SKILL.md
│   └── scripts/
└── evolve_diagnose/
    ├── SKILL.md
    └── scripts/diagnose.py
```

### deploy.sh Processing

Reads flow.yaml → symlinks only the actions allowed for each role.
