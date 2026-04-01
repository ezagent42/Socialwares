---
name: evolve_improve
description: "Propose and apply improvements to the four primitives based on diagnostic evidence"
---

# Improve Agent Configuration

## Quick Start

```bash
# Read all reports first:
ls .runtime/data/evolve/reports/
# Then discuss improvements with the developer in conversation
```

## Trigger

User says "improve", "fix this", "make it better", "apply changes" etc.

## Four Primitives Reference

| Primitive | Location | What it defines |
|-----------|----------|----------------|
| Role | agent/role/*.md | Agent identities + permissions |
| Scope | agent/scope/scope.md | App capability boundaries |
| Commitment | .runtime/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | .runtime/flow.yaml + {action}/SKILL.md | Actions + how to execute |

## What SCRIPT Does vs What EVOLVER (You) Does

There is no script for improve. This is a fully evolver-driven skill.

### Evolver (You)
- Read diagnostic evidence from reports (diagnose, eval, auto-test, check)
- Map each problem to a specific primitive
- Propose specific, evidence-backed changes to the developer
- On approval, make the changes to the primitive files
- Run deploy to recompile
- Suggest re-running eval/auto-test to measure improvement

## Prerequisites

Run `evolve_session_diagnose` and/or `evolve_api_check` and/or `evolve_auto` first to gather evidence.

## Flow

**Working directory**: Read .workspace_root to find workspace root.
Only modify files inside the workspace — NEVER modify template files at the repo root.

1. Review diagnostic reports in `.runtime/data/evolve/reports/diagnose_*.json`
2. Review eval reports in `.runtime/data/evolve/reports/eval_*.json`
3. Review auto-test reports in `.runtime/data/evolve/reports/auto_test_*.json`
4. Review structure check reports in `.runtime/data/evolve/reports/check_*.json`
5. Map each problem to a specific primitive (see table below)
6. Propose specific changes to the developer
7. On approval, make the changes:
   - Edit the relevant files (scope.md, role/*.md, SKILL.md, flow.yaml, commitment.yaml)
   - Run `./agent/deploy.sh` to recompile
   - Optionally re-run eval/auto-test to measure improvement

### Thinking Order: Flow → Commitment → Scope → Role

Always analyze in this order:
1. **Flow** — Is the functionality complete? Missing skills? Backend endpoints needed?
2. **Commitment** — Are constraints properly defined? Need validation/enforcement in backend?
3. **Scope** — Is the scope clear and accurate for what the app can do?
4. **Role** — Do we need new roles for new responsibilities?

### Primitive change → Backend change

Changing a primitive often requires corresponding backend code changes:
- **Flow change** (add skill) → backend must implement the API endpoint (`src/app.py`)
- **Flow change** (add state machine) → backend must implement state transitions
- **Commitment change** (add constraint) → backend may need validation logic
- Always propose both the primitive change AND the backend change together

### Problem-to-primitive mapping

| Problem | Primitive | Action |
|---------|-----------|--------|
| Missing capability | Flow | Create skill + implement backend endpoint |
| High error rate on a skill | Flow | Fix SKILL.md instructions or backend logic |
| Low fulfillment rate | Commitment | Adjust commitment.yaml or add backend enforcement |
| Out-of-scope requests | Scope | Expand scope/scope.md (if app supports it) |
| Permission issues | Role | Add/adjust role/ |
| Missing state transition | Flow | Add to flow.yaml + implement in backend |

## References

See `references/improvement-guide.md` for per-operation improvement examples (add skill, fix skill, adjust commitment, expand scope, add role).

## Saving Improve Report

After applying changes, **always** run the save_report script:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run --no-project agent/flow/evolve_improve/scripts/save_report.py \
  --change '{"primitive":"flow","file":"agent/flow/create_task/SKILL.md","action":"Updated trigger","reason":"40% error rate"}' \
  --based-on diagnose_20250326_120000.json \
  --next-step "Run 'evaluate' to check if score improved"
```

See `references/report-template.md` for full format and multi-change examples.

## Principles

- Always show evidence before proposing changes
- One change at a time — measure impact before making more
- Map every change to a specific primitive
- Developer has final approval on all modifications
- After applying, save an improve report (see above)
- Suggest re-running eval/auto-test to measure improvement
- Never modify template files at repo root — only workspace files
