---
name: import_bundle
description: "Import a role bundle into the current project with conflict detection"
---

# Import Bundle

Imports a role bundle directory into the current project, detecting conflicts with existing roles and skills, and merging configuration files.

## Trigger

User says "import", "install bundle", "add bundle from" followed by a path. Examples:
- "import /path/to/task-manager.bundle"
- "install the reviewer bundle"

## Flow

1. Confirm the bundle path
2. Read the bundle directory structure
3. Query existing roles and flows via API to detect conflicts
4. Validate bundle contents (must have `role/{name}/SOUL.md`)
5. If conflicts found, ask user for each: Overwrite, Skip, or Rename
6. Copy files into the project
7. Merge flow.yaml entries
8. Run `./agent/deploy.sh` via Bash tool
9. Verify import via API
10. Report: "{name} imported. {n} skills added. Deploy complete."

## Available APIs

Query existing roles to detect conflicts:

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

Query existing flows to detect conflicts:

```bash
curl http://localhost:8001/flows
# → {"flows": ["create_role", "check_health", ...]}
```

Get the flow registry for detailed role bindings:

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
```

Verify import after deploying:

```bash
curl http://localhost:8001/roles
curl http://localhost:8001/flows
```

## File Operations

1. **Copy role files** — Use Bash tool:

    ```bash
    mkdir -p agent/role/{name}
    cp bundle/role/{name}/SOUL.md agent/role/{name}/SOUL.md
    ```

2. **Copy skill files** — For each skill in the bundle, use Bash tool:

    ```bash
    mkdir -p agent/flow/{skill_name}
    cp bundle/flow/{skill_name}/SKILL.md agent/flow/{skill_name}/SKILL.md
    ```

3. **Merge flow.yaml** — Use Edit tool to add bundle's action entries into `agent/flow/flow.yaml`

4. **Merge eval.yaml** — Use Edit tool to add bundle's commitment entries into `agent/commitment/eval.yaml`

5. **Deploy** — Use Bash tool to run `./agent/deploy.sh`

## Validation

- Bundle must contain at least `role/{name}/SOUL.md`
- All skill names in bundle flow.yaml must have corresponding SKILL.md directories
- After merge, flow.yaml must remain valid YAML
