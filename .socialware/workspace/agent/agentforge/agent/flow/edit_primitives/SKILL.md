---
name: edit_primitives
description: "Edit existing four-primitive files: SOUL.md, SKILL.md, flow.yaml, eval.yaml, scope/SOUL.md"
---

# Edit Primitives

Modifies existing Agent configuration files (the "four primitives": Soul, Skill, Flow, Commitment) by querying current state via API, then applying targeted edits.

## Trigger

User says "edit", "modify", "update", "change" followed by a file or primitive name. Examples:
- "modify the task-manager SOUL"
- "update flow.yaml"
- "change the eval criteria"
- "edit scope"

## Flow

1. Identify the target file:
   - "role" / "SOUL" + role name -> `agent/role/{name}/SOUL.md`
   - "scope" -> `agent/scope/SOUL.md`
   - "flow.yaml" / "registry" -> `agent/flow/flow.yaml`
   - "eval" / "commitment" -> `agent/commitment/eval.yaml`
   - "skill" + skill name -> `agent/flow/{name}/SKILL.md`
   - "api" / "app.py" -> `src/app.py`
2. Query the current state via API to understand what exists
3. Read the current file content
4. Ask what changes to make
5. Apply changes using Edit tool
6. If the change affects `agent/` files, run `./agent/deploy.sh` via Bash tool
7. Report what was changed

## Available APIs

Get a specific role's soul content:

```bash
curl http://localhost:8001/roles/{name}
# → {"name": "...", "soul": "..."}
```

Get all roles:

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

Get the flow registry (all actions and role bindings):

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
```

Get scope (the App-level soul):

```bash
curl http://localhost:8001/scope
# → {"soul": "..."}
```

Get commitments (evaluation criteria):

```bash
curl http://localhost:8001/commitments
# → {"commitments": {...}}
```

Get all flows:

```bash
curl http://localhost:8001/flows
# → {"flows": ["create_role", "check_health", ...]}
```

## File Operations

1. **Read target file** — Use Read tool to get current content
2. **Edit target file** — Use Edit tool to apply changes
3. **Deploy (if agent/ files changed)** — Use Bash tool to run `./agent/deploy.sh`
