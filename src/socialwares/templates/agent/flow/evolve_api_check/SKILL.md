---
name: evolve_api_check
description: "Run API eval cases against live app and report performance score"
---

# Evaluate Performance

## Quick Start

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_api_check/scripts/run_eval.py \
  --cases agent/flow/evolve_api_check/eval_cases.yaml \
  --base-url <APP_BASE_URL>
```

The `--base-url` reads `APP_PORT` env var (default 8001). Pass `--base-url` to override.

## Trigger

User says "evaluate", "run eval", "check performance", "test the app" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | .runtime/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | .runtime/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

### Script (`scripts/run_eval.py`)
- Loads eval_cases.yaml (HTTP test cases)
- Sends HTTP requests to the live app
- Compares responses against expected values
- Outputs pass/fail per case + overall score as JSON report

### Evolver (You)
- Run the script and collect output
- **Interpret** results — don't just relay pass/fail counts
- For each failure, **map it to a primitive** (see `references/failure-mapping.md`)
- Compare with previous eval scores if available (check `.runtime/data/evolve/reports/eval_*.json`)
- Suggest specific next steps based on failures

## Working Directory

Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

## Flow

1. Run `scripts/run_eval.py` with the eval_cases.yaml file
2. Read results: pass/fail per case, overall score
3. For each failure, identify which primitive is responsible
4. Compare with previous scores if available
5. Report findings and suggest next action

## Usage

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_api_check/scripts/run_eval.py \
  --cases agent/flow/evolve_api_check/eval_cases.yaml \
  --base-url <APP_BASE_URL>
```

The `--base-url` reads `APP_PORT` env var (default 8001). Pass `--base-url` to override.

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

## References

See `references/failure-mapping.md` for failure-to-primitive mapping and examples of good vs bad analysis.

## Notes

- App backend must be running for eval to work
- Each case makes an HTTP request and compares the response
- Score = number of passing cases / total cases
