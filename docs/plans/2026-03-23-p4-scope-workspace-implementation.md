# P4 扩大 Scope — Workspace Dashboard + Evolve Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand AgentForge's capabilities with multi-workspace management (Dashboard) and automated optimization (Evolve Skill). Update scope/SOUL.md to reflect expanded abilities.

**Architecture:** Backend adds workspace CRUD endpoints (`/workspaces`). Frontend adds a Dashboard page for workspace management. Evolve Skill reads eval results, proposes improvements to four-primitive files, and routes changes (`.runtime/` for tenant-specific, `agent/` for universal → auto PR). `scripts/evolve.sh` already exists — the Skill wraps it.

**Tech Stack:** Python (FastAPI, subprocess, git), Next.js (Dashboard page), Bash (evolve.sh), pytest

**Reference:** `docs/plans/2026-03-19-socialware-framework-design.md` (第五部分: Phase 4)

---

### Task 1: Backend — Workspace CRUD API

**Files:**
- Modify: `src/app.py`
- Test: `tests/test_workspace_api.py`

**Step 1: Write the failing test**

Create `tests/test_workspace_api.py`:

```python
"""Tests for Workspace CRUD API."""
from __future__ import annotations

from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestWorkspaceList:
    def test_list_workspaces(self):
        r = client.get("/workspaces")
        assert r.status_code == 200
        assert "workspaces" in r.json()


class TestWorkspaceCreate:
    def test_create_workspace_validation(self):
        # Missing required fields
        r = client.post("/workspaces", json={})
        assert r.status_code == 422


class TestWorkspaceDelete:
    def test_delete_nonexistent(self):
        r = client.delete("/workspaces/nonexistent-ws-test")
        assert r.status_code == 404
```

**Step 2: Run test to verify it fails**

**Step 3: Add workspace endpoints to src/app.py**

```python
class WorkspaceRequest(BaseModel):
    room: str
    app_name: str
    description: str = ""

@app.get("/workspaces")
async def list_workspaces():
    """List all workspace instances."""
    ws_dir = APP_ROOT / ".socialware" / "workspace"
    if not ws_dir.exists():
        return {"workspaces": []}
    workspaces = []
    for room_dir in ws_dir.iterdir():
        if not room_dir.is_dir():
            continue
        for app_dir in room_dir.iterdir():
            if not app_dir.is_dir():
                continue
            workspaces.append({
                "room": room_dir.name,
                "app": app_dir.name,
                "path": str(app_dir.relative_to(APP_ROOT)),
                "has_runtime": (app_dir / ".runtime").exists(),
            })
    return {"workspaces": workspaces}

@app.post("/workspaces")
async def create_workspace(req: WorkspaceRequest):
    """Create a new workspace via create-my-socialware."""
    import subprocess
    script = APP_ROOT / "scripts" / "create-my-socialware.py"
    result = subprocess.run(
        ["python", str(script), "--room", req.room, "--app", req.app_name,
         "--description", req.description or f"{req.app_name} App"],
        capture_output=True, text=True, cwd=str(APP_ROOT),
    )
    if result.returncode != 0:
        raise HTTPException(400, f"Failed: {result.stderr}")
    return {"status": "created", "room": req.room, "app": req.app_name}

@app.delete("/workspaces/{room}/{app_name}")
async def delete_workspace(room: str, app_name: str):
    """Delete a workspace."""
    ws_dir = APP_ROOT / ".socialware" / "workspace" / room / app_name
    if not ws_dir.exists():
        raise HTTPException(404, "Workspace not found")
    import shutil
    shutil.rmtree(ws_dir)
    return {"status": "deleted"}

@app.post("/workspaces/{room}/{app_name}/sync")
async def sync_workspace(room: str, app_name: str):
    """Sync workspace with upstream (merge/rebase)."""
    ws_dir = APP_ROOT / ".socialware" / "workspace" / room / app_name
    if not ws_dir.exists():
        raise HTTPException(404, "Workspace not found")
    # Placeholder — full git merge/rebase in future
    return {"status": "sync not yet implemented"}
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add src/app.py tests/test_workspace_api.py
git commit -m "feat(api): add workspace CRUD endpoints for P4"
```

---

### Task 2: Frontend — Dashboard page

**Files:**
- Create: `app/src/app/dashboard/page.tsx`
- Create: `app/src/components/workspace-card.tsx`
- Modify: `app/src/lib/api.ts`

**Step 1: Add API functions**

Add to `app/src/lib/api.ts`:

```typescript
export async function getWorkspaces() {
  return request<{ workspaces: { room: string; app: string; path: string; has_runtime: boolean }[] }>("/workspaces");
}

export async function createWorkspace(room: string, appName: string, description: string) {
  return request<{ status: string }>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ room, app_name: appName, description }),
  });
}

export async function deleteWorkspace(room: string, appName: string) {
  return request<{ status: string }>(`/workspaces/${room}/${appName}`, { method: "DELETE" });
}
```

**Step 2: Create WorkspaceCard component**

Create `app/src/components/workspace-card.tsx` — card showing workspace name, room, status, open/delete buttons.

**Step 3: Create Dashboard page**

Create `app/src/app/dashboard/page.tsx` — lists workspaces with create button.

**Step 4: Verify build**

Run: `cd app && npx next build`

**Step 5: Commit**

```bash
git add app/src/
git commit -m "feat(frontend): add workspace dashboard page for P4"
```

---

### Task 3: Create Evolve Skill for AgentForge

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/evolve/SKILL.md`
- Modify: `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`

**Step 1: Create SKILL.md**

```markdown
---
name: evolve
description: "Analyze eval results and optimize Agent four-primitive configuration"
---

# Evolve

## Trigger

User says "evolve", "optimize", "improve agent", "auto-optimize", etc.

## Flow

1. Read eval results via `GET /metrics`
2. Identify failing or below-threshold commitments
3. Analyze current four-primitive configuration
4. Propose changes to improve:
   - SOUL.md — refine agent instructions
   - SKILL.md — improve skill steps
   - flow.yaml — adjust action bindings
   - eval.yaml — adjust thresholds if unreasonable
5. Apply changes (with user confirmation)
6. Route changes:
   - Changes to .runtime/ → tenant-specific, no PR
   - Changes to agent/ → universal, trigger `./scripts/evolve.sh {workspace} --pr`
7. Run deploy.sh

## API

```bash
# Get current metrics
curl http://localhost:8001/metrics

# Run evolve script (checks for agent/ changes → PR)
./scripts/evolve.sh my-team/agentforge --check
./scripts/evolve.sh my-team/agentforge --pr
```
```

**Step 2: Update flow.yaml**

Add to flow.yaml:
```yaml
  - action: evolve
    role: [agentforge]
    description: "Analyze eval results and optimize Agent configuration"
```

**Step 3: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/evolve/
git add .socialware/workspace/my-team/agentforge/agent/flow/flow.yaml
git commit -m "feat(agentforge): add evolve skill for P4 auto-optimization"
```

---

### Task 4: Update scope/SOUL.md

**Files:**
- Modify: `.socialware/workspace/my-team/agentforge/agent/scope/SOUL.md`

Update to include P4 capabilities (multi-workspace, evolve).

**Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/scope/SOUL.md
git commit -m "feat(agentforge): expand scope/SOUL.md with P4 capabilities"
```

---

### Task 5: Full verification

Run all tests, verify dashboard, verify evolve skill deployed.

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | Workspace CRUD API | `src/app.py`, `tests/test_workspace_api.py` |
| 2 | Dashboard frontend | `app/src/app/dashboard/page.tsx` |
| 3 | Evolve Skill | AgentForge `flow/evolve/SKILL.md` |
| 4 | scope/SOUL.md update | scope capabilities expansion |
| 5 | Full verification | All tests pass |
