# Socialwares

Socialware App scaffolding template — a web application for Agent interaction visualization.

> Traditional App: UI → API → DB (database CRUD visualization)
> Socialware: UI → Chat → Agent (Agent interaction visualization, progressive growth from conversations)

## Quick Start

```bash
# 1. Clone the template
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares

# 2. Install template dependencies
uv sync

# 3. Create your App
make create ROOM=my-team APP=task-manager DESC="Task Manager"

# 4. Enter your workspace (all development happens here)
cd .socialware/workspace/my-team/task-manager

# 5. Start agent (auto-deploys if sources changed)
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
├── app/.gitkeep                  ← Frontend placeholder
├── src/
│   ├── __init__.py
│   ├── app.py                    ← FastAPI (/health, /violations)
│   └── start_agent.py            ← SDK mode launch
├── agent/                        ← Four primitives + toolchain
│   ├── role/                     ← Who: flat .md files (one per role)
│   │   ├── default.md            ← App user role
│   │   ├── dev.md                ← Developer role (env setup)
│   │   └── evolver.md            ← Evolver role (diagnose + improve)
│   ├── scope/                    ← Where: App capability boundary
│   │   └── scope.md
│   ├── commitment/               ← What: Constraints on flow edges
│   │   └── commitment.yaml      ← Unified schema: from/to/condition/on_violation
│   ├── flow/                     ← How: Skills + action registry
│   │   ├── flow.yaml             ← Action registry (roles → actions)
│   │   ├── check_health/         ← default + dev + evolver
│   │   ├── inspect/              ← dev + evolver
│   │   ├── setup_claude/         ← dev only
│   │   ├── evolve_diagnose/      ← evolver only (+ scripts/diagnose.py)
│   │   ├── evolve_eval/          ← evolver only (+ scripts/run_eval.py)
│   │   ├── evolve_improve/       ← evolver only
│   │   └── evolve_auto/          ← evolver only (+ scripts/run_auto.py)
│   ├── adapters/                 ← Platform adapters (Claude/Codex/Kimi)
│   │   ├── base.py
│   │   ├── claude/ (shell.sh + sdk.py)
│   │   ├── codex/ (shell.sh + sdk.py)
│   │   └── kimicode/ (shell.sh + sdk.py)
│   ├── Makefile.template         ← Source for workspace Makefile
│   ├── deploy.sh                 ← Compile four primitives → .runtime/
│   └── start.sh                  ← Launch agent (requires deploy first)
├── Makefile                      ← Root: make create + make test only
├── scripts/
│   └── create-my-socialware.py   ← Create new App instance
├── claude.sh                     ← Claude Code launcher (agent-setup)
├── .socialware/workspace/        ← App instances (each app has own Makefile + pyproject.toml)
├── tests/
├── docs/
│   ├── discuss/commitment.md     ← Commitment design discussion
│   ├── designs/
│   └── guides/                   ← User guides (architecture, quickstart, etc.)
└── pyproject.toml
```

Each app has its own `Makefile`, `pyproject.toml`, and `.venv/` (copied from template during `make create`). Room is just a grouping folder:

```
.socialware/workspace/{room}/{app}/
├── Makefile                      ← make deploy / make start / make test / make clean
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

Subagent identities. Each role gets its own flat `.md` file and a filtered set of skills (from flow.yaml).

| Role | Purpose | Skills |
|------|---------|--------|
| `default` | App user | check_health |
| `dev` | Developer (env setup) | check_health, setup_claude, inspect |
| `evolver` | Diagnose + improve | check_health, inspect, diagnose, eval, improve, auto |

### Scope — Where

App capability boundary via `scope/scope.md`.

- **Internal**: What the Agent can and cannot do (constrains behavior)
- **External**: Public description (other Agents read this to decide delegation)
- **Participation**: Who can join, minimum members

### Commitment — What (Constraints on Flow Edges)

Commitment constrains the edges of the flow graph — what must be true between two role-actions. Uses a unified schema:

```yaml
# agent/commitment/commitment.yaml
commitments:
  C1:
    from: { role: coder, action: submit_code }
    to:   { role: pm, action: review_code }
    condition: "within 24h"
    on_violation: { role: tech_lead, action: escalate }
```

- `from` — edge start: who did what (trigger)
- `to` — edge end: who must do what (responsible party)
- `condition` — natural language condition that must be true
- `on_violation` — escalation when condition is not met

See [docs/discuss/commitment.md](docs/discuss/commitment.md) for full design discussion.

### Flow — How

Actions the Agent can execute, registered in `flow.yaml`:

```yaml
# agent/flow/flow.yaml
direct_actions:
  - { action: check_health,     role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude,     role: [dev],                   description: "Configure Claude Code" }
  - { action: inspect,          role: [dev, evolver],          description: "Show project structure" }
  - { action: evolve_diagnose,  role: [evolver],               description: "Diagnose from runtime data" }
  - { action: evolve_eval,      role: [evolver],               description: "Run eval cases" }
  - { action: evolve_improve,   role: [evolver],               description: "Apply improvements" }
  - { action: evolve_auto,      role: [evolver],               description: "Automated evolution loop" }
```

Each action has a `SKILL.md` (+ optional `scripts/`). `deploy.sh` reads `flow.yaml` and copies only the actions allowed for each role into `.runtime/`.

## Workflows

### deploy.sh

Run from within a workspace. Not available at repo root.

Compiles `agent/` four primitives into `.runtime/`. Idempotent — detects added/removed roles and skills. Takes `--adapter` parameter (claude/codex/kimi) to generate platform-specific config.

What it generates per role:
- Skills dir — symlinks to allowed flow/ actions (per flow.yaml): `.claude/skills/` (claude) or `.agents/skills/` (codex/kimi)
- Hooks dir — `log_prompt.sh` (UserPromptSubmit) + `log_tool.sh` (PreToolUse): `.claude/hooks/` (claude) or `.codex/hooks/` (codex) or none (kimi)
- Hook registration — `settings.local.json` (claude) or `.codex/hooks.json` (codex) or none (kimi)
- Prompt file — merged scope/scope.md + role/{name}.md: `SOUL.md` (claude) or `AGENTS.md` (codex/kimi)
- `.workspace_root` — marker pointing to workspace root
- `commitment.yaml` — copied from commitment/
- `flow.yaml` — copied for reference

```
.runtime/
├── data/
│   ├── Files/                  ← App runtime files
│   ├── Sqlite/                 ← App database
│   ├── prompts/                ← Hook logs (user prompts + tool calls)
│   ├── sessions/               ← SDK full conversations
│   └── evolve/                 ← Evolver output
│       ├── reports/            ← Unified reports (check/eval/diagnose/auto_test)
│       ├── violations/         ← Commitment violations
│       └── auto_sessions/      ← Auto-test generated conversations
└── agents/
    ├── default/                ← default role's $PROJECT_DIR
    │   ├── .claude/skills/     ← check_health (per flow.yaml) [or .agents/skills/ for codex/kimi]
    │   ├── .claude/hooks/      ← log_prompt.sh + log_tool.sh [or .codex/hooks/ for codex, none for kimi]
    │   ├── .claude/settings.local.json  [or .codex/hooks.json for codex]
    │   ├── .workspace_root
    │   ├── SOUL.md             ← [or AGENTS.md for codex/kimi]
    │   └── commitment.yaml
    └── evolver/                ← evolver role's $PROJECT_DIR
        ├── .claude/skills/     ← diagnose + eval + improve + auto + inspect + check_health
        ├── .claude/hooks/      ← log_prompt.sh + log_tool.sh
        ├── .claude/settings.local.json
        ├── .workspace_root
        ├── SOUL.md             ← [or AGENTS.md for codex/kimi]
        └── commitment.yaml
```

### start.sh

Run from within a workspace. Not available at repo root.

Launches agent. Requires `.runtime/` to exist (run `make deploy` or `./agent/deploy.sh` first). When using `make start`, deploy is automatic.

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

Copies template → workspace (including `Makefile` from `agent/Makefile.template`), customizes scope.md and role files. Then Make runs deploy. Fails if workspace already exists.

### claude.sh

First-time Claude Code environment setup. See [docs/guides/005-claude-setup.md](docs/guides/005-claude-setup.md).

## Runtime Data

Agent interactions and constraint violations are logged to `.runtime/data/`:

### Prompt & Tool Logs (`.runtime/data/prompts/*.jsonl`)

Written by UserPromptSubmit hook (log_prompt.sh) and PreToolUse hook (log_tool.sh) in shell mode, or adapter in SDK mode:

```json
{"timestamp": "2026-03-20T10:00:00Z", "role": "default", "type": "tool_call", "tool": "create_task", "input": {"title": "GPS"}, "session_id": "..."}
```

### Violation Queue (`.runtime/data/evolve/violations/*.jsonl`)

Written by evolver's `diagnose.py` when it finds commitment violations during conversation analysis:

```json
{"id": "v-001", "constraint": "C1", "description": "review overdue 24h", "detected_at": "2026-03-20T10:00:00Z", "resolved": false}
```

## Evolver

Built-in role for improving your app based on runtime evidence.

| Skill | Mode | What it does |
|-------|------|-------------|
| `evolve_diagnose` | Manual | Scan conversations + constraints → diagnostic report |
| `evolve_eval` | Manual | Run eval_cases.yaml → score (API checks) |
| `evolve_improve` | Manual | Map problems to primitives → propose + apply changes |
| `evolve_auto` | Auto | Automated loop: evaluate → diagnose → propose → apply → re-evaluate |

```bash
# From within a workspace:
make start ROLE=evolver
# "diagnose"       → analyze runtime data, compute fulfillment rates
# "evaluate"       → run eval cases, report score
# "improve"        → fix issues based on evidence
# "auto-optimize"  → automated improvement loop
```

Fulfillment rate = fulfilled / total per commitment. The evolver reads conversation logs, checks each commitment's condition, and maps low fulfillment to specific four-primitive improvements.

See [docs/guides/004-commitment-and-evolve.md](docs/guides/004-commitment-and-evolve.md) for full guide.

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
uv sync                            # install template dependencies
make test                          # run template tests (for contributors)
make create ROOM=dev APP=sandbox DESC="Development sandbox"
cd .socialware/workspace/dev/sandbox
uv sync                            # install app dependencies
make start                         # auto-deploys, then starts
```

## License

MIT
