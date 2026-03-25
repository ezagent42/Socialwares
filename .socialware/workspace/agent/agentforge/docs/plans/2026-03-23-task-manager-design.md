# Task-Manager Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `task-manager` Agent role with 4 CRUD skills for personal todo management, stored in JSON files.

**Architecture:** Independent role with 4 skills following the three-piece pattern (SKILL.md + app.py endpoint + flow.yaml). Task data persisted in `.runtime/data/Files/tasks.json`.

**Tech Stack:** Python/FastAPI, JSON file storage, pytest for testing

---

### Task 1: Add Task API endpoints to app.py

**Files:**
- Modify: `src/app.py` (after line 510, before the `if __name__` block)
- Test: `tests/test_api.py`

**Step 1: Write the failing tests**

Add to `tests/test_api.py`:

```python
class TestTasks:
    def setup_method(self):
        """Reset tasks file before each test."""
        from src.app import TASKS_FILE
        if TASKS_FILE.exists():
            TASKS_FILE.unlink()

    def test_list_tasks_empty(self):
        r = client.get("/tasks")
        assert r.status_code == 200
        assert r.json()["tasks"] == []

    def test_create_task(self):
        r = client.post("/tasks", json={"title": "Buy milk"})
        assert r.status_code == 200
        task = r.json()["task"]
        assert task["title"] == "Buy milk"
        assert task["status"] == "pending"
        assert "id" in task
        assert "created_at" in task

    def test_create_task_missing_title(self):
        r = client.post("/tasks", json={})
        assert r.status_code == 400

    def test_list_tasks_with_data(self):
        client.post("/tasks", json={"title": "Task A"})
        client.post("/tasks", json={"title": "Task B"})
        r = client.get("/tasks")
        assert len(r.json()["tasks"]) == 2

    def test_list_tasks_filter_status(self):
        client.post("/tasks", json={"title": "Task A"})
        r1 = client.post("/tasks", json={"title": "Task B"})
        task_id = r1.json()["task"]["id"]
        client.post(f"/tasks/{task_id}/complete")
        pending = client.get("/tasks?status=pending").json()["tasks"]
        done = client.get("/tasks?status=done").json()["tasks"]
        assert len(pending) == 1
        assert len(done) == 1

    def test_complete_task(self):
        r = client.post("/tasks", json={"title": "Do laundry"})
        task_id = r.json()["task"]["id"]
        r2 = client.post(f"/tasks/{task_id}/complete")
        assert r2.status_code == 200
        assert r2.json()["task"]["status"] == "done"

    def test_complete_task_not_found(self):
        assert client.post("/tasks/999/complete").status_code == 404

    def test_delete_task(self):
        r = client.post("/tasks", json={"title": "Temp task"})
        task_id = r.json()["task"]["id"]
        r2 = client.delete(f"/tasks/{task_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"
        # Verify it's gone
        tasks = client.get("/tasks").json()["tasks"]
        assert all(t["id"] != task_id for t in tasks)

    def test_delete_task_not_found(self):
        assert client.delete("/tasks/999").status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py::TestTasks -v`
Expected: FAIL — endpoints not found (404 or attribute errors)

**Step 3: Write the implementation in app.py**

Add after the ZChat section (before `if __name__`), plus a `TASKS_FILE` constant near the top:

Near line 31 (after `ADAPTERS_DIR`), add:
```python
TASKS_FILE = RUNTIME_DIR / "data" / "Files" / "tasks.json"
```

Before `if __name__`, add:
```python
# -- Tasks ------------------------------------------------------------------

import json
from datetime import datetime


def _load_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def _save_tasks(tasks: list[dict]) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


@app.post("/tasks")
async def create_task(req: dict):
    title = req.get("title")
    if not title:
        raise HTTPException(400, "title is required")
    tasks = _load_tasks()
    task = {
        "id": str(max((int(t["id"]) for t in tasks), default=0) + 1),
        "title": title,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    _save_tasks(tasks)
    return {"task": task}


@app.get("/tasks")
async def list_tasks(status: str | None = None):
    tasks = _load_tasks()
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return {"tasks": tasks}


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            _save_tasks(tasks)
            return {"task": t}
    raise HTTPException(404, f"Task '{task_id}' not found")


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    tasks = _load_tasks()
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        raise HTTPException(404, f"Task '{task_id}' not found")
    _save_tasks(new_tasks)
    return {"status": "deleted"}
```

**Step 4: Run tests to verify they pass**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py::TestTasks -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add src/app.py tests/test_api.py
git commit -m "feat(task-manager): add task CRUD API endpoints with tests"
```

---

### Task 2: Create task-manager role SOUL.md

**Files:**
- Create: `agent/role/task-manager/SOUL.md`

**Step 1: Create the role file**

```markdown
# Task Manager Agent

个人待办事项管理助手。帮助用户创建、查看、完成和删除任务。

## Identity

- Role: task-manager
- Permissions: 任务 CRUD 操作

## Responsibilities

1. 创建新任务
2. 列出所有任务（支持按状态筛选）
3. 标记任务为已完成
4. 删除任务

## Boundaries

- 不管理其他 agent 的配置
- 不执行任务内容本身，只做记录和跟踪
```

**Step 2: Verify the role is detectable via API**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py::TestPrimitives::test_get_roles -v`
Expected: PASS, and `task-manager` should appear in the roles list

**Step 3: Commit**

```bash
git add agent/role/task-manager/SOUL.md
git commit -m "feat(task-manager): add task-manager role SOUL.md"
```

---

### Task 3: Create 4 SKILL.md files

**Files:**
- Create: `agent/flow/create_task/SKILL.md`
- Create: `agent/flow/list_tasks/SKILL.md`
- Create: `agent/flow/complete_task/SKILL.md`
- Create: `agent/flow/delete_task/SKILL.md`

**Step 1: Create `agent/flow/create_task/SKILL.md`**

```markdown
---
name: create_task
description: "Create a new personal task"
---

# Create Task

Creates a new task in the task list.

## Trigger

User says "create a task", "add a task", "new todo", "I need to ...", etc.

## Flow

1. Ask for the task title (what needs to be done)
2. Call the API to create the task
3. Report the created task with its ID

## Available APIs

```bash
curl -X POST http://localhost:8001/tasks -H "Content-Type: application/json" -d '{"title": "Buy milk"}'
# → {"task": {"id": "1", "title": "Buy milk", "status": "pending", "created_at": "..."}}
```
```

**Step 2: Create `agent/flow/list_tasks/SKILL.md`**

```markdown
---
name: list_tasks
description: "List all tasks, optionally filtered by status"
---

# List Tasks

Shows all tasks or filters by status.

## Trigger

User says "show my tasks", "list tasks", "what do I need to do", "show completed tasks", etc.

## Flow

1. Determine if user wants a specific status filter (pending/done) or all tasks
2. Call the API with optional status parameter
3. Display the task list in a readable format

## Available APIs

```bash
curl http://localhost:8001/tasks
# → {"tasks": [{"id": "1", "title": "Buy milk", "status": "pending", ...}]}

curl http://localhost:8001/tasks?status=pending
# → {"tasks": [...only pending tasks...]}

curl http://localhost:8001/tasks?status=done
# → {"tasks": [...only completed tasks...]}
```
```

**Step 3: Create `agent/flow/complete_task/SKILL.md`**

```markdown
---
name: complete_task
description: "Mark a task as completed"
---

# Complete Task

Marks an existing task as done.

## Trigger

User says "complete task", "mark as done", "finish task", "I did ...", etc.

## Flow

1. If task ID not provided, call list_tasks API to show pending tasks
2. Ask user which task to complete (by ID)
3. Call the API to mark it done
4. Confirm completion

## Available APIs

```bash
curl -X POST http://localhost:8001/tasks/1/complete
# → {"task": {"id": "1", "title": "Buy milk", "status": "done", ...}}
```
```

**Step 4: Create `agent/flow/delete_task/SKILL.md`**

```markdown
---
name: delete_task
description: "Delete a task from the list"
---

# Delete Task

Removes a task permanently.

## Trigger

User says "delete task", "remove task", "cancel task", etc.

## Flow

1. If task ID not provided, call list_tasks API to show tasks
2. Ask user which task to delete (by ID)
3. Call the API to delete it
4. Confirm deletion

## Available APIs

```bash
curl -X DELETE http://localhost:8001/tasks/1
# → {"status": "deleted"}
```
```

**Step 5: Verify skills are detectable via API**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py::TestPrimitives::test_get_flows -v`
Expected: PASS

**Step 6: Commit**

```bash
git add agent/flow/create_task/SKILL.md agent/flow/list_tasks/SKILL.md agent/flow/complete_task/SKILL.md agent/flow/delete_task/SKILL.md
git commit -m "feat(task-manager): add 4 task skill SKILL.md files"
```

---

### Task 4: Register skills in flow.yaml

**Files:**
- Modify: `agent/flow/flow.yaml` (append to `direct_actions` list)

**Step 1: Add 4 direct_actions to flow.yaml**

Append after the last entry (line 73, `setup_claude`):

```yaml

  - action: create_task
    role: [task-manager]
    description: "Create a new personal task"

  - action: list_tasks
    role: [task-manager]
    description: "List all tasks, optionally filtered by status"

  - action: complete_task
    role: [task-manager]
    description: "Mark a task as completed"

  - action: delete_task
    role: [task-manager]
    description: "Delete a task from the list"
```

**Step 2: Verify flow.yaml is valid**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -c "import yaml; yaml.safe_load(open('agent/flow/flow.yaml', encoding='utf-8')); print('OK')"`
Expected: `OK`

**Step 3: Verify via API**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py::TestPrimitives::test_get_flows_registry -v`
Expected: PASS

**Step 4: Commit**

```bash
git add agent/flow/flow.yaml
git commit -m "feat(task-manager): register 4 task skills in flow.yaml"
```

---

### Task 5: Deploy and verify

**Step 1: Run deploy.sh**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && bash ./agent/deploy.sh`
Expected: Successful deployment, `task-manager` role appears in `.runtime/agents/`

**Step 2: Verify deployment**

Run: `ls D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge/.runtime/agents/task-manager/`
Expected: `SOUL.md`, `flow.yaml`, `eval.yaml`, `.claude/skills/` with symlinks to the 4 task skills

**Step 3: Run full test suite**

Run: `cd D:/workspace/zhidaoyuan/Socialwares/.socialware/workspace/agent/agentforge && python -m pytest tests/test_api.py -v`
Expected: All tests PASS (existing + new)

**Step 4: Commit**

```bash
git commit -m "chore: deploy task-manager agent"
```

---

## Summary of all files

### New files (6):
1. `agent/role/task-manager/SOUL.md`
2. `agent/flow/create_task/SKILL.md`
3. `agent/flow/list_tasks/SKILL.md`
4. `agent/flow/complete_task/SKILL.md`
5. `agent/flow/delete_task/SKILL.md`
6. `docs/plans/2026-03-23-task-manager-design.md` (this file)

### Modified files (3):
7. `src/app.py` — add TASKS_FILE constant + 4 endpoints + 2 helpers
8. `agent/flow/flow.yaml` — add 4 direct_actions
9. `tests/test_api.py` — add TestTasks class with 9 tests
