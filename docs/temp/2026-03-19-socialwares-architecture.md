# Socialwares 仓库架构设计

> v0.1 — 2026-03-19

## 一句话定义

Socialwares 是一个 monorepo，托管多个 **Socialware App**（chat 驱动的 Web 应用），
并提供统一的 **agent 基础设施**，让本地 agent 可以安装、启动、操作任意 app。

```
传统 App:  UI → API → DB        (数据库 CRUD 可视化)
Socialware: UI → Chat → Agent    (Agent 交互可视化)
```

---

## 1. 项目结构

```
Socialwares/
│
├── app/                                ← Socialware Apps (贡献者 PR 提交)
│   ├── taskarena/                      ← TaskArena: 任务管理 app
│   │   ├── src/                        ← 前端 + 后端代码
│   │   ├── agent/                      ← 四原语 contract (声明式)
│   │   │   ├── role/                   ← Who: Subagent 定义
│   │   │   │   ├── admin/
│   │   │   │   │   └── SOUL.md
│   │   │   │   ├── submitter/
│   │   │   │   │   └── SOUL.md
│   │   │   │   └── reviewer/
│   │   │   │       └── SOUL.md
│   │   │   ├── scope/                  ← Where: App 能力声明
│   │   │   │   └── SOUL.md
│   │   │   ├── commitment/             ← What: Eval 指标
│   │   │   │   └── eval.yaml
│   │   │   └── flow/                   ← How: Skills (操作定义)
│   │   │       ├── create_task/
│   │   │       │   └── SKILL.md
│   │   │       ├── review_task/
│   │   │       │   └── SKILL.md
│   │   │       └── ...
│   │   └── .socialware-workspace/      ← 运行时 workspace
│   │       └── default/
│   │           └── .runtime/           ← gitignored (DB, files)
│   │
│   ├── agentforge/                     ← AgentForge: Agent 管理 app
│   │   ├── src/
│   │   ├── agent/
│   │   └── .socialware-workspace/
│   │
│   └── auth/                           ← Auth: 统一认证 app (从 origin/main api/ 拆出)
│       ├── src/
│       ├── agent/
│       └── .socialware-workspace/
│
├── agent/                              ← Agent 基础设施 (runtime)
│   │                                     从 app/*/agent/ 读取 → 编译 → 适配
│   ├── registry.yaml                   ← 已安装 app 注册表
│   ├── SOUL.md                         ← 聚合自已安装 app 的 scope/SOUL.md
│   ├── skills/                         ← 软连接自 app/*/agent/flow/
│   │   ├── taskarena/ → ../../app/taskarena/agent/flow/
│   │   └── agentforge/ → ../../app/agentforge/agent/flow/
│   ├── agents/                         ← 解析自 app/*/agent/role/
│   ├── adapters/                       ← SDK 启动器
│   │   ├── base.py
│   │   ├── claude/
│   │   ├── codex/
│   │   └── kimicode/
│   └── hooks/
│
├── sw                                  ← CLI 入口 (过渡，最终被 Dashboard 替代)
├── scripts/                            ← 辅助脚本
│
├── .claude/                            ← Claude Code 配置
│   ├── settings.json
│   ├── mcp.json
│   └── skills/                         ← 软连接自 agent/skills/
│       ├── taskarena/ → ../../agent/skills/taskarena/
│       └── agentforge/ → ../../agent/skills/agentforge/
│
├── .gitignore                          ← 排除 .runtime/, .venv/ 等
├── pyproject.toml
└── docs/
```

### 关键约定

- **`app/`** 下的内容由贡献者通过 PR 提交，每个 app 自包含
- **`agent/`** 是"编译产物"，由 `sw install` 从 `app/*/agent/` 生成
- **`.socialware-workspace/`** 在每个 app 内部，`.runtime/` 被 gitignore
- **`.claude/skills/`** 通过两级软连接最终指向 `app/*/agent/flow/`

---

## 2. 各部件架构

### 2.1 Socialware App (`app/{name}/`)

每个 Socialware App 是一个独立的 chat 驱动 Web 应用。

```
┌─────────────────────────────────────────────┐
│              Socialware App                  │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Frontend │  │ Backend  │  │   Agent    │  │
│  │ (Next.js)│→│ (FastAPI)│←│ (via Chat) │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│       ↑              ↑              ↑        │
│     src/           src/        agent/        │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │        .socialware-workspace/        │    │
│  │  ┌─────────┐  ┌──────────────────┐   │    │
│  │  │ default │  │ workspace-alpha  │   │    │
│  │  │.runtime/│  │   .runtime/      │   │    │
│  │  └─────────┘  └──────────────────┘   │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**src/** — App 自身代码：
- 前端：用户看到的 UI + Chat 框
- 后端：API endpoints（Biz 层，从对话中渐进生长）

**agent/** — 四原语 contract（声明 agent 在此 app 中的行为）

**.socialware-workspace/** — 运行时隔离：
- 每个 workspace = 一个租户/分支
- `.runtime/` 含 SQLite、文件等，gitignored

### 2.2 四原语 (`app/{name}/agent/`)

```
           四原语 = Agent 在一个 App 中的完整 Contract

  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────────┐
  │  Role (Who) │  │ Scope (Where)│  │Commitment    │  │ Flow (How) │
  │             │  │              │  │  (What)      │  │            │
  │ Subagent    │  │  SOUL.md     │  │  Eval 指标   │  │  Skill     │
  │ 定义        │  │  能力边界    │  │  SLA         │  │  操作定义  │
  └─────────────┘  └──────────────┘  └──────────────┘  └────────────┘
        │                 │                  │                │
   role/admin/        scope/           commitment/       flow/create/
   role/reviewer/     SOUL.md          eval.yaml         flow/review/
   各有 SOUL.md                                          各有 SKILL.md
```

| 原语 | 目录 | 核心文件 | 作用 |
|------|------|---------|------|
| **Role** | `agent/role/{name}/` | `SOUL.md` | 定义 subagent 身份，每个角色一个目录 |
| **Scope** | `agent/scope/` | `SOUL.md` | App 级能力声明，对内=边界，对外=公开描述 |
| **Commitment** | `agent/commitment/` | `eval.yaml` | Eval 指标、SLA、达成标准 |
| **Flow** | `agent/flow/{action}/` | `SKILL.md` | 操作定义，每个 action 一个 Claude Code skill |

### 2.3 Agent 基础设施 (`agent/`)

根目录的 `agent/` 是"编译器 + 运行时"，把各 app 的四原语声明编译成可运行的 agent 配置。

```
                     sw install taskarena
                            │
                            ▼
  ┌──────────────────────────────────────────────┐
  │            agent/ (编译器 + 运行时)            │
  │                                               │
  │  ┌─────────┐    ┌─────────┐    ┌──────────┐  │
  │  │registry │    │ skills/ │    │ agents/  │  │
  │  │  .yaml  │    │(symlink)│    │(parsed)  │  │
  │  └────┬────┘    └────┬────┘    └────┬─────┘  │
  │       │              │              │         │
  │  记录已安装      软连接自         解析自       │
  │  的 app        flow/            role/         │
  │                                               │
  │  ┌────────────────────────────────────────┐   │
  │  │           adapters/                    │   │
  │  │  ┌────────┐ ┌───────┐ ┌──────────┐    │   │
  │  │  │ Claude │ │ Codex │ │ KimiCode │    │   │
  │  │  └────────┘ └───────┘ └──────────┘    │   │
  │  └────────────────────────────────────────┘   │
  └──────────────────────────────────────────────┘
                            │
                            ▼
                  .claude/skills/ (二级软连接)
                            │
                            ▼
                   Claude Code 可直接使用
```

**编译过程** (`sw install`):

1. 读 `app/{name}/agent/flow/` → 软连接到 `agent/skills/{name}/`
2. 读 `app/{name}/agent/scope/SOUL.md` → 聚合到 `agent/SOUL.md`
3. 读 `app/{name}/agent/role/` → 解析到 `agent/agents/`
4. 读 `app/{name}/agent/commitment/` → 记录 eval 配置
5. 更新 `agent/registry.yaml`
6. 更新 `.claude/skills/` 软连接

### 2.4 Dashboard（替代 CLI）

`sw` CLI 是过渡方案，最终被 Dashboard 替代：

```
┌────────────────────────────────────────┐
│         Socialware Dashboard            │
│                                         │
│  ┌──────────┐  ┌──────────────────┐     │
│  │ App 列表 │  │ App 详情         │     │
│  │          │  │                  │     │
│  │ ○ TaskA  │  │ [Install] [Start]│     │
│  │ ● AgentF │  │ [Spawn Agent ▼] │     │
│  │ ○ Auth   │  │   - admin       │     │
│  │          │  │   - reviewer    │     │
│  └──────────┘  └──────────────────┘     │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ Running Agents                    │   │
│  │ agentforge:admin    ● running     │   │
│  │ taskarena:reviewer  ● running     │   │
│  │ taskarena:admin     ○ stopped     │   │
│  └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

Dashboard 本身也是一个 Socialware App (`app/dashboard/`)，执行与 `sw` CLI 相同的操作。

---

## 3. 操作过程

### 3.1 安装并使用一个 Socialware App

```
用户                    sw CLI / Dashboard              系统
 │                           │                           │
 │  sw install taskarena     │                           │
 │ ─────────────────────────>│                           │
 │                           │  读 app/taskarena/agent/  │
 │                           │──────────────────────────>│
 │                           │                           │
 │                           │  flow/ → agent/skills/    │
 │                           │  scope/ → agent/SOUL.md   │
 │                           │  role/ → agent/agents/    │
 │                           │  更新 registry.yaml       │
 │                           │  更新 .claude/skills/     │
 │                           │<──────────────────────────│
 │  ✓ installed              │                           │
 │<──────────────────────────│                           │
 │                           │                           │
 │  sw start taskarena       │                           │
 │ ─────────────────────────>│                           │
 │                           │  启动 app/taskarena/src/  │
 │                           │  (API :8001 + 前端 :3001) │
 │                           │<──────────────────────────│
 │  ✓ running on :8001       │                           │
 │<──────────────────────────│                           │
 │                           │                           │
 │  claude (或 sw dev)       │                           │
 │ ─────────────────────────>│                           │
 │                           │  启动 Claude Code         │
 │                           │  加载 .claude/skills/     │
 │                           │  → taskarena skills 可用  │
 │                           │                           │
 │  "帮我创建一个采购任务"     │                           │
 │ ─────────────────────────>│  Agent 调用 flow/create   │
 │                           │──────────────────────────>│
 │                           │  POST :8001/tasks         │
 │                           │<──────────────────────────│
 │  ✓ 任务 task-001 已创建   │                           │
 │<──────────────────────────│                           │
```

### 3.2 Spawn Subagent

```
用户                    sw CLI / Dashboard              系统
 │                           │                           │
 │  sw agent spawn           │                           │
 │    taskarena:reviewer     │                           │
 │ ─────────────────────────>│                           │
 │                           │  读 role/reviewer/SOUL.md │
 │                           │  加载所有 flow/ skills    │
 │                           │  组合:                    │
 │                           │    scope/SOUL.md          │
 │                           │    + role/reviewer/SOUL.md │
 │                           │    + flow/* skills        │
 │                           │                           │
 │                           │  通过 adapter 启动        │
 │                           │  (Claude/Codex/KimiCode)  │
 │                           │──────────────────────────>│
 │                           │                           │
 │  ✓ reviewer agent running │        ┌─────────┐       │
 │<──────────────────────────│        │Reviewer │       │
 │                           │        │ Agent   │       │
 │                           │        └────┬────┘       │
 │                           │             │             │
 │                           │    连接 taskarena API     │
 │                           │    (权限由 app 检查)      │
 │                           │             │             │
 │                           │        ┌────▼────┐       │
 │                           │        │TaskArena│       │
 │                           │        │  :8001  │       │
 │                           │        └─────────┘       │
```

### 3.3 跨 App 协作

```
┌───────────────┐         P2P Bus (Zenoh)        ┌───────────────┐
│   TaskArena   │                                 │  AgentForge   │
│               │                                 │               │
│  admin agent ─┼─── "需要一个 reviewer" ────────>│  admin agent  │
│               │                                 │       │       │
│               │                                 │  spawn reviewer│
│               │         reviewer agent  <───────┼───────┘       │
│               │              │                  │               │
│  ◄────────────┼──── 连接到 TaskArena ───────────┤               │
│               │              │                  │               │
│  review task  │◄─── 执行 review ────────────────┤               │
│               │                                 │               │
└───────────────┘                                 └───────────────┘

跨 App 协作通过四原语声明：
- TaskArena 的 flow/ 声明 "review 可委托外部"
- AgentForge 的 scope/ 声明 "可接受 spawn 请求"
- Agent 间通过 P2P Bus 通信，类似 IM
```

### 3.4 渐进生长 (P1→P5)

```
P1: 定义 Agent
    用户只有 Chat 框 + 最简 UI
    agent/ 只有 scope/SOUL.md + 一两个 flow/
    src/ 只有最小 API

        ▼ 用户发现需要更多操作

P2: 完善 Flow
    flow/ 增加更多 skill
    src/ 的 API + UI 对应增长 (Biz 层沉淀)

        ▼ 用户发现需要保证质量

P3: 完善 Commitment
    commitment/ 增加 eval 指标
    src/ 增加监控/提醒功能

        ▼ 用户发现需要更多参与者

P4: 扩大 Scope
    scope/SOUL.md 扩展能力声明
    flow/ 和 commitment/ 随之丰富

        ▼ 用户发现需要分工

P5: 扩充 Role
    role/ 增加新的 subagent 角色
    scope/ 重新划分，flow/ 重新编排
```

---

## 4. origin/main 代码拆分

当前 origin/main 的 `api/` + `app/` 拆分为独立的 Socialware Apps：

| origin/main | 拆分到 | 说明 |
|---|---|---|
| `api/auth.py`, `api/routers/auth.py` | `app/auth/src/` | 统一认证 app |
| `api/routers/rooms.py`, `api/models.py (Room)` | `app/dashboard/src/` | Workspace 管理 |
| `api/routers/agents.py`, `api/agent_bridge.py` | `app/taskarena/src/` | 任务+Agent 调用 |
| `api/models.py (AgentTask)` | `app/taskarena/src/` | 任务模型 |
| `app/` (Next.js) | 各 app/*/src/ | 前端按功能拆分 |

---

## 5. 软连接拓扑

```
app/taskarena/agent/flow/
        │
        │ sw install
        ▼
agent/skills/taskarena/  (symlink → ../../app/taskarena/agent/flow/)
        │
        │ sw install
        ▼
.claude/skills/taskarena/ (symlink → ../../agent/skills/taskarena/)
        │
        │ Claude Code 启动时
        ▼
    Claude Code 自动识别为可用 skill
```

两级软连接的原因：
- 第一级（agent/skills/）：agent 基础设施统一管理，adapters 从这里读取
- 第二级（.claude/skills/）：Claude Code 特定的 skill 目录

---

## 6. `sw` CLI 命令（过渡方案）

```bash
# App 生命周期
sw install <app>                  # 编译四原语 → agent/ 基础设施
sw uninstall <app>                # 移除注册和软连接
sw start <app>                    # 启动 app 服务 (API + 前端)
sw stop <app>                     # 停止 app 服务
sw list                           # 列出所有 app 及状态
sw status                         # 查看 app + agent 运行状态

# Agent 生命周期
sw agent spawn <app>:<role>       # 启动指定角色的 agent
sw agent spawn <app>              # 启动该 app 全部 role 的 agents
sw agent list                     # 列出运行中的 agents
sw agent stop <app>:<role>        # 停止指定 agent
sw agent stop --all               # 停止全部 agents

# 开发模式
sw dev                            # = claude，加载所有已安装 skills
```

最终这些命令会被 Dashboard App (`app/dashboard/`) 的 UI 替代。

---

## 7. 当前约束与假设

| 项目 | 当前状态 |
|------|---------|
| 部署模型 | 中心化 + 登录认证 |
| Agent 运行时 | Claude Code (agnostic，兼容 Codex/KimiCode) |
| Agent 通信 | 预留 P2P Bus (Zenoh)，当前本地直连 |
| App 权限检查 | 由 app 自身 API 层处理，不在 agent 基础设施层 |
| Workspace | 每个 app 独立管理 `.socialware-workspace/` |
