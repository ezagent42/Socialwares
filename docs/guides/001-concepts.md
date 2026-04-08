# Concepts

## What is Socialwares?

Socialwares is a Python framework (pip package) for building **Socialware Apps** — web applications where an AI Agent drives the user experience through a chat interface.

```
Traditional App:  UI → API → DB CRUD         (database visualization)
Socialware App:   UI → Chat → Agent ↔ API    (Agent interaction visualization)
```

Users see a normal web interface with a chat box. Under the hood, an Agent reads structured instructions, calls APIs, manages state transitions, and responds through the chat. The framework provides the tooling to define, compile, launch, and evolve these Agent-driven applications.

## Framework vs App

| Concept | Description |
|---------|-------------|
| **socialwares** (pip package) | Python framework + CLI. Provides compiler, adapters, runner. |
| **Socialware App** (user project) | A concrete application: `socialware.py` + `agent/` + `src/` |

Analogy: `Django` (pip package) → Django project / `Rails` (gem) → Rails project.

## Four Primitives

Every Socialware App defines Agent behavior through four primitives:

| Primitive | Answers | Defined In | Content In |
|-----------|---------|-----------|------------|
| **Role** | Who? | `socialware.py` | `agent/role/*.md` |
| **Scope** | Where? | `socialware.py` | `agent/scope/scope.md` |
| **Flow** | How? | `socialware.py` | `agent/flow/*/SKILL.md` |
| **Commitment** | What standard? | `socialware.py` | compiled to `.runtime/commitment.yaml` |

**Relationship definitions** live in `socialware.py` (declarative Python API).
**Content definitions** live in `agent/` files (Markdown, YAML).

`socialwares deploy` merges both into `.runtime/` — the artifacts the Agent actually reads.

## Project Structure

```
my-app/
├── socialware.py              ← App declaration (relationship definitions)
├── agent/                     ← Content files (four primitives)
│   ├── role/                  ← Role descriptions (one .md per role)
│   ├── scope/                 ← Capability boundary
│   │   └── scope.md
│   ├── flow/                  ← Skills (one directory per action)
│   │   └── check_health/
│   │       ├── SKILL.md       ← Execution instructions for the Agent
│   │       ├── scripts/       ← Automation scripts
│   │       └── references/    ← Reference materials
│   └── commitment/
│       └── README.md          ← Explains that commitments are in socialware.py
├── src/api.py                 ← FastAPI backend
├── app/                       ← Frontend UI
└── pyproject.toml             ← Project config [tool.socialwares]
```

## Compile Products

`socialwares deploy` reads `socialware.py` + `agent/` → generates `.runtime/`:

```
.runtime/
├── agents/
│   ├── default/
│   │   ├── SOUL.md            ← scope + role merged (Agent system prompt)
│   │   └── .claude/
│   │       ├── skills/        ← symlinks to actions (user from agent/flow/ + built-in from framework)
│   │       └── hooks/         ← log_prompt.py, log_tool.py
│   └── evolver/
│       ├── SOUL.md
│       └── .claude/skills/    ← evolve_*/ skills
├── flow.yaml                  ← generated from socialware.py flow definitions
├── commitment.yaml            ← generated from socialware.py commitment definitions
└── compile_manifest.yaml      ← source traceability
```

The compiler treats all roles equally — evolver and default use identical compilation logic.

## Built-in vs User Skills

| Type | Examples | Where they live | Copied to project? |
|------|---------|----------------|-------------------|
| **Built-in** (framework-managed) | `evolve_*`, `dev_*`, `inspect`, `setup_claude` | Framework package | No — resolved directly at deploy time |
| **User** (project-managed) | `check_health`, `create_task`, etc. | `agent/flow/` in project | Yes — created by user |

Framework upgrades automatically update built-in skills. User skills remain under the developer's control. To customize a built-in skill, use `socialwares eject <skill>` to copy it into your project.

## Adapters

Socialwares supports multiple LLM backends through adapters:

| Adapter | Prompt File | Skills Dir | Hooks |
|---------|------------|-----------|-------|
| `claude` (default) | `SOUL.md` | `.claude/skills/` | `.claude/hooks/` |
| `codex` | `AGENTS.md` | `.agents/skills/` | `.codex/hooks/` |
| `kimi` | `AGENTS.md` | `.agents/skills/` | (none) |

Configure the default adapter in `pyproject.toml`:

```toml
[tool.socialwares]
adapter = "claude"        # or "codex", "kimi"
agent_dir = "agent"       # default; change to use a different directory
```

Override per-launch: `socialwares start --role default --adapter codex`

## CLI Overview

| Command | Purpose |
|---------|---------|
| `socialwares new <name>` | Create a new project from template |
| `socialwares new <name> --from <source>` | Create from git URL or local path |
| `socialwares deploy` | Compile four primitives → `.runtime/` |
| `socialwares start --role <role>` | Launch Agent locally (TUI / tmux / SDK) |
| `socialwares eject <skill>` | Copy a built-in skill to project for customization |
| `socialwares install <git-url> --channel <ch> [--subdir <dir>] [--path <dir>]` | Install App to an IRC channel |
| `socialwares assign <agent> --role <role> --channel <ch>` | Assign role to an existing Agent |
| `socialwares uninstall <app> --channel <ch>` | Uninstall App from channel |
| `socialwares list` | List installed Apps |

## Two Startup Modes

### Local Development: `socialwares start`

Creates a new Agent process with role-specific configuration.

```bash
socialwares start --role default                    # single role (TUI)
socialwares start --role default,reviewer,evolver   # multi-role (tmux panes)
socialwares start --role default --prompt "..."     # SDK mode (non-interactive)
```

### IRC Channel: `socialwares install` + `socialwares assign`

Deploys to an existing Agent infrastructure. Does not create new processes — only configures.

```bash
socialwares install git@github.com:xxx/my-app.git --channel "#support"
socialwares assign alice-support --role default --channel "#support"
```

| Command | What it does | Starts what |
|---------|-------------|-------------|
| `start` | Creates Agent locally | Adapter process (Claude Code, etc.) |
| `install` | Clones repo + compiles | Nothing — only clones + deploys |
| `assign` | Configures existing Agent | Nothing — only merges config + symlinks |
| `uninstall` | Removes App files + symlinks | Nothing — only cleans files |
