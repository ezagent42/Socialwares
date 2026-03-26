# AgentForge CMS 内容管理系统设计

> 版本: v1.0 | 日期: 2026-03-26

## 1. 概述

AgentForge 是一个 **Agent 创建与管理平台**，采用 CMS（内容管理系统）模式，让用户通过 Chat 对话来创建、编辑、管理 Agent 配置。

**类比 CMS：**

| CMS 概念 | AgentForge 对应 |
|----------|----------------|
| 文章/页面 | Agent 定义（一套完整的四原语配置） |
| 媒体/组件 | Skill、Hook、MCP Server |
| 分类/标签 | Role（角色）、权限映射 |
| 发布 | 导出为标准四原语文件 → deploy |

**核心原则：用户永远在和 AgentForge 的 Agent 对话，Agent 是唯一的操作中介。**

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────┐
│               FRONTEND (Next.js) — 单页面            │
│                                                      │
│  ┌──────────────────────┬─────────────────────────┐  │
│  │   Dashboard 区域      │      Chat Panel         │  │
│  │                      │                         │  │
│  │  Agent 返回数据的     │  - 消息列表              │  │
│  │  Card/Table 展示     │  - ui_block 内联渲染     │  │
│  │                      │  - 输入框                │  │
│  │  (从 Chat Store      │                         │  │
│  │   自动提取渲染)       │                         │  │
│  └──────────┬───────────┴───────────┬─────────────┘  │
│             └───────────────────────┘                 │
│                   Chat Store (共享状态)                │
│                         │                            │
│                   SSE / WebSocket                     │
└─────────────────────────┼────────────────────────────┘
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
| Agent 通信方式 | 复用已有 Adapter Layer + SSE/WS 包装 | adapter 抽象已完成，天然支持多平台切换 |
| UI 渲染策略 | 前端根据 `type + action` 自动推断组件 | Agent 不耦合前端组件名，只关心业务语义 |
| Dashboard 数据源 | Chat Store（Agent 返回数据的卡片化视图） | 统一由 Chat 驱动 |
| 页面结构 | 单页面（Dashboard + Chat 并排） | 无路由，简化架构 |
| Session 管理 | 单会话模式（per user） | 体验连贯 |
| 数据存储 | SQLite | Agent 配置持久化，支持查询和导出 |
| 登录认证 | GitHub OAuth，后端处理 | 前端无路由，后端是数据唯一入口 |
| 用户隔离 | 按 GitHub 用户隔离 | 每个用户独立的 Agent 配置空间 |

---

## 5. 前端设计

### 5.1 页面布局

单页面，两种状态：未登录（Login 页）和已登录（Dashboard + Chat）。

```
┌─────────────────────────────────────────────────────┐
│  AgentForge                        👤 alice [Logout] │
├─────────────────────────┬───────────────────────────┤
│                         │                           │
│   Dashboard 区域         │    Chat Panel             │
│                         │                           │
│  ┌───────────────────┐  │  ┌─────────────────────┐  │
│  │ Agent: task-mgr   │  │  │ 🤖 已创建 Agent:    │  │
│  │ Roles: 2          │  │  │    task-manager      │  │
│  │ Skills: 5         │  │  │    [agent_card]      │  │
│  │ [展开详情]         │  │  ├─────────────────────┤  │
│  └───────────────────┘  │  │ 👤 给它加个 reviewer │  │
│                         │  │    角色              │  │
│  ┌───────────────────┐  │  ├─────────────────────┤  │
│  │ Agent: chatbot    │  │  │ 🤖 已添加角色:      │  │
│  │ Roles: 1          │  │  │    reviewer          │  │
│  │ Skills: 3         │  │  │    [role_card]       │  │
│  │ [展开详情]         │  │  └─────────────────────┘  │
│  └───────────────────┘  │                           │
│                         │  ┌─────────────────────┐  │
│                         │  │ 输入消息...     [发送] │  │
│                         │  └─────────────────────┘  │
└─────────────────────────┴───────────────────────────┘
```

### 5.2 Chat Store（前端状态管理）

Chat Store 是前端的核心状态容器，保存所有 Agent 返回的数据：

```typescript
interface ChatStore {
  // 用户信息
  user: User | null;

  // 消息列表 (Chat Panel 渲染)
  messages: Message[];

  // 结构化数据索引 (Dashboard 渲染)
  entities: {
    agents: Record<string, AgentData>;
    roles: Record<string, RoleData>;
    skills: Record<string, SkillData>;
  };

  // Session 状态
  session: {
    connected: boolean;
    adapterId: string;
  };
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;            // 文本内容
  structured?: StructuredData; // 结构化数据 (可选)
  timestamp: number;
  source: "chat" | "ui_action"; // 消息来源: 手动输入 or UI 操作生成
}

interface StructuredData {
  type: "agent" | "role" | "skill" | "scope" | "commitment" | "deploy";
  action: "created" | "updated" | "deleted" | "listed" | "exported";
  data: Record<string, any>;
}
```

**渲染规则：**

| `type` | `action` | Chat 内联组件 | Dashboard 行为 |
|--------|----------|--------------|---------------|
| agent | created | AgentCard | 添加到 agents 列表 |
| agent | listed | AgentTable | 刷新 agents 列表 |
| agent | deleted | 删除确认提示 | 从列表移除 |
| role | created | RoleCard | 更新对应 agent 的 roles |
| role | updated | RoleCard (编辑态) | 更新对应 role 数据 |
| skill | created | SkillCard | 更新对应 agent 的 skills |
| skill | listed | SkillTable | 刷新 skills 列表 |
| deploy | exported | DeployLog | 显示部署状态 |

### 5.3 Dashboard 数据提取

Dashboard 从 Chat Store 的消息历史中提取最新状态：

```typescript
function aggregateEntities(messages: Message[]): EntityStore {
  const entities: EntityStore = { agents: {}, roles: {}, skills: {} };

  for (const msg of messages) {
    if (!msg.structured) continue;
    const { type, action, data } = msg.structured;

    switch (type) {
      case "agent":
        if (action === "created" || action === "updated")
          entities.agents[data.id] = data;
        if (action === "deleted")
          delete entities.agents[data.id];
        if (action === "listed")
          data.agents?.forEach(a => entities.agents[a.id] = a);
        break;
      // ... 同理处理 role, skill
    }
  }
  return entities;
}
```

### 5.4 UI 组件清单

**Chat 组件：**
- `ChatPanel` — 消息列表 + 输入框 + SSE 连接管理
- `MessageBubble` — 单条消息渲染（文本 + 可选 ui_block）
- `StructuredBlockRenderer` — 根据 `type + action` 分发到具体组件

**Card 组件（Chat 内联 + Dashboard 共用）：**
- `AgentCard` — 显示 Agent 名称、描述、角色数、技能数
- `RoleCard` — 显示角色名称、SOUL.md 预览
- `SkillCard` — 显示技能名称、描述、关联角色标签
- `DeployLog` — 显示部署编译日志

**Dashboard 组件：**
- `DashboardPanel` — 从 Chat Store 的 entities 中提取数据，渲染 Card 列表
- `AgentDetail` — 展开某个 Agent，显示其下所有 Role/Skill/Scope/Commitment

**编辑组件（在 Chat 流中内联）：**
- `MarkdownEditor` — 编辑 SOUL.md / SKILL.md 内容
- `YamlEditor` — 编辑 eval.yaml / flow.yaml

**交互组件：**
- `ConfirmDialog` — Agent 请求确认时的 [确认] / [取消] 按钮
- `ActionButton` — Card 上的操作按钮（删除、编辑、导出等），点击后生成 prompt
- `PromptGenerator` — 将 UI 操作转为自然语言 prompt 并发送

**Auth 组件：**
- `LoginPage` — GitHub 登录按钮
- `UserBar` — 顶部用户信息 + Logout 按钮

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

# === System ===
GET  /health                 # → 健康检查
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

### 6.3 Session Manager

管理 per-user 的 Agent 会话：

```python
class SessionManager:
    """Per-user Agent 会话管理"""

    # user_id → AgentSession
    sessions: dict[str, AgentSession]

    async def get_or_create(user_id: str, adapter_name: str) -> AgentSession:
        """获取用户的 Agent 会话，不存在则创建"""

    async def send(user_id: str, message: str) -> AsyncIterator[AgentResponse]:
        """
        发送用户消息:
        1. 获取用户的 AgentSession
        2. 调用 adapter.query(prompt)
        3. 解析 Agent 响应，提取结构化数据
        4. 保存到 chat_history 表 (绑定 user_id)
        5. yield 响应块
        """

    async def disconnect(user_id: str):
        """断开用户的 Agent 会话"""


class AgentSession:
    """单个用户的 Agent 会话"""

    user_id: str
    adapter: BaseAdapter
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

### 6.5 Agent 响应解析

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

Agent 的 Skill 通过 Python 函数调用这些模块，不经过 HTTP：

#### 6.5.1 Agent CRUD

```python
# src/crud/agent_crud.py

def create_agent(user_id: str, name: str, description: str) -> Agent:
    """
    创建 Agent 配置:
    1. 在 agents 表插入记录 (绑定 user_id)
    2. 自动创建默认 scope
    3. 自动创建默认 role (default)
    4. 自动注册 check_health skill
    5. 返回 Agent 对象
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
    """更新角色的 SOUL.md 内容"""

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
def update_commitment(agent_id: str, eval_yaml: str) -> Commitment:
```

#### 6.5.5 Export

```python
# src/crud/export.py

def export_agent(agent_id: str, output_dir: Path):
    """
    从数据库导出为标准四原语文件结构:

    output_dir/
    ├── agent/
    │   ├── role/{name}/SOUL.md
    │   ├── scope/SOUL.md
    │   ├── commitment/eval.yaml
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

## 7. 数据库设计

使用 SQLite，存储于 `.runtime/data/Sqlite/agentforge.db`：

```sql
-- 用户 (GitHub OAuth)
CREATE TABLE users (
    id              TEXT PRIMARY KEY,           -- UUID
    github_id       INTEGER NOT NULL UNIQUE,    -- GitHub user ID
    github_login    TEXT NOT NULL,              -- GitHub username
    github_name     TEXT DEFAULT '',            -- GitHub display name
    github_avatar   TEXT DEFAULT '',            -- Avatar URL
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 登录会话
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,           -- session_id (UUID)
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL               -- 过期时间
);

-- Agent 定义
CREATE TABLE agents (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, name)                       -- 同一用户下 Agent 名唯一
);

-- 角色定义
CREATE TABLE roles (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    soul_md         TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(agent_id, name)
);

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

-- 技能-角色权限映射
CREATE TABLE skill_roles (
    skill_id        TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    role_id         TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (skill_id, role_id)
);

-- Scope 定义 (每个 Agent 一条)
CREATE TABLE scopes (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    soul_md         TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Commitment 定义 (每个 Agent 一条)
CREATE TABLE commitments (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    eval_yaml       TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now'))
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

## 8. 消息协议

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

## 9. 前端渲染映射

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

## 10. 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | Next.js 15 + React 19 | 已有 |
| 前端样式 | Tailwind CSS 4 | 已有 |
| 前端状态 | zustand 或 React Context | 轻量级 Chat Store |
| 前端 Markdown | react-markdown | SOUL.md 预览 |
| 后端框架 | FastAPI | 已有 |
| 数据库 | SQLite (aiosqlite) | 轻量、无需额外服务 |
| ORM | 无，直接 SQL | 表结构简单 |
| Agent 通信 | SSE (sse-starlette) | 单向流式 |
| Agent 适配 | 已有 Adapter Layer | Claude/Codex/Kimi |
| 认证 | GitHub OAuth + httpx | 后端直接对接 |
| Session | HTTP-Only Cookie | 安全、简单 |

---

## 11. 开发阶段

```
Phase 1 — 登录 + 通信骨架
  ├── 后端: GitHub OAuth (login/callback/me/logout)
  ├── 后端: Session Manager + /api/chat/send + /api/chat/stream (SSE)
  ├── 后端: 对接已有 Adapter Layer
  ├── 前端: Login 页 + Auth 状态管理
  ├── 前端: Chat Panel 组件 (消息列表 + 输入框 + SSE 连接)
  └── 验证: GitHub 登录 → 发消息 → Agent 回复 → 前端显示

Phase 2 — 数据库 + CRUD
  ├── 后端: SQLite 初始化 + 表结构 (含 users/sessions)
  ├── 后端: agent_crud / role_crud / skill_crud / scope_crud / commitment_crud
  ├── Agent: manage_agent / manage_role / manage_skill 等 Skill
  └── 验证: 通过 Chat 创建 Agent → 数据写入 DB (绑定用户)

Phase 3 — 结构化渲染
  ├── 后端: Agent 响应解析 (提取 structured block)
  ├── 前端: Chat Store + StructuredBlockRenderer
  ├── 前端: AgentCard / RoleCard / SkillCard 组件
  └── 验证: Chat 中显示操作结果卡片

Phase 4 — Dashboard + 导出
  ├── 前端: Dashboard Panel (从 Chat Store 聚合数据)
  ├── 后端: export.py (DB → 四原语文件)
  ├── 前端: DeployLog 组件
  └── 验证: 创建 Agent → Dashboard 显示 → 导出为文件
```
