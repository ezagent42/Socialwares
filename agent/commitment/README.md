# Commitment — What

Defines constraints on flow edges. Commitment is an agent-readable specification that constrains the edges of the flow graph — what must be true between two role-actions.

## Core Concept

Commitment is NOT:
- API testing or eval metrics (that's eval)
- Skill execution instructions (that belongs in flow/SKILL.md)
- Agent behavior rules (that belongs in role .md)

Commitment IS:
- A promise from one role to another (or to itself)
- A condition that must be met between two actions
- Part of the collaboration contract between agents

### Graph Model

```
Role + Action = nodes
Flow          = edges (transitions between nodes)
Scope         = subgraph (boundary of what's inside)
Commitment    = constraints on edges (what must be true for traversal)
```

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

# Quality (natural language — agent/evolver interprets)
condition: "customer rates 4+ stars"

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

## Relationship to Flow

Flow and commitment are at different abstraction levels, connected by action names:

```
Flow:       state → action → state      (state machine internals)
Commitment: role+action → role+action    (inter-role promises)
```

- Flow defines WHAT transitions exist
- Commitment defines WHAT CONDITIONS apply to those transitions
- Shared vocabulary: action names

Commitment does not reference flow states. It constrains the role-action pair, not a specific state transition. If the same action appears in multiple flow transitions, the commitment applies to ALL of them.

## Two-Phase Checking

### Development Phase (structure check)

Evolver checks consistency between commitment and other primitives:

```
For each commitment:
  - from.role exists in agent/role/?
  - from.action exists in flow.yaml?
  - to.role exists in agent/role/?
  - to.action exists in flow.yaml?
  - on_violation.role exists in agent/role/?
  - on_violation.action exists in flow.yaml?
  - gap found → report to developer
```

### Runtime Phase (fulfillment check)

Evolver reads conversation logs and analyzes fulfillment:

```
For each commitment:
  1. Find all from.action events in conversations/
  2. Find corresponding to.action events
  3. Check condition (evolver as LLM interprets natural language)
  4. Calculate fulfillment rate
  5. Report
```

Fulfillment rate = fulfilled / total per commitment.

## Lifecycle

1. **Declaration** — developer writes constraints.yaml
2. **Activation** — when `from.action` occurs in conversation log, the commitment activates
3. **Verification** — check if `to.action` happened and whether `condition` was met
4. **Recording** — each commitment instance is fulfilled or broken, recorded in conversation data
5. **Signal** — evolver computes fulfillment rate for improvement decisions

## deploy.sh Processing

`constraints.yaml` is copied to each role's `.runtime/agents/{name}/constraints.yaml`.

## SessionStart Hook

deploy.sh generates a `check_violations.sh` hook for each role.
On session start, it reads `.runtime/data/violations/*.jsonl` and reports
unresolved violations assigned to the current role.

See [docs/discuss/commitment.md](../../docs/discuss/commitment.md) for full design discussion.
