# Scope — Where

Defines the App's capability boundary and public identity via SOUL.md.

## What Scope Means

Scope serves two purposes:

- **Internal (boundary)**: What the Agent can and cannot do.
  Constrains Agent behavior — operations outside scope should be refused.
- **External (declaration)**: Public description of this App's capabilities.
  Other Agents read this to decide whether to delegate tasks here (via /zchat).

This combines what SwSim called "Arena" (participation boundary: who can enter,
minimum participants) with the Agent's identity declaration.

## Files

- `SOUL.md` — the single source of truth for what this App is and what it can do

## SOUL.md Content

```markdown
# App Name

Short description of the app.

## Capabilities
- What the agent can do (list of operations)

## Boundaries
- What the agent should NOT do
- Participation rules (who can join, minimum members)

## Connections
- Which external Apps this App can delegate to (via /zchat)
```

## deploy.sh Processing

`scope/SOUL.md` is merged with each `role/{name}/SOUL.md`
to generate the complete SOUL.md specific to that role:

```
scope/SOUL.md (app-level: what the app does)
  + role/{name}/SOUL.md (role-level: who this agent is)
  = .runtime/agents/{name}/SOUL.md (combined identity)
```
