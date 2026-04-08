# Quickstart

A complete walkthrough: create a Socialware App, develop it, publish it, and let others install it.

## Prerequisites

```bash
pip install socialwares
# or from git:
pip install git+ssh://git@github.com/ezagent42/Socialwares.git
```

## 1. Create a Project

```bash
socialwares new task-review
cd task-review
```

Or create from an existing App (git URL or local path):

```bash
socialwares new my-app --from git@github.com:org/task-review.git
socialwares new my-app --from ../task-review
```

This clones the source, updates the app name, and removes `.git/` so you start fresh.

This generates:

```
task-review/
├── socialware.py           ← App declaration
├── agent/
│   ├── role/               ← default.md, dev.md, evolver.md
│   ├── scope/scope.md      ← Capability boundary
│   ├── flow/check_health/  ← One user skill (template)
│   └── commitment/README.md
├── src/api.py              ← FastAPI backend
├── app/                    ← Frontend UI
└── pyproject.toml
```

> **Note**: Only `check_health/` appears in `agent/flow/`. Built-in skills (dev_*, evolve_*, inspect, setup_claude) are provided by the framework and symlinked at deploy time.

## 2. Define the Four Primitives

Edit `socialware.py` to declare relationships:

```python
from socialwares import App

app = App("task-review")

# 1. Scope — what this App can do
app.scope(file="agent/scope/scope.md")

# 2. Roles — who uses this App
app.role("default", file="agent/role/default.md")
app.role("dev", file="agent/role/dev.md")
app.role("evolver", file="agent/role/evolver.md")

# 3. Actions — what each role can perform
app.action("check_health", role=["default"])
app.action("create_task", role=["default"])
app.action("review_task", role=["reviewer"])

# 4. State machine (optional)
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])

# 5. Commitment (optional)
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
)
```

Edit the content files:

- `agent/scope/scope.md` — Capabilities and boundaries
- `agent/role/default.md` — Default user role description
- `agent/flow/create_task/SKILL.md` — Skill instructions (create the directory)

Each skill directory follows this structure:

```
agent/flow/create_task/
├── SKILL.md          ← Required: Agent execution instructions
├── scripts/          ← Optional: automation scripts
└── references/       ← Optional: reference materials
```

## 3. Compile

```bash
socialwares deploy
```

This generates `.runtime/` with per-role configurations:

```bash
ls .runtime/agents/              # default/  dev/  evolver/
cat .runtime/agents/default/SOUL.md    # scope + role + workflows merged
ls .runtime/agents/default/.claude/skills/  # check_health  create_task  submit_task
```

## 4. Start the Backend

```bash
uv run uvicorn src.api:app --port 8001
```

## 5. Launch the Agent

```bash
# Single role (interactive TUI)
socialwares start --role default

# Multiple roles (tmux split panes)
socialwares start --role default,reviewer,evolver

# SDK mode (non-interactive, returns result)
socialwares start --role default --prompt "check health"
```

## 6. Iterate

The development loop:

```
Edit socialware.py + agent/ → socialwares deploy → socialwares start → test → repeat
```

## 7. Publish Your App

When the App is ready for others to use:

```bash
# Commit and push
git add -A && git commit -m "v1.0.0: task review app"
git push origin main
git tag v1.0.0 && git push origin v1.0.0
```

Your App is now installable via its git URL.

## 8. Others Install Your App

On another machine (with an IRC channel infrastructure):

```bash
# Install from a standalone repo
socialwares install git@github.com:yourorg/task-review.git --channel "#support"

# Install from a monorepo subdirectory
socialwares install git@github.com:yourorg/socialware-apps.git --channel "#support" --subdir task-review

# Or install to a custom path
socialwares install git@github.com:yourorg/task-review.git --channel "#support" --path /opt/agents/task-review

# Assign roles to existing Agents
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign bob-reviewer   --role reviewer --channel "#support"

# Check what's installed
socialwares list
```

### What `install` does:

1. `git clone` the repo to `.socialware/workspace/{channel}/apps/{app}/` (with `--subdir`, clones then extracts the subdirectory)
2. Run `socialwares deploy` inside the app directory
3. Record the installation in `installs.json`

### What `assign` does:

1. Merge SOUL.md into the Agent's config (idempotent, uses source markers)
2. Symlink skills for the assigned role
3. Deep-merge `flow.yaml`, `commitment.yaml`, and `settings.local.json`

Assign is idempotent — running it twice produces the same result. Multiple Apps can be assigned to the same Agent; SOUL.md blocks are tagged per-app and won't conflict.

### Uninstall:

```bash
socialwares uninstall task-review --channel "#support"
```

## 9. Configure Adapters

The default adapter is `claude` (Claude Code). Override in `pyproject.toml`:

```toml
[tool.socialwares]
adapter = "claude"     # or "codex", "kimi"
api_port = 8001
agent_dir = "agent"    # default; change to use a different directory
```

Or per-launch:

```bash
socialwares start --role default --adapter codex
```

## FAQ

### Q: `socialwares deploy` seems to do nothing

The source files haven't changed. Delete `.runtime/` and re-run to force a rebuild.

### Q: How to add a new role?

```bash
# Create the role content file
vim agent/role/admin.md

# Register in socialware.py
# app.role("admin", file="agent/role/admin.md")
# app.action("some_action", role=["admin"])

socialwares deploy
```

### Q: How does conversation logging work?

Hook scripts (`log_prompt.py`, `log_tool.py`) capture all prompts and tool calls to `.runtime/data/prompts/`. Logs are split by `session_id` into `{session_id}.jsonl`; without a session_id, they go to `current.jsonl`.

### Q: Where are flow.yaml and commitment.yaml?

They are compile products in `.runtime/`, generated by `socialwares deploy`. The source of truth is `socialware.py`. Do not edit them directly.
