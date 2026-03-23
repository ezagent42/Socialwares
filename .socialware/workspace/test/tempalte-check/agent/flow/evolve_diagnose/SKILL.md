---
name: evolve_diagnose
description: "Diagnose issues by analyzing runtime data — conversations, violations, constraints"
---

# Diagnose Issues

## Trigger

User says "diagnose", "what's wrong", "analyze problems", "check issues" etc.

## Flow

1. Run `scripts/diagnose.py` to scan all runtime data sources
2. Read the diagnostic report
3. Interpret findings and explain to the developer
4. Suggest which primitive to improve (Role/Scope/Commitment/Flow)

## Usage

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --constraints agent/commitment/constraints.yaml
```

## Data Sources Analyzed

| Source | What it finds | Suggests improving |
|--------|--------------|-------------------|
| conversations/*.jsonl | Failed actions, "can't do" responses | Flow (add skills) |
| violations/*.jsonl | Constraint violations, frequency | Commitment (adjust) |
| conversations/*.jsonl | Out-of-scope requests | Scope (expand) |
| conversations/*.jsonl | Permission denials | Role (add/adjust) |
| API errors in conversations | 500/404 errors | Flow (fix skills) |
