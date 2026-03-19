# Socialwares 仓库架构设计

> v3.0 — 2026-03-19
> 对齐 Socialware 开发指南 v0.5

## 一句话定义

Socialwares 是 Socialware App 的**脚手架模板**（对标 `mix phx.new`）。
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
├── app/                                      ← 前端 (Next.js: UI + Chat)
│
├── src/                                      ← 后端 (FastAPI: API + Agent SDK 启动)
│   └── start_agent.py                        ← 生产模式：App 后端调用 adapter 启动 agent
│
├── agent/                                    ← 四原语 + 工具链
│   ├── role/                                 ← §1 Who: Subagent 身份 + 权限
│   │   ├── admin/
│   │   │   └── SOUL.md                       ← admin 的身份、权限描述
│   │   └── reviewer/
│   │       └── SOUL.md
│   ├── scope/                                ← §4 Where: App 能力声明
│   │   └── SOUL.md                           ← 对内=边界，对外=公开描述
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
│   ├── start.sh                              ← 开发模式：统一启动入口
│   └── adapters/                             ← 平台适配
│       ├── base.py                           ← 公共接口
│       ├── claude/
│       │   ├── shell.sh                      ← Claude TUI + tmux (dev)
│       │   └── sdk.py                        ← Claude Agent SDK (prod)
│       ├── codex/
│       │   ├── shell.sh
│       │   └── sdk.py
│       └── kimicode/
│           └── sdk.py
│
├── .socialware/
│   └── workspace/                            ← 用户的 app 实例
│       ├── default/                          ← 默认 workspace (模板 copy)
│       │   └── .runtime/                     ← gitignored
│       │       ├── data/                     ← 共享数据 (Files/ + Sqlite/)
│       │       └── agents/                   ← per-role 实例
│       │           ├── admin/.claude/
│       │           └── reviewer/.claude/
│       └── {room-name}/                      ← 用户自建 workspace
│           └── {app-name}/
│               ├── src/
│               ├── agent/
│               └── .runtime/
│
├── .gitignore                                ← 排除 .runtime/
├── package.json
└── docs/
```

### 关键约定

| 约定 | 说明 |
|------|------|
| `app/` = 前端 | Next.js (UI + Chat 界面) |
| `src/` = 后端 | FastAPI (API + `start_agent.py`) |
| `agent/` = 四原语 + 工具链 | role/scope/commitment/flow + deploy + start + adapters |
| `.runtime/data/` | 共享数据，跨 role (Files/ + Sqlite/) |
| `.runtime/agents/` | per-role 隔离 (各有独立 .claude/) |
| 模板 vs 实例 | 根目录是模板，workspace/ 里是用户实例 |

---

## 2. 四原语

### 2.1 定义

```
  ┌─────────────────┐  ┌─────────────────┐
  │  §1 Role (Who)  │  │ §4 Scope (Where)│
  │                 │  │                 │
  │  agent/role/    │  │  agent/scope/   │
  │  每 role 一个    │  │  SOUL.md        │
  │  SOUL.md        │  │                 │
  │                 │  │  能力边界声明     │
  │  Subagent 身份  │  │  对内=边界       │
  │  + 权限描述     │  │  对外=公开描述    │
  ├─────────────────┤  ├─────────────────┤
  │ §3 Commitment   │  │  §2 Flow (How)  │
  │    (What)       │  │                 │
  │  agent/         │  │  agent/flow/    │
  │  commitment/    │  │  每 action 一个  │
  │  eval.yaml      │  │  SKILL.md       │
  │                 │  │  + scripts/     │
  │  Eval 指标      │  │                 │
  │  SLA 定义       │  │  = AutoService  │
  └─────────────────┘  └─────────────────┘
```

### 2.2 SwSim ↔ 目录 ↔ GitAgent/AutoService 映射

| SwSim 原语 | agent/ 目录 | 核心文件 | GitAgent | AutoService |
|---|---|---|---|---|
| **Role** (§1) | `role/{name}/` | `SOUL.md` | 子 agent 定义 | — |
| **Flow** (§2) | `flow/{action}/` | `SKILL.md` + `scripts/` | — | Skill 模式 |
| **Commitment** (§3) | `commitment/` | `eval.yaml` | — | Hook/eval |
| **Arena→Scope** (§4) | `scope/` | `SOUL.md` | Agent identity | — |

### 2.3 职责边界

| 谁管什么 | 在哪里 |
|----------|--------|
| **状态机** (哪个状态能转移到哪个状态) | `src/` — App 的 Biz 层 |
| **权限** (哪个 agent 能触发哪个 action) | `agent/role/` — SOUL.md 描述 |
| **怎么做** (action 的执行逻辑) | `agent/flow/` — Skill |
| **做到什么程度** (SLA、Eval 指标) | `agent/commitment/` — eval.yaml |
| **能力范围** (agent 能做什么、边界在哪) | `agent/scope/` — SOUL.md |

---

## 3. deploy.sh 编译机制

### 3.1 编译过程

`agent/deploy.sh` 读取四原语，为每个 role 生成独立 `$PROJECT_DIR`：

```
    agent/ (四原语)                    .runtime/ (编译产物)
    ┌──────────────────┐              ┌──────────────────────────┐
    │ role/             │              │ data/                    │
    │   admin/SOUL.md   │              │   Files/                 │
    │   reviewer/SOUL.md│  deploy.sh   │   Sqlite/                │
    │ scope/            │ ──────────>  ├──────────────────────────┤
    │   SOUL.md         │              │ agents/                  │
    │ commitment/       │              │   admin/                 │
    │   eval.yaml       │              │     .claude/             │
    │ flow/             │              │       skills/            │
    │   create_task/    │              │         create_task/ → …│
    │   review_task/    │              │         review_task/ → …│
    └──────────────────┘              │     SOUL.md              │
                                      │       (scope + admin)    │
                                      │   reviewer/              │
                                      │     .claude/             │
                                      │       skills/ → …        │
                                      │     SOUL.md              │
                                      │       (scope + reviewer) │
                                      └──────────────────────────┘
```

### 3.2 .runtime/ 内部结构

```
.runtime/                                 ← deploy.sh 生成 (gitignored)
├── data/                                 ← 共享数据 (跨 role)
│   ├── Files/                            ← 运行时文件
│   └── Sqlite/                           ← 持久化数据库
└── agents/                               ← per-role 实例
    ├── admin/                            ← admin 的 $PROJECT_DIR
    │   ├── .claude/
    │   │   ├── skills/                   ← 软连接自 agent/flow/
    │   │   ├── hooks/
    │   │   └── mcp.json
    │   └── SOUL.md                       ← 合并: scope/SOUL.md + role/admin/SOUL.md
    └── reviewer/                         ← reviewer 的 $PROJECT_DIR
        ├── .claude/
        │   ├── skills/
        │   ├── hooks/
        │   └── mcp.json
        └── SOUL.md                       ← 合并: scope/SOUL.md + role/reviewer/SOUL.md
```

### 3.3 deploy 触发时机

- 手动：`./agent/deploy.sh`
- 自动：`start.sh` 启动时检测 agent/ 是否有变更，有则自动 deploy

---

## 4. 启动机制

### 4.1 两个入口，各司其职

| | `agent/start.sh` | `src/start_agent.py` |
|---|---|---|
| **谁用** | 开发者手动执行 | App 后端代码调用 |
| **做什么** | Shell 入口，委托给 adapter | 用 Python SDK 程序化启动 |
| **场景** | 开发调试：本地跑 Claude TUI | 生产部署：App 启动时拉起 agent |
| **位于** | agent 工具链 | 后端代码 (Biz 层) |

```
开发模式:
  ./agent/start.sh --role admin
    → 检查 .runtime/ 是否最新 (不是则自动 deploy)
    → adapters/claude/shell.sh
    → Claude TUI 打开

生产模式:
  App 启动 (pnpm start)
    → src/ 后端启动
    → src/start_agent.py
    → adapters/claude/sdk.py
    → agent headless 进程运行
```

### 4.2 start.sh 用法

```bash
./agent/start.sh [options]

--role <name>[,name2]                 # 指定 role (默认: 全部)
--adapter <claude|codex|kimicode>     # 平台 (默认: claude)
--workspace <path>                    # workspace 路径 (默认: .socialware/workspace/default)
```

### 4.3 启动流程

```
  start.sh
     │
     ├── 1. 检查 .runtime/ 是否最新
     │      └── 不是 → 自动执行 deploy.sh
     │
     ├── 2. 根据 --adapter 选择平台
     │
     ├── 3. 根据 --role 启动
     │      ├── 单 role → adapters/{adapter}/shell.sh
     │      └── 多 role → tmux session，每 role 一个 pane
     │
     └── 4. 每个 agent 进程使用 --project-dir .runtime/agents/{role}/
```

### 4.4 多 role 启动

```
  ./agent/start.sh --role admin,reviewer

  ┌─ tmux session ──────────────────────────────────────┐
  │                                                      │
  │  pane 1: admin                pane 2: reviewer       │
  │  ┌──────────────────┐        ┌──────────────────┐   │
  │  │ PROJECT_DIR:     │        │ PROJECT_DIR:     │   │
  │  │ .runtime/agents/ │        │ .runtime/agents/ │   │
  │  │   admin/         │        │   reviewer/      │   │
  │  │                  │        │                  │   │
  │  │ SOUL.md:         │        │ SOUL.md:         │   │
  │  │ scope + admin    │        │ scope + reviewer │   │
  │  │                  │        │                  │   │
  │  │ skills: 全部     │        │ skills: 全部     │   │
  │  └────────┬─────────┘        └────────┬─────────┘   │
  │           │                           │              │
  │           └───── 都连同一个 App API ────┘              │
  │                       │                              │
  │                 ┌─────┴─────┐                        │
  │                 │ App API   │  ← App 检查权限         │
  │                 │ 共享 data/ │                        │
  │                 └───────────┘                        │
  └──────────────────────────────────────────────────────┘

  agent 隔离 (不同 SOUL.md, 不同 $PROJECT_DIR)
  数据共享 (.runtime/data/ 同一个 DB)
  权限由 App API 检查 (人 → agent → app)
```

### 4.5 adapter 内部

每个 adapter 接收 `project_dir` + `SOUL.md`，用各自平台的方式启动：

```
adapters/claude/shell.sh:
  claude --project-dir $project_dir --permission-mode bypassPermissions

adapters/claude/sdk.py:
  Agent(model=..., system_prompt=soul, project_dir=project_dir).run()

adapters/codex/shell.sh:
  codex --project-dir $project_dir
```

---

## 5. Workspace 与 Evolve 机制

### 5.1 Workspace 模型

每个 Workspace = 一个租户/分支。模板通过 git worktree 分化：

```
.socialware/workspace/
├── default/                      ← 主分支 (main)
│   ├── agent/                    ← 四原语 (可能与模板相同)
│   └── .runtime/
└── cinnox/                       ← 租户分支 (branch: workspace/cinnox)
    ├── agent/                    ← 可能有租户特定修改
    └── .runtime/                 ← 租户独立数据
```

### 5.2 Dashboard 操作

| 操作 | 说明 |
|------|------|
| **Create** | 新 branch + worktree + .runtime |
| **Delete** | 清理 worktree + .runtime |
| **Update** | merge / rebase from upstream (main) |

### 5.3 Evolve 机制

Evolve = 从运行数据中自动发现改进，回馈到四原语定义：

```
  Evolve 产出物路由:

  修改落在 .runtime/ 中？
  ├── YES → 租户特定适配，不触发 PR
  │         留在 Workspace DB，其他租户不受影响
  │
  └── NO → 修改落在 workspace worktree 中
            → 对 agent/ 四原语的修改
            → 自动触发 PR 回 main branch
            → main 合并后，所有 workspace merge/rebase 获得改进
```

---

## 6. 脚手架：create-my-socialware

类似 `mix phx.new` 或 `npx create-next-app`：

```bash
uv run create-my-socialware
```

```
┌─ create-my-socialware ─────────────────────────────┐
│                                                     │
│  ? Project name: .......... my-task-app             │
│  ? Description: ........... 任务管理 Socialware      │
│  ? Initial Role: .......... admin                   │
│  ? Flow strategy: ......... CRUD                    │
│                                                     │
│  执行:                                               │
│  1. Clone socialwares template repo                 │
│  2. 写入 agent/ 四原语初始配置                        │
│  3. 生成 scope/SOUL.md                               │
│  4. deploy → .runtime/                              │
│                                                     │
│  ✓ Created my-task-app at ./my-task-app             │
│  → cd my-task-app && pnpm start                     │
└─────────────────────────────────────────────────────┘
```

---

## 7. 渐进生长 (P1→P5→P0)

```
  P1 定义 Agent        P2 完善 Flow        P3 完善 Commitment
  ┌────────────┐      ┌────────────┐      ┌────────────┐
  │ scope/     │      │ flow/      │      │commitment/ │
  │ SOUL.md    │ ──>  │ 增加 skill │ ──>  │ 增加 eval  │
  │ role/ 1个  │      │ src/ API↑  │      │ src/ 监控↑ │
  │ flow/ 1-2个│      │ app/ UI↑   │      │            │
  └────────────┘      └────────────┘      └────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
  P4 扩大 Scope        P5 扩充 Role        P0 跨 App
  ┌────────────┐      ┌────────────┐      ┌────────────┐
  │ scope/     │      │ role/      │      │ 新建 App   │
  │ SOUL.md↑   │ ──>  │ 增加角色   │ ──>  │ 或 /zchat  │
  │ flow/ ↑    │      │ flow/ 不变 │      │ 连接已有   │
  │commitment/↑│      │ scope/ 重划│      │            │
  └────────────┘      └────────────┘      └────────────┘

  每次改进 materialize 为 Biz 层 (src/ API + app/ UI + DB) 增长
```

---

## 8. 跨 App 协作

### 8.1 三种交互模式

| # | 模式 | 说明 |
|---|------|------|
| 1 | **页面 / API** | HTTP 调用，和传统 App 无区别 |
| 2 | **/ask-agent** | 直接和 App 的 Agent 对话 |
| 3 | **/zchat** | Agent 间 P2P 直连 (Zenoh) |

### 8.2 跨 App 声明

通过四原语中的引用实现跨 App 委托和协作：

- **flow/** 中声明委托：action 可委托给外部 app 的某个 action
- **scope/** 中声明连接：允许哪些外部 agent 参与

### 8.3 通信拓扑

```
  ┌─ Workspace A ──────────┐     ┌─ Workspace B ──────────┐
  │  ┌───────┐ ┌─────────┐ │     │ ┌───────┐ ┌──────────┐ │
  │  │ admin │ │reviewer │ │     │ │ admin │ │ builder  │ │
  │  └───┬───┘ └────┬────┘ │     │ └───┬───┘ └────┬─────┘ │
  │      └─────┬────┘      │     │     └─────┬────┘       │
  │      ┌─────┴─────┐     │     │     ┌─────┴─────┐      │
  │      │ TaskArena │     │     │     │AgentForge │      │
  │      └───────────┘     │     │     └───────────┘      │
  └───────────┬────────────┘     └───────────┬────────────┘
              │                               │
              └───── P2P Bus (Zenoh) ─────────┘
                   Agent 间 IM 通信
```

- **Socialware 中心化托管**：App 代码 + 前端 + 后端 中心化
- **Agent 去中心化**：安装 Socialware → 绑定 agent → P2P 通信

---

## 9. origin/main 代码映射

| origin/main | 新位置 | 说明 |
|---|---|---|
| `api/` | `src/` | 重命名，后端保持 FastAPI |
| `app/` | `app/` | 不变，前端保持 Next.js |
| `agent/` (占位) | `agent/` | 替换为四原语 + 工具链 |
| `api/agent_bridge.py` | `src/start_agent.py` + `agent/adapters/` | 拆分为启动入口 + adapter |

---

## 10. 术语表

| 术语 | 定义 |
|------|------|
| **Socialware** | Agent 交互可视化的 Web 应用 |
| **Workspace** | 租户。独立部署实例 (= git worktree + .runtime) |
| **Room** | Workspace 内部组织/群组 |
| **Biz 层** | Agent 能力沉淀为 API + UI + DB |
| **四原语** | Role (Who) / Scope (Where) / Commitment (What) / Flow (How) |
| **SOUL.md** | Agent 能力声明。对内=Scope 边界，对外=公开描述 |
| **deploy** | 编译四原语 → .runtime/ (data/ 共享 + agents/ per-role 隔离) |
| **adapter** | 平台适配层 (Claude / Codex / KimiCode) |
| **.runtime/** | deploy 生成的运行时，始终 gitignored |
| **Evolve** | 从运行数据发现改进 → 回馈四原语 → PR 回 main |

---

## 11. 当前约束

| 项目 | 状态 |
|------|------|
| 部署模型 | 中心化 + 登录认证 |
| Agent 运行时 | Claude Code (agnostic，兼容 Codex/KimiCode) |
| Agent 通信 | 预留 P2P Bus (Zenoh)，当前本地 |
| App 权限检查 | App 自身 API 层 (人 → agent → app) |
| 状态机 | App Biz 层 (`src/`)，不在 agent/ 中 |
| Dashboard | 替代 CLI，本身也是 Socialware App |
