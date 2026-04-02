"""Find and search existing skills from multiple sources."""
from __future__ import annotations
from pathlib import Path
from src.db import Database

# Built-in skills from AgentForge project
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_BUILTIN_SKILLS_DIR = _PROJECT_ROOT / "agent" / "flow"


async def search_skills(db: Database, user_id: str, query: str) -> list[dict]:
    """Search skills from local DB + built-in template skills."""
    query_lower = query.lower()
    results = []

    # Source 1: Local skills (from user's other agents)
    conn = await db.connect()
    try:
        cursor = await conn.execute(
            "SELECT s.id, s.name, s.description, s.skill_md, a.name as agent_name "
            "FROM skills s JOIN agents a ON s.agent_id = a.id "
            "WHERE a.user_id = ? OR a.is_example = 1",
            (user_id,)
        )
        for row in await cursor.fetchall():
            name, desc, skill_md, agent_name = row[1], row[2], row[3], row[4]
            if query_lower in (name or "").lower() or query_lower in (desc or "").lower() or query_lower in (skill_md or "").lower():
                results.append({
                    "name": name,
                    "description": desc,
                    "source": "local",
                    "agent_name": agent_name,
                    "preview": (skill_md or "")[:200],
                    "skill_md": skill_md,
                })
    finally:
        await conn.close()

    # Source 2: Built-in skills from template
    if _BUILTIN_SKILLS_DIR.exists():
        for skill_dir in _BUILTIN_SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            skill_md = skill_file.read_text(encoding="utf-8")
            name = skill_dir.name
            if query_lower in name.lower() or query_lower in skill_md.lower():
                # Don't add duplicates
                if not any(r["name"] == name and r["source"] == "builtin" for r in results):
                    results.append({
                        "name": name,
                        "description": f"Built-in: {name}",
                        "source": "builtin",
                        "agent_name": "(template)",
                        "preview": skill_md[:200],
                        "skill_md": skill_md,
                    })

    return results


async def import_skill_from_url(url: str) -> dict:
    """Fetch a SKILL.md from a URL and parse it."""
    import httpx
    import re

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.text

    # Parse frontmatter
    name = "imported-skill"
    description = ""
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')

    return {"name": name, "description": description, "skill_md": content}
