# create_agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `create_role` with `create_agent` — a complete agent creation flow that generates all four primitives, supports per-agent scope, removes the review workflow, and auto-onlines the agent.

**Architecture:** Modify agentforge's flow registry, SKILL.md files, deploy.sh scope merging, and agentforge role identity. All changes are within `.socialware/workspace/agent/agentforge/`.

**Tech Stack:** Bash (deploy.sh), YAML (flow.yaml, eval.yaml), Markdown (SOUL.md, SKILL.md)

---

### Task 1: Remove reviewer role and review workflow

**Files:**
- Delete: `.socialware/workspace/agent/agentforge/agent/role/reviewer/SOUL.md`
- Delete: `.socialware/workspace/agent/agentforge/agent/flow/review_config/SKILL.md`
- Delete: `.socialware/workspace/agent/agentforge/agent/flow/approve_config/SKILL.md`
- Delete: `.socialware/workspace/agent/agentforge/agent/flow/reject_config/SKILL.md`
- Modify: `.socialware/workspace/agent/agentforge/agent/flow/flow.yaml`

**Step 1: Delete reviewer role directory**

Run: `rm -rf .socialware/workspace/agent/agentforge/agent/role/reviewer`

**Step 2: Delete review skill directories**

Run:
```bash
rm -rf .socialware/workspace/agent/agentforge/agent/flow/review_config
rm -rf .socialware/workspace/agent/agentforge/agent/flow/approve_config
rm -rf .socialware/workspace/agent/agentforge/agent/flow/reject_config
```

**Step 3: Remove agent_review flow and review actions from flow.yaml**

Remove the entire `flows.agent_review` block (lines 7-15) and replace with empty flows:
```yaml
flows: {}
```

Remove these three entries from `direct_actions`:
```yaml
  - action: review_config
    role: [reviewer]
    description: "Review a pending Agent configuration"

  - action: approve_config
    role: [reviewer]
    description: "Approve a reviewed configuration"

  - action: reject_config
    role: [reviewer]
    description: "Reject a configuration and send back for revision"
```

**Step 4: Verify flow.yaml is valid YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.socialware/workspace/agent/agentforge/agent/flow/flow.yaml'))"`
Expected: No error

**Step 5: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/role/reviewer \
        .socialware/workspace/agent/agentforge/agent/flow/review_config \
        .socialware/workspace/agent/agentforge/agent/flow/approve_config \
        .socialware/workspace/agent/agentforge/agent/flow/reject_config \
        .socialware/workspace/agent/agentforge/agent/flow/flow.yaml
git commit -m "refactor: remove reviewer role and agent_review workflow"
```

---

### Task 2: Rename create_role to create_agent

**Files:**
- Rename: `.socialware/workspace/agent/agentforge/agent/flow/create_role/` → `.socialware/workspace/agent/agentforge/agent/flow/create_agent/`
- Modify: `.socialware/workspace/agent/agentforge/agent/flow/flow.yaml`

**Step 1: Rename directory**

Run:
```bash
mv .socialware/workspace/agent/agentforge/agent/flow/create_role \
   .socialware/workspace/agent/agentforge/agent/flow/create_agent
```

**Step 2: Update flow.yaml — change action name**

Replace in `direct_actions`:
```yaml
  - action: create_role
    role: [agentforge]
    description: "Create a new Agent role with SOUL.md"
```
With:
```yaml
  - action: create_agent
    role: [agentforge]
    description: "Create a complete Agent with four primitives, then auto-online"
```

**Step 3: Verify flow.yaml**

Run: `python -c "import yaml; yaml.safe_load(open('.socialware/workspace/agent/agentforge/agent/flow/flow.yaml'))"`
Expected: No error

**Step 4: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/flow/create_role \
        .socialware/workspace/agent/agentforge/agent/flow/create_agent \
        .socialware/workspace/agent/agentforge/agent/flow/flow.yaml
git commit -m "refactor: rename create_role to create_agent"
```

---

### Task 3: Rewrite create_agent SKILL.md

**Files:**
- Modify: `.socialware/workspace/agent/agentforge/agent/flow/create_agent/SKILL.md`

**Step 1: Rewrite SKILL.md with full four-primitive creation flow**

Replace entire contents with:

```markdown
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
```

**Step 2: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/flow/create_agent/SKILL.md
git commit -m "feat: rewrite create_agent SKILL.md with full four-primitive flow"
```

---

### Task 4: Add per-agent scope support to directory structure

**Files:**
- Modify: `.socialware/workspace/agent/agentforge/agent/scope/SOUL.md` (keep as app-level)
- Create: `.socialware/workspace/agent/agentforge/agent/scope/.gitkeep` (placeholder for agent subdirs)

**Step 1: Verify existing app-level scope is unchanged**

Read `agent/scope/SOUL.md` — it should remain as the app-level scope. No changes needed to this file.

**Step 2: Commit** (no-op if nothing changed, skip if so)

---

### Task 5: Update deploy.sh to merge per-agent scope

**Files:**
- Modify: `.socialware/workspace/agent/agentforge/agent/deploy.sh:113-120`

**Step 1: Update SOUL.md merge logic in deploy.sh**

Replace the current merge block (lines 113-120):
```bash
    # Merge SOUL.md: scope/SOUL.md + role/{name}/SOUL.md
    {
        cat "$AGENT_DIR/scope/SOUL.md" 2>/dev/null || true
        echo ""
        echo "---"
        echo ""
        cat "$role_dir/SOUL.md" 2>/dev/null || true
    } > "$role_runtime/SOUL.md"
```

With:
```bash
    # Merge SOUL.md: app scope + agent scope (if exists) + role identity
    {
        cat "$AGENT_DIR/scope/SOUL.md" 2>/dev/null || true
        if [ -f "$AGENT_DIR/scope/$role_name/SOUL.md" ]; then
            echo ""
            echo "---"
            echo ""
            cat "$AGENT_DIR/scope/$role_name/SOUL.md"
        fi
        echo ""
        echo "---"
        echo ""
        cat "$role_dir/SOUL.md" 2>/dev/null || true
    } > "$role_runtime/SOUL.md"
```

**Step 2: Test deploy**

Run: `cd .socialware/workspace/agent/agentforge && ./agent/deploy.sh`
Expected: "Deploy complete." with no errors

**Step 3: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/deploy.sh
git commit -m "feat: deploy.sh merges per-agent scope into SOUL.md"
```

---

### Task 6: Update root template deploy.sh

**Files:**
- Modify: `agent/deploy.sh:113-120`

**Step 1: Apply same per-agent scope merge change to root template**

Same edit as Task 5, applied to the root `agent/deploy.sh` so new workspaces get the updated logic.

**Step 2: Test deploy on root**

Run: `./agent/deploy.sh`
Expected: "Deploy complete." with no errors

**Step 3: Commit**

```bash
git add agent/deploy.sh
git commit -m "feat: root template deploy.sh supports per-agent scope"
```

---

### Task 7: Update agentforge Role SOUL.md

**Files:**
- Modify: `.socialware/workspace/agent/agentforge/agent/role/agentforge/SOUL.md`

**Step 1: Update responsibilities**

Replace entire contents with:

```markdown
# AgentForge Agent

You are the AgentForge management agent. Your job is to create and manage Agent configurations for Socialware Apps.

## Identity

- Role: agentforge
- Permissions: Create/edit/delete files in agent/ and src/ directories

## Responsibilities

1. **Create agents** — Generate complete four-primitive configurations (Role, Scope, Flow, Commitment) for new Agents, then auto-online them
2. **Create skills** — Generate `flow/{name}/SKILL.md` files + corresponding API endpoints in `src/app.py` + register actions in `flow/flow.yaml`
3. **Edit primitives** — Modify existing SOUL.md, SKILL.md, flow.yaml, eval.yaml, scope/SOUL.md files
4. **Export bundles** — Package an agent and its skills into a portable bundle directory
5. **Import bundles** — Import a bundle into the current project, handling conflicts

## Core Pattern

Every agent you create has four primitives:
1. `role/{name}/SOUL.md` — WHO: agent identity, adapter, model
2. `scope/{name}/SOUL.md` — WHERE: working directories and boundaries
3. `flow/{skill}/SKILL.md` + `flow/flow.yaml` — HOW: workflow and action registry
4. `commitment/eval.yaml` — WHAT: evaluation criteria and thresholds

After creating/modifying files, always run `./agent/deploy.sh` to compile changes.

## Boundaries

- Only operate on `agent/` and `src/` directories
- Do not modify `.runtime/` directly (deploy.sh generates it)
- Do not manage Agent processes (auto-online via API after deploy)
- Do not evaluate Agent performance (that's the commitment's job)
```

**Step 2: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/role/agentforge/SOUL.md
git commit -m "docs: update agentforge role to reflect create_agent workflow"
```

---

### Task 8: Update agentforge Scope SOUL.md

**Files:**
- Modify: `.socialware/workspace/agent/agentforge/agent/scope/SOUL.md`

**Step 1: Update capabilities to reflect new naming**

Replace entire contents with:

```markdown
# AgentForge

Agent creation and management platform. Automates four-primitive file operations for Socialware Apps.

## Capabilities

- Create Agents (complete four-primitive configuration + auto-online)
- Create Agent skills (SKILL.md + API endpoint + flow.yaml registration)
- Edit existing four-primitive files (role, scope, commitment, flow)
- Export Agent bundles (package agent + skills for sharing)
- Import Agent bundles (merge into current project)
- Evaluate commitments (run eval metrics, generate reports)
- Multi-workspace management (create, list, sync, delete)
- Agent configuration optimization (Evolve)
- Health check (/health)

## Boundaries

- Manages files in agent/ and src/ only
- Does not manage Agent runtime processes
- Does not evaluate Agent performance directly (uses eval.yaml definitions)
```

**Step 2: Commit**

```bash
git add .socialware/workspace/agent/agentforge/agent/scope/SOUL.md
git commit -m "docs: update agentforge scope to reflect create_agent naming"
```

---

### Task 9: Run deploy and verify

**Step 1: Run deploy**

Run: `cd .socialware/workspace/agent/agentforge && ./agent/deploy.sh`
Expected: Deploy complete with roles: agentforge, default, dev (no reviewer)

**Step 2: Verify reviewer is gone**

Run: `ls .socialware/workspace/agent/agentforge/.runtime/agents/`
Expected: `agentforge  default  dev` (no reviewer)

**Step 3: Verify create_agent skill is linked**

Run: `ls .socialware/workspace/agent/agentforge/.runtime/agents/agentforge/.claude/skills/`
Expected: `create_agent` in list (not `create_role`)

**Step 4: Commit (if deploy generated changes)**

No commit needed — `.runtime/` should be gitignored.
