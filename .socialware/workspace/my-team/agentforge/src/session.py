"""Session Manager — manages per-user Agent sessions with real CRUD operations."""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import AsyncIterator

from src.db import Database
from src.crud import agent_crud, role_crud, skill_crud, scope_crud, commitment_crud


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
# Create Agent wizard (multi-step)
# ============================================================

async def _handle_create_wizard(wiz: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    """Handle multi-step Agent creation wizard."""
    step = wiz.get("step")
    text = message.strip()

    # Allow cancel at any step
    if text.lower() in ["cancel", "取消", "/cancel"]:
        session.pop("_pending_create", None)
        return "Agent creation cancelled.", None

    # --- Step 1: Name ---
    if step == "name":
        if not text:
            return "Please enter a valid name.", None
        wiz["name"] = text
        wiz["step"] = "model"
        return (
            "**Step 2/7 — Model**\n\n"
            "Which model should this Agent use?\n\n"
            "1. **claude** — Claude (Anthropic)\n"
            "2. **gemini** — Gemini (Google)\n"
            "3. **kimi** — Kimi (Moonshot)\n"
            "4. **codex** — Codex (OpenAI)\n\n"
            "Type the model name or number:"
        ), None

    # --- Step 2: Model ---
    if step == "model":
        model_map = {"1": "claude", "2": "gemini", "3": "kimi", "4": "codex"}
        model = model_map.get(text, text.lower())
        if model not in ("claude", "gemini", "kimi", "codex"):
            return f"Unknown model '{text}'. Please choose: claude, gemini, kimi, or codex.", None
        wiz["model"] = model
        wiz["step"] = "scope"
        return (
            "**Step 3/7 — Scope (Capabilities)**\n\n"
            "Describe what this Agent can do.\n"
            "Include capabilities and boundaries.\n\n"
            "Example:\n"
            "```\n"
            "Capabilities:\n"
            "- Create and manage tasks\n"
            "- Assign tasks to team members\n"
            "- Track task status\n"
            "\n"
            "Boundaries:\n"
            "- Only manage internal team tasks\n"
            "- Cannot access external systems\n"
            "```\n\n"
            "Type your scope description (or **skip** to use default):"
        ), None

    # --- Step 3: Scope ---
    if step == "scope":
        if text.lower() == "skip":
            wiz["scope"] = f"# {wiz['name']}\n\n## Capabilities\n\n- (Add capabilities)\n\n## Boundaries\n\n- (Add boundaries)\n"
        else:
            wiz["scope"] = f"# {wiz['name']}\n\n{text}\n"
        wiz["step"] = "role_ask"
        return (
            "**Step 4/7 — Roles**\n\n"
            "A `default` role has been created automatically.\n\n"
            "Would you like to add more roles? (e.g. reviewer, admin)\n\n"
            "Type a role name to add, or **done** to continue:"
        ), None

    # --- Step 4: Roles ---
    if step == "role_ask":
        if text.lower() in ["done", "skip", "完成", "跳过"]:
            wiz["step"] = "skill_ask"
            return (
                "**Step 5/7 — Skills**\n\n"
                "Skills define what actions the Agent can perform.\n\n"
                "Type a skill name to add (e.g. `create_task`), or **done** to continue:"
            ), None
        # Add role
        wiz["roles"].append({"name": text})
        wiz["step"] = "role_desc"
        wiz["_current_role"] = text
        return (
            f"Describe the **{text}** role.\n"
            f"What are its responsibilities and permissions?\n\n"
            f"Example: \"Reviews and approves submitted tasks\"\n\n"
            f"Type description (or **skip** for default):"
        ), None

    if step == "role_desc":
        role_name = wiz.pop("_current_role")
        for r in wiz["roles"]:
            if r["name"] == role_name:
                if text.lower() == "skip":
                    r["soul_md"] = f"# {role_name}\n\nRole for {wiz['name']}.\n\n## Identity\n\n- Role: {role_name}\n"
                else:
                    r["soul_md"] = f"# {role_name}\n\n{text}\n\n## Identity\n\n- Role: {role_name}\n"
        wiz["step"] = "role_ask"
        return (
            f"Role **{role_name}** added.\n\n"
            f"Add another role? Type a name, or **done** to continue:"
        ), None

    # --- Step 5: Skills ---
    if step == "skill_ask":
        if text.lower() in ["done", "skip", "完成", "跳过"]:
            wiz["step"] = "commitment_ask"
            return (
                "**Step 6/7 — Commitments (Quality Standards)**\n\n"
                "Commitments define quality expectations between roles.\n\n"
                "Example: \"Reviewer completes review within 24h after submission\"\n\n"
                "Type a commitment description, or **done** to continue:"
            ), None
        wiz["_current_skill"] = text
        wiz["step"] = "skill_desc"
        return (
            f"Describe the **{text}** skill.\n\n"
            f"1. When should it trigger?\n"
            f"2. What does it do?\n\n"
            f"Example: \"Triggered when user says 'create task'. Creates a new task with title and description.\"\n\n"
            f"Type description (or **skip** for default):"
        ), None

    if step == "skill_desc":
        skill_name = wiz.pop("_current_skill")
        if text.lower() == "skip":
            skill_md = f"---\nname: {skill_name}\ndescription: \"{skill_name}\"\n---\n\n# {skill_name}\n\n## Trigger\n\nUser requests {skill_name}.\n\n## Flow\n\n1. Execute {skill_name}\n2. Return result\n"
            desc = skill_name
        else:
            skill_md = f"---\nname: {skill_name}\ndescription: \"{text[:80]}\"\n---\n\n# {skill_name}\n\n{text}\n"
            desc = text[:80]
        wiz["step"] = "skill_roles"
        wiz["_current_skill_data"] = {"name": skill_name, "skill_md": skill_md, "description": desc}

        all_roles = ["default"] + [r["name"] for r in wiz["roles"]]
        if len(all_roles) == 1:
            # Only default role, auto-assign
            wiz["_current_skill_data"]["role_names"] = ["default"]
            wiz["skills"].append(wiz.pop("_current_skill_data"))
            wiz["step"] = "skill_ask"
            return (
                f"Skill **{skill_name}** added (assigned to: default).\n\n"
                f"Add another skill? Type a name, or **done** to continue:"
            ), None

        roles_list = ", ".join(f"`{r}`" for r in all_roles)
        return (
            f"Which roles can use **{skill_name}**?\n\n"
            f"Available roles: {roles_list}\n\n"
            f"Type role names separated by commas (e.g. `default, reviewer`), or **all**:"
        ), None

    if step == "skill_roles":
        skill_data = wiz.get("_current_skill_data", {})
        skill_name = skill_data.get("name", "")
        all_roles = ["default"] + [r["name"] for r in wiz["roles"]]

        if text.lower() == "all":
            skill_data["role_names"] = all_roles
        else:
            role_names = [r.strip() for r in text.split(",") if r.strip()]
            # Validate
            invalid = [r for r in role_names if r not in all_roles]
            if invalid:
                return f"Unknown role(s): {', '.join(invalid)}. Available: {', '.join(all_roles)}", None
            skill_data["role_names"] = role_names if role_names else ["default"]

        wiz["skills"].append(wiz.pop("_current_skill_data"))
        wiz["step"] = "skill_ask"
        assigned = ", ".join(skill_data["role_names"])
        return (
            f"Skill **{skill_name}** added (assigned to: {assigned}).\n\n"
            f"Add another skill? Type a name, or **done** to continue:"
        ), None

    # --- Step 6: Commitments ---
    if step == "commitment_ask":
        if text.lower() in ["done", "skip", "完成", "跳过"]:
            wiz["step"] = "confirm"
            return _build_create_preview(wiz), None
            # Note: goes straight to confirm (no preview step needed)
        wiz["_current_commitment"] = text
        wiz["step"] = "commitment_roles"

        all_roles = ["default"] + [r["name"] for r in wiz["roles"]]
        if len(all_roles) == 1:
            # Auto-assign from/to default
            wiz["commitments"].append({
                "condition": text,
                "from_role": "default",
                "to_role": "default",
            })
            wiz.pop("_current_commitment", None)
            wiz["step"] = "commitment_ask"
            return (
                f"Commitment added.\n\n"
                f"Add another commitment? Type description, or **done** to continue:"
            ), None

        roles_list = ", ".join(f"`{r}`" for r in all_roles)
        return (
            f"Who is responsible for this commitment?\n\n"
            f"Format: `from_role → to_role`\n"
            f"Example: `default → reviewer`\n\n"
            f"Available roles: {roles_list}"
        ), None

    if step == "commitment_roles":
        condition = wiz.pop("_current_commitment", "")
        parts = [p.strip() for p in text.replace("→", "->").split("->")]
        if len(parts) != 2:
            return "Please use format: `from_role → to_role` (e.g. `default → reviewer`)", None
        wiz["commitments"].append({
            "condition": condition,
            "from_role": parts[0],
            "to_role": parts[1],
        })
        wiz["step"] = "commitment_ask"
        return (
            f"Commitment added: {parts[0]} → {parts[1]}\n\n"
            f"Add another commitment? Type description, or **done** to continue:"
        ), None

    # --- Step 6 → 7 transition: show preview ---
    if step == "preview":
        wiz["step"] = "confirm"
        preview = _build_create_preview(wiz)
        return preview, None

    # --- Step 7: Confirm ---
    if step == "confirm":
        if text.lower() in ["cancel", "取消", "no"]:
            session.pop("_pending_create", None)
            return "Agent creation cancelled.", None
        if text.lower() in ["create", "confirm", "yes", "确认", "创建"]:
            return await _execute_create_wizard(wiz, user_id, db, session)
        return "Type **create** to confirm or **cancel** to abort.", None

    # Fallback
    session.pop("_pending_create", None)
    return "Something went wrong. Please try /create-agent again.", None


def _build_create_preview(wiz: dict) -> str:
    """Build confirmation preview for the create wizard."""
    lines = [
        "**Step 7/7 — Confirm**\n",
        f"**Name:** {wiz['name']}",
        f"**Model:** {wiz['model']}",
        f"**Scope:** {wiz['scope'][:100]}{'...' if len(wiz['scope']) > 100 else ''}",
        f"**Roles:** default" + (", " + ", ".join(r["name"] for r in wiz["roles"]) if wiz["roles"] else ""),
        f"**Skills:** " + (", ".join(s["name"] for s in wiz["skills"]) if wiz["skills"] else "(none)"),
        f"**Commitments:** {len(wiz['commitments'])}",
        "",
        "Type **create** to confirm or **cancel** to abort.",
    ]
    return "\n".join(lines)


async def _execute_create_wizard(wiz: dict, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    """Execute the full create wizard — write all data to DB."""
    session.pop("_pending_create", None)

    name = wiz["name"]
    model = wiz["model"]

    # Create agent (auto-creates default role + scope + commitment)
    try:
        agent = await agent_crud.create_agent(db, user_id, name, "", model)
    except ValueError as e:
        return str(e), None

    agent_id = agent["id"]

    # Update scope with user-provided content
    if wiz.get("scope"):
        await scope_crud.update_scope(db, agent_id, wiz["scope"])

    # Add extra roles
    for role_data in wiz.get("roles", []):
        soul_md = role_data.get("soul_md", f"# {role_data['name']}\n\nRole for {name}.\n")
        await role_crud.create_role(db, agent_id, role_data["name"], soul_md)

    # Add skills
    for skill_data in wiz.get("skills", []):
        # Resolve role names to role IDs
        all_roles = await role_crud.list_roles(db, agent_id)
        role_id_map = {r["name"]: r["id"] for r in all_roles}
        role_ids = [role_id_map[rn] for rn in skill_data.get("role_names", ["default"]) if rn in role_id_map]
        if not role_ids:
            role_ids = [all_roles[0]["id"]]  # fallback to first role

        await skill_crud.create_skill(
            db, agent_id, skill_data["name"], skill_data["skill_md"],
            role_ids, skill_data.get("description", "")
        )

    # Update commitment
    if wiz.get("commitments"):
        commit_lines = ["commitments:"]
        for i, c in enumerate(wiz["commitments"], 1):
            commit_lines.append(f"  C{i}:")
            commit_lines.append(f"    from: {{ role: {c['from_role']}, action: '*' }}")
            commit_lines.append(f"    to: {{ role: {c['to_role']}, action: '*' }}")
            commit_lines.append(f"    condition: \"{c['condition']}\"")
            commit_lines.append(f"    on_violation: null")
        await commitment_crud.update_commitment(db, agent_id, "\n".join(commit_lines))

    # Re-fetch full agent data
    agent = await agent_crud.get_agent(db, user_id, agent_id)

    role_count = len(agent.get("roles", []))
    skill_count = len(agent.get("skills", []))
    return (
        f"Agent **{name}** created successfully!\n"
        f"Model: {model} | Roles: {role_count} | Skills: {skill_count} | Commitments: {len(wiz.get('commitments', []))}"
    ), {"type": "agent", "action": "created", "data": agent}


# ============================================================
# Add Role flow (multi-step)
# ============================================================

async def _handle_add_role_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()
    step = flow.get("step")

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_add_role", None)
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
        return f"Adding role to **{match['name']}**.\n\nWhat should the role be named?", None

    if step == "name":
        flow["role_name"] = text
        flow["step"] = "desc"
        return f"Describe the **{text}** role.\nWhat are its responsibilities?\n\n(Type description or **skip** for default)", None

    if step == "desc":
        role_name = flow["role_name"]
        agent_id = flow["agent_id"]
        if text.lower() == "skip":
            soul_md = f"# {role_name}\n\nRole for {flow['agent_name']}.\n\n## Identity\n\n- Role: {role_name}\n"
        else:
            soul_md = f"# {role_name}\n\n{text}\n\n## Identity\n\n- Role: {role_name}\n"
        session.pop("_pending_add_role", None)
        role = await role_crud.create_role(db, agent_id, role_name, soul_md)
        return f"Role **{role_name}** added to {flow['agent_name']}.", {
            "type": "role", "action": "created", "data": {**role, "agent_name": flow["agent_name"]}
        }

    session.pop("_pending_add_role", None)
    return "Something went wrong. Try /add-role again.", None


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
        return f"Adding skill to **{match['name']}**.\n\nWhat should the skill be named?", None

    if step == "name":
        flow["skill_name"] = text
        flow["step"] = "desc"
        return f"Describe the **{text}** skill.\n\n1. When should it trigger?\n2. What does it do?\n\n(Type description or **skip** for default)", None

    if step == "desc":
        skill_name = flow["skill_name"]
        if text.lower() == "skip":
            skill_md = f"---\nname: {skill_name}\ndescription: \"{skill_name}\"\n---\n\n# {skill_name}\n\n## Trigger\n\nUser requests {skill_name}.\n\n## Flow\n\n1. Execute {skill_name}\n2. Return result\n"
            desc = skill_name
        else:
            skill_md = f"---\nname: {skill_name}\ndescription: \"{text[:80]}\"\n---\n\n# {skill_name}\n\n{text}\n"
            desc = text[:80]
        flow["skill_md"] = skill_md
        flow["desc"] = desc
        flow["step"] = "roles"

        # Get roles for this agent
        roles = await role_crud.list_roles(db, flow["agent_id"])
        flow["all_roles"] = roles
        if len(roles) == 1:
            # Auto-assign to only role
            role_ids = [roles[0]["id"]]
            session.pop("_pending_add_skill", None)
            skill = await skill_crud.create_skill(db, flow["agent_id"], skill_name, skill_md, role_ids, desc)
            return f"Skill **{skill_name}** added to {flow['agent_name']} (assigned to: {roles[0]['name']}).", {
                "type": "skill", "action": "created", "data": {**skill, "agent_name": flow["agent_name"]}
            }

        roles_list = ", ".join(f"`{r['name']}`" for r in roles)
        return f"Which roles can use **{skill_name}**?\n\nAvailable: {roles_list}\n\nType role names separated by commas, or **all**:", None

    if step == "roles":
        skill_name = flow["skill_name"]
        all_roles = flow["all_roles"]
        role_map = {r["name"]: r["id"] for r in all_roles}

        if text.lower() == "all":
            role_ids = [r["id"] for r in all_roles]
            assigned = ", ".join(r["name"] for r in all_roles)
        else:
            names = [n.strip() for n in text.split(",") if n.strip()]
            invalid = [n for n in names if n not in role_map]
            if invalid:
                return f"Unknown role(s): {', '.join(invalid)}. Available: {', '.join(role_map.keys())}", None
            role_ids = [role_map[n] for n in names]
            assigned = ", ".join(names)

        session.pop("_pending_add_skill", None)
        skill = await skill_crud.create_skill(db, flow["agent_id"], skill_name, flow["skill_md"], role_ids, flow["desc"])
        return f"Skill **{skill_name}** added to {flow['agent_name']} (assigned to: {assigned}).", {
            "type": "skill", "action": "created", "data": {**skill, "agent_name": flow["agent_name"]}
        }

    session.pop("_pending_add_skill", None)
    return "Something went wrong. Try /add-skill again.", None


# ============================================================
# Edit Scope flow
# ============================================================

async def _handle_edit_scope_flow(flow: dict, message: str, user_id: str, db: Database, session: dict) -> tuple[str, dict | None]:
    text = message.strip()

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_edit_scope", None)
        return "Cancelled.", None

    if flow.get("step") == "agent":
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == text.lower() and not a.get("is_example")), None)
        if not match:
            names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
            return f"Agent '{text}' not found. Your agents: {names}", None
        # Return editing structured data for the scope
        session.pop("_pending_edit_scope", None)
        scope = await scope_crud.get_scope(db, match["id"])
        return f"Editing scope for **{match['name']}**.", {
            "type": "scope", "action": "editing",
            "data": {"agent_id": match["id"], "agent_name": match["name"], "soul_md": scope["soul_md"]}
        }

    session.pop("_pending_edit_scope", None)
    return "Something went wrong. Try /edit-scope again.", None


# ============================================================
# Export Agent flow
# ============================================================

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
        session.pop("_pending_export_agent", None)
        return _build_export_response([match])

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
        return f"Are you sure you want to delete Agent **{match['name']}**? This will remove all roles, skills, and configurations.", {
            "type": "agent", "action": "confirm_required",
            "data": {"message": f"Delete Agent '{match['name']}'? This cannot be undone.", "confirm_label": "Delete", "cancel_label": "Cancel"},
        }

    session.pop("_pending_delete_agent", None)
    return "Something went wrong. Try /delete-agent again.", None


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
        # Check pending export first
        pending_export = session.get("_pending_export")
        if action == "confirm" and pending_export:
            session.pop("_pending_export", None)
            return await _handle_export(pending_export["targets"], user_id, db)
        elif pending_export:
            session.pop("_pending_export", None)
            return "Export cancelled.", None

        # Then check pending delete/other actions
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

    if entity == "role":
        for t in targets:
            try:
                await role_crud.delete_role(db, t["id"])
            except ValueError as e:
                return str(e), None
        return f"Role deleted.", {"type": "role", "action": "deleted", "data": targets[0]}

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
            # Enrich skills with full skill_md and role names
            conn = await db.connect()
            try:
                enriched_skills = []
                for s in agent.get("skills", []):
                    cursor = await conn.execute("SELECT skill_md FROM skills WHERE id = ?", (s["id"],))
                    row = await cursor.fetchone()
                    skill_md = row[0] if row else ""
                    # Get role names for this skill
                    rc = await conn.execute(
                        "SELECT r.name FROM skill_roles sr JOIN roles r ON sr.role_id = r.id WHERE sr.skill_id = ?",
                        (s["id"],)
                    )
                    role_names = [r[0] for r in await rc.fetchall()]
                    enriched_skills.append({**s, "skill_md": skill_md, "roles": role_names})
                agent["skills"] = enriched_skills

                # Enrich roles with full soul_md
                enriched_roles = []
                for r in agent.get("roles", []):
                    cursor = await conn.execute("SELECT soul_md FROM roles WHERE id = ?", (r["id"],))
                    row = await cursor.fetchone()
                    enriched_roles.append({**r, "soul_md": row[0] if row else ""})
                agent["roles"] = enriched_roles
            finally:
                await conn.close()

            return f"Agent: {agent['name']}", {"type": "agent", "action": "detailed", "data": agent}
        except ValueError as e:
            return str(e), None
    return f"Detail view for {entity} is not yet supported.", None


def _build_export_response(targets: list) -> tuple[str, dict | None]:
    """Build export response with download links."""
    downloads = []
    for t in targets:
        downloads.append({
            "id": t.get("id", ""),
            "name": t.get("name", ""),
            "download_url": f"/api/export/{t['id']}",
        })

    if len(downloads) == 1:
        d = downloads[0]
        return f"Agent '{d['name']}' is ready for download.", {
            "type": "deploy", "action": "exported",
            "data": {"agent_name": d["name"], "download_url": d["download_url"], "downloads": downloads},
        }
    names = ", ".join(d["name"] for d in downloads)
    return f"{len(downloads)} agents ready for download: {names}", {
        "type": "deploy", "action": "exported",
        "data": {"downloads": downloads},
    }


async def _handle_edit(entity: str, target: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Handle edit action — return current content for editor."""
    if entity == "role":
        roles = await role_crud.list_roles(db, target.get("agent_id", ""))
        for r in roles:
            if r.get("id") == target["id"] or r.get("name") == target.get("name"):
                # Need full soul_md, re-fetch
                conn = await db.connect()
                try:
                    cursor = await conn.execute("SELECT id, agent_id, name, soul_md FROM roles WHERE id = ?", (target["id"],))
                    row = await cursor.fetchone()
                    if row:
                        return f"Editing role: {row[2]}", {"type": "role", "action": "editing", "data": {
                            "id": row[0], "agent_id": row[1], "name": row[2], "soul_md": row[3],
                            "agent_name": target.get("agent_name", ""),
                        }}
                finally:
                    await conn.close()

    if entity == "scope":
        agent_id = target.get("agent_id") or target.get("id", "")
        scope = await scope_crud.get_scope(db, agent_id)
        return f"Editing scope", {"type": "scope", "action": "editing", "data": {
            "agent_id": agent_id, "soul_md": scope["soul_md"],
            "agent_name": target.get("agent_name", target.get("name", "")),
        }}

    if entity == "commitment":
        agent_id = target.get("agent_id") or target.get("id", "")
        commit = await commitment_crud.get_commitment(db, agent_id)
        return f"Editing commitment", {"type": "commitment", "action": "editing", "data": {
            "agent_id": agent_id, "commitment_yaml": commit["commitment_yaml"],
            "agent_name": target.get("agent_name", target.get("name", "")),
        }}

    return f"Edit for {entity} not yet supported.", None


async def _handle_update(entity: str, target: dict, context: dict, user_id: str, db: Database) -> tuple[str, dict | None]:
    """Handle update action from editor save."""
    if entity == "role" and "soul_md" in context:
        result = await role_crud.update_role(db, target["id"], context["soul_md"])
        return f"Role '{result['name']}' updated.", {"type": "role", "action": "updated", "data": result}

    if entity == "scope" and "soul_md" in context:
        agent_id = target.get("agent_id") or target.get("id", "")
        result = await scope_crud.update_scope(db, agent_id, context["soul_md"])
        return "Scope updated.", {"type": "scope", "action": "updated", "data": result}

    if entity == "commitment" and "commitment_yaml" in context:
        agent_id = target.get("agent_id") or target.get("id", "")
        result = await commitment_crud.update_commitment(db, agent_id, context["commitment_yaml"])
        return "Commitment updated.", {"type": "commitment", "action": "updated", "data": result}

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

    # --- Pending add-role flow ---
    pending_add_role = session.get("_pending_add_role")
    if pending_add_role:
        return await _handle_add_role_flow(pending_add_role, message, user_id, db, session)

    # --- Pending add-skill flow ---
    pending_add_skill = session.get("_pending_add_skill")
    if pending_add_skill:
        return await _handle_add_skill_flow(pending_add_skill, message, user_id, db, session)

    # --- Pending edit-scope flow ---
    pending_edit_scope = session.get("_pending_edit_scope")
    if pending_edit_scope:
        return await _handle_edit_scope_flow(pending_edit_scope, message, user_id, db, session)

    # --- Pending export-agent flow ---
    pending_export = session.get("_pending_export_agent")
    if pending_export:
        return await _handle_export_agent_flow(pending_export, message, user_id, db, session)

    # --- Pending delete-agent flow ---
    pending_delete = session.get("_pending_delete_agent")
    if pending_delete:
        return await _handle_delete_agent_flow(pending_delete, message, user_id, db, session)

    # --- Slash commands (from command palette) ---
    if lower == "/create-agent":
        session["_pending_create"] = {"step": "name", "roles": [], "skills": [], "commitments": []}
        return "**Step 1/7 — Agent Name**\n\nWhat would you like to name your Agent?", None
    if lower == "/list-agents":
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            return "No agents found. Use /create-agent to create one.", {
                "type": "agent", "action": "listed", "data": {"agents": []}
            }
        return f"Found {len(agents)} agent(s).", {
            "type": "agent", "action": "listed", "data": {"agents": agents}
        }
    if lower == "/add-role":
        session["_pending_add_role"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            session.pop("_pending_add_role", None)
            return "No agents found. Create one first with /create-agent.", None
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        return f"Which Agent should I add a role to?\n\nYour agents: {names}", None
    if lower == "/add-skill":
        session["_pending_add_skill"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        if not agents:
            session.pop("_pending_add_skill", None)
            return "No agents found. Create one first with /create-agent.", None
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        return f"Which Agent should I add a skill to?\n\nYour agents: {names}", None
    if lower == "/edit-scope":
        session["_pending_edit_scope"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        if not names:
            session.pop("_pending_edit_scope", None)
            return "No agents found. Create one first with /create-agent.", None
        return f"Which Agent's scope would you like to edit?\n\nYour agents: {names}", None
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

    # --- Create Agent (natural language) → enter wizard ---
    if _match_intent(lower, ["创建", "create", "新建", "new"]) and _match_intent(lower, ["agent", "智能体"]):
        name = _extract_name(message)
        wiz = {"step": "name", "roles": [], "skills": [], "commitments": []}
        if name:
            # Pre-fill name, go to step 2
            wiz["name"] = name
            wiz["step"] = "model"
            session["_pending_create"] = wiz
            return (
                f"Creating Agent **{name}**.\n\n"
                "**Step 2/7 — Model**\n\n"
                "Which model should this Agent use?\n\n"
                "1. **claude** — Claude (Anthropic)\n"
                "2. **gemini** — Gemini (Google)\n"
                "3. **kimi** — Kimi (Moonshot)\n"
                "4. **codex** — Codex (OpenAI)\n\n"
                "Type the model name or number:"
            ), None
        session["_pending_create"] = wiz
        return "**Step 1/7 — Agent Name**\n\nWhat would you like to name your Agent?", None

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
        return f"Are you sure you want to delete Agent '{name}'? This will remove all roles, skills, and configurations.", {
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
        return _build_export_response([match])

    # --- Import Agent ---
    if _match_intent(lower, ["导入", "import"]):
        return "Import requires a file path. Usage: '导入 /path/to/agent-config'", None

    # --- Add Role (natural language) ---
    if _match_intent(lower, ["添加", "add", "加", "新增"]) and _match_intent(lower, ["角色", "role"]):
        # Try to extract agent name from message like "给 task-manager 加个 reviewer 角色"
        agent_name = _extract_agent_name_from_context(message)
        if agent_name:
            agents = await agent_crud.list_agents(db, user_id)
            match = next((a for a in agents if a["name"].lower() == agent_name.lower() and not a.get("is_example")), None)
            if match:
                session["_pending_add_role"] = {"step": "name", "agent_id": match["id"], "agent_name": match["name"]}
                return f"Adding role to **{match['name']}**.\n\nWhat should the role be named?", None
        # Fallback: start guided flow
        session["_pending_add_role"] = {"step": "agent"}
        agents = await agent_crud.list_agents(db, user_id)
        names = ", ".join(f"`{a['name']}`" for a in agents if not a.get("is_example"))
        return f"Which Agent should I add a role to?\n\nYour agents: {names}", None

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
        # Check pending export
        pending_export = session.get("_pending_export")
        if pending_export:
            session.pop("_pending_export", None)
            return await _handle_export(pending_export["targets"], user_id, db)
        # Check pending delete
        pending = session.get("_pending_action")
        if pending:
            session.pop("_pending_action", None)
            return await _execute_pending(pending, user_id, db)
        return "No pending operation to confirm.", None

    # --- User typed a path for pending export ---
    pending_export = session.get("_pending_export")
    if pending_export and (message.strip().startswith(("/", "./", "~", "C:", "D:")) or "/" in message or "\\" in message):
        session.pop("_pending_export", None)
        return await _handle_export(pending_export["targets"], user_id, db, message.strip())

    if lower.strip() in ["取消", "cancel", "no", "否"]:
        session.pop("_pending_action", None)
        return "Operation cancelled.", None

    # --- Fallback ---
    return f"I can help you manage Agent configurations. Try:\n- 创建一个 <name> Agent\n- 列出所有 Agent\n- 查看 <name> 的详情\n- 导出 <name>\n- 删除 <name>", None


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
