"""Socialware App backend — FastAPI entry point.

Start: uvicorn src.app:app --port 8001
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# Force UTF-8 on Windows to prevent GBK encoding errors with Claude SDK
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import yaml
from fastapi import FastAPI, HTTPException

from src.eval import EvalRunner
from src.zchat import ZChatMessage, ZChatRouter
from src.chat_history import ChatHistoryManager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_ROOT = Path(__file__).parent.parent
AGENT_DIR = APP_ROOT / "agent"
RUNTIME_DIR = APP_ROOT / ".runtime"
ADAPTERS_DIR = AGENT_DIR / "adapters"

# ---------------------------------------------------------------------------
# Adapter helpers
# ---------------------------------------------------------------------------
# Ensure the adapters package is importable
if str(ADAPTERS_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTERS_DIR))

from base import BaseAdapter, RoleConfig  # noqa: E402


def _list_adapter_names() -> list[str]:
    """Return adapter directory names (each has an sdk.py)."""
    return sorted(
        p.name
        for p in ADAPTERS_DIR.iterdir()
        if p.is_dir() and (p / "sdk.py").exists()
    )


def _load_adapter_class(name: str) -> type[BaseAdapter]:
    """Dynamically import and return the adapter class for *name*."""
    adapter_pkg_dir = str(ADAPTERS_DIR / name)
    if adapter_pkg_dir not in sys.path:
        sys.path.insert(0, adapter_pkg_dir)
    mod = importlib.import_module(f"{name}.sdk")
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseAdapter) and attr is not BaseAdapter:
            return attr
    raise RuntimeError(f"No adapter class found in {name}/sdk.py")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
class _Session:
    def __init__(self) -> None:
        self.active: bool = False
        self.role: str | None = None
        self.adapter_name: str | None = None
        self.adapter: BaseAdapter | None = None
        self.workspace: str | None = None

    def open(self, role: str, adapter_name: str, adapter: BaseAdapter, workspace: str | None = None) -> None:
        self.active = True
        self.role = role
        self.adapter_name = adapter_name
        self.adapter = adapter
        self.workspace = workspace

    def close(self) -> None:
        self.active = False
        self.role = None
        self.adapter_name = None
        self.adapter = None
        self.workspace = None


_session = _Session()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
_chat_history = ChatHistoryManager(APP_ROOT / "data")

# ---------------------------------------------------------------------------
# ZChat router
# ---------------------------------------------------------------------------
_zchat_router = ZChatRouter()

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class SessionRequest(BaseModel):
    role: str = "default"
    adapter: str = "claude"
    workspace: str | None = None  # e.g. "my-team/agentforge" → .socialware/workspace/my-team/agentforge


class ChatRequest(BaseModel):
    message: str


class WorkspaceRequest(BaseModel):
    room: str
    app_name: str
    description: str = ""


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Socialware App",
    description="Web application for agent interaction visualization",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


# -- Adapters ---------------------------------------------------------------

@app.get("/adapters")
async def list_adapters():
    adapters = []
    for name in _list_adapter_names():
        try:
            cls = _load_adapter_class(name)
            available = cls.is_available()
        except Exception:
            available = False
        adapters.append({"name": name, "available": available})
    return {"adapters": adapters}


# -- Session ----------------------------------------------------------------

@app.get("/session")
async def get_session():
    if not _session.active:
        return {"active": False}
    return {
        "active": True,
        "role": _session.role,
        "adapter": _session.adapter_name,
        "workspace": _session.workspace,
    }


@app.post("/session")
async def create_session(req: SessionRequest):
    if _session.active:
        raise HTTPException(status_code=409, detail="Session already active")

    # Determine runtime directory based on workspace
    if req.workspace:
        ws_runtime = APP_ROOT / ".socialware" / "workspace" / req.workspace / ".runtime"
    else:
        ws_runtime = RUNTIME_DIR

    # Auto-deploy if .runtime/ doesn't exist but agent/ does
    if not (ws_runtime / "agents").exists():
        if req.workspace:
            ws_agent_dir = APP_ROOT / ".socialware" / "workspace" / req.workspace / "agent"
        else:
            ws_agent_dir = AGENT_DIR
        deploy_sh = ws_agent_dir / "deploy.sh"
        if deploy_sh.exists():
            import subprocess
            subprocess.run(
                f'bash "{deploy_sh}"',
                shell=True,
                capture_output=True,
                cwd=str(ws_agent_dir.parent),
            )

    # Validate role is deployed
    role_dir = ws_runtime / "agents" / req.role
    if not role_dir.exists():
        raise HTTPException(status_code=400, detail=f"Role '{req.role}' not deployed")

    # Validate adapter available
    try:
        cls = _load_adapter_class(req.adapter)
        if not cls.is_available():
            raise HTTPException(status_code=400, detail=f"Adapter '{req.adapter}' not available")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Adapter '{req.adapter}' error: {exc}")

    config = RoleConfig.from_runtime(role_dir)
    adapter = cls(config)

    # Start long-running agent session
    try:
        await adapter.connect()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to connect agent: {exc}")

    _session.open(req.role, req.adapter, adapter, req.workspace)
    chat_session = _chat_history.new_session(req.role, req.adapter)
    _chat_history.add_system_message(f"Connected to {req.role} via {req.adapter}")
    return {
        "active": True, "role": req.role, "adapter": req.adapter,
        "workspace": req.workspace, "session_id": chat_session.session_id,
    }


@app.delete("/session")
async def delete_session():
    # Disconnect agent session
    if _session.adapter:
        try:
            await _session.adapter.disconnect()
        except Exception:
            pass
    _chat_history.close_session()
    _session.close()
    return {"status": "closed"}


# -- Chat -------------------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    if not _session.active or _session.adapter is None:
        raise HTTPException(status_code=400, detail="No active session")

    # Save user message
    _chat_history.add_user_message(req.message)

    # Query agent
    messages = await _session.adapter.query(req.message)

    # Save agent responses
    for msg in messages:
        if msg.get("type") == "text" and msg.get("text"):
            _chat_history.add_agent_message(msg["text"])

    return {"messages": messages}


@app.get("/chat/history")
async def get_chat_history():
    """Get current session's chat history."""
    session = _chat_history.get_current()
    if not session:
        return {"messages": []}
    return {
        "session_id": session.session_id,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in session.messages
        ],
    }


@app.get("/chat/sessions")
async def list_chat_sessions():
    """List all saved chat sessions."""
    return {"sessions": _chat_history.list_sessions()}


# -- Four-primitive query (read-only) --------------------------------------

@app.get("/roles")
async def list_roles():
    roles_dir = AGENT_DIR / "role"
    if not roles_dir.exists():
        return {"roles": []}
    roles = sorted(
        p.name for p in roles_dir.iterdir() if p.is_dir()
    )
    return {"roles": roles}


@app.get("/roles/{name}")
async def get_role(name: str):
    soul_path = AGENT_DIR / "role" / name / "SOUL.md"
    if not soul_path.exists():
        raise HTTPException(status_code=404, detail=f"Role '{name}' not found")
    soul = soul_path.read_text(encoding="utf-8")
    return {"name": name, "soul": soul}


@app.get("/flows")
async def list_flows():
    flows_dir = AGENT_DIR / "flow"
    if not flows_dir.exists():
        return {"flows": []}
    flows = sorted(
        p.name for p in flows_dir.iterdir() if p.is_dir()
    )
    return {"flows": flows}


# In-memory state tracking
_flow_states: dict[str, str] = {}

@app.get("/flows/state")
async def get_flow_state(flow: str | None = None):
    """Get current state of flow state machines."""
    if flow:
        return {"flow": flow, "state": _flow_states.get(flow, "_none_")}
    return {"states": _flow_states}

@app.post("/flows/transition")
async def transition_flow(req: dict):
    """Execute a state transition."""
    flow_name = req.get("flow", "")
    action = req.get("action", "")
    flow_yaml = AGENT_DIR / "flow" / "flow.yaml"
    if not flow_yaml.exists():
        raise HTTPException(404, "flow.yaml not found")
    data = yaml.safe_load(flow_yaml.read_text(encoding="utf-8")) or {}
    flows = data.get("flows", {})
    if not flows or flow_name not in flows:
        raise HTTPException(404, f"Flow '{flow_name}' not defined")
    flow_def = flows[flow_name]
    current_state = _flow_states.get(flow_name, "_none_")
    for t in flow_def.get("transitions", []):
        if t["from"] == current_state and t["action"] == action:
            _flow_states[flow_name] = t["to"]
            return {"flow": flow_name, "from": current_state, "to": t["to"], "action": action}
    raise HTTPException(400, f"No transition from '{current_state}' via '{action}'")

@app.get("/flows/registry")
async def get_flows_registry():
    flow_yaml = AGENT_DIR / "flow" / "flow.yaml"
    if not flow_yaml.exists():
        raise HTTPException(status_code=404, detail="flow.yaml not found")
    data = yaml.safe_load(flow_yaml.read_text(encoding="utf-8"))
    return data


@app.get("/scope")
async def get_scope():
    soul_path = AGENT_DIR / "scope" / "SOUL.md"
    if not soul_path.exists():
        raise HTTPException(status_code=404, detail="scope/SOUL.md not found")
    soul = soul_path.read_text(encoding="utf-8")
    return {"soul": soul}


@app.get("/commitments")
async def get_commitments():
    eval_yaml = AGENT_DIR / "commitment" / "eval.yaml"
    if not eval_yaml.exists():
        raise HTTPException(status_code=404, detail="eval.yaml not found")
    data = yaml.safe_load(eval_yaml.read_text(encoding="utf-8"))
    return data


# -- Metrics / Eval ---------------------------------------------------------

@app.get("/metrics")
async def get_metrics():
    """Return evaluation results for all commitments."""
    eval_yaml = AGENT_DIR / "commitment" / "eval.yaml"
    if not eval_yaml.exists():
        return {"metrics": []}
    db_path = RUNTIME_DIR / "data" / "Sqlite" / "socialware.db"
    runner = EvalRunner(eval_yaml, db_path=db_path if db_path.exists() else None)
    results = runner.run_all()
    return {"metrics": [
        {"id": r.commitment_id, "description": r.description,
         "metric": r.metric, "threshold": r.threshold,
         "value": r.value, "passed": r.passed}
        for r in results
    ]}


@app.post("/eval")
async def run_eval(req: dict):
    """Run evaluation for a specific commitment or all."""
    eval_yaml = AGENT_DIR / "commitment" / "eval.yaml"
    if not eval_yaml.exists():
        raise HTTPException(404, "eval.yaml not found")
    db_path = RUNTIME_DIR / "data" / "Sqlite" / "socialware.db"
    runner = EvalRunner(eval_yaml, db_path=db_path if db_path.exists() else None)
    cid = req.get("commitment_id", "all")
    if cid == "all":
        results = runner.run_all()
    else:
        results = [runner.run(cid)]
    return {"results": [
        {"id": r.commitment_id, "passed": r.passed, "value": r.value, "threshold": r.threshold}
        for r in results
    ]}


# -- Workspaces -------------------------------------------------------------

@app.get("/workspaces")
async def list_workspaces():
    """List all workspace instances."""
    ws_dir = APP_ROOT / ".socialware" / "workspace"
    if not ws_dir.exists():
        return {"workspaces": []}
    workspaces = []
    for room_dir in sorted(ws_dir.iterdir()):
        if not room_dir.is_dir() or room_dir.name.startswith("."):
            continue
        for app_dir in sorted(room_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            workspaces.append({
                "room": room_dir.name,
                "app": app_dir.name,
                "path": str(app_dir.relative_to(APP_ROOT)),
                "has_runtime": (app_dir / ".runtime").exists(),
            })
    return {"workspaces": workspaces}

@app.post("/workspaces")
async def create_workspace(req: WorkspaceRequest):
    """Create a new workspace via create-my-socialware."""
    import subprocess
    script = APP_ROOT / "scripts" / "create-my-socialware.py"
    if not script.exists():
        raise HTTPException(500, "create-my-socialware.py not found")
    result = subprocess.run(
        ["python", str(script), "--room", req.room, "--app", req.app_name,
         "--description", req.description or f"{req.app_name} App"],
        capture_output=True, text=True, cwd=str(APP_ROOT),
    )
    if result.returncode != 0:
        raise HTTPException(400, f"Failed: {result.stderr}")
    return {"status": "created", "room": req.room, "app": req.app_name}

@app.delete("/workspaces/{room}/{app_name}")
async def delete_workspace(room: str, app_name: str):
    """Delete a workspace."""
    import shutil as _shutil
    ws_dir = APP_ROOT / ".socialware" / "workspace" / room / app_name
    if not ws_dir.exists():
        raise HTTPException(404, "Workspace not found")
    _shutil.rmtree(ws_dir)
    return {"status": "deleted"}

@app.post("/workspaces/{room}/{app_name}/sync")
async def sync_workspace(room: str, app_name: str):
    """Sync workspace with upstream (placeholder)."""
    ws_dir = APP_ROOT / ".socialware" / "workspace" / room / app_name
    if not ws_dir.exists():
        raise HTTPException(404, "Workspace not found")
    return {"status": "sync not yet implemented"}


# -- ZChat ------------------------------------------------------------------

@app.post("/zchat/receive")
async def zchat_receive(msg: dict):
    """Receive a ZChat message from another App."""
    zchat_msg = ZChatMessage.from_dict(msg)
    result = _zchat_router.dispatch(zchat_msg)
    return {"status": "received", "result": result}

@app.get("/zchat/discover")
async def zchat_discover():
    """Expose this App's SOUL.md for service discovery."""
    soul_path = AGENT_DIR / "scope" / "SOUL.md"
    soul = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""
    return {"app": "socialware", "soul": soul}

@app.post("/zchat/send")
async def zchat_send(msg: dict):
    """Send a ZChat message to another App (HTTP transport)."""
    target_url = msg.get("target_url", "")
    if not target_url:
        raise HTTPException(400, "target_url required")
    try:
        import httpx
        async with httpx.AsyncClient() as http_client:
            r = await http_client.post(f"{target_url}/zchat/receive", json=msg, timeout=30)
            return {"status": "sent", "response": r.json()}
    except Exception as exc:
        raise HTTPException(502, f"Failed to reach target: {exc}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
