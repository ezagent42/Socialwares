# Improve — Improvement Guide Reference

## Adding a new skill (Flow)

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

## Fixing a skill (Flow) — Good vs Bad

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

## Adjusting commitment

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
            - Proposal: Update agent/flow/create_task/SKILL.md to include
              the exact JSON body format and error handling

            Want me to apply this change?"
Developer: "yes"
Evolver:   -> edits SKILL.md -> runs deploy.sh
           "Done. Run 'evaluate' to check if the score improved."
```
