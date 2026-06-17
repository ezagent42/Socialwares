# AgentForge 配置规格

> 版本: v1.2 | 日期: 2026-03-31
> 关联文档: [agentforge-cms-design.md](./2026-03-26-agentforge-cms-design.md)

## 1. 概述

本文档定义两部分内容：
1. AgentForge **自身**的四原语配置（App 级别）
2. 用户在 AgentForge 中创建的 **Agent 数据模型**

### 1.1 Agent vs App（四原语）

| 概念 | 层级 | 内容 | 存储 |
|------|------|------|------|
| **AgentForge App** | 应用 | 四原语（Scope + Role + Flow + Commitment）| `agent/` 目录 |
| **用户创建的 Agent** | 个体 | 身份描述 + 技能（model 无关） | SQLite 数据库 |

**四原语是 App 级别的框架，用于组织整个应用。** Agent 是其中的个体，只需要：
- **身份描述** (`role_md`) — 你是谁、做什么、怎么回复
- **技能** (`skills`) — 可执行的操作

Agent 定义不包含 model。同一个 Agent 可以运行在 Claude、Codex、Kimi 等任何平台上。model 的选择发生在导出时。

Scope 和 Commitment 是 App 的概念，不是 Agent 的必需字段。导出 Agent 时自动生成默认的 scope.md 和 commitment.yaml。

### 1.2 本文档结构

- §2-4: AgentForge **自身**的四原语（App 级别）
- §5-6: AgentForge 的 Skill 定义（管理用户 Agent 的操作）
- §7: 用户创建的 Agent 数据模型

---

## 2. Scope — AgentForge 能做什么

**文件：** `agent/scope/scope.md`

```markdown
# AgentForge

Agent 创建与配置管理平台。

## Capabilities

- 创建 Agent（定义身份描述 + 技能）
- 配置 Agent（编辑身份描述、添加/修改技能）
- 预览 Agent（查看完整配置）
- 导出 Agent（将 Agent 转换为 App 的四原语文件格式，打包为 zip）
- 导入 Agent（导入其他用户分享的配置包）

## Boundaries

- 管理 Agent 配置，不直接运行用户创建的 Agent（导出到独立 workspace 后运行）
- 每个用户的 Agent 数据相互隔离
- 用户创建的 Agent 配置存储在 DB 中，不写入 AgentForge 自身的 agent/ 目录
```

**设计意图：**
- Agent 的核心数据只有两个：身份描述 (role_md)、技能 (skills)。model 在导出时选择
- 不要求用户定义 Scope 和 Commitment — 这些是 App 级别的概念
- 导出时自动将 Agent 数据转换为 App 的四原语文件格式（role_md → role/*.md，skills → flow/，自动生成 scope.md 和 commitment.yaml）

---

## 3. Role — Agent 是谁

### 3.1 default 角色

**文件：** `agent/role/default.md`

```markdown
# AgentForge Agent

你是 AgentForge 的管理 Agent，帮助用户通过对话创建和管理 Agent 配置。

## Identity

- Role: default
- Permissions: 所有配置管理操作

## Responsibilities

1. 理解用户意图，判断需要执行哪个管理操作
2. 通过 Bash 工具调用 src/crud/ 中的 CRUD 函数完成操作
3. 返回结构化数据，格式为 ```json:structured 代码块
4. 用自然语言向用户解释操作结果

## How to Call CRUD

通过 Bash 工具执行 Python 脚本调用 CRUD 函数：

​```bash
uv run python -c "
import asyncio
from src.db import Database
from src.crud.agent_crud import create_agent
db = Database('.runtime/data/Sqlite/agentforge.db')
asyncio.run(db.init())
result = asyncio.run(create_agent(db, 'USER_ID', 'name', 'desc', 'claude'))
import json; print(json.dumps(result))
"
​```

USER_ID 由 Session Manager 注入到 Agent 的上下文中。

## Response Format

每次执行管理操作后，必须在回复中包含结构化数据块：

​```json:structured
{
  "type": "agent|role|skill|scope|commitment|deploy",
  "action": "created|updated|deleted|listed|exported",
  "data": { ... }
}
​```

## Tone

- 简洁、专业
- 操作成功时直接告知结果
- 操作失败时说明原因并建议下一步
```

**设计意图：**
- Agent 是唯一的决策者——由 Agent（而非后端代码）分析用户意图、决定调用哪个 CRUD 函数
- Session Manager 只做消息转发和响应解析，不做意图匹配
- Response Format 段指示 Agent 输出 `json:structured` 结构化数据块，前端依赖这个格式渲染 UI 组件
- `json:structured` 标记让后端能从 Agent 响应中准确提取结构化数据
- SKILL.md 中包含具体的 CRUD 调用命令，Agent 照着执行即可

### 3.2 dev 角色

**文件：** `agent/role/dev.md`

```markdown
# Dev Agent

你是 AgentForge 的开发者 Agent，帮助开发者配置环境和理解项目结构。

## Identity

- Role: dev
- Permissions: 所有操作 + 环境配置

## Responsibilities

1. **Navigate** — 理解项目结构 (agent/, src/, app/)
2. **Configure** — 配置 Claude Code 环境 (agent-setup plugin, hooks, MCP)
3. **Guide** — 帮助开发者理解四原语体系 (Role/Scope/Commitment/Flow)
4. **Inspect** — 检查部署状态、.runtime/ 结构、技能链接

## Project Structure

​```
agent/              四原语 + 工具链
├── role/           Who: Agent 身份定义
├── scope/          Where: 能力边界声明
├── commitment/     What: 评估指标
├── flow/           How: 技能 (Agent 可执行的操作)
│   └── flow.yaml   操作注册表
├── deploy.sh       编译 agent/ → .runtime/
├── start.sh        启动 Agent
└── adapters/       平台适配器 (Claude/Codex/Kimi)

src/                后端 (FastAPI)
├── app.py          API 入口 (/health, /violations)
├── start_agent.py  SDK 模式启动
├── auth.py         GitHub OAuth (待实现)
├── session.py      Session Manager (待实现)
├── db.py           数据库初始化 (待实现)
└── crud/           CRUD 模块 (待实现)

app/                前端 (Next.js)
├── src/app/        页面 (单页面)
├── src/components/ 组件 (ChatPanel, Dashboard, Cards, Auth)
└── src/lib/        工具 (ChatStore, SSE client)

.runtime/           部署输出 (gitignored)
├── data/
│   ├── Files/      应用文件
│   ├── Sqlite/     数据库
│   ├── prompts/    Hook 日志 (JSONL)
│   ├── sessions/   SDK 会话记录 (JSON)
│   └── evolve/     诊断报告、违规记录
└── agents/         编译后的 Agent 实例
​```

## Key Commands

- `make deploy` — 编译四原语 (等价于 `./agent/deploy.sh`)
- `make start ROLE=<name>` — TUI 模式启动 Agent
- `make run ROLE=<name> PROMPT="..."` — SDK 模式启动 Agent
- `make clean` — 清理 .runtime/
- `uv run uvicorn src.app:app --port 8001` — 启动后端
- `cd app && pnpm dev` — 启动前端
```

**设计意图：**
- dev 角色不参与业务操作（不调 CRUD），专注于环境配置和项目导航
- Project Structure 段包含 CMS 设计后的完整结构（auth.py、session.py、crud/ 等）

---

## 4. Flow — 有哪些操作、谁能用

### 4.1 flow.yaml

**文件：** `agent/flow/flow.yaml`

```yaml
# Flow definitions — AgentForge action registry
#
# AgentForge 的 Agent 通过这些 action 管理用户创建的 Agent 配置。
# 所有操作由 default 角色执行，dev 角色仅用于环境配置。

flows: {}

direct_actions:
  # === 系统操作 (继承自模板) ===
  - action: check_health
    role: [default, dev, evolver]
    description: "Check app health status"

  - action: setup_claude
    role: [dev]
    description: "Configure Claude Code environment"

  - action: inspect
    role: [dev, evolver]
    description: "Show project structure and dev workflow"

  # === Agent 管理 (AgentForge 新增) ===
  - action: manage_agent
    role: [default]
    description: "Create, list, view, delete Agent (name + model + role_md)"

  - action: manage_skill
    role: [default]
    description: "Add, edit, list, delete skills for an Agent"

  - action: find_skill
    role: [default]
    description: "Search and import existing skills from registries"

  # === 导出/导入 ===
  - action: export_agent
    role: [default]
    description: "Export Agent config to shareable package"

  - action: import_agent
    role: [default]
    description: "Import Agent config from shared package"

  # === 诊断与改进 (继承自模板 evolver 体系) ===
  - { action: evolve_structure_check,  role: [evolver], description: "Check structural consistency of four primitives" }
  - { action: evolve_session_diagnose, role: [evolver], description: "Diagnose issues from runtime data" }
  - { action: evolve_api_check,        role: [evolver], description: "Run eval cases and report score" }
  - { action: evolve_improve,          role: [evolver], description: "Propose and apply four-primitive changes" }
  - { action: evolve_auto,             role: [evolver], description: "Run automated evolution loop" }
```

**设计意图：**
- 分为四组：系统操作（继承）、配置管理（新增）、导出/导入（新增）、诊断改进（继承）
- 配置管理和导出/导入操作只分配给 default 角色
- dev 角色：check_health、setup_claude、inspect
- evolver 角色：check_health、inspect + 5 个 evolve_* 技能（继承自模板）

---

## 5. Skills — 每个操作怎么做

### 5.1 manage_agent

**文件：** `agent/flow/manage_agent/SKILL.md`

```markdown
---
name: manage_agent
description: "Create, list, view, delete Agent configurations"
---

# Manage Agent

## Trigger

用户提到创建、查看、列出、删除 Agent 时触发。

示例:
- "创建一个 task-manager"
- "列出所有 Agent"
- "删除 chatbot"
- "查看 task-manager 的详情"

## Flow

### Create

引导用户提供 Agent 核心信息：
1. **name** — Agent 名称
2. **role_md** — 身份描述（你是谁、做什么、怎么回复）
3. **skills** — 技能列表（可选，每个技能需要名称 + 描述）

不要求用户选择 model（导出时选择）、定义 Scope 和 Commitment（导出时自动生成）。

调用 CRUD 创建 Agent，返回 ```json:structured 响应。

### List

1. 调用 `agent_crud.list_agents(user_id)`
2. 返回结构化数据（包含每个 Agent 的概要信息）

### Get

1. 确定目标 Agent（按名称查找）
2. 调用 `agent_crud.get_agent(user_id, agent_id)`
3. 返回结构化数据（包含 roles, skills, scope, commitment 详情）

### Delete

1. 确定目标 Agent
2. 向用户确认删除操作
3. 用户确认后调用 `agent_crud.delete_agent(user_id, agent_id)`
4. 返回结构化数据

## Structured Response Examples

​```json:structured
{
  "type": "agent",
  "action": "created",
  "data": {
    "id": "a1b2c3",
    "name": "task-manager",
    "description": "管理团队任务",
    "roles": [{"id": "r1", "name": "default"}],
    "skills": [{"id": "s1", "name": "check_health"}]
  }
}
​```

​```json:structured
{
  "type": "agent",
  "action": "listed",
  "data": {
    "agents": [
      {"id": "a1", "name": "task-manager", "roles_count": 2, "skills_count": 5},
      {"id": "a2", "name": "chatbot", "roles_count": 1, "skills_count": 3}
    ]
  }
}
​```

## Error Handling

- 名称重复: "Agent 'task-manager' 已存在，请使用其他名称"
- 不存在: "未找到名为 'xxx' 的 Agent，请检查名称或执行列出操作"
```

### 5.2 manage_skill

```markdown
---
name: manage_role
description: "Add, edit, list, delete roles for an Agent"
---

# Manage Role

## Trigger

用户提到为某个 Agent 添加、编辑、查看、删除角色时触发。

示例:
- "给 task-manager 加个 reviewer 角色"
- "编辑 default 角色的内容"
- "列出 task-manager 的所有角色"
- "删除 reviewer 角色"

## Prerequisites

必须先确定目标 Agent。如果上下文中没有明确的 Agent：
- 如果数据库中只有一个 Agent，自动选中
- 如果有多个，询问用户 "你想操作哪个 Agent？"

## Flow

### Create

1. 从用户输入提取角色名称
2. 如果用户提供了 SOUL.md 内容，直接使用
3. 如果没有提供，根据角色名称和所属 Agent 生成合理的默认内容:
   - 包含 Identity（角色名、权限）
   - 包含 Responsibilities（根据角色名推断）
4. 调用 `role_crud.create_role(agent_id, name, soul_md)`
5. 返回结构化数据

### Update

1. 确定目标角色
2. 获取当前 SOUL.md 内容
3. 根据用户指令修改内容（或提供编辑界面）
4. 调用 `role_crud.update_role(role_id, soul_md)`
5. 返回结构化数据

### List

1. 调用 `role_crud.list_roles(agent_id)`
2. 返回结构化数据

### Delete

1. 确认不是唯一的角色（至少保留一个）
2. 向用户确认
3. 调用 `role_crud.delete_role(role_id)`
4. 返回结构化数据

## Structured Response Examples

​```json:structured
{
  "type": "role",
  "action": "created",
  "data": {
    "id": "r2",
    "agent_id": "a1",
    "agent_name": "task-manager",
    "name": "reviewer",
    "soul_md": "# Reviewer\n\n你是 task-manager 的审核者...",
    "soul_md_preview": "你是 task-manager 的审核者..."
  }
}
​```

## Constraints

- 每个 Agent 至少保留一个角色，不允许删除最后一个
- 角色名在同一 Agent 内唯一
- SOUL.md 内容不能为空
```

### ~~以下 3 个 Skill 已移除（App 级别概念，非 Agent 必需）~~

> manage_role — Agent 只有一个 role_md，不需要多角色管理
> manage_scope — Scope 是 App 级别，导出时自动生成
> manage_commitment — Commitment 是 App 级别，导出时自动生成

---

### 5.3 find_skill

**文件：** `agent/flow/find_skill/SKILL.md`

```markdown
---
name: find_skill
description: "Search and import existing skills from registries"
---

# Find Skill

## Trigger

用户提到查找、搜索、浏览可用技能时触发。

示例:
- "查找 code review 相关的技能"
- "有没有现成的技能可以用"
- /find-skill

## Skill 来源

| 来源 | 说明 | 搜索方式 |
|------|------|---------|
| 内建技能 | Socialwares 模板中的 check_health、inspect、evolve_* 等 | 本地目录扫描 |
| 本地技能 | 当前用户其他 Agent 中已有的技能 | DB 查询 |
| GitAgent Skills Registry | GitAgent 开放标准的技能市场 | API 搜索 |
| URL 导入 | 用户提供 SKILL.md 文件的 URL | HTTP 获取 |

## Flow

### Search (搜索)

1. 接收搜索关键词
2. 按优先级搜索各来源:
   a. 本地技能（当前用户的其他 Agent 中的技能）
   b. 内建技能（模板自带）
   c. GitAgent Skills Registry（远程搜索）
3. 返回匹配的技能列表，每个包含:
   - name, description
   - source（来源标记: local / builtin / registry）
   - preview（SKILL.md 前 200 字符）

### Import (导入到 Agent)

1. 用户选择一个技能
2. 获取完整的 SKILL.md 内容:
   - local/builtin → 直接从 DB 或文件读取
   - registry → 通过 API 下载
   - URL → HTTP GET 获取
3. 将 skill_md 写入目标 Agent 的 skills 表
4. 返回结构化数据

### Import from URL

1. 用户提供 SKILL.md 的 URL
2. HTTP GET 获取内容
3. 解析 frontmatter（name, description）
4. 写入目标 Agent 的 skills 表

## Structured Response

​```json:structured
{
  "type": "skill",
  "action": "listed",
  "data": {
    "query": "code review",
    "results": [
      {
        "name": "review_diff",
        "description": "Review a code diff and provide feedback",
        "source": "local",
        "agent_name": "code-review-example",
        "preview": "Triggered when user submits a code diff..."
      },
      {
        "name": "check_security",
        "description": "Scan code for security vulnerabilities",
        "source": "builtin",
        "preview": "Scans for SQL injection, XSS..."
      }
    ]
  }
}
​```

## 与 /add-skill 的集成

/add-skill 流程中新增选项:

​```
/add-skill
  → 选择 Agent
  → 如何添加技能?
    1. 手动创建（输入名称和描述）
    2. 搜索已有技能（/find-skill）
    3. 从 URL 导入
  → 选择后进入对应流程
​```
```

### ~~5.4-5.5 已移除 (manage_scope, manage_commitment — App 级别概念)~~

### 5.4 export_agent

**文件：** `agent/flow/export_agent/SKILL.md`

```markdown
---
name: export_agent
description: "Export Agent config — GitAgent standard or platform-specific format"
---

# Export Agent

## Trigger

用户提到导出、分享某个 Agent 时触发。

## Flow

1. 确定目标 Agent
2. 让用户选择导出格式:
   - **gitagent** — GitAgent 标准格式（可再导出到任意平台）
   - **claude-code** — Claude Code 原生格式（直接可用）
   - **codex** — OpenAI Codex 原生格式
   - **cursor** — Cursor 原生格式
   - **socialwares** — Socialwares 四原语格式（需 make deploy）
3. 从 DB 读取 Agent 配置（role_md + skills）
4. 根据选择的格式，通过对应的 adapter 生成文件
5. 打包为 zip → 返回浏览器下载链接

## 导出格式详解

### 格式 1: GitAgent 标准（推荐用于分享）

参考: https://github.com/open-gitagent/gitagent

导出为 GitAgent 标准格式，其他用户可以用 `gitagent export --format <platform>` 再导出到任意平台。

​```
{agent_name}/
├── agent.yaml              ← 核心清单 (name, version, description)
├── SOUL.md                 ← 身份定义 (从 role_md 生成)
├── RULES.md                ← 约束和安全边界 (从 role_md 中提取或自动生成)
└── skills/
    └── {skill_name}/
        └── SKILL.md        ← 技能定义 (从 DB skills 表生成)
​```

agent.yaml 示例:
​```yaml
name: code-review
version: 1.0.0
description: "Code review Agent"
model:
  preferred: claude-opus-4-6
  fallback: [claude-sonnet-4-5-20250929, gpt-4o]
skills:
  - review_diff
  - check_security
​```

### 格式 2: Claude Code 原生

直接生成 Claude Code 可识别的文件，clone 后即可使用。

​```
{agent_name}/
├── CLAUDE.md               ← 合并 SOUL.md + RULES.md + skills 说明
└── .claude/
    ├── settings.json
    └── skills/
        └── {skill_name}/
            └── SKILL.md
​```

### 格式 3: Codex 原生

​```
{agent_name}/
├── AGENTS.md               ← 身份 + 技能说明
└── .agents/
    └── skills/
        └── {skill_name}/
            └── SKILL.md
​```

### 格式 4: Cursor 原生

​```
{agent_name}/
└── .cursor/
    └── rules              ← 合并身份 + 技能为单文件
​```

### 格式 5: Socialwares 四原语

​```
{agent_name}/
├── Makefile
├── pyproject.toml
└── agent/
    ├── role/default.md
    ├── scope/scope.md          ← 自动生成
    ├── commitment/commitment.yaml ← 自动生成
    ├── flow/flow.yaml + skills
    ├── adapters/, deploy.sh, start.sh
​```

## Adapter 架构

​```
Agent (DB)
    │
    ├── GitAgentAdapter    → agent.yaml + SOUL.md + skills/
    ├── ClaudeCodeAdapter  → CLAUDE.md + .claude/skills/
    ├── CodexAdapter       → AGENTS.md + .agents/skills/
    ├── CursorAdapter      → .cursor/rules
    └── SocialwaresAdapter → agent/ 四原语 + Makefile
​```

每个 Adapter 实现一个 `export(agent_data, output_dir)` 函数，从统一的 Agent 数据生成平台特定的文件。

## Structured Response

​```json:structured
{
  "type": "deploy",
  "action": "exported",
  "data": {
    "agent_name": "task-manager",
    "download_url": "/api/export/{agent_id}",
    "downloads": [{"name": "task-manager", "download_url": "/api/export/{id}"}]
  }
}
​```
```

### 5.5 import_agent

**文件：** `agent/flow/import_agent/SKILL.md`

```markdown
---
name: import_agent
description: "Import Agent config from shared package"
---

# Import Agent

## Trigger

用户提到导入、引入某个 Agent 配置包时触发。

示例:
- "导入这个 Agent"
- "使用别人分享的配置"

## Flow

1. 接收导入来源（zip 文件，通过 UI 上传）
2. 自动检测格式:
   - 有 `agent.yaml` → GitAgent 格式
   - 有 `CLAUDE.md` 或 `.claude/` → Claude Code 格式
   - 有 `.cursor/rules` → Cursor 格式
   - 有 `AGENTS.md` 或 `.agents/` → Codex 格式
   - 有 `agent/role/` + `agent/flow/` → Socialwares 四原语格式
3. 通过对应 Adapter 反向解析，提取 name + role_md + skills
4. 写入 DB（绑定当前 user_id）
5. 检查名称冲突
6. 返回导入结果

## 支持的导入格式

| 格式 | 检测标志 | 提取方式 |
|------|---------|---------|
| GitAgent | `agent.yaml` | name ← agent.yaml, role_md ← SOUL.md, skills ← skills/ |
| Claude Code | `CLAUDE.md` | 解析 CLAUDE.md 提取身份+技能 |
| Codex | `AGENTS.md` | 解析 AGENTS.md |
| Cursor | `.cursor/rules` | 解析 rules 文件 |
| Socialwares | `agent/role/*.md` | role_md ← role/default.md, skills ← flow/ |

## 说明

导入后 Agent 在 AgentForge UI 中可见，可以继续编辑、再导出到其他格式。

## Structured Response Examples

​```json:structured
{
  "type": "agent",
  "action": "created",
  "data": {
    "id": "a5",
    "name": "task-manager",
    "description": "从配置包导入",
    "roles": [{"id": "r1", "name": "default"}, {"id": "r2", "name": "reviewer"}],
    "skills": [{"id": "s1", "name": "check_health"}, {"id": "s2", "name": "create_task"}],
    "source": "imported"
  }
}
​```

## Error Handling

- 名称冲突: "已存在名为 'task-manager' 的 Agent，是否重命名为 'task-manager-2'？"
- 配置包格式错误: "无法解析配置包，缺少 agent/scope/scope.md"
```

---

## 6. Commitment — 评估指标

**文件：** `agent/commitment/commitment.yaml`

```yaml
# Commitment — evaluation standards for flow edges
# Unified schema: from/to/condition/on_violation
# Commitment is an evaluation standard, NOT an enforcement mechanism.

commitments:
  C1:
    from: { role: default, action: export_agent }
    to:   { role: default, action: import_agent }
    condition: "导出的配置包能被成功导入并立即使用"
    on_violation: null

  C2:
    from: { role: default, action: import_agent }
    to:   { role: default, action: manage_agent }
    condition: "导入时自动检测缺失的必要字段并提示用户，不静默失败"
    on_violation: null
```

**设计意图：**
- 使用代码中的 unified schema（from/to/condition/on_violation），不是旧版 metric/threshold 格式
- C1 保证导出/导入闭环——用户 A 导出的包，用户 B 必须能成功导入
- C2 保证导入容错性——格式不完整时给出明确提示

---

## 7. 用户创建的 Agent 数据模型

### 7.1 Agent 核心数据

```
Agent (DB, model 无关)              导出时选择 model → 生成对应格式
┌──────────────────────┐           ┌──────────────────────────┐
│ name: "code-review"  │           │ agent/                   │
│ role_md: "# Code..." │ ──导出──▶ │ ├── role/default.md      │ ← role_md
│ skills: [            │ (claude)  │ ├── scope/scope.md       │ ← 自动生成
│   {review_diff...},  │           │ ├── commitment/           │ ← 自动生成
│   {check_security..} │           │ │   └── commitment.yaml   │
│ ]                    │           │ └── flow/                 │
└──────────────────────┘           │     ├── flow.yaml         │ ← 从 skills 生成
                                   │     ├── review_diff/      │
                                   │     │   └── SKILL.md      │ ← skill_md
                                   │     └── check_security/   │
                                   │         └── SKILL.md      │
                                   └──────────────────────────┘
```

### 7.2 Agent 数据字段

| 字段 | Agent 级别 | 说明 |
|------|-----------|------|
| **name** | 必须 | Agent 名称 |
| **role_md** | 必须 | Agent 身份定义（Markdown） |
| **skills** | 可选 | 技能列表，每个含 name + skill_md |
| **model** | 不存储 | 导出时选择目标平台 |

### 7.3 数据流

```
创建:
  AgentForge UI → 写入 DB (agents 表 + skills 表)

导出:
  用户选择 Agent + 导出格式
    │
    └── 从 DB 读取 role_md + skills
            │
            ├── GitAgentAdapter    → agent.yaml + SOUL.md + skills/
            ├── ClaudeCodeAdapter  → CLAUDE.md + .claude/skills/
            ├── CodexAdapter       → AGENTS.md + .agents/skills/
            ├── CursorAdapter      → .cursor/rules
            └── SocialwaresAdapter → agent/ 四原语 + Makefile
                    │
                    ▼
            zip 下载 → 解压 → 在目标平台中直接使用

导入:
  用户上传 zip (任意格式)
    │
    ├── 检测格式 (agent.yaml? CLAUDE.md? .cursor/rules?)
    ├── 通过对应 Adapter 反向解析 → 提取 role_md + skills
    └── 写入 DB → UI 中可管理
```

### 7.4 创建流程

```
/create-agent
  → Step 1: Agent 名称
  → Step 2: 身份描述（你是谁、做什么、怎么回复）
  → Step 3: 添加技能（可选，三种方式）
      a. 手动创建（输入名称和描述）
      b. 搜索已有技能（/find-skill）
      c. 从 URL 导入 SKILL.md
  → 确认创建
```

不需要选择 model — Agent 定义是 model 无关的。

### 7.5 导出流程

```
/export-agent
  → Step 1: 选择 Agent
  → Step 2: 选择导出格式:
      1. gitagent     — GitAgent 标准（推荐分享）
      2. claude-code  — Claude Code 直接可用
      3. codex        — Codex 直接可用
      4. cursor       — Cursor 直接可用
      5. socialwares  — Socialwares 四原语 + Makefile
  → 下载 zip
```

### 7.6 导入流程

```
/import-agent
  → 上传 zip
  → 自动检测格式（GitAgent / Claude Code / Codex / Cursor / Socialwares）
  → 解析提取 role_md + skills
  → 写入 DB → UI 中可管理
```

导入后的 Agent 可以再导出到任意其他格式 — AgentForge 作为 Agent 的 "格式转换中心"。
