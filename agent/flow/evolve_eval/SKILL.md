---
name: evolve_eval
description: "Run API eval cases against live app and report performance score"
---

# Evaluate Performance

## Quick Start

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_eval/scripts/run_eval.py --cases agent/flow/evolve_eval/eval_cases.yaml --base-url http://localhost:8001
```

## Trigger

User says "evaluate", "run eval", "check performance", "test the app" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | agent/commitment/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | agent/flow/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

### Script (`scripts/run_eval.py`)
- Loads eval_cases.yaml (HTTP test cases)
- Sends HTTP requests to the live app
- Compares responses against expected values
- Outputs pass/fail per case + overall score as JSON report

### Evolver (You)
- Run the script and collect output
- **Interpret** results — don't just relay pass/fail counts
- For each failure, **map it to a primitive**:
  - Endpoint returns wrong data? -> Flow (SKILL.md has wrong API instructions)
  - Endpoint returns 403/401? -> Role (permissions misconfigured)
  - Endpoint doesn't exist? -> Scope (capability not implemented) or Flow (action not registered)
  - Response too slow / quality issue? -> Commitment (condition not met)
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

## Reference Examples

### Good failure analysis
Script output:
```
[FAIL] POST /tasks — expected 201, got 500
[FAIL] GET /tasks/1 — expected {"title": "test"}, got 404
[PASS] GET /health — 200 ok
```

Your interpretation:
"Eval score: 1/3 (33%). Two failures, both in task CRUD:
1. **POST /tasks returns 500** — the backend crashes on task creation. This is a **Flow** issue: check `agent/flow/create_task/SKILL.md` for the correct request format, and verify the app's `/tasks` endpoint handler.
2. **GET /tasks/1 returns 404** — likely a consequence of failure #1 (no task was created). Fix #1 first, then re-run eval.

Suggest: run `evolve_diagnose` to check if the create_task skill is being invoked correctly, then `evolve_improve` to fix the SKILL.md."

### Bad failure analysis (avoid this)
"1 out of 3 tests passed. Score is 33%."
(No root cause analysis, no primitive mapping, no next steps.)

## Notes

- App backend must be running for eval to work
- Each case makes an HTTP request and compares the response
- Score = number of passing cases / total cases
