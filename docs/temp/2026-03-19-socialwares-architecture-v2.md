# Socialwares 仓库架构设计 v2

> v2.0 — 2026-03-19

## 一句话定义

Socialwares 是 Socialware App 的**脚手架模板**（对标 `phx.gen`）。
用户 clone 模板 → 在 workspace 中创建自己的 app → 定义四原语 → deploy → start。

```
传统 App:   UI → API → DB         (数据库 CRUD 可视化)
Socialware: UI → Chat → Agent      (Agent 交互可视化，从对话中渐进生长)
```

---

## 1. 项目结构

```
socialwares/                                  ← 模板 (Git Repo Root)
│
├── src/                                      ← App 代码模板
│   ├── api/                                  ← FastAPI 后端
│   └── web/                                  ← Next.js 前端
│
├── agents/                                   ← 四原语 + 工具链
│   ├── role/                                 ← §1 Who: Subagent 定义
│   │   ├── admin/
│   │   │   └── SOUL.md
│   │   └── reviewer/
│   │       └── SOUL.md
│   ├── scope/                                ← §4 Where: 能力声明
│   │   └── SOUL.md
│   ├── commitment/                           ← §3 What: Eval 指标
│   │   └── eval.yaml
│   ├── flow/                                 ← §2 How: Skills (AutoService 模式)
│   │   ├── create_task/
│   │   │   ├── SKILL.md
│   │   │   └── scripts/
│   │   └── review_task/
│   │       ├── SKILL.md
│   │       └── scripts/
│   │
│   ├── deploy.sh                             ← 编译：四原语 → .runtime/
│   ├── start.sh                              ← 统一启动入口
│   └── adapters/                             ← 平台适配
│       ├── base.py                           ← 公共接口
│       ├── claude/
│       │   ├── shell.sh                      ← Claude TUI + tmux (dev)
│       │   └── sdk.py                        ← Claude Agent SDK (prod)
│       ├── codex/
│       │   ├── shell.sh                      ← Codex CLI
│       │   └── sdk.py                        ← OpenAI Agents SDK
│       └── kimicode/
│           └── sdk.py                        ← KimiCode SDK
│
├── .socialware/
│   └── workspace/                            ← 用户的 app 实例
│       ├── default/                          ← 默认 workspace (模板 copy)
│       │   ├── src/
│       │   ├── agents/
│       │   └── .runtime/                     ← gitignored
│       └── {room-name}/                      ← 用户自建 workspace
│           └── {app-name}/
│               ├── src/                      ← 用户自定义的 app 代码
│               ├── agents/                   ← 用户自定义的四原语
│               └── .runtime/                 ← gitignored
│
├── .gitignore                                ← 排除 .runtime/
└── docs/
```

### 关键约定

| 约定 | 说明 |
|------|------|
| 模板 vs 实例 | 根目录 `src/` + `agents/` 是模板，workspace 里的是用户实例 |
| `.runtime/` | deploy.sh 生成，每个 role 独立子目录，始终 gitignored |
| Flow = Skill | `agents/flow/{action}/` 遵循 AutoService 模式 (SKILL.md + scripts/) |
| Role = Sub-agent | `agents/role/{name}/SOUL.md` 定义每个角色的 agent 身份 |
| Scope = SOUL.md | `agents/scope/SOUL.md` 是 App 级能力声明 |

---

## 2. 四原语

### 2.1 原语定义

```
  ┌─────────────────┐  ┌─────────────────┐
  │  §1 Role (Who)  │  │ §4 Scope (Where)│
  │                 │  │                 │
  │  组织中的位置     │  │  能力边界声明     │
  │  + 能力集        │  │  对内=边界       │
  │                 │  │  对外=公开描述    │
  │  agents/role/   │  │  agents/scope/  │
  │  每 role 一个    │  │  SOUL.md        │
  │  SOUL.md        │  │                 │
  ├─────────────────┤  ├─────────────────┤
  │ §3 Commitment   │  │  §2 Flow (How)  │
  │    (What)       │  │                 │
  │  可追踪义务      │  │  状态机 + 动作   │
  │  SLA + 截止时间  │  │  = Skill        │
  │                 │  │                 │
  │  agents/        │  │  agents/flow/   │
  │  commitment/    │  │  每 action 一个  │
  │  eval.yaml      │  │  SKILL.md       │
  └─────────────────┘  └─────────────────┘
```

### 2.2 SwSim 四原语 → agents/ 目录 → GitAgent/AutoService 映射

| SwSim 原语 | agents/ 目录 | 核心文件 | GitAgent 对应 | AutoService 对应 |
|---|---|---|---|---|
| **Role** (§1) | `role/{name}/` | `SOUL.md` | 子 agent 定义 | — |
| **Flow** (§2) | `flow/{action}/` | `SKILL.md` + `scripts/` | — | Skill 模式 |
| **Commitment** (§3) | `commitment/` | `eval.yaml` | — | Hook/eval |
| **Arena→Scope** (§4) | `scope/` | `SOUL.md` | Agent identity | — |

### 2.3 四原语在 .socialware.md 中的表现

四原语同时体现为两种形态：

```
agents/ 目录结构 (可执行)          .socialware.md 文件 (声明式)
─────────────────────────         ─────────────────────────────
agents/role/admin/SOUL.md    ←→   §1 Roles: R1 admin [权限列表]
agents/flow/create_task/     ←→   §2 Flows: F1 状态机 transitions
agents/commitment/eval.yaml  ←→   §3 Commitments: C1 SLA 定义
agents/scope/SOUL.md         ←→   §4 Arena: 参与边界
```

---

## 3. deploy.sh 编译机制

### 3.1 编译过程

`agents/deploy.sh` 读取四原语，为每个 role 生成独立的 `$PROJECT_DIR`：

```
    agents/ (四原语源码)                    .runtime/ (编译产物)
    ┌──────────────────┐                   ┌──────────────────────────┐
    │ role/             │                   │ admin/                   │
    │   admin/SOUL.md   │                   │   .claude/               │
    │   reviewer/SOUL.md│    deploy.sh      │     skills/              │
    │ scope/            │ ──────────────>   │       create_task/ → ... │
    │   SOUL.md         │                   │       review_task/ → ... │
    │ commitment/       │                   │     hooks/               │
    │   eval.yaml       │                   │   SOUL.md (scope + role) │
    │ flow/             │                   │   Files/                 │
    │   create_task/    │                   │   Sqlite/                │
    │   review_task/    │                   ├──────────────────────────┤
    └──────────────────┘                   │ reviewer/                │
                                           │   .claude/               │
                                           │     skills/ → ...        │
                                           │   SOUL.md (scope + role) │
                                           │   Files/                 │
                                           │   Sqlite/                │
                                           └──────────────────────────┘
```

### 3.2 每个 role 的 .runtime/ 内容

```
.runtime/{role}/                          ← 该 role 的 $PROJECT_DIR
├── .claude/                              ← Claude Code 配置
│   ├── skills/                           ← 软连接自 agents/flow/
│   │   ├── create_task/ → ../../../../agents/flow/create_task/
│   │   └── review_task/ → ../../../../agents/flow/review_task/
│   ├── hooks/                            ← 从 agents/ 配置生成
│   └── mcp.json                          ← MCP 配置
├── SOUL.md                               ← 合并: scope/SOUL.md + role/{name}/SOUL.md
├── Files/                                ← 运行时文件
└── Sqlite/                               ← 持久化数据
```

### 3.3 deploy 触发时机

- 手动：`./agents/deploy.sh`
- 自动：`start.sh` 启动时检测 agents/ 是否有变更，有则自动 deploy

---

## 4. start.sh 启动机制

### 4.1 统一入口

```bash
./agents/start.sh [options]

# 选项
--role <name>[,name2]       # 指定启动的 role (默认: 全部)
--adapter <claude|codex|kimicode>  # 平台 (默认: claude)
--mode <shell|sdk>          # shell=TUI开发, sdk=生产 (默认: shell)
--workspace <path>          # workspace 路径 (默认: .socialware/workspace/default)
```

### 4.2 启动流程

```
  start.sh
     │
     ├── 1. 检查 .runtime/ 是否最新
     │      └── 不是 → 自动执行 deploy.sh
     │
     ├── 2. 根据 --adapter 选择平台
     │
     ├── 3. 根据 --mode 选择启动方式
     │      ├── shell → adapters/{platform}/shell.sh
     │      └── sdk   → adapters/{platform}/sdk.py
     │
     └── 4. 根据 --role 启动 agent
            ├── 单 role → 直接启动
            └── 多 role → tmux 多 pane，每 role 一个
```

### 4.3 使用示例

```bash
# 开发模式：Claude TUI，单角色
./agents/start.sh --role admin

# 开发模式：Claude TUI，多角色 (tmux)
./agents/start.sh --role admin,reviewer

# 生产模式：Claude Agent SDK
./agents/start.sh --role admin --mode sdk

# 切换平台：Codex
./agents/start.sh --role admin --adapter codex

# 指定 workspace
./agents/start.sh --role admin --workspace .socialware/workspace/my-room/my-app
```

### 4.4 adapter 内部机制

每个 adapter 做同一件事，用不同的平台 SDK：

```
adapter 接收:
  - project_dir: .runtime/{role}/     ← $PROJECT_DIR
  - soul: 合并后的 SOUL.md            ← system prompt
  - skills: .runtime/{role}/.claude/skills/

adapter 执行:
  ┌─ claude/shell.sh ────────────────────────┐
  │ claude --project-dir $project_dir        │
  │        --system-prompt $soul             │
  │        --permission-mode bypassPermissions│
  └──────────────────────────────────────────┘

  ┌─ claude/sdk.py ──────────────────────────┐
  │ Agent(                                   │
  │   model="claude-sonnet-4-6",            │
  │   system_prompt=soul,                    │
  │   project_dir=project_dir,               │
  │ ).run()                                  │
  └──────────────────────────────────────────┘

  ┌─ codex/shell.sh ─────────────────────────┐
  │ codex --project-dir $project_dir         │
  │       --system-prompt $soul              │
  └──────────────────────────────────────────┘
```

---

## 5. 用户旅程

### 5.1 从模板到运行

```
用户                         socialwares 模板                    系统
 │                                │                              │
 │  git clone socialwares         │                              │
 │ ──────────────────────────────>│                              │
 │                                │                              │
 │  (workspace/default/ 自动      │                              │
 │   copy 模板内容)               │                              │
 │                                │                              │
 │  修改 agents/ 四原语            │                              │
 │  (在 workspace 中)             │                              │
 │                                │                              │
 │  ./agents/deploy.sh            │                              │
 │ ──────────────────────────────>│  编译四原语 → .runtime/       │
 │                                │  每 role 独立 PROJECT_DIR    │
 │                                │────────────────────────────>│
 │  ✓ .runtime/ 就绪              │                              │
 │<───────────────────────────────│                              │
 │                                │                              │
 │  ./agents/start.sh --role admin│                              │
 │ ──────────────────────────────>│  检查 .runtime/ 最新          │
 │                                │  选择 adapter (claude)       │
 │                                │  启动 agent                  │
 │                                │────────────────────────────>│
 │                                │                              │
 │  Claude TUI 就绪               │         ┌──────────┐        │
 │  "帮我创建一个任务"             │         │  Agent   │        │
 │ ──────────────────────────────>│────────>│ (admin)  │        │
 │                                │         │ flow/    │        │
 │                                │         │ create → │──> API │
 │  ✓ 任务已创建                   │         └──────────┘        │
 │<───────────────────────────────│                              │
```

### 5.2 创建新 workspace

```
用户                         socialwares                        系统
 │                                │                              │
 │  创建新 room + app             │                              │
 │  (Dashboard 或手动 copy)       │                              │
 │ ──────────────────────────────>│                              │
 │                                │  .socialware/workspace/      │
 │                                │    my-room/                  │
 │                                │      my-task-app/            │
 │                                │        src/ (copy from tmpl) │
 │                                │        agents/ (copy)        │
 │                                │────────────────────────────>│
 │                                │                              │
 │  修改 agents/ 四原语            │                              │
 │  (定制自己的 app)               │                              │
 │                                │                              │
 │  ./agents/start.sh             │                              │
 │    --workspace .socialware/    │                              │
 │      workspace/my-room/        │                              │
 │      my-task-app               │                              │
 │    --role admin                │                              │
 │ ──────────────────────────────>│  deploy + 启动                │
 │                                │────────────────────────────>│
```

### 5.3 多 agent 协作

```
  ./agents/start.sh --role admin,reviewer

  ┌─ tmux session ──────────────────────────────────────┐
  │                                                      │
  │  ┌─ pane 1: admin ───────┐  ┌─ pane 2: reviewer ──┐ │
  │  │                       │  │                      │ │
  │  │  Claude TUI           │  │  Claude TUI          │ │
  │  │  PROJECT_DIR:         │  │  PROJECT_DIR:        │ │
  │  │  .runtime/admin/      │  │  .runtime/reviewer/  │ │
  │  │                       │  │                      │ │
  │  │  SOUL.md:             │  │  SOUL.md:            │ │
  │  │  scope + admin 身份   │  │  scope + reviewer 身份│ │
  │  │                       │  │                      │ │
  │  │  skills:              │  │  skills:             │ │
  │  │  全部 flow/           │  │  全部 flow/          │ │
  │  │                       │  │                      │ │
  │  └───────────┬───────────┘  └──────────┬───────────┘ │
  │              │                          │             │
  │              └──── P2P Bus (Zenoh) ─────┘             │
  │                  (未来：agent 间通信)                   │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

---

## 6. 渐进生长 (P1→P5→P0)

```
  P1 定义 Agent        P2 完善 Flow        P3 完善 Commitment
  ┌────────────┐      ┌────────────┐      ┌────────────┐
  │ scope/     │      │ flow/      │      │commitment/ │
  │ SOUL.md    │ ──>  │ 增加 skill │ ──>  │ 增加 eval  │
  │ role/ 1个  │      │ src/ API↑  │      │ src/ 监控↑ │
  │ flow/ 1-2个│      │ src/ UI↑   │      │            │
  └────────────┘      └────────────┘      └────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
  P4 扩大 Scope        P5 扩充 Role        P0 跨 App
  ┌────────────┐      ┌────────────┐      ┌────────────┐
  │ scope/     │      │ role/      │      │ 新建 App   │
  │ SOUL.md↑   │ ──>  │ 增加角色   │ ──>  │ 或 /zchat  │
  │ flow/ ↑    │      │ flow/ 重编 │      │ 连接已有   │
  │commitment/↑│      │ scope/ 重划│      │            │
  └────────────┘      └────────────┘      └────────────┘

  每次改进 materialize 为 Biz 层 (API + UI + DB) 增长
```

---

## 7. 跨 App 协作

### 7.1 通过四原语声明

```yaml
# app-A 的 agents/flow/delegate_review/SKILL.md
# 声明: 此 action 委托给外部 app
---
name: delegate_review
description: "委托审核给 AgentForge 的 reviewer"
delegate:
  app: agentforge
  action: spawn_reviewer
---
```

```yaml
# app-A 的 agents/scope/SOUL.md
# 声明: 允许哪些外部 agent 参与
connections:
  - app: agentforge
    permissions: [spawn, query]
```

### 7.2 通信拓扑

```
  ┌─ Workspace A ─────────────┐     ┌─ Workspace B ─────────────┐
  │                           │     │                           │
  │  ┌─────────┐ ┌─────────┐ │     │ ┌─────────┐ ┌─────────┐  │
  │  │ admin   │ │reviewer │ │     │ │ admin   │ │ builder │  │
  │  │ agent   │ │ agent   │ │     │ │ agent   │ │ agent   │  │
  │  └────┬────┘ └────┬────┘ │     │ └────┬────┘ └────┬────┘  │
  │       │           │      │     │      │           │       │
  │  ┌────┴───────────┴────┐ │     │ ┌────┴───────────┴────┐  │
  │  │    TaskArena App    │ │     │ │   AgentForge App    │  │
  │  └─────────────────────┘ │     │ └─────────────────────┘  │
  │                           │     │                           │
  └───────────┬───────────────┘     └───────────┬───────────────┘
              │                                  │
              └──────── P2P Bus (Zenoh) ─────────┘
                     Agent 间 IM 通信
```

- **Socialware 中心化托管**：App 代码 + 前端 + 后端 中心化部署
- **Agent 去中心化**：通过安装 Socialware 绑定 agent，agent 间 P2P 通信
- **跨 App 编排**：通过 flow/ 的 delegate 和 scope/ 的 connections 声明

---

## 8. origin/main 代码拆分

当前 origin/main 的 `api/` + `app/` 拆分方案：

| origin/main 文件 | 归属 | 说明 |
|---|---|---|
| `api/auth.py`, `api/routers/auth.py` | 独立 auth app | 统一认证，其他 app 通过 flow/ delegate |
| `api/routers/rooms.py`, `api/models.py (Room)` | `src/api/` | Workspace/Room 管理 (Dashboard 功能) |
| `api/routers/agents.py` | `src/api/` | Agent 调用 → 未来对接 agents/start.sh |
| `api/agent_bridge.py` | `agents/adapters/claude/sdk.py` | 替换为 adapter 模式 |
| `api/models.py (AgentTask)` | `src/api/` | 任务模型 (Biz 层) |
| `app/` (Next.js 全部) | `src/web/` | 重命名 |

---

## 9. 术语表

| 术语 | 定义 |
|------|------|
| **Socialware** | Agent 交互可视化的 Web 应用 |
| **Workspace** | 租户，独立部署实例 (= git worktree + .runtime) |
| **Room** | Workspace 内部组织/群组 |
| **Biz 层** | Agent 能力沉淀为 API + UI + DB |
| **四原语** | Role / Scope / Commitment / Flow |
| **SOUL.md** | Agent 能力声明 (对内=Scope 边界，对外=公开描述) |
| **deploy** | 编译四原语 → .runtime/ (每 role 独立 $PROJECT_DIR) |
| **adapter** | 平台适配层 (Claude / Codex / KimiCode) |
| **.runtime/** | deploy 生成的运行时目录，始终 gitignored |

---

## 10. 当前约束

| 项目 | 状态 |
|------|------|
| 部署模型 | 中心化 + 登录认证 |
| Agent 运行时 | Claude Code (agnostic，兼容 Codex/KimiCode) |
| Agent 通信 | 预留 P2P Bus (Zenoh)，当前本地 |
| App 权限检查 | App 自身 API 层处理 (人→agent→app) |
| Dashboard | 替代 CLI，本身也是 Socialware App |
