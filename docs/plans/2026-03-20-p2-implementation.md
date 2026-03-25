# P2 Chat UI + Chat API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add browser Chat UI + backend Chat API + adapter query() so users can interact with AgentForge through a web interface instead of terminal TUI.

**Architecture:** Backend FastAPI adds session management (/session), chat endpoint (/chat) that delegates to adapter.query(), and read-only four-primitive query endpoints. Frontend Next.js provides a simple chat window where `/agentforge` command triggers Agent connection. Adapter abstraction layer extended with async query() and is_available() methods.

**Tech Stack:** Python (FastAPI, claude_code_sdk, asyncio), TypeScript (Next.js 15, React 19, Tailwind CSS), pytest (backend tests)

**Reference docs:**
- Design: `docs/plans/2026-03-20-p2-chat-ui-design.md`
- Requirements: `docs/plans/2026-03-19-socialware-framework-design.md` (第三部分)

---

### Task 1: Extend BaseAdapter with query() and is_available()

**Files:**
- Modify: `agent/adapters/base.py`
- Test: `tests/test_adapters.py`

**Step 1: Write the failing test**

Create `tests/test_adapters.py`:

```python
"""Tests for adapter base class and implementations."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add adapters to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent" / "adapters"))

from base import BaseAdapter, RoleConfig


class TestBaseAdapter:
    """Test BaseAdapter has required abstract methods."""

    def test_query_is_abstract(self):
        assert hasattr(BaseAdapter, "query")

    def test_is_available_is_abstract(self):
        assert hasattr(BaseAdapter, "is_available")

    def test_cannot_instantiate_without_query(self):
        class IncompleteAdapter(BaseAdapter):
            def launch_shell(self): ...
            def launch_sdk(self): ...
            # missing query and is_available

        config = RoleConfig(name="test", project_dir=Path("."), soul="", skills_dir=Path("."))
        with pytest.raises(TypeError):
            IncompleteAdapter(config)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters.py::TestBaseAdapter -v`
Expected: FAIL — BaseAdapter doesn't have query or is_available yet.

**Step 3: Implement**

Modify `agent/adapters/base.py`:

```python
"""Base adapter interface for multi-platform agent launching.

Each adapter reads a deployed role directory (.runtime/agents/{role}/)
and launches the agent using the platform's SDK or CLI.
"""
from __future__ import annotations

import abc
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RoleConfig:
    """Deployed role configuration."""

    name: str
    project_dir: Path
    soul: str
    skills_dir: Path

    @classmethod
    def from_runtime(cls, role_dir: str | Path) -> RoleConfig:
        """Load role config from a deployed .runtime/agents/{role}/ directory."""
        role_dir = Path(role_dir)
        soul = ""
        soul_path = role_dir / "SOUL.md"
        if soul_path.exists():
            soul = soul_path.read_text()

        return cls(
            name=role_dir.name,
            project_dir=role_dir,
            soul=soul,
            skills_dir=role_dir / ".claude" / "skills",
        )


class BaseAdapter(abc.ABC):
    """Abstract base class for agent platform adapters."""

    def __init__(self, config: RoleConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """Launch agent in interactive shell/TUI mode (dev)."""
        ...

    @abc.abstractmethod
    def launch_sdk(self) -> None:
        """Launch agent programmatically via SDK (prod)."""
        ...

    @abc.abstractmethod
    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt to the Agent Runtime, return response messages.

        Returns:
            List of message dicts: [{"type": "text", "text": "..."}]
        """
        ...

    @classmethod
    @abc.abstractmethod
    def is_available(cls) -> bool:
        """Check if this adapter's runtime is installed on the system."""
        ...
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_adapters.py::TestBaseAdapter -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent/adapters/base.py tests/test_adapters.py
git commit -m "feat(adapters): add query() and is_available() abstract methods to BaseAdapter"
```

---

### Task 2: Implement ClaudeAdapter.query() and is_available()

**Files:**
- Modify: `agent/adapters/claude/sdk.py`
- Modify: `tests/test_adapters.py`

**Step 1: Write the failing test**

Add to `tests/test_adapters.py`:

```python
import importlib


class TestClaudeAdapter:
    """Test Claude adapter implementation."""

    def _load_claude_adapter(self):
        sys.path.insert(0, str(REPO_ROOT / "agent" / "adapters" / "claude"))
        mod = importlib.import_module("sdk")
        importlib.reload(mod)  # ensure fresh import
        return mod.ClaudeAdapter

    def test_is_available_returns_bool(self):
        cls = self._load_claude_adapter()
        result = cls.is_available()
        assert isinstance(result, bool)

    def test_has_query_method(self):
        cls = self._load_claude_adapter()
        config = RoleConfig(name="test", project_dir=Path("."), soul="test", skills_dir=Path("."))
        adapter = cls(config)
        assert hasattr(adapter, "query")
        assert callable(adapter.query)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters.py::TestClaudeAdapter -v`
Expected: FAIL — ClaudeAdapter doesn't have query or is_available.

**Step 3: Implement**

Rewrite `agent/adapters/claude/sdk.py`:

```python
#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Reference:
- CLI: https://docs.anthropic.com/en/docs/claude-code/cli-reference
- SDK: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if claude CLI is installed."""
        return shutil.which("claude") is not None

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        cmd = ["claude", "--dangerously-skip-permissions"]

        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])

        subprocess.run(cmd, cwd=str(self.config.project_dir))

    def launch_sdk(self) -> None:
        """Launch programmatically via Claude Agent SDK."""
        print(f"[Claude SDK] Launching {self.config.name}")
        print(f"[Claude SDK] Working dir: {self.config.project_dir}")
        print(f"[Claude SDK] SOUL.md: {len(self.config.soul)} chars")

        try:
            import asyncio
            asyncio.run(self._run_sdk("You are ready. Wait for instructions."))
        except ImportError:
            print("[Claude SDK] claude_code_sdk not installed.")
            print("  Install: pip install claude-code-sdk")
            self.launch_shell()

    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt to Claude Code, return text responses."""
        from claude_code_sdk import query as claude_query
        from claude_code_sdk import ClaudeCodeOptions
        from claude_code_sdk.types import AssistantMessage, TextBlock

        options = ClaudeCodeOptions(
            cwd=str(self.config.project_dir),
            system_prompt=self.config.soul,
            permission_mode="bypassPermissions",
        )

        messages = []
        async for event in claude_query(prompt=prompt, options=options):
            if isinstance(event, AssistantMessage):
                for block in event.content:
                    if isinstance(block, TextBlock):
                        messages.append({"type": "text", "text": block.text})

        return messages

    async def _run_sdk(self, prompt: str) -> None:
        result = await self.query(prompt)
        for msg in result:
            print(msg.get("text", ""))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to .runtime/agents/{role}/")
    parser.add_argument("--mode", default="sdk", choices=["shell", "sdk"])
    args = parser.parse_args()

    config = RoleConfig.from_runtime(args.project_dir)
    adapter = ClaudeAdapter(config)

    if args.mode == "shell":
        adapter.launch_shell()
    else:
        adapter.launch_sdk()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_adapters.py::TestClaudeAdapter -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent/adapters/claude/sdk.py tests/test_adapters.py
git commit -m "feat(adapters): implement ClaudeAdapter.query() and is_available()"
```

---

### Task 3: Implement CodexAdapter and KimiCodeAdapter query() and is_available()

**Files:**
- Modify: `agent/adapters/codex/sdk.py`
- Modify: `agent/adapters/kimicode/sdk.py`
- Modify: `tests/test_adapters.py`

**Step 1: Write the failing test**

Add to `tests/test_adapters.py`:

```python
class TestCodexAdapter:
    def _load(self):
        sys.path.insert(0, str(REPO_ROOT / "agent" / "adapters" / "codex"))
        mod = importlib.import_module("sdk")
        importlib.reload(mod)
        return mod.CodexAdapter

    def test_is_available_returns_bool(self):
        assert isinstance(self._load().is_available(), bool)

    def test_has_query_method(self):
        config = RoleConfig(name="test", project_dir=Path("."), soul="", skills_dir=Path("."))
        assert callable(self._load()(config).query)


class TestKimiCodeAdapter:
    def _load(self):
        sys.path.insert(0, str(REPO_ROOT / "agent" / "adapters" / "kimicode"))
        mod = importlib.import_module("sdk")
        importlib.reload(mod)
        return mod.KimiCodeAdapter

    def test_is_available_returns_bool(self):
        assert isinstance(self._load().is_available(), bool)

    def test_has_query_method(self):
        config = RoleConfig(name="test", project_dir=Path("."), soul="", skills_dir=Path("."))
        assert callable(self._load()(config).query)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters.py::TestCodexAdapter tests/test_adapters.py::TestKimiCodeAdapter -v`
Expected: FAIL

**Step 3: Implement CodexAdapter**

Rewrite `agent/adapters/codex/sdk.py`:

```python
#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class CodexAdapter(BaseAdapter):
    """OpenAI Codex CLI / Agents SDK adapter."""

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("codex") is not None

    def launch_shell(self) -> None:
        subprocess.run([
            "codex", "--cd", str(self.config.project_dir), "--full-auto",
        ])

    def launch_sdk(self) -> None:
        print(f"[Codex SDK] Launching {self.config.name}")
        try:
            from agents import Agent, Runner
            agent = Agent(name=self.config.name, instructions=self.config.soul)
            result = Runner.run_sync(agent, "You are ready. Wait for instructions.")
            print(result.final_output)
        except ImportError:
            print("[Codex SDK] openai-agents not installed.")

    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt via OpenAI Agents SDK."""
        try:
            from agents import Agent, Runner
            agent = Agent(name=self.config.name, instructions=self.config.soul)
            result = await Runner.run(agent, prompt)
            return [{"type": "text", "text": result.final_output}]
        except ImportError:
            return [{"type": "text", "text": "[Codex SDK not installed] pip install openai-agents"}]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    CodexAdapter(config).launch_sdk()
```

**Implement KimiCodeAdapter**

Rewrite `agent/adapters/kimicode/sdk.py`:

```python
#!/usr/bin/env python3
"""Kimi Code SDK adapter.

Reference:
- CLI: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class KimiCodeAdapter(BaseAdapter):
    """Kimi Code CLI adapter."""

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("kimi") is not None

    def launch_shell(self) -> None:
        subprocess.run([
            "kimi", "--work-dir", str(self.config.project_dir), "--yolo",
        ])

    def launch_sdk(self) -> None:
        print(f"[Kimi] Launching {self.config.name} via CLI")
        self.launch_shell()

    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt via Kimi CLI subprocess."""
        try:
            result = subprocess.run(
                ["kimi", "--work-dir", str(self.config.project_dir),
                 "--yolo", "-p", prompt],
                capture_output=True, text=True, timeout=120,
            )
            return [{"type": "text", "text": result.stdout}]
        except FileNotFoundError:
            return [{"type": "text", "text": "[Kimi CLI not installed]"}]
        except subprocess.TimeoutExpired:
            return [{"type": "text", "text": "[Kimi CLI timeout]"}]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    KimiCodeAdapter(config).launch_shell()
```

**Step 4: Run test**

Run: `python -m pytest tests/test_adapters.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agent/adapters/codex/sdk.py agent/adapters/kimicode/sdk.py tests/test_adapters.py
git commit -m "feat(adapters): implement query() and is_available() for Codex and Kimicode"
```

---

### Task 4: Backend API — Session management + Chat endpoint

**Files:**
- Modify: `src/app.py`
- Test: `tests/test_chat_api.py`

**Step 1: Write the failing test**

Create `tests/test_chat_api.py`:

```python
"""Tests for Chat API endpoints: /session, /chat, /adapters."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


class TestHealthExisting:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200


class TestAdapters:
    def test_list_adapters(self):
        r = client.get("/adapters")
        assert r.status_code == 200
        data = r.json()
        assert "adapters" in data
        names = {a["name"] for a in data["adapters"]}
        assert {"claude", "codex", "kimicode"} == names
        for a in data["adapters"]:
            assert "available" in a
            assert isinstance(a["available"], bool)


class TestSession:
    def test_no_session_initially(self):
        r = client.get("/session")
        assert r.status_code == 200
        assert r.json()["active"] is False

    def test_create_session(self):
        # Clean up first
        client.delete("/session")
        r = client.post("/session", json={"role": "default", "adapter": "claude"})
        # May fail if claude not available, but should be 200 or 400
        assert r.status_code in (200, 400)

    def test_delete_session(self):
        r = client.delete("/session")
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

    def test_chat_without_session_returns_400(self):
        client.delete("/session")
        r = client.post("/chat", json={"message": "hello"})
        assert r.status_code == 400


class TestPrimitivesQuery:
    def test_get_roles(self):
        r = client.get("/roles")
        assert r.status_code == 200
        assert "roles" in r.json()

    def test_get_flows(self):
        r = client.get("/flows")
        assert r.status_code == 200
        assert "flows" in r.json()

    def test_get_scope(self):
        r = client.get("/scope")
        assert r.status_code == 200
        assert "soul" in r.json()

    def test_get_commitments(self):
        r = client.get("/commitments")
        assert r.status_code == 200

    def test_get_flows_registry(self):
        r = client.get("/flows/registry")
        assert r.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_chat_api.py -v`
Expected: FAIL — endpoints don't exist.

**Step 3: Implement**

Rewrite `src/app.py`:

```python
"""Socialware App backend — FastAPI entry point.

Provides:
- /health — health check
- /session — Agent session management (single session)
- /chat — send message to Agent, get reply
- /adapters — list available agent runtimes
- /roles, /flows, /commitments, /scope — four-primitive read-only queries

Start: uvicorn src.app:app --port 8001
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add adapters to path
APP_ROOT = Path(__file__).parent.parent
ADAPTERS_DIR = APP_ROOT / "agent" / "adapters"
sys.path.insert(0, str(ADAPTERS_DIR))

from base import BaseAdapter, RoleConfig

app = FastAPI(
    title="Socialware App",
    description="Web application for agent interaction visualization",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

ADAPTER_NAMES = ["claude", "codex", "kimicode"]


def _load_adapter_class(name: str) -> type[BaseAdapter]:
    """Dynamically load adapter class by name."""
    sys.path.insert(0, str(ADAPTERS_DIR / name))
    mod = importlib.import_module(f"{name}.sdk")
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BaseAdapter)
            and attr is not BaseAdapter
        ):
            return attr
    raise RuntimeError(f"No adapter class found in {name}/sdk.py")


# ---------------------------------------------------------------------------
# Session state (single session, in-memory)
# ---------------------------------------------------------------------------


class SessionState:
    def __init__(self):
        self.active = False
        self.role: str | None = None
        self.adapter_name: str | None = None
        self.adapter: BaseAdapter | None = None

    def clear(self):
        self.active = False
        self.role = None
        self.adapter_name = None
        self.adapter = None


_session = SessionState()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class SessionRequest(BaseModel):
    role: str
    adapter: str = "claude"


class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_dir() -> Path:
    """Return agent/ directory path."""
    return APP_ROOT / "agent"


def _runtime_dir() -> Path:
    """Return .runtime/ directory path."""
    return APP_ROOT / ".runtime"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


# --- Adapters ---


@app.get("/adapters")
async def list_adapters() -> dict[str, list[dict[str, Any]]]:
    """List available agent runtime adapters."""
    result = []
    for name in ADAPTER_NAMES:
        try:
            cls = _load_adapter_class(name)
            available = cls.is_available()
        except Exception:
            available = False
        result.append({"name": name, "available": available})
    return {"adapters": result}


# --- Session ---


@app.get("/session")
async def get_session() -> dict[str, Any]:
    """Get current session info."""
    if _session.active:
        return {
            "active": True,
            "role": _session.role,
            "adapter": _session.adapter_name,
        }
    return {"active": False}


@app.post("/session")
async def create_session(req: SessionRequest) -> dict[str, Any]:
    """Create an Agent session."""
    if _session.active:
        raise HTTPException(409, "Session already active. DELETE /session first.")

    # Check adapter
    try:
        adapter_cls = _load_adapter_class(req.adapter)
    except Exception:
        raise HTTPException(400, f"Adapter '{req.adapter}' not found")

    if not adapter_cls.is_available():
        raise HTTPException(400, f"Adapter '{req.adapter}' runtime not installed")

    # Check role
    runtime_role_dir = _runtime_dir() / "agents" / req.role
    if not runtime_role_dir.exists():
        raise HTTPException(400, f"Role '{req.role}' not deployed. Run deploy.sh first.")

    config = RoleConfig.from_runtime(runtime_role_dir)
    _session.active = True
    _session.role = req.role
    _session.adapter_name = req.adapter
    _session.adapter = adapter_cls(config)

    return {"status": "created", "role": req.role, "adapter": req.adapter}


@app.delete("/session")
async def delete_session() -> dict[str, str]:
    """Close the current session."""
    _session.clear()
    return {"status": "closed"}


# --- Chat ---


@app.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    """Send a message to the active Agent session."""
    if not _session.active or _session.adapter is None:
        raise HTTPException(400, "No active session. POST /session first.")

    messages = await _session.adapter.query(req.message)
    return {"messages": messages}


# --- Four primitives query (read-only) ---


@app.get("/roles")
async def list_roles() -> dict[str, list[str]]:
    """List deployed roles."""
    role_dir = _agent_dir() / "role"
    if not role_dir.exists():
        return {"roles": []}
    roles = [d.name for d in role_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    return {"roles": sorted(roles)}


@app.get("/roles/{name}")
async def get_role(name: str) -> dict[str, str]:
    """Read a role's SOUL.md."""
    soul_path = _agent_dir() / "role" / name / "SOUL.md"
    if not soul_path.exists():
        raise HTTPException(404, f"Role '{name}' not found")
    return {"name": name, "soul": soul_path.read_text(encoding="utf-8")}


@app.get("/flows")
async def list_flows() -> dict[str, list[str]]:
    """List available skills."""
    flow_dir = _agent_dir() / "flow"
    if not flow_dir.exists():
        return {"flows": []}
    flows = [d.name for d in flow_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    return {"flows": sorted(flows)}


@app.get("/flows/registry")
async def get_flow_registry() -> dict[str, Any]:
    """Read flow.yaml."""
    flow_yaml = _agent_dir() / "flow" / "flow.yaml"
    if not flow_yaml.exists():
        raise HTTPException(404, "flow.yaml not found")
    data = yaml.safe_load(flow_yaml.read_text(encoding="utf-8"))
    return data or {}


@app.get("/scope")
async def get_scope() -> dict[str, str]:
    """Read scope/SOUL.md."""
    soul_path = _agent_dir() / "scope" / "SOUL.md"
    if not soul_path.exists():
        raise HTTPException(404, "scope/SOUL.md not found")
    return {"soul": soul_path.read_text(encoding="utf-8")}


@app.get("/commitments")
async def get_commitments() -> dict[str, Any]:
    """Read commitment/eval.yaml."""
    eval_path = _agent_dir() / "commitment" / "eval.yaml"
    if not eval_path.exists():
        return {"commitments": {}}
    data = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
    return data or {"commitments": {}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Step 4: Run test**

Run: `python -m pytest tests/test_chat_api.py -v`
Expected: All PASS

Note: pyyaml needs to be installed. Run `pip install pyyaml` if not already present.

**Step 5: Commit**

```bash
git add src/app.py tests/test_chat_api.py
git commit -m "feat(api): add session management, chat endpoint, and four-primitive query APIs"
```

---

### Task 5: curl verification of all backend endpoints

**Files:** None (manual testing only)

**Step 1: Start backend**

```bash
cd D:/workspace/zhidaoyuan/Socialwares
python -m uvicorn src.app:app --port 8001
```

**Step 2: Test endpoints**

```bash
# Health
curl http://localhost:8001/health

# Adapters
curl http://localhost:8001/adapters

# Session — no session
curl http://localhost:8001/session

# Four primitives
curl http://localhost:8001/roles
curl http://localhost:8001/roles/default
curl http://localhost:8001/flows
curl http://localhost:8001/flows/registry
curl http://localhost:8001/scope
curl http://localhost:8001/commitments

# Chat without session — should 400
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"message":"hello"}'

# Create session
curl -X POST http://localhost:8001/session -H "Content-Type: application/json" -d '{"role":"default","adapter":"claude"}'

# Chat with session
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"message":"check health"}'

# Delete session
curl -X DELETE http://localhost:8001/session
```

**Step 3: Verify all responses are correct**

No commit needed — this is a manual verification step.

---

### Task 6: Frontend — Initialize Next.js project

**Files:**
- Create: `app/` (entire Next.js project)

**Step 1: Initialize Next.js**

```bash
cd D:/workspace/zhidaoyuan/Socialwares
# Remove the empty .gitkeep
rm app/.gitkeep 2>/dev/null

npx create-next-app@latest app --typescript --tailwind --app --src-dir --no-eslint --import-alias "@/*"
```

When prompted:
- Would you like to use Turbopack? → Yes

**Step 2: Verify it runs**

```bash
cd app && npm run dev
```

Open http://localhost:3000 — should see Next.js default page.

**Step 3: Commit**

```bash
git add app/
git commit -m "feat(frontend): initialize Next.js 15 project with TypeScript and Tailwind"
```

---

### Task 7: Frontend — API client library

**Files:**
- Create: `app/src/lib/api.ts`

**Step 1: Create API client**

Create `app/src/lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Session
export async function getSession() {
  return request<{ active: boolean; role?: string; adapter?: string }>("/session");
}

export async function createSession(role: string, adapter: string) {
  return request<{ status: string; role: string; adapter: string }>("/session", {
    method: "POST",
    body: JSON.stringify({ role, adapter }),
  });
}

export async function deleteSession() {
  return request<{ status: string }>("/session", { method: "DELETE" });
}

// Chat
export async function sendMessage(message: string) {
  return request<{ messages: { type: string; text: string }[] }>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

// Adapters
export async function getAdapters() {
  return request<{ adapters: { name: string; available: boolean }[] }>("/adapters");
}

// Four primitives
export async function getRoles() {
  return request<{ roles: string[] }>("/roles");
}

export async function getFlows() {
  return request<{ flows: string[] }>("/flows");
}

export async function getScope() {
  return request<{ soul: string }>("/scope");
}
```

**Step 2: Commit**

```bash
git add app/src/lib/api.ts
git commit -m "feat(frontend): add API client library"
```

---

### Task 8: Frontend — Chat UI components

**Files:**
- Create: `app/src/components/message-bubble.tsx`
- Create: `app/src/components/chat-panel.tsx`
- Create: `app/src/components/session-bar.tsx`

**Step 1: Create MessageBubble**

Create `app/src/components/message-bubble.tsx`:

```tsx
type MessageProps = {
  role: "user" | "agent" | "system";
  content: string;
};

export default function MessageBubble({ role, content }: MessageProps) {
  const styles = {
    user: "bg-blue-600 text-white ml-auto",
    agent: "bg-gray-200 text-gray-900",
    system: "bg-yellow-100 text-yellow-800 text-sm italic text-center",
  };

  return (
    <div className={`max-w-[80%] rounded-lg px-4 py-2 mb-2 whitespace-pre-wrap ${styles[role]} ${role === "system" ? "mx-auto" : ""}`}>
      {role !== "system" && (
        <div className="text-xs font-semibold mb-1 opacity-70">
          {role === "user" ? "You" : "Agent"}
        </div>
      )}
      {content}
    </div>
  );
}
```

**Step 2: Create SessionBar**

Create `app/src/components/session-bar.tsx`:

```tsx
type SessionBarProps = {
  connected: boolean;
  role?: string;
  adapter?: string;
  onDisconnect: () => void;
};

export default function SessionBar({ connected, role, adapter, onDisconnect }: SessionBarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 border-b bg-white">
      <div className="font-semibold text-lg">Socialware Chat</div>
      <div className="flex items-center gap-3">
        {connected ? (
          <>
            <span className="text-sm text-green-600">
              ● {role} ({adapter})
            </span>
            <button
              onClick={onDisconnect}
              className="text-sm px-2 py-1 rounded border hover:bg-gray-100"
            >
              Disconnect
            </button>
          </>
        ) : (
          <span className="text-sm text-gray-400">● Not Connected</span>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Create ChatPanel**

Create `app/src/components/chat-panel.tsx`:

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import MessageBubble from "./message-bubble";
import SessionBar from "./session-bar";
import { createSession, deleteSession, sendMessage, getAdapters } from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
};

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "system",
      content: "Welcome to Socialware Chat. Type /agentforge to connect an Agent.",
    },
  ]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [sessionRole, setSessionRole] = useState<string>();
  const [sessionAdapter, setSessionAdapter] = useState<string>();
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (role: Message["role"], content: string) => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role, content }]);
  };

  const handleConnect = async (role: string) => {
    addMessage("system", `Connecting to ${role}...`);

    try {
      // Detect available adapters
      const { adapters } = await getAdapters();
      const available = adapters.filter((a) => a.available);

      if (available.length === 0) {
        addMessage("system", "No agent runtime available. Install Claude Code, Codex, or Kimi Code.");
        return;
      }

      const adapterName = available[0].name;
      addMessage("system", `Detected runtime: ${adapterName}`);

      await createSession(role, adapterName);
      setConnected(true);
      setSessionRole(role);
      setSessionAdapter(adapterName);
      addMessage("system", `✓ ${role} connected via ${adapterName}`);
    } catch (err: any) {
      addMessage("system", `Connection failed: ${err.message}`);
    }
  };

  const handleDisconnect = async () => {
    try {
      await deleteSession();
    } catch {}
    setConnected(false);
    setSessionRole(undefined);
    setSessionAdapter(undefined);
    addMessage("system", "Disconnected.");
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");

    // Slash commands
    if (text.startsWith("/")) {
      const cmd = text.slice(1).split(" ")[0];
      if (cmd === "disconnect") {
        await handleDisconnect();
        return;
      }
      // Treat any other slash command as a role connection
      addMessage("user", text);
      await handleConnect(cmd);
      return;
    }

    addMessage("user", text);

    if (!connected) {
      addMessage("system", "Not connected. Type /agentforge to connect.");
      return;
    }

    setLoading(true);
    try {
      const { messages: replies } = await sendMessage(text);
      for (const msg of replies) {
        if (msg.type === "text" && msg.text) {
          addMessage("agent", msg.text);
        }
      }
    } catch (err: any) {
      addMessage("system", `Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <SessionBar
        connected={connected}
        role={sessionRole}
        adapter={sessionAdapter}
        onDisconnect={handleDisconnect}
      />

      <div className="flex-1 overflow-y-auto p-4 flex flex-col">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
        ))}
        {loading && (
          <div className="text-sm text-gray-400 animate-pulse">Agent is thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (/agentforge to connect)"
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add app/src/components/
git commit -m "feat(frontend): add ChatPanel, MessageBubble, and SessionBar components"
```

---

### Task 9: Frontend — Wire up page.tsx

**Files:**
- Modify: `app/src/app/page.tsx`

**Step 1: Replace default page**

Overwrite `app/src/app/page.tsx`:

```tsx
import ChatPanel from "@/components/chat-panel";

export default function Home() {
  return <ChatPanel />;
}
```

**Step 2: Verify it builds**

```bash
cd app && npm run build
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
git add app/src/app/page.tsx
git commit -m "feat(frontend): wire ChatPanel to home page"
```

---

### Task 10: Full integration test

**Files:** None (manual testing)

**Step 1: Start backend**

```bash
cd D:/workspace/zhidaoyuan/Socialwares
python -m uvicorn src.app:app --port 8001
```

**Step 2: Start frontend**

```bash
cd D:/workspace/zhidaoyuan/Socialwares/app
npm run dev
```

**Step 3: Open browser**

1. Open http://localhost:3000
2. See "Welcome to Socialware Chat" message
3. Type `/agentforge` → should detect runtime and connect
4. Type "check health" → Agent should respond
5. Click Disconnect → session closed

**Step 4: Run all backend tests**

```bash
python -m pytest tests/test_app.py tests/test_agentforge.py tests/test_adapters.py tests/test_chat_api.py -v
```

Expected: All tests PASS.

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(p2): complete Chat UI + Chat API + Adapter query

- BaseAdapter extended with query() and is_available()
- Claude/Codex/Kimicode adapters implement query()
- Backend: /session, /chat, /adapters, four-primitive query endpoints
- Frontend: Next.js Chat UI with slash command agent connection
- Tests: adapter tests + chat API tests"
```

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | BaseAdapter + query/is_available | `agent/adapters/base.py`, `tests/test_adapters.py` |
| 2 | ClaudeAdapter query | `agent/adapters/claude/sdk.py` |
| 3 | Codex + Kimi query | `agent/adapters/codex/sdk.py`, `agent/adapters/kimicode/sdk.py` |
| 4 | Backend API | `src/app.py`, `tests/test_chat_api.py` |
| 5 | curl verification | Manual testing |
| 6 | Next.js init | `app/` project |
| 7 | API client | `app/src/lib/api.ts` |
| 8 | Chat components | `app/src/components/*.tsx` |
| 9 | Wire page | `app/src/app/page.tsx` |
| 10 | Integration test | Manual browser + test suite |

**Development order:** Tasks 1-5 (backend, curl testable) → Tasks 6-9 (frontend) → Task 10 (联调)
