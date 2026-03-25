---
name: evolve_improve
description: "Propose and apply improvements to the four primitives based on diagnostic evidence"
---

# Improve Agent Configuration

## Trigger

User says "improve", "fix this", "make it better", "apply changes" etc.

## Prerequisites

Run `evolve_diagnose` and/or `evolve_eval` first to gather evidence.

## Flow

**Working directory**: Read .workspace_root to find workspace root.
Only modify files inside the workspace — NEVER modify template files at the repo root.

1. Review diagnostic reports in `.runtime/data/evolve/reports/diagnose_*.json`
2. Review eval reports in `.runtime/data/evolve/reports/eval_*.json`
3. Review auto-test reports in `.runtime/data/evolve/reports/auto_test_*.json`
4. Review structure check reports in `.runtime/data/evolve/reports/check_*.json`
5. Map each problem to a specific primitive:

   | Problem | Primitive | Action |
   |---------|-----------|--------|
   | Missing capability | Flow | Create new skill in agent/flow/ |
   | High error rate on a skill | Flow | Edit the SKILL.md |
   | Constraint violations | Commitment | Adjust commitment.yaml |
   | Out-of-scope requests | Scope | Expand scope/scope.md |
   | Permission issues | Role | Add/adjust role/ |
   | Overall poor performance | Scope | Improve scope/scope.md reasoning |

6. Propose specific changes to the developer
7. On approval, make the changes:
   - Edit the relevant files (scope.md, role/*.md, SKILL.md, flow.yaml, commitment.yaml)
   - Run `./agent/deploy.sh` to recompile
   - Optionally re-run `evolve_eval` to measure improvement

## Example Conversation

```
Developer: "diagnose" → (runs diagnose, sees high error rate on create_task)
Developer: "improve"
Evolver:   "Based on the diagnosis:
            - create_task skill has 40% error rate
            - The SKILL.md doesn't specify the required request format
            - Proposal: Update agent/flow/create_task/SKILL.md to include
              the exact JSON body format and error handling

            Want me to apply this change?"
Developer: "yes"
Evolver:   → edits SKILL.md → runs deploy.sh
           "Done. Run 'evaluate' to check if the score improved."
```

## Principles

- Always show evidence before proposing changes
- One change at a time — measure impact before making more
- Map every change to a specific primitive
- Developer has final approval on all modifications
- After applying, suggest re-running eval to measure improvement
