# Improve — Improvement Guide Reference

## Thinking Order

Always work through improvements in this order:
1. **Flow** — Is the functionality complete? (add skills, fix skills, add state machine transitions)
2. **Commitment** — Are constraints well-defined? (adjust conditions, add on_violation)
3. **Scope** — Is scope accurate? (match scope.md to actual capabilities)
4. **Role** — Are roles sufficient? (add roles for new responsibilities)

## Primitive + Backend: Always Together

Changing a primitive often requires corresponding backend changes. Always propose both:

| Primitive change | Backend change needed |
|-----------------|----------------------|
| Add new skill (Flow) | Implement API endpoint in `src/app.py` |
| Add state machine (Flow) | Implement state transitions + validation |
| Add commitment constraint | May need validation/enforcement logic |
| Expand scope | Ensure backend actually supports the capability |

## Adding a new skill (Flow)

1. **Backend**: implement the API endpoint in `src/app.py`
2. **Primitive**: create `agent/flow/{action}/SKILL.md` with clear trigger + flow
3. Register in `agent/flow/flow.yaml` with correct roles
4. Run `./agent/deploy.sh`

Example good SKILL.md structure:
```markdown
## Trigger
User says "create task", "new task", "add task", "create a task: <title>" etc.

## Flow
1. Parse task title from user input
2. POST /tasks with JSON body {"title": "...", "status": "draft"}
3. Return task ID and confirmation
```

## Fixing a skill (Flow) — Good vs Bad

**Bad**: vague trigger, no API reference
```markdown
## Trigger
User wants to create something.

## Flow
Create it in the system.
```

**Good**: specific trigger phrases, endpoint notation, expected response
```markdown
## Trigger
User says "create task", "new task", "add task", "create a task: <title>" etc.

## Flow
1. Extract task title from user input
2. Call API: POST /tasks with JSON body {"title": "<extracted_title>", "status": "draft"}
3. Expected response: 201 with {"id": <int>, "title": "...", "status": "draft"}
4. Report: "Task #<id> created: <title>"
```

Note: SKILL.md should use endpoint notation (e.g. `POST /tasks`), not hardcoded URLs. The agent discovers the app's base URL from project configuration.

## Adjusting commitment

**Bad condition** (unmeasurable):
```yaml
C1:
  from: { role: coder, action: submit_code }
  to: { role: pm, action: review_code }
  condition: "response should be quick"
```

**Good condition** (specific, verifiable from timestamps):
```yaml
C1:
  from: { role: coder, action: submit_code }
  to: { role: pm, action: review_code }
  condition: "within 24h"
  on_violation: { role: tech_lead, action: escalate }
```

Remember: commitment changes may need backend support. If adding a time-based constraint, ensure the backend records timestamps. If adding a precondition, ensure the backend can enforce it.

## Expanding scope

- Add new capabilities to `agent/scope/scope.md` that match what the app can actually do
- Don't declare capabilities that don't have corresponding flow actions
- Every capability in scope should have at least one action in flow.yaml that implements it

## Adding a role

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
            - Proposal:
              1. Update agent/flow/create_task/SKILL.md to include
                 the exact JSON body format and error handling
              2. Verify src/app.py POST /tasks endpoint accepts this format

            Want me to apply this change?"
Developer: "yes"
Evolver:   -> edits SKILL.md -> verifies backend -> runs deploy.sh
           "Done. Run 'evaluate' to check if the score improved."
```
