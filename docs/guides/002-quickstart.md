# Quickstart

Create and run a Socialware App in 5 minutes.

## Prerequisites

- Python >= 3.12, [uv](https://docs.astral.sh/uv/), Git
- [Claude Code](https://claude.ai/code) (or Codex / Kimi Code)

## Step 1: Get the Template

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync    # install template dependencies (for make create)
```

## Step 2: Create Your App

```bash
make create ROOM=my-team APP=task-manager DESC="Task Manager"
```

This copies the template (including a workspace `Makefile` from `agent/Makefile.template`), customizes SOUL files, and runs initial deploy. Fails if workspace already exists.

## Step 3: Enter Your Workspace

All development — deploy, start, edit — happens inside the workspace. Each app has its own dependencies:

```bash
cd .socialware/workspace/my-team/task-manager
uv sync    # install app dependencies (independent from template root)
```

## Step 4: Start the Agent

```bash
make start                   # launches agent as default role (auto-deploys if needed)
```

`make start` automatically runs deploy if sources have changed, so you do not need to run `make deploy` separately the first time.

Try: "check health" — the agent runs the check_health skill.

## Step 5: Develop

```bash
# Edit four primitives
vim agent/scope/scope.md           # app capabilities
vim agent/role/default.md          # agent identity
vim agent/flow/flow.yaml           # register new actions

# Add a skill
mkdir agent/flow/create_task
vim agent/flow/create_task/SKILL.md

# Redeploy and start (from within workspace)
make deploy                        # only rebuilds if files changed
make start ROLE=default
```

## Step 6: Set Up Claude Code Environment

```bash
# From within workspace:
make start ROLE=dev
# In Claude Code: "setup claude"
```

## Step 7: Use Different Platforms

```bash
# From within workspace:
./agent/start.sh --role default --adapter codex
./agent/start.sh --role default --adapter kimicode
```

## Step 8: Multiple Roles

```bash
# From within workspace:
./agent/start.sh --role default,dev    # tmux panes
```

## Step 9: Start Backend API

```bash
# From within workspace:
uv run uvicorn src.app:app --port 8001
```

## Step 10: Add Tests

```bash
# From within your workspace — add your own tests:
mkdir -p tests
# Write tests for your app
make test
```

To run the template's built-in tests (for template contributors):
```bash
# From repo root:
make test
```

## FAQ

### Q: make deploy does nothing
Source files haven't changed. Run `make clean && make deploy` from within your workspace to force rebuild.

### Q: How to add a new role?
```bash
# From within workspace:
vim agent/role/admin.md            # create role file
vim agent/flow/flow.yaml           # add role to action permissions
make deploy
```

### Q: How does conversation logging work?
- Shell mode: PostToolUse hook auto-captures to .runtime/data/conversations/
- SDK mode: adapter's log_conversation() function

### Q: Where do deploy and start run?
Always from within an app directory (`cd .socialware/workspace/{room}/{app}`). Each app is self-contained with its own Makefile, pyproject.toml, and .venv. Room is just a grouping folder. The repo root Makefile only has `make create` and `make test` — running `make deploy` or `make start` at the root will display an error.
