# Phase 6: Agent SDK Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace session.py's hardcoded intent matching with real Agent (Claude SDK), so user messages are processed by an AI Agent that reads SKILL.md and calls CRUD functions.

**Architecture:** Session Manager loads `.runtime/agents/default/` RoleConfig, creates Claude SDK adapter, forwards user messages to Agent. Agent reads SOUL.md (identity) + SKILL.md (operations), decides what to do, calls CRUD via Bash tool, returns `json:structured` response. Session Manager parses structured blocks from Agent output and streams via SSE.

**Tech Stack:** Python 3.12+, claude-agent-sdk >= 0.1.16, FastAPI, aiosqlite

**Prerequisites:** Phase 5 complete (simplified DB, adapters, 45 tests passing)

**Design Ref:** [cms-design.md §6.3](../plans/2026-03-26-agentforge-cms-design.md)

---

## Task 1: Create CRUD CLI Scripts

Agent will call CRUD via Bash tool. Create standalone scripts that Agent can execute.

**Files:**
- Create: `src/crud/cli.py`
- Test: `tests/test_crud_cli.py`

**Step 1: Write the failing test**

```python
# tests/test_crud_cli.py
import pytest
import subprocess
import json
import asyncio


@pytest.fixture
def db_path(tmp_path):
    from src.db import Database
    db = Database(tmp_path / "test.db")
    asyncio.run(db.init())
    # Seed a user
    async def _seed():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'test')")
        await conn.commit()
        await conn.close()
    asyncio.run(_seed())
    return str(tmp_path / "test.db")


def test_cli_create_agent(db_path):
    result = subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "create-agent",
         "--db", db_path, "--user-id", "u1",
         "--name", "test-app", "--role-md", "# Test"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["name"] == "test-app"


def test_cli_list_agents(db_path):
    # Create first
    subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "create-agent",
         "--db", db_path, "--user-id", "u1",
         "--name", "a1", "--role-md", "# A1"],
        capture_output=True, text=True, cwd="."
    )
    result = subprocess.run(
        ["uv", "run", "python", "-m", "src.crud.cli", "list-agents",
         "--db", db_path, "--user-id", "u1"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data) >= 1
```

**Step 2: Implement src/crud/cli.py**

```python
"""CLI interface for CRUD operations — called by Agent via Bash tool."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from src.db import Database
from src.crud import agent_crud, skill_crud


async def cmd_create_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.create_agent(db, args.user_id, args.name, args.description or "", args.role_md or "")
    print(json.dumps(result, ensure_ascii=False))


async def cmd_list_agents(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.list_agents(db, args.user_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_get_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.get_agent(db, args.user_id, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_delete_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.delete_agent(db, args.user_id, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_create_skill(args):
    db = Database(args.db)
    await db.init()
    result = await skill_crud.create_skill(db, args.agent_id, args.name, args.skill_md or "", args.description or "")
    print(json.dumps(result, ensure_ascii=False))


async def cmd_list_skills(args):
    db = Database(args.db)
    await db.init()
    result = await skill_crud.list_skills(db, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(prog="crud-cli")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("create-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--role-md", default="")

    p = sub.add_parser("list-agents")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)

    p = sub.add_parser("get-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--agent-id", required=True)

    p = sub.add_parser("delete-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--agent-id", required=True)

    p = sub.add_parser("create-skill")
    p.add_argument("--db", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--skill-md", default="")
    p.add_argument("--description", default="")

    p = sub.add_parser("list-skills")
    p.add_argument("--db", required=True)
    p.add_argument("--agent-id", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "create-agent": cmd_create_agent,
        "list-agents": cmd_list_agents,
        "get-agent": cmd_get_agent,
        "delete-agent": cmd_delete_agent,
        "create-skill": cmd_create_skill,
        "list-skills": cmd_list_skills,
    }
    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
```

**Commit:** `feat: add CRUD CLI for Agent to call via Bash tool`

---

## Task 2: Update AgentForge SKILL.md Files for CLI Usage

Update each manage_* SKILL.md in `agent/flow/` to include concrete CLI commands the Agent can execute.

**Files:**
- Modify: `agent/flow/manage_agent/SKILL.md`
- Modify: `agent/flow/manage_skill/SKILL.md`
- Modify: `agent/flow/find_skill/SKILL.md`
- Modify: `agent/flow/export_agent/SKILL.md`

Each SKILL.md should include a "## How to Execute" section with:
```bash
uv run python -m src.crud.cli create-agent --db "$DB_PATH" --user-id "$USER_ID" --name "xxx" --role-md "# xxx"
```

**Commit:** `feat: update SKILL.md files with CLI execution commands`

---

## Task 3: Rewrite Session Manager for Agent SDK

Replace hardcoded intent matching in session.py with real Claude SDK adapter.

**Files:**
- Rewrite: `src/session.py`
- Test: `tests/test_chat_api.py`

**Key architecture:**

```python
class SessionManager:
    async def send(user_id, message, db):
        session = self.get_or_create(user_id)

        # 1. Build system prompt with user_id context
        system_prompt = f"Your user_id is: {user_id}\nDB path: {db.db_path}\n"

        # 2. Load adapter from .runtime/agents/default/
        config = RoleConfig.from_runtime(".runtime/agents/default/")
        adapter = ClaudeAdapter(config)

        # 3. Send message to Agent via SDK
        async for msg in adapter.launch_sdk(message):
            # 4. Parse structured blocks from Agent response
            # 5. Yield SSE events
```

**Fallback:** Keep hardcoded intent matching as fallback when Agent SDK is not available (no API key, no .runtime/).

**Commit:** `feat: integrate Claude SDK into Session Manager`

---

## Task 4: Agent Response Parser

Extract `json:structured` blocks from Agent's streaming response.

**Files:**
- Create: `src/response_parser.py`
- Test: `tests/test_response_parser.py`

**Logic:**
```python
def parse_agent_response(text: str) -> tuple[str, dict | None]:
    """Extract json:structured block from Agent response.
    Returns (clean_text, structured_data_or_none)
    """
```

**Commit:** `feat: add Agent response parser for structured blocks`

---

## Task 5: User Context Injection

Inject user_id and DB path into Agent's system prompt so Agent can call CRUD with correct user context.

**Files:**
- Modify: `src/session.py`

Agent's system prompt should include:
```
Environment:
- USER_ID: {user_id}
- DB_PATH: {db.db_path}
- WORKSPACE: {workspace_root}

When executing CRUD operations, use these values in CLI commands.
```

**Commit:** `feat: inject user context into Agent system prompt`

---

## Task 6: Deploy AgentForge for Agent SDK

Ensure `make deploy` generates correct `.runtime/agents/default/` with all manage_* skills linked.

**Files:**
- Verify: `agent/flow/flow.yaml` has all actions registered
- Run: `make deploy` and verify `.runtime/agents/default/SOUL.md` + `.claude/skills/`

**Commit:** `chore: verify deploy generates correct Agent runtime`

---

## Task 7: Integration Test — Agent-Driven CRUD

End-to-end test: send message via Session Manager → Agent processes → CRUD executed → structured response.

**Files:**
- Create: `tests/test_agent_integration.py`

**Note:** This test requires ANTHROPIC_API_KEY. Skip if not available.

```python
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
def test_agent_creates_agent_via_sdk():
    ...
```

**Commit:** `test: add Agent SDK integration test`

---

## Dependencies

```
Task 1 (CRUD CLI)
  └── Task 2 (SKILL.md updates)
        └── Task 3 (Session Manager rewrite)
              ├── Task 4 (Response parser)
              └── Task 5 (Context injection)
                    └── Task 6 (Deploy verify)
                          └── Task 7 (Integration test)
```
