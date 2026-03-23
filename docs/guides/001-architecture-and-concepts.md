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

## Four Primitives

Every Socialware App defines Agent behavior through four primitives:

| Primitive | Directory | Key File | Purpose |
|-----------|-----------|----------|---------|
| **Role** (Who) | agent/role/ | {name}.md | Agent identities + permissions |
| **Scope** (Where) | agent/scope/ | scope.md | App capability boundary + public identity |
| **Commitment** (What) | agent/commitment/ | constraints.yaml | Constraints on flow edges |
| **Flow** (How) | agent/flow/ | flow.yaml + SKILL.md | Actions the agent can execute |

## Three Built-in Roles

| Role | Purpose | Skills |
|------|---------|--------|
| `default` | App user | check_health |
| `dev` | Developer (env setup, project nav) | check_health, setup_claude, inspect |
| `evolver` | Diagnose + improve | diagnose, eval, improve, auto, inspect |

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

- **Room** = organizational group (team, project)
- **Workspace** = one app instance within a room
- Each workspace has its own `Makefile` (copied from `agent/Makefile.template` during `make create`)
- Each workspace has its own dependencies (pyproject.toml)
- `.runtime/` is gitignored — only exists inside workspaces, never at repo root
- Root Makefile only provides `make create` and `make test`
