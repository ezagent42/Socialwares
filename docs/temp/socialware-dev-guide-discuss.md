# Socialware 开发指南

> **v0.4** · 基于 ZChat / Claude Code · Git-native

从 Agent 交互可视化到可编程组织：构建下一代协作应用的完整指南。

---

## 快速开始（Overview）

Socialware = **Agent 交互可视化**的 Web 应用。用户看到普通界面 + Chat 框，底层 Agent 驱动一切。

> **一句话理解**：传统 App 是 DB CRUD 可视化（`UI→API→DB`），Socialware 是 Agent 交互可视化（`UI→Chat→Agent`）。App 从对话中渐进生长，不是一次性设计完成。

### 5 步构建你的第一个 Socialware

| 步骤 | 操作 | 说明 | 命令 |
|------|------|------|------|
| **1** | 创建 Repo | App = Git Repo，包含 src/、agent/、.socialware/ | `git clone template && cd my-app` |
| **2** | 配置四原语 | 在 agent/ 下定义 Role/Scope/Commitment/Flow | `cd agent/flow && make install` |
| **3** | 启动 App | 同时启动前端+后端+Agent，浏览器访问 | `pnpm start` |
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
| **四原语** | = Role / Scope / Commitment / Flow。 |
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

### 架构拓扑

```
┌─ SOCIALWARE（中心化部署）──────────────────────────────────┐
│                                                           │
│  ┌─ App (Standard) ──┐       ┌─ Custom App (Workspace) ─┐│
│  │  ┌──────────────┐ │       │  ┌──────────────┐        ││
│  │  │      UI      │ │ wksp/ │  │      UI      │        ││
│  │  └──────────────┘ │ branch│  └──────────────┘        ││
│  │  ┌──────────────┐ │<----->│  ┌──────────────┐        ││
│  │  │     Chat     │ │       │  │     Chat     │        ││
│  │  └──────┬───────┘ │       │  └──────┬───────┘        ││
│  └─────────┼─────────┘       └─────────┼────────────────┘│
│            │                           │                  │
├────────────┼───────────────────────────┼──────────────────┤
│ ZCHAT      ▼         跨 App 协作       ▼    (Zenoh P2P)  │
│  ┌─────────────┐  <~ ~ ~ ~ ~ ~>  ┌─────────────┐        │
│  │   Agent     │     ┌──────┐    │   Agent     │        │
│  │(Claude Code)│<--->│  IM  │<-->│(Claude Code)│        │
│  └─────────────┘     └──────┘    └─────────────┘        │
│  ┌──────────┐                                            │
│  │ DB CRUD  │                                            │
│  └──────────┘                                            │
└──────────────────────────────────────────────────────────┘
```

### 关键特征

1. **App = UI + Chat + Agent**：Chat 是核心管道，Agent 驱动 UI 状态
2. **Workspace = Branch Divergence**：App 随业务分化 = git branch divergence
3. **ZChat**：Agent 间 P2P 通信层，跨 App 协作通道

---

## Ch.2 Socialware 的文件结构

### 核心理念

每个 Socialware App = 一个 **Git Repo**。代码+配置版本控制，`.runtime` gitignored。启动 = 前端+后端+Agent 一体。

### 整体架构

```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ GitAgent — Socialware App Repo ─ ─ ─ ─ ─ ─ ─ ─ ┐

  ┌─ Socialware Slot ──────────────────┐   ┌─ .runtime/ per-workspace ──┐
  │ .socialware/workspace/room-name    │   │                            │
  │                                    │   │  ┌──────────────────────┐  │
  │  ┌─────────────────────────────┐   │   │  │     Files/           │  │
  │  │ .runtime/ (Files + Sqlite)  │ - ┼ - ┼->│     Sqlite/          │  │
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
                    │
  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
    Socialware Dashboard — workspace CRUD (create/delete/update)
  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### 文件结构

```
my-socialware-app/                    ← Git Repo Root
├── src/                              ← 前端 + 后端
├── agent/                            ← 四原语 (见 Ch.3)
│   ├── role/                         ← Subagent + Makefile
│   ├── scope/                        ← SOUL.md + Makefile
│   ├── commitment/                   ← Eval Metrics + Makefile
│   └── flow/                         ← Skill + Makefile
├── .socialware/workspace/
│   ├── default/                      ← 默认 Workspace
│   │   └── ~~.runtime/~~             ← gitignored (Files/ + Sqlite/)
│   └── workspace-alpha/              ← 其他实例 (branch diverged)
│       └── ~~.runtime/~~             ← gitignored
└── .gitignore                        ← 排除所有 .runtime/
```

### Socialware Dashboard

当前核心功能围绕 Git workspace 管理实现：

| 操作 | 说明 |
|------|------|
| **Create** | 新 branch + worktree + .runtime |
| **Delete** | 清理 worktree + .runtime |
| **Update** | merge / rebase from upstream |

---

## Ch.3 Agent 启动方式

### 核心理念

Socialware Agent 有两种启动方式：**Shell 脚本**（开发调试，Claude TUI）和 **Python SDK**（生产部署，程序化控制）。两者共享同一套四原语配置，通过 `.runtime/` 实现动态编译和挂载。

> ℹ️ **deploy 机制**：`agents/deploy.sh` 可随时手动执行。start 脚本启动时也会自动检查 agents/ 四原语是否有变更——有更新则自动 deploy，确保 .runtime/ 始终最新。

### 启动架构

```
┌─ ─ ─ .socialware/workspace/room-name ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐

  ① deploy（手动执行 或 start 检测到变更后自动触发）

  ┌──────────────┐       ┌─────────────────────┐
  │ agents/ 四原语 │ ───> │   agents/deploy.sh   │
  │ role/ scope/ │       │ 编译四原语 → .runtime │     $PROJECT_DIR
  │ commit/ flow/│       └──────────┬──────────┘   ┌─────────────────┐
  └──────────────┘                  │               │ = .runtime/roleN│
                                    ▼               │ SDK --project-  │
  ┌──────────────────────────────────────────┐     │ dir 指定该 role │
  │ .runtime/ — deploy.sh 生成                │     │ 专属的 .claude/ │
  │ 每个 role 独立子目录：                      │     └─────────────────┘
  │ .claude/ (skills/hooks/mcp) + Files/ + Sqlite/│
  └──────┬──────────┬──────────┬─────────────┘
         │          │          │
    ┌────▼───┐ ┌────▼───┐ ┌───▼──┐
    │ role1/ │ │ role2/ │ │ ...  │
    └────────┘ └────────┘ └──────┘

  ② start（读取 .runtime/ 中对应 role 启动 Agent）

  ┌─ 方式 A：Shell 脚本 ────────┐  ┌─ 方式 B：Python SDK ──────────┐
  │ agents/start_claude.sh      │  │ src/start_agent.py            │
  │                             │  │ --project-dir .runtime/roleN  │
  │  ┌─────────┐ ┌───────────┐ │  │                               │
  │  │ 单 role │ │ 多 role   │ │  │  ┌─────────┐ ┌─────────────┐ │
  │  │ 直接启动 │ │ tmux 多   │ │  │  │ 单 role │ │  多 role    │ │
  │  │ Claude  │ │ 窗格，每   │ │  │  │ SDK 单  │ │  每 role    │ │
  │  │ TUI     │ │ role 一个  │ │  │  │ 进程    │ │  独立进程   │ │
  │  │         │ │ pane      │ │  │  │         │ │             │ │
  │  └─────────┘ └───────────┘ │  │  └─────────┘ └─────────────┘ │
  └─────────────────────────────┘  └───────────────────────────────┘

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### 方式 A：Shell 脚本启动

适合**开发调试**。通过 `agents/start_claude.sh` 启动 Claude Code TUI。

**单 role — 直接启动：**

```
┌──────────────────┐       ┌──────────────┐
│ start_claude.sh  │ ────> │  Claude TUI  │
│   --role role1   │       │  role1 环境   │
└──────────────────┘       └──────────────┘
```

```bash
./agents/start_claude.sh --role role1
```

**多 role — tmux 多窗格：**

```
                           ┌─ tmux session ──────────────┐
┌──────────────────┐  ┌──>│ pane 1: Claude TUI (role1)  │
│ start_claude.sh  │──┤   ├─────────────────────────────┤
│ --role role1,role2│  └──>│ pane 2: Claude TUI (role2)  │
└──────────────────┘       └─────────────────────────────┘
```

```bash
./agents/start_claude.sh --role role1,role2
```

### 方式 B：Python SDK 启动

适合**生产部署**。通过 `src/start_agent.py` 调用 Claude Agent SDK。

> ℹ️ **关于 `--project-dir`**：Claude Agent SDK 可通过此参数指定 `$PROJECT_DIR`（如 `.runtime/role1`），使 Agent 使用该 role 专属的 `.claude/`，而非用户全局或项目根目录的 .claude 文件夹。这是多 role 隔离的关键机制。

```bash
# 单 role
python src/start_agent.py \
  --role role1 \
  --project-dir .runtime/role1

# 多 role（内部为每个 role fork 独立进程）
python src/start_agent.py \
  --role role1,role2
# 各自使用 .runtime/roleN 作为 PROJECT_DIR
```

### .runtime/ 动态编译

`agents/deploy.sh` 读取 `agents/` 四原语配置，为每个 role **生成**独立子目录到 `.runtime/`。每个子目录是该 role 的完整 `$PROJECT_DIR`。

```
.runtime/                             ← deploy.sh 生成（gitignored）
├── role1/                            ← role1 的 $PROJECT_DIR
│   ├── .claude/                      ← skills/ hooks/ mcp/
│   ├── Files/                        ← 运行时文件
│   └── Sqlite/                       ← 持久化数据
├── role2/                            ← role2 的 $PROJECT_DIR
│   ├── .claude/                      ← skills/ hooks/ mcp/
│   ├── Files/
│   └── Sqlite/
└── ...                               ← 更多 role
```

> ⚠️ **deploy 触发时机**：① 手动执行 `./agents/deploy.sh`；② start 脚本启动时自动检查 agents/ 是否有变更，有更新则自动 deploy。无需记忆——start 会确保 .runtime/ 始终最新。

---

## Ch.4 Socialware 的渐进生长

### 核心理念

Socialware 从对话中**渐进生长**。焦点沿"由内而外"递进。每次改进 materialize 为 **Biz 层**（API + UI + DB）增长。

> ℹ️ **Phase vs Step**：本章 5 个 Phase = App 能力演进视角。Ch.5 的 3 个 Step = 开发团队里程碑。两者是同一过程的不同切面。

### Agent 配置四原语

```
  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  👤 Role   │  │  🌐 Scope  │  │📊Commitment│  │  ⚡ Flow   │
  │  Who       │  │  Where     │  │  What      │  │  How       │
  │  Subagent  │  │  SOUL.md   │  │  Eval Met. │  │  Skill     │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘
```

对应 `agent/` 目录下四个子文件夹，各有 `Makefile` 用于安装到对应位置（如 `.claude/skills/`）。

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
              创建新 Socialware / ZChat 连接已有
```

#### Phase 1：纯 Chat + 少量 UI

- **焦点** → Agent 四原语初始配置
- 用户几乎所有操作通过 Chat 完成，UI 只是辅助输入

#### Phase 2：完善 Flow — 把事情做对

- **焦点** → Flow（How）→ Skill
- 例：发现用户无法添加任务 → 新增 API + UI
- Flow 完善直接 materialize 为 Biz 层增长

#### Phase 3：完善 Commitment — 把事情做到位

- **焦点** → Commitment（What）→ Eval Metrics
- 例：无法及时提醒用户 → 增加邮件发送功能

#### Phase 4：扩大 Scope — 把事情做得更广

- **焦点** → Scope（Where）→ SOUL.md
- 例：通知扩展到团队成员

#### Phase 5：扩充 Role — 引入新角色

- **焦点** → Role（Who）→ Subagent
- 例：添加 Notifier 角色，配置专属四原语

#### Phase 0 ↩ 触达单体边界

当 Phase 5 仍无法满足需求：
1. **创建新 Socialware App** — 重新经历 Phase 1→5
2. **通过 ZChat 连接其他 Socialware** — 网络效应起点

---

## Ch.5 实战示例：TaskArena & AgentForge

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

在 Claude Code 中安装 Socialware 基础插件：

```bash
# 安装基础插件
/install ezagent/socialware

# 安装后，/socialware 命令可用
# 它是所有 Socialware App 共享的基础连接器
```

### Step 2：业务逻辑嵌入（≈ Phase 2→5）

`/socialware` 连接器访问 App 页面后，执行安装脚本，部署完整 bundle 到用户的 Agent 环境：

```bash
# 连接 TaskArena
/socialware connect https://taskarena.socialware.app

# 自动安装 bundle（skill + mcp + SOUL.md 等）
# 安装完成后 /taskarena 命令可用
```

Plugin 可引导用户建立定时任务：

```json
CronCreate {
  cron: "0 9 * * *",
  prompt: "/taskarena 提醒我 review 本日工作",
  recurring: true
}
```

AgentForge 的安装指引：

```bash
# 方式一：Git-native
cd .claude/ && git submodule add https://agentforge.app/agent-a

# 方式二：脚本安装
curl https://agentforge.app/agent-a/install | sh
```

### Step 3：与外部 Agent / 人类连接（≈ Phase 0）

```
┌──────────────┐                    ┌──────────────┐
│  TaskArena   │  <── /zchat ───>   │  AgentForge  │
│ /taskarena   │  Agent 间直接通信   │ /agentforge  │
│ CORE 逻辑    │                    │ Bundle 分发   │
└──────────────┘                    └──────────────┘
                 SOCIALWARE 网络
```

### 三种外部交互模式

| # | 模式 | 说明 |
|---|------|------|
| 1 | **页面 / API** | 和传统 App 无区别，HTTP 调用 |
| 2 | **/ask-agent** | 直接和 App 的 Agent 对话，获取智能响应 |
| 3 | **/zchat** | Agent 内部直连，编排 Subagent + 人类通信 |

### Skill 层级架构

```
  Enduser 侧输出                     Enduser 侧输出
  ┌──────────────┐                   ┌──────────────┐
  │ CORE 逻辑    │                   │ Bundle 输出   │
  │ CronCreate.. │                   │Skill+MCP+Hook│
  └──────┬───────┘                   └──────┬───────┘
         │                                  │
         ▼                                  ▼
  ┌──────────────┐                   ┌──────────────┐   ┌─────┐
  │ /taskarena   │                   │ /agentforge  │   │ ... │
  └──────┬───────┘                   └──────┬───────┘   └──┬──┘
         │                                  │              │
         └──────────────┬───────────────────┘              │
                        ▼                                  │
              ┌──────────────────┐                         │
              │   /socialware    │ <────────────────────────┘
              │  基础连接器       │
              │ 安装脚本 → bundle│
              └──────────────────┘
```

---

> **VERSION NOTE**：当前基于 v1 实现，默认 Agent 环境为 Claude Code。随着 Socialware 生态成熟，安装和交互方式将进一步标准化。
