---
name: evaluate
description: "Run commitment evaluations and check if Agent meets defined standards"
---

# Evaluate Commitments

Runs all commitment evaluations against the current Agent configuration and reports whether each commitment passes or fails its defined threshold.

## Trigger

User says "evaluate", "check metrics", "run eval", "how is the agent doing", etc.

## Flow

1. Call the eval API to run all evaluations
2. Call the metrics API to get results
3. Display results: commitment description, current value, threshold, pass/fail
4. If any commitment fails, suggest improvements

## Available APIs

Run all evaluations:

```bash
curl -X POST http://localhost:8001/eval \
  -H "Content-Type: application/json" \
  -d '{"commitment_id": "all"}'
# → {"results": [...]}
```

Get evaluation metrics:

```bash
curl http://localhost:8001/metrics
# → {"metrics": [...]}
```

Get defined commitments (to understand what is being evaluated):

```bash
curl http://localhost:8001/commitments
# → {"commitments": {...}}
```

## File Operations

This skill is read-only and does not modify files. All data is retrieved via APIs.
