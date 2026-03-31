# TDD Guide for Socialware Apps

## Mapping: Action → API → Test

Socialware 的 TDD 开发遵循三层映射关系：

```
socialware.py                 src/api.py                  tests/test_api.py
─────────────                 ──────────                  ─────────────────
app.action("check_health")  → @app.get("/health")       → test_health()
app.action("create_task")   → @app.post("/tasks")       → test_create_task()
app.action("list_tasks")    → @app.get("/tasks")        → test_list_tasks()
app.action("resolve_task")  → @app.post("/tasks/{id}")  → test_resolve_task()
```

每个 `app.action(...)` 注册的业务操作，都应有对应的 API endpoint 和测试用例。

## Example Test Structure

```python
"""tests/test_api.py — Socialware App API 测试。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import app


@pytest.fixture
async def client():
    """创建异步测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    """GET /health 应返回 status ok。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── 业务操作示例: create_task ─────────────────────────

@pytest.mark.asyncio
async def test_create_task(client):
    """POST /tasks 应创建任务并返回 id。"""
    payload = {"title": "Write unit tests", "assignee": "default"}
    resp = await client.post("/tasks", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Write unit tests"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_task_missing_title(client):
    """POST /tasks 缺少 title 时应返回 422。"""
    resp = await client.post("/tasks", json={"assignee": "default"})
    assert resp.status_code == 422


# ── 业务操作示例: list_tasks ──────────────────────────

@pytest.mark.asyncio
async def test_list_tasks(client):
    """GET /tasks 应返回任务列表。"""
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

## Example API Endpoint Implementation

```python
"""src/api.py — 新增业务 endpoint 的模式。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ── Request / Response Models ─────────────────────────

class TaskCreate(BaseModel):
    title: str
    assignee: str = "default"


class TaskResponse(BaseModel):
    id: str
    title: str
    assignee: str
    created_at: str


# ── In-memory store (替换为持久化存储) ─────────────────

_tasks: dict[str, dict] = {}


# ── Endpoints ─────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse)
async def create_task(payload: TaskCreate) -> dict:
    """创建一个新任务。"""
    task_id = uuid.uuid4().hex[:8]
    task = {
        "id": task_id,
        "title": payload.title,
        "assignee": payload.assignee,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task


@app.get("/tasks")
async def list_tasks() -> list[dict]:
    """列出所有任务。"""
    return list(_tasks.values())


@app.post("/tasks/{task_id}/resolve")
async def resolve_task(task_id: str) -> dict:
    """标记任务为已完成。"""
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    _tasks[task_id]["resolved"] = True
    _tasks[task_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()
    return _tasks[task_id]
```

## How to Run Tests

```bash
# 运行全部测试（详细输出）
uv run pytest tests/ -v

# 运行指定测试
uv run pytest tests/test_api.py -v -k test_create_task

# 运行并显示覆盖率
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

## TDD Cycle Checklist

1. **Red**: 先写测试，运行确认失败
2. **Green**: 写最少的代码让测试通过
3. **Refactor**: 重构代码（加类型、模型、错误处理），确保测试仍然通过
4. **Repeat**: 对下一个 action 重复以上步骤

## Tips

- 每次只实现一个 action 的 API endpoint
- 测试用例应覆盖正常路径和异常路径（如缺少字段、资源不存在）
- 使用 Pydantic `BaseModel` 做请求验证，FastAPI 会自动返回 422
- 保持 endpoint 函数简洁，复杂逻辑抽到 service 层
- SKILL.md 也需要"测试"——检查 trigger、flow、error handling 是否完整
