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

## Commitment — What (Evaluation Standards)

Evaluation standards for flow edges defined in `agent/commitment/commitment.yaml`.

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

### Deploy and Hook Tagging

Deploy processes commitment.yaml in three steps:
1. Copies `commitment.yaml` to each role's `.runtime/agents/{name}/`
2. Generates `commitment_watch.yaml` per role — lists which actions to tag
3. `log_prompt.sh` + `log_tool.sh` hooks read `commitment_watch.yaml` and tag matching log entries with commitment IDs

```yaml
# .runtime/agents/reviewer/commitment_watch.yaml (auto-generated)
watch:
  - commitment: C1
    action: review_code
    capture: [timestamp, output, duration]
```

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
| `condition` | yes | string | Evaluation standard (natural language) |
| `on_violation` | no | `{ role, action }` or null | Suggested escalation path |

- `to.role` = the responsible party
- `from.role` = the triggering party
- `on_violation.role` = the escalation party

### Condition Examples

```yaml
# Time standard
condition: "within 24h"

# Precondition standard
condition: "review_code completed with result approved"

# Quality standard (natural language — evolver interprets)
condition: "customer rates 4+ stars"

# Span standard (from/to can be non-adjacent)
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

Reads flow.yaml → **symlinks** only the actions allowed for each role into `.runtime/agents/{name}/.claude/skills/`. Symlinks within workspace mean changes to `agent/flow/` are instantly visible. Template→workspace isolation is handled by `create-my-socialware` (copy).

### Role-Based Skill Allocation

`deploy.sh` reads `flow.yaml` and only copies actions allowed for each role:

- `default` role → gets `check_health` skill only
- `dev` role → gets `check_health` + `setup_claude` + `inspect` skills
- `evolver` role → gets `check_health` + `inspect` + all evolve_* skills
