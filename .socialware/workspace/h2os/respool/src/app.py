"""ResPool App backend — FastAPI entry point.

Serves the test web UI + WebSocket chat endpoint for Agent interaction.
Start: uv run uvicorn src.app:app --port $APP_PORT
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# App config
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))
ADAPTER_NAME = os.getenv("ADAPTER", "claude")

APP_ROOT = Path(__file__).parent.parent
RUNTIME_DIR = APP_ROOT / ".runtime"
VIOLATIONS_DIR = RUNTIME_DIR / "data" / "evolve" / "violations"

app = FastAPI(
    title="ResPool",
    description="Resource pool management — Agent interaction visualization",
    version="0.1.0",
)

# Serve static files (test web UI)
STATIC_DIR = APP_ROOT / "app" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Health ---

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Test Web UI ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the test chat UI."""
    index_file = APP_ROOT / "app" / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return HTMLResponse("<h1>ResPool</h1><p>app/index.html not found. Run from workspace root.</p>")


# --- WebSocket Chat ---

def _load_adapter(role: str):
    """Load SDK adapter for the given role."""
    adapter_path = APP_ROOT / "agent" / "adapters"
    sys.path.insert(0, str(adapter_path))
    sys.path.insert(0, str(adapter_path / ADAPTER_NAME))

    from base import RoleConfig

    project_dir = RUNTIME_DIR / "agents" / role
    if not project_dir.exists():
        raise FileNotFoundError(f"Role '{role}' not deployed at {project_dir}")

    config = RoleConfig.from_runtime(project_dir)
    mod = importlib.import_module(f"{ADAPTER_NAME}.sdk")

    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and hasattr(attr, "launch_sdk") and attr_name != "BaseAdapter":
            return attr(config)

    raise RuntimeError(f"No adapter found in {ADAPTER_NAME}/sdk.py")


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket chat — streams Agent responses token by token."""
    await ws.accept()

    try:
        # Wait for init message
        init = await ws.receive_json()
        role = init.get("role", "default")

        # Check deployment
        if not RUNTIME_DIR.exists():
            await ws.send_json({"type": "error", "content": ".runtime/ not found. Run 'make deploy' first."})
            await ws.close()
            return

        await ws.send_json({"type": "system", "content": f"Connected as {role}. Agent adapter: {ADAPTER_NAME}"})

        # Chat loop
        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "user_message":
                continue

            prompt = msg.get("content", "").strip()
            if not prompt:
                continue

            await ws.send_json({"type": "status", "content": "thinking"})

            try:
                adapter = _load_adapter(role)
                from base import is_noise

                async for message in adapter.launch_sdk(prompt):
                    m = message if isinstance(message, dict) else {"_type": "raw", "content": str(message)}

                    if is_noise(m):
                        continue

                    # Extract text content
                    content = ""
                    if "content" in m and isinstance(m["content"], str):
                        content = m["content"]
                    elif "result" in m and isinstance(m["result"], str):
                        content = m["result"]

                    msg_type = m.get("_type", "unknown")

                    await ws.send_json({
                        "type": "agent",
                        "content": content,
                        "msg_type": msg_type,
                        "raw": m,
                    })

                await ws.send_json({"type": "done"})

            except NotImplementedError as e:
                await ws.send_json({"type": "error", "content": str(e)})
            except Exception as e:
                await ws.send_json({"type": "error", "content": f"Agent error: {type(e).__name__}: {e}"})

    except WebSocketDisconnect:
        pass


# --- Violations API ---

@app.get("/violations")
async def list_violations() -> list[dict]:
    violations = []
    if not VIOLATIONS_DIR.exists():
        return violations
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                if not v.get("resolved", False):
                    violations.append(v)
    return violations


@app.post("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: str) -> dict:
    if not VIOLATIONS_DIR.exists():
        raise HTTPException(404, f"Violation {violation_id} not found")
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        lines = f.read_text().splitlines()
        updated = []
        found = False
        for line in lines:
            if line.strip():
                v = json.loads(line)
                if v.get("id") == violation_id:
                    v["resolved"] = True
                    v["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    found = True
                updated.append(json.dumps(v, ensure_ascii=False))
        if found:
            f.write_text("\n".join(updated) + "\n")
            return {"status": "resolved", "id": violation_id}
    raise HTTPException(404, f"Violation {violation_id} not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
