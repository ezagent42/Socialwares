# Quickstart

Create and run a Socialware App in 5 minutes.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Claude Code](https://claude.ai/code) or Codex / Kimi Code
- Git

## Step 1: Get the Template

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

## Step 2: Understand Four Primitives

All Agent behavior is defined through four primitives in `agent/`:

| Primitive | Directory | Purpose | Key File |
|-----------|-----------|---------|----------|
| **Role** (Who) | `agent/role/` | Agent identity and permissions | `SOUL.md` |
| **Scope** (Where) | `agent/scope/` | App capability boundaries | `SOUL.md` |
| **Commitment** (What) | `agent/commitment/` | Eval metrics | `eval.yaml` |
| **Flow** (How) | `agent/flow/` | Actions the agent can perform | `flow.yaml` + `SKILL.md` |

## Step 3: Quick-Try the Template

From the repo root — uses the template directly without creating a workspace:

```bash
./agent/deploy.sh                # compile four primitives → .runtime/
./agent/start.sh --role default  # launch agent (Claude Code TUI)
```

Try saying: "check health" — the agent runs the check_health skill.

## Step 4: Create Your Own App

```bash
# From repo root:
uv run scripts/create-my-socialware.py \
    --room my-team \
    --app task-manager \
    --description "Task management app"
```

This copies the template into `.socialware/workspace/my-team/task-manager/`.
**Does NOT deploy** — you edit four primitives first.

## Step 5: Enter Your Workspace

```bash
cd .socialware/workspace/my-team/task-manager
```

**All development happens here.** The workspace is self-contained.

## Step 6: Edit Four Primitives

```bash
# What your app can do
vim agent/scope/SOUL.md

# Agent identity
vim agent/role/default/SOUL.md

# Add a new skill
mkdir -p agent/flow/create_task
cat > agent/flow/create_task/SKILL.md << 'EOF'
---
name: create_task
description: "Create a new task"
---

# Create Task

## Trigger
User says "create task", "new task", etc.

## Flow
1. Get task title and description from user
2. Call API: POST /tasks
3. Return result
EOF

# Register the action in flow.yaml
vim agent/flow/flow.yaml
```

Add to `flow.yaml`:
```yaml
direct_actions:
  - { action: check_health,  role: [default, dev], description: "Check app health" }
  - { action: setup_claude,  role: [dev], description: "Configure Claude Code" }
  - { action: create_task,   role: [default], description: "Create a new task" }  # ← add this
```

## Step 7: Deploy and Start

```bash
./agent/deploy.sh                # compile agent/ → .runtime/
./agent/start.sh --role default  # launch agent
```

After editing four primitives, always re-deploy before starting.

## Step 8: Set Up Claude Code Environment

Use the dev role to configure Claude Code plugins and settings:

```bash
./agent/start.sh --role dev
# In Claude Code, say: "setup claude"
# This installs agent-setup plugin into .runtime/agents/dev/.claude/
```

## Step 9: Use Different Platforms

```bash
./agent/start.sh --role default                    # Claude Code (default)
./agent/start.sh --role default --adapter codex    # Codex
./agent/start.sh --role default --adapter kimicode # Kimi Code
```

## Step 10: Multi-Role

```bash
# Multiple roles in tmux panes
./agent/start.sh --role default,dev
```

## Step 11: Start Backend API

```bash
uv run uvicorn src.app:app --port 8001
```

## Step 12: Feed Improvements Back

When you improve Agent config in your workspace, you can PR it back to the template:

```bash
# Compare your workspace agent/ with the template
diff -rq agent/ ../../../agent/ --exclude=README.md --exclude=__pycache__

# If improvements are general, create a branch and PR manually
```

## FAQ

### Q: deploy.sh reports "No role found"
Ensure `agent/role/` has at least one role directory (e.g. `default/`) with a `SOUL.md`.

### Q: start.sh says ".runtime/ not found"
Run `./agent/deploy.sh` first. start.sh does not auto-deploy.

### Q: How to add a new role?
```bash
mkdir agent/role/admin
vim agent/role/admin/SOUL.md
# Add the role to flow.yaml actions
vim agent/flow/flow.yaml
./agent/deploy.sh  # re-deploy
```

### Q: Which skills does each role get?
`deploy.sh` reads `flow.yaml` and only symlinks actions allowed for that role.
Check `flow.yaml` to see the role→action mapping.

## Next Steps

- Read [README.md](../README.md) for full architecture
- Check `docs/designs/` for architecture decisions
- Add more skills in `agent/flow/` and register them in `flow.yaml`
