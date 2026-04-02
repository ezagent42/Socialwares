"""Import agent — auto-detect format and parse to role_md + skills."""
from __future__ import annotations
import re
from pathlib import Path
import yaml
from src.db import Database
from src.crud.agent_crud import create_agent
from src.crud.skill_crud import create_skill


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
    raise ValueError("Unknown format — cannot detect agent config in this directory")


def _parse_gitagent(source_dir: Path) -> dict:
    data = yaml.safe_load((source_dir / "agent.yaml").read_text())
    name = data.get("name", "imported-agent")
    desc = data.get("description", "")
    role_md = ""
    if (source_dir / "SOUL.md").exists():
        role_md = (source_dir / "SOUL.md").read_text()
    skills = []
    skills_dir = source_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_md = (skill_dir / "SKILL.md").read_text()
                skills.append({"name": skill_dir.name, "skill_md": skill_md, "description": ""})
    return {"name": name, "description": desc, "role_md": role_md, "skills": skills}


def _parse_claude_code(source_dir: Path) -> dict:
    role_md = ""
    if (source_dir / "CLAUDE.md").exists():
        role_md = (source_dir / "CLAUDE.md").read_text()
    name = "imported-agent"
    match = re.search(r'^#\s+(.+)', role_md)
    if match:
        name = re.sub(r'[^\w\-]', '_', match.group(1).strip()).strip('_') or "imported-agent"
    skills = []
    skills_dir = source_dir / ".claude" / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append({"name": skill_dir.name, "skill_md": (skill_dir / "SKILL.md").read_text(), "description": ""})
    return {"name": name, "description": "", "role_md": role_md, "skills": skills}


def _parse_codex(source_dir: Path) -> dict:
    role_md = ""
    if (source_dir / "AGENTS.md").exists():
        role_md = (source_dir / "AGENTS.md").read_text()
    name = "imported-agent"
    match = re.search(r'^#\s+(.+)', role_md)
    if match:
        name = re.sub(r'[^\w\-]', '_', match.group(1).strip()).strip('_') or "imported-agent"
    skills = []
    skills_dir = source_dir / ".agents" / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append({"name": skill_dir.name, "skill_md": (skill_dir / "SKILL.md").read_text(), "description": ""})
    return {"name": name, "description": "", "role_md": role_md, "skills": skills}


def _parse_cursor(source_dir: Path) -> dict:
    content = (source_dir / ".cursor" / "rules").read_text()
    name = "imported-agent"
    match = re.search(r'^#\s+(.+)', content)
    if match:
        name = re.sub(r'[^\w\-]', '_', match.group(1).strip()).strip('_') or "imported-agent"
    return {"name": name, "description": "", "role_md": content, "skills": []}


def _parse_socialwares(source_dir: Path) -> dict:
    role_md = ""
    role_dir = source_dir / "agent" / "role"
    if role_dir.exists():
        for f in role_dir.glob("*.md"):
            role_md = f.read_text()
            break
    name = "imported-agent"
    match = re.search(r'^#\s+(.+)', role_md)
    if match:
        name = re.sub(r'[^\w\-]', '_', match.group(1).strip()).strip('_') or "imported-agent"
    skills = []
    flow_dir = source_dir / "agent" / "flow"
    if flow_dir.exists():
        for skill_dir in flow_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append({"name": skill_dir.name, "skill_md": (skill_dir / "SKILL.md").read_text(), "description": ""})
    return {"name": name, "description": "", "role_md": role_md, "skills": skills}


_PARSERS = {
    "gitagent": _parse_gitagent,
    "claude-code": _parse_claude_code,
    "codex": _parse_codex,
    "cursor": _parse_cursor,
    "socialwares": _parse_socialwares,
}


async def import_agent(db: Database, user_id: str, source_dir: Path) -> dict:
    source_dir = Path(source_dir)
    fmt = detect_format(source_dir)
    parsed = _PARSERS[fmt](source_dir)

    agent = await create_agent(db, user_id, parsed["name"], parsed["description"], parsed["role_md"])
    for skill in parsed.get("skills", []):
        await create_skill(db, agent["id"], skill["name"], skill["skill_md"], skill.get("description", ""))

    from src.crud.agent_crud import get_agent
    full = await get_agent(db, user_id, agent["id"])
    full["source"] = "imported"
    full["format"] = fmt
    return full
