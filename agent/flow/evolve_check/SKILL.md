---
name: evolve_check
description: "Check structural consistency of four primitives — no app needed"
---

# Check Structure

## Quick Start

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_check/scripts/check_structure.py --agent-dir agent
```

## Trigger

User says "check structure", "verify primitives", "consistency check" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | agent/commitment/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | agent/flow/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

### Script (`scripts/check_structure.py`)
- Reads flow.yaml, commitment.yaml, role/*.md, scope.md
- Checks structural references: does every action have a SKILL.md? Does every commitment reference valid roles/actions?
- Outputs a machine-readable JSON report + console summary

### Evolver (You)
- Run the script and collect output
- Read the report and **explain** each issue to the developer in plain language
- Map each gap to the specific primitive that needs fixing
- Prioritize: which gaps are blocking (e.g., missing SKILL.md for an action) vs cosmetic (e.g., unused role file)
- Suggest next steps: "Run evolve_improve to fix these" or "This is fine for now"

## Working Directory

Read .workspace_root to find workspace root:
```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

## Flow

1. Run `scripts/check_structure.py`
2. Read the report
3. Explain results to developer — map each gap to a primitive
4. Suggest next action

## Usage

```bash
uv run agent/flow/evolve_check/scripts/check_structure.py --agent-dir agent
```

## What It Checks

1. Every action in flow.yaml has a SKILL.md directory
2. Every commitment's from/to role exists in role/*.md
3. Every commitment's from/to action exists in flow.yaml
4. Scope capabilities are listed for manual review

## Output

- Console report with structural issues
- JSON report saved to `.runtime/data/evolve/reports/check_<timestamp>.json`

## Reference Examples

### Good report interpretation
Script output:
```
MISSING SKILL: action 'submit_task' in flow.yaml has no agent/flow/submit_task/SKILL.md
ORPHAN ROLE: commitment C1 references role 'reviewer' but no agent/role/reviewer.md exists
```

Your explanation to developer:
"Two structural gaps found:
1. **Flow gap**: `submit_task` is declared in flow.yaml but has no SKILL.md — the agent won't know how to execute it. Fix: create `agent/flow/submit_task/SKILL.md` with trigger + instructions.
2. **Role gap**: Commitment C1 expects a `reviewer` role but `agent/role/reviewer.md` doesn't exist. Fix: create the role file or update the commitment to use an existing role.

Run `evolve_improve` to apply these fixes."

### Bad report interpretation (avoid this)
"There are 2 errors. Please fix them."
(No explanation of what's wrong, no mapping to primitives, no suggested fix.)

## Notes

- Does NOT require app to be running
- Pure file-based check — fast, no network
- Run this first before evaluate or diagnose
