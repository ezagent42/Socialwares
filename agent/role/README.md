# Role — Who

Defines Subagent identities. Each role is a single `.md` file.

## Structure

```
role/
├── README.md
├── default.md    ← App user role
├── dev.md        ← Developer role
└── evolver.md    ← Evolver role
```

## File Format

Each role file follows a consistent template:

```markdown
# {Role Name} Agent

{One-line description}

## Identity

- Role: {name}
- Permissions: {list}

## Responsibilities

{Numbered list of responsibilities}
```

Role files define **identity only** — operational details belong in flow/ skills.

## deploy.sh Processing

For each `role/*.md` file, deploy.sh:
1. Creates `.runtime/agents/{role_name}/`
2. Merges `scope/scope.md` + `role/{name}.md` → `.runtime/agents/{name}/SOUL.md`
3. Symlinks allowed flow/ skills (per flow.yaml)
