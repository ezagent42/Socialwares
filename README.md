# Socialwares

Socialware App scaffolding template — a web application for Agent interaction visualization.

> Traditional App: UI → API → DB (database CRUD visualization)
> Socialware: UI → Chat → Agent (Agent interaction visualization, progressive growth from conversations)

## Quick Start

```bash
# 1. Clone the template
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares

# 2. Install dependencies
uv sync

# 3. Create your App (workspace/{room}/{app}/ structure)
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task Manager"

# 4. Enter your workspace (all development happens here)
cd .socialware/workspace/my-team/task-manager

# 5. Edit four primitives
vim agent/scope/SOUL.md          # what your app can do
vim agent/role/default/SOUL.md   # agent identity
vim agent/flow/                  # add skills
vim agent/flow/flow.yaml         # register actions per role

# 6. Deploy and start
./agent/deploy.sh                # compile agent/ → .runtime/
./agent/start.sh --role default  # launch agent

# 7. Set up Claude Code environment (via dev role)
./agent/start.sh --role dev      # start dev agent
# In Claude Code: say "setup claude" → installs agent-setup plugin + settings
```

### Quick-Try (without creating a workspace)

```bash
# From repo root — uses the template directly in default workspace
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
│   ├── role/                 ← Who: Subagent identities
│   │   ├── default/SOUL.md   ← Default app user role
│   │   └── dev/SOUL.md       ← Developer role (project nav + env setup)
│   ├── scope/                ← Where: App capability declaration
│   │   └── SOUL.md
│   ├── commitment/           ← What: Eval metrics
│   │   └── eval.yaml
│   ├── flow/                 ← How: Skills + action registry
│   │   ├── flow.yaml         ← Action registry (state machines + direct actions)
│   │   ├── check_health/     ← Skill: check app health (default + dev)
│   │   └── setup_claude/     ← Skill: configure Claude Code env (dev only)
│   ├── deploy.sh             ← Compile four primitives → .runtime/
│   ├── start.sh              ← Launch agent (workspace-local)
│   └── adapters/             ← Platform adapters (Claude/Codex/Kimi)
├── scripts/
│   ├── create-my-socialware.py  ← Create a new App instance
│   └── evolve.sh                ← Workspace evolution → PR
├── claude.sh                 ← Claude Code launcher (agent-setup bootstrap)
├── .socialware/workspace/    ← Workspace instances
│   └── default/.gitkeep
├── tests/                    ← Tests
└── docs/                     ← Design documents
```

## Four Primitives

Each Socialware App defines Agent behavior through four primitives. Each primitive corresponds to a directory under `agent/`:

### Role — Who

Defines Subagent identities. Each role has its own subdirectory with `SOUL.md`.

```
agent/role/
├── default/SOUL.md   ← App user role
└── dev/SOUL.md       ← Developer role (env setup, project navigation)
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
    description: "Customer satisfaction >= 4.5"
    metric: customer_rating
    threshold: ">=4.5"
```

Execution method is determined by the App's Biz layer (API middleware / cron / eval scripts).

### Flow — How

Defines operations the Agent can execute. Two parts:

**flow.yaml** — action registry (which actions exist, who can use them):

```yaml
direct_actions:
  - { action: check_health, role: [default, dev], description: "Check app health" }
  - { action: setup_claude, role: [dev], description: "Configure Claude Code" }
```

**{action}/SKILL.md** — how to execute each action:

```
agent/flow/
├── flow.yaml               ← Action registry
├── check_health/SKILL.md   ← default + dev roles
└── setup_claude/SKILL.md   ← dev role only
```

`deploy.sh` reads `flow.yaml` and only symlinks actions allowed for each role.

> State machines are managed by the App (`src/`), permissions are checked by the App API. Flow defines "what actions exist and how to execute them".

## Workflows

### deploy.sh — Compile Four Primitives

Compiles the `agent/` four primitives into a runnable `.runtime/` structure.
Workspace-local: reads `agent/` from its own directory.

```bash
./agent/deploy.sh
```

Generated structure:

```
.runtime/
├── data/                    ← Shared data (Files/ + Sqlite/)
└── agents/
    ├── default/             ← default role's $PROJECT_DIR
    │   ├── .claude/skills/  ← check_health only (per flow.yaml)
    │   ├── SOUL.md          ← Merged: scope + role/default
    │   └── eval.yaml
    └── dev/                 ← dev role's $PROJECT_DIR
        ├── .claude/skills/  ← check_health + setup_claude
        ├── SOUL.md          ← Merged: scope + role/dev
        └── eval.yaml
```

### start.sh — Start Agent

Workspace-local: `cd` into your workspace first.

```bash
./agent/start.sh --role default              # App user role
./agent/start.sh --role dev                  # Developer role (env setup)
./agent/start.sh --role admin --adapter codex  # Different platform
./agent/start.sh --role admin,reviewer       # Multiple roles → tmux
```

### create-my-socialware — Create a New App

```bash
# Interactive
uv run scripts/create-my-socialware.py

# Command-line arguments
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "Task Manager"
```

What it does:
1. Copies template (src/, app/, agent/ + deploy.sh + start.sh + adapters/) → `.socialware/workspace/{room}/{app}/`
2. Customizes scope/SOUL.md and role/SOUL.md with your app name

Then `cd` into the workspace and work there. deploy/start are workspace-local.

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

# Deploy and start agent (from workspace or repo root)
./agent/deploy.sh && ./agent/start.sh --role default
```

## License

MIT
