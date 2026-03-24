# Commitment — Discussion and Design

> Summary of discussions on what commitment is, its schema, and how it works.

---

## What Commitment Is

Commitment is an evaluation standard for the edges of the flow graph — it defines what "good" looks like between two role-actions. It is NOT an enforcement mechanism; agents are not forced to comply. Only the evolver sees commitment standards for assessment.

It is NOT:
- API testing (that's eval)
- Skill instructions (that belongs in flow/SKILL.md)
- Agent behavior rules (that belongs in role .md)
- Forced execution rules or automated enforcement

It IS:
- An evaluation standard (like OKR) for agent collaboration
- A condition that SHOULD be met between two actions
- The criteria evolver uses to assess and improve the system

### Key Design Decision: Evaluation, Not Enforcement

Commitment is NOT included in non-evolver roles' SOUL.md. If it were, agents would be "forced" to follow it, making it enforcement rather than evaluation. Instead:

- Only the **evolver** sees commitment.yaml in its context
- Other roles operate based on their SOUL.md (scope + role) and skills
- The evolver evaluates whether commitments were met after the fact
- Low fulfillment drives improvement suggestions, not runtime enforcement

## Relationship to Four Primitives

If you view the four primitives as a graph:

```
Role + Action = nodes
Flow          = edges (transitions between nodes)
Scope         = subgraph (boundary of what's inside)
Commitment    = evaluation standards on edges (what "good" looks like for traversal)
```

Commitment evaluates things that a single skill can't express — cross-action, cross-role standards.

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
| `condition` | yes | string | Evaluation standard (natural language) |
| `on_violation` | no | `{ role, action }` or null | Suggested escalation path |

- `to.role` = the responsible party (debtor in T2SO terms)
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
Commitment: role+action → role+action    (inter-role evaluation standards)
```

- Flow defines WHAT transitions exist
- Commitment defines WHAT STANDARDS apply to those transitions
- Shared vocabulary: action names

Commitment does not reference flow states. It doesn't need to — it cares about "who did what → who must do what", not "from which state to which state". State machine mechanics are flow's responsibility.

If the same action appears in multiple flow transitions (e.g., review can trigger from "submitted" or "resubmitted"), commitment applies to ALL of them — it evaluates the role-action pair, not a specific state transition.

## Lifecycle

### 1. Declaration (developer writes commitment.yaml)

Developer defines evaluation standards based on their collaboration requirements.

### 2. Deploy (deploy.sh processes commitment.yaml)

Deploy does three things:
1. Copies `commitment.yaml` to each role's `.runtime/agents/{name}/`
2. Generates `commitment_watch.yaml` per role — lists which actions this role should tag:
   ```yaml
   # .runtime/agents/reviewer/commitment_watch.yaml (auto-generated)
   watch:
     - commitment: C1
       action: review_code
       capture: [timestamp, output, duration]
   ```
3. Does NOT add commitment to non-evolver SOUL.md — only evolver sees commitment

### 3. Data Capture (hooks tag conversation data)

`log_prompt.sh` + `log_tool.sh` hooks read `commitment_watch.yaml`:
- For every action the agent performs, log_prompt.sh / log_tool.sh record it in .runtime/data/prompts/
- When the action matches a commitment_watch entry, the hook **tags** the log entry with the commitment ID and captures extra fields (timestamp, output, duration)
- This tagging is transparent to the agent — it does not know which actions are being watched

### 4. Evolver Evaluates (reads tagged logs + commitment.yaml)

Evolver reads conversation logs and for each commitment:
1. Filters log entries tagged with the commitment ID
2. Checks if `condition` was met (LLM interprets natural language)
3. Computes fulfillment rate = fulfilled / total

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

Evolver reads tagged conversation logs and analyzes fulfillment:

```
For each commitment:
  1. Filter log entries tagged with this commitment ID
  2. Check condition (evolver as LLM interprets natural language)
  3. Calculate fulfillment rate
  4. Report
```

## commitment_watch.yaml — Hook Tagging Mechanism

Deploy generates a `commitment_watch.yaml` per role that tells hooks which actions to tag:

```yaml
# Auto-generated by deploy.sh from commitment.yaml
# Role: reviewer
watch:
  - commitment: C1
    action: review_code
    capture: [timestamp, output, duration]
  - commitment: C3
    action: close_task
    capture: [timestamp]
```

When `log_prompt.sh` / `log_tool.sh` hooks run:
1. Reads the role's `commitment_watch.yaml`
2. If the current action matches a watch entry, adds to the log:
   - `commitment_id`: e.g., "C1"
   - `captured_data`: the fields listed in `capture`
3. If no match, logs normally without commitment tags

This mechanism keeps commitment invisible to the agent while providing structured data for the evolver.

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
Run app → collect prompt & tool data (tagged by hooks) → evolver analyzes
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

Fulfillment rate $c_{ij}(t)$ = fulfilled / total per commitment, computed by evolver from tagged conversation logs.
