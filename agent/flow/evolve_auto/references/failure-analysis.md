# Auto Test — Failure Analysis Reference

## Failure Analysis Workflow

Script reports:
```
[FAIL] Agent uses create_task skill
  Expected skill 'create_task' not found in trace
```

Your analysis:
1. Read `agent/flow/create_task/SKILL.md` — is the trigger clear?
2. Read the test input "create a task: write docs" — does it match the trigger?
3. Check: was a different skill used instead? Was no skill used?
4. Propose fix: "The trigger says 'User says create task, new task'. The test input 'create a task: write docs' should match. Possible issue: agent didn't recognize the pattern. Suggest: expand trigger examples in SKILL.md."

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
| Agent refuses to act | Missing capability | Scope | Add capability to scope.md |
| Agent says "not permitted" | Role restriction | Role | Update role permissions |
