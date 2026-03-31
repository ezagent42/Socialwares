---
name: dev_build
description: "Guide test-driven development — write tests first, then implement"
---

# Build (Test-Driven Development Guide)

## Trigger

User says "build", "develop", "TDD", "write tests", "开发", "写测试" etc.

## Flow

### Step 1: Understand Current State

Read `socialware.py` to discover all registered actions:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
cat socialware.py
```

Also read `src/api.py` to see which API endpoints already exist:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
grep -n 'def \|@app\.' src/api.py
```

Build a mapping: which actions have corresponding API endpoints, which do not.

### Step 2: For Each Action Missing an API Endpoint

Follow TDD cycle — **Red → Green → Refactor**:

#### 2a. Red — Write the Test First

Create or append to `tests/test_api.py`:

```python
# Example: testing a new "create_task" endpoint
async def test_create_task(client):
    resp = await client.post("/tasks", json={"title": "Test task"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test task"
    assert "id" in data
```

Run the test — it should **fail** (Red):

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run pytest tests/ -v -k test_create_task
```

Confirm the failure with the user before proceeding.

#### 2b. Green — Implement the Endpoint

Add the endpoint to `src/api.py`:

```python
@app.post("/tasks")
async def create_task(payload: dict) -> dict:
    # minimal implementation to make the test pass
    ...
```

Run the test again — it should **pass** (Green):

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run pytest tests/ -v -k test_create_task
```

#### 2c. Refactor

Review the implementation:
- Add proper Pydantic models for request/response
- Add error handling (HTTPException for edge cases)
- Add type hints

Run full test suite to ensure nothing is broken:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run pytest tests/ -v
```

### Step 3: Review SKILL.md Quality

For each action's `agent/flow/{action}/SKILL.md`, verify:

1. **Trigger**: Clear trigger keywords defined
2. **Flow**: Step-by-step execution instructions present
3. **Error handling**: What to do when things go wrong
4. **References**: Any supporting docs in `references/` directory

If SKILL.md is missing or incomplete, guide user to improve it.

### Step 4: Deploy and Verify

After all implementations are done:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

Show the compile result and confirm:
- All actions have corresponding API endpoints
- All tests pass
- SKILL.md files are complete

## Important

- **Always write the test before the implementation** — this is the core TDD principle
- Show the user the failing test first, then guide them to make it pass
- One action at a time — don't implement everything in a batch
- Use the user's language (Chinese or English based on their input)
- Reference `references/tdd-guide.md` for test patterns and conventions
- After completing all actions, suggest: "运行完整测试套件确认: `uv run pytest tests/ -v`"
