"""Claude SDK adapter — sends user messages to Claude Agent with SOUL.md + SKILL.md context."""
from __future__ import annotations

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
) -> AsyncIterator[str]:
    """Send message to Claude Agent and stream response chunks."""
    import anthropic

    client = anthropic.AsyncAnthropic()

    messages = []
    if history:
        for h in history[-10:]:  # Keep last 10 messages for context
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
