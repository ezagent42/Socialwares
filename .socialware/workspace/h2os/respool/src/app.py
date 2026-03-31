"""ResPool App backend — FastAPI entry point.

Serves the test web UI + WebSocket chat endpoint for Agent interaction.
Errors auto-record as violations and can trigger evolver diagnose.
Start: uv run uvicorn src.app:app --port $APP_PORT
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import traceback
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Windows GBK fix: force UTF-8 for subprocess and file I/O
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# App config
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))
ADAPTER_NAME = os.getenv("ADAPTER", "claude")
AUTO_EVOLVE = os.getenv("AUTO_EVOLVE", "false").lower() == "true"

APP_ROOT = Path(__file__).parent.parent
RUNTIME_DIR = APP_ROOT / ".runtime"
VIOLATIONS_DIR = RUNTIME_DIR / "data" / "evolve" / "violations"
ERROR_LOG_DIR = RUNTIME_DIR / "data" / "evolve" / "errors"

app = FastAPI(
    title="ResPool",
    description="Resource pool management — Agent interaction visualization",
    version="0.1.0",
)

# Serve static files (test web UI)
STATIC_DIR = APP_ROOT / "app" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Error → Violation → Evolve pipeline ---

def _record_error(error: Exception, context: dict) -> dict:
    """Record a runtime error as a violation + error log.

    Returns the violation dict for immediate use.
    """
    now = datetime.now(timezone.utc)
    error_id = f"err-{uuid.uuid4().hex[:8]}"

    # 1. Write detailed error log
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    error_entry = {
        "id": error_id,
        "timestamp": now.isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context,
    }
    error_file = ERROR_LOG_DIR / f"{now.strftime('%Y%m%d')}.jsonl"
    with open(error_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(error_entry, ensure_ascii=False, default=str) + "\n")

    # 2. Write as violation (evolver can pick this up)
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    violation = {
        "id": error_id,
        "timestamp": now.isoformat(),
        "type": "runtime_error",
        "severity": "error",
        "source": context.get("source", "unknown"),
        "description": f"{type(error).__name__}: {error}",
        "context": context,
        "resolved": False,
    }
    violations_file = VIOLATIONS_DIR / "runtime_errors.jsonl"
    with open(violations_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(violation, ensure_ascii=False, default=str) + "\n")

    return violation


async def _trigger_evolve_diagnose(violation: dict) -> None:
    """Trigger evolver to diagnose an error (background, best-effort).

    Only runs if AUTO_EVOLVE=true. Loads evolver role adapter and sends
    a diagnose prompt with the error context.
    """
    if not AUTO_EVOLVE:
        return

    try:
        from claude_code_sdk import query, ClaudeCodeOptions
        prompt = (
            f"A runtime error just occurred. Please diagnose and suggest a fix.\n\n"
            f"Error ID: {violation['id']}\n"
            f"Type: {violation['description']}\n"
            f"Source: {violation['context'].get('source', 'unknown')}\n"
            f"Role: {violation['context'].get('role', 'unknown')}\n"
            f"User input: {violation['context'].get('prompt', 'N/A')}\n\n"
            f"Error log: .runtime/data/evolve/errors/\n"
            f"Violation log: .runtime/data/evolve/violations/runtime_errors.jsonl\n\n"
            f"Run evolve_session_diagnose then evolve_improve if you can identify the root cause."
        )
        soul = _load_soul("evolver")
        options = ClaudeCodeOptions(
            cwd=str(APP_ROOT),
            system_prompt=soul,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
            permission_mode="bypassPermissions",
        )
        async for _ in query(prompt=prompt, options=options):
            pass  # consume stream
    except Exception:
        pass  # best-effort, don't let evolve failure break the app


# --- Health ---

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Test Web UI ---

@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = APP_ROOT / "app" / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return HTMLResponse("<h1>ResPool</h1><p>app/index.html not found.</p>")


# --- WebSocket Chat ---

def _get_role_dir(role: str) -> Path:
    return RUNTIME_DIR / "agents" / role


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket chat — streams Agent responses via claude-code-sdk."""
    await ws.accept()

    try:
        init = await ws.receive_json()
        role = init.get("role", "default")

        if not RUNTIME_DIR.exists():
            await ws.send_json({"type": "error", "content": ".runtime/ not found. Run 'make deploy' first."})
            await ws.close()
            return

        role_dir = _get_role_dir(role)
        if not role_dir.exists():
            await ws.send_json({"type": "error", "content": f"Role '{role}' not deployed."})
            await ws.close()
            return

        await ws.send_json({"type": "system", "content": f"Connected as {role}. Agent adapter: {ADAPTER_NAME}"})

        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "user_message":
                continue

            prompt = msg.get("content", "").strip()
            if not prompt:
                continue

            await ws.send_json({"type": "status", "content": "thinking"})

            try:
                import subprocess, shutil

                claude_path = shutil.which("claude") or shutil.which("claude.CMD")
                if not claude_path:
                    raise RuntimeError("claude CLI not found in PATH")

                soul_path = role_dir / "SOUL.md"
                cmd = [
                    claude_path,
                    "--output-format", "stream-json",
                    "--verbose",
                    "--permission-mode", "bypassPermissions",
                    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep",
                    "--print",
                ]
                if soul_path.exists():
                    cmd.extend(["--append-system-prompt-file", str(soul_path)])
                cmd.extend(["--", prompt])

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(role_dir),
                    env={**os.environ, "PYTHONUTF8": "1"},
                )

                # Stream stdout line by line

                async for raw_line in proc.stdout:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    dtype = data.get("type", "")

                    # Only use result (final answer), skip assistant (duplicate streaming)
                    if dtype == "result":
                        result_text = data.get("result", "")
                        if result_text:
                            await ws.send_json({"type": "agent", "content": result_text, "msg_type": "result"})

                await proc.wait()
                await ws.send_json({"type": "done"})

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"

                # Record error → violation
                violation = _record_error(e, {
                    "source": "ws_chat",
                    "role": role,
                    "prompt": prompt,
                    "adapter": ADAPTER_NAME,
                })

                await ws.send_json({
                    "type": "error",
                    "content": f"Agent error: {error_msg}",
                    "violation_id": violation["id"],
                })

                # Trigger evolver in background (if AUTO_EVOLVE=true)
                asyncio.create_task(_trigger_evolve_diagnose(violation))

    except WebSocketDisconnect:
        pass


# --- Violations + Errors API ---

@app.get("/violations")
async def list_violations() -> list[dict]:
    violations = []
    if not VIOLATIONS_DIR.exists():
        return violations
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = json.loads(line)
                if not v.get("resolved", False):
                    violations.append(v)
    return violations


@app.get("/errors")
async def list_errors() -> list[dict]:
    """List recent runtime errors (detailed, for debugging)."""
    errors = []
    if not ERROR_LOG_DIR.exists():
        return errors
    for f in sorted(ERROR_LOG_DIR.glob("*.jsonl"), reverse=True)[:7]:  # last 7 days
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                errors.append(json.loads(line))
    return errors


@app.post("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: str) -> dict:
    if not VIOLATIONS_DIR.exists():
        raise HTTPException(404, f"Violation {violation_id} not found")
    for f in VIOLATIONS_DIR.glob("*.jsonl"):
        lines = f.read_text(encoding="utf-8").splitlines()
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
            f.write_text("\n".join(updated) + "\n", encoding="utf-8")
            return {"status": "resolved", "id": violation_id}
    raise HTTPException(404, f"Violation {violation_id} not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
