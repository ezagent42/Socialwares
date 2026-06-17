# Phase 7: find_skill Wiring + Export Format Selection Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire find_skill into the session.py command system and frontend, and add format selection step to the export flow.

**Architecture:** find_skill CRUD module already exists (`src/crud/find_skill.py`). Need to: (1) add `/find-skill` handler in session.py, (2) integrate find_skill into `/add-skill` flow, (3) add format selection to export flow in session.py, (4) update frontend DeployLog to show format-specific download buttons.

**Tech Stack:** Python 3.12+, FastAPI | Next.js 15, React 19

**Prerequisites:** Phase 5 complete (find_skill.py exists, export adapters exist)

---

## Task 1: Wire /find-skill in session.py

**Files:**
- Modify: `src/session.py`
- Test: `tests/test_chat_api.py` (add find-skill tests)

**Step 1: Add `/find-skill` slash command handler**

In `_handle_natural_language`, add:
```python
if lower == "/find-skill":
    session["_pending_find_skill"] = {"step": "query"}
    return "What kind of skill are you looking for?\n\nType a keyword to search:", None
```

**Step 2: Add `_handle_find_skill_flow`**

```python
async def _handle_find_skill_flow(flow, message, user_id, db, session):
    text = message.strip()
    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_find_skill", None)
        return "Cancelled.", None

    if flow["step"] == "query":
        from src.crud.find_skill import search_skills
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
        # User selects a skill by number
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
```

**Step 3: Add pending check in _handle_natural_language**

After the other pending checks, add:
```python
pending_find = session.get("_pending_find_skill")
if pending_find:
    return await _handle_find_skill_flow(pending_find, message, user_id, db, session)
```

**Step 4: Test**

```python
def test_find_skill_command(db, user_id):
    from src.session import SessionManager
    sm = SessionManager()
    # Create agent with skill first
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "finder-test", db))
    asyncio.run(_collect(sm, user_id, "# Finder", db))
    asyncio.run(_collect(sm, user_id, "review_code", db))
    asyncio.run(_collect(sm, user_id, "Review code for bugs", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    asyncio.run(_collect(sm, user_id, "create", db))
    # Search
    events = asyncio.run(_collect(sm, user_id, "/find-skill", db))
    assert "keyword" in _text(events).lower()
    events = asyncio.run(_collect(sm, user_id, "review", db))
    assert "review_code" in _text(events)
```

**Commit:** `feat: wire /find-skill command in session.py`

---

## Task 2: Integrate find_skill into /add-skill Flow

**Files:**
- Modify: `src/session.py` — `_handle_add_skill_flow`

When user enters `/add-skill` and reaches the "skill name" step, offer three options:

```python
return (
    f"Adding skill to **{match['name']}**.\n\n"
    f"How would you like to add a skill?\n"
    f"  1. Type a skill name to create manually\n"
    f"  2. Type **search <keyword>** to find existing skills\n"
    f"  3. Type **url <url>** to import from URL\n"
)
```

If user types `search <keyword>`, call `search_skills()` and let them pick.
If user types `url <url>`, call `import_skill_from_url()`.

**Commit:** `feat: integrate find_skill into /add-skill flow`

---

## Task 3: Add Format Selection to Export Flow

**Files:**
- Modify: `src/session.py` — `_handle_export_agent_flow` and `_build_export_response`

**Current flow:** Select agent → immediately return download link (default format).

**New flow:**
```
/export-agent
  → Select agent
  → Select format:
    1. gitagent (recommended)
    2. claude-code
    3. codex
    4. cursor
    5. socialwares
  → Return download link with selected format
```

**Implementation:**

```python
async def _handle_export_agent_flow(flow, message, user_id, db, session):
    text = message.strip()

    if text.lower() in ["cancel", "取消"]:
        session.pop("_pending_export_agent", None)
        return "Cancelled.", None

    if flow["step"] == "agent":
        # Find agent
        agents = await agent_crud.list_agents(db, user_id)
        match = next((a for a in agents if a["name"].lower() == text.lower()), None)
        if not match:
            names = ", ".join(f"`{a['name']}`" for a in agents)
            return f"Agent '{text}' not found. Available: {names}", None
        flow["agent"] = match
        flow["step"] = "format"
        return (
            f"Export **{match['name']}** in which format?\n\n"
            "1. **gitagent** — GitAgent standard (recommended for sharing)\n"
            "2. **claude-code** — Claude Code native format\n"
            "3. **codex** — OpenAI Codex format\n"
            "4. **cursor** — Cursor format\n"
            "5. **socialwares** — Socialwares four-primitives\n\n"
            "Type format name or number:"
        ), None

    if flow["step"] == "format":
        format_map = {"1": "gitagent", "2": "claude-code", "3": "codex", "4": "cursor", "5": "socialwares"}
        fmt = format_map.get(text, text.lower())
        from src.crud.export import FORMATS
        if fmt not in FORMATS:
            return f"Unknown format '{text}'. Available: {', '.join(FORMATS)}", None
        agent = flow["agent"]
        session.pop("_pending_export_agent", None)
        return _build_export_response([agent], fmt)

    session.pop("_pending_export_agent", None)
    return "Something went wrong. Try /export-agent again.", None
```

Update `_build_export_response` to include format:
```python
def _build_export_response(targets, format="gitagent"):
    downloads = []
    for t in targets:
        downloads.append({
            "id": t.get("id", ""),
            "name": t.get("name", ""),
            "download_url": f"/api/export/{t['id']}?format={format}",
            "format": format,
        })
    ...
```

**Commit:** `feat: add format selection to /export-agent flow`

---

## Task 4: Update Frontend DeployLog for Format

**Files:**
- Modify: `app/src/components/structured-block-renderer.tsx` — DeployLog component

Show the selected format in the download button:

```tsx
function DeployLog({ data }) {
  // data.downloads[].format now available
  return (
    <div>
      {downloads.map(d => (
        <a href={d.download_url} download>
          Download {d.name}.zip ({d.format})
        </a>
      ))}
    </div>
  );
}
```

**Commit:** `feat: show export format in DeployLog download button`

---

## Task 5: Update Frontend /find-skill Command

**Files:**
- Already in COMMANDS array (added in Phase 5)
- Verify structured rendering for `{type: "skill", action: "listed"}` works

**Commit:** `verify: find-skill frontend rendering`

---

## Dependencies

```
Task 1 (/find-skill command)
  └── Task 2 (integrate into /add-skill)
Task 3 (export format selection) ← independent
Task 4 (frontend DeployLog) ← after Task 3
Task 5 (frontend verify) ← after Task 1
```

Tasks 1-2 and Tasks 3-4 can run in parallel.
