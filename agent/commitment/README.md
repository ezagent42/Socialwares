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
log_prompt.sh + log_tool.sh → capture all prompts + tool calls
diagnose.py     → matches log events to commitment actions
evolver (LLM)   → judges conditions → fulfillment rate → improvement suggestions
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
2. **Deploy** — deploy.sh copies commitment.yaml to each role's `.runtime/agents/{name}/`
3. **Data capture** — log_prompt.sh (UserPromptSubmit) + log_tool.sh (PreToolUse) hooks capture all prompts and tool calls to `.runtime/data/prompts/`
4. **Evolver evaluates** — diagnose.py reads logs + commitment.yaml, matches events to commitment actions; evolver (LLM) judges conditions and computes fulfillment rate
5. **Improvement** — low fulfillment → evolver suggests changes to four primitives

## deploy.sh Processing

1. Copies `commitment.yaml` to each role's `.runtime/agents/{name}/`
2. Copies `flow.yaml` for reference
3. Generates hooks (`log_prompt.sh` + `log_tool.sh`) that capture all prompts and tool calls

Hooks do NOT tag entries with commitment IDs. The evolver's `diagnose.py` later reads these logs alongside commitment.yaml to match events to commitments.

## Evolver Verification

Evolver reads conversation logs and for each commitment:
1. `diagnose.py` extracts events matching `from` and `to` actions from logs
2. Evolver (LLM) checks if `condition` was met (interprets natural language)
3. Computes fulfillment rate = fulfilled / total
4. Low fulfillment → suggests improvements to four primitives

See [docs/discuss/commitment.md](../../docs/discuss/commitment.md) for full design discussion.
