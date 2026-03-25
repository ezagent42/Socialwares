---
name: create_skill
description: "Create a new skill: SKILL.md + API endpoint in src/app.py + register in flow.yaml"
---

# Create Skill

Creates a new skill by generating a SKILL.md file, adding an API endpoint to the backend, and registering the skill in the flow registry.

## Trigger

User says "add a skill", "create skill", "new action", "add capability for ...", etc.

## Flow

1. Ask for skill name (lowercase with underscores, e.g. "create_task")
2. Ask for trigger condition (what the user says to invoke it)
3. Ask for execution steps (what the agent should do)
4. Ask which roles should have access to this skill
5. Query existing flows via API to check for conflicts
6. Create `agent/flow/{skill_name}/SKILL.md` using Write tool
7. Generate API endpoint code in `src/app.py` using Edit tool
8. Register the skill in `agent/flow/flow.yaml` using Edit tool
9. Run `./agent/deploy.sh` via Bash tool
10. Verify creation via API
11. Report what was created

## Available APIs

Query existing flows to check for name conflicts:

```bash
curl http://localhost:8001/flows
# → {"flows": ["create_role", "check_health", ...]}
```

Get the full flow registry with role bindings:

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
```

Query existing roles (to validate role bindings):

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}
```

Verify creation after deploying:

```bash
curl http://localhost:8001/flows
# Should now include the new skill name
```

## File Operations

1. **Create SKILL.md** — Use Write tool to create `agent/flow/{skill_name}/SKILL.md` with frontmatter, trigger, flow, and API sections

2. **Add API endpoint** — Use Edit tool to add a new endpoint to `src/app.py`:

    ```python
    @app.post("/{endpoint}")
    async def skill_handler(data: dict[str, Any]) -> dict[str, Any]:
        """Handler description."""
        return {"status": "ok"}
    ```

3. **Register in flow.yaml** — Use Edit tool to add to `agent/flow/flow.yaml`:

    ```yaml
      - action: {skill_name}
        role: [{role_list}]
        description: "{description}"
    ```

4. **Deploy** — Use Bash tool to run `./agent/deploy.sh`

## Validation

- Skill name must match: `^[a-z][a-z0-9_]*$`
- SKILL.md must have valid YAML frontmatter (name + description)
- flow.yaml must remain valid YAML after editing
- API endpoint must not conflict with existing endpoints
