---
name: evolve_diagnose
description: "Diagnose issues by analyzing conversation data against commitment standards"
---

# Diagnose Issues

## Quick Start

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_diagnose/scripts/diagnose.py --data-dir .runtime/data --commitment agent/commitment/commitment.yaml
# Then read output + commitment.yaml → judge each condition → report to developer
```

## Trigger

User says "diagnose", "what's wrong", "analyze problems", "check issues" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | agent/commitment/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | agent/flow/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

### Script (`scripts/diagnose.py`)
The script ONLY extracts data. It does NOT judge fulfillment. It:
- Loads commitment definitions from commitment.yaml
- Reads hook prompt logs (prompts/*.jsonl) with cursor-based incremental scan
- Reads SDK session files (sessions/*.json) with cursor-based incremental scan
- For each commitment, finds `from` and `to` action events in the data
- Outputs raw event counts and timestamps
- Updates cursor in evolve/state.yaml for next incremental run

### Evolver (You) — This is the critical part
After running the script, YOU must:
1. **Run the script** -> get extracted events per commitment
2. **Read commitment.yaml** -> understand each commitment's condition (time, quality, sequence, etc.)
3. **Compare events against conditions** -> judge whether each commitment is fulfilled or violated
4. **Write analysis** -> explain each judgment with evidence (timestamps, counts, diffs)
5. **Map violations to primitives** -> suggest which primitive to fix

The script gives you data. You give the developer judgment.

## Working Directory

Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

## Flow

1. Run `scripts/diagnose.py` to extract events from hook logs and SDK sessions
2. Read `agent/commitment/commitment.yaml` to understand each condition
3. For each commitment, compare extracted events against the condition
4. Judge: FULFILLED, VIOLATED, or INSUFFICIENT DATA
5. Write detailed analysis with evidence
6. Suggest which primitive to improve for each violation

## Usage

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --commitment agent/commitment/commitment.yaml
```

## Data Sources Analyzed

| Source | What it finds | Suggests improving |
|--------|--------------|-------------------|
| prompts/*.jsonl | Hook log entries — actions, tool usage | Flow (add skills) |
| sessions/*.json | SDK session traces — full conversations | Commitment (adjust) |

## How to Judge Fulfillment

This is your core responsibility. The script gives you raw events. You must apply the commitment conditions.

### Example: Time condition

```yaml
C1:
  from: { role: default, action: submit_task }
  to: { role: reviewer, action: review_task }
  condition: "within 24h"
```

Script output:
```
from events: 1
  2026-03-25T02:33:39 [default] submit_task
to events: 0
```

Your judgment: "C1 VIOLATED — submit_task happened but review_task never occurred. Reviewer needs to act."

### Example: Sequence condition

```yaml
C2:
  from: { role: default, action: create_task }
  to: { role: default, action: submit_task }
  condition: "within 10 seconds"
```

Script output:
```
from events: 1
  2026-03-25T02:31:43 [default] create_task
to events: 1
  2026-03-25T02:33:39 [default] submit_task
```

Your judgment: "C2 VIOLATED — create_task at 02:31:43, submit_task at 02:33:39, difference = 116 seconds > 10 seconds."

### Example: Both actions happen but condition unclear

```yaml
C3:
  from: { role: pm, action: create_task }
  to: { role: pm, action: close_task }
  condition: "within 48h"
```

Script output:
```
from events: 3
  2026-03-23T10:00:00 [pm] create_task
  2026-03-24T09:00:00 [pm] create_task
  2026-03-25T14:00:00 [pm] create_task
to events: 2
  2026-03-24T08:00:00 [pm] close_task
  2026-03-25T10:00:00 [pm] close_task
```

Your judgment: "C3 PARTIALLY FULFILLED — 3 tasks created, 2 closed. First task (03-23 10:00) closed at 03-24 08:00 (22h, within 48h ✓). Second task (03-24 09:00) closed at 03-25 10:00 (25h, within 48h ✓). Third task (03-25 14:00) not yet closed. Rate: 2/3 = 67%."

### Example: Insufficient data

Script output:
```
from events: 0
to events: 0
```

Your judgment: "C1 INSUFFICIENT DATA — no events found for either action. The workflow hasn't been exercised yet. This is not a violation, but the commitment is untested."

## Mapping Violations to Primitives

| Violation pattern | Likely primitive | Fix |
|-------------------|-----------------|-----|
| `to` action never happens | Flow | Add/fix the SKILL.md for the `to` action |
| `to` action happens but too late | Commitment | Adjust the time condition, or fix the workflow bottleneck |
| Wrong role performs action | Role | Fix role permissions in role/*.md and flow.yaml |
| Action produces wrong output | Flow | Fix the SKILL.md instructions |
| Condition is unrealistic | Commitment | Adjust commitment.yaml to a realistic standard |
| Action not recognized | Scope | Check if capability is declared in scope.md |

## Output

- Console report with commitment fulfillment rates
- JSON report saved to `.runtime/data/evolve/reports/diagnose_<timestamp>.json`
- Cursor state saved to `.runtime/data/evolve/state.yaml`
- Violations written to `.runtime/data/evolve/violations/current.jsonl`

## Notes

- The script extracts. You judge. Do not skip the judgment step.
- Always read commitment.yaml before interpreting script output.
- Be specific: cite timestamps, compute time differences, count events.
- If data is insufficient, say so — don't guess.
