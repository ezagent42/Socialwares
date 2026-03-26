# Auto Test — Failure Analysis Reference

## Failure Analysis Workflow

### Skill check failure

Script reports:
```
[FAIL] Agent uses create_task skill
  expected skill 'create_task' not found in trace
```

Your analysis:
1. Read `agent/flow/create_task/SKILL.md` — is the trigger clear?
2. Read the test input "create a task: write docs" — does it match the trigger?
3. Check: was a different skill used instead? Was no skill used?
4. Propose fix: "The trigger says 'User says create task, new task'. The test input 'create a task: write docs' should match. Possible issue: agent didn't recognize the pattern. Suggest: expand trigger examples in SKILL.md."

### Content check failure (expected_contains)

Script reports:
```
[FAIL] Agent checks health and reports ok
  missing keywords: ['ok']
```

Your analysis:
1. The agent invoked the right skill, but the reply didn't contain "ok"
2. Read the SKILL.md — does it instruct the agent to include status in the reply?
3. Check: did the API return an error? Did the agent summarize incorrectly?
4. Propose fix: "SKILL.md says 'Return status information' but doesn't specify to include the actual status value. Suggest: add 'Report the status field from the response' to the flow."

### Content check failure (expected_not_contains)

Script reports:
```
[FAIL] Agent creates task with correct title
  unwanted keywords found: ['error']
```

Your analysis:
1. The agent reply contained "error" — likely the API call failed
2. Check: is the backend running? Does the endpoint exist?
3. Check: does the SKILL.md have the correct API endpoint and method?
4. Propose fix: either fix the backend endpoint or update SKILL.md with correct API details

## Good trigger example

```markdown
## Trigger
User says "create task", "new task", "add task", "create a task: <title>" etc.
```

## Bad trigger example

```markdown
## Trigger
User wants to create something.
```

## Failure Pattern Reference

| Failure pattern | Likely cause | Primitive | Fix |
|----------------|-------------|-----------|-----|
| Expected skill not in trace, no skill used | Trigger too narrow | Flow | Expand trigger phrases in SKILL.md |
| Expected skill not in trace, different skill used | Trigger overlap between skills | Flow | Make triggers more specific and distinct |
| Expected skill used but wrong output | SKILL.md instructions unclear | Flow | Clarify the flow/instructions in SKILL.md |
| Missing keywords in reply | SKILL.md doesn't instruct to include key info | Flow | Add explicit output instructions to SKILL.md |
| Unwanted keywords in reply (e.g. "error") | API call failed or wrong endpoint | Flow | Fix SKILL.md API details or backend endpoint |
| Unwanted keywords in reply (e.g. "not found") | Resource doesn't exist or wrong ID format | Flow | Check SKILL.md ID parsing logic |
| Agent refuses to act | Missing capability | Scope | Add capability to scope.md |
| Agent says "not permitted" | Role restriction | Role | Update role permissions |
