# Flow — How

Defines operations the Agent can execute (Skills).

## Structure

Each operation has its own subdirectory containing a `SKILL.md`:

```
flow/
├── check_health/
│   └── SKILL.md
├── create_task/
│   ├── SKILL.md
│   └── scripts/       ← Optional: helper scripts
└── review_task/
    └── SKILL.md
```

## SKILL.md Format

```yaml
---
name: action_name
description: "Operation description"
---
```

Followed by Markdown content describing:
- Trigger conditions (what the user says to trigger it)
- Execution flow (steps)
- API calls (curl examples)
- Permission requirements

## deploy.sh Processing

Each skill directory under `flow/` is symlinked to
`.runtime/agents/{role}/.claude/skills/{skill_name}/`.

## Notes

- State machines are managed by the App (`src/`), not defined in flow/
- Permissions are checked by the App API; permission notes in flow/ are for Agent reference only
