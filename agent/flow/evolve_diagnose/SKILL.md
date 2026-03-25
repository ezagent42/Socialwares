---
name: evolve_diagnose
description: "Diagnose issues by analyzing conversation data against commitment standards"
---

# Diagnose Issues

## Trigger

User says "diagnose", "what's wrong", "analyze problems", "check issues" etc.

## Flow

**Working directory**: Agent runs from .runtime/agents/evolver/.
Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

1. Run `scripts/diagnose.py` to scan hook logs and SDK sessions
2. Read the diagnostic report
3. Interpret findings and explain to the developer
4. Suggest which primitive to improve (Role/Scope/Commitment/Flow)

## Usage

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --commitment agent/commitment/commitment.yaml
```

## Data Sources Analyzed

| Source | What it finds | Suggests improving |
|--------|--------------|-------------------|
| prompts/*.jsonl | Hook log entries — actions, tool usage | Flow (add skills) |
| sessions/*.json | SDK session traces — full conversations | Commitment (adjust) |

## How It Works

1. Loads commitment definitions from commitment.yaml
2. Reads hook prompt logs (prompts/*.jsonl) with cursor-based incremental scan
3. Reads SDK session files (sessions/*.json) with cursor-based incremental scan
4. For each commitment, finds from.action and to.action events in the data
5. Computes fulfillment rate (triggered vs fulfilled)
6. Generates report with per-commitment rates and recommendations
7. Updates cursor in evolve/state.yaml for next incremental run

## Output

- Console report with commitment fulfillment rates
- JSON report saved to `.runtime/data/evolve/reports/diagnose_<timestamp>.json`
- Cursor state saved to `.runtime/data/evolve/state.yaml`
- Violations written to `.runtime/data/evolve/violations/current.jsonl`
