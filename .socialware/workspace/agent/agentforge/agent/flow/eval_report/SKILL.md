---
name: eval_report
description: "Generate a summary report of all commitment evaluation results"
---

# Evaluation Report

Generates a human-readable summary report of all commitment evaluation results, including overall pass rate and per-commitment status.

## Trigger

User says "eval report", "show report", "commitment status", "quality report", etc.

## Flow

1. Call the metrics API to get all evaluation data
2. Format as a readable report with:
   - Overall pass rate (e.g. "8/10 commitments passing")
   - Per-commitment status: name, current value, threshold, pass/fail
   - Trend indicators if historical data is available
3. Suggest actions for failing commitments

## Available APIs

Get all evaluation metrics:

```bash
curl http://localhost:8001/metrics
# → {"metrics": [...]}
```

Get defined commitments (for descriptions and thresholds):

```bash
curl http://localhost:8001/commitments
# → {"commitments": {...}}
```

Get current roles (for context on which agents are being evaluated):

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

## File Operations

This skill is read-only and does not modify files. All data is retrieved via APIs.
