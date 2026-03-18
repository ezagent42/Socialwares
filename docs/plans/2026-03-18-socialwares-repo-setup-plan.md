# Socialwares 仓库初始化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Initialize the empty Socialwares MonoRepo with Claude dev config (from agent-setup) + GitAgent-format agent/ directory + multi-platform adapter scripts + mock SW app stubs + dev guide.

**Architecture:** Two-track setup — (1) extract and adapt Claude Code config from agent-setup for development, (2) create agent/ directory following GitAgent spec + AutoService runtime pattern. SW apps (TaskArena, AgentForge) are stubbed with mock implementations based on four Socialware primitives (Role/Flow/Commitment/Arena). All wired via symlinks and setup scripts.

**Tech Stack:** Bash (scripts), Python 3.12+ (adapters, mock apps, shared libs), uv (package manager), YAML (GitAgent config), Markdown (SKILL.md, SOUL.md)

**Target Repo:** `git@github.com:ezagent42/Socialwares.git` (currently empty)

---

## Pre-requisites

Before starting, clone the empty repo:

```bash
cd ~/projects
gh repo clone ezagent42/Socialwares
cd Socialwares
git checkout -b feat/initial-setup
```

---

## Task 1: Repo skeleton + .gitignore + pyproject.toml

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `README.md`

**Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/

# Agent runtime state
.gitagent/
agent/agents/_generated/

# User-local overrides
claude.local.sh
.mcp.env

# Secrets
.env
*.key

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

**Step 2: Create pyproject.toml (uv workspace)**

```toml
[project]
name = "socialwares"
version = "0.1.0"
description = "Socialwares MonoRepo — SW Apps for agent-driven collaboration"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["apps/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Create README.md**

```markdown
# Socialwares

Socialware App MonoRepo — 面向 agent 的协作应用。

## 快速开始

\```bash
# 克隆仓库
gh repo clone ezagent42/Socialwares
cd Socialwares

# 配置 Claude Code 开发环境
./scripts/setup-claude.sh

# 启动开发
claude
\```

## 目录结构

- `apps/` — Socialware App 本体 (TaskArena, AgentForge)
- `agent/` — GitAgent 格式的 agent 定义 (本机启动)
- `scripts/` — 运维和适配脚本
- `scenarios/` — 多 agent 场景编排
- `docs/` — 文档

## 四原语

每个 Socialware App 通过四个原语暴露 API:

- **Role** — 角色定义与权限
- **Flow** — 状态机与流程
- **Commitment** — 承诺与 SLA
- **Arena** — 作用域与可见性
```

**Step 4: Commit**

```bash
git add .gitignore pyproject.toml README.md
git commit -m "chore: repo skeleton with pyproject.toml and gitignore"
```

---

## Task 2: Claude Code config from agent-setup

**Files:**
- Create: `.claude/settings.json`
- Create: `.claude/mcp.json`
- Create: `.claude/CLAUDE.md`
- Create: `CLAUDE.md`
- Create: `hooks/enforce-tools.sh`
- Create: `hooks/session-start.sh`
- Create: `.claude/settings.local.json` (template, gitignored)
- Create: `claude.sh`

**Step 1: Create .claude/settings.json**

Adapted from agent-setup — keep bypassPermissions, plugins, teammate mode:

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  },
  "enabledPlugins": {
    "playground@claude-plugins-official": true,
    "hookify@claude-plugins-official": true,
    "skill-creator@claude-plugins-official": true
  },
  "teammateMode": "auto",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "hooks/enforce-tools.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "hooks/session-start.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

> **注意**: hooks 注册在 settings.json 中（非插件模式），不使用 hooks.json。

**Step 2: Create .claude/mcp.json**

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

**Step 3: Create .claude/CLAUDE.md**

```markdown
# CLAUDE.md — Socialwares

## Project Overview

Socialwares MonoRepo — 面向 agent 的协作应用集合。

每个 App（TaskArena、AgentForge 等）是独立 Python 服务，暴露 API，
agent 通过 Role/Flow/Commitment/Arena 四原语进行调用。

## Directory Structure

- `apps/` — Socialware App 本体 (Python API server)
- `agent/` — GitAgent 格式的 agent 定义
- `agent/skills/` — Agent 技能 (per-skill symlinked to .claude/skills/)
- `agent/adapters/` — SDK 启动模板 (Claude, Codex, KimiCode)
- `scripts/` — 运维和适配脚本
- `scenarios/` — 多 agent 场景编排
- `docs/` — 文档

## Conventions

- Python packages: use `uv`, not `pip`
- JavaScript packages: use `pnpm`, not `npm`/`npx`
- Python 3.12+, strict type hints
- 中文文档，英文变量名
- Tests: pytest, target >90% coverage

## Four Primitives (四原语)

Every SW App exposes its API through:
- **Role**: 角色定义与权限检查
- **Flow**: 状态机定义与转换
- **Commitment**: SLA 承诺与超时追踪
- **Arena**: 作用域（谁能看到、谁能参与）

## Development

```bash
# Run tests
uv run pytest

# Run specific app
uv run --package taskarena pytest

# Launch agent
./scripts/launch.sh --adapter claude
```
```

**Step 4: Create top-level CLAUDE.md** (same content, symlink or copy — use copy for git compatibility)

Copy `.claude/CLAUDE.md` to `./CLAUDE.md`.

**Step 5: Create hooks/enforce-tools.sh**

Copy verbatim from agent-setup `hooks/enforce-tools.sh` (88 lines, blocks pip/npm, suggests uv/pnpm). Make executable.

**Step 6: Create hooks/session-start.sh**

Adapted from agent-setup — check for agent/ directory health instead of plugin:

```bash
#!/usr/bin/env bash
# session-start.sh — Health check for Socialwares dev environment
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MSG="Socialwares dev environment active"
STATUS="ok"

if [ ! -f "${REPO_ROOT}/agent/agent.yaml" ]; then
  MSG="agent/agent.yaml missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
fi

if [ ! -d "${REPO_ROOT}/.claude/skills" ]; then
  MSG=".claude/skills/ directory missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
elif [ ! -L "${REPO_ROOT}/.claude/skills/taskarena" ]; then
  MSG=".claude/skills/ symlinks missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${MSG}"
  }
}
EOF
```

**Step 7: Create claude.sh**

Copy from agent-setup `templates/claude.sh.tpl` (source: `/tmp/agent-setup-plan/templates/claude.sh.tpl` or `git@github.com:ezagent42/agent-setup.git templates/claude.sh.tpl`).

**Precise changes to make:**

1. **DELETE lines 72-105** — the entire "Agent Setup plugin bootstrap" section:
   - Remove: `AGENT_SETUP_MARKETPLACE=...`
   - Remove: `if ! grep -q '"agent-setup"' ...` marketplace registration block
   - Remove: `PLUGIN_INSTALLED=false` ... plugin installation block
   - Remove: `if [ "$PLUGIN_INSTALLED" != "true" ]` block
   - Start from `# ============================================` comment "Agent Setup plugin bootstrap" to the next `# ============================================` comment "Flags per mode"

2. **KEEP everything else** (368→~330 lines):
   - Lines 1-71: Shell config sourcing, PATH setup, pre-flight checks (tmux, claude) — KEEP AS-IS
   - Lines 106-end: Flags, iTerm2 detection, session management, mode selection, tmux session creation — KEEP AS-IS

3. **Verify** the resulting file:
   - No references to `agent-setup`, `plugin`, `marketplace`, `installed_plugins.json`
   - `INTERACTIVE_FLAGS` still includes `--permission-mode bypassPermissions`
   - mcp.json loading (`if [ -f "$SCRIPT_DIR/.claude/mcp.json" ]`) still present

**Step 8: Commit**

```bash
chmod +x hooks/enforce-tools.sh hooks/session-start.sh claude.sh
git add .claude/ CLAUDE.md hooks/ claude.sh
git commit -m "feat: Claude Code dev config adapted from agent-setup"
```

---

## Task 3: agent/ core — agent.yaml + SOUL.md + RULES.md

**Files:**
- Create: `agent/agent.yaml`
- Create: `agent/SOUL.md`
- Create: `agent/RULES.md`

**Step 1: Create agent/agent.yaml**

```yaml
name: socialwares-dev
version: "0.1.0"
description: "Socialwares MonoRepo 开发者 agent — 开发和测试 Socialware Apps"
spec_version: "0.1.0"

author: ezagent42
license: proprietary
tags: [socialware, development, multi-agent]

model:
  preferred: claude-sonnet-4-6
  fallback:
    - claude-haiku-4-5-20251001

skills:
  - _shared
  - taskarena
  - agentforge
  - dev

tools:
  - taskarena-api
  - agentforge-api

dependencies: []

runtime:
  max_turns: 100
  timeout: 3600
```

**Step 2: Create agent/SOUL.md**

```markdown
# Socialwares Developer Agent

你是 Socialwares 项目的开发者 agent。

## 身份

你帮助开发者构建 Socialware Apps — 面向 agent 的协作应用。
每个 App 通过 Role/Flow/Commitment/Arena 四原语暴露 API。

## 职责

1. **开发 SW Apps**: TaskArena (任务管理), AgentForge (agent 管理)
2. **测试四原语**: 确保每个 App 正确实现 Role 权限、Flow 状态机、Commitment SLA、Arena 作用域
3. **自举**: 用已开发的 App 管理开发过程本身
4. **编排**: 配置多 agent 场景，测试 agent 间协作

## 原则

- 代码简洁，类型严格 (Python typing)
- 测试优先 (TDD)
- 四原语是核心抽象，所有 API 都必须映射到四原语
- 中文文档，英文变量名
```

**Step 3: Create agent/RULES.md**

```markdown
# 开发约束

## 必须

- 所有 Python 代码必须使用 type hints
- 所有 API 必须映射到四原语 (Role/Flow/Commitment/Arena)
- 使用 uv 管理 Python 依赖，不使用 pip
- 每个 App 必须有 tests/ 目录和 >90% 覆盖率
- config.yaml 中的 roles/flows/commitments 必须与 .socialware.md 定义一致

## 禁止

- 不使用 pip/npm/npx (使用 uv/pnpm)
- 不在 agent/agents/ 手动创建文件 (通过 AgentForge scripts 生成)
- 不硬编码 API URL (使用 config.yaml)
- 不跳过 pre_send 权限检查
```

**Step 4: Commit**

```bash
git add agent/agent.yaml agent/SOUL.md agent/RULES.md
git commit -m "feat: agent/ core — GitAgent identity (agent.yaml, SOUL.md, RULES.md)"
```

---

## Task 4: agent/skills/_shared/ — shared libraries

**Files:**
- Create: `agent/skills/_shared/__init__.py`
- Create: `agent/skills/_shared/config.py`
- Create: `agent/skills/_shared/sw_client.py`
- Create: `agent/skills/_shared/scripts/call_api.py`

**Step 1: Create __init__.py**

```python
"""Shared libraries for Socialware agent skills."""
```

**Step 2: Create config.py**

```python
"""Configuration loader for Socialware skills.

Loads config.yaml from each skill directory. Follows AutoService pattern.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_skill_config(skill_dir: str | Path) -> dict[str, Any]:
    """Load config.yaml from a skill directory.

    Args:
        skill_dir: Path to the skill directory containing config.yaml

    Returns:
        Parsed config dict. Empty dict if config.yaml not found.
    """
    config_path = Path(skill_dir) / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_api_url(config: dict[str, Any]) -> str:
    """Extract API base URL from skill config."""
    return config.get("api_url", "http://localhost:8000")
```

**Step 3: Create sw_client.py**

```python
"""Socialware App API client.

Generic HTTP client for calling SW App APIs.
All SW Apps expose CRUD + action endpoints following four-primitive pattern.
"""
from __future__ import annotations

import json
import sys
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class SWClient:
    """Generic Socialware App API client."""

    def __init__(self, base_url: str, identity: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.identity = identity

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send HTTP request to SW App API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /tasks, /tasks/123)
            data: Request body (JSON)

        Returns:
            Parsed JSON response
        """
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.identity:
            headers["X-Identity"] = self.identity

        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            error_body = e.read().decode()
            print(f"API Error {e.code}: {error_body}", file=sys.stderr)
            return {"error": e.code, "detail": error_body}


def create_client(config: dict[str, Any]) -> SWClient:
    """Create SWClient from skill config."""
    return SWClient(
        base_url=config.get("api_url", "http://localhost:8000"),
        identity=config.get("identity"),
    )
```

**Step 4: Create scripts/call_api.py**

```python
#!/usr/bin/env python3
"""Generic API call script for Socialware skills.

Usage:
  uv run call_api.py --config ../taskarena/config.yaml --method GET --path /tasks
  uv run call_api.py --config ../taskarena/config.yaml --method POST --path /tasks --data '{"title":"test"}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import load_skill_config
from sw_client import create_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Socialware App API")
    parser.add_argument("--config", required=True, help="Path to skill config.yaml")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--path", required=True, help="API path")
    parser.add_argument("--data", help="JSON request body")
    args = parser.parse_args()

    config = load_skill_config(Path(args.config).parent)
    client = create_client(config)

    data = json.loads(args.data) if args.data else None
    result = client.request(args.method, args.path, data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 5: Commit**

```bash
git add agent/skills/_shared/
git commit -m "feat: agent/skills/_shared — config loader + SW API client"
```

---

## Task 5: agent/skills/taskarena/ — TaskArena skill (mock)

**Files:**
- Create: `agent/skills/taskarena/SKILL.md`
- Create: `agent/skills/taskarena/config.yaml`
- Create: `agent/skills/taskarena/scripts/create_task.py`
- Create: `agent/skills/taskarena/scripts/update_task.py`
- Create: `agent/skills/taskarena/scripts/query_task.py`
- Create: `agent/skills/taskarena/scripts/review_task.py`
- Create: `agent/skills/taskarena/references/taskarena-api.md`

**Step 1: Create SKILL.md**

```markdown
---
name: taskarena
description: "TaskArena Socialware App — 任务 CRUD、状态机、角色权限、SLA 追踪"
---

# TaskArena

任务管理 Socialware App。通过四原语 (Role/Flow/Commitment/Arena) 管理任务生命周期。

## Commands

| 命令 | 说明 | 需要角色 |
|------|------|----------|
| /taskarena create | 创建任务 | R2 (提交者) |
| /taskarena update | 更新任务 | R2 (提交者) |
| /taskarena review | 审核任务 | R3 (审核者) |
| /taskarena query | 查询任务 | 所有角色 |
| /taskarena close | 关闭任务 | R1 (管理员) |

## 四原语

### Role (角色)

- R1 管理员: propose, assign, review, close, force_resolve
- R2 提交者: propose, submit, update
- R3 审核者: review, comment

### Flow (状态机)

```
draft → [propose] → submitted → [review] → under_review
     → [approve] → approved → [close] → closed
     → [reject] → rejected → [resubmit] → submitted
```

### Commitment (承诺)

- C1: 审核者在任务提交后 72h 内完成审核
- C2: 管理员在 C1 违约后 24h 内 force_resolve

### Arena (作用域)

- min: 2 人
- 基于 Room 成员身份

## Usage

```bash
# 创建任务
uv run agent/skills/taskarena/scripts/create_task.py --title "GPS采购" --budget 300000

# 查询任务
uv run agent/skills/taskarena/scripts/query_task.py --id task-001

# 审核任务
uv run agent/skills/taskarena/scripts/review_task.py --id task-001 --decision approve

# 更新任务
uv run agent/skills/taskarena/scripts/update_task.py --id task-001 --status under_review
```
```

**Step 2: Create config.yaml**

```yaml
domain: taskarena
api_url: http://localhost:8001
language: zh

roles:
  R1:
    name: admin
    label: "管理员"
    permissions: [propose, assign, review, close, force_resolve]
  R2:
    name: submitter
    label: "提交者"
    permissions: [propose, submit, update]
  R3:
    name: reviewer
    label: "审核者"
    permissions: [review, comment]

flow:
  name: task_lifecycle
  states: [draft, submitted, under_review, approved, rejected, closed]
  transitions:
    - from: draft
      to: submitted
      action: propose
      role: R2
    - from: submitted
      to: under_review
      action: review
      role: R3
    - from: under_review
      to: approved
      action: approve
      role: R3
    - from: under_review
      to: rejected
      action: reject
      role: R3
    - from: rejected
      to: submitted
      action: resubmit
      role: R2
    - from: approved
      to: closed
      action: close
      role: R1

commitments:
  C1:
    description: "审核者在任务提交后 72h 内完成审核"
    trigger_state: submitted
    deadline_hours: 72
    escalation_role: R1
  C2:
    description: "管理员在 C1 违约后 24h 内 force_resolve"
    trigger: C1_violation     # 由 C1 超时触发，不是状态触发
    deadline_hours: 24
    escalation_role: R1

arena:
  min_members: 2
  scope: room
```

**Step 3: Create scripts/create_task.py**

```python
#!/usr/bin/env python3
"""Create a task in TaskArena.

Usage:
  uv run create_task.py --title "GPS采购" --budget 300000
  uv run create_task.py --title "代码审查" --assignee bob
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Create TaskArena task")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--budget", type=float, help="Budget amount")
    parser.add_argument("--assignee", help="Assignee identity")
    parser.add_argument("--description", help="Task description")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {"title": args.title, "status": "draft"}
    if args.budget:
        data["budget"] = args.budget
    if args.assignee:
        data["assignee"] = args.assignee
    if args.description:
        data["description"] = args.description

    result = client.request("POST", "/tasks", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 4: Create scripts/update_task.py**

```python
#!/usr/bin/env python3
"""Update a task in TaskArena.

Usage:
  uv run update_task.py --id task-001 --status under_review
  uv run update_task.py --id task-001 --title "Updated title"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Update TaskArena task")
    parser.add_argument("--id", required=True, help="Task ID")
    parser.add_argument("--status", help="New status")
    parser.add_argument("--title", help="New title")
    parser.add_argument("--assignee", help="New assignee")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data: dict = {}
    if args.status:
        data["status"] = args.status
    if args.title:
        data["title"] = args.title
    if args.assignee:
        data["assignee"] = args.assignee

    result = client.request("PUT", f"/tasks/{args.id}", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 5: Create scripts/query_task.py**

```python
#!/usr/bin/env python3
"""Query tasks from TaskArena.

Usage:
  uv run query_task.py                    # list all
  uv run query_task.py --id task-001      # get one
  uv run query_task.py --status submitted # filter by status
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Query TaskArena tasks")
    parser.add_argument("--id", help="Task ID (get one)")
    parser.add_argument("--status", help="Filter by status")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    if args.id:
        result = client.request("GET", f"/tasks/{args.id}")
    elif args.status:
        result = client.request("GET", f"/tasks?status={args.status}")
    else:
        result = client.request("GET", "/tasks")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 6: Create scripts/review_task.py**

```python
#!/usr/bin/env python3
"""Review a task in TaskArena.

Usage:
  uv run review_task.py --id task-001 --decision approve
  uv run review_task.py --id task-001 --decision reject --reason "缺售后条款"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Review TaskArena task")
    parser.add_argument("--id", required=True, help="Task ID")
    parser.add_argument("--decision", required=True, choices=["approve", "reject"])
    parser.add_argument("--reason", help="Review reason (required for reject)")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {"decision": args.decision}
    if args.reason:
        data["reason"] = args.reason

    result = client.request("POST", f"/tasks/{args.id}/review", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 7: Create references/taskarena-api.md**

```markdown
# TaskArena API Reference

## Endpoints

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | /tasks | 创建任务 | R2 |
| GET | /tasks | 查询任务列表 | any |
| GET | /tasks/{id} | 查询单个任务 | any |
| PUT | /tasks/{id} | 更新任务 | R2 |
| POST | /tasks/{id}/review | 审核任务 | R3 |
| POST | /tasks/{id}/close | 关闭任务 | R1 |

## Flow State Machine

```
draft → submitted → under_review → approved → closed
                                 → rejected → submitted (resubmit)
```

## Request/Response Examples

### Create Task

```json
POST /tasks
{
  "title": "GPS设备采购",
  "budget": 300000,
  "description": "采购50台车载GPS设备"
}

Response:
{
  "id": "task-001",
  "title": "GPS设备采购",
  "status": "draft",
  "created_by": "alice:Alice@local",
  "created_at": "2026-03-18T10:00:00Z"
}
```

### Review Task

```json
POST /tasks/task-001/review
{
  "decision": "reject",
  "reason": "缺安装售后条款"
}

Response:
{
  "id": "task-001",
  "status": "rejected",
  "review": {
    "decision": "reject",
    "reason": "缺安装售后条款",
    "reviewer": "bob:Bob@local",
    "reviewed_at": "2026-03-18T12:00:00Z"
  }
}
```
```

**Step 8: Commit**

```bash
git add agent/skills/taskarena/
git commit -m "feat: agent/skills/taskarena — TaskArena skill with CRUD scripts + four-primitive config"
```

---

## Task 6: agent/skills/agentforge/ — AgentForge skill (mock)

**Files:**
- Create: `agent/skills/agentforge/SKILL.md`
- Create: `agent/skills/agentforge/config.yaml`
- Create: `agent/skills/agentforge/scripts/spawn_agent.py`
- Create: `agent/skills/agentforge/scripts/wake_agent.py`
- Create: `agent/skills/agentforge/scripts/list_agents.py`
- Create: `agent/skills/agentforge/scripts/download_template.py`
- Create: `agent/skills/agentforge/scripts/generate_from_roles.py`
- Create: `agent/skills/agentforge/references/agentforge-api.md`

**Step 1: Create SKILL.md**

```markdown
---
name: agentforge
description: "AgentForge Socialware App — Agent 生命周期管理、模板、staffing、多平台适配"
---

# AgentForge

Agent 管理 Socialware App。管理 agent 的 spawn/sleep/wake/destroy 生命周期，
支持模板系统、parent-child 层级、和多平台适配 (Claude, Codex, KimiCode)。

## Commands

| 命令 | 说明 | 需要角色 |
|------|------|----------|
| /agentforge spawn | 从模板创建 agent | R2 (操作者) |
| /agentforge wake | 唤醒 sleeping agent | R2 (操作者) |
| /agentforge sleep | 休眠 agent | R2 (操作者) |
| /agentforge destroy | 销毁 agent | R2 (操作者) |
| /agentforge list | 查看 agent 列表 | 所有角色 |
| /agentforge config | 配置 agent | R1 (管理员) |
| /agentforge download | 下载 agent 模板 | R1 (管理员) |
| /agentforge generate | 从角色配置生成 agent | R1 (管理员) |

## 四原语

### Role (角色)

- R1 管理员 (af:admin): register-template, config, spawn, destroy, query, audit
- R2 操作者 (af:operator): spawn, destroy, sleep, wake, list, query
- R3 观察者: query, list

### Flow (状态机)

```
created → [spawn] → active ⇄ [sleep/wake] → sleeping
                        → [destroy] → destroyed
```

### Commitment (承诺)

- C1: Agent 响应 @mention 后 5min 内开始处理 (SLA)

### Arena (作用域)

- 基于 Room 成员身份
- parent-child: 子 agent 权限 ≤ 父 agent

## Usage

```bash
# 从模板创建 agent
uv run agent/skills/agentforge/scripts/spawn_agent.py --template code-reviewer --name reviewer-1

# 唤醒 agent
uv run agent/skills/agentforge/scripts/wake_agent.py --name reviewer-1

# 列出所有 agent
uv run agent/skills/agentforge/scripts/list_agents.py

# 下载 agent 模板
uv run agent/skills/agentforge/scripts/download_template.py --source "github:ezagent42/templates/code-reviewer"

# 从角色配置生成 agent
uv run agent/skills/agentforge/scripts/generate_from_roles.py --config ../taskarena/config.yaml
```
```

**Step 2: Create config.yaml**

```yaml
domain: agentforge
api_url: http://localhost:8002
language: zh

roles:
  R1:
    name: admin
    label: "管理员"
    permissions: [register-template, config, spawn, destroy, query, audit]
  R2:
    name: operator
    label: "操作者"
    permissions: [spawn, destroy, sleep, wake, list, query]
  R3:
    name: observer
    label: "观察者"
    permissions: [query, list]

flow:
  name: agent_lifecycle
  states: [created, active, sleeping, destroyed]
  transitions:
    - from: created
      to: active
      action: spawn
      role: R2
    - from: active
      to: sleeping
      action: sleep
      role: R2
    - from: sleeping
      to: active
      action: wake
      role: R2
    - from: active
      to: destroyed
      action: destroy
      role: R2
    - from: sleeping
      to: destroyed
      action: destroy
      role: R2

commitments:
  C1:
    description: "Agent 响应 @mention 后 5min 内开始处理"
    trigger_state: active
    deadline_minutes: 5

arena:
  scope: room

templates_dir: "../agents/"

adapters:
  claude:
    sdk: claude-agent-sdk
    launcher: "../adapters/claude/launcher.py"
  codex:
    sdk: openai-agents
    launcher: "../adapters/codex/launcher.py"
  kimicode:
    sdk: kimicode-sdk
    launcher: "../adapters/kimicode/launcher.py"
```

**Step 3: Create scripts/spawn_agent.py**

```python
#!/usr/bin/env python3
"""Spawn an agent from template.

Usage:
  uv run spawn_agent.py --template code-reviewer --name reviewer-1
  uv run spawn_agent.py --template code-reviewer --name reviewer-1 --adapter codex
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Spawn agent from template")
    parser.add_argument("--template", required=True, help="Template name")
    parser.add_argument("--name", required=True, help="Agent instance name")
    parser.add_argument("--adapter", default="claude", choices=["claude", "codex", "kimicode"])
    parser.add_argument("--parent", help="Parent agent name")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {
        "template": args.template,
        "name": args.name,
        "adapter": args.adapter,
    }
    if args.parent:
        data["parent"] = args.parent

    result = client.request("POST", "/agents/spawn", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 4: Create scripts/wake_agent.py**

```python
#!/usr/bin/env python3
"""Wake a sleeping agent.

Usage:
  uv run wake_agent.py --name reviewer-1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Wake sleeping agent")
    parser.add_argument("--name", required=True, help="Agent name")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    result = client.request("POST", f"/agents/{args.name}/wake")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 5: Create scripts/list_agents.py**

```python
#!/usr/bin/env python3
"""List all agents.

Usage:
  uv run list_agents.py
  uv run list_agents.py --status active
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="List AgentForge agents")
    parser.add_argument("--status", help="Filter by status")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    path = "/agents"
    if args.status:
        path += f"?status={args.status}"

    result = client.request("GET", path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 6: Create scripts/download_template.py**

```python
#!/usr/bin/env python3
"""Download agent template from registry.

Usage:
  uv run download_template.py --source "github:ezagent42/templates/code-reviewer"
  uv run download_template.py --source "local:templates/task-worker"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config

SKILL_DIR = Path(__file__).parent.parent
AGENTS_DIR = SKILL_DIR.parent.parent / "agents"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download agent template")
    parser.add_argument("--source", required=True, help="Template source (github:org/repo/name or local:path)")
    parser.add_argument("--target", help="Target directory name (default: template name)")
    args = parser.parse_args()

    # Parse source
    if args.source.startswith("github:"):
        parts = args.source[7:].split("/")
        template_name = parts[-1] if not args.target else args.target
        print(f"TODO: Download from GitHub — {args.source}")
        print(f"Target: {AGENTS_DIR / template_name}")
    elif args.source.startswith("local:"):
        local_path = Path(args.source[6:])
        template_name = local_path.name if not args.target else args.target
        print(f"TODO: Copy from local — {local_path}")
        print(f"Target: {AGENTS_DIR / template_name}")
    else:
        print(f"Unknown source format: {args.source}", file=sys.stderr)
        sys.exit(1)

    result = {
        "action": "download_template",
        "source": args.source,
        "target": str(AGENTS_DIR / template_name),
        "status": "mock — not implemented yet",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 7: Create scripts/generate_from_roles.py**

```python
#!/usr/bin/env python3
"""Generate agent definitions from SW App role config.

Reads a SW App's config.yaml, extracts roles, generates GitAgent agent
definitions in agent/agents/ directory.

Usage:
  uv run generate_from_roles.py --config ../taskarena/config.yaml
  uv run generate_from_roles.py --config ../taskarena/config.yaml --adapter codex
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config

AGENTS_DIR = Path(__file__).parent.parent.parent.parent / "agents"


def generate_agent(
    domain: str,
    role_id: str,
    role_config: dict,
    adapter: str,
) -> dict:
    """Generate a GitAgent agent definition from a role config."""
    agent_name = f"{domain}-{role_config['name']}"
    agent_dir = AGENTS_DIR / agent_name

    agent_yaml = {
        "name": agent_name,
        "version": "0.1.0",
        "description": f"Auto-generated agent for {domain} role {role_id} ({role_config['label']})",
        "model": {"preferred": "claude-sonnet-4-6"},
        "tags": [domain, role_id, "auto-generated"],
    }

    soul_md = f"""# {role_config['label']} Agent

你是 {domain} 的 {role_config['label']}。

## 角色

- 角色 ID: {role_id}
- 权限: {', '.join(role_config.get('permissions', []))}

## 职责

根据 {domain} 的流程规则，执行 {role_id} 角色允许的操作。
"""

    return {
        "name": agent_name,
        "dir": str(agent_dir),
        "agent_yaml": agent_yaml,
        "soul_md": soul_md,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate agents from role config")
    parser.add_argument("--config", required=True, help="Path to SW App config.yaml")
    parser.add_argument("--adapter", default="claude", choices=["claude", "codex", "kimicode"])
    parser.add_argument("--dry-run", action="store_true", help="Print without creating files")
    args = parser.parse_args()

    config_path = Path(args.config)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    domain = config.get("domain", config_path.parent.name)
    roles = config.get("roles", {})

    generated = []
    for role_id, role_config in roles.items():
        agent = generate_agent(domain, role_id, role_config, args.adapter)
        generated.append(agent)

        if not args.dry_run:
            agent_dir = Path(agent["dir"])
            agent_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_dir / "agent.yaml", "w") as f:
                yaml.dump(agent["agent_yaml"], f, allow_unicode=True, default_flow_style=False)
            with open(agent_dir / "SOUL.md", "w") as f:
                f.write(agent["soul_md"])

    print(json.dumps(generated, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

**Step 8: Create references/agentforge-api.md**

```markdown
# AgentForge API Reference

## Endpoints

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | /agents/spawn | 从模板创建 agent | R2 |
| GET | /agents | 列出所有 agent | any |
| GET | /agents/{name} | 查询单个 agent | any |
| POST | /agents/{name}/wake | 唤醒 sleeping agent | R2 |
| POST | /agents/{name}/sleep | 休眠 agent | R2 |
| POST | /agents/{name}/destroy | 销毁 agent | R2 |
| PUT | /agents/{name}/config | 配置 agent | R1 |
| GET | /templates | 列出可用模板 | any |

## Flow State Machine

```
created → active ⇄ sleeping → destroyed
```

## Request/Response Examples

### Spawn Agent

```json
POST /agents/spawn
{
  "template": "code-reviewer",
  "name": "reviewer-1",
  "adapter": "claude"
}

Response:
{
  "name": "reviewer-1",
  "template": "code-reviewer",
  "status": "created",
  "adapter": "claude",
  "owner": "alice:Alice@local",
  "parent": null,
  "created_at": "2026-03-18T10:00:00Z"
}
```
```

**Step 9: Commit**

```bash
git add agent/skills/agentforge/
git commit -m "feat: agent/skills/agentforge — AgentForge skill with lifecycle scripts + multi-adapter config"
```

---

## Task 7: agent/skills/dev/ — dev-specific skill

**Files:**
- Create: `agent/skills/dev/SKILL.md`
- Create: `agent/skills/dev/references/four-primitives.md`

**Step 1: Create SKILL.md**

```markdown
---
name: dev
description: "Socialwares 开发者技能 — 项目开发工作流、四原语参考、自举指南"
---

# Socialwares Dev Skill

Socialwares 项目开发专用技能。

## 开发工作流

1. **创建 App**: 在 `apps/{name}/` 下创建新 SW App
2. **定义四原语**: 在 `agent/skills/{name}/config.yaml` 中定义 Role/Flow/Commitment/Arena
3. **写 SKILL.md**: 在 `agent/skills/{name}/SKILL.md` 中写技能文档
4. **写 scripts/**: 在 `agent/skills/{name}/scripts/` 中写 API 调用脚本
5. **测试**: `uv run pytest tests/`
6. **自举**: 用已开发的 skills 管理后续开发

## 自举循环

```
Iteration 0: 基础 Claude Code 配置
Iteration 1: TaskArena → 用 /taskarena 管理开发任务
Iteration 2: AgentForge → 用 /agentforge 管理开发 agent
Iteration 3: adapters → 用 launch.sh 启动 headless agent
```

## 新建 SW App Checklist

- [ ] `apps/{name}/pyproject.toml`
- [ ] `apps/{name}/src/{name}/__init__.py`
- [ ] `agent/skills/{name}/SKILL.md`
- [ ] `agent/skills/{name}/config.yaml` (四原语定义)
- [ ] `agent/skills/{name}/scripts/` (CRUD 脚本)
- [ ] `agent/tools/{name}-api.yaml` (MCP 工具定义)
- [ ] `tests/test_{name}.py`
```

**Step 2: Create references/four-primitives.md**

```markdown
# 四原语参考

## Role (角色)

角色定义参与者的权限。每个 SW App 定义自己的角色。

```yaml
roles:
  R1:
    name: admin
    permissions: [create, read, update, delete, close]
  R2:
    name: operator
    permissions: [create, read, update]
  R3:
    name: observer
    permissions: [read]
```

pre_send hook 根据角色检查权限：发送者没有权限 → 消息被拒绝。

## Flow (状态机)

状态机定义实体的生命周期。

```yaml
flow:
  name: entity_lifecycle
  states: [draft, active, closed]
  transitions:
    - from: draft
      to: active
      action: activate
      role: R1
```

每个 transition 指定: from 状态、to 状态、触发 action、需要的 role。

## Commitment (承诺)

SLA 定义和超时追踪。

```yaml
commitments:
  C1:
    description: "审核者在提交后 72h 内完成审核"
    trigger_state: submitted
    deadline_hours: 72
    escalation_role: R1
```

L1 层: 记录违约但不自动追踪。
App 层: Verifier Node 自动追踪超时并升级。

## Arena (作用域)

定义谁能参与、谁能看到。

```yaml
arena:
  min_members: 2
  scope: room        # room | global | custom
  open: false        # 是否允许非成员加入
```
```

**Step 3: Commit**

```bash
git add agent/skills/dev/
git commit -m "feat: agent/skills/dev — developer skill with four-primitives reference"
```

---

## Task 8: agent/tools/ + agent/knowledge/ + agent/agents/ + agent/hooks/ + agent/memory/

**Files:**
- Create: `agent/tools/taskarena-api.yaml`
- Create: `agent/tools/agentforge-api.yaml`
- Create: `agent/knowledge/index.yaml`
- Create: `agent/knowledge/socialware-concepts.md`
- Create: `agent/agents/README.md`
- Create: `agent/agents/.gitkeep`
- Create: `agent/hooks/hooks.yaml`
- Create: `agent/memory/MEMORY.md`
- Create: `agent/memory/memory.yaml`

**Step 1: Create agent/tools/taskarena-api.yaml**

```yaml
name: taskarena-api
description: "TaskArena API — 任务 CRUD、状态机转换、审核"
version: "0.1.0"

input_schema:
  type: object
  properties:
    action:
      type: string
      enum: [create, read, update, review, close, list]
      description: "API action"
    task_id:
      type: string
      description: "Task ID (for read/update/review/close)"
    data:
      type: object
      description: "Request body"
  required: [action]

implementation:
  type: script
  path: "../skills/taskarena/scripts/"
  runtime: python3
  timeout: 30

annotations:
  requires_confirmation: false
  read_only: false
  cost: low
```

**Step 2: Create agent/tools/agentforge-api.yaml**

```yaml
name: agentforge-api
description: "AgentForge API — Agent 生命周期管理、模板、配置"
version: "0.1.0"

input_schema:
  type: object
  properties:
    action:
      type: string
      enum: [spawn, wake, sleep, destroy, list, config, download, generate]
      description: "API action"
    agent_name:
      type: string
      description: "Agent name"
    data:
      type: object
      description: "Request body"
  required: [action]

implementation:
  type: script
  path: "../skills/agentforge/scripts/"
  runtime: python3
  timeout: 30

annotations:
  requires_confirmation: true
  read_only: false
  cost: medium
```

**Step 3: Create agent/knowledge/index.yaml**

```yaml
documents:
  - path: socialware-concepts.md
    tags: [socialware, concepts, overview]
    priority: high
    always_load: true
    summary: "Socialware 核心概念和四原语"
  - path: ../skills/dev/references/four-primitives.md
    tags: [primitives, role, flow, commitment, arena]
    priority: high
    always_load: false
    summary: "四原语 (Role/Flow/Commitment/Arena) 详细参考"
```

**Step 4: Create agent/knowledge/socialware-concepts.md**

```markdown
# Socialware 核心概念

## Socialware App

Socialware App 是面向 agent 的协作应用。每个 App 是独立软件，
通过 HTTP API 暴露功能，agent 通过四原语进行调用。

## 四原语

- **Role**: 谁能做什么 (权限)
- **Flow**: 事情怎么推进 (状态机)
- **Commitment**: 什么时候必须做完 (SLA)
- **Arena**: 谁能看到 (作用域)

## 三层架构

- **L0 感知层**: Side Panel 提示，#CRUD 标注
- **L1 组织层**: /action 命令，pre_send 权限检查，Flow 状态机
- **App 工具层**: /action:func 命令，工具实际执行

## 当前 Apps

- **TaskArena**: 任务 CRUD + 审核流程
- **AgentForge**: Agent 生命周期管理 + 多平台适配
```

**Step 5: Create agent/agents/README.md**

```markdown
# Agent 子定义目录

此目录存放从 AgentForge 下载或自动生成的子 agent 定义。

## 添加方式

1. **从模板下载**:
   ```bash
   uv run agent/skills/agentforge/scripts/download_template.py --source "github:org/templates/name"
   ```

2. **从角色配置生成**:
   ```bash
   uv run agent/skills/agentforge/scripts/generate_from_roles.py --config agent/skills/taskarena/config.yaml
   ```

3. **手动创建** (遵循 GitAgent 格式):
   ```
   agent-name/
   ├── agent.yaml
   └── SOUL.md
   ```

## 注意

- `_generated/` 子目录下的文件会被 .gitignore 忽略
- 手动创建的模板会被 git 追踪
```

**Step 6: Create remaining files**

`agent/agents/.gitkeep` — empty file.

`agent/hooks/hooks.yaml`:

```yaml
hooks:
  on_session_start:
    - script: ../../hooks/session-start.sh
      description: "Health check for Socialwares environment"
      timeout: 10
  pre_tool_use:
    - script: ../../hooks/enforce-tools.sh
      description: "Block pip/npm, suggest uv/pnpm"
      timeout: 5
```

`agent/memory/MEMORY.md`:

```markdown
# Working Memory

## Current State
- Project: Socialwares MonoRepo initial setup
- Phase: Iteration 0 (基础配置)

## Key Decisions
- GitAgent format for agent/ directory
- AutoService pattern for skills/ (SKILL.md + config.yaml + scripts/)
- Four primitives (Role/Flow/Commitment/Arena) as universal API pattern
```

`agent/memory/memory.yaml`:

```yaml
layers:
  - name: working
    path: MEMORY.md
    max_lines: 200
    format: markdown

update_triggers:
  - on_session_end
  - on_explicit_save

archive_policy:
  max_entries: 50
  retention: "90d"
```

**Step 7: Commit**

```bash
git add agent/tools/ agent/knowledge/ agent/agents/ agent/hooks/ agent/memory/
git commit -m "feat: agent/ remaining dirs — tools, knowledge, agents, hooks, memory"
```

---

## Task 9: agent/adapters/ — SDK launcher templates

**Files:**
- Create: `agent/adapters/base.py`
- Create: `agent/adapters/claude/launcher.py`
- Create: `agent/adapters/claude/multi_launcher.py`
- Create: `agent/adapters/claude/requirements.txt`
- Create: `agent/adapters/codex/launcher.py`
- Create: `agent/adapters/codex/requirements.txt`
- Create: `agent/adapters/kimicode/launcher.py`
- Create: `agent/adapters/kimicode/requirements.txt`

**Step 1: Create base.py**

```python
"""Base adapter interface for multi-platform agent launching.

Each adapter reads a GitAgent directory (agent.yaml + SOUL.md + skills/)
and launches the agent using the platform's SDK.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Parsed agent configuration from GitAgent format."""

    name: str
    version: str
    description: str
    model_preferred: str
    model_fallback: list[str] = field(default_factory=list)
    soul: str = ""
    rules: str = ""
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    max_turns: int = 100
    timeout: int = 3600

    @classmethod
    def from_dir(cls, agent_dir: str | Path) -> AgentConfig:
        """Load agent config from a GitAgent directory."""
        agent_dir = Path(agent_dir)
        with open(agent_dir / "agent.yaml") as f:
            raw = yaml.safe_load(f)

        soul = ""
        soul_path = agent_dir / "SOUL.md"
        if soul_path.exists():
            soul = soul_path.read_text()

        rules = ""
        rules_path = agent_dir / "RULES.md"
        if rules_path.exists():
            rules = rules_path.read_text()

        model = raw.get("model", {})
        runtime = raw.get("runtime", {})

        return cls(
            name=raw["name"],
            version=raw["version"],
            description=raw["description"],
            model_preferred=model.get("preferred", "claude-sonnet-4-6"),
            model_fallback=model.get("fallback", []),
            soul=soul,
            rules=rules,
            skills=raw.get("skills", []),
            tools=raw.get("tools", []),
            max_turns=runtime.get("max_turns", 100),
            timeout=runtime.get("timeout", 3600),
        )


class BaseAdapter(abc.ABC):
    """Abstract base class for agent SDK adapters."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def build_system_prompt(self) -> str:
        """Build the system prompt from SOUL + RULES + SKILLs."""
        ...

    @abc.abstractmethod
    def launch(self) -> None:
        """Launch the agent using the platform SDK."""
        ...

    @abc.abstractmethod
    def launch_headless(self, task: str) -> Any:
        """Launch the agent headlessly with a specific task."""
        ...
```

**Step 2: Create claude/launcher.py**

```python
#!/usr/bin/env python3
"""Claude Agent SDK launcher.

Reads GitAgent directory and launches via Claude Agent SDK.

Usage:
  uv run launcher.py                              # launch main agent
  uv run launcher.py --agent-dir ../../agents/code-reviewer  # launch sub-agent
  uv run launcher.py --task "Review PR #42"        # headless mode
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")

        # Load SKILL.md from each skill directory
        agent_dir = Path(__file__).parent.parent.parent
        skills_dir = agent_dir / "skills"
        for skill_name in self.config.skills:
            skill_md = skills_dir / skill_name / "SKILL.md"
            if skill_md.exists():
                parts.append(f"\n---\n{skill_md.read_text()}")

        return "\n".join(parts)

    def launch(self) -> None:
        system_prompt = self.build_system_prompt()
        print(f"[Claude Adapter] Launching agent: {self.config.name}")
        print(f"[Claude Adapter] Model: {self.config.model_preferred}")
        print(f"[Claude Adapter] System prompt length: {len(system_prompt)} chars")
        print(f"[Claude Adapter] Max turns: {self.config.max_turns}")
        print()

        # TODO: Replace with actual Claude Agent SDK call
        # from claude_agent_sdk import Agent
        # agent = Agent(
        #     model=self.config.model_preferred,
        #     system_prompt=system_prompt,
        #     max_turns=self.config.max_turns,
        # )
        # agent.run()

        print("[Claude Adapter] Mock mode — SDK not installed yet")
        print(f"[Claude Adapter] Would launch with prompt:\n{system_prompt[:500]}...")

    def launch_headless(self, task: str) -> str:
        system_prompt = self.build_system_prompt()
        print(f"[Claude Adapter] Headless task: {task}")

        # TODO: Replace with actual Claude Agent SDK call
        # from claude_agent_sdk import Agent
        # agent = Agent(
        #     model=self.config.model_preferred,
        #     system_prompt=system_prompt,
        #     max_turns=self.config.max_turns,
        # )
        # return agent.run_headless(task)

        return f"[Mock] Would execute: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via Claude SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent),
                        help="GitAgent directory")
    parser.add_argument("--task", help="Headless task (omit for interactive)")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = ClaudeAdapter(config)

    if args.task:
        result = adapter.launch_headless(args.task)
        print(result)
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
```

**Step 3: Create claude/multi_launcher.py**

```python
#!/usr/bin/env python3
"""Multi-agent scenario launcher for Claude SDK.

Reads a scenario YAML and launches multiple agents.

Usage:
  uv run multi_launcher.py ../../scenarios/examples/task-review.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch multi-agent scenario")
    parser.add_argument("scenario", help="Path to scenario YAML")
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = yaml.safe_load(f)

    print(f"[Multi-Launcher] Scenario: {scenario['name']}")
    print(f"[Multi-Launcher] Description: {scenario.get('description', '')}")
    print()

    for agent_cfg in scenario.get("agents", []):
        template_dir = Path(args.scenario).parent.parent.parent / agent_cfg["template"]
        print(f"[Multi-Launcher] Agent: {agent_cfg['name']}")
        print(f"  Template: {agent_cfg['template']}")
        print(f"  Adapter: {agent_cfg.get('adapter', 'claude')}")
        print(f"  Roles: {agent_cfg.get('roles', [])}")
        print(f"  Template exists: {template_dir.exists()}")
        print()

    # TODO: Actually launch agents with asyncio
    print("[Multi-Launcher] Mock mode — would launch all agents concurrently via bus")


if __name__ == "__main__":
    main()
```

**Step 4: Create claude/requirements.txt**

```
claude-agent-sdk>=0.1.0
pyyaml>=6.0
```

**Step 5: Create codex/launcher.py**

```python
#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK launcher.

Reads GitAgent directory and launches via OpenAI Agents SDK.

Usage:
  uv run launcher.py --agent-dir ../../
  uv run launcher.py --agent-dir ../../agents/code-reviewer --task "Review PR #42"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class CodexAdapter(BaseAdapter):
    """OpenAI Agents SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")
        return "\n".join(parts)

    def launch(self) -> None:
        print(f"[Codex Adapter] Launching agent: {self.config.name}")
        print(f"[Codex Adapter] Model: gpt-4o (mapped from {self.config.model_preferred})")
        print("[Codex Adapter] Mock mode — SDK not installed yet")

    def launch_headless(self, task: str) -> str:
        print(f"[Codex Adapter] Headless task: {task}")
        return f"[Mock] Would execute via OpenAI Agents SDK: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via Codex SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent))
    parser.add_argument("--task", help="Headless task")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = CodexAdapter(config)

    if args.task:
        print(adapter.launch_headless(args.task))
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
```

**Step 6: Create codex/requirements.txt**

```
openai-agents>=0.1.0
pyyaml>=6.0
```

**Step 7: Create kimicode/launcher.py**

```python
#!/usr/bin/env python3
"""KimiCode SDK launcher.

Reads GitAgent directory and launches via KimiCode SDK.

Usage:
  uv run launcher.py --agent-dir ../../
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class KimiCodeAdapter(BaseAdapter):
    """KimiCode SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")
        return "\n".join(parts)

    def launch(self) -> None:
        print(f"[KimiCode Adapter] Launching agent: {self.config.name}")
        print("[KimiCode Adapter] Mock mode — SDK not installed yet")

    def launch_headless(self, task: str) -> str:
        return f"[Mock] Would execute via KimiCode SDK: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via KimiCode SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent))
    parser.add_argument("--task", help="Headless task")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = KimiCodeAdapter(config)

    if args.task:
        print(adapter.launch_headless(args.task))
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
```

**Step 8: Create kimicode/requirements.txt**

```
pyyaml>=6.0
# kimicode-sdk — add when available
```

**Step 9: Commit**

```bash
git add agent/adapters/
git commit -m "feat: agent/adapters — Claude, Codex, KimiCode SDK launcher templates"
```

---

## Task 10: apps/ stubs — TaskArena + AgentForge

**Files:**
- Create: `apps/taskarena/pyproject.toml`
- Create: `apps/taskarena/src/taskarena/__init__.py`
- Create: `apps/taskarena/src/taskarena/app.py`
- Create: `apps/taskarena/README.md`
- Create: `apps/agentforge/pyproject.toml`
- Create: `apps/agentforge/src/agentforge/__init__.py`
- Create: `apps/agentforge/src/agentforge/app.py`
- Create: `apps/agentforge/README.md`

**Step 1: Create apps/taskarena/pyproject.toml**

```toml
[project]
name = "taskarena"
version = "0.1.0"
description = "TaskArena Socialware App — 任务 CRUD + 状态机 + 角色权限 + SLA"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "pyyaml>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create apps/taskarena/src/taskarena/__init__.py**

```python
"""TaskArena — 任务管理 Socialware App."""
__version__ = "0.1.0"
```

**Step 3: Create apps/taskarena/src/taskarena/app.py**

```python
"""TaskArena FastAPI application.

Mock implementation — returns stub data for all endpoints.
Four primitives (Role/Flow/Commitment/Arena) are defined in config
and enforced by pre_send middleware.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Header

app = FastAPI(title="TaskArena", version="0.1.0")

# In-memory mock store
_tasks: dict[str, dict[str, Any]] = {}
_counter = 0

# Flow state machine
VALID_TRANSITIONS = {
    ("draft", "propose"): "submitted",
    ("submitted", "review"): "under_review",
    ("under_review", "approve"): "approved",
    ("under_review", "reject"): "rejected",
    ("rejected", "resubmit"): "submitted",
    ("approved", "close"): "closed",
}


@app.post("/tasks")
def create_task(
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    global _counter
    _counter += 1
    task_id = f"task-{_counter:03d}"
    task = {
        "id": task_id,
        "title": data.get("title", "Untitled"),
        "description": data.get("description", ""),
        "budget": data.get("budget"),
        "status": "draft",
        "created_by": x_identity,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _tasks[task_id] = task
    return task


@app.get("/tasks")
def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    return _tasks[task_id]


@app.put("/tasks/{task_id}")
def update_task(task_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    _tasks[task_id].update(data)
    return _tasks[task_id]


@app.post("/tasks/{task_id}/review")
def review_task(
    task_id: str,
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")

    task = _tasks[task_id]
    decision = data.get("decision")

    if decision == "approve":
        action = "approve"
    elif decision == "reject":
        action = "reject"
    else:
        raise HTTPException(400, f"Invalid decision: {decision}")

    key = (task["status"], action)
    if key not in VALID_TRANSITIONS:
        raise HTTPException(
            409,
            f"Cannot {action} task in status {task['status']}",
        )

    task["status"] = VALID_TRANSITIONS[key]
    task["review"] = {
        "decision": decision,
        "reason": data.get("reason", ""),
        "reviewer": x_identity,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return task


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Step 4: Create apps/taskarena/README.md**

```markdown
# TaskArena

任务管理 Socialware App。

## 运行

```bash
uv run --package taskarena uvicorn taskarena.app:app --port 8001
```

## API

See `agent/skills/taskarena/references/taskarena-api.md`
```

**Step 5: Create apps/agentforge/ (same pattern)**

`apps/agentforge/pyproject.toml`:
```toml
[project]
name = "agentforge"
version = "0.1.0"
description = "AgentForge Socialware App — Agent 生命周期管理 + 多平台适配"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "pyyaml>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

`apps/agentforge/src/agentforge/__init__.py`:
```python
"""AgentForge — Agent 管理 Socialware App."""
__version__ = "0.1.0"
```

`apps/agentforge/src/agentforge/app.py`:
```python
"""AgentForge FastAPI application.

Mock implementation — agent lifecycle management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Header

app = FastAPI(title="AgentForge", version="0.1.0")

_agents: dict[str, dict[str, Any]] = {}

VALID_TRANSITIONS = {
    ("created", "spawn"): "active",
    ("active", "sleep"): "sleeping",
    ("sleeping", "wake"): "active",
    ("active", "destroy"): "destroyed",
    ("sleeping", "destroy"): "destroyed",
}


@app.post("/agents/spawn")
def spawn_agent(
    data: dict[str, Any],
    x_identity: str = Header(default="anonymous"),
) -> dict[str, Any]:
    name = data.get("name", f"agent-{len(_agents)+1}")
    agent = {
        "name": name,
        "template": data.get("template", "default"),
        "status": "created",
        "adapter": data.get("adapter", "claude"),
        "owner": x_identity,
        "parent": data.get("parent"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _agents[name] = agent
    # Auto-transition to active
    agent["status"] = "active"
    return agent


@app.get("/agents")
def list_agents(status: str | None = None) -> list[dict[str, Any]]:
    agents = list(_agents.values())
    if status:
        agents = [a for a in agents if a["status"] == status]
    return agents


@app.get("/agents/{name}")
def get_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    return _agents[name]


@app.post("/agents/{name}/wake")
def wake_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "wake")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot wake agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


@app.post("/agents/{name}/sleep")
def sleep_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "sleep")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot sleep agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


@app.post("/agents/{name}/destroy")
def destroy_agent(name: str) -> dict[str, Any]:
    if name not in _agents:
        raise HTTPException(404, f"Agent {name} not found")
    agent = _agents[name]
    key = (agent["status"], "destroy")
    if key not in VALID_TRANSITIONS:
        raise HTTPException(409, f"Cannot destroy agent in status {agent['status']}")
    agent["status"] = VALID_TRANSITIONS[key]
    return agent


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

`apps/agentforge/README.md`:
```markdown
# AgentForge

Agent 管理 Socialware App。

## 运行

```bash
uv run --package agentforge uvicorn agentforge.app:app --port 8002
```

## API

See `agent/skills/agentforge/references/agentforge-api.md`
```

**Step 6: Commit**

```bash
git add apps/
git commit -m "feat: apps/ stubs — TaskArena + AgentForge mock FastAPI servers"
```

---

## Task 11: scripts/ — setup + launch scripts

**Files:**
- Create: `scripts/setup-claude.sh`
- Create: `scripts/setup-codex.sh`
- Create: `scripts/setup-kimicode.sh`
- Create: `scripts/launch.sh`
- Create: `scripts/launch-scenario.sh`

**Step 1: Create scripts/setup-claude.sh**

```bash
#!/usr/bin/env bash
# setup-claude.sh — Configure Claude Code dev environment
# Creates per-skill symlinks: .claude/skills/{name} → ../../agent/skills/{name}
# Follows AutoService pattern: individual symlinks, not whole-directory symlink.
# This allows mixing symlinked agent skills with native Claude Code skills.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$REPO_ROOT/.claude"
AGENT_SKILLS_DIR="$REPO_ROOT/agent/skills"

echo "Setting up Claude Code for Socialwares..."
echo "Repo: $REPO_ROOT"
echo ""

# 1. Ensure .claude/skills/ exists as a real directory (not a symlink)
if [ -L "$CLAUDE_DIR/skills" ]; then
    echo "⚠ .claude/skills is a symlink (old pattern). Replacing with directory..."
    rm "$CLAUDE_DIR/skills"
fi
mkdir -p "$CLAUDE_DIR/skills"

# 2. Create per-skill symlinks (AutoService pattern)
#    Each skill in agent/skills/ gets its own symlink in .claude/skills/
LINKED=0
for skill_dir in "$AGENT_SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    target="../../agent/skills/$skill_name"
    link="$CLAUDE_DIR/skills/$skill_name"

    if [ -L "$link" ]; then
        # Symlink exists, verify target
        current_target=$(readlink "$link")
        if [ "$current_target" = "$target" ]; then
            echo "· $skill_name (already linked)"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "✓ $skill_name (updated)"
        fi
    elif [ -d "$link" ]; then
        echo "⚠ $skill_name is a real directory, skipping (native skill?)"
    else
        ln -s "$target" "$link"
        echo "✓ $skill_name → $target"
    fi
    ((LINKED++))
done

echo ""
echo "Linked $LINKED skills from agent/skills/ to .claude/skills/"

# 3. Verify agent.yaml exists
if [ ! -f "$REPO_ROOT/agent/agent.yaml" ]; then
    echo "⚠ agent/agent.yaml not found"
else
    echo "✓ agent/agent.yaml found"
fi

# 4. Summary
echo ""
echo "Done. Claude Code is ready for Socialwares development."
echo ""
echo "Next steps:"
echo "  claude                    # start Claude Code"
echo "  ./scripts/launch.sh      # launch agent via SDK"
echo ""
echo "To add native Claude skills (not from agent/):"
echo "  mkdir .claude/skills/my-native-skill/"
echo "  # won't conflict with symlinked agent skills"
```

**Step 2: Create scripts/setup-codex.sh**

```bash
#!/usr/bin/env bash
# setup-codex.sh — Configure OpenAI Codex adapter
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up Codex adapter for Socialwares..."
echo ""

# Check if gitagent CLI is available
if command -v gitagent &> /dev/null; then
    echo "gitagent found, exporting..."
    cd "$REPO_ROOT/agent"
    gitagent export --format openai
    echo "✓ Exported to OpenAI format"
else
    echo "gitagent CLI not found. Using manual adapter."
    echo ""
    echo "To launch with Codex adapter:"
    echo "  uv run agent/adapters/codex/launcher.py"
    echo ""
    echo "To install gitagent:"
    echo "  npm install -g gitagent"
fi
```

**Step 3: Create scripts/setup-kimicode.sh**

```bash
#!/usr/bin/env bash
# setup-kimicode.sh — Configure KimiCode adapter
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up KimiCode adapter for Socialwares..."
echo ""
echo "To launch with KimiCode adapter:"
echo "  uv run agent/adapters/kimicode/launcher.py"
echo ""
echo "KimiCode SDK integration is in development."
```

**Step 4: Create scripts/launch.sh**

```bash
#!/usr/bin/env bash
# launch.sh — Launch a single agent via SDK adapter
#
# Usage:
#   ./scripts/launch.sh                                    # main agent, claude adapter
#   ./scripts/launch.sh --adapter codex                    # main agent, codex adapter
#   ./scripts/launch.sh --agent-dir agent/agents/reviewer  # sub-agent
#   ./scripts/launch.sh --task "Review PR #42"             # headless mode

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Defaults
ADAPTER="claude"
AGENT_DIR="$REPO_ROOT/agent"
TASK=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --adapter)
            ADAPTER="$2"
            shift 2
            ;;
        --agent-dir)
            AGENT_DIR="$2"
            shift 2
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

LAUNCHER="$REPO_ROOT/agent/adapters/$ADAPTER/launcher.py"

if [ ! -f "$LAUNCHER" ]; then
    echo "❌ Adapter not found: $ADAPTER"
    echo "Available adapters: claude, codex, kimicode"
    exit 1
fi

echo "🚀 Launching agent..."
echo "  Adapter: $ADAPTER"
echo "  Agent dir: $AGENT_DIR"
[ -n "$TASK" ] && echo "  Task: $TASK"
echo ""

CMD="uv run $LAUNCHER --agent-dir $AGENT_DIR"
[ -n "$TASK" ] && CMD="$CMD --task \"$TASK\""

eval "$CMD"
```

**Step 5: Create scripts/launch-scenario.sh**

```bash
#!/usr/bin/env bash
# launch-scenario.sh — Launch multi-agent scenario
#
# Usage:
#   ./scripts/launch-scenario.sh scenarios/examples/task-review.yaml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <scenario.yaml>"
    echo ""
    echo "Available scenarios:"
    find "$REPO_ROOT/scenarios" -name "*.yaml" -type f 2>/dev/null | while read -r f; do
        echo "  $f"
    done
    exit 1
fi

SCENARIO="$1"

if [ ! -f "$SCENARIO" ]; then
    echo "❌ Scenario not found: $SCENARIO"
    exit 1
fi

echo "🚀 Launching multi-agent scenario..."
echo "  File: $SCENARIO"
echo ""

uv run "$REPO_ROOT/agent/adapters/claude/multi_launcher.py" "$SCENARIO"
```

**Step 6: Make all scripts executable and commit**

```bash
chmod +x scripts/*.sh
git add scripts/
git commit -m "feat: scripts/ — setup (claude/codex/kimicode) + launch (single/scenario)"
```

---

## Task 12: scenarios/ — example scenario

**Files:**
- Create: `scenarios/README.md`
- Create: `scenarios/examples/task-review.yaml`

**Step 1: Create scenarios/README.md**

```markdown
# 多 Agent 场景编排

YAML 格式定义多 agent 协作场景。

## 用法

```bash
./scripts/launch-scenario.sh scenarios/examples/task-review.yaml
```

## 格式

```yaml
name: scenario-name
description: "场景描述"

bus:
  type: local
  endpoint: localhost:8080

agents:
  - name: agent-name
    template: agent/agents/template-dir
    adapter: claude|codex|kimicode
    roles: [taskarena:R1]
    auto_start: true

workflow:
  - agent-name: "/command arg1 arg2"
```
```

**Step 2: Create scenarios/examples/task-review.yaml**

```yaml
name: task-review-flow
description: "3 agent 自动执行 提交→审核 流程 (mock)"

bus:
  type: local
  endpoint: localhost:8080

agents:
  - name: manager
    template: agent/agents/taskarena-admin
    adapter: claude
    roles: [taskarena:R1]
    auto_start: true

  - name: submitter
    template: agent/agents/taskarena-submitter
    adapter: claude
    roles: [taskarena:R2]
    auto_start: true

  - name: reviewer
    template: agent/agents/taskarena-reviewer
    adapter: claude
    roles: [taskarena:R3]
    auto_start: false
    trigger: "@mention"

workflow:
  - submitter: "/taskarena create --title 'GPS设备采购' --budget 300000"
  - manager: "/taskarena update --id task-001 --assignee reviewer"
  - reviewer: "/taskarena review --id task-001 --decision approve"
  - manager: "/taskarena close --id task-001"
```

**Step 3: Commit**

```bash
git add scenarios/
git commit -m "feat: scenarios/ — multi-agent scenario format with task-review example"
```

---

## Task 13: docs/dev-guide.md — developer guide

**Files:**
- Create: `docs/dev-guide.md`

**Step 1: Create docs/dev-guide.md**

````markdown
# Socialwares 开发指南

## 概览

Socialwares 是面向 agent 的协作应用 MonoRepo。每个 App 通过四原语
(Role/Flow/Commitment/Arena) 暴露 API，agent 通过 skills 和 adapters 调用。

## 项目结构

```
Socialwares/
├── apps/                   ← SW App 本体 (Python FastAPI server)
│   ├── taskarena/          ← 任务管理
│   └── agentforge/         ← Agent 管理
├── agent/                  ← GitAgent 格式 agent 定义
│   ├── agent.yaml          ← 身份和模型配置
│   ├── SOUL.md             ← Agent 人格
│   ├── skills/             ← 技能 (SKILL.md + config.yaml + scripts/)
│   ├── adapters/           ← SDK 启动模板 (Claude/Codex/KimiCode)
│   ├── tools/              ← MCP 工具定义
│   ├── agents/             ← 子 agent 定义 (从 AgentForge 下载)
│   └── knowledge/          ← 参考文档
├── scenarios/              ← 多 agent 场景编排
├── scripts/                ← 运维和适配脚本
└── docs/                   ← 文档
```

## 快速开始

### 1. 环境配置

```bash
gh repo clone ezagent42/Socialwares
cd Socialwares

# 配置 Claude Code (创建 .claude/skills/ symlink)
./scripts/setup-claude.sh

# 安装依赖
uv sync
```

### 2. 启动 Mock 服务

```bash
# TaskArena (端口 8001)
uv run --package taskarena uvicorn taskarena.app:app --port 8001

# AgentForge (端口 8002)
uv run --package agentforge uvicorn agentforge.app:app --port 8002
```

### 3. 开发模式 (Claude Code CLI)

```bash
claude
# 然后在 Claude Code 里使用 /taskarena /agentforge 命令
```

### 4. Agent 模式 (SDK)

```bash
# 单 agent
./scripts/launch.sh --adapter claude

# 多 agent 场景
./scripts/launch-scenario.sh scenarios/examples/task-review.yaml
```

## 四原语开发规范

每个 SW App 必须定义四原语，在 `agent/skills/{app}/config.yaml` 中声明：

### Role (角色)

```yaml
roles:
  R1:
    name: admin
    label: "管理员"
    permissions: [create, read, update, delete, close]
```

- 每个角色有唯一 ID (R1, R2, ...)
- permissions 列表定义允许的操作
- pre_send hook 根据角色检查权限

### Flow (状态机)

```yaml
flow:
  name: entity_lifecycle
  states: [draft, active, closed]
  transitions:
    - from: draft
      to: active
      action: activate
      role: R1
```

- 每个 transition 指定 from/to/action/role
- 非法 transition 被 API 拒绝 (HTTP 409)
- 状态机图推荐用 Mermaid 画在 SKILL.md 里

### Commitment (承诺)

```yaml
commitments:
  C1:
    description: "描述承诺内容"
    trigger_state: submitted
    deadline_hours: 72
    escalation_role: R1
```

- trigger_state: 哪个状态触发计时
- deadline_hours: 超时时间
- escalation_role: 超时后升级给谁

### Arena (作用域)

```yaml
arena:
  min_members: 2
  scope: room        # room | global | custom
  open: false        # 是否允许外部加入
```

## 创建新 SW App

### Checklist

1. `apps/{name}/pyproject.toml` — 项目配置
2. `apps/{name}/src/{name}/app.py` — FastAPI 应用
3. `agent/skills/{name}/SKILL.md` — 技能文档
4. `agent/skills/{name}/config.yaml` — 四原语定义
5. `agent/skills/{name}/scripts/` — API 调用脚本
6. `agent/tools/{name}-api.yaml` — MCP 工具定义
7. `agent/skills/{name}/references/` — API 参考文档
8. `tests/test_{name}.py` — 测试

### 步骤

```bash
# 1. 创建 App 目录
mkdir -p apps/myapp/src/myapp
touch apps/myapp/src/myapp/__init__.py

# 2. 创建 skill 目录
mkdir -p agent/skills/myapp/{scripts,references}

# 3. 定义四原语 (编辑 config.yaml)
cat > agent/skills/myapp/config.yaml << 'EOF'
domain: myapp
api_url: http://localhost:8003
roles:
  R1: {name: admin, label: "管理员", permissions: [all]}
  R2: {name: user, label: "用户", permissions: [read, create]}
flow:
  name: myapp_lifecycle
  states: [draft, active, closed]
  transitions: []
commitments: {}
arena: {scope: room}
EOF

# 4. 写 SKILL.md
# 5. 写 scripts/
# 6. 写测试
# 7. 自举: 用 /taskarena 追踪这些开发任务
```

## Agent 适配

### 支持的平台

| 平台 | 适配器 | SDK | 状态 |
|------|--------|-----|------|
| Claude | `agent/adapters/claude/` | claude-agent-sdk | Mock |
| Codex | `agent/adapters/codex/` | openai-agents | Mock |
| KimiCode | `agent/adapters/kimicode/` | kimicode-sdk | Mock |

### 添加新适配器

1. 创建 `agent/adapters/{name}/launcher.py`
2. 继承 `agent/adapters/base.py:BaseAdapter`
3. 实现 `build_system_prompt()`, `launch()`, `launch_headless()`
4. 创建 `requirements.txt`
5. 在 `agent/skills/agentforge/config.yaml` 的 adapters 中注册

### SKILL.md 的 allowed-tools 字段

SKILL.md frontmatter 支持可选的 `allowed-tools` 字段，用于声明该技能需要的工具权限：

```yaml
---
name: taskarena
description: "TaskArena Socialware App"
allowed-tools: "Bash"
---
```

当前项目使用 `bypassPermissions` 模式，所以 `allowed-tools` **不需要设置**。
但如果将来切换到更严格的权限模式，需要在每个 SKILL.md 中添加此字段。

常见值:
- `"Bash"` — 允许执行 bash 命令 (scripts/)
- `"Bash(taskarena:*)"` — 只允许特定命名空间的命令
- `"Read,Grep,Bash"` — 多个工具用逗号分隔

## 多 Agent 场景

### 场景 YAML 格式

```yaml
name: scenario-name
description: "描述"
bus: {type: local, endpoint: localhost:8080}
agents:
  - name: agent-name
    template: agent/agents/template-dir
    adapter: claude
    roles: [app:R1]
    auto_start: true
workflow:
  - agent-name: "/command args"
```

### 从角色自动生成 Agent

```bash
# 从 TaskArena 角色配置生成 agent 定义
uv run agent/skills/agentforge/scripts/generate_from_roles.py \
  --config agent/skills/taskarena/config.yaml

# 生成的 agent 在 agent/agents/
ls agent/agents/
# taskarena-admin/  taskarena-submitter/  taskarena-reviewer/
```

## 自举开发模式

```
Iteration 0: 基础环境 → Claude Code 写代码
Iteration 1: TaskArena 可用 → /taskarena 管理开发任务
Iteration 2: AgentForge 可用 → /agentforge 管理开发 agent
Iteration 3: Adapters 可用 → launch.sh 启动 headless agent
```

每一步都在用上一步的产出开发下一步。这就是 Socialware 的自举。

## 常用命令

```bash
# 开发
uv sync                                           # 安装依赖
uv run pytest                                     # 运行测试
uv run --package taskarena uvicorn taskarena.app:app --port 8001  # 启动 TA

# Agent
./scripts/setup-claude.sh                         # 配置 Claude Code
./scripts/launch.sh --adapter claude              # 启动单 agent
./scripts/launch-scenario.sh scenarios/xxx.yaml   # 多 agent 场景

# 生成
uv run agent/skills/agentforge/scripts/generate_from_roles.py --config ...
```
````

**Step 2: Commit**

```bash
git add docs/
git commit -m "docs: dev-guide.md — development guide with four-primitives spec and bootstrap workflow"
```

---

## Task 14: Final — push to remote

**Step 1: Verify structure**

```bash
find . -not -path './.git/*' -type f | sort | head -60
```

Expected: all files from tasks 1-13.

**Step 2: Push**

```bash
git push -u origin feat/initial-setup
```

**Step 3: Create PR**

```bash
gh pr create --title "feat: Socialwares repo initial setup" --body "$(cat <<'EOF'
## Summary

- Claude Code dev config adapted from agent-setup (settings, hooks, mcp, claude.sh)
- GitAgent format agent/ directory with skills, tools, adapters, knowledge
- TaskArena + AgentForge mock FastAPI stubs
- Multi-platform adapter templates (Claude, Codex, KimiCode)
- Setup scripts (setup-claude.sh, setup-codex.sh, setup-kimicode.sh)
- Launch scripts (launch.sh, launch-scenario.sh)
- Dev guide (docs/dev-guide.md)

## Four Primitives

All SW Apps expose API through Role/Flow/Commitment/Arena.
Config defined in agent/skills/{app}/config.yaml.

## Self-Bootstrap

.claude/skills/ → agent/skills/ symlink enables:
- Iteration 0: Basic Claude Code config
- Iteration 1: /taskarena commands for task management
- Iteration 2: /agentforge commands for agent management
- Iteration 3: SDK launchers for headless agents

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

Plan complete and saved to `docs/plans/2026-03-18-socialwares-repo-setup-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
