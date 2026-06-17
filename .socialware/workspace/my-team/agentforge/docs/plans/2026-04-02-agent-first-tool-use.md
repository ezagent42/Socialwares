# Agent-First Tool Use Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route all user messages (slash commands + natural language) through Claude Agent with Tool Use, replacing hardcoded intent matching as the primary path.

**Architecture:** Claude Agent receives all messages, decides which CRUD tools to call, executes them via tool_use/tool_result loop, then composes a final response containing `json:structured` blocks for the frontend. Hardcoded handlers remain as fallback when no API key.

**Tech Stack:** Anthropic Python SDK (tool use), FastAPI, async CRUD functions, SQLite

---

### Task 1: Define Tool Schemas in claude_adapter.py

**Files:**
- Modify: `src/claude_adapter.py`

**Step 1: Write the failing test**

Create test that verifies tool definitions exist and have correct structure.

```python
# tests/test_claude_adapter.py (new file)
import pytest
from src.claude_adapter import AGENT_TOOLS


def test_agent_tools_defined():
    """All 10 CRUD tools should be defined with name, description, input_schema."""
    assert len(AGENT_TOOLS) == 10
    names = {t["name"] for t in AGENT_TOOLS}
    expected = {
        "list_agents", "create_agent", "get_agent", "delete_agent",
        "create_skill", "list_skills", "delete_skill",
        "export_agent", "search_skills", "import_agent",
    }
    assert names == expected
    for tool in AGENT_TOOLS:
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_claude_adapter.py::test_agent_tools_defined -v`
Expected: FAIL with "cannot import name 'AGENT_TOOLS'"

**Step 3: Write minimal implementation**

Add `AGENT_TOOLS` list to `src/claude_adapter.py`:

```python
AGENT_TOOLS = [
    {
        "name": "list_agents",
        "description": "List all agents for the current user. Returns agent list with id, name, description, skills_count.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_agent",
        "description": "Create a new agent. Requires name and role_md (identity description in markdown).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent name (alphanumeric + hyphens)"},
                "description": {"type": "string", "description": "Short description of the agent"},
                "role_md": {"type": "string", "description": "Agent identity description in markdown"},
            },
            "required": ["name", "role_md"],
        },
    },
    {
        "name": "get_agent",
        "description": "Get agent detail including all skills. Use this to view an agent's full configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "delete_agent",
        "description": "Delete an agent and all its skills. This cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "create_skill",
        "description": "Add a skill to an agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to add skill to"},
                "name": {"type": "string", "description": "Skill name"},
                "description": {"type": "string", "description": "Short skill description"},
                "skill_md": {"type": "string", "description": "Skill content in markdown"},
            },
            "required": ["agent_id", "name", "skill_md"],
        },
    },
    {
        "name": "list_skills",
        "description": "List all skills for an agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "delete_skill",
        "description": "Delete a skill from an agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill ID to delete"},
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "export_agent",
        "description": "Export an agent configuration as a downloadable zip in the specified format. Available formats: gitagent, claude-code, codex, cursor, socialwares.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to export"},
                "format": {
                    "type": "string",
                    "description": "Export format",
                    "enum": ["gitagent", "claude-code", "codex", "cursor", "socialwares"],
                },
            },
            "required": ["agent_id", "format"],
        },
    },
    {
        "name": "search_skills",
        "description": "Search for existing skills by keyword. Searches local skills and built-in template skills.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "import_agent",
        "description": "Import an agent configuration from a directory path. Auto-detects format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "description": "Path to the agent config directory or zip file"},
            },
            "required": ["source_path"],
        },
    },
]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_claude_adapter.py::test_agent_tools_defined -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_adapter.py tests/test_claude_adapter.py
git commit -m "feat: define CRUD tool schemas for Agent tool use"
```

---

### Task 2: Implement Tool Executor

**Files:**
- Modify: `src/claude_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_claude_adapter.py (append)
import asyncio
from src.db import Database
from src.claude_adapter import execute_tool


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'tester')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


def test_execute_tool_list_agents(db, user_id):
    result = asyncio.run(execute_tool("list_agents", {}, user_id, db))
    assert isinstance(result, dict)
    assert "agents" in result


def test_execute_tool_create_and_list(db, user_id):
    create_result = asyncio.run(execute_tool("create_agent", {
        "name": "test-bot",
        "description": "A test agent",
        "role_md": "# Test Bot\nYou are a test bot.",
    }, user_id, db))
    assert create_result["name"] == "test-bot"

    list_result = asyncio.run(execute_tool("list_agents", {}, user_id, db))
    assert any(a["name"] == "test-bot" for a in list_result["agents"])


def test_execute_tool_unknown():
    """Unknown tool should return error dict."""
    result = asyncio.run(execute_tool("unknown_tool", {}, "u1", None))
    assert "error" in result
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_claude_adapter.py::test_execute_tool_list_agents -v`
Expected: FAIL with "cannot import name 'execute_tool'"

**Step 3: Write minimal implementation**

Add `execute_tool()` function to `src/claude_adapter.py`:

```python
async def execute_tool(tool_name: str, tool_input: dict, user_id: str, db: Database) -> dict:
    """Execute a CRUD tool and return the result as a dict."""
    from src.crud import agent_crud, skill_crud
    from src.crud.find_skill import search_skills
    from src.crud.export import export_agent_zip, FORMATS

    try:
        if tool_name == "list_agents":
            agents = await agent_crud.list_agents(db, user_id)
            return {"agents": agents}

        elif tool_name == "create_agent":
            agent = await agent_crud.create_agent(
                db, user_id,
                tool_input["name"],
                tool_input.get("description", ""),
                tool_input["role_md"],
            )
            return agent

        elif tool_name == "get_agent":
            agent = await agent_crud.get_agent(db, user_id, tool_input["agent_id"])
            return agent

        elif tool_name == "delete_agent":
            result = await agent_crud.delete_agent(db, user_id, tool_input["agent_id"])
            return result

        elif tool_name == "create_skill":
            skill = await skill_crud.create_skill(
                db, tool_input["agent_id"],
                tool_input["name"],
                tool_input["skill_md"],
                tool_input.get("description", ""),
            )
            return skill

        elif tool_name == "list_skills":
            skills = await skill_crud.list_skills(db, tool_input["agent_id"])
            return {"skills": skills}

        elif tool_name == "delete_skill":
            result = await skill_crud.delete_skill(db, tool_input["skill_id"])
            return result

        elif tool_name == "export_agent":
            zip_path, agent_name = await export_agent_zip(
                db, tool_input["agent_id"], format=tool_input["format"],
            )
            return {
                "agent_name": agent_name,
                "format": tool_input["format"],
                "download_url": f"/api/export/{tool_input['agent_id']}?format={tool_input['format']}",
            }

        elif tool_name == "search_skills":
            results = await search_skills(db, user_id, tool_input["query"])
            return {"results": results}

        elif tool_name == "import_agent":
            from src.crud.import_agent import import_agent
            from pathlib import Path
            agent = await import_agent(db, user_id, Path(tool_input["source_path"]))
            return agent

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_claude_adapter.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add src/claude_adapter.py tests/test_claude_adapter.py
git commit -m "feat: implement tool executor for Agent CRUD operations"
```

---

### Task 3: Implement Tool Use Loop in send_to_agent

**Files:**
- Modify: `src/claude_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_claude_adapter.py (append)

def test_send_to_agent_has_tools_param():
    """send_to_agent should accept db and user_id params for tool execution."""
    import inspect
    from src.claude_adapter import send_to_agent
    sig = inspect.signature(send_to_agent)
    params = list(sig.parameters.keys())
    assert "db" in params
    assert "user_id" in params
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_claude_adapter.py::test_send_to_agent_has_tools_param -v`
Expected: FAIL — current `send_to_agent` doesn't have `db` or `user_id` params

**Step 3: Rewrite send_to_agent with tool use loop**

Replace the existing `send_to_agent()` in `src/claude_adapter.py`:

```python
async def send_to_agent(
    message: str,
    system_prompt: str,
    history: list[dict] | None = None,
    db: Database = None,
    user_id: str = "",
) -> AsyncIterator[str]:
    """Send message to Claude Agent with tool use support.

    If db and user_id are provided, enables tool use loop:
    1. Send message + tools to Claude
    2. If Claude returns tool_use, execute locally and send tool_result back
    3. Repeat until Claude returns a final text response
    """
    import anthropic

    client = anthropic.AsyncAnthropic()

    messages = []
    if history:
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    # Use tools only when db is available
    tools = AGENT_TOOLS if db else None

    while True:
        kwargs = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.messages.create(**kwargs)

        # Check if response contains tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final text response — yield all text blocks
            for block in response.content:
                if block.type == "text":
                    yield block.text
            break

        # Execute tools and build tool_result message
        # First, add assistant's response (with tool_use) to messages
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_use_blocks:
            result = await execute_tool(tool_block.name, tool_block.input, user_id, db)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        messages.append({"role": "user", "content": tool_results})

        # Safety: max 5 tool-use rounds to prevent infinite loop
        if len([m for m in messages if m["role"] == "user"]) > 7:
            yield "Too many tool calls, stopping."
            break
```

Note: this replaces streaming with non-streaming `messages.create()` since tool use requires seeing the full response to detect tool_use blocks. Add `import json` at top of file if not already present.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_claude_adapter.py::test_send_to_agent_has_tools_param -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_adapter.py tests/test_claude_adapter.py
git commit -m "feat: implement tool use loop in send_to_agent"
```

---

### Task 4: Update System Prompt with Structured Output Format

**Files:**
- Modify: `src/claude_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_claude_adapter.py (append)

def test_system_prompt_includes_structured_format(tmp_path):
    from src.claude_adapter import build_system_prompt
    prompt = build_system_prompt(tmp_path, "u1", "test.db")
    assert "json:structured" in prompt
    assert "type" in prompt and "action" in prompt
    assert "agent" in prompt and "listed" in prompt
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_claude_adapter.py::test_system_prompt_includes_structured_format -v`
Expected: FAIL — current system prompt doesn't mention structured format

**Step 3: Add structured format documentation to build_system_prompt**

In `build_system_prompt()`, add a new section after the skills section:

```python
    # Structured output format
    parts.append("""
## Response Format

After executing tool calls, compose a response for the user. When the response includes data that should be rendered as UI components, include a `json:structured` code block. The frontend uses `type` + `action` to select the component.

### Supported structured types:

| type | action | data shape | when to use |
|------|--------|------------|-------------|
| agent | listed | `{"agents": [...]}` | After list_agents — show agent cards |
| agent | created | `{"id", "name", "description", "role_md", "skills": []}` | After create_agent |
| agent | updated | same as created | After get_agent or update |
| agent | deleted | `{"id", "name"}` | After delete_agent |
| agent | confirm_required | `{"message", "confirm_label", "cancel_label"}` | Before destructive actions |
| skill | created | `{"id", "agent_id", "name", "skill_md"}` | After create_skill |
| skill | listed | `{"skills": [...]}` | After list_skills |
| skill | deleted | `{"id", "name"}` | After delete_skill |
| deploy | exported | `{"downloads": [{"name", "download_url", "format"}]}` | After export_agent |

### Example response with structured data:

Found 2 agent(s).

```json:structured
{"type": "agent", "action": "listed", "data": {"agents": [{"id": "abc123", "name": "chatbot", "description": "A helpful chatbot", "is_example": false, "skills_count": 3}]}}
```

### Important rules:
- Always include structured data when a tool returns displayable results
- The `json:structured` block must be valid JSON on a single logical block
- Text before/after the block is shown as chat text
- For delete operations, ask the user to confirm before calling delete_agent/delete_skill
- When creating an agent, guide the user through providing: name, description, and role_md (identity)
- Available export formats: gitagent, claude-code, codex, cursor, socialwares
""")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_claude_adapter.py::test_system_prompt_includes_structured_format -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_adapter.py tests/test_claude_adapter.py
git commit -m "feat: add structured output format docs to Agent system prompt"
```

---

### Task 5: Update session.py Routing

**Files:**
- Modify: `src/session.py`
- Modify: `tests/test_chat_api.py`

**Step 1: Write the failing test**

```python
# tests/test_chat_api.py (append or modify existing test)

@pytest.mark.asyncio
async def test_slash_command_routes_to_sdk_when_available(db, user_id, monkeypatch):
    """Slash commands should also go through SDK when API key is set."""
    from src.session import _should_use_sdk
    session = {"user_id": user_id}

    # Mock SDK as available
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("src.claude_adapter.is_sdk_available", lambda: True)

    # Slash commands should now return True (not be bypassed)
    assert _should_use_sdk("/list-agents", session) is True
    assert _should_use_sdk("/create-agent", session) is True
    assert _should_use_sdk("/export-agent", session) is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_chat_api.py::test_slash_command_routes_to_sdk_when_available -v`
Expected: FAIL — `_should_use_sdk` currently returns False for slash commands

**Step 3: Update _should_use_sdk and _handle_via_sdk**

In `src/session.py`, modify `_should_use_sdk()`:

```python
def _should_use_sdk(message: str, session: dict) -> bool:
    """Determine if message should be routed to Claude SDK Agent."""
    from src.claude_adapter import is_sdk_available

    if not is_sdk_available():
        return False

    # Don't use SDK if there's a pending multi-step flow
    # (this is for fallback flows only — SDK handles its own multi-turn)
    for key in _PENDING_KEYS:
        if session.get(key):
            return False

    return True
```

Changes:
- Removed the `message.strip().startswith("/")` check — slash commands now go through SDK
- Removed the confirm/cancel bypass — Agent handles confirmations in conversation context
- Kept pending flow check for safety (fallback flows in progress)

Update `_handle_via_sdk()` to pass `db` and `user_id`:

```python
async def _handle_via_sdk(message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    """Route message to Claude Agent via SDK with tool use."""
    from src.claude_adapter import build_system_prompt, send_to_agent

    system_prompt = build_system_prompt(_RUNTIME_DIR, user_id, str(db.db_path))

    full_response = ""
    async for chunk in send_to_agent(
        message, system_prompt, session.get("history"),
        db=db, user_id=user_id,
    ):
        full_response += chunk

    clean_text, structured = parse_agent_response(full_response)
    return clean_text, structured
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_chat_api.py -v`
Expected: All existing tests PASS (they don't set ANTHROPIC_API_KEY so they still use fallback path)

**Step 5: Commit**

```bash
git add src/session.py tests/test_chat_api.py
git commit -m "feat: route all messages through Agent SDK when available"
```

---

### Task 6: Integration Test with Mocked SDK

**Files:**
- Create: `tests/test_tool_use_integration.py`

**Step 1: Write the integration test**

This test mocks the Anthropic SDK to verify the full flow without needing a real API key.

```python
"""Integration test: Agent tool use loop with mocked Claude SDK."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.db import Database
from src.claude_adapter import execute_tool, send_to_agent, build_system_prompt, AGENT_TOOLS


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    asyncio.run(database.init())
    return database


@pytest.fixture
def user_id(db):
    async def _setup():
        conn = await db.connect()
        await conn.execute("INSERT INTO users (id, github_id, github_login) VALUES ('u1', 1, 'tester')")
        await conn.commit()
        await conn.close()
        return "u1"
    return asyncio.run(_setup())


def test_tool_execute_create_get_delete(db, user_id):
    """Full lifecycle: create → get → delete via execute_tool."""
    # Create
    agent = asyncio.run(execute_tool("create_agent", {
        "name": "lifecycle-bot",
        "description": "test lifecycle",
        "role_md": "# Lifecycle Bot",
    }, user_id, db))
    assert agent["name"] == "lifecycle-bot"
    agent_id = agent["id"]

    # Get
    detail = asyncio.run(execute_tool("get_agent", {"agent_id": agent_id}, user_id, db))
    assert detail["name"] == "lifecycle-bot"
    assert detail["role_md"] == "# Lifecycle Bot"

    # Create skill
    skill = asyncio.run(execute_tool("create_skill", {
        "agent_id": agent_id,
        "name": "greet",
        "description": "Greeting skill",
        "skill_md": "# Greet\nSay hello.",
    }, user_id, db))
    assert skill["name"] == "greet"

    # List skills
    skills = asyncio.run(execute_tool("list_skills", {"agent_id": agent_id}, user_id, db))
    assert len(skills["skills"]) == 1

    # Delete skill
    del_skill = asyncio.run(execute_tool("delete_skill", {"skill_id": skill["id"]}, user_id, db))
    assert del_skill["name"] == "greet"

    # Delete agent
    deleted = asyncio.run(execute_tool("delete_agent", {"agent_id": agent_id}, user_id, db))
    assert deleted["name"] == "lifecycle-bot"

    # Verify gone
    result = asyncio.run(execute_tool("get_agent", {"agent_id": agent_id}, user_id, db))
    assert "error" in result


def test_tool_execute_search_skills(db, user_id):
    """search_skills tool returns results list."""
    result = asyncio.run(execute_tool("search_skills", {"query": "manage"}, user_id, db))
    assert "results" in result
    assert isinstance(result["results"], list)


def test_tool_execute_export_agent(db, user_id):
    """export_agent tool returns download URL."""
    agent = asyncio.run(execute_tool("create_agent", {
        "name": "export-test",
        "description": "",
        "role_md": "# Export Test",
    }, user_id, db))

    result = asyncio.run(execute_tool("export_agent", {
        "agent_id": agent["id"],
        "format": "gitagent",
    }, user_id, db))
    assert "download_url" in result
    assert "gitagent" in result["download_url"]
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_tool_use_integration.py -v`
Expected: PASS (all 3 tests)

**Step 3: Commit**

```bash
git add tests/test_tool_use_integration.py
git commit -m "test: add tool use integration tests with full CRUD lifecycle"
```

---

### Task 7: Clean Up Old Slash Command Handlers (Optional)

**Files:**
- Modify: `src/session.py`

**Note:** The old slash command handlers in `_handle_natural_language()` remain as fallback when SDK is not available. No code needs to be removed — they only execute when `_should_use_sdk()` returns False (no API key). This task is about verifying the fallback still works.

**Step 1: Run the full test suite**

Run: `uv run pytest -v`
Expected: All existing tests PASS — they don't set ANTHROPIC_API_KEY so they all use the fallback path.

**Step 2: Verify no regressions**

Confirm these test files all pass:
- `tests/test_chat_api.py` (13 tests)
- `tests/test_agent_crud.py`
- `tests/test_db.py`
- `tests/test_export.py`
- `tests/test_import.py`
- `tests/test_e2e_export_import.py`
- `tests/test_e2e_workflow.py`
- `tests/test_e2e_isolation.py`
- `tests/test_claude_adapter.py` (new, 6 tests)
- `tests/test_tool_use_integration.py` (new, 3 tests)

**Step 3: Commit (if any fixes needed)**

```bash
git commit -m "test: verify full test suite passes with agent-first routing"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/claude_adapter.py` | Add `AGENT_TOOLS` (10 tools), `execute_tool()`, rewrite `send_to_agent()` with tool use loop, add structured format docs to `build_system_prompt()` |
| `src/session.py` | Remove slash command bypass in `_should_use_sdk()`, pass `db`/`user_id` to `send_to_agent()` |
| `tests/test_claude_adapter.py` | New: tool schema tests, execute_tool tests, system prompt test |
| `tests/test_tool_use_integration.py` | New: full lifecycle integration tests |

## Execution Flow After Implementation

```
User: "/list-agents" or "列出所有agent"
  │
  ├── SDK available?
  │   ├── YES → send_to_agent(message, tools=AGENT_TOOLS)
  │   │         → Claude thinks → calls list_agents tool
  │   │         → execute_tool("list_agents", {}) → returns agents
  │   │         → Claude composes response with json:structured block
  │   │         → parse_agent_response() → (text, structured)
  │   │         → SSE stream to frontend
  │   │
  │   └── NO → _handle_natural_language()
  │            → hardcoded intent match → agent_crud.list_agents()
  │            → returns (text, structured)
  │            → SSE stream to frontend
```
