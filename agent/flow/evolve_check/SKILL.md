---
name: evolve_check
description: "Check structural consistency of four primitives — no app needed"
---

# Check Structure

## Trigger

User says "check structure", "verify primitives", "consistency check" etc.

## Working Directory

Read .workspace_root to find workspace root:
```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

## Flow

1. Run `scripts/check_structure.py`
2. Read the report
3. Report gaps to developer

## Usage

```bash
uv run agent/flow/evolve_check/scripts/check_structure.py --agent-dir agent
```

## What It Checks

1. Every action in flow.yaml has a SKILL.md directory
2. Every commitment's from/to role exists in role/*.md
3. Every commitment's from/to action exists in flow.yaml
4. Scope capabilities are listed for manual review

## Notes

- Does NOT require app to be running
- Pure file-based check — fast, no network
- Run this first before evaluate or diagnose
