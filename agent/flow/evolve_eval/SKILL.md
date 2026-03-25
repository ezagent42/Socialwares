---
name: evolve_eval
description: "Run API eval cases against live app and report performance score"
---

# Evaluate Performance

## Trigger

User says "evaluate", "run eval", "check performance", "test the app" etc.

## Flow

**Working directory**: Agent runs from .runtime/agents/evolver/.
Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

1. Run `scripts/run_eval.py` with the eval_cases.yaml file
2. Report results: pass/fail per case, overall score
3. Compare with previous scores if available

## Usage

```bash
uv run agent/flow/evolve_eval/scripts/run_eval.py \
  --cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001
```

## eval_cases.yaml

API eval cases — direct HTTP checks for backend endpoints. The file grows with your app through progressive phases:
- P1: basic health check
- P2: add task CRUD cases
- P3: add quality/SLA cases
- P5: add role-based permission cases

Conversation tests have moved to `agent/flow/evolve_auto/conversation_tests/`.

## Output

- Console report with per-case pass/fail and overall score
- JSON report saved to `.runtime/data/evolve/reports/eval_<timestamp>.json`

## Notes

- App backend must be running for eval to work
- Each case makes an HTTP request and compares the response
- Score = number of passing cases / total cases
