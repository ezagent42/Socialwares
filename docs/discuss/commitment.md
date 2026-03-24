# Commitment — Discussion and Design

> Summary of discussions on what commitment is, its schema, and how it works.

---

## What Commitment Is

Commitment is a constraint on the edges of the flow graph — it defines what must be true between two role-actions.

It is NOT:
- API testing (that's eval)
- Skill instructions (that belongs in flow/SKILL.md)
- Agent behavior rules (that belongs in role .md)

It IS:
- A promise from one role to another (or to itself)
- A condition that must be met between two actions
- Part of the collaboration contract between agents

## Relationship to Four Primitives

If you view the four primitives as a graph:

```
Role + Action = nodes
Flow          = edges (transitions between nodes)
Scope         = subgraph (boundary of what's inside)
Commitment    = constraints on edges (what must be true for traversal)
```

Commitment constrains things that a single skill can't express — cross-action, cross-role constraints.

| Belongs in Skill (node) | Belongs in Commitment (edge) |
|---|---|
| Output format requirements | Time limit between two actions |
| How to execute an action | Precondition for next action |
| What fields to include | Ordering between roles |

## Schema

Unified — every commitment has the same 4 fields:

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
| `condition` | yes | string | What must be true for this edge |
| `on_violation` | no | `{ role, action }` or null | What happens if condition is not met |

- `to.role` = the responsible party (debtor in T2SO terms)
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

Commitment does not reference flow states. It doesn't need to — it cares about "who did what → who must do what", not "from which state to which state". State machine mechanics are flow's responsibility.

If the same action appears in multiple flow transitions (e.g., review can trigger from "submitted" or "resubmitted"), commitment applies to ALL of them — it constrains the role-action pair, not a specific state transition.

## Lifecycle

### 1. Declaration (developer writes constraints.yaml)

Developer defines commitments based on their collaboration requirements.

### 2. Activation (runtime)

When `from.action` occurs (appears in conversation log), the commitment activates.

### 3. Verification (runtime or evolver)

Check if `to.action` happened and whether `condition` was met.

### 4. Recording (conversation log)

Each commitment instance is fulfilled or broken, recorded in conversation data.

### 5. Signal (evolver analysis)

Fulfillment rate = fulfilled / total. This is the T2SO $c_{ij}(t)$ signal.

## Two-Phase Checking

### Development Phase (structure check)

Evolver checks consistency between commitment and other primitives:

```
For each commitment:
  ✓ from.role exists in agent/role/?
  ✓ from.action exists in flow.yaml?
  ✓ to.role exists in agent/role/?
  ✓ to.action exists in flow.yaml?
  ✓ on_violation.role exists in agent/role/?
  ✓ on_violation.action exists in flow.yaml?
  ✗ gap found → report to developer
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

## Improvement Cycle

After checking, evolver maps results to four-primitive improvements:

| Finding | Primitive to Improve | Example |
|---------|---------------------|---------|
| Low fulfillment rate | Flow | Add reminder skill, improve existing skill |
| on_violation never triggered | Flow + Role | Implement escalation logic, verify role exists |
| Deadline too tight | Commitment | Adjust condition (24h → 48h) |
| Missing capability in scope | Scope | Update scope.md to reflect actual behavior |
| Need new responsible party | Role | Add new role for escalation |

Cycle:
```
Run app → collect conversation data → evolver analyzes
→ fulfillment rates per commitment
→ map low rates to specific primitives
→ developer modifies agent/ files
→ deploy → next cycle
```

## Progressive Growth Alignment (dev-guide P1→P5)

| Phase | What happens with Commitment |
|-------|------------------------------|
| P1 | Empty — no multi-step flow yet |
| P2 | Still empty — adding skills, single role |
| P3 | First commitments appear — multi-role collaboration starts |
| P4 | Scope expands — may need new commitments for new capabilities |
| P5 | New roles — commitments reference new roles, on_violation paths expand |

## T2SO Correspondence

Our schema maps to T2SO's Commitment definition:

| T2SO | Our Schema |
|------|-----------|
| promisor (AgentID) | `to.role` (responsible party) |
| promisee (AgentID) | `from.role` (triggering party) |
| role (Role) | `to.role` |
| flow (Flow) | `from.action` + `to.action` (references flow actions) |
| deadline (Timestamp) | `condition` (e.g., "within 24h") |
| outcome (Verifiable) | `condition` (natural language, evolver verifies) |

Fulfillment rate $c_{ij}(t)$ = fulfilled / total per commitment, computed by evolver from conversation logs.
