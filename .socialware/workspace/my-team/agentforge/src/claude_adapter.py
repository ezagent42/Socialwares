"""Claude Agent SDK adapter — sends user messages to Claude Agent with SOUL.md + SKILL.md context.

Uses claude-agent-sdk which leverages the local Claude Code CLI's OAuth authentication,
so no ANTHROPIC_API_KEY is needed — users just need Claude Code installed and logged in.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator


# Tool schemas — kept for reference and test validation.
# The actual MCP tools are created dynamically by _create_mcp_tools().
AGENT_TOOLS = [
    {
        "name": "list_agents",
        "description": "List all agents for the current user. Returns agent list with id, name, description, skills_count.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
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
        "description": "Get agent detail including all skills.",
        "input_schema": {
            "type": "object",
            "properties": {"agent_id": {"type": "string"}},
            "required": ["agent_id"],
        },
    },
    {
        "name": "delete_agent",
        "description": "Delete an agent and all its skills. This cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {"agent_id": {"type": "string"}},
            "required": ["agent_id"],
        },
    },
    {
        "name": "create_skill",
        "description": "Add a skill to an agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "skill_md": {"type": "string"},
            },
            "required": ["agent_id", "name", "skill_md"],
        },
    },
    {
        "name": "list_skills",
        "description": "List all skills for an agent.",
        "input_schema": {
            "type": "object",
            "properties": {"agent_id": {"type": "string"}},
            "required": ["agent_id"],
        },
    },
    {
        "name": "delete_skill",
        "description": "Delete a skill from an agent.",
        "input_schema": {
            "type": "object",
            "properties": {"skill_id": {"type": "string"}},
            "required": ["skill_id"],
        },
    },
    {
        "name": "export_agent",
        "description": "Export an agent configuration as a downloadable zip. Formats: gitagent, claude-code, codex, cursor, socialwares.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "format": {"type": "string", "enum": ["gitagent", "claude-code", "codex", "cursor", "socialwares"]},
            },
            "required": ["agent_id", "format"],
        },
    },
    {
        "name": "search_skills",
        "description": "Search for existing skills by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "import_agent",
        "description": "Import an agent configuration from a directory path. Auto-detects format.",
        "input_schema": {
            "type": "object",
            "properties": {"source_path": {"type": "string"}},
            "required": ["source_path"],
        },
    },
]


async def execute_tool(tool_name: str, tool_input: dict, user_id: str, db) -> dict:
    """Execute a CRUD tool and return the result as a dict."""
    from src.crud import agent_crud, skill_crud
    from src.crud.find_skill import search_skills
    from src.crud.export import export_agent_zip

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
            agent = await import_agent(db, user_id, Path(tool_input["source_path"]))
            return agent

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


def is_sdk_available() -> bool:
    """Check if Claude Agent SDK is available AND the Claude Code CLI works."""
    try:
        import claude_agent_sdk  # noqa: F401
        import subprocess, os
        sdk_dir = Path(claude_agent_sdk.__file__).parent
        cli_name = "claude.exe" if os.name == "nt" else "claude"
        cli_path = sdk_dir / "_bundled" / cli_name
        if not cli_path.exists():
            return False
        result = subprocess.run(
            [str(cli_path), "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (ImportError, Exception):
        return False


def _load_runtime_config(runtime_dir: Path) -> dict:
    """Load SOUL.md and skills from .runtime/agents/default/."""
    config = {"soul_md": "", "skills": [], "flow_yaml": ""}

    soul_path = runtime_dir / "SOUL.md"
    if soul_path.exists():
        config["soul_md"] = soul_path.read_text(encoding="utf-8")

    flow_path = runtime_dir / "flow.yaml"
    if flow_path.exists():
        config["flow_yaml"] = flow_path.read_text(encoding="utf-8")

    # Load skills from agent/flow/*/SKILL.md
    skills_root = runtime_dir.parent.parent.parent / "agent" / "flow"
    if skills_root.exists():
        for skill_dir in skills_root.iterdir():
            skill_file = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_file.exists():
                config["skills"].append({
                    "name": skill_dir.name,
                    "content": skill_file.read_text(encoding="utf-8"),
                })

    return config


def build_system_prompt(runtime_dir: Path, user_id: str, db_path: str) -> str:
    """Build the system prompt with SOUL.md, skills, and user context."""
    config = _load_runtime_config(runtime_dir)

    parts = []

    # Identity
    if config["soul_md"]:
        parts.append(config["soul_md"])

    # User context
    parts.append(f"""
## Environment

- USER_ID: {user_id}
- DB_PATH: {db_path}
- WORKSPACE: {runtime_dir.parent.parent.parent}

When executing CRUD operations, use these values in CLI commands.
""")

    # Skills
    if config["skills"]:
        parts.append("## Available Skills\n")
        for skill in config["skills"]:
            parts.append(f"### {skill['name']}\n\n{skill['content']}\n")

    # Structured output format (kept concise to avoid Windows CLI arg length limits)
    parts.append("""## Response Format

Include a `json:structured` fenced block when tool results should render as UI. Format:
```json:structured
{"type": "<type>", "action": "<action>", "data": {<tool result>}}
```

Types: agent(listed/created/updated/deleted/confirm_required), skill(created/listed/deleted), deploy(exported).
For listed: wrap in {"agents":[...]} or {"skills":[...]}. For exported: {"downloads":[{"name","download_url","format"}]}.
Confirm before delete. Export formats: gitagent, claude-code, codex, cursor, socialwares.
""")

    return "\n\n".join(parts)


_SDK_SYSTEM_PROMPT = """\
You are AgentForge, an AI Agent configuration management assistant.
You have MCP tools for CRUD operations on Agents and Skills. Use them to fulfill user requests.

## Tool Workflows

When creating an agent:
- Ask for name, then description, then role_md (identity). If user gives a vague description like \
"help me fill this in", generate a proper role_md based on the agent's name and purpose.

When user asks to find/search a skill and add it:
1. ALWAYS call search_skills first with the keyword
2. If results found: show them, let user pick one, then use its skill_md to call create_skill
3. If NO results found: tell the user nothing was found. Then generate a draft skill_md \
yourself and SHOW IT TO THE USER for review. Only call create_skill after user confirms or \
provides edits. NEVER create a skill without user confirmation.

When user says "help me fill in/补充" or gives a vague description: generate a draft, \
show it to the user, and wait for confirmation before saving. Do NOT store the user's \
instruction text as content.

## Response Format

After tool calls, include a json:structured fenced block so the frontend renders UI:
```json:structured
{"type": "<type>", "action": "<action>", "data": {<tool result>}}
```
Types: agent(listed/created/updated/deleted), skill(created/listed/deleted), deploy(exported).
For list results wrap as {"agents":[...]} or {"skills":[...]}.
For export wrap as {"downloads":[{"name","download_url","format"}]}.
Confirm with user before deleting. Export formats: gitagent, claude-code, codex, cursor, socialwares.
Reply in the same language the user uses.
"""


def _create_mcp_tools(db, user_id: str) -> list:
    """Create MCP tool functions bound to a specific db and user_id via closure."""
    import asyncio
    from claude_agent_sdk import tool

    def _result(data: dict) -> dict:
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}

    def _run(coro):
        """Run async CRUD in the current or new event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    @tool("list_agents", "List all agents for the current user. Returns agent list with id, name, description, skills_count.", {})
    async def list_agents_tool(args):
        result = await execute_tool("list_agents", args, user_id, db)
        return _result(result)

    @tool("create_agent", "Create a new agent. Requires name and role_md (identity description in markdown).", {"name": str, "description": str, "role_md": str})
    async def create_agent_tool(args):
        result = await execute_tool("create_agent", args, user_id, db)
        return _result(result)

    @tool("get_agent", "Get agent detail including all skills. Use this to view an agent's full configuration.", {"agent_id": str})
    async def get_agent_tool(args):
        result = await execute_tool("get_agent", args, user_id, db)
        return _result(result)

    @tool("delete_agent", "Delete an agent and all its skills. This cannot be undone.", {"agent_id": str})
    async def delete_agent_tool(args):
        result = await execute_tool("delete_agent", args, user_id, db)
        return _result(result)

    @tool("create_skill", "Add a skill to an agent.", {"agent_id": str, "name": str, "description": str, "skill_md": str})
    async def create_skill_tool(args):
        result = await execute_tool("create_skill", args, user_id, db)
        return _result(result)

    @tool("list_skills", "List all skills for an agent.", {"agent_id": str})
    async def list_skills_tool(args):
        result = await execute_tool("list_skills", args, user_id, db)
        return _result(result)

    @tool("delete_skill", "Delete a skill from an agent.", {"skill_id": str})
    async def delete_skill_tool(args):
        result = await execute_tool("delete_skill", args, user_id, db)
        return _result(result)

    @tool("export_agent", "Export an agent config as a downloadable zip. Formats: gitagent, claude-code, codex, cursor, socialwares.", {"agent_id": str, "format": str})
    async def export_agent_tool(args):
        result = await execute_tool("export_agent", args, user_id, db)
        return _result(result)

    @tool("search_skills", "Search for existing skills by keyword. Searches local skills and built-in template skills.", {"query": str})
    async def search_skills_tool(args):
        result = await execute_tool("search_skills", args, user_id, db)
        return _result(result)

    @tool("import_agent", "Import an agent configuration from a directory path. Auto-detects format.", {"source_path": str})
    async def import_agent_tool(args):
        result = await execute_tool("import_agent", args, user_id, db)
        return _result(result)

    return [
        list_agents_tool, create_agent_tool, get_agent_tool, delete_agent_tool,
        create_skill_tool, list_skills_tool, delete_skill_tool,
        export_agent_tool, search_skills_tool, import_agent_tool,
    ]


async def send_to_agent(
    message: str,
    system_prompt: str,
    history: list[dict] | None = None,
    db=None,
    user_id: str = "",
    session: dict | None = None,
) -> AsyncIterator[str]:
    """Send message to Claude Agent via claude-agent-sdk with MCP tool use.

    Uses the local Claude Code CLI's OAuth authentication — no API key needed.
    The SDK handles the tool use loop automatically.

    Session persistence: stores `_sdk_session_id` in the session dict so
    subsequent messages resume the same Agent conversation, preserving context
    for multi-step flows (create wizard, etc.).
    """
    from claude_agent_sdk import (
        ClaudeSDKClient,
        ClaudeAgentOptions,
        AssistantMessage,
        ResultMessage,
        SystemMessage,
        TextBlock,
        create_sdk_mcp_server,
    )

    # Create MCP tools bound to this request's db + user_id
    tools = _create_mcp_tools(db, user_id) if db else []
    server = create_sdk_mcp_server("agentforge-tools", tools=tools) if tools else None

    # Check for existing SDK session to resume
    sdk_session_id = session.get("_sdk_session_id") if session else None

    opts_kwargs = {
        "max_turns": 10,
        "permission_mode": "bypassPermissions",
    }

    if sdk_session_id:
        # Resume existing Agent conversation — preserves full context
        opts_kwargs["resume"] = sdk_session_id
    else:
        # New conversation — set system prompt and MCP tools
        opts_kwargs["system_prompt"] = system_prompt

    if server:
        opts_kwargs["mcp_servers"] = {"agentforge": server}

    opts = ClaudeAgentOptions(**opts_kwargs)

    async with ClaudeSDKClient(options=opts) as client:
        await client.query(message)
        async for msg in client.receive_response():
            # Capture session_id from init message for future resumption
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                new_session_id = msg.data.get("session_id") if msg.data else None
                if new_session_id and session is not None:
                    session["_sdk_session_id"] = new_session_id
            elif isinstance(msg, ResultMessage):
                if msg.result:
                    yield msg.result
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield block.text
