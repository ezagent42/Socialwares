# Four Primitives

Detailed guide to Role, Scope, Commitment, and Flow.

## Role — Who

Agent identities. Each role is a flat `.md` file in `agent/role/`.

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

Constraints on flow edges defined in `agent/commitment/constraints.yaml`.

Commitment is a constraint on the edges of the flow graph — it defines what must be true between two role-actions.

It is NOT:
- API testing or eval metrics (that's eval)
- Skill instructions (that belongs in flow/SKILL.md)
- Agent behavior rules (that belongs in role .md)

It IS:
- A promise from one role to another (or to itself)
- A condition that must be met between two actions
- Part of the collaboration contract between agents

### Unified Schema

Every commitment has the same four fields:

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
| `condition` | yes | string | What must be true for this edge (natural language) |
| `on_violation` | no | `{ role, action }` or null | What happens if condition is not met |

- `to.role` = the responsible party
- `from.role` = the triggering party
- `on_violation.role` = the escalation party

### Condition Examples

```yaml
# Time constraint
condition: "within 24h"

# Precondition
condition: "review_code completed with result approved"

# Quality (natural language — agent/evolver interprets)
condition: "customer rates 4+ stars"

# Span constraint (from/to can be non-adjacent)
condition: "within 48h"
```

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
├── setup_claude/SKILL.md
├── inspect/SKILL.md
├── evolve_diagnose/
│   ├── SKILL.md
│   └── scripts/diagnose.py
├── evolve_eval/
│   ├── SKILL.md
│   ├── scripts/run_eval.py
│   └── eval_cases.yaml
├── evolve_improve/SKILL.md
└── evolve_auto/
    ├── SKILL.md
    └── scripts/run_loop.py
```

### deploy.sh Processing

Reads flow.yaml → **copies** (not symlinks) only the actions allowed for each role into `.runtime/agents/{name}/.claude/skills/`. This prevents accidental template modification.

### Role-Based Skill Allocation

`deploy.sh` reads `flow.yaml` and only copies actions allowed for each role:

- `default` role → gets `check_health` skill only
- `dev` role → gets `check_health` + `setup_claude` + `inspect` skills
- `evolver` role → gets `check_health` + `inspect` + all evolve_* skills
