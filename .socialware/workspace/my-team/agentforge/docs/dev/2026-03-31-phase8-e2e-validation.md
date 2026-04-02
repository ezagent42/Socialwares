# Phase 8: End-to-End Validation + Polish Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Validate all features work end-to-end, fix edge cases, add missing error handling, and polish the user experience.

**Architecture:** Integration tests that exercise the full stack: Frontend → Backend → CRUD → DB → Export → Import roundtrip. Manual verification checklist for features that can't be automated.

**Tech Stack:** pytest, httpx (async test client), Next.js build verification

**Prerequisites:** Phase 5-7 complete

---

## Task 1: Export/Import Roundtrip Tests (All 5 Formats)

**Files:**
- Create: `tests/test_e2e_export_import.py`

Test for each format: create agent with skills → export → import → verify data matches.

```python
@pytest.mark.parametrize("format", ["gitagent", "claude-code", "codex", "cursor", "socialwares"])
def test_roundtrip(db, user_id, tmp_path, format):
    """Export → Import roundtrip preserves agent data."""
    # Create agent with skill
    agent = asyncio.run(create_agent(db, user_id, f"rt-{format}", "test", "# RT\nRoundtrip."))
    asyncio.run(create_skill(db, agent["id"], "ping", "# Ping", "Ping"))

    # Export
    asyncio.run(export_agent(db, agent["id"], tmp_path / "out", format=format))

    # Import as different user
    asyncio.run(add_user(db, "u2"))
    imported = asyncio.run(import_agent(db, "u2", tmp_path / "out"))

    # Verify
    assert imported["name"] == f"rt-{format}" or "rt" in imported["name"]
    assert "RT" in imported["role_md"] or "Roundtrip" in imported["role_md"]
```

**Commit:** `test: add export/import roundtrip tests for all 5 formats`

---

## Task 2: User Isolation E2E Test

**Files:**
- Create: `tests/test_e2e_isolation.py`

```python
def test_user_a_cannot_see_user_b_agents(db):
    """User A's agents are invisible to User B."""
    asyncio.run(add_user(db, "ua"))
    asyncio.run(add_user(db, "ub"))
    asyncio.run(create_agent(db, "ua", "secret", "", "# Secret"))

    agents = asyncio.run(list_agents(db, "ub"))
    user_agents = [a for a in agents if not a.get("is_example")]
    assert len(user_agents) == 0

def test_user_b_cannot_delete_user_a_agent(db):
    asyncio.run(add_user(db, "ua"))
    asyncio.run(add_user(db, "ub"))
    agent = asyncio.run(create_agent(db, "ua", "mine", "", "# Mine"))
    with pytest.raises(ValueError):
        asyncio.run(delete_agent(db, "ub", agent["id"]))

def test_example_agent_visible_to_all(db):
    asyncio.run(add_user(db, "ua"))
    from src.seed import seed_example_agent
    asyncio.run(seed_example_agent(db))
    agents = asyncio.run(list_agents(db, "ua"))
    assert any(a.get("is_example") for a in agents)
```

**Commit:** `test: add user isolation E2E tests`

---

## Task 3: Session Manager Wizard E2E Tests

**Files:**
- Modify: `tests/test_chat_api.py` — add comprehensive wizard tests

```python
def test_full_workflow(db, user_id):
    """Create → List → View → Add Skill → Export → Delete."""
    sm = SessionManager()
    # Create
    asyncio.run(_collect(sm, user_id, "/create-agent", db))
    asyncio.run(_collect(sm, user_id, "workflow-test", db))
    asyncio.run(_collect(sm, user_id, "# Workflow\nTest agent.", db))
    asyncio.run(_collect(sm, user_id, "done", db))
    events = asyncio.run(_collect(sm, user_id, "create", db))
    agent = _structured(events)["data"]

    # List
    events = asyncio.run(_collect(sm, user_id, "/list-agents", db))
    listed = _structured(events)["data"]["agents"]
    assert any(a["name"] == "workflow-test" for a in listed)

    # View
    view_msg = f'```ui_action\n{{"entity":"agent","action":"detail","targets":[{{"id":"{agent["id"]}","name":"workflow-test"}}]}}\n```'
    events = asyncio.run(_collect(sm, user_id, view_msg, db))
    detail = _structured(events)
    assert detail["action"] == "detailed"
    assert detail["data"]["role_md"] == "# Workflow\nTest agent."

    # Delete
    del_msg = f'```ui_action\n{{"entity":"agent","action":"delete","targets":[{{"id":"{agent["id"]}","name":"workflow-test"}}]}}\n```'
    events = asyncio.run(_collect(sm, user_id, del_msg, db))
    assert _structured(events)["action"] == "confirm_required"
    events = asyncio.run(_collect(sm, user_id, "confirm", db))
```

**Commit:** `test: add full workflow E2E test`

---

## Task 4: Error Handling Improvements

**Files:**
- Modify: `src/session.py` — wrap all CRUD calls in try/except
- Modify: `src/app.py` — add global exception handler

```python
# src/app.py
@app.exception_handler(Exception)
async def global_handler(request, exc):
    import traceback
    logging.error(f"Unhandled: {traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"error": str(exc)})
```

**Commit:** `fix: improve error handling in session.py and app.py`

---

## Task 5: Frontend Build Verification

**Files:**
- Verify: `app/` builds cleanly

```bash
cd app
npx tsc --noEmit
npx next build
```

Fix any TypeScript errors or build warnings.

**Commit:** `fix: resolve any frontend build issues`

---

## Task 6: Manual Verification Checklist

This is NOT automated — execute manually and check off:

```
Backend:
□ POST /api/chat/send with "/create-agent" → returns Step 1 prompt
□ Full 3-step wizard → agent created in DB
□ /list-agents → returns agents including example
□ /add-skill → guided flow works
□ /export-agent → format selection → zip download
□ /delete-agent → confirm → deleted
□ GET /api/export/{id}?format=gitagent → valid zip
□ GET /api/export/{id}?format=claude-code → valid zip
□ GET /api/auth/login → redirects to GitHub
□ GET /api/auth/me → returns user or 401

Frontend:
□ Login page → GitHub OAuth → redirect back
□ Sidebar: Terminal/Dashboard toggle works
□ Sidebar: Theme toggle works
□ Sidebar: Logout with confirmation
□ Chat: Send message → response appears
□ Chat: Command palette shows on focus
□ Chat: /create-agent → 3-step wizard
□ Dashboard: Agent cards appear after creation
□ Dashboard: Example agent has EXAMPLE badge
□ Dashboard: Batch select → action bar appears
□ AgentCard: View → AgentDetail (Identity + Skills)
□ AgentCard: Export → download link
□ AgentCard: Delete → confirm dialog → removed
```

**Commit:** `docs: add manual verification checklist`

---

## Task 7: Update README

**Files:**
- Create/Update: `README.md` in agentforge workspace

Include:
- What is AgentForge
- Quick start (backend + frontend)
- Available commands
- Export/Import formats
- Architecture overview

**Commit:** `docs: add AgentForge README`

---

## Dependencies

```
Task 1 (roundtrip tests) ← independent
Task 2 (isolation tests) ← independent
Task 3 (wizard E2E) ← independent
Task 4 (error handling) ← independent
Task 5 (frontend build) ← independent
Task 6 (manual checklist) ← after 1-5
Task 7 (README) ← after 6
```

Tasks 1-5 can all run in parallel.
