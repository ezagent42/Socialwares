# Quickstart

Create and run a Socialware App in 5 minutes.

## Prerequisites

- Python >= 3.12, [uv](https://docs.astral.sh/uv/), Git
- [Claude Code](https://claude.ai/code) (or Codex / Kimi Code)

## Step 1: Get the Template

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

## Step 2: Quick-Try the Template

```bash
make start                   # auto-deploys, launches agent as default role
```

Try: "check health" — the agent runs the check_health skill.

## Step 3: Create Your Own App

```bash
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task Manager"
cd .socialware/workspace/my-team/task-manager
```

This copies the template, customizes SOUL files, runs initial deploy. Fails if workspace already exists.

## Step 4: Develop

```bash
# Edit four primitives
vim agent/scope/scope.md           # app capabilities
vim agent/role/default.md          # agent identity
vim agent/flow/flow.yaml           # register new actions

# Add a skill
mkdir agent/flow/create_task
vim agent/flow/create_task/SKILL.md

# Deploy and start
make deploy                        # only rebuilds if files changed
make start ROLE=default
```

## Step 5: Set Up Claude Code Environment

```bash
make start ROLE=dev
# In Claude Code: "setup claude"
```

## Step 6: Use Different Platforms

```bash
./agent/start.sh --role default --adapter codex
./agent/start.sh --role default --adapter kimicode
```

## Step 7: Multiple Roles

```bash
./agent/start.sh --role default,dev    # tmux panes
```

## Step 8: Start Backend API

```bash
uv run uvicorn src.app:app --port 8001
```

## Step 9: Run Tests

```bash
make test
```

## FAQ

### Q: make deploy does nothing
Source files haven't changed. Run `make clean && make deploy` to force rebuild.

### Q: How to add a new role?
```bash
vim agent/role/admin.md            # create role file
vim agent/flow/flow.yaml           # add role to action permissions
make deploy
```

### Q: How does conversation logging work?
- Shell mode: PostToolUse hook auto-captures to .runtime/data/conversations/
- SDK mode: adapter's log_conversation() function
