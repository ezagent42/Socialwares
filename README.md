# Socialwares

Agent-first Socialware Web App — built on the RSCF model (Role, Scope, Commitment, Flow).

## Structure

```
Socialwares/
├── api/     FastAPI backend (Python, uv)
├── app/     Next.js frontend (TypeScript, pnpm)
└── agent/   Agent logic placeholder (pending interface definition)
```

## Quick Start

```bash
make install   # install all dependencies
cp api/.env.example api/.env
cp app/.env.local.example app/.env.local
# fill in ANTHROPIC_API_KEY and AUTH_SECRET
make dev       # start api :8000 and app :3000
```

## Architecture

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full architecture principles.

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 + App Router + shadcn/ui + Tailwind |
| Auth | Auth.js v5 (Credentials) |
| Backend | FastAPI + SQLAlchemy async + SQLite |
| Agent | Anthropic SDK via `api/agent_bridge.py` |
