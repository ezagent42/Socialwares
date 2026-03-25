# P2 设计文档：Chat UI + Chat API + Adapter Query

> 日期: 2026-03-20 | 阶段: Phase 2

## 目标

为 Socialware 提供浏览器 Chat 界面。Chat 本身是一个简单的 IM 窗口，用户输入 `/agentforge` 命令后连接 Agent Runtime，开始和 AgentForge 对话。

## 核心理念

- **Chat 是 IM，不依赖 Agent** — 没有 Agent 环境也能打开 Chat 窗口
- **Agent 按需注册** — 用户输入斜杠命令时才检测环境、连接 Runtime
- **单 session** — 一次只对接一个 role
- **不管对话历史持久化** — 对话历史由 Agent Runtime 自己管理

## 设计决策

| 决策点 | 选择 |
|--------|------|
| Agent 连接方式 | 斜杠命令触发（`/agentforge`） |
| Adapter 选择 | 方案 B：通过 adapter 抽象层，支持 Claude/Codex/Kimicode |
| Session 模式 | 单 session，一次一个 role |
| 对话历史 | 不持久化，由 Runtime 管理 |
| 前端框架 | Next.js App Router |
| 开发顺序 | 后端 → curl 测试 → 前端 → 联调 |

---

## 第一部分：Adapter 扩展

### BaseAdapter 新增 query() 方法

```python
# agent/adapters/base.py

class BaseAdapter(abc.ABC):
    # 已有
    @abstractmethod
    def launch_shell(self) -> None: ...
    @abstractmethod
    def launch_sdk(self) -> None: ...

    # 新增
    @abstractmethod
    async def query(self, prompt: str, options: dict | None = None) -> list[dict]:
        """Send a prompt to the Agent Runtime, return response messages.

        Args:
            prompt: User message
            options: Runtime-specific options (cwd, system_prompt, etc.)

        Returns:
            List of message dicts: [{"type": "text", "text": "..."}]
        """
        ...
```

### 三个 Adapter 实现

| Adapter | query() 实现 |
|---------|-------------|
| Claude | `claude_code_sdk.query(prompt, ClaudeCodeOptions(...))` |
| Codex | openai agents SDK 调用 |
| Kimicode | kimi CLI subprocess 调用 |

### 环境检测

```python
# agent/adapters/base.py 新增

@classmethod
@abstractmethod
def is_available(cls) -> bool:
    """Check if this adapter's runtime is installed."""
    ...
```

| Adapter | 检测方式 |
|---------|---------|
| Claude | `shutil.which("claude") is not None` |
| Codex | `shutil.which("codex") is not None` |
| Kimicode | `shutil.which("kimi") is not None` |

---

## 第二部分：后端 API

### 端点列表

```
# 已有
GET  /health                     ← 健康检查

# Session 管理
POST   /session                  ← 创建 Agent session
DELETE /session                  ← 关闭当前 session
GET    /session                  ← 获取当前 session 信息

# Chat
POST /chat                       ← 发送消息给 Agent，返回回复

# 环境查询
GET  /adapters                   ← 列出可用的 adapter

# 四原语查询（只读）
GET  /roles                      ← 列出已部署的 role
GET  /roles/{name}               ← 读取某个 role 的 SOUL.md
GET  /flows                      ← 列出 skill
GET  /flows/registry             ← 读取 flow.yaml
GET  /commitments                ← 读取 eval.yaml
GET  /scope                      ← 读取 scope/SOUL.md
```

### Session 管理

```python
# POST /session
# 请求:
{"role": "agentforge", "adapter": "claude"}

# 响应:
{"status": "created", "role": "agentforge", "adapter": "claude"}

# 错误:
# 400 — adapter 不可用（未安装对应 Runtime）
# 400 — role 不存在（未部署）
# 409 — 已有活跃 session（需先 DELETE）
```

```python
# GET /session
# 响应（有活跃 session）:
{"active": true, "role": "agentforge", "adapter": "claude"}

# 响应（无活跃 session）:
{"active": false}
```

```python
# DELETE /session
# 响应:
{"status": "closed"}
```

### Chat

```python
# POST /chat
# 请求:
{"message": "创建一个任务管理 Agent"}

# 响应:
{"messages": [{"type": "text", "text": "好的，请确认 role 名称？"}]}

# 错误:
# 400 — 无活跃 session（需先 POST /session）
```

工作流程：

```
POST /chat {message}
  → 后端获取当前 session 的 adapter 实例
  → 调用 adapter.query(message, options)
  → options 包含 cwd（.runtime/agents/{role}/）和 system_prompt（SOUL.md）
  → 返回 Agent 回复
```

### 环境查询

```python
# GET /adapters
# 响应:
{
  "adapters": [
    {"name": "claude", "available": true},
    {"name": "codex", "available": false},
    {"name": "kimicode", "available": true}
  ]
}
```

### 四原语查询

```python
# GET /roles
# 响应:
{"roles": ["agentforge", "default", "dev"]}

# GET /roles/agentforge
# 响应:
{"name": "agentforge", "soul": "# AgentForge Agent\n\n..."}

# GET /flows
# 响应:
{"flows": ["check_health", "create_role", "create_skill", ...]}

# GET /flows/registry
# 响应:
{"flows": {}, "direct_actions": [...]}

# GET /commitments
# 响应:
{"commitments": {}}

# GET /scope
# 响应:
{"soul": "# AgentForge\n\nAgent creation and management..."}
```

---

## 第三部分：前端 Chat UI

### 技术栈

- Next.js 15 (App Router)
- React 19
- Tailwind CSS
- TypeScript

### 文件结构

```
app/
├── src/
│   ├── app/
│   │   ├── page.tsx              ← 首页：Chat 窗口
│   │   ├── layout.tsx            ← 根布局
│   │   └── globals.css           ← Tailwind 全局样式
│   ├── components/
│   │   ├── chat-panel.tsx        ← 消息列表 + 输入框
│   │   ├── message-bubble.tsx    ← 单条消息（user / agent / system）
│   │   └── session-bar.tsx       ← 顶栏：连接状态 + 设置
│   └── lib/
│       └── api.ts                ← fetch 封装
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

### 页面布局

```
┌─ Session Bar ──────────────────────────────────┐
│  Socialware Chat            ● Not Connected     │
├─────────────────────────────────────────────────┤
│                                                  │
│  欢迎使用 Socialware Chat                        │
│  输入 /agentforge 连接 Agent                     │
│                                                  │
│  User: /agentforge                               │
│                                                  │
│  System: 检测到可用 Runtime: Claude Code          │
│          正在启动 AgentForge Agent...             │
│          ✓ AgentForge 已连接                     │
│                                                  │
│  Agent: 你好，我是 AgentForge。                   │
│         我可以帮你创建和管理 Agent。               │
│                                                  │
│  User: 创建一个任务管理 Agent                     │
│                                                  │
│  Agent: 好的，请确认 role 名称？                  │
│                                                  │
├─────────────────────────────────────────────────┤
│  [输入消息...                           ] [发送] │
└─────────────────────────────────────────────────┘
```

### 交互流程

1. **初始状态** — Chat 窗口打开，顶栏显示 "Not Connected"，输入框可用
2. **用户输入 `/agentforge`** — 前端识别斜杠命令：
   - 调用 GET /adapters 获取可用 adapter
   - 选择第一个可用的 adapter
   - 调用 POST /session {role: "agentforge", adapter: "claude"}
   - 连接成功 → 顶栏变为 "● Connected: agentforge (claude)"
   - 显示系统消息
3. **用户输入普通消息** — 如果已连接 Agent：
   - 调用 POST /chat {message}
   - 显示 Agent 回复
4. **用户输入普通消息** — 如果未连接 Agent：
   - 只在本地显示，不发送（P2 阶段不处理无 Agent 的聊天）
5. **用户输入 `/disconnect`** — 调用 DELETE /session，断开连接

### 消息类型

```typescript
type Message = {
  id: string
  role: "user" | "agent" | "system"
  content: string
  timestamp: number
}
```

---

## 开发顺序

```
Step 1: BaseAdapter 加 query() + is_available() + 三个 adapter 实现
        → 单元测试

Step 2: 后端 API（/session, /chat, /adapters, 四原语查询）
        → curl 测试

Step 3: 前端 Next.js 项目初始化 + Chat UI 组件
        → 浏览器联调
```
