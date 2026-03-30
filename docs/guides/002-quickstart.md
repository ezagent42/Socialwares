# Quickstart

Create and run a Socialware App in 5 minutes.

## Prerequisites

- Python >= 3.12, [uv](https://docs.astral.sh/uv/), Git
- [Claude Code](https://claude.ai/code) (or Codex / Kimi Code)

## Step 1: Install the Framework

```bash
pip install socialwares
# or
uv pip install socialwares
```

## Step 2: Create Your App

```bash
socialwares new task-manager
cd task-manager
```

This generates a project with `socialware.py`, `agent/` content files, `src/`, and `pyproject.toml`.

## Step 3: Install Dependencies

```bash
uv sync    # install project dependencies (socialwares + fastapi + etc.)
```

## Step 4: Deploy and Start the Agent

```bash
socialwares deploy                   # compile socialware.py + agent/ → .runtime/
socialwares start --role default     # launch agent as default role
```

Try: "check health" — the agent runs the check_health skill.

## Step 5: Develop

```bash
# Edit content files
vim agent/scope/scope.md           # app capabilities
vim agent/role/default.md          # agent identity

# Add a skill
mkdir agent/flow/create_task
vim agent/flow/create_task/SKILL.md

# Register action in socialware.py
vim socialware.py
# Add: app.action("create_task", role=["default"])

# Redeploy and start
socialwares deploy
socialwares start --role default
```

## Step 6: Define Relationships in socialware.py

```python
from socialwares import App

app = App("task-manager", description="Task Manager")

# Content references
app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("evolver", file="agent/role/evolver.md")

# Action → role mapping
app.action("check_health", role=["default"])
app.action("create_task", role=["default"])

# Evolve skills (same registration as business skills)
app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

# State machine (optional)
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])

# Commitment (optional)
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("default", "close_task"),
    condition="within 48h",
)
```

## Step 7: Use Different Adapters

```bash
socialwares start --role default --adapter claude       # default
socialwares start --role default --adapter codex
socialwares start --role default --adapter kimicode
```

## Step 8: Multiple Roles

```bash
socialwares start --role default,evolver    # tmux panes
```

## Step 9: Start Backend API

```bash
uv run uvicorn src.api:api --port 8001
```

## Step 10: Use Evolver

```bash
socialwares start --role evolver
# "check structure" → verify four primitives consistency
# "diagnose"        → analyze runtime data
# "evaluate"        → run API checks
# "improve"         → propose improvements
```

## Step 11: Deploy to IRC Channel

```bash
socialwares install git@github.com:xxx/task-manager.git --channel "#support"
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign bob-evolver    --role evolver  --channel "#support"
```

## Step 12: Add Tests

```bash
mkdir -p tests
# Write tests for your app
uv run pytest
```

## FAQ

### Q: socialwares deploy does nothing
Source files haven't changed. Delete `.runtime/` and run `socialwares deploy` to force rebuild.

### Q: How to add a new role?
```bash
vim agent/role/admin.md                    # create role content file
vim socialware.py                          # add: app.role("admin", file="agent/role/admin.md")
                                           # add: app.action("some_action", role=["admin"])
socialwares deploy
```

### Q: How does conversation logging work?
- Shell mode: UserPromptSubmit hook (log_prompt.sh) + PreToolUse hook (log_tool.sh) auto-capture to .runtime/data/prompts/
- SDK mode: `save_session()` saves full session to `.runtime/data/sessions/`. Hooks also fire in SDK mode.

### Q: Where are flow.yaml and commitment.yaml?
They are compile products generated in `.runtime/` by `socialwares deploy`. The source of truth is `socialware.py`. Do not edit `.runtime/flow.yaml` or `.runtime/commitment.yaml` directly.

### Q: What replaced Makefile, claude.sh, make sync?
| Old | New |
|-----|-----|
| `make create ROOM=x APP=y` | `socialwares new my-app` |
| `make deploy` | `socialwares deploy` |
| `make start ROLE=x` | `socialwares start --role x` |
| `make sync` | `pip install --upgrade socialwares` |
| `claude.sh` | `socialwares start --role default --adapter claude` |
