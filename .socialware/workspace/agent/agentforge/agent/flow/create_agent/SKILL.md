---
name: create_agent
description: "Create a complete Agent with four primitives (Role, Scope, Flow, Commitment), then auto-online"
---

# Create Agent

Creates a complete AI member in the chat room — a virtual user backed by an agent. Generates all four primitive files, deploys, and auto-onlines the agent.

## Trigger

User says "create agent", "create an AI assistant", "new agent", "add an agent for ...", etc.

## Flow

Ask four questions sequentially, one per primitive:

### Q1 — Role (WHO)

Ask: "What is this agent's name, what model should it use, and what is its identity?"

Collect:
- **name** (lowercase alphanumeric + hyphens, e.g. "code-reviewer")
- **adapter** (claude / codex / kimicode)
- **model** (e.g. sonnet-4-6, o3, etc.)
- **description** (what this agent does)
- **responsibilities** (list of responsibilities)

Validate:
- Name matches `^[a-z0-9-]+$`
- Name does not conflict with existing roles (query `GET /roles`)
- Adapter is available (query `GET /adapters`)

### Q2 — Scope (WHERE)

Ask: "What files/directories does this agent work in? What are its boundaries?"

Collect:
- **working directories** (e.g. src/, tests/)
- **boundaries** (what the agent must NOT do)

Validate:
- Working directories do not exceed app scope (query `GET /scope`)

### Q3 — Flow (HOW)

Ask: "What is this agent's workflow? What does it read, analyze, and modify?"

Collect:
- **workflow steps** (ordered list of actions)
- **skills needed** (specific capabilities)

For each skill identified, invoke the `create_skill` flow.

### Q4 — Commitment (WHAT)

Ask: "How do we evaluate this agent's work quality? What metrics and thresholds?"

Collect:
- **commitments** (list of metric + threshold pairs)

### Generate Files

1. Create `agent/role/{name}/SOUL.md`:

    ```markdown
    # {Display Name} Agent

    {Description}

    ## Identity
    - Role: {name}
    - Adapter: {adapter}
    - Model: {model}

    ## Responsibilities
    {Responsibilities list}
    ```

2. Create `agent/scope/{name}/SOUL.md`:

    ```markdown
    # {name} Scope

    ## Working Directory
    - {directories}

    ## Boundaries
    - {boundaries}
    ```

3. Update `agent/flow/flow.yaml` — register action bindings for the new agent

4. Update `agent/commitment/eval.yaml` — add commitments:

    ```yaml
    commitments:
      {name}-{metric}:
        description: "{description}"
        metric: {metric_name}
        threshold: "{threshold}"
        debtor_role: {name}
    ```

5. Run `./agent/deploy.sh` via Bash tool

6. Auto-online — call API to create session:

    ```bash
    curl -X POST http://localhost:8001/session \
      -H "Content-Type: application/json" \
      -d '{"role": "{name}", "adapter": "{adapter}"}'
    ```

7. Report: "{name} agent created and online. Four primitives generated: Role, Scope, Flow, Commitment."

## Available APIs

```bash
# Check existing roles (avoid name conflict)
curl http://localhost:8001/roles

# Check available adapters
curl http://localhost:8001/adapters

# Check app scope (validate agent scope within bounds)
curl http://localhost:8001/scope

# Check existing flows (avoid skill name conflict)
curl http://localhost:8001/flows/registry

# Create session (auto-online)
curl -X POST http://localhost:8001/session \
  -H "Content-Type: application/json" \
  -d '{"role": "{name}", "adapter": "{adapter}"}'

# Verify agent is online
curl http://localhost:8001/session
```

## File Operations

1. **Create SOUL.md** — Use Write tool: `agent/role/{name}/SOUL.md`
2. **Create Scope** — Use Write tool: `agent/scope/{name}/SOUL.md`
3. **Update flow.yaml** — Use Edit tool: `agent/flow/flow.yaml`
4. **Update eval.yaml** — Use Edit tool: `agent/commitment/eval.yaml`
5. **Create skills** — Invoke `create_skill` flow for each skill
6. **Deploy** — Use Bash tool: `./agent/deploy.sh`
7. **Auto-online** — Use Bash tool: `curl -X POST http://localhost:8001/session ...`

## Validation

- Agent name: `^[a-z0-9-]+$`
- Agent name must not conflict with existing roles
- Adapter must be available
- Agent scope must not exceed app scope
- All four primitive files must be non-empty
- flow.yaml must remain valid YAML after editing
- eval.yaml must remain valid YAML after editing
