---
name: evolve_auto
description: "Automated conversation testing — run agent on test cases via SDK, score results"
---

# Automated Conversation Testing

## Trigger

User says "auto-test", "run conversation checks", "automated testing", "test via SDK" etc.

## What It Does

Runs automated conversation tests against the agent via SDK adapter:

```
For each conversation_check in eval_cases.yaml:
  1. Send user input to agent via SDK
  2. Collect response trace
  3. Check if expected skill was used
  4. Score pass/fail
```

## Usage

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_auto/scripts/run_auto.py \
  --cases agent/flow/evolve_eval/eval_cases.yaml \
  --adapter claude \
  --role default
```

## Flow

**Working directory**: Agent runs from .runtime/agents/evolver/.
Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

1. Developer says "run conversation checks" or "auto-test with claude adapter"
2. Evolver runs `scripts/run_auto.py --cases ... --adapter claude --role default`
3. Script loads conversation_checks from eval_cases.yaml
4. Each test input is sent to the agent via SDK adapter
5. Response traces are checked for expected_skill usage
6. Reports results:
   - Per-case PASS/FAIL
   - Overall conversation score
7. Results saved to `.runtime/data/auto_tests/`

## Prerequisites

- eval_cases.yaml must have `conversation_checks` entries
- SDK adapter must be configured for the chosen platform
- Role must be deployed to `.runtime/agents/<role>/`

## Notes

- Tests run sequentially to avoid overwhelming the SDK
- Each test case specifies input, expected_skill, and description
- Results are timestamped and saved for trend analysis
- Does NOT modify agent/ primitives — only tests and reports
