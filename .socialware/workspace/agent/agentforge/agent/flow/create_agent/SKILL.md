---
name: create_role
description: "Create a new Agent role with SOUL.md, optional skills, and optional eval commitments"
---

# Create Role

Creates a new Agent role by generating a SOUL.md identity file, registering it in flow.yaml, and deploying the configuration.

## Trigger

User says "create a role", "new agent", "create an agent for ...", "add role", etc.

## Flow

1. Ask for role name (must be lowercase alphanumeric + hyphens, e.g. "task-manager")
2. Ask for a description of what this agent does
3. Query existing roles via API to check for conflicts
4. Create `agent/role/{name}/SOUL.md` with Identity, Responsibilities, Boundaries sections
5. Update `agent/flow/flow.yaml` to bind actions to the new role
6. Optionally invoke create_skill flow for each skill the role needs
7. Optionally add evaluation criteria to `agent/commitment/eval.yaml`
8. Run `./agent/deploy.sh` to compile changes
9. Verify the role was created via API
10. Report: "{name} role created. Start with: `./agent/start.sh --role {name}`"

## Available APIs

Query existing roles before creating (to avoid conflicts):

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

Get details of a specific role:

```bash
curl http://localhost:8001/roles/{name}
# → {"name": "...", "soul": "..."}
```

Check current flow registry to see role bindings:

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
```

Verify creation after deploying:

```bash
curl http://localhost:8001/roles
# Should now include the new role name
```

## File Operations

1. **Create SOUL.md** — Use Write tool to create `agent/role/{name}/SOUL.md`:

    ```markdown
    # {Display Name} Agent

    {Description from user}

    ## Identity

    - Role: {name}
    - Permissions: {inferred from description}

    ## Responsibilities

    {List of responsibilities based on description}
    ```

2. **Register in flow.yaml** — Use Edit tool to add role bindings in `agent/flow/flow.yaml`

3. **Deploy** — Use Bash tool to run `./agent/deploy.sh`

## Validation

- Role name must match: `^[a-z0-9-]+$`
- SOUL.md must not be empty
- Role directory must not already exist (ask user to confirm overwrite if it does)
