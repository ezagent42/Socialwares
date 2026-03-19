# Socialware 开发指南

> **v0.5** · 基于 ZChat / Claude Code · Git-native

从 Agent 交互可视化到可编程组织：构建下一代协作应用的完整指南。

---

## 快速开始（Overview）

Socialware = **Agent 交互可视化**的 Web 应用。用户看到普通界面 + Chat 框，底层 Agent 驱动一切。

> **一句话理解**：传统 App 是 DB CRUD 可视化（`UI→API→DB`），Socialware 是 Agent 交互可视化（`UI→Chat→Agent`）。App 从对话中渐进生长，不是一次性设计完成。

### 5 步构建你的第一个 Socialware

| 步骤 | 操作 | 说明 | 命令 |
|------|------|------|------|
| **1** | 创建项目 | 脚手架生成完整 Repo | `uv run create-my-socialware` |
| **2** | 配置四原语 | 在 agent/ 下定义 Role/Scope/Commitment/Flow | `cd agent/flow && make install` |
| **3** | 启动 App | 同时启动前端+后端+Agent | `pnpm start` |
| **4** | 迭代生长 | Phase 1→5：Flow→Commitment→Scope→Role | — |
| **5** | 发布 & 互联 | 提供 /install 入口，跨 App 通过 /zchat 协作 | `/socialware connect https://your.app` |

### 核心架构一览

```
Agent 配置四原语                   渐进生长路径
┌──────────┬──────────┐           ● P1 → 定义 Agent
│ 👤 Role  │ 🌐 Scope │           ● P2 → 完善 Flow
│ Subagent │ SOUL.md  │           ● P3 → 完善 Commitment
├──────────┼──────────┤           ● P4 → 扩大 Scope
│📊Commit. │ ⚡ Flow  │           ● P5 → 扩充 Role
│Eval Metr.│  Skill   │           ↩ P0 → ZChat 互联
└──────────┴──────────┘
```

### 当前约束

| 部署模型 | Agent Runtime | Agent 通信 |
|----------|---------------|------------|
| 中心化 + 登录认证 | Claude Code (agnostic) | Zenoh P2P |

---

## Ch.0 前置概念与当前约束

### 术语表

| 术语 | 定义 |
|------|------|
| **Workspace** | = 租户。独立部署实例，独立 git worktree 和 .runtime。 |
| **Room** | = Workspace 内部组织/群组。可创建多个。 |
| **Biz 层** | = Agent 能力沉淀为 API endpoints、UI pages、DB schemas。 |
| **四原语** | = Role（Who）/ Scope（Where）/ Commitment（What）/ Flow（How）。 |
| **SOUL.md** | = Agent 能力声明。对内=Scope 边界，对外=公开描述供其他 Agent 读取。 |

### 部署模型

> ⚠️ **当前阶段**：Socialware 是**中心化部署**的 Web 应用，标准登录认证。后端 Agent 间通过 Zenoh P2P 通信。

- **前端 + 后端**：中心化托管（登录、认证、subdomain 路由）
- **Agent 间通信**：Zenoh P2P，低延迟灵活拓扑
- 未来可能探索 local-first，但当前中心化在认证、SOUL.md 可发现性、插件安装链路等方面优势明确

### Agent 运行环境

设计上 **Agent-runtime agnostic**，当前默认 **Claude Code**。兼容 Codex CLI、Gemini CLI。

---

## Ch.1 Socialware 的用户旅程

### 核心理念

用户看到普通 Web 应用 + Chat 框连接 Agent。应用 = Agent 交互的可视化投影。

### 传统 App vs Socialware

```
┌─────────────────────────────┐  ┌─────────────────────────────┐
│       TRADITIONAL APP       │  │       SOCIALWARE APP        │
├─────────────────────────────┤  ├─────────────────────────────┤
│  UI → API → DB CRUD        │  │  UI → Chat → Agent ↔ ...   │
│                             │  │                             │
│  数据库 CRUD 可视化           │  │  Agent 交互可视化            │
│  逻辑静态                    │  │  逻辑动态生长                 │
└─────────────────────────────┘  └─────────────────────────────┘
```

### 关键特征

1. **App = UI + Chat + Agent**：Chat 是核心管道，Agent 驱动 UI 状态
2. **Workspace = Branch Divergence**：App 随业务分化 = git branch divergence
3. **ZChat**：Agent 间 P2P 通信层，跨 App 协作通道

---

## Ch.2 Socialware 的文件结构

### 核心理念

每个 Socialware App = 一个 **Git Repo**。前端（`app/`）与后端（`src/`）分离，Agent 配置（`agent/`）独立管理，运行时状态（`.runtime`）gitignored。启动 = 前端 + 后端 + Agent 一体。

### 文件结构

```
my-socialware-app/                    ← Git Repo Root
├── app/                              ← 前端（UI + Chat 界面）
├── src/                              ← 后端（API + Agent 启动脚本）
│   └── start_agent.py                ← Python SDK 启动入口
├── agent/                            ← Agent 四原语 + 运行脚本
│   ├── role/                         ← Subagent 定义 + Makefile
│   ├── scope/                        ← SOUL.md + Makefile
│   ├── commitment/                   ← Eval Metrics + Makefile
│   ├── flow/                         ← Skill + Makefile
│   ├── start_claude.sh               ← Shell 启动入口
│   └── deploy.sh                     ← 四原语编译部署
├── .socialware/workspace/
│   ├── default/                      ← 默认 Workspace
│   │   └── ~~.runtime/~~             ← gitignored (data/ + agents/)
│   └── workspace-alpha/              ← 其他实例 (branch diverged)
│       └── ~~.runtime/~~             ← gitignored (data/ + agents/)
├── package.json
└── .gitignore                        ← 排除所有 .runtime/
```

### 使用 create-my-socialware 创建项目

类似 `npx create-next-app` 或 Elixir 的 `mix phx.new`，Socialware 提供脚手架工具 **`create-my-socialware`** 用于创建新项目：

```bash
uv run create-my-socialware
```

交互式流程：

```
┌─ create-my-socialware ───────────────────────────────────────┐
│                                                              │
│  ? Project name: .......... autoservice                      │
│  ? Description: ........... 智能客服与营销机器人               │
│  ? Initial Role: .......... marketing                        │
│  ? Flow strategy: ......... HEAR                             │
│  ? Commitment metric: ..... 5-star rating                    │
│                                                              │
│  ┌─ 执行步骤 ─────────────────────────────────────────────┐  │
│  │ 1. Clone socialware template repo                      │  │
│  │ 2. 写入 agent/role/、agent/scope/、agent/flow/ 等配置   │  │
│  │ 3. 生成 SOUL.md                                        │  │
│  │ 4. 设置 git remote 为用户指定的 URL                     │  │
│  │ 5. 初始 deploy → 生成 .runtime/                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ✓ Created autoservice at ./autoservice                      │
│  → cd autoservice && pnpm start                              │
└──────────────────────────────────────────────────────────────┘
```

### 整体架构

```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ GitAgent — Socialware App Repo ─ ─ ─ ─ ─ ─ ─ ─ ┐

  ┌─ Socialware Slot ──────────────────┐   ┌─ .runtime/ per-workspace ──┐
  │ .socialware/workspace/room-name    │   │                            │
  │                                    │   │  ┌──────────────────────┐  │
  │  ┌─────────────────────────────┐   │   │  │ data/  (Files+Sqlite)│  │
  │  │ .runtime/ (data + agents)   │ - ┼ - ┼->│ agents/(role1,role2) │  │
  │  └─────────────────────────────┘   │   │  └──────────────────────┘  │
  │  ↑ gitignored                      │   │  gitignored — per-wksp    │
  │                                    │   └────────────────────────────┘
  │  ┌─────────────────────────────┐   │
  │  │ .gitignore 以外的内容        │   │
  │  └──────────────┬──────────────┘   │
  │                 │ worktree         │
  └─────────────────┼──────────────────┘
                    │
       ┌────────────┼────────────────┐
       ▼                             ▼
  ┌──────────────┐  ┌────────────────────────┐
  │Socialware.app│  │workspace.Socialware.app│
  │ (模板主应用)  │  │   (Workspace 实例)      │
  └──────────────┘  └────────────────────────┘

  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
    Socialware Dashboard — workspace CRUD (create/delete/update)
  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### Socialware Dashboard

| 操作 | 说明 |
|------|------|
| **Create** | 新 branch + worktree + .runtime |
| **Delete** | 清理 worktree + .runtime |
| **Update** | merge / rebase from upstream |

---

## Ch.3 Agent 启动方式

### 核心理念

两种启动方式：**Shell 脚本**（开发调试，Claude TUI）和 **Python SDK**（生产部署，程序化控制）。两者共享同一套四原语配置，通过 `.runtime/` 实现动态编译和挂载。

> ℹ️ **deploy 机制**：`agent/deploy.sh` 可随时手动执行。start 脚本启动时自动检查变更——有更新则自动 deploy。

### 启动架构

```
┌─ ─ ─ .socialware/workspace/room-name ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐

  ① deploy（手动执行 或 start 检测到变更后自动触发）

  ┌──────────────┐       ┌─────────────────────┐
  │ agent/ 四原语 │ ───> │   agent/deploy.sh   │
  │ role/ scope/ │       │ 编译四原语 → .runtime │     $PROJECT_DIR
  │ commit/ flow/│       └──────────┬──────────┘   ┌──────────────────────┐
  └──────────────┘                  │               │= .runtime/agents/    │
                                    ▼               │  roleN               │
  ┌──────────────────────────────────────────────┐ │ SDK --project-dir    │
  │ .runtime/ — deploy.sh 生成                    │ │ 指定该 role 的       │
  │ data/    → Files/ + Sqlite/ (Workspace DB)   │ │ 专属 .claude/        │
  │ agents/  → 每个 role 独立子目录 (.claude/)    │ └──────────────────────┘
  └──────┬──────────┬──────────┬─────────────────┘
         │          │          │
    ┌────▼───┐ ┌────▼───┐ ┌───▼──┐
    │ role1/ │ │ role2/ │ │ ...  │  ← .runtime/agents/ 下
    └────────┘ └────────┘ └──────┘

  ② start（读取 .runtime/ 中对应 role 启动 Agent）

  ┌─ 方式 A：Shell 脚本 ────────┐  ┌─ 方式 B：Python SDK ──────────┐
  │ agent/start_claude.sh      │  │ src/start_agent.py            │
  │                             │  │ --project-dir .runtime/agents/roleN  │
  │  ┌─────────┐ ┌───────────┐ │  │                               │
  │  │ 单 role │ │ 多 role   │ │  │  ┌─────────┐ ┌─────────────┐ │
  │  │ 直接启动 │ │ tmux 多   │ │  │  │ 单 role │ │  多 role    │ │
  │  │ Claude  │ │ 窗格，每   │ │  │  │ SDK 单  │ │  每 role    │ │
  │  │ TUI     │ │ role 一个  │ │  │  │ 进程    │ │  独立进程   │ │
  │  └─────────┘ └───────────┘ │  │  └─────────┘ └─────────────┘ │
  └─────────────────────────────┘  └───────────────────────────────┘

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### 方式 A：Shell 脚本启动

```bash
# 单 role — 直接启动 Claude TUI
./agent/start_claude.sh --role role1

# 多 role — 自动创建 tmux session，每 role 一个 pane
./agent/start_claude.sh --role role1,role2
```

### 方式 B：Python SDK 启动

> ℹ️ **`--project-dir`**：指定 `$PROJECT_DIR`（如 `.runtime/agents/role1`），使 Agent 使用该 role 专属的 `.claude/`，而非全局 .claude。这是多 role 隔离的关键机制。

```bash
# 单 role
python src/start_agent.py --role role1 --project-dir .runtime/agents/role1

# 多 role（内部为每个 role fork 独立进程）
python src/start_agent.py --role role1,role2
```

### .runtime/ 动态编译

```
.runtime/                             ← deploy.sh 生成（gitignored）
├── data/                             ← 运行时数据（Workspace DB）
│   ├── Files/                        ← 运行时文件
│   └── Sqlite/                       ← 持久化数据库
└── agents/                           ← deploy.sh 编译产物（per-role 实例）
    ├── role1/                        ← role1 的 $PROJECT_DIR
    │   └── .claude/                  ← skills/ hooks/ mcp/
    ├── role2/                        ← role2 的 $PROJECT_DIR
    │   └── .claude/
    └── ...
```

> ⚠️ **deploy 触发**：① 手动 `./agent/deploy.sh`；② start 自动检查变更后触发。start 会确保 .runtime/ 始终最新。

---

## Ch.4 Socialware 的渐进生长

### 核心理念

Socialware 从对话中**渐进生长**。焦点沿"由内而外"递进。每次改进 materialize 为 **Biz 层**（API + UI + DB）增长。

> ℹ️ **Phase vs Step**：Phase = App 能力演进视角。Step = 开发团队里程碑。同一过程不同切面。

### Agent 配置四原语

```
  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  👤 Role   │  │  🌐 Scope  │  │📊Commitment│  │  ⚡ Flow   │
  │  Who       │  │  Where     │  │  What      │  │  How       │
  │  Subagent  │  │  SOUL.md   │  │  Eval Met. │  │  Skill     │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘
```

### 五阶段生长模型

```
  Phase 1       Phase 2       Phase 3       Phase 4       Phase 5
  ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐
  │Agent │────>│ Flow │────>│Commit│────>│Scope │────>│ Role │
  │定义   │     │做对   │     │做到位 │     │做更广 │     │加角色 │
  └──────┘     └──────┘     └──────┘     └──────┘     └──┬───┘
      ▲                                                   │
      │              Phase 0 ↩ 触达单体边界                 │
      └───────────────────────────────────────────────────┘
```

#### Phase 1 ~ 5 & Phase 0

| Phase | 焦点 | 示例 |
|-------|------|------|
| **1** 纯 Chat + 少量 UI | Agent 四原语初始配置 | 所有操作通过 Chat 完成 |
| **2** 完善 Flow | Flow → Skill | 无法添加任务 → 新增 API + UI |
| **3** 完善 Commitment | Commitment → Eval Metrics | 无法及时提醒 → 增加邮件功能 |
| **4** 扩大 Scope | Scope → SOUL.md | 通知扩展到团队成员 |
| **5** 扩充 Role | Role → Subagent | 添加 Notifier 角色 |
| **0** ↩ 触达边界 | 创建新 Socialware 或 ZChat 连接 | 网络效应起点 |

---

## Ch.5 Evolve 机制：租户适配与持续优化

### 核心问题

当 Socialware 部署了多个 Workspace（租户），两个关键挑战浮现：

1. **数据/context 分离**：不同租户依赖不同的客户数据和业务上下文，如何与 Agent 定义（四原语）解耦？
2. **差异化优化**：不同租户的优化重点不同，如何让每个租户有自己的 evolve 策略，同时保持与主库的同步？

### 数据架构：Agent 定义 vs 租户数据

```
┌─ autoservice/ (主库 Repo) ──────────────────────────────────────────────┐
│                                                                         │
│  agent/                           ← Git-managed（四原语定义）             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐               │
│  │   Role   │ │  Scope   │ │  Commitment  │ │   Flow   │               │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────┘               │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  .socialware/workspace/                                                 │
│                                                                         │
│  ┌─ default ────────────────────┐  ┌─ cinnox ────────────────────────┐ │
│  │                              │  │                                  │ │
│  │  四原语 (worktree from main) │  │  四原语 (worktree from branch)   │ │
│  │  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐│  │  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │ │
│  │    .runtime/  (gitignored)  ││  │    .runtime/  (gitignored)     │ │
│  │  │ ├── data/               │││  │  │ ├── data/                 │ │ │
│  │    │   ├── Files/           ││  │    │   ├── Files/              │ │
│  │  │ │   └── Sqlite/ ←WkspDB│││  │  │ │   └── Sqlite/ ←WkspDB  │ │ │
│  │    └── agents/              ││  │    └── agents/                 │ │
│  │  │     └── role1/.claude/  │││  │  │     └── role1/.claude/    │ │ │
│  │  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘│  │  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │ │
│  │                              │  │                                  │ │
│  │  Workspace DB (data/) 存放：  │  │  Workspace DB (data/) 存放：      │ │
│  │  · 客户对话历史               │  │  · CINNOX 客户数据                │ │
│  │  · 通用营销数据               │  │  · 区域化服务配置                  │ │
│  │  · Eval 评估结果              │  │  · Eval 评估结果                  │ │
│  └──────────────────────────────┘  └──────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**分离原则**：

| 层面 | 存储位置 | 生命周期 |
|------|----------|----------|
| **Agent 定义**（四原语） | Git worktree（可 branch diverge） | 版本控制，可 merge 回 main |
| **Agent 实例**（编译产物） | `.runtime/agents/` per-role .claude/ | deploy.sh 生成，gitignored |
| **租户数据/context** | `.runtime/data/`（Sqlite + Files） | 运行时，gitignored，per-workspace 隔离 |

### Evolve Skill：差异化优化

每个 Socialware 有一个默认的 evolve skill（`/{name}: evolve`），租户可以在此基础上创建自己的 evolve skill。

#### 示例：AutoService（客服/营销机器人）

```
┌─ autoservice (主库 main branch) ──────────────────────────────────────┐
│                                                                       │
│  Role: marketing                                                      │
│  Commitment: 5-star 评价                                              │
│  Flow: HEAR 策略                                                      │
│                                                                       │
│  /autoservice: evolve                                                 │
│  · 分析所有 workspace 的 Eval Metrics                                  │
│  · 发现通用改进 → 直接修改 agent/ 四原语 → 提交 main branch            │
│  · 例：HEAR 策略 → 优化为 SPIN 策略（所有租户受益）                     │
│                                                                       │
└────────┬──────────────────────────────────────────────────────────────┘
         │  git branch / worktree
         ▼
┌─ cinnox workspace (branch: workspace/cinnox) ────────────────────────┐
│                                                                       │
│  Role: marketing（继承自 main）                                       │
│  Commitment: 5-star 评价（继承自 main）                               │
│  Flow: SPIN 策略（继承自 main）+ "首先明确客户需要的 region"（本地新增）  │
│                                                                       │
│  /cinnox: evolve                                                      │
│  · 分析 CINNOX 的 Eval Metrics + Workspace DB 中的客户数据             │
│  · 租户特定适配 → 修改 .runtime/ 中的内容 → 不触发 PR                  │
│  · 通用改进 → 修改 workspace/cinnox worktree → 自动触发 PR 回 main     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Evolve 产出物的路由规则

evolve 的结果按**修改位置**自动决定同步策略：

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Evolve 产出物路由                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  修改落在 .runtime/ 中？                                             │
│  ├── YES → 租户特定适配，不触发 PR                                   │
│  │         例：调整 .runtime/ 中的 prompt 参数、                     │
│  │         添加租户专属的数据处理规则                                  │
│  │         · 留在 Workspace DB                                      │
│  │         · 其他租户不受影响                                        │
│  │                                                                  │
│  └── NO → 修改落在 workspace worktree 中                            │
│           ├── 这是对 agent/ 四原语的修改                             │
│           ├── 自动触发 PR 回 main branch                            │
│           ├── 例：发现 SPIN 策略比 HEAR 更好                        │
│           └── main 合并后，所有 workspace 通过                      │
│               merge/rebase 获得此改进                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> ℹ️ **关键设计**：PR 是自动触发的。当 evolve skill 修改了 worktree 中的文件（而非 .runtime/），系统检测到 git 变更后自动创建 PR。开发者 review 后合并到 main，所有 workspace 通过 Dashboard 的 Update 操作（merge/rebase）获得改进。

### Evolve 流程图

```
                    /autoservice: evolve              /cinnox: evolve
                    (在 main 上运行)                   (在 cinnox branch 上运行)
                           │                                  │
                           ▼                                  ▼
                    ┌──────────────┐                   ┌──────────────┐
                    │ 分析所有租户  │                   │ 分析 CINNOX  │
                    │ Eval Metrics │                   │ Eval + 客户DB│
                    └──────┬───────┘                   └──────┬───────┘
                           │                                  │
                           ▼                                  ▼
                    ┌──────────────┐                   ┌──────────────┐
                    │  修改 agent/ │                   │  修改落在哪？ │
                    │  四原语定义   │                   └──────┬───────┘
                    └──────┬───────┘                     ┌────┴────┐
                           │                             ▼         ▼
                           ▼                      .runtime/   worktree/
                    ┌──────────────┐               (不触发PR)  (自动触发PR)
                    │ 提交 main    │                    │         │
                    │ branch       │                    │         ▼
                    └──────┬───────┘                    │   ┌──────────┐
                           │                            │   │ PR → main│
                           ▼                            │   └──────────┘
                    ┌──────────────┐                    │
                    │ 所有 workspace│                    │
                    │ merge/rebase │<───────────────────┘
                    │ 获得改进      │   (main 合并后下发)
                    └──────────────┘
```

### 具体示例：AutoService 的 evolve 结果

**AutoService 默认优化（`/autoservice: evolve`）：**

```
优化前：                        优化后：
┌──────────────────────┐      ┌──────────────────────┐
│ Role: marketing      │      │ Role: marketing      │   (不变)
│ Commitment: 5-star   │      │ Commitment: 5-star   │   (不变)
│ Flow: HEAR 策略  ────┼─ ──> │ Flow: SPIN 策略  ✅  │   (改进)
└──────────────────────┘      └──────────────────────┘
                              → 提交 main，所有租户受益
```

**CINNOX 租户优化（`/cinnox: evolve`）：**

```
继承 main 的 SPIN 策略后：     优化后：
┌──────────────────────┐      ┌───────────────────────────────────┐
│ Role: marketing      │      │ Role: marketing                   │ (不变)
│ Commitment: 5-star   │      │ Commitment: 5-star                │ (不变)
│ Flow: SPIN 策略      │      │ Flow: SPIN 策略                   │ (继承)
│                      │──> │ Flow: 首先明确客户需要的 region ✅  │ (新增)
└──────────────────────┘      └───────────────────────────────────┘
                              修改落在 worktree → 自动 PR 回 main？
                              → 如果是通用改进：YES
                              → 如果是 CINNOX 特定：修改 .runtime/ 即可
```

### 创建新 Workspace 的 evolve 流程

```bash
# 方式一：从现有 Socialware 的 Dashboard 创建
# Dashboard → Create → 输入 workspace 名称 → 自动创建 branch + worktree

# 方式二：通过 CLI
/autoservice: create --workspace cinnox

# 创建后，开发者可以为 cinnox 配置专属的 evolve skill：
# agent/flow/ 下新增 cinnox-specific 的 skill 文件
# 或在 .runtime/ 中调整 prompt 参数
```

---

## Ch.6 实战示例：TaskArena & AgentForge

### 核心理念

所有 API 围绕 Agent 调用建立——人类看到的每个 API/UI 都是某个 Skill 内部调用的 API。

> ℹ️ **Step ↔ Phase 映射**：Step 1 ≈ Phase 1 | Step 2 ≈ Phase 2→5 | Step 3 ≈ Phase 0 回环

### 两个示例 App

**TaskArena — 任务管理**

```
┌─ taskarena.socialware.app ──────────────────┐
│ ⬡ 安装 Socialware 插件              /install │
├─────────────────────────────────────────────┤
│ 📋 My Tasks                                 │
│                                             │
│  [ ] 完成 Q2 季度报告初稿             [P0]   │
│  [ ] Review PR #142                  [P1]   │
│  [✓] ~~更新 SOUL.md~~               [Done]  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ 建议我优先处理的任务...              [→] │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
  业务逻辑 CORE：Capture → Clarify → Organize → Reflect → Engage
```

**AgentForge — Agent 创建与分发**

```
┌─ agentforge.socialware.app ─────────────────┐
│ ⬡ 安装 Socialware 插件              /install │
├─────────────────────────────────────────────┤
│ 🤖 Available Agents                         │
│  ┌──────────────┐  ┌──────────────┐         │
│  │📋 TaskArena  │  │📅 Calendar   │         │
│  │  [CORE][cron]│  │  [gcal][sync]│         │
│  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐         │
│  │📊 Analytics  │  │✍️ Writer     │         │
│  │  [SQL]       │  │  [draft]     │         │
│  └──────────────┘  └──────────────┘         │
│ ┌─────────────────────────────────────────┐ │
│ │ 我想要一个管理日程的 Agent...        [→] │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
  业务逻辑：创建完整 bundle（Skill + MCP + Hook + py/bin）
```

### Step 1：初步 UI + Agent 上线（≈ Phase 1）

```bash
/install ezagent/socialware      # /socialware 命令可用
```

### Step 2：业务逻辑嵌入（≈ Phase 2→5）

```bash
/socialware connect https://taskarena.socialware.app
# 自动安装 bundle → /taskarena 命令可用
```

### Step 3：与外部 Agent / 人类连接（≈ Phase 0）

```
┌──────────────┐                    ┌──────────────┐
│  TaskArena   │  <── /zchat ───>   │  AgentForge  │
│ /taskarena   │  Agent 间直接通信   │ /agentforge  │
└──────────────┘                    └──────────────┘
```

### 三种外部交互模式

| # | 模式 | 说明 |
|---|------|------|
| 1 | **页面 / API** | 和传统 App 无区别，HTTP 调用 |
| 2 | **/ask-agent** | 直接和 App 的 Agent 对话 |
| 3 | **/zchat** | Agent 内部直连，编排 Subagent + 人类通信 |

---

> **VERSION NOTE**：v0.5。默认 Agent 环境为 Claude Code。随着 Socialware 生态成熟，安装和交互方式将进一步标准化。
