# AgentForge CMS 内容管理系统设计

> 版本: v1.2 | 日期: 2026-03-31

## 1. 概述

AgentForge 是一个 **Agent 创建与管理平台**，采用 CMS（内容管理系统）模式，让用户通过 Chat 对话来创建、编辑、管理 Agent。

### 1.1 Agent vs App（四原语）的区别

| 概念 | 层级 | 包含 |
|------|------|------|
| **Agent** | 个体 | 身份描述 (role.md) + 技能 (skills) + 模型选择 |
| **App (Workspace)** | 应用 | 四原语 (Scope + Role + Flow + Commitment) + 后端 + 前端 |

**四原语是 App 级别的概念，不是 Agent 级别的。** 在 Socialware 框架中：
- `scope.md` — App 的能力边界
- `commitment.yaml` — App 的质量标准（由 evolver 评估用）
- `flow.yaml` — App 的操作注册表
- `role/*.md` — Agent 在 App 中的身份定义

**AgentForge 管理的核心对象是 Agent（不是 App），Agent 的定义是 model 无关的：**

```
Agent = {
  name: "code-review",          ← 名称
  role_md: "# Code Reviewer\n  ← 身份描述（你是谁、做什么、怎么回复）
            你是一个代码审查者...",
  skills: [                     ← 技能列表（可选）
    { name: "review_diff", skill_md: "..." },
    { name: "check_security", skill_md: "..." },
  ],
}
```

**Agent 定义不包含 model — 同一个 Agent 可以运行在任何平台上。** 导出时用户选择目标格式：

```
导出时用户选择格式:
  → gitagent     — GitAgent 标准 (agent.yaml + SOUL.md + skills/)，可再导出到任意平台
  → claude-code  — CLAUDE.md + .claude/skills/，直接在 Claude Code 中使用
  → codex        — AGENTS.md + .agents/skills/，直接在 Codex 中使用
  → cursor       — .cursor/rules，直接在 Cursor 中使用
  → socialwares  — 四原语 + Makefile，通过 make deploy + make start 使用
```

参考标准: [GitAgent](https://github.com/open-gitagent/gitagent) — 框架无关的 git-native Agent 定义标准。

**导出通过 Adapter 模式实现：**
```
Agent (DB)
    │
    ├── GitAgentAdapter    → agent.yaml + SOUL.md + skills/
    ├── ClaudeCodeAdapter  → CLAUDE.md + .claude/skills/
    ├── CodexAdapter       → AGENTS.md + .agents/skills/
    ├── CursorAdapter      → .cursor/rules
    └── SocialwaresAdapter → agent/ 四原语 + Makefile
```

每个 Adapter 从统一的 Agent 数据 (role_md + skills) 生成平台特定的文件。

**类比 CMS：**

| CMS 概念 | AgentForge 对应 |
|----------|----------------|
| 文章/页面 | Agent 定义（身份 + 技能） |
| 媒体库/组件市场 | Skill 搜索与导入（find_skill — 本地/内建/GitAgent Registry/URL） |
| 发布/导出 | 多格式导出（GitAgent / Claude Code / Codex / Cursor / Socialwares） |
| 导入 | 多格式导入（自动检测格式） |

**核心原则：用户永远在和 AgentForge 的 Agent 对话，Agent 是唯一的操作中介。**

---

## 2. 系统架构

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js) — 单页面             │
│                                                           │
│  ┌──┬──────────────┬──────────────────────────────────┐   │
│  │  │  Dashboard   │       Chat Terminal               │   │
│  │侧│              │                                  │   │
│  │边│  Agent Card  │  消息列表 + StructuredBlock 渲染   │   │
│  │栏│  列表        │  命令面板 (输入时弹出)             │   │
│  │  │  (entities)  │  输入框 + Send                    │   │
│  │☀ │              │                                  │   │
│  │👤│              │                                  │   │
│  └──┴──────────────┴──────────────────────────────────┘   │
│                                                           │
│                   Chat Store (zustand 共享状态)             │
│                         │                                 │
│                   SSE (POST /api/chat/send)                │
└─────────────────────────┼─────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────┐
│                  BACKEND (FastAPI)                     │
│                         │                            │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │           Auth Layer (GitHub OAuth)             │  │
│  │  登录/回调/Session 管理/用户数据隔离              │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │                            │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │           HTTP Layer                            │  │
│  │  POST /api/chat/send    ← 用户发消息            │  │
│  │  GET  /api/chat/stream  ← SSE 接收 Agent 响应   │  │
│  │  GET  /health                                   │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │                            │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │       Session Manager → Adapter Layer           │  │
│  │       (复用已有 Claude/Codex/Kimi adapter)       │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │ Agent skill 内部调用        │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │       Business Layer (Agent 配置管理)            │  │
│  │  agent_crud / role_crud / skill_crud            │  │
│  │  scope_crud / commitment_crud / export          │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │                            │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │       Database (SQLite)                         │  │
│  │  users / agents / roles / skills / ...          │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入: "帮我创建一个 task-manager Agent"
    │
    ▼
Chat Panel ──POST /api/chat/send──▶ Backend
    │                                  │
    │                          Auth 验证 (user_id)
    │                                  │
    │                          Session Manager
    │                                  │
    │                          Adapter Layer
    │                          (Claude SDK)
    │                                  │
    │                          Agent 分析意图
    │                          调用 manage_agent skill
    │                                  │
    │                          skill 调用 agent_crud.create()
    │                          (绑定当前 user_id)
    │                                  │
    │                          写入 SQLite
    │                                  │
    │                          返回结构化数据:
    │                          {
    │                            type: "agent",
    │                            action: "created",
    │                            data: { name: "task-manager", ... }
    │                          }
    │                                  │
    ◀──────────SSE stream──────────────┘
    │
    ▼
Chat Store 保存结构化数据
    │
    ├──▶ Chat Panel: 显示消息 "已创建 Agent: task-manager"
    │                + 内联渲染 agent_card
    │
    └──▶ Dashboard 区域: 自动出现 task-manager 的 Card
```

### 2.3 双交互模式

用户有两种方式与 Agent 交互：**Chat 输入** 和 **UI 操作**。两者最终都走同一条通道（POST /api/chat/send → Agent → SSE 响应）。

```
┌──────────────────────────────────────────────────────┐
│                     用户交互                          │
│                                                      │
│   模式 A: Chat 输入              模式 B: UI 操作      │
│   ┌──────────────────┐         ┌──────────────────┐  │
│   │ 用户手动输入文字   │         │ 用户点击按钮/操作  │  │
│   │ "删除 task-manager"│        │ Card 上的 [删除]  │  │
│   └────────┬─────────┘         └────────┬─────────┘  │
│            │                            │             │
│            │                   Prompt 生成器           │
│            │                   将 UI 操作转为 prompt    │
│            │                   "删除 Agent task-manager"│
│            │                            │             │
│            └──────────┬─────────────────┘             │
│                       │                               │
│                       ▼                               │
│              POST /api/chat/send                      │
│              (统一入口，走同一条通道)                    │
│                       │                               │
│                       ▼                               │
│              Chat Panel 显示用户消息                    │
│              + Agent 响应 + UI 更新                    │
└──────────────────────────────────────────────────────┘
```

**核心原则：UI 操作 = 自动生成 prompt + 发送给 Agent。** Agent 始终是唯一的操作执行者，前端只是输入方式不同。

#### 2.3.1 UIAction 结构化指令

前端不维护 prompt 映射表，而是将 UI 操作序列化为结构化指令，让 Agent 通过 SKILL.md 自行理解：

```typescript
// src/lib/ui-action.ts

interface UIAction {
  entity: string;               // "agent" | "role" | "skill" | ...
  action: string;               // "delete" | "edit" | "export" | ...
  targets: TargetItem[];        // 操作目标（支持单选和多选）
  context?: Record<string, any>; // 可选额外上下文
}

// 序列化为发送给 Agent 的消息格式
function serializeUIAction(action: UIAction): string {
  return `\`\`\`ui_action\n${JSON.stringify(action, null, 2)}\n\`\`\``;
}
```

**为什么不用 Prompt 模板映射表？** 映射表无法处理多选批量操作、复合操作等场景，且每新增操作都要改前端代码。Agent 通过 SKILL.md 天然具备理解结构化指令的能力，新增操作只需改 SKILL.md。

> 详见 [agentforge-dual-interaction-impl.md](./2026-03-26-agentforge-dual-interaction-impl.md) §4

#### 2.3.2 UI 操作 → Chat 的完整流程

以 "用户在 Dashboard 点击 AgentCard 的删除按钮" 为例：

```
1. 用户点击 AgentCard 上的 [删除] 按钮

2. 前端序列化 UIAction:
   sendUIAction({ entity:"agent", action:"delete", targets:[{id:"a1", name:"task-manager"}] })
   → 发送 ```ui_action JSON``` 给 Agent
   → Chat 显示: 🔧 delete agent: task-manager

3. Agent 收到 ui_action，根据 SKILL.md 理解意图:
   → "你确定要删除 Agent task-manager 吗？这将删除所有关联的角色和技能。"
   → 响应中包含 confirm_required

4. 前端渲染确认组件（内联在 Chat 中）:
   ┌──────────────────────────────────┐
   │ 🤖 确定删除 Agent task-manager？  │
   │    将同时删除 2 个角色和 5 个技能   │
   │                                  │
   │    [确认删除]     [取消]           │
   └──────────────────────────────────┘

5. 用户点击 [确认删除]:
   sendUIAction({ entity:"_dialog", action:"confirm", targets:[] })

6. Agent 执行删除:
   → agent_crud.delete_agent(...)
   → 返回结构化数据 { type: "agent", action: "deleted", ... }

8. Chat Panel 显示删除结果
   Dashboard 自动移除该 Card
```

#### 2.3.3 UI 操作的消息标记

UI 触发的消息在 Chat 中需要与手动输入区分，方便用户理解对话上下文：

```typescript
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  structured?: StructuredData;
  timestamp: number;
  source: "chat" | "ui_action";  // 消息来源
}
```

Chat Panel 中的渲染区别：
- `source: "chat"` → 正常用户消息气泡
- `source: "ui_action"` → 带操作图标的轻量消息（如 "🔧 删除 Agent task-manager"），视觉上弱化，不喧宾夺主

#### 2.3.4 可交互的 Agent 响应

Agent 返回的结构化数据中，Card 组件可以携带操作按钮：

```typescript
// 渲染规则扩展：Card 组件根据 type + action 决定显示哪些操作按钮

// AgentCard 操作按钮
const AGENT_ACTIONS = {
  created: ["detail", "edit", "export", "delete"],
  listed:  ["detail", "edit", "export", "delete"],  // 每个列表项都有
  updated: ["detail", "export"],
};

// RoleCard 操作按钮
const ROLE_ACTIONS = {
  created: ["edit", "delete"],
  listed:  ["edit", "delete"],
  updated: ["edit"],
};

// SkillCard 操作按钮
const SKILL_ACTIONS = {
  created: ["edit", "delete"],
  listed:  ["edit", "delete"],
  updated: ["edit"],
};
```

这意味着每次 Agent 返回数据并渲染 Card 后，Card 上就自带可点击的操作按钮，用户可以直接通过点击继续操作，形成 **对话 + 点击的混合交互循环**。

---

## 3. 登录与用户系统

### 3.1 GitHub OAuth 流程

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  前端     │     │  后端     │     │  GitHub  │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │  GET /api/auth/login            │
     │───────────────▶│                │
     │                │  302 Redirect  │
     │◀───────────────│───────────────▶│
     │                │                │
     │  (用户在 GitHub 授权)            │
     │                │                │
     │                │  callback?code=│
     │                │◀───────────────│
     │                │                │
     │                │  POST /oauth/  │
     │                │  access_token  │
     │                │───────────────▶│
     │                │                │
     │                │  user info     │
     │                │◀───────────────│
     │                │                │
     │                │  创建/更新 user │
     │                │  生成 session   │
     │                │                │
     │  Set-Cookie    │                │
     │  + redirect /  │                │
     │◀───────────────│                │
     │                │                │
     │  后续请求携带    │                │
     │  session cookie │                │
     │───────────────▶│                │
```

### 3.2 Auth API

```python
# === 登录相关 ===
GET  /api/auth/login        # → 302 重定向到 GitHub OAuth 授权页
GET  /api/auth/callback      # ← GitHub 回调，换取 token，创建 session
GET  /api/auth/me            # → 返回当前登录用户信息
POST /api/auth/logout        # → 清除 session

# === Session 管理 ===
# 使用 HTTP-Only Cookie 存储 session_id
# 后端维护 session → user_id 映射
# 所有 /api/chat/* 端点要求已登录
```

### 3.3 用户数据隔离

每个 GitHub 用户拥有独立的数据空间：

```
User A (github: alice)
  ├── Agent: task-manager
  │   ├── Role: default, reviewer
  │   ├── Skills: create_task, review_task
  │   └── ...
  └── Agent: chatbot
      └── ...

User B (github: bob)
  ├── Agent: code-assistant
  │   └── ...
  └── ...
```

**隔离实现：**
- agents 表包含 `user_id` 字段
- 所有 CRUD 操作自动绑定当前登录用户的 `user_id`
- 查询时自动过滤 `WHERE user_id = :current_user_id`
- Agent Session Manager 也按用户隔离，每个用户独立会话

### 3.4 前端登录状态

```typescript
// 页面加载时
async function checkAuth(): Promise<User | null> {
  const res = await fetch("/api/auth/me");
  if (res.status === 401) return null;
  return res.json();
}

// 未登录 → 显示登录页（GitHub 登录按钮）
// 已登录 → 显示主界面（Dashboard + Chat）
```

前端状态：

```
┌─────────────────────────────────────┐
│  未登录状态                          │
│                                     │
│       ┌─────────────────────┐       │
│       │   AgentForge        │       │
│       │                     │       │
│       │  [Login with GitHub]│       │
│       │                     │       │
│       └─────────────────────┘       │
└─────────────────────────────────────┘

          ↓ GitHub OAuth ↓

┌─────────────────────────────────────┐
│  已登录状态                          │
│  ┌─────────┐                        │
│  │ 👤 alice │              [Logout] │
│  └─────────┘                        │
│  ┌─────────────────┬───────────────┐│
│  │  Dashboard      │  Chat Panel   ││
│  │  (Cards)        │  (Messages)   ││
│  └─────────────────┴───────────────┘│
└─────────────────────────────────────┘
```

---

## 4. 关键设计决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| Agent 通信方式 | 复用已有 Adapter Layer + SSE 包装 | adapter 抽象已完成，天然支持多平台切换 |
| UI 渲染策略 | 前端根据 `type + action` 自动推断组件 | Agent 不耦合前端组件名，只关心业务语义 |
| Dashboard 数据源 | Chat Store entities（Agent 返回数据的卡片化视图） | 统一由 Chat 驱动 |
| 页面布局 | 三栏：Sidebar（图标导航）+ Dashboard + Chat Terminal | 紧凑、可切换视图 |
| 主题 | 亮/暗双主题，CSS 变量 + localStorage 持久化 | 跟随系统偏好，可手动切换 |
| Session 管理 | 单会话模式（per user） | 体验连贯 |
| 数据存储 | SQLite | Agent 配置持久化，支持查询和导出 |
| Agent 数据模型 | name + role_md + skills（model 无关） | 同一 Agent 可导出到任意平台 |
| 导出格式 | Adapter 模式（GitAgent / Claude / Codex / Cursor / Socialwares） | 参考 GitAgent 标准，一次创建多平台使用 |
| 登录认证 | GitHub OAuth，后端处理 | 前端无路由，后端是数据唯一入口 |
| 用户隔离 | 按 GitHub 用户隔离 | 每个用户独立的 Agent 配置空间 |

---

## 5. 前端设计

### 5.1 页面布局

三栏布局：窄 Sidebar（图标导航）+ Dashboard Panel + Chat Terminal。

```
未登录:
┌───────────────────────────────┐
│         AgentForge            │
│                               │
│    [Continue with GitHub]     │
│                               │
│    Craft · Configure · Deploy │
└───────────────────────────────┘

已登录:
┌──┬──────────────┬──────────────────────────┐
│  │  AGENTS  2   │  AgentForge Terminal     │
│  │              │                          │
│  │ ┌──────────┐ │  消息列表                 │
│侧│ │code-rev  │ │  + StructuredBlock 渲染   │
│边│ │ EXAMPLE  │ │                          │
│栏│ └──────────┘ │  ┌────────────────────┐  │
│  │ ┌──────────┐ │  │ /create-agent      │  │
│  │ │task-mgr  │ │  │ /list-agents       │  │ ← 命令面板
│  │ │ CLAUDE   │ │  │ /find-skill        │  │
│☀ │ └──────────┘ │  └────────────────────┘  │
│👤│              │  [> 输入指令...]   [Send] │
└──┴──────────────┴──────────────────────────┘

Sidebar 图标 (上→下):
  Logo → Terminal → Dashboard → (spacer) → Theme toggle → User avatar
```

**Sidebar:**
- 窄栏（56px），只有图标
- Terminal/Dashboard 视图切换（移动端单视图，桌面端并排）
- 主题切换（亮/暗）
- 用户头像 → 点击弹出退出确认

**Dashboard Panel:**
- Agent 卡片列表（从 Chat Store entities 聚合）
- 批量操作栏（多选后出现 Export/Delete/Clear）
- Example Agent 有角标，不可删除

**Chat Terminal:**
- 消息列表 + StructuredBlockRenderer 内联渲染
- 命令面板（输入时弹出，点击直接发送）
- 加载状态动画

### 5.2 Chat Store（前端状态管理）

```typescript
interface ChatStore {
  user: User | null;
  messages: Message[];
  entities: EntityStore;        // Dashboard 数据源
  selected: TargetItem[];       // 批量操作选中项
  session: { connected: boolean; loading: boolean };

  // 方法
  checkAuth(): Promise<void>;
  sendMessage(content: string, source: "chat" | "ui_action", displayText?: string): Promise<void>;
  sendUIAction(action: UIAction): Promise<void>;
  toggleSelect(item: TargetItem): void;
  clearSelection(): void;
}
```

### 5.3 渲染规则

| `type` | `action` | Chat 内联组件 | Dashboard 行为 |
|--------|----------|--------------|---------------|
| agent | created | AgentCard | 添加到列表 |
| agent | detailed | AgentDetail（四原语展开） | — |
| agent | listed | DataTable | 刷新列表 |
| agent | deleted | DeleteResult | 从列表移除 |
| agent | confirm_required | ConfirmDialog | — |
| skill | created | SkillCard | — |
| skill | editing | MarkdownEditor | — |
| scope | editing | MarkdownEditor | — |
| deploy | exported | DeployLog（下载按钮） | — |

### 5.4 UI 组件清单

**布局组件：**
- `AppShell` — 主布局（Sidebar + Dashboard + Chat）
- `Sidebar` — 图标导航 + 主题切换 + 用户菜单
- `LoginPage` — GitHub 登录页

**Chat 组件：**
- `ChatPanel` — 消息列表 + 命令面板 + 输入框 + SSE 流式渲染
- `MessageBubble` — 消息气泡（区分 chat / ui_action 来源样式）
- `StructuredBlockRenderer` — type + action → 组件分发

**Card 组件（Chat + Dashboard 共用）：**
- `AgentCard` — Agent 信息 + checkbox 多选 + View/Export/Delete 按钮 + Example 角标
- `AgentDetail` — 四原语展开视图（Scope/Roles/Skills/Commitment 分区）
- `RoleCard` — 角色名 + 描述预览
- `SkillCard` — 技能名 + 描述 + 角色标签
- `DeployLog` — 导出结果 + zip 下载按钮

**Dashboard 组件：**
- `DashboardPanel` — Agent 列表 + 空状态 + 批量操作栏
- `BatchActionBar` — 多选后的 Export/Delete/Clear 操作

**编辑/交互组件：**
- `MarkdownEditor` — 内联 Markdown 编辑器（Edit/Preview 切换）
- `MarkdownPreview` — 只读 Markdown 预览
- `YamlEditor` / `YamlPreview` — YAML 编辑/预览
- `ConfirmDialog` — 确认/取消对话框
- `ActionButton` — Card 操作按钮（发送 UIAction）

---

## 6. 后端设计

### 6.1 HTTP Layer

```python
# === Auth ===
GET  /api/auth/login         # → 302 重定向到 GitHub OAuth
GET  /api/auth/callback      # ← GitHub 回调，创建 session
GET  /api/auth/me            # → 当前用户信息
POST /api/auth/logout        # → 清除 session

# === Chat (需登录) ===
POST /api/chat/send          # ← 用户发消息给 Agent
GET  /api/chat/stream        # → SSE 流，接收 Agent 响应

# === System (继承自模板) ===
GET  /health                           # → 健康检查
GET  /violations                       # → 列出未解决的 commitment 违规
POST /violations/{violation_id}/resolve # → 标记违规已解决
```

### 6.2 Auth 实现

```python
# src/auth.py

import httpx
from fastapi import Request, HTTPException

GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]

async def github_login(request: Request):
    """重定向到 GitHub OAuth 授权页"""
    redirect_uri = f"{request.base_url}api/auth/callback"
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user"
    )
    return RedirectResponse(github_url)

async def github_callback(code: str):
    """
    GitHub 回调处理:
    1. 用 code 换取 access_token
    2. 用 access_token 获取用户信息
    3. 创建或更新 users 表记录
    4. 生成 session_id，写入 sessions 表
    5. Set-Cookie: session_id (HTTP-Only)
    6. 重定向到首页
    """

async def get_current_user(request: Request) -> User:
    """
    从 Cookie 中提取 session_id
    查找 sessions 表获取 user_id
    返回 User 对象
    未登录时抛出 401
    """
```

### 6.3 Session Manager + Agent 集成

**核心原则：用户消息必须经过 Agent（Claude/Codex/Kimi）处理，由 Agent 决定调用哪个 CRUD 函数。** Session Manager 不做意图解析，只负责管理 Agent 会话和消息转发。

```
用户消息 → Session Manager → Adapter → Agent (Claude SDK)
                                          │
                                Agent 根据 SOUL.md 理解身份
                                Agent 根据 SKILL.md 决定操作
                                          │
                                Agent 调用 CRUD 函数 (通过 Bash/tool)
                                          │
                                Agent 返回 ```json:structured 结果
                                          │
                              Session Manager 解析 structured 块
                                          │
                                    SSE → 前端
```

**Agent 的执行环境：**

Agent 运行在 `.runtime/agents/default/` 中（由 `deploy.sh` 编译生成），具备：
- `SOUL.md` — 合并了 scope.md + role/default.md，告诉 Agent 它是 AgentForge 管理者
- `.claude/skills/` — 链接了所有 skill（manage_agent、manage_skill、export_agent、import_agent 等）
- 每个 SKILL.md 中描述了触发条件、执行流程、CRUD 函数调用方式、结构化响应格式

**Agent 如何调用 CRUD：**

Agent 通过 Bash 工具执行 Python 脚本或直接调用 API：
```bash
# Agent 在 SKILL.md 指导下执行
uv run python -c "
import asyncio
from src.db import Database
from src.crud.agent_crud import create_agent
db = Database('.runtime/data/Sqlite/agentforge.db')
asyncio.run(db.init())
result = asyncio.run(create_agent(db, '$USER_ID', 'task-manager', 'desc', 'claude'))
print(result)
"
```

或者 Agent 通过 HTTP 调用后端 API（如果我们提供内部 CRUD 端点）。

**Session Manager 架构：**

```python
class SessionManager:
    """Per-user Agent 会话管理 — 不做意图解析，只做消息转发"""

    sessions: dict[str, AgentSession]

    async def get_or_create(user_id: str, adapter_name: str) -> AgentSession:
        """获取用户的 Agent 会话，不存在则创建

        1. 加载 .runtime/agents/default/ 的 RoleConfig
        2. 实例化对应的 Adapter (Claude/Codex/Kimi)
        3. 建立 Agent SDK 连接
        """

    async def send(user_id: str, message: str) -> AsyncIterator[AgentResponse]:
        """
        转发用户消息给 Agent:
        1. 获取用户的 AgentSession
        2. 将 user_id 注入消息上下文（Agent 需要知道是谁在操作）
        3. 调用 adapter.launch_sdk(prompt)
        4. 流式接收 Agent 响应
        5. 解析 ```json:structured 代码块
        6. 保存到 chat_history 表
        7. yield SSE 事件
        """

    async def disconnect(user_id: str):
        """断开 Agent 会话"""


class AgentSession:
    """单个用户的 Agent 会话"""

    user_id: str
    adapter: BaseAdapter      # Claude/Codex/Kimi SDK adapter
    config: RoleConfig        # .runtime/agents/default/ 的配置
    history: list[ChatMessage]
    connected: bool
```

### 6.4 Adapter 配置隔离

**所有 adapter 只加载项目级配置，不加载用户全局配置。** 这保证 AgentForge 的 Agent 行为不受用户本机环境影响。

| Adapter | 隔离方式 |
|---------|---------|
| Claude SDK | `setting_sources=["project", "local"]`（去掉 `"user"`） |
| Codex SDK | `--cd project_dir`（确保不加载 `~/.codex/` 全局配置） |
| Kimi SDK | `--work-dir project_dir`（确保不加载 `~/.kimi/` 全局配置） |

每个 adapter 的 `launch_sdk()` 实现必须遵守此规则。`BaseAdapter` 文档中应标注此约束。

deploy.sh 是 adapter-aware 的（`--adapter claude|codex|kimi`），为不同平台生成不同配置：

| | Claude | Codex | Kimi |
|--|--------|-------|------|
| Skills 目录 | `.claude/skills/` | `.agents/skills/` | `.agents/skills/` |
| Prompt 文件 | `SOUL.md` | `AGENTS.md` | `AGENTS.md` |
| Hooks | `.claude/hooks/` | `.codex/hooks/` | 无 |

### 6.5 Hook 数据采集

deploy.sh 为每个角色生成两个 hook 脚本（Claude/Codex），用于采集运行时数据：

- `log_prompt.sh` (UserPromptSubmit) — 记录用户输入到 `.runtime/data/prompts/*.jsonl`
- `log_tool.sh` (PreToolUse) — 记录工具调用到 `.runtime/data/prompts/*.jsonl`

这些数据是 evolver 诊断的来源。Kimi 平台无 hook 支持。

### 6.6 Agent 响应解析

Agent 在回复中使用 JSON 代码块标记结构化输出：

```markdown
已为你创建 Agent "task-manager"，包含默认角色和基础健康检查技能。

​```json:structured
{
  "type": "agent",
  "action": "created",
  "data": {
    "id": "uuid-xxx",
    "name": "task-manager",
    "description": "任务管理 Agent",
    "roles": ["default"],
    "skills": ["check_health"]
  }
}
​```
```

后端解析规则：
1. 扫描 Agent 响应中的 ` ```json:structured ` 代码块
2. 提取 JSON 并验证 `{type, action, data}` 结构
3. 将文本部分和结构化部分分别放入 `Message.content` 和 `Message.structured`
4. 通过 SSE 推送给前端

### 6.5 Business Layer

Agent 的 Skill 通过 Python 函数调用这些模块，不经过 HTTP。

**核心原则：CRUD 操作只写入 DB。导出时从 DB 生成完整 workspace。**

```
创建/编辑 Agent → 写入 SQLite (DB) ← UI 唯一数据源

导出:
    从 DB 读取配置 + 从模板复制运行时工具
    → 打包为完整可运行的 workspace zip
    → 浏览器下载

导入:
    方式 1: AgentForge UI 上传 zip → 解析四原语文件 → 写入 DB（UI 可管理）
    方式 2: 手动解压 zip 到独立 workspace → make deploy → 直接可用

运行 Agent:
    导出的 workspace 中 → make deploy → make start ROLE=default
```

#### 6.5.1 Agent CRUD

```python
# src/crud/agent_crud.py

def create_agent(user_id: str, name: str, description: str, model: str = "claude") -> Agent:
    """
    创建 Agent 配置 (只写 DB):
    1. 在 agents 表插入记录 (绑定 user_id, 含 model 字段)
    2. 自动创建默认 scope + default 角色 + 空 commitment
    3. 返回 Agent 对象
    注：配置只存 DB，导出时才生成文件
    """

def get_agent(user_id: str, agent_id: str) -> Agent:
    """获取 Agent 详情（含 roles, skills 列表），验证 user_id 归属"""

def list_agents(user_id: str) -> list[Agent]:
    """列出当前用户的所有 Agent"""

def delete_agent(user_id: str, agent_id: str):
    """删除 Agent 及其所有关联数据，验证 user_id 归属"""
```

#### 6.5.2 Role CRUD

```python
# src/crud/role_crud.py

def create_role(agent_id: str, name: str, soul_md: str) -> Role:
    """为指定 Agent 创建角色"""

def update_role(role_id: str, soul_md: str) -> Role:
    """更新角色的 role.md 内容"""

def list_roles(agent_id: str) -> list[Role]:
    """列出指定 Agent 的所有角色"""

def delete_role(role_id: str):
    """删除角色并清理 skill_roles 关联"""
```

#### 6.5.3 Skill CRUD

```python
# src/crud/skill_crud.py

def create_skill(agent_id: str, name: str, skill_md: str,
                 role_ids: list[str], description: str) -> Skill:
    """创建技能并建立 skill_roles 关联"""

def update_skill(skill_id: str, skill_md: str = None,
                 role_ids: list[str] = None) -> Skill:
    """更新技能内容和/或角色权限"""

def list_skills(agent_id: str) -> list[Skill]:
    """列出指定 Agent 的所有技能（含关联角色）"""

def delete_skill(skill_id: str):
    """删除技能"""
```

#### 6.5.4 Scope & Commitment

```python
# src/crud/scope_crud.py
def get_scope(agent_id: str) -> Scope:
def update_scope(agent_id: str, soul_md: str) -> Scope:

# src/crud/commitment_crud.py
def get_commitment(agent_id: str) -> Commitment:
def update_commitment(agent_id: str, commitment_yaml: str) -> Commitment:
```

#### 6.5.5 Export

```python
# src/crud/export.py

def export_agent(agent_id: str, output_dir: Path):
    """
    从数据库导出为标准四原语文件结构:

    output_dir/
    ├── agent/
    │   ├── role/{name}.md
    │   ├── scope/scope.md
    │   ├── commitment/commitment.yaml
    │   ├── flow/
    │   │   ├── flow.yaml          (自动生成)
    │   │   └── {skill}/SKILL.md
    │   ├── adapters/              (从模板复制)
    │   ├── deploy.sh              (从模板复制)
    │   └── start.sh               (从模板复制)
    ├── src/app.py                 (基础模板)
    └── pyproject.toml             (自动生成)
    """
```

---

## 7. .runtime/ 目录结构

`make deploy` 后生成的完整 .runtime/ 结构：

```
.runtime/
├── .deploy_stamp              ← Makefile 增量构建标记
├── data/
│   ├── Files/                 ← 应用文件
│   ├── Sqlite/                ← 数据库 (agentforge.db)
│   ├── prompts/               ← Hook 日志 (JSONL)
│   ├── sessions/              ← SDK 会话记录 (JSON)
│   └── evolve/
│       ├── reports/           ← 诊断报告 (JSON)
│       ├── violations/        ← Commitment 违规 (JSONL)
│       ├── auto_sessions/     ← 自动测试会话 (JSON)
│       └── state.yaml         ← 增量扫描游标
└── agents/
    ├── default/               ← default 角色的 PROJECT_DIR
    │   ├── .claude/skills/    ← 允许的技能 (符号链接)
    │   ├── .claude/hooks/     ← log_prompt.sh, log_tool.sh
    │   ├── .claude/settings.local.json
    │   ├── .workspace_root    ← 工作区根路径
    │   ├── SOUL.md            ← 合并的 prompt (scope.md + role.md)
    │   ├── commitment.yaml    ← 复制
    │   └── flow.yaml          ← 复制 (供参考)
    ├── dev/                   ← dev 角色
    └── evolver/               ← evolver 角色 (类似结构)
```

## 8. 数据库设计

使用 SQLite，存储于 `.runtime/data/Sqlite/agentforge.db`。

### 8.1 核心数据模型

Agent 的核心数据只有两个：身份描述和技能。Model 在导出时选择，不存储在 Agent 中。

```
Agent (model 无关)
 ├── name          "code-review"
 ├── role_md       "# Code Reviewer\n你是..."    ← Agent 的身份定义
 └── skills[]
      ├── { name: "review_diff", skill_md: "...", description: "..." }
      └── { name: "check_security", skill_md: "...", description: "..." }
```

### 8.2 表结构

```sql
-- 用户 (GitHub OAuth)
CREATE TABLE users (
    id              TEXT PRIMARY KEY,
    github_id       INTEGER NOT NULL UNIQUE,
    github_login    TEXT NOT NULL,
    github_name     TEXT DEFAULT '',
    github_avatar   TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 登录会话
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL
);

-- Agent 定义（核心表，model 无关）
CREATE TABLE agents (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    role_md         TEXT DEFAULT '',             -- Agent 身份描述（Markdown）
    is_example      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);
-- 注：不存储 model。Agent 定义是 model 无关的，model 在导出时选择。

-- 技能定义
CREATE TABLE skills (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    skill_md        TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(agent_id, name)
);

-- 对话历史
CREATE TABLE chat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    structured      TEXT,                       -- JSON string, nullable
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 9. 消息协议

### 8.1 前端 → 后端

```typescript
// POST /api/chat/send
interface ChatSendRequest {
  message: string;        // 用户输入的文本
}
// Cookie 中自动携带 session_id，后端据此确定 user_id
```

### 8.2 后端 → 前端 (SSE)

```typescript
// GET /api/chat/stream (SSE events)

// 文本块事件
interface TextChunkEvent {
  event: "text";
  data: { content: string };
}

// 结构化数据事件
interface StructuredEvent {
  event: "structured";
  data: {
    type: string;         // "agent" | "role" | "skill" | ...
    action: string;       // "created" | "updated" | "deleted" | "listed"
    data: Record<string, any>;
  };
}

// 完成事件
interface DoneEvent {
  event: "done";
  data: { message_id: string };
}

// 错误事件
interface ErrorEvent {
  event: "error";
  data: { message: string };
}
```

### 8.3 结构化数据示例

```json
// Agent 创建
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

// 角色列表
{
  "type": "role",
  "action": "listed",
  "data": {
    "agent_id": "a1b2c3",
    "agent_name": "task-manager",
    "roles": [
      {"id": "r1", "name": "default", "soul_md_preview": "你是..."},
      {"id": "r2", "name": "reviewer", "soul_md_preview": "你是..."}
    ]
  }
}

// 导出完成
{
  "type": "deploy",
  "action": "exported",
  "data": {
    "agent_name": "task-manager",
    "output_dir": ".socialware/workspace/my-team/task-manager/",
    "files_generated": 12
  }
}
```

---

## 10. 前端渲染映射

前端根据 `type + action` 自动推断渲染组件：

```typescript
const COMPONENT_MAP: Record<string, Record<string, React.ComponentType>> = {
  agent: {
    created: AgentCard,
    updated: AgentCard,
    listed:  AgentTable,
    deleted: DeleteConfirm,
  },
  role: {
    created: RoleCard,
    updated: RoleCard,
    listed:  RoleTable,
    deleted: DeleteConfirm,
  },
  skill: {
    created: SkillCard,
    updated: SkillCard,
    listed:  SkillTable,
    deleted: DeleteConfirm,
  },
  scope:      { updated: MarkdownPreview },
  commitment: { updated: YamlPreview },
  deploy:     { exported: DeployLog },
};

function StructuredBlockRenderer({ data }: { data: StructuredData }) {
  const Component = COMPONENT_MAP[data.type]?.[data.action];
  if (!Component) return null;
  return <Component {...data.data} />;
}
```

---

## 11. 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | Next.js 15 + React 19 | 已有 |
| 前端样式 | Tailwind CSS 4 | 已有 |
| 前端状态 | zustand 或 React Context | 轻量级 Chat Store |
| 前端 Markdown | react-markdown | scope.md / role.md 预览 |
| 后端框架 | FastAPI | 已有 |
| 数据库 | SQLite (aiosqlite) | 轻量、无需额外服务 |
| ORM | 无，直接 SQL | 表结构简单 |
| Agent 通信 | SSE (sse-starlette) | 单向流式 |
| Agent 适配 | 已有 Adapter Layer | Claude/Codex/Kimi |
| 认证 | GitHub OAuth + httpx | 后端直接对接 |
| Session | HTTP-Only Cookie | 安全、简单 |

---

## 12. 开发阶段

```
Phase 1 — 登录 + 通信骨架                              [已完成]
  ├── 后端: GitHub OAuth (login/callback/me/logout)
  ├── 后端: Session Manager + /api/chat/send (SSE)
  ├── 前端: Login 页 + Auth 状态管理
  ├── 前端: Chat Panel + 命令面板
  └── 验证: GitHub 登录 → 发消息 → 响应 → 前端显示

Phase 2 — 数据库 + CRUD                                [已完成]
  ├── 后端: SQLite 初始化 + 9 张表
  ├── 后端: 6 个 CRUD 模块 + export + import
  ├── 后端: session.py 硬编码意图匹配（临时方案）
  └── 验证: 通过 Chat 创建 Agent → 数据写入 DB

Phase 3 — 结构化渲染 + 前端                             [已完成]
  ├── 前端: Chat Store + StructuredBlockRenderer
  ├── 前端: AgentCard / RoleCard / SkillCard + AgentDetail
  ├── 前端: Sidebar + Dashboard + 主题切换
  └── 验证: Chat 中显示操作结果卡片 + Dashboard 联动

Phase 4 — Dashboard + 导出                              [已完成]
  ├── 前端: Dashboard Panel + 批量操作
  ├── 后端: export → 浏览器下载 zip
  ├── 后端: 创建引导 wizard（7 步流程）
  ├── 预设 example agent (code-review-example)
  └── 验证: 创建 Agent → Dashboard 显示 → 导出 zip → 解压可用

Phase 5 — Agent 集成（待实现）
  ├── 后端: Session Manager 接入真实 Adapter Layer
  │   - 替换 session.py 中的硬编码意图匹配
  │   - 用户消息通过 Claude SDK 发给 Agent
  │   - Agent 根据 SKILL.md 理解意图并调用 CRUD
  ├── 后端: CRUD 函数提供为 Agent 可调用的工具
  │   - 方案 A: Agent 通过 Bash 执行 Python 脚本调用 CRUD
  │   - 方案 B: 提供内部 HTTP API，Agent 通过 curl 调用
  ├── 后端: user_id 上下文注入
  │   - Session Manager 将 user_id 注入 Agent 的系统提示
  │   - Agent 在调用 CRUD 时使用该 user_id
  ├── 后端: Agent 响应解析
  │   - 从 Agent 的回复中提取 ```json:structured 代码块
  │   - 通过 SSE 推送给前端
  └── 验证: 用户发消息 → Agent 理解 → 调用 CRUD → 返回结构化数据 → 前端渲染
```
