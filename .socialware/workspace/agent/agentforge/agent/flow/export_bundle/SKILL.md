---
name: export_bundle
description: "Export a role and its bound skills as a portable bundle directory"
---

# Export Bundle

Exports a role and all its bound skills into a self-contained bundle directory that can be shared and imported into other projects.

## Trigger

User says "export", "package", "bundle" followed by a role name. Examples:
- "export task-manager"
- "package the reviewer role"
- "bundle admin for sharing"

## Flow

1. Confirm the role name to export
2. Query role bindings via API to find all skills bound to this role
3. Verify `agent/role/{name}/` exists
4. Create the bundle directory structure
5. Copy all relevant files
6. Report: "Exported to {name}.bundle/ — copy this directory to another project and use import_bundle to install."

## Available APIs

Query the flow registry to find all actions bound to the role:

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
# Parse direct_actions to find all actions where role includes the target role name
```

Verify the role exists:

```bash
curl http://localhost:8001/roles/{name}
# → {"name": "...", "soul": "..."}
```

List all roles:

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

## File Operations

1. **Create bundle directory** — Use Bash tool:

    ```bash
    mkdir -p {name}.bundle/role/{name}
    mkdir -p {name}.bundle/flow
    mkdir -p {name}.bundle/commitment
    ```

2. **Copy role SOUL.md** — Use Bash tool:

    ```bash
    cp agent/role/{name}/SOUL.md {name}.bundle/role/{name}/SOUL.md
    ```

3. **Copy bound skills** — For each skill bound to this role, use Bash tool:

    ```bash
    cp -r agent/flow/{skill_name} {name}.bundle/flow/
    ```

4. **Extract flow.yaml entries** — Use Write tool to create `{name}.bundle/flow.yaml` containing only entries for this role

5. **Copy eval entries** — Use Write tool to create `{name}.bundle/commitment/eval.yaml` with relevant entries

## Notes

- Does NOT include `.runtime/` (receiver runs deploy.sh)
- Does NOT include `src/app.py` API code (receiver creates their own endpoints)
- Bundle is self-contained: flow.yaml inside the bundle only references included skills
