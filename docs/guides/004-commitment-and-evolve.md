# Commitment and Evolution

## Commitment (Constraints on Flow Edges)

Commitment is a constraint on the edges of the flow graph — it defines what must be true between two role-actions. It is an agent-readable specification, not app code that developers implement.

### What Commitment IS and IS NOT

| Commitment IS | Commitment IS NOT |
|---|---|
| A promise from one role to another | API testing or eval metrics |
| A condition between two actions | Skill execution instructions |
| Part of the collaboration contract | Agent behavior rules |
| Agent-readable specification | App developer implementation code |

### Unified Schema

Every commitment uses the same four fields in `agent/commitment/constraints.yaml`:

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
| `condition` | yes | string | What must be true (natural language) |
| `on_violation` | no | `{ role, action }` or null | What happens if condition not met |

### Examples

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

### Two-Phase Checking

#### Development Phase (structure check)

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

#### Runtime Phase (fulfillment check)

Evolver reads conversation logs and analyzes fulfillment:

```
For each commitment:
  1. Find all from.action events in conversations/
  2. Find corresponding to.action events
  3. Check condition (evolver as LLM interprets natural language)
  4. Calculate fulfillment rate
  5. Report
```

Fulfillment rate = fulfilled / total per commitment. This is the primary signal for the evolver's improvement cycle.

### Lifecycle

1. **Declaration** — developer writes constraints.yaml
2. **Activation** — when `from.action` occurs in conversation log, the commitment activates
3. **Verification** — check if `to.action` happened and whether `condition` was met
4. **Recording** — each commitment instance is fulfilled or broken, recorded in conversation data
5. **Signal** — evolver computes fulfillment rate for improvement decisions

See [docs/discuss/commitment.md](../discuss/commitment.md) for full design discussion.

---

## Evolver

Built-in role for improving your app based on runtime evidence.

### Getting Started

```bash
# From within a workspace:
make start ROLE=evolver
```

### Manual Mode

```
You: "diagnose"        → scripts/diagnose.py scans runtime data → report
You: "evaluate"        → scripts/run_eval.py runs eval cases → score
You: "improve"         → propose changes based on evidence → apply
```

#### Diagnose

Reads conversations + constraints. The diagnose script scans:
- Conversation logs for failed actions and missing capabilities
- Constraint violations and their patterns
- Fulfillment rate = fulfilled / total per commitment

#### Eval

Two sections in `eval_cases.yaml`:
- `api_checks` — HTTP endpoint verification
- `conversation_checks` — conversation-based behavior verification

#### Improve

Maps findings to four-primitive improvements:

| Finding | Primitive to Improve | Example |
|---------|---------------------|---------|
| Low fulfillment rate | Flow | Add reminder skill, improve existing skill |
| on_violation never triggered | Flow + Role | Implement escalation logic, verify role exists |
| Deadline too tight | Commitment | Adjust condition (24h → 48h) |
| Missing capability in scope | Scope | Update scope.md to reflect actual behavior |
| Need new responsible party | Role | Add new role for escalation |

### Auto Mode

```
You: "auto-optimize, run 5 iterations"
Evolver: → evaluate → diagnose → propose → apply → re-evaluate
         → reports results, you decide whether to apply
```

### Data Sources

| Source | Location | What evolver looks for |
|--------|----------|----------------------|
| Conversation logs | .runtime/data/conversations/*.jsonl | Failed actions, missing capabilities |
| Violation queue | .runtime/data/violations/*.jsonl | Constraint violation patterns |
| Eval cases | agent/flow/evolve_eval/eval_cases.yaml | Performance score trends |
| Constraints | agent/commitment/constraints.yaml | Active constraint summary |

### Improvement Cycle

```
Run app → collect conversation data → evolver analyzes
→ fulfillment rates per commitment
→ map low rates to specific primitives
→ developer modifies agent/ files
→ deploy → next cycle
```

### Evolver vs Dev

| | dev | evolver |
|---|---|---|
| Purpose | Set up environment, navigate project | Analyze data, improve agent config |
| Data analysis | No | Yes (reads .runtime/data/) |
| When | Building the app | After running, has data |
