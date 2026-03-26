# Commitment and Evolution

## Commitment (Evaluation Standards for Flow Edges)

Commitment is an evaluation standard for the edges of the flow graph — it defines what "good" looks like between two role-actions. It is an agent-readable specification used by the evolver for assessment, not an enforcement mechanism.

### What Commitment IS and IS NOT

| Commitment IS | Commitment IS NOT |
|---|---|
| An evaluation standard (like OKR) | Forced execution rules |
| A condition that SHOULD be met | API testing or eval metrics |
| Criteria for evolver assessment | Skill execution instructions |
| Visible only to evolver | Part of non-evolver SOUL.md |

### Key Design Decision: Evaluation, Not Enforcement

Commitment is NOT included in non-evolver roles' SOUL.md. Only the evolver sees commitment standards:

```
commitment.yaml → defines standards
log_prompt.sh + log_tool.sh → capture all prompts + tool calls
diagnose.py     → matches log events to commitment actions
evolver (LLM)   → judges conditions → fulfillment rate → improvement suggestions
```

Other roles operate based on their SOUL.md (scope + role) and skills. They do not know which of their actions are being evaluated against commitments.

### Unified Schema

Every commitment uses the same four fields in `agent/commitment/commitment.yaml`:

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

### Hook Data Capture

`log_prompt.sh` (UserPromptSubmit) and `log_tool.sh` (PreToolUse) hooks capture all user prompts and tool calls to `.runtime/data/prompts/`. The hooks do NOT tag entries with commitment IDs -- they log all interactions uniformly.

The evolver's `diagnose.py` later reads these logs alongside `commitment.yaml`, matches events to commitment actions, and computes fulfillment rates. This keeps commitment invisible to the agent while providing data for the evolver to analyze.

### Two-Phase Checking

#### Development Phase (structure check)

Evolver checks consistency between commitment and other primitives, plus flow graph completeness:

```
For each commitment:
  - from.role exists in agent/role/?
  - from.action exists in flow.yaml?
  - to.role exists in agent/role/?
  - to.action exists in flow.yaml?
  - on_violation.role exists in agent/role/?
  - on_violation.action exists in flow.yaml?
  - gap found → report to developer

For each flow state machine:
  - All states reachable from initial state?
  - Terminal states exist (no infinite loops)?
  - No isolated states?
```

#### Runtime Phase (fulfillment check)

Evolver reads conversation logs and analyzes fulfillment:

```
For each commitment:
  1. diagnose.py extracts events matching from/to actions from logs
  2. Evolver (LLM) checks condition against extracted events (interprets natural language)
  3. Calculate fulfillment rate
  4. Report
```

Fulfillment rate = fulfilled / total per commitment. This is the primary signal for the evolver's improvement cycle.

### Lifecycle

1. **Declaration** — developer writes commitment.yaml
2. **Deploy** — deploy.sh copies commitment.yaml to each role's `.runtime/agents/{name}/`
3. **Data capture** — log_prompt.sh + log_tool.sh hooks capture all prompts and tool calls to `.runtime/data/prompts/`
4. **Evolver evaluates** — diagnose.py reads logs + commitment.yaml, matches events to commitments, extracts data; evolver (LLM) judges conditions and computes fulfillment rate
5. **Improvement** — low fulfillment → evolver suggests changes to four primitives

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
You: "check structure" → scripts/check_structure.py verifies four primitives + flow graph completeness → report
You: "diagnose"        → scripts/diagnose.py scans runtime data + flow transition events → report
You: "evaluate"        → scripts/run_eval.py runs eval cases → score
You: "improve"         → propose changes based on evidence → apply
```

#### Diagnose

Reads conversations + commitment standards. The diagnose script scans:
- Conversation logs for failed actions and missing capabilities
- Commitment fulfillment by matching log events to commitment actions
- Flow transition events (observed vs declared order) when flows are defined
- Fulfillment rate = fulfilled / total per commitment

#### Eval

`eval_cases.yaml` contains API checks — HTTP endpoint verification.
Conversation tests live in `agent/flow/evolve_auto/conversation_tests/*.yaml`.

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
You: "auto-test with claude adapter"
Evolver: → runs conversation test cases via SDK → scores results
         → analyzes failures (expected_skill, expected_contains, expected_not_contains)
         → proposes improvements to SKILL.md triggers or flow
```

### Data Sources

| Source | Location | What evolver looks for |
|--------|----------|----------------------|
| Prompt & tool logs | .runtime/data/prompts/*.jsonl | Actions, tool calls, failed actions, missing capabilities |
| SDK sessions | .runtime/data/sessions/*.json | Full conversation traces |
| Eval cases | agent/flow/evolve_api_check/eval_cases.yaml | Performance score trends |
| Commitment standards | agent/commitment/commitment.yaml | Evaluation standards (from/to/condition) |

### Improvement Cycle

```
Run app → hooks capture prompts + tool calls → evolver analyzes
→ diagnose.py extracts commitment-related events from logs
→ evolver judges conditions, computes fulfillment rates
→ map low rates to specific primitives
→ developer modifies agent/ files
→ deploy → next cycle
```

### Evolver vs Dev

| | dev | evolver |
|---|---|---|
| Purpose | Set up environment, navigate project | Analyze data, improve agent config |
| Sees commitment | No (not in SOUL.md) | Yes (reads commitment.yaml + conversation logs) |
| Data analysis | No | Yes (reads .runtime/data/) |
| When | Building the app | After running, has data |
