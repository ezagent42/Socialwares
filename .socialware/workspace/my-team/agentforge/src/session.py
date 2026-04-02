"""Session Manager — manages per-user Agent sessions with real CRUD operations."""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import AsyncIterator

from pathlib import Path

from src.db import Database
from src.crud import agent_crud, skill_crud
from src.crud.find_skill import search_skills
from src.response_parser import parse_agent_response


class SessionManager:
    """Per-user Agent session management."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def get_or_create(self, user_id: str) -> dict:
        if user_id not in self._sessions:
            self._sessions[user_id] = {
                "user_id": user_id,
                "history": [],
                "connected": True,
            }
        return self._sessions[user_id]

    async def send(self, user_id: str, message: str, db: Database) -> AsyncIterator[dict]:
        """Send user message and stream response with real CRUD operations."""
        session = self.get_or_create(user_id)
        session["history"].append({"role": "user", "content": message})

        message_id = uuid.uuid4().hex[:12]

        # Save user message
        conn = await db.connect()
        try:
            await conn.execute(
                "INSERT INTO chat_history (user_id, session_id, role, content) VALUES (?, ?, ?, ?)",
                (user_id, "default", "user", message)
            )
            await conn.commit()
        finally:
            await conn.close()

        # Parse ui_action if present
        ui_action = _parse_ui_action(message)

        # Execute real operations
        try:
            if ui_action:
                response_text, structured = await _handle_ui_action(ui_action, user_id, db, session)
            elif _should_use_sdk(message, session):
                response_text, structured = await _handle_via_sdk(message, user_id, db, session)
            else:
                response_text, structured = await _handle_natural_language(message, user_id, db, session)
        except Exception as e:
            response_text = f"Error: {str(e)}"
            structured = None

        # Stream text
        if response_text.strip():
            yield {"event": "text", "data": json.dumps({"content": response_text})}
            await asyncio.sleep(0)

        # Stream structured data
        if structured:
            yield {"event": "structured", "data": json.dumps(structured)}

        # Save assistant message
        conn = await db.connect()
        try:
            await conn.execute(
                "INSERT INTO chat_history (user_id, session_id, role, content, structured) VALUES (?, ?, ?, ?, ?)",
                (user_id, "default", "assistant", response_text, json.dumps(structured) if structured else None)
            )
            await conn.commit()
        finally:
            await conn.close()

        session["history"].append({"role": "assistant", "content": response_text, "structured": structured})

        yield {"event": "done", "data": json.dumps({"message_id": message_id})}

    def disconnect(self, user_id: str):
        self._sessions.pop(user_id, None)


# ============================================================
# Create Agent wizard (multi-step, 3 steps)
# ============================================================

async def _handle_create_wizard(wiz: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()
    step = wiz.get("step")

    if text.lower() in ["cancel", "取消", "/cancel"]:
        session.pop("_pending_create", None)
        return "Agent creation cancelled.", None

    # Step 1: Name
    if step == "name":
        if not text:
            return "Please enter a valid name.", None
        wiz["name"] = text
        wiz["step"] = "role_md"
        return (
            "**Step 2/3 — Identity Description**\n\n"
            "Describe who this Agent is, what it does, and how it should respond.\n\n"
            "Example:\n```\n# Code Reviewer\n\nYou are a code review assistant.\n\n"
            "## Responsibilities\n- Review code for bugs and security issues\n- Suggest improvements\n\n"
            "## Tone\n- Constructive and specific\n```\n\n"
            "Type your description (Markdown):"
        ), None

    # Step 2: Role MD
    if step == "role_md":
        if text.lower() == "skip":
            wiz["role_md"] = f"# {wiz['name']}\n\nAgent for {wiz['name']}.\n"
        else:
            wiz["role_md"] = text
        wiz["step"] = "skills"
        return (
            "**Step 3/3 — Skills (optional)**\n\n"
            "Add skills this Agent can use. Type a skill name, or **done** to finish:"
        ), None

    # Step 3: Skills
    if step == "skills":
        if text.lower() in ["done", "skip", "完成", "跳过"]:
            wiz["step"] = "confirm"
            preview = (
                f"**Confirm Creation**\n\n"
                f"**Name:** {wiz['name']}\n"
                f"**Identity:** {wiz['role_md'][:100]}{'...' if len(wiz['role_md']) > 100 else ''}\n"
                f"**Skills:** {', '.join(s['name'] for s in wiz.get('skills_list', [])) or '(none)'}\n\n"
                f"Type **create** to confirm or **cancel** to abort."
            )
            return preview, None
        # Adding a skill
        wiz.setdefault("_current_skill", None)
        if wiz.get("_current_skill") is None:
            wiz["_current_skill"] = text
            return f"Describe the **{text}** skill (or **skip** for default):", None
        else:
            skill_name = wiz.pop("_current_skill")
            if text.lower() == "skip":
                skill_md = f"---\nname: {skill_name}\ndescription: \"{skill_name}\"\n---\n\n# {skill_name}\n\n## Trigger\n\nUser requests {skill_name}.\n\n## Flow\n\n1. Execute {skill_name}\n2. Return result\n"
                desc = skill_name
            else:
                skill_md = f"---\nname: {skill_name}\ndescription: \"{text[:80]}\"\n---\n\n# {skill_name}\n\n{text}\n"
                desc = text[:80]
            wiz.setdefault("skills_list", []).append({"name": skill_name, "skill_md": skill_md, "description": desc})
            return f"Skill **{skill_name}** added. Add another skill name, or **done** to finish:", None

    # Confirm
    if step == "confirm":
        if text.lower() in ["cancel", "取消", "no"]:
            session.pop("_pending_create", None)
            return "Agent creation cancelled.", None
        if text.lower() in ["create", "confirm", "yes", "确认", "创建"]:
            session.pop("_pending_create", None)
            try:
                agent = await agent_crud.create_agent(db, user_id, wiz["name"], "", wiz["role_md"])
                for skill_data in wiz.get("skills_list", []):
                    await skill_crud.create_skill(db, agent["id"], skill_data["name"], skill_data["skill_md"], skill_data["description"])
                agent = await agent_crud.get_agent(db, user_id, agent["id"])
                return f"Agent **{wiz['name']}** created successfully!", {"type": "agent", "action": "created", "data": agent}
            except ValueError as e:
                return str(e), None
        return "Type **create** to confirm or **cancel** to abort.", None

    session.pop("_pending_create", None)
    return "Something went wrong. Try /create-agent again.", None


# ============================================================
# Add Skill flow (multi-step)
# ============================================================

async def _handle_add_skill_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()
    step = flow.get("step")

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_add_skill", None)
        return "Cancelled.", None

    if step == "agent":
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == text.lower() and not a.get("is_example")), None)
        if not match:
            names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
            return f"Agent '{text}' not found. Your agents: {names}", None
        flow["agent_id"] = match["id"]
        flow["agent_name"] = match["name"]
        flow["step"] = "name"
        return (
            f"Adding skill to **{match['name']}**.\n\n"
            f"How would you like to add a skill?\n"
            f"  1. Type a skill name to create manually\n"
            f"  2. Type **search <keyword>** to find existing skills\n"
            f"  3. Type **url <url>** to import from URL"
        ), None

    if step == "name":
        # Option: search existing skills
        if text.lower().startswith("search "):
            query = text[7:].strip()
            if not query:
                return "Please provide a search keyword. Example: `search review`", None
            results = await search_skills(db, user_id, query)
            if not results:
                return f"No skills found for '{query}'. Type a skill name to create manually, or `search <keyword>` to try again.", None
            flow["search_results"] = results
            flow["step"] = "search_select"
            lines = [f"Found {len(results)} skill(s):\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"  {i}. **{r['name']}** ({r['source']}) — {r['description'][:60]}")
            lines.append(f"\nType a number to add, or **cancel**:")
            return "\n".join(lines), None

        # Option: import from URL
        if text.lower().startswith("url "):
            url = text[4:].strip()
            if not url:
                return "Please provide a URL. Example: `url https://example.com/SKILL.md`", None
            try:
                from src.crud.find_skill import import_skill_from_url
                imported = await import_skill_from_url(url)
                skill = await skill_crud.create_skill(db, flow["agent_id"], imported["name"], imported["skill_md"], imported["description"])
                session.pop("_pending_add_skill", None)
                return f"Skill **{imported['name']}** imported and added to {flow['agent_name']}.", {
                    "type": "skill", "action": "created", "data": {**skill, "agent_name": flow["agent_name"]}
                }
            except Exception as e:
                return f"Failed to import from URL: {e}\n\nType a skill name, `search <keyword>`, or `url <url>`:", None

        flow["skill_name"] = text
        flow["step"] = "desc"
        return f"Describe the **{text}** skill.\n\n1. When should it trigger?\n2. What does it do?\n\n(Type description or **skip** for default)", None

    if step == "search_select":
        try:
            idx = int(text) - 1
            results = flow.get("search_results", [])
            if 0 <= idx < len(results):
                selected = results[idx]
                skill = await skill_crud.create_skill(db, flow["agent_id"], selected["name"], selected["skill_md"], selected["description"])
                session.pop("_pending_add_skill", None)
                return f"Skill **{selected['name']}** added to {flow['agent_name']}.", {
                    "type": "skill", "action": "created", "data": {**skill, "agent_name": flow["agent_name"]}
                }
        except ValueError:
            pass
        session.pop("_pending_add_skill", None)
        return "Invalid selection. Try /add-skill again.", None

    if step == "desc":
        skill_name = flow["skill_name"]
        if text.lower() == "skip":
            skill_md = f"---\nname: {skill_name}\ndescription: \"{skill_name}\"\n---\n\n# {skill_name}\n\n## Trigger\n\nUser requests {skill_name}.\n\n## Flow\n\n1. Execute {skill_name}\n2. Return result\n"
            desc = skill_name
        else:
            skill_md = f"---\nname: {skill_name}\ndescription: \"{text[:80]}\"\n---\n\n# {skill_name}\n\n{text}\n"
            desc = text[:80]
        session.pop("_pending_add_skill", None)
        skill = await skill_crud.create_skill(db, flow["agent_id"], skill_name, skill_md, desc)
        return f"Skill **{skill_name}** added to {flow['agent_name']}.", {
            "type": "skill", "action": "created", "data": {**skill, "agent_name": flow["agent_name"]}
        }

    session.pop("_pending_add_skill", None)
    return "Something went wrong. Try /add-skill again.", None


# ============================================================
# Export Agent flow
# ============================================================

_EXPORT_FORMATS = ["gitagent", "claude-code", "codex", "cursor", "socialwares"]
_FORMAT_MENU = (
    "Select export format:\n\n"
    "1. **gitagent** — agent.yaml + SOUL.md + skills/ (推荐)\n"
    "2. **claude-code** — CLAUDE.md + .claude/skills/\n"
    "3. **codex** — AGENTS.md + .agents/skills/\n"
    "4. **cursor** — .cursor/rules\n"
    "5. **socialwares** — agent/role/ + flow/ + scope.md\n\n"
    "Type the format name or number (1-5):"
)

_FORMAT_ALIASES = {
    "1": "gitagent", "2": "claude-code", "3": "codex", "4": "cursor", "5": "socialwares",
}


async def _handle_export_agent_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_export_agent", None)
        return "Cancelled.", None

    if flow.get("step") == "agent":
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == text.lower()), None)
        if not match:
            names = ", ".join(f"`{a['name']}`" for a in agents)
            return f"Agent '{text}' not found. Available: {names}", None
        flow["agent"] = match
        flow["step"] = "format"
        return _FORMAT_MENU, None

    if flow.get("step") == "format":
        fmt = _FORMAT_ALIASES.get(text, text.lower())
        if fmt not in _EXPORT_FORMATS:
            return f"Unknown format '{text}'. Please enter a number 1-5 or format name.", None
        session.pop("_pending_export_agent", None)
        return _build_export_response([flow["agent"]], fmt)

    session.pop("_pending_export_agent", None)
    return "Something went wrong. Try /export-agent again.", None


# ============================================================
# Delete Agent flow
# ============================================================

async def _handle_delete_agent_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_delete_agent", None)
        return "Cancelled.", None

    if flow.get("step") == "agent":
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == text.lower() and not a.get("is_example")), None)
        if not match:
            names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
            return f"Agent '{text}' not found. Your agents: {names}", None
        session.pop("_pending_delete_agent", None)
        session["_pending_action"] = {"entity": "agent", "action": "delete", "targets": [match]}
        return f"Are you sure you want to delete Agent **{match['name']}**? This will remove all skills and configurations.", {
            "type": "agent", "action": "confirm_required",
            "data": {"message": f"Delete Agent '{match['name']}'? This cannot be undone.", "confirm_label": "Delete", "cancel_label": "Cancel"},
        }

    session.pop("_pending_delete_agent", None)
    return "Something went wrong. Try /delete-agent again.", None


# ============================================================
# Find Skill flow (multi-step)
# ============================================================

async def _handle_find_skill_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()
    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_find_skill", None)
        return "Cancelled.", None

    if flow["step"] == "query":
        results = await search_skills(db, user_id, text)
        if not results:
            session.pop("_pending_find_skill", None)
            return f"No skills found for '{text}'. Try a different keyword.", None
        flow["results"] = results
        flow["step"] = "select"
        lines = [f"Found {len(results)} skill(s):\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. **{r['name']}** ({r['source']}) — {r['description'][:60]}")
        lines.append(f"\nType a number to view details, or **cancel**:")
        return "\n".join(lines), {"type": "skill", "action": "listed", "data": {"query": text, "results": results}}

    if flow["step"] == "select":
        try:
            idx = int(text) - 1
            results = flow["results"]
            if 0 <= idx < len(results):
                selected = results[idx]
                session.pop("_pending_find_skill", None)
                return f"**{selected['name']}**\n\nSource: {selected['source']}\n\n```\n{selected['skill_md'][:500]}\n```\n\nUse `/add-skill` to add this to an Agent.", None
        except ValueError:
            pass
        session.pop("_pending_find_skill", None)
        return "Invalid selection. Try /find-skill again.", None

    session.pop("_pending_find_skill", None)
    return "Something went wrong. Try /find-skill again.", None


# ============================================================
# UI Action handler
# ============================================================

async def _handle_ui_action(ui_action: dict, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    """Handle structured UIAction from frontend."""
    entity = ui_action.get("entity", "")
    action = ui_action.get("action", "")
    targets = ui_action.get("targets", [])
    context = ui_action.get("context", {})

    # Confirm/cancel dialog
    if entity == "_dialog":
        pending = session.get("_pending_action")
        if action == "confirm" and pending:
            session.pop("_pending_action", None)
            return await _execute_pending(pending, user_id, db)
        else:
            session.pop("_pending_action", None)
            return "Operation cancelled.", None

    # Delete requires confirmation
    if action == "delete" and targets:
        names = ", ".join(t.get("name", t.get("id", "")) for t in targets)
        session["_pending_action"] = {"entity": entity, "action": action, "targets": targets}
        msg = f"Are you sure you want to delete {entity}: {names}?"
        structured = {
            "type": entity,
            "action": "confirm_required",
            "data": {"message": msg, "confirm_label": "Delete", "cancel_label": "Cancel"},
        }
        return msg, structured

    # Detail/view
    if action == "detail" and targets:
        return await _handle_detail(entity, targets[0], user_id, db)

    # Export — return download link for browser download
    if action == "export" and targets:
        return _build_export_response(targets)

    # Edit triggers editing mode
    if action == "edit" and targets:
        return await _handle_edit(entity, targets[0], user_id, db)

    # Update with context (from editor save)
    if action == "update" and targets and context:
        return await _handle_update(entity, targets[0], context, user_id, db)

    return f"Received {action} {entity} action.", None


async def _execute_pending(pending: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Execute a previously confirmed action."""
    entity = pending["entity"]
    targets = pending["targets"]

    if entity == "agent":
        results = []
        for t in targets:
            try:
                result = await agent_crud.delete_agent(db, user_id, t["id"])
                results.append(result)
            except ValueError as e:
                return str(e), None
        if len(results) == 1:
            return f"Agent '{results[0]['name']}' has been deleted.", {"type": "agent", "action": "deleted", "data": results[0]}
        names = ", ".join(r["name"] for r in results)
        return f"Deleted {len(results)} agents: {names}.", {"type": "agent", "action": "deleted", "data": {"deleted": results}}

    if entity == "skill":
        for t in targets:
            await skill_crud.delete_skill(db, t["id"])
        return f"Skill deleted.", {"type": "skill", "action": "deleted", "data": targets[0]}

    return "Deleted.", None


async def _handle_detail(entity: str, target: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Handle detail/view action — returns full agent info for detail panel."""
    if entity == "agent":
        try:
            agent = await agent_crud.get_agent(db, user_id, target["id"])
            # Enrich skills with full skill_md
            conn = await db.connect()
            try:
                enriched_skills = []
                for s in agent.get("skills", []):
                    cursor = await conn.execute("SELECT skill_md FROM skills WHERE id = ?", (s["id"],))
                    row = await cursor.fetchone()
                    skill_md = row[0] if row else ""
                    enriched_skills.append({**s, "skill_md": skill_md})
                agent["skills"] = enriched_skills
            finally:
                await conn.close()

            return f"Agent: {agent['name']}", {"type": "agent", "action": "detailed", "data": agent}
        except ValueError as e:
            return str(e), None
    return f"Detail view for {entity} is not yet supported.", None


def _build_export_response(targets: list, fmt: str = "gitagent") -> tuple[str, dict | None]:
    """Build export response with download links for the given format."""
    downloads = []
    for t in targets:
        downloads.append({
            "id": t.get("id", ""),
            "name": t.get("name", ""),
            "format": fmt,
            "download_url": f"/api/export/{t['id']}?format={fmt}",
        })

    if len(downloads) == 1:
        d = downloads[0]
        return f"Agent **{d['name']}** ({fmt}) is ready for download.", {
            "type": "deploy", "action": "exported",
            "data": {"agent_name": d["name"], "format": fmt, "download_url": d["download_url"], "downloads": downloads},
        }
    names = ", ".join(d["name"] for d in downloads)
    return f"{len(downloads)} agents ready for download ({fmt}): {names}", {
        "type": "deploy", "action": "exported",
        "data": {"format": fmt, "downloads": downloads},
    }


async def _handle_edit(entity: str, target: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Handle edit action — return current content for editor."""
    if entity == "agent":
        agent_id = target.get("id", "")
        try:
            agent = await agent_crud.get_agent(db, user_id, agent_id)
            return f"Editing agent: {agent['name']}", {"type": "agent", "action": "editing", "data": agent}
        except ValueError as e:
            return str(e), None

    if entity == "skill":
        conn = await db.connect()
        try:
            cursor = await conn.execute("SELECT id, agent_id, name, description, skill_md FROM skills WHERE id = ?", (target["id"],))
            row = await cursor.fetchone()
            if row:
                return f"Editing skill: {row[2]}", {"type": "skill", "action": "editing", "data": {
                    "id": row[0], "agent_id": row[1], "name": row[2], "description": row[3], "skill_md": row[4],
                    "agent_name": target.get("agent_name", ""),
                }}
        finally:
            await conn.close()

    return f"Edit for {entity} not yet supported.", None


async def _handle_update(entity: str, target: dict, context: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Handle update action from editor save."""
    if entity == "agent" and "role_md" in context:
        agent_id = target.get("id", "")
        conn = await db.connect()
        try:
            await conn.execute("UPDATE agents SET role_md = ? WHERE id = ?", (context["role_md"], agent_id))
            await conn.commit()
        finally:
            await conn.close()
        agent = await agent_crud.get_agent(db, user_id, agent_id)
        return f"Agent '{agent['name']}' updated.", {"type": "agent", "action": "updated", "data": agent}

    if entity == "skill" and "skill_md" in context:
        conn = await db.connect()
        try:
            await conn.execute("UPDATE skills SET skill_md = ? WHERE id = ?", (context["skill_md"], target["id"]))
            if "description" in context:
                await conn.execute("UPDATE skills SET description = ? WHERE id = ?", (context["description"], target["id"]))
            await conn.commit()
        finally:
            await conn.close()
        return "Skill updated.", {"type": "skill", "action": "updated", "data": target}

    return f"Update for {entity} not supported.", None


# ============================================================
# Natural language handler
# ============================================================

async def _handle_natural_language(message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    """Handle natural language messages by matching intent to CRUD operations."""
    lower = message.lower().strip()

    # --- Pending create wizard ---
    pending_create = session.get("_pending_create")
    if pending_create:
        return await _handle_create_wizard(pending_create, message, user_id, db, session)

    # --- Pending add-skill flow ---
    pending_add_skill = session.get("_pending_add_skill")
    if pending_add_skill:
        return await _handle_add_skill_flow(pending_add_skill, message, user_id, db, session)

    # --- Pending export-agent flow ---
    pending_export = session.get("_pending_export_agent")
    if pending_export:
        return await _handle_export_agent_flow(pending_export, message, user_id, db, session)

    # --- Pending delete-agent flow ---
    pending_delete = session.get("_pending_delete_agent")
    if pending_delete:
        return await _handle_delete_agent_flow(pending_delete, message, user_id, db, session)

    # --- Pending find-skill flow ---
    pending_find = session.get("_pending_find_skill")
    if pending_find:
        return await _handle_find_skill_flow(pending_find, message, user_id, db, session)

    # --- Slash commands (from command palette) ---
    if lower == "/create-agent":
        session["_pending_create"] = {"step": "name", "skills_list": []}
        return "**Step 1/3 — Agent Name**\n\nWhat would you like to name your Agent?", None
    if lower == "/list-agents":
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            return "No agents found. Use /create-agent to create one.", {
                "type": "agent", "action": "listed", "data": {"agents": []}
            }
        return f"Found {len(agents)} agent(s).", {
            "type": "agent", "action": "listed", "data": {"agents": agents}
        }
    if lower == "/add-skill":
        session["_pending_add_skill"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            session.pop("_pending_add_skill", None)
            return "No agents found. Create one first with /create-agent.", None
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        return f"Which Agent should I add a skill to?\n\nYour agents: {names}", None
    if lower == "/export-agent":
        session["_pending_export_agent"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        names = ", ".join(f"`{a['name']}`" for a in agents)
        if not names:
            session.pop("_pending_export_agent", None)
            return "No agents found. Create one first with /create-agent.", None
        return f"Which Agent would you like to export?\n\nAvailable: {names}", None
    if lower == "/import-agent":
        return "Please upload or provide the path to the Agent config zip.\nExample: 导入 /path/to/agent.zip", None
    if lower == "/delete-agent":
        session["_pending_delete_agent"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        if not names:
            session.pop("_pending_delete_agent", None)
            return "No agents found.", None
        return f"Which Agent would you like to delete?\n\nYour agents: {names}", None
    if lower == "/find-skill":
        session["_pending_find_skill"] = {"step": "query"}
        return "What kind of skill are you looking for?\n\nType a keyword to search:", None

    # --- Create Agent (natural language) → enter wizard ---
    if _match_intent(lower, ["创建", "create", "新建", "new"]) and _match_intent(lower, ["agent", "智能体"]):
        name = _extract_name(message)
        wiz = {"step": "name", "skills_list": []}
        if name:
            wiz["name"] = name
            wiz["step"] = "role_md"
            session["_pending_create"] = wiz
            return f"Creating Agent **{name}**.\n\n**Step 2/3 — Identity Description**\n\nDescribe who this Agent is:", None
        session["_pending_create"] = wiz
        return "**Step 1/3 — Agent Name**\n\nWhat would you like to name your Agent?", None

    # --- List Agents ---
    if _match_intent(lower, ["列出", "list", "查看所有", "show all", "所有"]) and _match_intent(lower, ["agent", "智能体"]):
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            return "No agents found. Create one with: '创建一个 <name> Agent'", {
                "type": "agent", "action": "listed", "data": {"agents": []}
            }
        return f"Found {len(agents)} agent(s).", {
            "type": "agent", "action": "listed", "data": {"agents": agents}
        }

    # --- Delete Agent ---
    if _match_intent(lower, ["删除", "delete", "remove"]) and _match_intent(lower, ["agent", "智能体"]):
        name = _extract_name(message)
        if not name:
            return "Please specify which Agent to delete.", None
        # Find agent by name
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == name.lower()), None)
        if not match:
            return f"Agent '{name}' not found.", None
        session["_pending_action"] = {"entity": "agent", "action": "delete", "targets": [match]}
        return f"Are you sure you want to delete Agent '{name}'? This will remove all skills and configurations.", {
            "type": "agent", "action": "confirm_required",
            "data": {"message": f"Delete Agent '{name}'? This cannot be undone.", "confirm_label": "Delete", "cancel_label": "Cancel"},
        }

    # --- View Agent detail ---
    if _match_intent(lower, ["查看", "view", "详情", "detail", "show"]) and _match_intent(lower, ["agent", "智能体"]):
        name = _extract_name(message)
        if not name:
            return "Please specify which Agent to view.", None
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == name.lower()), None)
        if not match:
            return f"Agent '{name}' not found.", None
        agent = await agent_crud.get_agent(db, user_id, match["id"])
        return f"Agent: {agent['name']}", {"type": "agent", "action": "updated", "data": agent}

    # --- Export Agent ---
    if _match_intent(lower, ["导出", "export"]):
        name = _extract_name(message)
        if not name:
            return "Please specify which Agent to export.", None
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == name.lower()), None)
        if not match:
            return f"Agent '{name}' not found.", None
        session["_pending_export_agent"] = {"step": "format", "agent": match}
        return _FORMAT_MENU, None

    # --- Import Agent ---
    if _match_intent(lower, ["导入", "import"]):
        return "Import requires a file path. Usage: '导入 /path/to/agent-config'", None

    # --- Add Skill (natural language) ---
    if _match_intent(lower, ["添加", "add", "加", "新增"]) and _match_intent(lower, ["技能", "skill"]):
        agent_name = _extract_agent_name_from_context(message)
        if agent_name:
            agents = await agent_crud.list_agents(db, user_id)
            match = next((a for a in agents if a["name"].lower() == agent_name.lower() and not a.get("is_example")), None)
            if match:
                session["_pending_add_skill"] = {"step": "name", "agent_id": match["id"], "agent_name": match["name"]}
                return f"Adding skill to **{match['name']}**.\n\nWhat should the skill be named?", None
        session["_pending_add_skill"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        return f"Which Agent should I add a skill to?\n\nYour agents: {names}", None

    # --- Health check ---
    if _match_intent(lower, ["health", "健康", "状态"]):
        return "App is running. Health check: OK.", None

    # --- Confirm/cancel (text-based) ---
    if lower.strip() in ["确认", "confirm", "yes", "是"]:
        pending = session.get("_pending_action")
        if pending:
            session.pop("_pending_action", None)
            return await _execute_pending(pending, user_id, db)
        return "No pending operation to confirm.", None

    if lower.strip() in ["取消", "cancel", "no", "否"]:
        session.pop("_pending_action", None)
        return "Operation cancelled.", None

    # --- Fallback ---
    return f"I can help you manage Agent configurations. Try:\n- 创建一个 <name> Agent\n- 列出所有 Agent\n- 查看 <name> 的详情\n- 导出 <name>\n- 删除 <name>", None


# ============================================================
# Claude SDK integration
# ============================================================

_RUNTIME_DIR = Path(__file__).parent.parent / ".runtime" / "agents" / "default"

_PENDING_KEYS = (
    "_pending_create", "_pending_add_skill", "_pending_export_agent",
    "_pending_delete_agent", "_pending_find_skill", "_pending_action",
)


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


# ============================================================
# Helpers
# ============================================================

def _match_intent(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _extract_path(message: str) -> str:
    """Extract a file path from the message if present."""
    # Match common path patterns: /path/to/dir, ./relative, C:\windows\path
    match = re.search(r'(?:到|to|path[:\s]+|目录[:\s]+)\s*[`"]?([./~\w][\w./\\:-]*)[`"]?', message, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip("`\"'")
    return ""


def _extract_agent_name_from_context(message: str) -> str:
    """Extract agent name from '给 xxx 添加/加' pattern."""
    patterns = [
        r'(?:给|for)\s+(\S+)\s+(?:添加|加|add|新增)',
        r'(?:to|into)\s+(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip().strip("'\"")
            if name.lower() not in ["agent", "智能体", ""]:
                return name
    return ""


def _extract_name(message: str) -> str:
    """Extract agent/entity name from message. Tries common patterns."""
    # Pattern: "创建一个 xxx Agent" or "创建 xxx"
    patterns = [
        r'(?:创建|新建|create|new)\s*(?:一个\s*)?(\S+)\s+(?:agent|智能体)',
        r'(?:删除|delete|remove)\s+(?:agent\s+)?(\S+?)(?:\s+agent|\s*$)',
        r'(?:导出|export)\s+(?:agent\s+)?(\S+)',
        r'(?:查看|view|detail|详情)\s+(\S+?)(?:\s*的|\s+agent)',
        r'agent[:\s]+(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip().strip("'\"")
            # Filter out common noise words
            if name.lower() not in ["一个", "所有", "all", "the", "a", "an", "agent", "智能体", ""]:
                return name
    return ""


def _extract_description(message: str) -> str:
    """Extract description from message if present."""
    patterns = [
        r'(?:描述|description|desc)[:\s]+(.+)',
        r'(?:用于|for)\s+(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _parse_ui_action(message: str) -> dict | None:
    """Extract ui_action JSON from message if present."""
    match = re.search(r'```ui_action\n(.*?)\n```', message, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None
