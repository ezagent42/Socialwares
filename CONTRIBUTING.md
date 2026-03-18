# Contributing

## Architecture Principles

### API is an Extension of Agent Internals

The FastAPI layer is **not** a primary abstraction. It exists to expose Agent
behavior to the browser. Business logic belongs in `agent_bridge.py` and
eventually in `agent/`.

Rule: before adding a new API endpoint, ask — "Which Agent capability am I
exposing?" If the answer is "none — this is pure CRUD," reconsider whether an
Agent should handle it on behalf of the user instead.

### Thin API Rule (Start Thin, Promote Later)

1. New feature logic starts in `agent_bridge.py`
2. Promote to a dedicated API endpoint only when it needs independent access
   control, caching, or webhook integration
3. Promote to the `agent/` module only after the Agent interface is defined
   (pending GitAgent research)

### RSCF Mapping

| RSCF Primitive | This App's Equivalent |
|---|---|
| **Arena (Scope)** | `Room` — defines task boundaries and workspace path isolation |
| **Flow** | `AgentTask.status` — drives API evolution (open → in_progress → submitted → completed) |
| **Commitment** | `POST /agents/invoke` — the contract: prompt in, result + status transition out |
| **Role** | `agent/Role/` — placeholder, definition pending GitAgent research |

### Multi-Tenant Workspace Isolation

Each Room maps to `.socialweb-workspace/{room.name}/`. All file-system
operations by agents must be scoped to this path.

- `room.name` is validated as `^[a-z0-9-]+$` (no path traversal)
- `workspace_path` is constructed with `os.path.join(WORKSPACE_ROOT, room.name)`
  and verified to start with `WORKSPACE_ROOT`
- Never allow user-supplied paths to escape the workspace boundary

## Package Managers

- **Python**: use `uv` — `pip`/`pip3` are not allowed
- **JavaScript**: use `pnpm` — `npm`/`npx` are not allowed

## Commit Format

```
type(scope): description
```

Scopes: `api`, `app`, `agent`, `docs`
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
