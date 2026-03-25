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
For each conversation test in conversation_tests/*.yaml:
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
  --tests-dir agent/flow/evolve_auto/conversation_tests \
  --adapter claude
```

## Flow

**Working directory**: Agent runs from .runtime/agents/evolver/.
Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

1. Developer says "run conversation checks" or "auto-test with claude adapter"
2. Evolver runs `scripts/run_auto.py --tests-dir ... --adapter claude`
3. Script loads conversation tests from `conversation_tests/*.yaml`
4. Each test input is sent to the agent via SDK adapter
5. Response traces are checked for expected_skill usage
6. Reports results:
   - Per-case PASS/FAIL
   - Failure analysis with improvement suggestions
   - Overall conversation score
7. Report saved to `.runtime/data/evolve/reports/auto_test_<timestamp>.json`
8. Auto-generated sessions saved to `.runtime/data/evolve/auto_sessions/`

## Prerequisites

- `conversation_tests/` directory must have test YAML files (e.g., `default.yaml`)
- SDK adapter must be configured for the chosen platform
- Role must be deployed to `.runtime/agents/<role>/`

## Notes

- Tests run sequentially to avoid overwhelming the SDK
- Each test case specifies input, expected_skill, and description
- Test files are organized per role: `default.yaml`, `reviewer.yaml`, etc.
- Results are timestamped and saved for trend analysis
- Does NOT modify agent/ primitives — only tests and reports
