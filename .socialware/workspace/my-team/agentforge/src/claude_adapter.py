"""Claude SDK adapter — sends user messages to Claude Agent with SOUL.md + SKILL.md context."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncIterator


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
            from pathlib import Path
            agent = await import_agent(db, user_id, Path(tool_input["source_path"]))
            return agent

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


def is_sdk_available() -> bool:
    """Check if Claude SDK is available and configured."""
    try:
        import anthropic  # noqa: F401
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    except ImportError:
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

    return "\n\n".join(parts)


async def send_to_agent(
    message: str,
    system_prompt: str,
    history: list[dict] | None = None,
    db=None,
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
