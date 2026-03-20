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
| **Role** (Who) | `agent/role/` | Agent identities (default, dev, evolver) | `SOUL.md` |
| **Scope** (Where) | `agent/scope/` | App capability boundaries | `SOUL.md` |
| **Commitment** (What) | `agent/commitment/` | Constraints on flow edges | `constraints.yaml` |
| **Flow** (How) | `agent/flow/` | Actions + action registry | `flow.yaml` + `SKILL.md` |

## Step 3: Quick-Try the Template

```bash
./agent/start.sh --role default  # auto-deploys on first run
```

Try saying: "check health" — the agent runs the check_health skill.

## Step 4: Create Your Own App

```bash
uv run scripts/create-my-socialware.py \
    --room my-team \
    --app task-manager \
    --description "Task management app"
```

Copies template + customizes SOUL.md + auto-deploys. Fails if workspace already exists.

## Step 5: Enter Your Workspace

```bash
cd .socialware/workspace/my-team/task-manager
```

All development happens here. The workspace is self-contained (has its own agent/, src/, deploy.sh, start.sh).

## Step 6: Edit Four Primitives

```bash
# App capabilities + boundaries
vim agent/scope/SOUL.md

# Agent identity
vim agent/role/default/SOUL.md

# Add a new skill
mkdir -p agent/flow/create_task
vim agent/flow/create_task/SKILL.md

# Register the action in flow.yaml
vim agent/flow/flow.yaml
# Add: - { action: create_task, role: [default], description: "Create a new task" }
```

## Step 7: Start Again

```bash
./agent/start.sh --role default  # auto-detects changes, re-deploys if needed
```

`start.sh` checks if `agent/` has been modified since last deploy and auto-redeploys.
You can also run `./agent/deploy.sh` manually to see what gets compiled.

### What deploy.sh generates:

```
.runtime/
├── data/
│   ├── conversations/    ← Agent interaction logs (JSONL, auto-captured)
│   └── violations/       ← Constraint violation queue (JSONL, app writes)
└── agents/{role}/
    ├── .claude/skills/   ← Symlinked from agent/flow/ (filtered by flow.yaml)
    ├── .claude/hooks/    ← log_action.sh (conversation logging)
    │                       + check_violations.sh (violation notifications)
    ├── SOUL.md           ← Merged: scope + role
    └── constraints.yaml  ← Copied from commitment/
```

## Step 8: Set Up Claude Code Environment

```bash
./agent/start.sh --role dev
# In Claude Code: say "setup claude"
# Installs agent-setup plugin + hooks + MCP
```

## Step 9: Use Different Platforms

```bash
./agent/start.sh --role default                    # Claude Code (default)
./agent/start.sh --role default --adapter codex    # Codex
./agent/start.sh --role default --adapter kimicode # Kimi Code
```

## Step 10: Multiple Roles

```bash
./agent/start.sh --role default,dev    # tmux panes
```

## Step 11: Start Backend API

```bash
uv run uvicorn src.app:app --port 8001
```

## Step 12: Use the Evolver

After your app has been running and has some data in `.runtime/data/`:

```bash
./agent/start.sh --role evolver
```

```
You: "diagnose"        → scan conversations + violations → report
You: "evaluate"        → run eval cases → score
You: "improve"         → propose + apply four-primitive changes
You: "auto-optimize"   → automated evolution loop
```

See [docs/guides/using-evolver.md](guides/using-evolver.md) for full guide.

## Step 13: Run Tests

```bash
uv run pytest -v    # 36 tests
```

## FAQ

### Q: deploy.sh reports "No role found"
Ensure `agent/role/` has at least one role directory (e.g. `default/`) with a `SOUL.md`.

### Q: start.sh seems slow on first run
It auto-deploys on first run (or when `agent/` has changed). Subsequent starts are fast.

### Q: How to add a new role?
```bash
mkdir agent/role/admin
vim agent/role/admin/SOUL.md
vim agent/flow/flow.yaml    # add the role to action permissions
./agent/deploy.sh           # or just start.sh (auto-deploys)
```

### Q: What data does the evolver read?
- `.runtime/data/conversations/*.jsonl` — agent interaction logs (auto-captured by hooks)
- `.runtime/data/violations/*.jsonl` — constraint violations (written by your app backend)
- `agent/flow/evolve_eval/eval_cases.yaml` — your benchmark test cases

### Q: How do conversation logs get captured?
- **Shell mode** (start.sh): PostToolUse hook `log_action.sh` auto-captures every tool call
- **SDK mode** (start_agent.py): adapter's `log_conversation()` function

## Next Steps

- Read [README.md](../README.md) for full architecture
- Read [docs/guides/using-evolver.md](guides/using-evolver.md) for evolver guide
- Read [docs/designs/progressive-dev-guide-example.md](designs/progressive-dev-guide-example.md) for P1→P5 example
- Check `docs/designs/` for architecture decisions
