# Architecture and Concepts

## What is a Socialware App?

A web application for Agent interaction visualization. Users see a normal UI + Chat box; Agents drive everything underneath.

> Traditional App: UI → API → DB (database CRUD visualization)
> Socialware: UI → Chat → Agent (Agent interaction visualization)

## Runtime Model

```
User → Login → Session (role assigned)
  → Chat message → Backend receives
  → Backend spawns agent with user's role
  → Agent processes → calls API → state transitions
  → API checks constraints → response back to chat
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
│   ├── role/                     ← Flat .md files (one per role)
│   │   ├── default.md
│   │   ├── dev.md
│   │   └── evolver.md
│   ├── scope/
│   │   └── scope.md              ← App capability boundary
│   ├── commitment/
│   │   └── commitment.yaml      ← Unified schema: from/to/condition/on_violation
│   ├── flow/
│   │   ├── flow.yaml             ← Action registry (roles → actions)
│   │   ├── check_health/SKILL.md
│   │   ├── setup_claude/SKILL.md
│   │   ├── inspect/SKILL.md
│   │   ├── evolve_diagnose/SKILL.md + scripts/diagnose.py
│   │   ├── evolve_eval/SKILL.md + scripts/run_eval.py + eval_cases.yaml
│   │   ├── evolve_improve/SKILL.md
│   │   └── evolve_auto/SKILL.md + scripts/run_auto.py
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
├── .socialware/workspace/        ← Workspace instances
├── tests/
├── docs/
│   ├── discuss/commitment.md     ← Commitment design discussion
│   ├── designs/
│   └── guides/ (001-005)
└── pyproject.toml
```

## Four Primitives

Every Socialware App defines Agent behavior through four primitives:

| Primitive | Directory | Key File | Purpose |
|-----------|-----------|----------|---------|
| **Role** (Who) | agent/role/ | {name}.md | Agent identities + permissions |
| **Scope** (Where) | agent/scope/ | scope.md | App capability boundary + public identity |
| **Commitment** (What) | agent/commitment/ | commitment.yaml | Constraints on flow edges |
| **Flow** (How) | agent/flow/ | flow.yaml + SKILL.md | Actions the agent can execute |

## Three Built-in Roles

| Role | Purpose | Skills |
|------|---------|--------|
| `default` | App user | check_health |
| `dev` | Developer (env setup, project nav) | check_health, setup_claude, inspect |
| `evolver` | Diagnose + improve | check_health, inspect, diagnose, eval, improve, auto |

## Progressive Growth

```
P1 Define Agent → P2 Refine Flow → P3 Refine Commitment → P4 Expand Scope → P5 Expand Role
                                                                               ↓
                                         P0 ← Reach boundary ← New App or /zchat
```

Each phase: edit agent/ → deploy → grow src/ → repeat.
See [designs/progressive-dev-guide-example.md](../designs/progressive-dev-guide-example.md) for detailed example.

## Workspace Model

Each workspace is a self-contained copy of the template. Deploy and start only happen inside workspaces — never at the repo root.

```
.socialware/workspace/
└── {room}/{app}/              ← cd here to develop
    ├── Makefile               ← make deploy / make start / make clean
    ├── src/                   ← your app code
    ├── agent/                 ← your four primitives
    │   └── Makefile.template  ← source for workspace Makefile
    ├── .runtime/              ← deploy output (gitignored)
    └── pyproject.toml         ← independent dependencies
```

- **Room** = organizational group (team, project) — just a directory for grouping
- **App** = self-contained development unit (`{room}/{app}/`) — has its own Makefile, pyproject.toml, agent/, src/, .runtime/
- Each app has its own `Makefile` (copied from `agent/Makefile.template` during `make create`)
- Each app has its own dependencies (`pyproject.toml` + `.venv/`)
- `.runtime/` is gitignored — only exists inside apps, never at repo root
- Root Makefile only provides `make create` and `make test` (template-level tests for contributors)

## Makefile Split

| Makefile | Location | Commands |
|----------|----------|----------|
| Root Makefile | `socialwares/Makefile` | `make create`, `make test` |
| Workspace Makefile | `.socialware/workspace/{room}/{app}/Makefile` | `make deploy`, `make start`, `make test`, `make clean` |
| Makefile.template | `agent/Makefile.template` | Source copied to workspace during `make create` |
