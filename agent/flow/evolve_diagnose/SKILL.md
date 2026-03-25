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

## References

- `references/judgment-examples.md` — how to judge fulfillment for each condition type
- `references/violation-mapping.md` — map violations to four-primitive improvements

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
