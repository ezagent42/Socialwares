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
socialware.py   → defines commitment relationships (source of truth)
socialwares deploy → generates .runtime/commitment.yaml
log_prompt.sh + log_tool.sh → capture all prompts + tool calls
diagnose.py     → matches log events to commitment actions
evolver (LLM)   → judges conditions → fulfillment rate → improvement suggestions
```

Other roles operate based on their SOUL.md (scope + role) and skills. They do not know which of their actions are being evaluated against commitments.

### Declaration in socialware.py

Commitments are defined in `socialware.py` (not in a separate YAML file):

```python
app.commitment("C1",
    from_=("coder", "submit_code"),
    to=("pm", "review_code"),
    condition="within 24h",
    on_violation=("tech_lead", "escalate"),
)

app.commitment("C2",
    from_=("coder", "submit_code"),
    to=("coder", "merge_code"),
    condition="review_code completed with result approved",
)

app.commitment("C3",
    from_=("pm", "create_task"),
    to=("pm", "close_task"),
    condition="within 48h",
    on_violation=("pm", "auto_close"),
)
```

### Compiled Schema

`socialwares deploy` generates `.runtime/commitment.yaml` from `socialware.py`:

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

### Hook Data Capture

`log_prompt.sh` (UserPromptSubmit) and `log_tool.sh` (PreToolUse) hooks capture all user prompts and tool calls to `.runtime/data/prompts/`. The hooks do NOT tag entries with commitment IDs -- they log all interactions uniformly.

The evolver's `diagnose.py` later reads these logs alongside `.runtime/commitment.yaml`, matches events to commitment actions, and computes fulfillment rates. This keeps commitment invisible to the agent while providing data for the evolver to analyze.

### Two-Phase Checking

#### Development Phase (structure check)

Evolver checks consistency between commitment and other primitives, plus flow graph completeness:

```
For each commitment:
  - from.role exists in agent/role/?
  - from.action registered in socialware.py?
  - to.role exists in agent/role/?
  - to.action registered in socialware.py?
  - on_violation.role exists in agent/role/?
  - on_violation.action registered in socialware.py?
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

1. **Declaration** — developer writes commitment in `socialware.py` using `app.commitment(...)`
2. **Compile** — `socialwares deploy` generates `.runtime/commitment.yaml`
3. **Data capture** — log_prompt.sh + log_tool.sh hooks capture all prompts and tool calls to `.runtime/data/prompts/`
4. **Evolver evaluates** — diagnose.py reads logs + `.runtime/commitment.yaml`, matches events to commitments, extracts data; evolver (LLM) judges conditions and computes fulfillment rate
5. **Improvement** — low fulfillment → evolver suggests changes to four primitives

---

## Evolver

Evolver is an ordinary role — it uses the exact same skill structure (`SKILL.md` + `scripts/`) as business roles. The compiler treats evolver identically to any other role.

### Getting Started

```bash
socialwares start --role evolver
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
| Deadline too tight | Commitment | Adjust condition in socialware.py (24h → 48h) |
| Missing capability in scope | Scope | Update scope.md to reflect actual behavior |
| Need new responsible party | Role | Add new role for escalation |

### Auto Mode

```
You: "auto-test with claude adapter"
Evolver: → runs conversation test cases via SDK → scores results
         → analyzes failures (expected_skill, expected_contains, expected_not_contains)
         → proposes improvements to SKILL.md triggers or flow
```

### Adding Custom Evolve Checks

Adding a custom evolve check = adding a normal skill:

1. Create `agent/flow/evolve_xxx/SKILL.md + scripts/`
2. Register in `socialware.py`: `app.action("evolve_xxx", role=["evolver"])`
3. `socialwares deploy`

### Data Sources

| Source | Location | What evolver looks for |
|--------|----------|----------------------|
| Prompt & tool logs | .runtime/data/prompts/*.jsonl | Actions, tool calls, failed actions, missing capabilities |
| SDK sessions | .runtime/data/sessions/*.json | Full conversation traces |
| Eval cases | agent/flow/evolve_api_check/eval_cases.yaml | Performance score trends |
| Commitment standards | .runtime/commitment.yaml (compiled) | Evaluation standards (from/to/condition) |

### Improvement Cycle

```
Run app → hooks capture prompts + tool calls → evolver analyzes
→ diagnose.py extracts commitment-related events from logs
→ evolver judges conditions, computes fulfillment rates
→ map low rates to specific primitives
→ developer modifies socialware.py + agent/ files
→ socialwares deploy → next cycle
```

### Evolver vs Business Roles

| | Business Role (e.g. default) | evolver |
|---|---|---|
| Purpose | Execute business logic | Analyze data, improve agent config |
| Sees commitment | No (not in SOUL.md) | Yes (reads .runtime/commitment.yaml + logs) |
| Data analysis | No | Yes (reads .runtime/data/) |
| Skill structure | agent/flow/xxx/SKILL.md | agent/flow/evolve_xxx/SKILL.md (same structure) |
| Registration | `app.action("xxx", role=["default"])` | `app.action("evolve_xxx", role=["evolver"])` |
| When | Building / using the app | After running, has data |
