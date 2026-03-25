# create_agent Design

## Background

AgentForge is a meta-app that manages Socialware Apps. The chat tool itself only supports human-to-human communication. AgentForge's ability is to create an "AI member" in the chat room — a virtual user backed by an agent (Claude/Codex/Kimi).

The existing `create_role` skill only creates the Role primitive (SOUL.md) and registers it in flow.yaml. Scope, Flow, and Commitment are either skipped or optional. This produces an incomplete agent. Additionally, the name "create_role" is misleading — it sounds like RBAC role creation rather than creating a full agent participant.

## Decision Summary

| Decision | Choice |
|----------|--------|
| Rename | `create_role` → `create_agent` |
| Four primitives | All required, no optional |
| Config storage | Four primitives ARE the config (no separate config file) |
| Agent location | Within current app workspace (`agent/role/{name}/`) |
| Interaction model | Sequential guided questions (one per primitive) |
| Auto-online | Yes, agent auto-joins chat room after creation |
| Review flow | Removed (`agent_review` state machine deleted) |
| Scope structure | App-level + per-agent (agent scope cannot exceed app scope) |

## New Scope Structure

```
agent/scope/
├── SOUL.md                  ← App-level scope (overall boundary)
└── {agent-name}/
    └── SOUL.md              ← Agent-level scope (must be within app scope)
```

## create_agent Flow

### Trigger

User says "create agent", "create an AI assistant", "new agent", etc.

### Interaction (Sequential Guided)

```
User: "创建一个代码审查 Agent"
        ↓
Q1 — Role: name, adapter/model, identity description
        ↓
Q2 — Scope: working directories, boundaries
        ↓
Q3 — Flow: workflow steps (read what, analyze what, modify what)
        ↓
Q4 — Commitment: evaluation criteria and thresholds
        ↓
Generate all four primitives → deploy → auto-online (create session)
```

### File Operations

1. **Create `agent/role/{name}/SOUL.md`**

   ```markdown
   # {Display Name} Agent

   {Description}

   ## Identity
   - Role: {name}
   - Adapter: {claude|codex|kimi}
   - Model: {model-id}

   ## Responsibilities
   {Responsibilities from user description}
   ```

2. **Create `agent/scope/{name}/SOUL.md`**

   ```markdown
   # {name} Scope

   ## Working Directory
   - {directories}

   ## Boundaries
   - {boundaries}
   ```

3. **Update `agent/flow/flow.yaml`** — register action bindings for the new agent

4. **Create `agent/flow/{skill}/SKILL.md`** — if agent has specific skills, invoke `create_skill`

5. **Update `agent/commitment/eval.yaml`** — add evaluation criteria

   ```yaml
   commitments:
     {name}-{metric}:
       description: "{description}"
       metric: {metric_name}
       threshold: "{threshold}"
       debtor_role: {name}
   ```

6. **Run `./agent/deploy.sh`**

7. **Call `POST /session`** — auto-online, agent joins chat room

### Validation

- Agent name: `^[a-z0-9-]+$`
- Agent name must not conflict with existing roles
- Agent scope must not exceed app scope
- Adapter must be one of: claude, codex, kimicode
- All four primitive files must be non-empty

### Available APIs

```bash
# Check existing roles
curl http://localhost:8001/roles

# Check existing flows
curl http://localhost:8001/flows/registry

# Check app scope
curl http://localhost:8001/scope

# Check adapters
curl http://localhost:8001/adapters

# Create session (auto-online)
curl -X POST http://localhost:8001/session -d '{"role": "{name}", "adapter": "{adapter}"}'
```

## Removals

1. **Delete `agent_review` flow** — remove entire `flows.agent_review` from flow.yaml
2. **Delete review actions** — `review_config`, `approve_config`, `reject_config` (SKILL.md files + flow.yaml entries)
3. **Delete `reviewer` role** — `agent/role/reviewer/`

## Renames

4. **`create_role` → `create_agent`** — rename directory `agent/flow/create_role/` → `agent/flow/create_agent/`, rewrite SKILL.md
5. **flow.yaml action registration** — `create_role` → `create_agent`

## Modifications

6. **`agent/scope/` structure** — support app-level + per-agent scope files
7. **`deploy.sh`** — detect `agent/scope/{name}/SOUL.md` and merge into corresponding `.runtime/agents/{name}/`
8. **AgentForge Role SOUL.md** — update responsibilities from "Create roles" to "Create agents"
