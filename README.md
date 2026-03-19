# Socialwares

Socialware App scaffolding template — a web application for Agent interaction visualization.

> Traditional App: UI → API → DB (database CRUD visualization)
> Socialware: UI → Chat → Agent (Agent interaction visualization, progressive growth from conversations)

## Quick Start

```bash
# 1. Clone the template
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares

# 2. Set up Claude Code environment (agent-setup plugin auto-installs on first run)
./claude.sh
# Inside Claude Code, run /agent-setup:init to complete setup, then exit

# 3. Install dependencies
uv sync

# 4. Create your App (workspace/{room}/{app}/ structure)
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task Manager"

# 5. Start the backend API
uv run uvicorn src.app:app --port 8001 &

# 6. Start the agent (CLI mode, new terminal)
./agent/start.sh --role default --workspace .socialware/workspace/my-team/task-manager

# Or use the template directly (without creating a workspace)
./agent/deploy.sh
./agent/start.sh --role default
```

## Directory Structure

```
socialwares/
├── app/                      ← Frontend (Next.js: UI + Chat)
├── src/                      ← Backend (FastAPI: API + Agent SDK startup)
│   ├── app.py                ← FastAPI entry point
│   └── start_agent.py        ← SDK mode Agent startup
├── agent/                    ← Four primitives + toolchain
│   ├── role/                 ← Who: Subagent identity and permissions
│   │   └── default/SOUL.md
│   ├── scope/                ← Where: App capability declaration
│   │   └── SOUL.md
│   ├── commitment/           ← What: Eval metrics
│   │   └── eval.yaml
│   ├── flow/                 ← How: Skills (operation definitions)
│   │   └── check_health/SKILL.md
│   ├── deploy.sh             ← Compile four primitives → .runtime/
│   ├── start.sh              ← CLI mode startup entry point
│   └── adapters/             ← Platform adapters (Claude/Codex/Kimi)
├── scripts/
│   ├── create-my-socialware.py  ← Create a new App instance
│   └── evolve.sh                ← Workspace evolution → PR
├── .socialware/workspace/    ← Workspace instances
│   └── default/.gitkeep
├── tests/                    ← Tests
└── docs/                     ← Design documents
```

## Four Primitives

Each Socialware App defines Agent behavior through four primitives. Each primitive corresponds to a directory under `agent/`:

### Role — Who

Defines Subagent identity. Each role has its own subdirectory containing a `SOUL.md` that describes its identity and permissions.

```
agent/role/
├── admin/SOUL.md      ← Admin agent identity
└── reviewer/SOUL.md   ← Reviewer agent identity
```

### Scope — Where

Defines App-level capability declarations. `SOUL.md` describes what the Agent can do and where its boundaries are.

- Internal: Agent operation boundaries
- External: Public description, readable by other Agents

### Commitment — What

Defines trackable commitments and evaluation criteria. Declarative — describes "what counts as meeting the standard", without prescribing "how to check".

```yaml
commitments:
  C1:
    description: "Customer satisfaction ≥ 4.5"
    metric: customer_rating
    threshold: ">=4.5"
```

Execution method is determined by the App's Biz layer (API middleware / cron / eval scripts).

### Flow — How

Defines operations the Agent can execute. Each operation has its own subdirectory containing a `SKILL.md` (Claude Code skill format).

```
agent/flow/
├── create_task/SKILL.md
├── review_task/SKILL.md
└── query_task/SKILL.md
```

> State machines are managed by the App (`src/`), permissions are checked by the App API. Flow only defines "how to do it".

## Workflows

### deploy.sh — Compile Four Primitives

Compiles the `agent/` four primitives into a runnable `.runtime/` structure:

```bash
./agent/deploy.sh                    # Compile to default workspace
./agent/deploy.sh .socialware/workspace/my-app   # Compile to specified workspace
```

Generated structure:

```
.runtime/
├── data/                    ← Shared data (Files/ + Sqlite/)
└── agents/
    └── {role}/              ← Each role's $PROJECT_DIR
        ├── .claude/skills/  ← Symlinked from agent/flow/
        ├── SOUL.md          ← Merged: scope/SOUL.md + role/{name}/SOUL.md
        └── eval.yaml        ← Copied from agent/commitment/eval.yaml
```

### start.sh — Start Agent

```bash
# CLI mode: Claude TUI
./agent/start.sh --role default
./agent/start.sh --role admin --adapter codex
./agent/start.sh --role admin,reviewer              # Multiple roles → tmux

# Specify workspace
./agent/start.sh --role admin --workspace .socialware/workspace/my-app

# SDK mode
python src/start_agent.py --role admin
python src/start_agent.py --role admin --adapter codex
```

### create-my-socialware — Create a New App

```bash
# Interactive
uv run scripts/create-my-socialware.py

# Command-line arguments
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task Manager"
```

What it does:
1. Copies template (src/, app/, agent/ four primitives) → `.socialware/workspace/{room}/{app}/`
2. Customizes scope/SOUL.md and role/SOUL.md
3. Automatically runs deploy.sh

### evolve.sh — Workspace Evolution

```bash
# Check changes
./scripts/evolve.sh my-team/task-manager --check

# Create PR (feed workspace improvements back to the template)
./scripts/evolve.sh my-team/task-manager --pr
```

Evolution routing:
- Changes in `.runtime/` → workspace-specific adaptation, does not trigger a PR
- Changes in `agent/` → generic improvements, automatically creates a PR back to main

## Platform Adapters

Adapters translate the deployed `.runtime/agents/{role}/` into platform-specific launch commands. Each adapter lives in `agent/adapters/{platform}/` with a `shell.sh` (CLI mode) and/or `sdk.py` (SDK mode).

### Usage

```bash
# Default: Claude Code
./agent/start.sh --role default

# Switch platform
./agent/start.sh --role default --adapter codex
./agent/start.sh --role default --adapter kimicode

# SDK mode (production)
python src/start_agent.py --role default --adapter codex
```

### Supported Platforms

| Platform | Command | Working Directory | Permission Skip | Ref |
|----------|---------|-------------------|-----------------|-----|
| Claude Code | `claude` | `cd $dir` | `--dangerously-skip-permissions` | [docs](https://docs.anthropic.com/en/docs/claude-code/cli-reference) |
| Codex | `codex` | `--cd $dir` | `--full-auto` | [docs](https://openai.github.io/codex/cli/reference) |
| Kimi Code | `kimi` | `--work-dir $dir` | `--yolo` | [docs](https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html) |

### Adding a New Adapter

1. Create `agent/adapters/{name}/shell.sh` and/or `sdk.py`
2. `shell.sh` receives `$PROJECT_DIR` as first argument, `cd` into it, launch CLI
3. `sdk.py` extends `BaseAdapter` from `agent/adapters/base.py`
4. Use with `--adapter {name}`

## Progressive Growth

```
P1 Define Agent → P2 Refine Flow → P3 Refine Commitment → P4 Expand Scope → P5 Expand Role
                                                                          ↓
                                    P0 ← Reach monolith boundary ← Create new App or /zchat connection
```

Each improvement materializes as growth in the Biz layer (API + UI + DB).

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Start the backend
uv run uvicorn src.app:app --port 8001

# Start the agent
./agent/deploy.sh && ./agent/start.sh --role default
```

## License

MIT
