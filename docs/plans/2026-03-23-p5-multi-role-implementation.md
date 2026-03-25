# P5 扩充 Role — 多 Role + 状态机协作 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multiple roles (reviewer, admin) to AgentForge with flow.yaml state machine defining role-based collaboration workflows (e.g. Agent creation requires reviewer approval).

**Architecture:** New roles are just `role/{name}/SOUL.md` directories. State machine defined in flow.yaml `flows:` section with transitions mapping actions to roles. Backend adds `/flows/state` endpoint to track and enforce state transitions. deploy.sh already handles role-based skill allocation via flow.yaml.

**Tech Stack:** Python (FastAPI, yaml), pytest

**Reference:** `docs/plans/2026-03-19-socialware-framework-design.md` (第六部分: Phase 5)

---

### Task 1: Create reviewer role

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/role/reviewer/SOUL.md`
- Test: `tests/test_agentforge.py`

**Step 1: Write the failing test**

Add to `tests/test_agentforge.py`:

```python
class TestP5MultiRole:
    """Test P5 multi-role setup."""

    def test_reviewer_role_exists(self):
        assert (AGENTFORGE_DIR / "agent" / "role" / "reviewer").is_dir()

    def test_reviewer_soul_md_exists(self):
        soul = AGENTFORGE_DIR / "agent" / "role" / "reviewer" / "SOUL.md"
        assert soul.exists()
        content = soul.read_text()
        assert "review" in content.lower()
```

**Step 2: Run test to verify it fails**

**Step 3: Create reviewer SOUL.md**

Create `.socialware/workspace/my-team/agentforge/agent/role/reviewer/SOUL.md`:

```markdown
# Reviewer Agent

You are the configuration reviewer for AgentForge. Your job is to review Agent configurations created by the agentforge role before they go live.

## Identity

- Role: reviewer
- Permissions: Read agent/ files, approve/reject configurations

## Responsibilities

1. **Review** — Examine new role SOUL.md for completeness and correctness
2. **Review** — Check SKILL.md files follow the three-piece pattern
3. **Review** — Verify flow.yaml registrations are correct
4. **Approve** — Mark configurations as approved for deployment
5. **Reject** — Send configurations back for revision with feedback

## Boundaries

- Cannot create or modify agent/ files (only agentforge role can)
- Can only approve or reject
- Must provide feedback when rejecting
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/role/reviewer/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add reviewer role for P5 multi-role collaboration"
```

---

### Task 2: Create review and approve/reject Skills

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/review_config/SKILL.md`
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/approve_config/SKILL.md`
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/reject_config/SKILL.md`

**Step 1: Create Skills**

`review_config/SKILL.md`:
```markdown
---
name: review_config
description: "Review a pending Agent configuration before deployment"
---

# Review Configuration

## Trigger

User says "review", "check config", "review agent", etc.

## Flow

1. List pending configurations (state = "draft")
2. Read the SOUL.md and SKILL.md files for the pending role
3. Check completeness:
   - SOUL.md has Identity, Responsibilities, Boundaries
   - Each SKILL.md has frontmatter (name, description)
   - flow.yaml has action registrations
4. Present findings to the reviewer
5. Ask: approve or reject?

## API

```bash
# Get current state of a flow
curl http://localhost:8001/flows/state?flow=agent_review
```
```

`approve_config/SKILL.md`:
```markdown
---
name: approve_config
description: "Approve a reviewed Agent configuration for deployment"
---

# Approve Configuration

## Trigger

User says "approve", "looks good", "ship it", etc.

## Flow

1. Transition state: reviewed → approved
2. Trigger deploy.sh to compile the approved configuration
3. Report: "Configuration approved and deployed"

## API

```bash
curl -X POST http://localhost:8001/flows/transition \
  -H "Content-Type: application/json" \
  -d '{"flow": "agent_review", "action": "approve"}'
```
```

`reject_config/SKILL.md`:
```markdown
---
name: reject_config
description: "Reject a configuration and send it back for revision"
---

# Reject Configuration

## Trigger

User says "reject", "needs changes", "not ready", etc.

## Flow

1. Ask for rejection reason / feedback
2. Transition state: reviewed → draft
3. Report feedback to the agentforge role

## API

```bash
curl -X POST http://localhost:8001/flows/transition \
  -H "Content-Type: application/json" \
  -d '{"flow": "agent_review", "action": "reject", "feedback": "..."}'
```
```

**Step 2: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/review_config/
git add .socialware/workspace/my-team/agentforge/agent/flow/approve_config/
git add .socialware/workspace/my-team/agentforge/agent/flow/reject_config/
git commit -m "feat(agentforge): add review/approve/reject skills for P5"
```

---

### Task 3: Update flow.yaml with state machine

**Files:**
- Modify: `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`

**Step 1: Add state machine and new action registrations**

Add to flow.yaml:

```yaml
flows:
  agent_review:
    name: agent_review
    description: "Agent creation requires reviewer approval"
    states: [draft, reviewed, approved, rejected]
    transitions:
      - { from: _none_,   action: create_role,     to: draft,    role: [agentforge] }
      - { from: draft,    action: review_config,   to: reviewed, role: [reviewer] }
      - { from: reviewed, action: approve_config,  to: approved, role: [reviewer] }
      - { from: reviewed, action: reject_config,   to: draft,    role: [reviewer] }

direct_actions:
  # ... existing actions ...
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

**Step 2: Verify deploy gives reviewer the correct skills**

Run deploy and check that reviewer role only gets review/approve/reject + check_health skills.

**Step 3: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/flow.yaml
git commit -m "feat(agentforge): add agent_review state machine to flow.yaml for P5"
```

---

### Task 4: Backend — State transition endpoint

**Files:**
- Modify: `src/app.py`
- Test: `tests/test_flow_state.py`

**Step 1: Write test**

Create `tests/test_flow_state.py`:

```python
"""Tests for flow state machine endpoints."""
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

class TestFlowState:
    def test_get_flow_state(self):
        r = client.get("/flows/state")
        assert r.status_code == 200

    def test_post_transition(self):
        r = client.post("/flows/transition", json={
            "flow": "agent_review", "action": "create_role"
        })
        # May succeed or fail depending on state, but shouldn't 500
        assert r.status_code in (200, 400, 404)
```

**Step 2: Implement endpoints**

Add to `src/app.py`:

```python
# In-memory state tracking (P5 — production would use Sqlite)
_flow_states: dict[str, str] = {}

@app.get("/flows/state")
async def get_flow_state(flow: str | None = None):
    """Get current state of flow state machines."""
    if flow:
        return {"flow": flow, "state": _flow_states.get(flow, "_none_")}
    return {"states": _flow_states}

@app.post("/flows/transition")
async def transition_flow(req: dict):
    """Execute a state transition."""
    flow_name = req.get("flow", "")
    action = req.get("action", "")

    # Read flow.yaml to validate transition
    flow_yaml = AGENT_DIR / "flow" / "flow.yaml"
    if not flow_yaml.exists():
        raise HTTPException(404, "flow.yaml not found")

    data = yaml.safe_load(flow_yaml.read_text(encoding="utf-8")) or {}
    flows = data.get("flows", {})

    if flow_name not in flows:
        raise HTTPException(404, f"Flow '{flow_name}' not defined")

    flow_def = flows[flow_name]
    current_state = _flow_states.get(flow_name, "_none_")

    # Find matching transition
    for t in flow_def.get("transitions", []):
        if t["from"] == current_state and t["action"] == action:
            _flow_states[flow_name] = t["to"]
            return {"flow": flow_name, "from": current_state, "to": t["to"], "action": action}

    raise HTTPException(400, f"No transition from '{current_state}' via '{action}'")
```

**Step 3: Run tests**

**Step 4: Commit**

```bash
git add src/app.py tests/test_flow_state.py
git commit -m "feat(api): add flow state machine endpoints for P5"
```

---

### Task 5: Full verification

Run all tests, deploy AgentForge, verify reviewer role has correct skills.

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | Reviewer role | `role/reviewer/SOUL.md` |
| 2 | Review/approve/reject Skills | `flow/review_config/`, `approve_config/`, `reject_config/` |
| 3 | flow.yaml state machine | `flow.yaml` with agent_review flow |
| 4 | State transition API | `src/app.py` `/flows/state` + `/flows/transition` |
| 5 | Full verification | All tests pass |
