# Socialwares

A Python framework for building Socialware Apps that can be installed into IRC channels.

## Concept

Socialware App = A web application that visualizes Agent interactions. Users see a normal interface + Chat box, with an Agent driving everything under the hood.

```
Traditional App:  UI → API → DB CRUD         (database visualization)
Socialware:       UI → Chat → Agent ↔ API    (Agent interaction visualization)
```

Each Socialware App is defined by four primitives:
- **Role** — Who (character description)
- **Scope** — Boundary (capability range)
- **Flow** — How (action + state machine)
- **Commitment** — Constraint (evaluation criteria)

## Installation

```bash
pip install socialwares
# or from git:
pip install git+https://github.com/ezagent42/Socialwares.git
```

## Quickstart

### 1. Create a project

```bash
socialwares new my-app
cd my-app
```

Generated project structure:

```
my-app/
├── socialware.py           ← App declaration (relationship definitions)
├── agent/                  ← Four primitives content
│   ├── role/               ← Role descriptions (.md)
│   ├── scope/              ← Capability boundary (.md)
│   └── flow/               ← Skill directories (business + evolve)
├── src/api.py              ← FastAPI backend
├── app/                    ← Frontend UI
└── pyproject.toml
```

### 2. Define the App

Edit `socialware.py` (relationship definitions):

```python
from socialwares import App

app = App("my-app")

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("evolver", file="agent/role/evolver.md")

app.action("check_health", role=["default"])
app.action("evolve_structure_check", role=["evolver"])

flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed")
flow.transition("draft", "submit_task", "submitted", role=["default"])

app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
)
```

Edit the content files under `agent/` (role descriptions, SKILL.md, etc.).

### 3. Compile + Start

```bash
socialwares deploy                    # compile four primitives → .runtime/
uvicorn src.api:app --port 8001       # start backend
socialwares start --role default      # start agent
```

### 4. Evolve

```bash
socialwares start --role evolver      # start evolver
# "check structure" / "diagnose" / "evaluate" / "improve"
```

## Installing into an IRC Channel

```bash
# install (default path: .socialware/workspace/{channel}/apps/{app}/)
socialwares install git@github.com:xxx/my-app.git --channel "#support"

# or install to a custom path
socialwares install git@github.com:xxx/my-app.git --channel "#support" --path /opt/agents/my-app

# assign roles
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign alice-evolver  --role evolver  --channel "#support"

# uninstall
socialwares uninstall my-app --channel "#support"
```

## Four Primitives

| Primitive | Directory | Definition |
|-----------|-----------|------------|
| **Role** | `agent/role/*.md` | Markdown files |
| **Scope** | `agent/scope/scope.md` | Markdown file |
| **Flow** | `agent/flow/*/SKILL.md` | One skill directory per action; state machine declared in `socialware.py` |
| **Commitment** | `socialware.py` | Python declarative |

**Relationship definitions** in `socialware.py`: action → role, state machine, constraints.
**Content definitions** in `agent/` files: role descriptions, SKILL.md.

## Evolver

A regular role with 5 built-in evolve actions (structure_check / api_check / session_diagnose / improve / auto). These skills are provided by the framework and automatically symlinked into the project at deploy time. To add custom checks, add a skill directory and register an action.

## CLI

| Command | Function |
|---------|----------|
| `socialwares new <name>` | Create a project from template |
| `socialwares new <name> --from <source>` | Create a project from git URL or local path |
| `socialwares deploy` | Compile four primitives → `.runtime/` |
| `socialwares start --role <role>` | Start agent |
| `socialwares eject <skill>` | Copy a built-in skill to project for customization |
| `socialwares install <url> --channel <ch> [--path <dir>]` | Install to channel |
| `socialwares assign <agent> --role <role> --channel <ch>` | Assign role |
| `socialwares uninstall <app> --channel <ch>` | Uninstall |
| `socialwares list` | View installed apps |

## Documentation

- [Concepts](docs/guides/001-concepts.md)
- [Four Primitives](docs/guides/002-four-primitives.md)
- [Quickstart](docs/guides/003-quickstart.md)
- [Built-in Roles: Dev & Evolver](docs/guides/004-builtin-roles.md)
- [Migration Guide (v0.1→v0.2)](docs/guides/005-migration-guide.md)
