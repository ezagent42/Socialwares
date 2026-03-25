---
name: evolve_auto
description: "Automated conversation testing — run agent on test cases via SDK, score results"
---

# Automated Conversation Testing

## Quick Start

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_auto/scripts/run_auto.py --tests-dir agent/flow/evolve_auto/conversation_tests --adapter claude
```

## Trigger

User says "auto-test", "run conversation checks", "automated testing", "test via SDK" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | agent/commitment/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | agent/flow/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

### Script (`scripts/run_auto.py`)
- Loads conversation test cases from `conversation_tests/*.yaml`
- Sends each test input to the agent via SDK adapter
- Collects response traces
- Checks if the expected_skill was used
- Outputs pass/fail per case + overall score

### Evolver (You)
- Run the script and collect output
- For each **failure**, perform root cause analysis:
  1. Read the failed test's expected_skill SKILL.md — is the trigger clear enough?
  2. Read the test input — does it match the trigger patterns?
  3. Check: was a different skill used instead? Was no skill used at all?
  4. Identify the root cause and propose a specific fix
- Map failures to primitives (usually Flow, sometimes Scope or Role)
- Suggest concrete improvements

## Working Directory

Read .workspace_root to find workspace root, then cd there before running scripts.

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
```

## Flow

1. Developer says "run conversation checks" or "auto-test with claude adapter"
2. Run `scripts/run_auto.py --tests-dir ... --adapter claude`
3. Script loads conversation tests from `conversation_tests/*.yaml`
4. Each test input is sent to the agent via SDK adapter
5. Response traces are checked for expected_skill usage
6. For each failure, analyze root cause (see `references/failure-analysis.md`)
7. Report results with analysis and improvement suggestions
8. Report saved to `.runtime/data/evolve/reports/auto_test_<timestamp>.json`
9. Auto-generated sessions saved to `.runtime/data/evolve/auto_sessions/`

## Usage

```bash
WORKSPACE_ROOT=$(cat .workspace_root)
cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_auto/scripts/run_auto.py \
  --tests-dir agent/flow/evolve_auto/conversation_tests \
  --adapter claude
```

## References

See `references/failure-analysis.md` for failure analysis workflow, good/bad trigger examples, and failure pattern table.

## Prerequisites

- `conversation_tests/` directory must have test YAML files (e.g., `default.yaml`)
- SDK adapter must be configured for the chosen platform
- Role must be deployed to `.runtime/agents/<role>/`

## Output

- Console report with per-case PASS/FAIL
- Failure analysis with root cause and improvement suggestions
- Overall conversation score
- JSON report saved to `.runtime/data/evolve/reports/auto_test_<timestamp>.json`
- Auto-generated sessions saved to `.runtime/data/evolve/auto_sessions/`

## Notes

- Tests run sequentially to avoid overwhelming the SDK
- Each test case specifies input, expected_skill, and description
- Test files are organized per role: `default.yaml`, `reviewer.yaml`, etc.
- Results are timestamped and saved for trend analysis
- Does NOT modify agent/ primitives — only tests and reports
