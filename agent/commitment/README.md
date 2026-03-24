# Commitment — What

Defines evaluation standards for flow edges. Commitment is an agent-readable specification that defines what "good" looks like between two role-actions — an evaluation standard, not an enforcement mechanism.

## Core Concept

Commitment is NOT:
- Forced execution rules (the agent is not forced to comply)
- API testing (that's eval)
- Skill instructions (that belongs in flow/SKILL.md)
- Automated enforcement hooks

Commitment IS:
- An evaluation standard (like OKR) for agent collaboration
- A condition that SHOULD be met between two actions
- The criteria evolver uses to assess and improve the system

### How It Works

```
commitment.yaml → defines standards
log_prompt.sh + log_tool.sh → capture data (tagged with commitment IDs)
evolver         → compares data vs standards → fulfillment rate → improvement suggestions
```

The agent is NOT given commitment in its SOUL.md (that would make it enforcement). Only the evolver sees commitment standards for evaluation.

## Files

- `commitment.yaml` — evaluation standards using the unified schema

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
| `condition` | yes | string | Evaluation standard (natural language) |
| `on_violation` | no | `{ role, action }` or null | Suggested escalation path |

### Full Examples

```yaml
commitments:
  # Deadline standard
  C1:
    from: { role: coder, action: submit_code }
    to:   { role: pm, action: review_code }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }

  # Precondition standard
  C2:
    from: { role: coder, action: submit_code }
    to:   { role: coder, action: merge_code }
    condition: "review_code completed with result approved"
    on_violation: null

  # Span standard
  C3:
    from: { role: pm, action: create_task }
    to:   { role: pm, action: close_task }
    condition: "within 48h"
    on_violation: { role: pm, action: auto_close }
```

## Lifecycle

1. **Declaration** — developer writes commitment.yaml
2. **Deploy** — deploy.sh:
   - Copies commitment.yaml to each role's .runtime/
   - Generates `commitment_watch.yaml` per role (lists which actions to tag)
   - Hooks use commitment_watch.yaml to tag relevant log entries
3. **Data capture** — log_prompt.sh + log_tool.sh hooks capture interaction data to .runtime/data/prompts/; for actions listed in commitment_watch.yaml, adds commitment tags and extra fields (output, duration)
4. **Evolver evaluates** — evolver reads tagged conversation logs + commitment.yaml → checks if conditions were met → computes fulfillment rate
5. **Improvement** — low fulfillment → evolver suggests changes to four primitives

## deploy.sh Processing

1. Copies `commitment.yaml` to each role's `.runtime/agents/{name}/`
2. Generates `commitment_watch.yaml` per role — lists actions this role should tag:
   ```yaml
   # .runtime/agents/reviewer/commitment_watch.yaml (auto-generated)
   watch:
     - commitment: C1
       action: review_code
       capture: [timestamp, output, duration]
   ```
3. `log_prompt.sh` + `log_tool.sh` hooks read `commitment_watch.yaml` — when a matching action is seen, the log entry is tagged with commitment ID and extra data is captured

## Evolver Verification

Evolver reads conversation logs and for each commitment:
1. Filters log entries tagged with the commitment ID
2. Checks if `condition` was met (LLM interprets natural language)
3. Computes fulfillment rate = fulfilled / total
4. Low fulfillment → suggests improvements to four primitives

See [docs/discuss/commitment.md](../../docs/discuss/commitment.md) for full design discussion.
