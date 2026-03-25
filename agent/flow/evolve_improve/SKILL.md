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
| Commitment | agent/commitment/commitment.yaml | Evaluation standards on flow edges (from/to/condition) |
| Flow | agent/flow/flow.yaml + {action}/SKILL.md | Actions + how to execute |

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

Run `evolve_diagnose` and/or `evolve_eval` and/or `evolve_auto` first to gather evidence.

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

### Problem-to-primitive mapping

| Problem | Primitive | Action |
|---------|-----------|--------|
| Missing capability | Flow | Create new skill in agent/flow/ |
| High error rate on a skill | Flow | Edit the SKILL.md |
| Constraint violations | Commitment | Adjust commitment.yaml |
| Out-of-scope requests | Scope | Expand scope/scope.md |
| Permission issues | Role | Add/adjust role/ |
| Overall poor performance | Scope | Improve scope/scope.md reasoning |

## References

See `references/improvement-guide.md` for per-operation improvement examples (add skill, fix skill, adjust commitment, expand scope, add role).

## Principles

- Always show evidence before proposing changes
- One change at a time — measure impact before making more
- Map every change to a specific primitive
- Developer has final approval on all modifications
- After applying, suggest re-running eval to measure improvement
- Never modify template files at repo root — only workspace files
