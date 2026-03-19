# Role — Who

Defines Subagent identity and permissions.

## Structure

Each role has its own subdirectory containing a `SOUL.md`:

```
role/
├── default/
│   └── SOUL.md      ← Agent identity description
├── admin/
│   └── SOUL.md
└── reviewer/
    └── SOUL.md
```

## SOUL.md Contents

Describes the role's:
- Identity and name
- Granted permissions (which actions it can trigger)
- Responsibility description

## deploy.sh Processing

`deploy.sh` generates an independent `$PROJECT_DIR` for each role:
- Merges `scope/SOUL.md` + `role/{name}/SOUL.md` → `.runtime/agents/{name}/SOUL.md`
- Symlinks all skills under `flow/` → `.runtime/agents/{name}/.claude/skills/`
