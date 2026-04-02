# AgentForge Phase 5 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align codebase with v1.2 design docs — simplify Agent data model, implement multi-format export adapters, add find_skill, simplify create wizard, and prepare for Agent SDK integration.

**Architecture:** Simplify DB from 9 tables to 4 core tables (users, sessions, agents, skills). Replace 7-step create wizard with 3-step flow. Implement adapter pattern for 5 export formats (GitAgent, Claude Code, Codex, Cursor, Socialwares). Add find_skill for skill discovery. Agent SDK integration is designed but deferred to Phase 6.

**Tech Stack:** Python 3.12+, FastAPI, aiosqlite, pyyaml | Next.js 15, React 19, Tailwind CSS 4, zustand

**Working Directory:** `.socialware/workspace/my-team/agentforge/`

**Design Docs:**
- [cms-design.md](./2026-03-26-agentforge-cms-design.md)
- [primitives-spec.md](./2026-03-26-agentforge-primitives-spec.md)
- [dual-interaction-impl.md](./2026-03-26-agentforge-dual-interaction-impl.md)

---

## Task 1: Simplify Database Schema

Remove roles, scopes, commitments, skill_roles tables. Add `role_md` to agents table. Remove `model` field.

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py — add new test
def test_database_simplified_schema(db, db_path):
    """New schema has agents with role_md, no roles/scopes/commitments tables."""
    tables = asyncio.run(db.list_tables())
    assert "agents" in tables
    assert "skills" in tables
    assert "users" in tables
    assert "sessions" in tables
    assert "chat_history" in tables
    # Removed tables
    assert "roles" not in tables
    assert "scopes" not in tables
    assert "commitments" not in tables
    assert "skill_roles" not in tables


def test_agents_table_has_role_md(db):
    """agents table has role_md column, no model column."""
    async def _check():
        conn = await db.connect()
        cursor = await conn.execute("PRAGMA table_info(agents)")
        columns = {row[1] for row in await cursor.fetchall()}
        await conn.close()
        return columns
    columns = asyncio.run(_check())
    assert "role_md" in columns
    assert "model" not in columns
```

**Step 2: Run test to verify it fails**

Run: `cd .socialware/workspace/my-team/agentforge && uv run pytest tests/test_db.py -v`
Expected: FAIL — old schema still has roles/scopes/commitments tables

**Step 3: Update src/db.py SCHEMA**

Replace the SCHEMA constant with simplified version:

```python
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
    role_md         TEXT DEFAULT '',
    is_example      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS

**Step 5: Delete old database**

Run: `rm -f .runtime/data/Sqlite/agentforge.db`

**Step 6: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: simplify DB schema — remove roles/scopes/commitments, add role_md"
```

---

## Task 2: Rewrite agent_crud.py for Simplified Model

**Files:**
- Rewrite: `src/crud/agent_crud.py`
- Test: `tests/test_agent_crud.py`

**Step 1: Write the failing test**

```python
# tests/test_agent_crud.py — rewrite
def test_create_agent_with_role_md(db, user_id):
    from src.crud.agent_crud import create_agent
    agent = asyncio.run(create_agent(db, user_id, "test-app", "A test agent", "# Test Agent\nYou review code."))
    assert agent["name"] == "test-app"
    assert agent["role_md"] == "# Test Agent\nYou review code."
    assert "model" not in agent  # no model field


def test_create_agent_no_model(db, user_id):
    """Agent creation does not accept model parameter."""
    from src.crud.agent_crud import create_agent
    agent = asyncio.run(create_agent(db, user_id, "x", "", "# X"))
    assert "model" not in agent
```

**Step 2: Run test to verify it fails**

**Step 3: Rewrite agent_crud.py**

```python
"""Agent CRUD operations — simplified model (role_md + skills, no model)."""
from __future__ import annotations
import re
import uuid
from src.db import Database


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _safe_name(name: str) -> str:
    name = re.sub(r'[^\w\-]', '_', name.strip()).strip('_')
    return name or "unnamed"


async def create_agent(db: Database, user_id: str, name: str, description: str, role_md: str) -> dict:
    name = _safe_name(name)
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id FROM agents WHERE user_id = ? AND name = ?", (user_id, name))
        if await cursor.fetchone():
            raise ValueError(f"Agent '{name}' already exists")
        agent_id = _uuid()
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description, role_md) VALUES (?, ?, ?, ?, ?)",
            (agent_id, user_id, name, description, role_md)
        )
        await conn.commit()
        return {"id": agent_id, "name": name, "description": description, "role_md": role_md, "skills": []}
    finally:
        await conn.close()


async def list_agents(db: Database, user_id: str) -> list[dict]:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, role_md, is_example FROM agents WHERE user_id = ? OR is_example = 1 ORDER BY is_example DESC, created_at DESC",
            (user_id,)
        )
        agents = []
        for row in await cursor.fetchall():
            sc = await conn.execute("SELECT COUNT(*) FROM skills WHERE agent_id = ?", (row[0],))
            skills_count = (await sc.fetchone())[0]
            agents.append({
                "id": row[0], "name": row[1], "description": row[2],
                "role_md_preview": (row[3] or "")[:100],
                "is_example": bool(row[4]), "skills_count": skills_count,
            })
        return agents
    finally:
        await conn.close()


async def get_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT id, name, description, role_md, is_example FROM agents WHERE id = ? AND (user_id = ? OR is_example = 1)",
            (agent_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        sc = await conn.execute("SELECT id, name, description, skill_md FROM skills WHERE agent_id = ?", (agent_id,))
        skills = [{"id": s[0], "name": s[1], "description": s[2], "skill_md": s[3]} for s in await sc.fetchall()]
        return {
            "id": row[0], "name": row[1], "description": row[2],
            "role_md": row[3], "is_example": bool(row[4]), "skills": skills,
        }
    finally:
        await conn.close()


async def update_agent(db: Database, user_id: str, agent_id: str, role_md: str = None, description: str = None) -> dict:
    conn = await db.connect()
    try:
        if role_md is not None:
            await conn.execute("UPDATE agents SET role_md = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?", (role_md, agent_id, user_id))
        if description is not None:
            await conn.execute("UPDATE agents SET description = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?", (description, agent_id, user_id))
        await conn.commit()
        return await get_agent(db, user_id, agent_id)
    finally:
        await conn.close()


async def delete_agent(db: Database, user_id: str, agent_id: str) -> dict:
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT name FROM agents WHERE id = ? AND user_id = ?", (agent_id, user_id))
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

**Step 4: Update tests, run all**

Run: `uv run pytest tests/ -v`

**Step 5: Commit**

```bash
git commit -m "feat: rewrite agent_crud — simplified model with role_md, no model"
```

---

## Task 3: Rewrite skill_crud.py (Remove skill_roles)

Skills now belong directly to an agent, no role permission mapping needed.

**Files:**
- Rewrite: `src/crud/skill_crud.py`
- Test: `tests/test_skill_crud.py`

**Key changes:**
- Remove `role_ids` parameter from `create_skill`
- Remove `skill_roles` table queries
- Simplify `list_skills` — no role join needed
- Keep: create, list, update, delete

**Step 1-5:** Same TDD pattern. Run: `uv run pytest tests/ -v`

**Commit:** `feat: simplify skill_crud — remove role-based permissions`

---

## Task 4: Remove Old CRUD Modules

Delete role_crud.py, scope_crud.py, commitment_crud.py and their tests.

**Files:**
- Delete: `src/crud/role_crud.py`
- Delete: `src/crud/scope_crud.py`
- Delete: `src/crud/commitment_crud.py`
- Delete: `tests/test_role_crud.py`
- Delete: `tests/test_scope_commitment_crud.py`

**Step 1:** Delete files

**Step 2:** Run all tests — verify no imports break

Run: `uv run pytest tests/ -v`

**Step 3:** Fix any broken imports in session.py, export.py, etc.

**Commit:** `refactor: remove role/scope/commitment CRUD modules (App-level concepts)`

---

## Task 5: Rewrite Export Adapters

Replace single Socialwares export with adapter pattern supporting 5 formats.

**Files:**
- Rewrite: `src/crud/export.py`
- Create: `src/adapters/__init__.py`
- Create: `src/adapters/gitagent.py`
- Create: `src/adapters/claude_code.py`
- Create: `src/adapters/codex.py`
- Create: `src/adapters/cursor.py`
- Create: `src/adapters/socialwares.py`
- Test: `tests/test_export.py`

**Step 1: Write failing tests**

```python
def test_export_gitagent_format(db, user_id, tmp_path):
    """GitAgent export creates agent.yaml + SOUL.md + skills/."""
    # Create agent with role_md + skill
    agent = asyncio.run(create_agent(db, user_id, "test", "desc", "# Test\nYou test."))
    asyncio.run(create_skill(db, agent["id"], "check", "# Check\n...", "check stuff"))
    from src.adapters.gitagent import GitAgentAdapter
    result = asyncio.run(GitAgentAdapter.export(db, agent["id"], tmp_path / "out"))
    assert (tmp_path / "out" / "agent.yaml").exists()
    assert (tmp_path / "out" / "SOUL.md").exists()
    assert (tmp_path / "out" / "skills" / "check" / "SKILL.md").exists()


def test_export_claude_code_format(db, user_id, tmp_path):
    """Claude Code export creates CLAUDE.md + .claude/skills/."""
    agent = asyncio.run(create_agent(db, user_id, "test", "desc", "# Test"))
    from src.adapters.claude_code import ClaudeCodeAdapter
    result = asyncio.run(ClaudeCodeAdapter.export(db, agent["id"], tmp_path / "out"))
    assert (tmp_path / "out" / "CLAUDE.md").exists()


def test_export_cursor_format(db, user_id, tmp_path):
    """Cursor export creates .cursor/rules."""
    agent = asyncio.run(create_agent(db, user_id, "test", "desc", "# Test"))
    from src.adapters.cursor import CursorAdapter
    result = asyncio.run(CursorAdapter.export(db, agent["id"], tmp_path / "out"))
    assert (tmp_path / "out" / ".cursor" / "rules").exists()
```

**Step 2: Implement each adapter**

Each adapter has the same interface:

```python
class BaseExportAdapter:
    @staticmethod
    async def export(db: Database, agent_id: str, output_dir: Path) -> dict:
        """Export agent to platform-specific format. Returns {agent_name, output_dir, files}."""
        ...
```

**GitAgentAdapter** generates:
- `agent.yaml` — name, version, description, skills list
- `SOUL.md` — from role_md
- `skills/{name}/SKILL.md` — from each skill

**ClaudeCodeAdapter** generates:
- `CLAUDE.md` — merged role_md + skills descriptions
- `.claude/skills/{name}/SKILL.md`

**CodexAdapter** generates:
- `AGENTS.md` — merged role_md + skills
- `.agents/skills/{name}/SKILL.md`

**CursorAdapter** generates:
- `.cursor/rules` — single merged file

**SocialwaresAdapter** generates:
- `agent/role/default.md`, `agent/scope/scope.md` (auto), `agent/flow/*/SKILL.md`, `flow.yaml`, `deploy.sh`, etc.

**Step 3: Update export.py to dispatch to adapters**

```python
ADAPTERS = {
    "gitagent": GitAgentAdapter,
    "claude-code": ClaudeCodeAdapter,
    "codex": CodexAdapter,
    "cursor": CursorAdapter,
    "socialwares": SocialwaresAdapter,
}

async def export_agent(db, agent_id, output_dir, format="gitagent"):
    adapter = ADAPTERS.get(format)
    if not adapter:
        raise ValueError(f"Unknown format: {format}")
    return await adapter.export(db, agent_id, output_dir)
```

**Step 4: Update /api/export endpoint to accept format parameter**

```python
@app.get("/api/export/{agent_id}")
async def export_download(agent_id: str, format: str = "gitagent", request: Request = None):
    ...
```

**Step 5:** Run tests, commit

```bash
git commit -m "feat: multi-format export adapters (gitagent/claude/codex/cursor/socialwares)"
```

---

## Task 6: Rewrite Import with Auto-Detection

**Files:**
- Rewrite: `src/crud/import_agent.py`
- Test: `tests/test_import.py`

**Key logic:**

```python
def detect_format(source_dir: Path) -> str:
    if (source_dir / "agent.yaml").exists():
        return "gitagent"
    if (source_dir / "CLAUDE.md").exists() or (source_dir / ".claude").exists():
        return "claude-code"
    if (source_dir / ".cursor" / "rules").exists():
        return "cursor"
    if (source_dir / "AGENTS.md").exists() or (source_dir / ".agents").exists():
        return "codex"
    if (source_dir / "agent" / "role").exists():
        return "socialwares"
    raise ValueError("Unknown format")
```

Each format has a reverse parser that extracts `name`, `role_md`, `skills[]`.

**Tests:** Import roundtrip for each format — export → import → verify data matches.

**Commit:** `feat: multi-format import with auto-detection`

---

## Task 7: Simplify Create Wizard (7 Steps → 3 Steps)

**Files:**
- Modify: `src/session.py` — `_handle_create_wizard`

**New flow:**

```
/create-agent
  → Step 1: Agent 名称
  → Step 2: 身份描述 (role_md)
  → Step 3: 添加技能 (manual / find / URL, or skip)
  → 确认创建
```

Remove: model selection, scope, roles, commitment steps.

**Step 1:** Rewrite `_handle_create_wizard` in session.py
**Step 2:** Update `test_chat_api.py` tests
**Step 3:** Run all tests

**Commit:** `feat: simplify create wizard — 3 steps (name + role_md + skills)`

---

## Task 8: Add find_skill Command

**Files:**
- Create: `src/crud/find_skill.py`
- Modify: `src/session.py` — add `/find-skill` handler
- Test: `tests/test_find_skill.py`

**Sources:**
1. **Local** — query skills table for current user's other agents
2. **Built-in** — scan template `agent/flow/*/SKILL.md` files
3. **URL** — HTTP GET a SKILL.md URL

**Interface:**

```python
async def search_skills(db: Database, user_id: str, query: str) -> list[dict]:
    """Search local + built-in skills matching query."""

async def import_skill_from_url(url: str) -> dict:
    """Fetch SKILL.md from URL, parse frontmatter."""
```

**Commit:** `feat: add find_skill — search local/built-in skills + URL import`

---

## Task 9: Update Seed Example Agent

Update `src/seed.py` to match simplified model (role_md instead of separate roles/scope/commitment).

**Files:**
- Rewrite: `src/seed.py`

**Step 1:** Rewrite seed to use new `create_agent(db, user_id, name, desc, role_md)` + `create_skill(db, agent_id, name, skill_md, desc)`

**Commit:** `refactor: update seed example agent for simplified model`

---

## Task 10: Update Frontend — Commands + AgentCard

**Files:**
- Modify: `app/src/components/chat-panel.tsx` — update COMMANDS, add `/find-skill`
- Modify: `app/src/components/cards/agent-card.tsx` — remove model badge, show role_md preview
- Modify: `app/src/components/agent-detail.tsx` — remove Scope/Commitment sections, show role_md + skills only
- Modify: `app/src/components/structured-block-renderer.tsx` — update DeployLog for format selection

**Step 1:** Update COMMANDS array:

```typescript
const COMMANDS = [
  { slash: "/create-agent", desc: "Create a new Agent" },
  { slash: "/list-agents", desc: "View all your Agents" },
  { slash: "/add-skill", desc: "Add a skill to an Agent" },
  { slash: "/find-skill", desc: "Search existing skills" },
  { slash: "/export-agent", desc: "Export Agent (multi-format)" },
  { slash: "/import-agent", desc: "Import Agent config" },
  { slash: "/delete-agent", desc: "Delete an Agent" },
];
```

Remove: `/add-role`, `/edit-scope`

**Step 2:** Update AgentCard — show `role_md_preview` instead of model badge

**Step 3:** Update AgentDetail — only show role_md + skills sections (remove Scope/Commitment)

**Step 4:** Update DeployLog — add format selector buttons for export

**Step 5:** Verify: `npx tsc --noEmit`

**Commit:** `feat: update frontend for simplified Agent model`

---

## Task 11: Update Export Flow in Session.py

**Files:**
- Modify: `src/session.py` — export handler adds format selection step

**New flow:**

```
/export-agent
  → Step 1: 选择 Agent
  → Step 2: 选择导出格式
      1. gitagent (推荐)
      2. claude-code
      3. codex
      4. cursor
      5. socialwares
  → 下载 zip
```

**Commit:** `feat: export with format selection (5 formats)`

---

## Task 12: Run Full Test Suite + Cleanup

**Step 1:** Run all tests

```bash
cd .socialware/workspace/my-team/agentforge
uv run pytest tests/ -v
```

**Step 2:** Run frontend build

```bash
cd app && npx tsc --noEmit && npx next build
```

**Step 3:** Delete old DB and restart

```bash
rm -f .runtime/data/Sqlite/agentforge.db
uv run uvicorn src.app:app --port 8001 --reload
```

**Step 4:** Manual verification:
- Login → /create-agent (3 steps) → /list-agents → View → /export-agent (select format) → download zip → verify contents

**Commit:** `chore: Phase 5 complete — simplified model + multi-format export`

---

## Dependencies

```
Task 1 (DB Schema)
  ├── Task 2 (agent_crud)
  ├── Task 3 (skill_crud)
  ├── Task 4 (remove old CRUDs)
  │     ├── Task 5 (export adapters)
  │     ├── Task 6 (import multi-format)
  │     └── Task 7 (create wizard)
  ├── Task 8 (find_skill) ← independent after Task 1
  └── Task 9 (seed) ← after Task 2+3

Task 10 (frontend) ← after Task 2+5
Task 11 (export flow) ← after Task 5
Task 12 (final validation) ← after all
```

**Parallelizable:** Tasks 5, 6, 7, 8 can run in parallel after Task 4.
