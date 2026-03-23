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

# 3. Create your App
make create ROOM=my-team APP=task-manager DESC="Task Manager"

# 4. Enter your workspace (all development happens here)
cd .socialware/workspace/my-team/task-manager

# 5. Start agent (ready — create already deployed)
make start

# 6. Edit four primitives as you develop
vim agent/scope/scope.md
vim agent/role/default.md
vim agent/flow/flow.yaml

# 7. Redeploy and start
make deploy
make start ROLE=default
```

## Directory Structure

```
socialwares/
├── app/                          ← Frontend (Next.js: UI + Chat)
├── src/                          ← Backend (FastAPI)
│   ├── app.py                    ← API entry point (/health, /violations)
│   └── start_agent.py            ← SDK mode Agent startup
├── agent/                        ← Four primitives + toolchain
│   ├── role/                     ← Who: Subagent identities
│   │   ├── default.md            ← App user role
│   │   ├── dev.md                ← Developer role (env setup)
│   │   └── evolver.md            ← Evolver role (diagnose + improve)
│   ├── scope/                    ← Where: App capability boundary
│   │   └── scope.md
│   ├── commitment/               ← What: Constraints on flow edges
│   │   └── constraints.yaml
│   ├── flow/                     ← How: Skills + action registry
│   │   ├── flow.yaml             ← Action registry (roles → actions)
│   │   ├── check_health/         ← default + dev + evolver
│   │   ├── inspect/              ← default + dev + evolver
│   │   ├── setup_claude/         ← dev only
│   │   ├── evolve_diagnose/      ← evolver only (+ scripts/diagnose.py)
│   │   ├── evolve_eval/          ← evolver only (+ scripts/run_eval.py)
│   │   ├── evolve_improve/       ← evolver only
│   │   └── evolve_auto/          ← evolver only (+ scripts/run_loop.py)
│   ├── deploy.sh                 ← Compile four primitives → .runtime/
│   ├── start.sh                  ← Launch agent (requires deploy first)
│   └── adapters/                 ← Platform adapters (Claude/Codex/Kimi)
├── Makefile                      ← Root: make create + make test only
├── scripts/
│   └── create-my-socialware.py   ← Create new App instance
├── claude.sh                     ← Claude Code launcher (agent-setup)
├── .socialware/workspace/        ← Workspace instances (each has its own Makefile)
├── tests/
└── docs/
    └── guides/                   ← User guides (architecture, quickstart, etc.)
```

Each workspace has its own `Makefile` (copied from `agent/Makefile.template` during `make create`):

```
.socialware/workspace/{room}/{app}/
├── Makefile                      ← make deploy / make start / make clean
├── agent/                        ← Four primitives + toolchain
│   └── Makefile.template         ← Template for workspace Makefile
├── src/
├── app/
├── .runtime/                     ← Deploy output (gitignored)
└── pyproject.toml
```

## Four Primitives

Each Socialware App defines Agent behavior through four primitives in `agent/`:

### Role — Who

Subagent identities. Each role gets its own `.md` file and a filtered set of skills (from flow.yaml).

| Role | Purpose | Skills |
|------|---------|--------|
| `default` | App user | check_health |
| `dev` | Developer (env setup) | check_health, setup_claude |
| `evolver` | Diagnose + improve | diagnose, eval, improve, auto |

### Scope — Where

App capability boundary via `scope/scope.md`.

- **Internal**: What the Agent can and cannot do (constrains behavior)
- **External**: Public description (other Agents read this to decide delegation)
- **Participation**: Who can join, minimum members

### Commitment — What (Constraints)

Constraints bind to flow edges — enforce time, quality, or certainty on state transitions.

```yaml
# agent/commitment/constraints.yaml
transition_constraints:
  C1:
    description: "Review within 72h"
    on: { flow: F1, from: submitted, action: review }
    type: time
    deadline: 72h
    on_violation:
      trigger_action: force_resolve
      trigger_role: admin
```

**Violation lifecycle:**
1. App backend detects violation → writes to `.runtime/data/violations/current.jsonl`
2. On session start → hook notifies the responsible role
3. Role handles it (e.g., admin force_resolves)

Detection is the app developer's responsibility. See [agent/commitment/README.md](agent/commitment/README.md) for implementation guide.

### Flow — How

Actions the Agent can execute, registered in `flow.yaml`:

```yaml
# agent/flow/flow.yaml
direct_actions:
  - { action: check_health,     role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude,     role: [dev],                   description: "Configure Claude Code" }
  - { action: evolve_diagnose,  role: [evolver],               description: "Diagnose from runtime data" }
  - { action: evolve_eval,      role: [evolver],               description: "Run eval cases" }
  - { action: evolve_improve,   role: [evolver],               description: "Apply improvements" }
  - { action: evolve_auto,      role: [evolver],               description: "Automated evolution loop" }
```

Each action has a `SKILL.md` (+ optional `scripts/`). `deploy.sh` reads `flow.yaml` and only symlinks actions allowed for each role.

## Workflows

### deploy.sh

Run from within a workspace. Not available at repo root.

Compiles `agent/` four primitives into `.runtime/`. Idempotent — detects added/removed roles and skills.

What it generates per role:
- `.claude/skills/` — symlinks to allowed flow/ actions (per flow.yaml)
- `.claude/hooks/log_action.sh` — PostToolUse hook for conversation logging
- `.claude/hooks/check_violations.sh` — SessionStart hook for violation notifications
- `SOUL.md` — merged scope/scope.md + role/{name}.md
- `constraints.yaml` — copied from commitment/
- `flow.yaml` — copied for reference

```
.runtime/
├── data/
│   ├── Files/                  ← App runtime files
│   ├── Sqlite/                 ← App database
│   ├── conversations/          ← Agent interaction logs (JSONL)
│   └── violations/             ← Constraint violation queue (JSONL)
└── agents/
    ├── default/                ← default role's $PROJECT_DIR
    │   ├── .claude/skills/     ← check_health (per flow.yaml)
    │   ├── .claude/hooks/      ← log_action.sh + check_violations.sh
    │   ├── SOUL.md
    │   └── constraints.yaml
    └── evolver/                ← evolver role's $PROJECT_DIR
        ├── .claude/skills/     ← diagnose + eval + improve + auto
        ├── .claude/hooks/
        ├── SOUL.md
        └── constraints.yaml
```

### start.sh

Run from within a workspace. Not available at repo root.

Launches agent. Requires `.runtime/` to exist (run `make deploy` or `./agent/deploy.sh` first).

```bash
./agent/start.sh --role default              # App user
./agent/start.sh --role dev                  # Developer (env setup)
./agent/start.sh --role evolver              # Evolver (diagnose + improve)
./agent/start.sh --role admin --adapter codex  # Different platform
./agent/start.sh --role admin,reviewer       # Multiple roles → tmux
```

### create-my-socialware

```bash
make create ROOM=my-team APP=task-manager DESC="Task Manager"
```

Copies template → workspace (including `Makefile` from `agent/Makefile.template`), customizes scope.md and role files, runs initial deploy. Fails if workspace already exists.

### claude.sh

First-time Claude Code environment setup. See [docs/guides/005-claude-setup.md](docs/guides/005-claude-setup.md).

## Runtime Data

Agent interactions and constraint violations are logged to `.runtime/data/`:

### Conversation Logs (`.runtime/data/conversations/*.jsonl`)

Written by PostToolUse hook (shell mode) or adapter (SDK mode):

```json
{"timestamp": "2026-03-20T10:00:00Z", "role": "default", "type": "tool_call", "tool": "create_task", "input": {"title": "GPS"}, "success": true}
```

### Violation Queue (`.runtime/data/violations/*.jsonl`)

Written by app backend when constraints are violated:

```json
{"id": "v-001", "constraint": "C1", "description": "review overdue 72h", "trigger_action": "force_resolve", "trigger_role": "admin", "detected_at": "2026-03-20T10:00:00Z", "resolved": false}
```

API endpoints: `GET /violations`, `POST /violations/{id}/resolve`

## Evolver

Built-in role for improving your app based on runtime evidence.

| Skill | Mode | What it does |
|-------|------|-------------|
| `evolve_diagnose` | Manual | Scan conversations + violations → diagnostic report |
| `evolve_eval` | Manual | Run eval_cases.yaml → score |
| `evolve_improve` | Manual | Map problems to primitives → propose + apply changes |
| `evolve_auto` | Auto | Automated loop: evaluate → diagnose → propose → apply → re-evaluate |

```bash
# From within a workspace:
./agent/start.sh --role evolver
# "diagnose"       → analyze runtime data
# "evaluate"       → run eval cases, report score
# "improve"        → fix issues based on evidence
# "auto-optimize"  → automated improvement loop
```

See [docs/guides/using-evolver.md](docs/guides/using-evolver.md) for full guide.

## Platform Adapters

| Platform | Command | Working Directory | Permission Skip | Ref |
|----------|---------|-------------------|-----------------|-----|
| Claude Code | `claude` | `cd $dir` | `--dangerously-skip-permissions` | [docs](https://docs.anthropic.com/en/docs/claude-code/cli-reference) |
| Codex | `codex` | `--cd $dir` | `--full-auto` | [docs](https://openai.github.io/codex/cli/reference) |
| Kimi Code | `kimi` | `--work-dir $dir` | `--yolo` | [docs](https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html) |

Adding a new adapter: create `agent/adapters/{name}/shell.sh` and/or `sdk.py`.
See `agent/adapters/base.py` for the interface.

## Progressive Growth

```
P1 Define Agent → P2 Refine Flow → P3 Refine Commitment → P4 Expand Scope → P5 Expand Role
                                                                               ↓
                                         P0 ← Reach boundary ← New App or /zchat
```

Each phase: edit agent/ → `make deploy` → start → grow src/ → repeat (all from within a workspace).
See [docs/designs/progressive-dev-guide-example.md](docs/designs/progressive-dev-guide-example.md) for detailed example.

## Development

```bash
uv sync
make test        # run template tests
make create ROOM=dev APP=sandbox DESC="Development sandbox"
cd .socialware/workspace/dev/sandbox
make deploy && make start
```

## License

MIT
