# Check Structure — Report Interpretation Reference

## Good interpretation

Script output:
```
MISSING SKILL: action 'submit_task' in flow.yaml has no agent/flow/submit_task/SKILL.md
ORPHAN ROLE: commitment C1 references role 'reviewer' but no agent/role/reviewer.md exists
```

Your explanation to developer:
"Two structural gaps found:
1. **Flow gap**: `submit_task` is declared in flow.yaml but has no SKILL.md — the agent won't know how to execute it. Fix: create `agent/flow/submit_task/SKILL.md` with trigger + instructions.
2. **Role gap**: Commitment C1 expects a `reviewer` role but `agent/role/reviewer.md` doesn't exist. Fix: create the role file or update the commitment to use an existing role.

Run `evolve_improve` to apply these fixes."

## Bad interpretation

"There are 2 errors. Please fix them."
(No explanation of what's wrong, no mapping to primitives, no suggested fix.)
