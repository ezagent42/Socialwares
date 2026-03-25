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

## Improvement Reference

### Adding a new skill (Flow)
1. Create `agent/flow/{action}/SKILL.md` with clear trigger + flow
2. Register in `agent/flow/flow.yaml` with correct roles
3. Run `./agent/deploy.sh`

Example good SKILL.md structure:
```markdown
## Trigger
User says "create task", "new task", "add task", "create a task: <title>" etc.

## Flow
1. Parse task title from user input
2. POST /tasks with JSON body {"title": "...", "status": "draft"}
3. Return task ID and confirmation
```

### Fixing a skill (Flow)

**Bad**: vague trigger, no API reference
```markdown
## Trigger
User wants to create something.

## Flow
Create it in the system.
```

**Good**: specific trigger phrases, exact curl command, expected response
```markdown
## Trigger
User says "create task", "new task", "add task", "create a task: <title>" etc.

## Flow
1. Extract task title from user input
2. Call API:
   ```bash
   curl -X POST http://localhost:8001/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "<extracted_title>", "status": "draft"}'
   ```
3. Expected response: 201 with `{"id": <int>, "title": "...", "status": "draft"}`
4. Report: "Task #<id> created: <title>"
```

### Adjusting commitment (Commitment)

**Bad condition** (unmeasurable):
```yaml
C1:
  description: "Should be fast"
  condition: "response should be quick"
```

**Good condition** (specific, verifiable from timestamps):
```yaml
C1:
  description: "Review within 24h of submission"
  on: { flow: F1, from: submitted, action: review }
  type: time
  deadline: 24h
```

### Expanding scope (Scope)
- Add new capabilities to `agent/scope/scope.md` that match what the app can actually do
- Don't declare capabilities that don't have corresponding flow actions
- Every capability in scope should have at least one action in flow.yaml that implements it

### Adding a role (Role)
1. Create `agent/role/{name}.md` with identity + responsibilities
2. Add role to relevant actions in `agent/flow/flow.yaml`
3. If the role has commitments, add them to `agent/commitment/commitment.yaml`
4. Run `./agent/deploy.sh`

## Example Conversation

```
Developer: "diagnose" -> (runs diagnose, sees high error rate on create_task)
Developer: "improve"
Evolver:   "Based on the diagnosis:
            - create_task skill has 40% error rate
            - The SKILL.md doesn't specify the required request format
            - Proposal: Update agent/flow/create_task/SKILL.md to include
              the exact JSON body format and error handling

            Want me to apply this change?"
Developer: "yes"
Evolver:   -> edits SKILL.md -> runs deploy.sh
           "Done. Run 'evaluate' to check if the score improved."
```

## Principles

- Always show evidence before proposing changes
- One change at a time — measure impact before making more
- Map every change to a specific primitive
- Developer has final approval on all modifications
- After applying, suggest re-running eval to measure improvement
- Never modify template files at repo root — only workspace files
