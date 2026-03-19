# Socialwares — Claude Code Project Guide

## Project Overview

Agent-first Socialware Web App built on the RSCF model (Role, Scope, Commitment, Flow).

## Monorepo Structure

```
Socialwares/
├── api/     FastAPI backend (Python 3.12+, uv, SQLAlchemy async + SQLite)
├── app/     Next.js 15 frontend (TypeScript, pnpm, shadcn/ui, Tailwind)
├── agent/   Agent logic placeholder (RSCF: Role, Scope, Commitment, Flow)
```

## Package Managers — STRICT

- **Python**: `uv` only. NEVER use `pip` or `pip3`.
- **JavaScript**: `pnpm` only. NEVER use `npm` or `npx`.

## Common Commands

| Task | Command |
|---|---|
| Install all deps | `make install` |
| Dev servers (api:8000 + app:3000) | `make dev` |
| API only | `cd api && uv run uvicorn main:app --reload --port 8000` |
| App only | `pnpm --filter app run dev` |
| Lint all | `make lint` |
| Lint API | `cd api && uv run ruff check .` |
| Lint App | `pnpm --filter app run lint` |
| Run API tests | `cd api && uv run pytest` |
| Build App | `pnpm --filter app run build` |

## Architecture Rules

1. **API is an extension of Agent internals** — business logic belongs in `agent_bridge.py` (and eventually `agent/`), not in route handlers.
2. **Thin API Rule** — new logic starts in `agent_bridge.py`, promote to endpoint only when it needs independent access control/caching/webhooks.
3. **Workspace isolation** — each Room maps to `.socialware-workspace/{room.name}/`. Agents must be scoped to this path. Room names: `^[a-z0-9-]+$`.

## RSCF Mapping

| Primitive | Implementation |
|---|---|
| Arena (Scope) | `Room` — task boundaries + workspace path isolation |
| Flow | `AgentTask.status` — open → in_progress → submitted → completed |
| Commitment | `POST /agents/invoke` — prompt in, result + status out |
| Role | `agent/Role/` — pending definition |

## Commit Format

```
type(scope): description
```

- **Scopes**: `api`, `app`, `agent`, `docs`
- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Tech Stack Details

### API (`api/`)
- FastAPI, SQLAlchemy 2.0 async, aiosqlite, Pydantic v2
- Auth: python-jose (JWT) + passlib (bcrypt)
- Agent: Anthropic SDK
- Lint: ruff (line-length=100)
- Test: pytest + pytest-asyncio (asyncio_mode=auto)

### App (`app/`)
- Next.js 15 (App Router, Turbopack dev)
- React 19, TypeScript 5
- Auth: next-auth v5 (Credentials provider)
- UI: shadcn/ui + Radix UI + Tailwind CSS 3.4
- Lint: eslint + eslint-config-next
