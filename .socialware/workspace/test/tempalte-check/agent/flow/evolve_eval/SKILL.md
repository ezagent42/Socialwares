---
name: evolve_eval
description: "Run eval cases against live app and report performance score"
---

# Evaluate Performance

## Trigger

User says "evaluate", "run eval", "check performance", "test the app" etc.

## Flow

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

The eval cases file grows with your app through progressive phases:
- P1: basic health check
- P2: add task CRUD cases
- P3: add quality/SLA cases
- P5: add role-based permission cases

## Notes

- App backend must be running for eval to work
- Each case makes an HTTP request and compares the response
- Score = number of passing cases / total cases
