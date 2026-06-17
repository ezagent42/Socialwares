# AgentForge CMS 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 AgentForge 从脚手架模板发展为可用的 Agent 配置管理平台，支持 GitHub 登录、Chat 驱动的 CRUD、结构化渲染和导出/导入。

**Architecture:** 后端 FastAPI 提供 GitHub OAuth + Chat SSE 通道 + SQLite CRUD；前端 Next.js 单页面（Dashboard + Chat Panel），通过 Chat Store 共享状态；Agent 通过 Adapter Layer 执行操作并返回 `json:structured` 结构化数据。

**Tech Stack:** Python 3.12+, FastAPI, aiosqlite, SSE (sse-starlette), httpx | Next.js 15, React 19, Tailwind CSS 4, zustand

**Design Docs:**
- [cms-design.md](../plans/2026-03-26-agentforge-cms-design.md) — 系统架构
- [dual-interaction-impl.md](../plans/2026-03-26-agentforge-dual-interaction-impl.md) — 双交互模式
- [primitives-spec.md](../plans/2026-03-26-agentforge-primitives-spec.md) — 四原语规格

**Working Directory:** `.socialware/workspace/my-team/agentforge/`

---

## Phase 1 — 数据库 + CRUD

> 先建数据层，后续所有功能都依赖它。

### Task 1: SQLite 数据库初始化

**Files:**
- Create: `src/db.py`
- Test: `tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py
import pytest
import asyncio
from pathlib import Path


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def db(db_path):
    from src.db import Database
    database = Database(db_path)
    asyncio.get_event_loop().run_until_complete(database.init())
    return database


def test_database_creates_tables(db, db_path):
    """Database.init() creates all required tables."""
    assert db_path.exists()
    tables = asyncio.get_event_loop().run_until_complete(db.list_tables())
    expected = {"users", "sessions", "agents", "roles", "skills", "skill_roles", "scopes", "commitments", "chat_history"}
    assert set(tables) == expected


def test_database_is_idempotent(db):
    """Calling init() twice does not raise."""
    asyncio.get_event_loop().run_until_complete(db.init())
```

**Step 2: Run test to verify it fails**

Run: `cd .socialware/workspace/my-team/agentforge && uv run pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.db'`

**Step 3: Write minimal implementation**

```python
# src/db.py
"""SQLite database initialization and connection management."""
from __future__ import annotations

import aiosqlite
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    github_id       INTEGER NOT NULL UNIQUE,
    github_login    TEXT NOT NULL,
    github_name     TEXT DEFAULT '',
    github_avatar   TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS roles (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    soul_md         TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(agent_id, name)
);

CREATE TABLE IF NOT EXISTS skills (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    skill_md        TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(agent_id, name)
);

CREATE TABLE IF NOT EXISTS skill_roles (
    skill_id        TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    role_id         TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (skill_id, role_id)
);

CREATE TABLE IF NOT EXISTS scopes (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    soul_md         TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS commitments (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    commitment_yaml TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    structured      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    async def init(self):
        """Create tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.execute("PRAGMA foreign_keys = ON")
            await db.commit()

    async def list_tables(self) -> list[str]:
        """List all table names (for testing)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def connect(self) -> aiosqlite.Connection:
        """Get a database connection with foreign keys enabled."""
        db = await aiosqlite.connect(self.db_path)
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        return db
```

**Step 4: Add aiosqlite dependency**

Run: `cd .socialware/workspace/my-team/agentforge && uv add aiosqlite`

**Step 5: Run test to verify it passes**

Run: `cd .socialware/workspace/my-team/agentforge && uv run pytest tests/test_db.py -v`
Expected: 2 PASSED

**Step 6: Commit**

```bash
git add src/db.py tests/test_db.py pyproject.toml
git commit -m "feat(agentforge): add SQLite database initialization"
```

---

### Task 2: Agent CRUD

**Files:**
- Create: `src/crud/agent_crud.py`
- Create: `src/crud/__init__.py`
- Test: `tests/test_agent_crud.py`

**Step 1: Write the failing test**

```python
# tests/test_agent_crud.py
import pytest
import asyncio
from pathlib import Path


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.get_event_loop().run_until_complete(database.init())
    return database


@pytest.fixture
def user_id(db):
    """Create a test user and return user_id."""
    async def _create():
        conn = await db.connect()
        await conn.execute(
            "INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)",
            ("u1", 12345, "testuser")
        )
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.get_event_loop().run_until_complete(_create())


def test_create_agent(db, user_id):
    from src.crud.agent_crud import create_agent
    agent = asyncio.get_event_loop().run_until_complete(
        create_agent(db, user_id, "task-manager", "Manage tasks")
    )
    assert agent["name"] == "task-manager"
    assert agent["description"] == "Manage tasks"
    assert "id" in agent
    # auto-created default role
    assert len(agent["roles"]) == 1
    assert agent["roles"][0]["name"] == "default"
    # auto-created scope
    assert "scope" in agent


def test_create_agent_duplicate_name(db, user_id):
    from src.crud.agent_crud import create_agent
    asyncio.get_event_loop().run_until_complete(
        create_agent(db, user_id, "dup", "first")
    )
    with pytest.raises(ValueError, match="already exists"):
        asyncio.get_event_loop().run_until_complete(
            create_agent(db, user_id, "dup", "second")
        )


def test_list_agents(db, user_id):
    from src.crud.agent_crud import create_agent, list_agents
    asyncio.get_event_loop().run_until_complete(create_agent(db, user_id, "a1", ""))
    asyncio.get_event_loop().run_until_complete(create_agent(db, user_id, "a2", ""))
    agents = asyncio.get_event_loop().run_until_complete(list_agents(db, user_id))
    assert len(agents) == 2


def test_get_agent(db, user_id):
    from src.crud.agent_crud import create_agent, get_agent
    created = asyncio.get_event_loop().run_until_complete(
        create_agent(db, user_id, "x", "desc")
    )
    agent = asyncio.get_event_loop().run_until_complete(
        get_agent(db, user_id, created["id"])
    )
    assert agent["name"] == "x"
    assert "roles" in agent
    assert "skills" in agent


def test_delete_agent(db, user_id):
    from src.crud.agent_crud import create_agent, delete_agent, list_agents
    created = asyncio.get_event_loop().run_until_complete(
        create_agent(db, user_id, "del-me", "")
    )
    asyncio.get_event_loop().run_until_complete(
        delete_agent(db, user_id, created["id"])
    )
    agents = asyncio.get_event_loop().run_until_complete(list_agents(db, user_id))
    assert len(agents) == 0


def test_user_isolation(db):
    """User A cannot see User B's agents."""
    from src.crud.agent_crud import create_agent, list_agents
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ua", 1, "alice"))
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES (?, ?, ?)", ("ub", 2, "bob"))
        await conn.commit()
        await conn.close()
    asyncio.get_event_loop().run_until_complete(_setup())
    asyncio.get_event_loop().run_until_complete(create_agent(db, "ua", "alice-agent", ""))
    asyncio.get_event_loop().run_until_complete(create_agent(db, "ub", "bob-agent", ""))
    alice_agents = asyncio.get_event_loop().run_until_complete(list_agents(db, "ua"))
    bob_agents = asyncio.get_event_loop().run_until_complete(list_agents(db, "ub"))
    assert len(alice_agents) == 1
    assert alice_agents[0]["name"] == "alice-agent"
    assert len(bob_agents) == 1
    assert bob_agents[0]["name"] == "bob-agent"
```

**Step 2: Run test to verify it fails**

Run: `cd .socialware/workspace/my-team/agentforge && uv run pytest tests/test_agent_crud.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/crud/__init__.py
```

```python
# src/crud/agent_crud.py
"""Agent CRUD operations."""
from __future__ import annotations

import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_agent(db: Database, user_id: str, name: str, description: str) -> dict:
    conn = await db.connect()
    try:
        # Check duplicate
        cursor = await conn.execute(
            "SELECT id FROM agents WHERE user_id = ? AND name = ?", (user_id, name)
        )
        if await cursor.fetchone():
            raise ValueError(f"Agent '{name}' already exists")

        agent_id = _uuid()
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description) VALUES (?, ?, ?, ?)",
            (agent_id, user_id, name, description)
        )

        # Auto-create default role
        role_id = _uuid()
        default_soul = f"# Default Agent\n\nDefault role for {name}.\n\n## Identity\n\n- Role: default\n- Permissions: all operations\n"
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            (role_id, agent_id, "default", default_soul)
        )

        # Auto-create scope
        scope_id = _uuid()
        default_scope = f"# {name}\n\n{description}\n\n## Capabilities\n\n- (Add capabilities here)\n\n## Boundaries\n\n- (Add boundaries here)\n"
        await conn.execute(
            "INSERT INTO scopes (id, agent_id, soul_md) VALUES (?, ?, ?)",
            (scope_id, agent_id, default_scope)
        )

        # Auto-create empty commitment
        commit_id = _uuid()
        await conn.execute(
            "INSERT INTO commitments (id, agent_id, commitment_yaml) VALUES (?, ?, ?)",
            (commit_id, agent_id, "commitments: {}")
        )

        await conn.commit()
        return {
            "id": agent_id,
            "name": name,
            "description": description,
            "roles": [{"id": role_id, "name": "default"}],
            "skills": [],
            "scope": {"id": scope_id},
        }
    finally:
        await conn.close()


async def list_agents(db: Database, user_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, created_at FROM agents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        agents = []
        for row in rows:
            # Count roles and skills
            rc = await conn.execute("SELECT COUNT(*) FROM roles WHERE agent_id = ?", (row[0],))
            roles_count = (await rc.fetchone())[0]
            sc = await conn.execute("SELECT COUNT(*) FROM skills WHERE agent_id = ?", (row[0],))
            skills_count = (await sc.fetchone())[0]
            agents.append({
                "id": row[0], "name": row[1], "description": row[2],
                "roles_count": roles_count, "skills_count": skills_count,
            })
        return agents
    finally:
        await conn.close()


async def get_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description FROM agents WHERE id = ? AND user_id = ?",
            (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")

        # Fetch roles
        rc = await conn.execute("SELECT id, name, soul_md FROM roles WHERE agent_id = ?", (agent_id,))
        roles = [{"id": r[0], "name": r[1], "soul_md_preview": r[2][:100]} for r in await rc.fetchall()]

        # Fetch skills
        sc = await conn.execute("SELECT id, name, description FROM skills WHERE agent_id = ?", (agent_id,))
        skills = [{"id": s[0], "name": s[1], "description": s[2]} for s in await sc.fetchall()]

        # Fetch scope
        spc = await conn.execute("SELECT soul_md FROM scopes WHERE agent_id = ?", (agent_id,))
        scope_row = await spc.fetchone()

        # Fetch commitment
        cc = await conn.execute("SELECT commitment_yaml FROM commitments WHERE agent_id = ?", (agent_id,))
        commit_row = await cc.fetchone()

        return {
            "id": row[0], "name": row[1], "description": row[2],
            "roles": roles, "skills": skills,
            "scope": scope_row[0] if scope_row else "",
            "commitment": commit_row[0] if commit_row else "",
        }
    finally:
        await conn.close()


async def delete_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT name FROM agents WHERE id = ? AND user_id = ?", (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        name = row[0]
        await conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        await conn.commit()
        return {"id": agent_id, "name": name}
    finally:
        await conn.close()
```

**Step 4: Run test to verify it passes**

Run: `cd .socialware/workspace/my-team/agentforge && uv run pytest tests/test_agent_crud.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
git add src/crud/ tests/test_agent_crud.py
git commit -m "feat(agentforge): add Agent CRUD with user isolation"
```

---

### Task 3: Role CRUD

**Files:**
- Create: `src/crud/role_crud.py`
- Test: `tests/test_role_crud.py`

**Step 1: Write the failing test**

```python
# tests/test_role_crud.py
import pytest
import asyncio


@pytest.fixture
def db(tmp_path):
    from src.db import Database
    database = Database(tmp_path / "test.db")
    asyncio.get_event_loop().run_until_complete(database.init())
    return database


@pytest.fixture
def agent_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.commit()
        await conn.close()
        from src.crud.agent_crud import create_agent
        agent = await create_agent(db, "u1", "test-app", "")
        return agent["id"]
    return asyncio.get_event_loop().run_until_complete(_setup())


def test_create_role(db, agent_id):
    from src.crud.role_crud import create_role
    role = asyncio.get_event_loop().run_until_complete(
        create_role(db, agent_id, "reviewer", "# Reviewer\nReviews tasks")
    )
    assert role["name"] == "reviewer"
    assert "id" in role


def test_list_roles(db, agent_id):
    from src.crud.role_crud import create_role, list_roles
    asyncio.get_event_loop().run_until_complete(create_role(db, agent_id, "admin", "# Admin"))
    roles = asyncio.get_event_loop().run_until_complete(list_roles(db, agent_id))
    assert len(roles) == 2  # default + admin


def test_update_role(db, agent_id):
    from src.crud.role_crud import create_role, update_role
    role = asyncio.get_event_loop().run_until_complete(create_role(db, agent_id, "ed", "old"))
    updated = asyncio.get_event_loop().run_until_complete(update_role(db, role["id"], "new content"))
    assert updated["soul_md"] == "new content"


def test_delete_role_prevents_last(db, agent_id):
    from src.crud.role_crud import list_roles, delete_role
    roles = asyncio.get_event_loop().run_until_complete(list_roles(db, agent_id))
    assert len(roles) == 1  # only default
    with pytest.raises(ValueError, match="at least one"):
        asyncio.get_event_loop().run_until_complete(delete_role(db, roles[0]["id"]))
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_role_crud.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/crud/role_crud.py
"""Role CRUD operations."""
from __future__ import annotations

import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


async def create_role(db: Database, agent_id: str, name: str, soul_md: str) -> dict:
    conn = await db.connect()
    try:
        role_id = _uuid()
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            (role_id, agent_id, name, soul_md)
        )
        await conn.commit()
        return {"id": role_id, "agent_id": agent_id, "name": name, "soul_md": soul_md}
    finally:
        await conn.close()


async def list_roles(db: Database, agent_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, soul_md FROM roles WHERE agent_id = ? ORDER BY created_at",
            (agent_id,)
        )
        return [{"id": r[0], "name": r[1], "soul_md_preview": r[2][:100]} for r in await cursor.fetchall()]
    finally:
        await conn.close()


async def update_role(db: Database, role_id: str, soul_md: str) -> dict:
    conn = await db.connect()
    try:
        await conn.execute(
            "UPDATE roles SET soul_md = ?, updated_at = datetime('now') WHERE id = ?",
            (soul_md, role_id)
        )
        await conn.commit()
        cursor = await conn.execute("SELECT id, agent_id, name, soul_md FROM roles WHERE id = ?", (role_id,))
        r = await cursor.fetchone()
        return {"id": r[0], "agent_id": r[1], "name": r[2], "soul_md": r[3]}
    finally:
        await conn.close()


async def delete_role(db: Database, role_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT agent_id, name FROM roles WHERE id = ?", (role_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Role not found: {role_id}")
        agent_id, name = row[0], row[1]
        # Check at least one role remains
        count_cursor = await conn.execute("SELECT COUNT(*) FROM roles WHERE agent_id = ?", (agent_id,))
        count = (await count_cursor.fetchone())[0]
        if count <= 1:
            raise ValueError("Cannot delete: agent must have at least one role")
        await conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        await conn.commit()
        return {"id": role_id, "name": name}
    finally:
        await conn.close()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_role_crud.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add src/crud/role_crud.py tests/test_role_crud.py
git commit -m "feat(agentforge): add Role CRUD with last-role protection"
```

---

### Task 4: Skill CRUD

**Files:**
- Create: `src/crud/skill_crud.py`
- Test: `tests/test_skill_crud.py`

**Step 1-5:** 同 Task 3 模式。关键逻辑：
- `create_skill(db, agent_id, name, skill_md, role_ids, description)` — 创建技能 + skill_roles 关联
- `list_skills(db, agent_id)` — 列出技能含关联角色
- `update_skill(db, skill_id, skill_md?, role_ids?)` — 更新内容和/或权限
- `delete_skill(db, skill_id)` — 删除技能 + 级联清理 skill_roles

**Commit:** `feat(agentforge): add Skill CRUD with role permission mapping`

---

### Task 5: Scope + Commitment CRUD

**Files:**
- Create: `src/crud/scope_crud.py`
- Create: `src/crud/commitment_crud.py`
- Test: `tests/test_scope_commitment_crud.py`

**Step 1-5:** 简单的 get/update 操作（每个 Agent 只有一条 scope 和一条 commitment）。

**Commit:** `feat(agentforge): add Scope and Commitment CRUD`

---

### Task 6: Export 功能

**Files:**
- Create: `src/crud/export.py`
- Test: `tests/test_export.py`

**关键逻辑：**
- `export_agent(db, agent_id, output_dir)` — 从 DB 读取 → 生成标准四原语文件结构
- 输出文件名使用代码实际约定：`agent/role/{name}.md`（扁平），`agent/scope/scope.md`，`agent/commitment/commitment.yaml`
- 从模板目录复制 `deploy.sh`、`start.sh`、`adapters/`
- 自动生成 `flow.yaml`（根据 skills + skill_roles 映射）

**Commit:** `feat(agentforge): add Agent export to standard file structure`

---

### Task 7: Import 功能

**Files:**
- Create: `src/crud/import_agent.py`
- Test: `tests/test_import.py`

**关键逻辑：**
- `import_agent(db, user_id, source_dir)` — 解析四原语文件 → 写入 DB
- 读取 `agent/role/*.md` → roles 表
- 读取 `agent/scope/scope.md` → scopes 表
- 读取 `agent/flow/*/SKILL.md` + `flow.yaml` → skills + skill_roles 表
- 读取 `agent/commitment/commitment.yaml` → commitments 表
- 检查名称冲突

**关键测试：** export → import 闭环（对应 Commitment C1）

```python
def test_export_import_roundtrip(db, user_id, tmp_path):
    """C1: 导出的配置包能被成功导入"""
    # 创建 Agent + role + skill
    # 导出到 tmp_path/exported/
    # 导入到另一个名字
    # 验证内容一致
```

**Commit:** `feat(agentforge): add Agent import with roundtrip validation`

---

## Phase 2 — GitHub 登录 + Chat 通信

### Task 8: GitHub OAuth 后端

**Files:**
- Create: `src/auth.py`
- Modify: `src/app.py` — 添加 auth 路由
- Test: `tests/test_auth.py`

**关键端点：**
- `GET /api/auth/login` → 302 重定向到 GitHub
- `GET /api/auth/callback` → code 换 token → 创建 user/session → Set-Cookie → 重定向首页
- `GET /api/auth/me` → 返回当前用户信息
- `POST /api/auth/logout` → 清除 session

**环境变量：** `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

**Commit:** `feat(agentforge): add GitHub OAuth authentication`

---

### Task 9: Session Manager + Chat API

**Files:**
- Create: `src/session.py`
- Modify: `src/app.py` — 添加 `/api/chat/send` 和 `/api/chat/stream`
- Test: `tests/test_chat_api.py`

**关键逻辑：**
- `SessionManager` — 管理 per-user Agent 会话
- `POST /api/chat/send` — 接收消息，通过 adapter 发给 Agent
- `GET /api/chat/stream` — SSE 流式返回 Agent 响应
- 解析 Agent 响应中的 `` ```json:structured``` `` 代码块

**依赖：** `sse-starlette`

**Commit:** `feat(agentforge): add Session Manager and Chat SSE API`

---

## Phase 3 — 前端

### Task 10: Next.js 项目初始化

**Files:**
- Create: `app/package.json`, `app/tsconfig.json`, `app/next.config.ts`, `app/tailwind.config.ts`
- Create: `app/src/app/layout.tsx`, `app/src/app/page.tsx`, `app/src/app/globals.css`

**Step 1:** 在 `app/` 目录初始化 Next.js 15 + React 19 + Tailwind CSS 4 项目

Run:
```bash
cd .socialware/workspace/my-team/agentforge/app
pnpm init
pnpm add next@15 react@19 react-dom@19
pnpm add -D typescript @types/react @types/node tailwindcss@4
```

**Step 2:** 创建单页面布局骨架（Login 状态 / Dashboard + Chat 状态）

**Commit:** `feat(agentforge): initialize Next.js frontend`

---

### Task 11: Chat Store + SSE Client

**Files:**
- Create: `app/src/lib/chat-store.ts`
- Create: `app/src/lib/ui-action.ts`
- Create: `app/src/lib/entity-updater.ts`
- Create: `app/src/lib/types.ts`

**依赖：** `zustand`

**关键实现：**
- `ChatStore` — messages, entities, selected, session 状态
- `sendMessage(content, source)` — 统一消息发送
- `sendUIAction(action)` — UI 操作序列化 + 发送
- `updateEntities(current, event)` — 结构化数据 → 实体索引
- `formatUIActionDisplay(action)` — UI 操作的 Chat 显示文本

**Commit:** `feat(agentforge): add Chat Store with UIAction support`

---

### Task 12: Chat Panel 组件

**Files:**
- Create: `app/src/components/chat-panel.tsx`
- Create: `app/src/components/message-bubble.tsx`

**关键实现：**
- 消息列表 + 输入框 + SSE 连接
- MessageBubble 区分 `source: "chat"` vs `"ui_action"` 样式
- 流式渲染 Agent 回复

**Commit:** `feat(agentforge): add Chat Panel with SSE streaming`

---

### Task 13: 结构化渲染组件

**Files:**
- Create: `app/src/components/structured-block-renderer.tsx`
- Create: `app/src/components/cards/agent-card.tsx`
- Create: `app/src/components/cards/role-card.tsx`
- Create: `app/src/components/cards/skill-card.tsx`
- Create: `app/src/components/action-button.tsx`
- Create: `app/src/components/confirm-dialog.tsx`
- Create: `app/src/components/batch-action-bar.tsx`

**关键实现：**
- `COMPONENT_MAP` — type + action → 组件映射
- `AgentCard` — 显示 Agent 信息 + ActionButton + checkbox
- `ConfirmDialog` — 确认/取消按钮 → sendUIAction
- `BatchActionBar` — 多选操作栏

**Commit:** `feat(agentforge): add structured rendering components`

---

### Task 14: Login 页面 + Auth 状态

**Files:**
- Create: `app/src/components/login-page.tsx`
- Create: `app/src/components/user-bar.tsx`
- Modify: `app/src/app/page.tsx` — 根据 auth 状态切换 Login / Main

**Commit:** `feat(agentforge): add GitHub login UI`

---

## Phase 4 — Dashboard + 完善

### Task 15: Dashboard Panel

**Files:**
- Create: `app/src/components/dashboard-panel.tsx`
- Modify: `app/src/app/page.tsx` — 左侧 Dashboard + 右侧 Chat 布局

**关键实现：**
- 从 Chat Store 的 entities 中提取数据
- 渲染 AgentCard 列表
- 展开详情显示 Role/Skill/Scope/Commitment

**Commit:** `feat(agentforge): add Dashboard panel`

---

### Task 16: Markdown/YAML 编辑器

**Files:**
- Create: `app/src/components/markdown-editor.tsx`
- Create: `app/src/components/yaml-editor.tsx`
- Create: `app/src/components/markdown-preview.tsx`
- Create: `app/src/components/yaml-preview.tsx`

**依赖：** `react-markdown`

**关键实现：**
- 内联在 Chat 流中的编辑器
- 保存 → sendUIAction({ entity, action:"update", context:{ soul_md: content } })

**Commit:** `feat(agentforge): add inline Markdown and YAML editors`

---

### Task 17: Agent 四原语 Skill 文件

**Files:**
- Create: `agent/flow/manage_agent/SKILL.md`
- Create: `agent/flow/manage_role/SKILL.md`
- Create: `agent/flow/manage_skill/SKILL.md`
- Create: `agent/flow/manage_scope/SKILL.md`
- Create: `agent/flow/manage_commitment/SKILL.md`
- Create: `agent/flow/export_agent/SKILL.md`
- Create: `agent/flow/import_agent/SKILL.md`
- Modify: `agent/flow/flow.yaml` — 注册新 action
- Modify: `agent/scope/scope.md` — 更新为设计文档中的内容
- Modify: `agent/role/default.md` — 更新为设计文档中的内容

**内容来源：** `docs/plans/2026-03-26-agentforge-primitives-spec.md` §5

**Commit:** `feat(agentforge): add CMS management skills and update primitives`

---

### Task 18: Commitment 更新 + Deploy 验证

**Files:**
- Modify: `agent/commitment/commitment.yaml` — 写入 C1/C2
- Run: `make deploy` 验证编译通过
- Run: `make start ROLE=default` 验证 Agent 能启动

**Commit:** `feat(agentforge): add commitment standards and verify deployment`

---

## 依赖关系

```
Task 1 (DB)
  ├── Task 2 (Agent CRUD)
  ├── Task 3 (Role CRUD)
  ├── Task 4 (Skill CRUD)
  ├── Task 5 (Scope+Commitment CRUD)
  │     ├── Task 6 (Export)
  │     └── Task 7 (Import) ← depends on Task 6
  │
  ├── Task 8 (GitHub OAuth) ← independent of CRUD
  └── Task 9 (Session+Chat API) ← depends on Task 8

Task 10 (Next.js init) ← independent
  ├── Task 11 (Chat Store)
  │     ├── Task 12 (Chat Panel)
  │     ├── Task 13 (Cards+Renderer)
  │     └── Task 14 (Login UI)
  └── Task 15 (Dashboard) ← depends on 12+13
       └── Task 16 (Editors) ← depends on 15

Task 17 (Skill files) ← independent, can be done anytime
Task 18 (Commitment) ← final verification
```

**可并行的任务：**
- Task 1-7 (后端) 与 Task 10-16 (前端) 可并行
- Task 17 (Skill 文件) 与所有编码任务可并行
- Task 2-5 (各 CRUD) 在 Task 1 完成后可并行
