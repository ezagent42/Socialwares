# Commitment — What

Defines constraints on flow edges. Commitment is an agent-readable specification that constrains the edges of the flow graph — what must be true between two role-actions.

## Core Concept

Commitment is NOT:
- API testing or eval metrics (that's eval)
- Skill execution instructions (that belongs in flow/SKILL.md)
- Agent behavior rules (that belongs in role .md)
- Automated enforcement hooks

Commitment IS:
- A promise from one role to another (or to itself)
- A condition that must be met between two actions
- Part of the collaboration contract between agents
- An agent-readable spec — the agent reads it and follows it

### Example

| Belongs in Skill (node) | Belongs in Commitment (edge) |
|---|---|
| Output format requirements | Time limit between two actions |
| How to execute an action | Precondition for next action |
| What fields to include | Ordering between roles |

## Files

- `constraints.yaml` — constraint definitions using the unified schema

## Unified Schema

Every commitment has the same four fields:

```yaml
commitments:
  C1:
    from: { role: coder, action: submit_code }
    to:   { role: pm, action: review_code }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }
```

### Field Definitions

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

# Span constraint (from/to can be non-adjacent)
condition: "within 48h"
```

### Full Examples

```yaml
commitments:
  # Deadline: submit → review within 24h
  C1:
    from: { role: coder, action: submit_code }
    to:   { role: pm, action: review_code }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }

  # Precondition: can't merge without approved review
  C2:
    from: { role: coder, action: submit_code }
    to:   { role: coder, action: merge_code }
    condition: "review_code completed with result approved"
    on_violation: null

  # Span: task must close within 48h of creation
  C3:
    from: { role: pm, action: create_task }
    to:   { role: pm, action: close_task }
    condition: "within 48h"
    on_violation: { role: pm, action: auto_close }
```

## Lifecycle

1. **Declaration** — developer writes constraints.yaml
2. **Deploy** — deploy.sh copies constraints.yaml to each role's `.runtime/agents/{name}/`
3. **Agent reads** — agent starts with constraints.yaml in its working directory; it knows what commitments exist and is expected to follow them
4. **Agent follows** — during operation, the agent respects commitments (e.g., completes review within 24h) because it has read the spec
5. **Evolver checks** — evolver reads conversation logs, checks if each commitment's condition was actually met, computes fulfillment rate

There is NO automatic enforcement hook. The agent follows commitments because it reads the spec (like an employee following a handbook). The evolver verifies compliance afterwards (like a manager reviewing performance).

## deploy.sh Processing

`constraints.yaml` is copied to each role's `.runtime/agents/{name}/constraints.yaml`.

## Evolver Verification

The evolver reads conversation logs (`.runtime/data/conversations/*.jsonl`) and for each commitment:
1. Finds `from.action` events (trigger)
2. Finds corresponding `to.action` events (fulfillment)
3. Checks if `condition` was met (LLM interprets natural language)
4. Computes fulfillment rate = fulfilled / total
5. Low fulfillment → suggests improvements to four primitives

See [docs/discuss/commitment.md](../../docs/discuss/commitment.md) for full design discussion.
