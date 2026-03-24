---
name: evolve_auto
description: "Run automated evolution loop — evaluate, propose, generate, evaluate, keep or discard"
---

# Automated Evolution

## Trigger

User says "auto-optimize", "auto-evolve", "run evolution loop", "automatic improvement" etc.

## What It Does

Runs an automated improvement loop (inspired by [EvoSkill](https://github.com/sentient-agi/EvoSkill)):

```
For each iteration:
  1. Evaluate current config (run eval_cases)
  2. Identify failures
  3. Propose improvement (new skill or SOUL.md edit)
  4. Apply change
  5. Re-evaluate
  6. If score improved → keep, else → discard
```

## Usage

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_auto/scripts/run_loop.py \
  --eval-cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001 \
  --iterations 5
```

## Flow

**Working directory**: Agent runs from .runtime/agents/evolver/.
Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

1. Developer says "auto-optimize, run 5 iterations"
2. Evolver runs `scripts/run_loop.py --iterations 5`
3. Loop executes: evaluate → diagnose failures → propose → apply → re-evaluate
4. Reports results:
   - Iterations completed
   - Score change (before → after)
   - What was changed (new skills, SOUL.md edits)
5. Developer reviews and decides:
   - "apply" → keep the changes, run deploy
   - "show diff" → see what changed
   - "discard" → revert to before

## Prerequisites

- App backend must be running
- eval_cases.yaml must have test cases
- Runtime data in .runtime/data/ (conversations, violations) helps diagnosis

## Notes

- Each iteration creates a checkpoint so changes can be reverted
- The loop does NOT modify code (src/) — only agent/ four primitives
- Developer has final say on all changes
- For EvoSkill integration: install with `pip install evoskill` (optional)
