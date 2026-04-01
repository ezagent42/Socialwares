---
name: inspect
description: "Show project structure, four primitives, development workflow, and conventions"
---

# Inspect Project

## Trigger

User says "inspect", "show structure", "how does this work", "project layout", "dev guide" etc.

## Project Structure

```
workspace/                            ← all dev happens here (cd into workspace)
├── Makefile                          ← make deploy / make start / make clean
├── app/                              ← Frontend (Next.js: UI + Chat)
├── src/                              ← Backend (FastAPI)
│   ├── app.py                        ← API entry point
│   └── start_agent.py                ← SDK mode launch
├── agent/                            ← Four primitives + toolchain
│   ├── role/                         ← Who: {name}.md files
│   ├── scope/                        ← Where: scope.md
│   ├── commitment/                   ← What: commitment.yaml
│   ├── flow/                         ← How: flow.yaml + {action}/SKILL.md
│   ├── deploy.sh                     ← Compile → .runtime/
│   ├── start.sh                      ← Launch agent
│   └── adapters/                     ← Claude/Codex/Kimi
├── .runtime/                         ← Deploy output (gitignored, workspace-only)
│   ├── data/prompts/                 ← Hook logs (user prompts + tool calls)
│   ├── data/sessions/                ← SDK full conversations
│   ├── data/evolve/                  ← Evolver output
│   │   ├── reports/                  ← Unified reports (check/eval/diagnose/auto_test)
│   │   ├── violations/               ← Commitment violations
│   │   └── auto_sessions/            ← Auto-test generated conversations
│   └── agents/{role}/                ← Per-role $PROJECT_DIR
└── pyproject.toml                    ← Independent dependencies
```

## Four Primitives

| Primitive | Directory | Key File | Purpose |
|-----------|-----------|----------|---------|
| **Role** | agent/role/ | {name}.md | Agent identity + permissions |
| **Scope** | agent/scope/ | scope.md | App capability boundary |
| **Commitment** | agent/commitment/ | commitment.yaml | Evaluation standards on flow edges |
| **Flow** | agent/flow/ | flow.yaml + SKILL.md | Actions + how to execute |

## Development Workflow

```
1. Edit four primitives (agent/)
2. make deploy (or ./agent/deploy.sh)
3. make start ROLE=default (or ./agent/start.sh --role default)
4. Test in Claude Code
5. Repeat
```

## Adding a New Skill

```bash
mkdir agent/flow/my_action
vim agent/flow/my_action/SKILL.md
# Add to flow.yaml: - { action: my_action, role: [default], description: "..." }
make deploy
```

## Adding a New Role

```bash
vim agent/role/admin.md
# Add role to flow.yaml action permissions
make deploy
```

## Key Commands

```bash
# From within workspace:
make deploy              # Compile four primitives → .runtime/
make start ROLE=default  # Launch agent (auto-deploys if needed)
make start ROLE=evolver  # Launch evolver
make clean               # Remove .runtime/

# From repo root (template-level only):
make create ROOM=x APP=y DESC="..."  # Create new workspace
make test                             # Run template tests
```
