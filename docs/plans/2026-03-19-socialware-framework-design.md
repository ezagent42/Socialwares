# Socialware 底层框架 & AgentForge 需求设计文档

> 版本: v0.5 | 日期: 2026-03-20 | 阶段: Phase 1
> 对齐: README.md + QUICKSTART.md + socialware-dev-guide-discuss-v2.md v0.5 + 当前代码实现

## 概述

本文档定义 Socialware 底层框架和 AgentForge 应用的需求设计。

### 底层框架（✅ 已实现）

| 模块 | 状态 | 说明 |
|------|------|------|
| 四原语配置 | ✅ | role/ scope/ commitment/ flow/ + flow.yaml |
| deploy.sh | ✅ | 编译四原语 → .runtime/，按 flow.yaml 选择性符号链接 |
| start.sh | ✅ | 统一启动入口，支持 adapter 切换 |
| Adapters | ✅ | Claude Code / Codex / Kimicode，shell + SDK 双模式 |
| create-my-socialware | ✅ | 脚手架创建 workspace 实例 |
| evolve.sh | ✅ | 变更检测 + PR 路由 |

### AgentForge（🔲 待实现）

AgentForge 是一个 Socialware App 实例，通过对话自动化 QUICKSTART 中的手动文件编辑步骤。

---

## 第一部分：底层框架（已实现，仅作记录）

### 1. 四原语配置

```
agent/
├── role/{name}/SOUL.md           ← Who：Agent 身份（每个 role 一个子目录）
├── scope/SOUL.md                 ← Where：App 级能力边界（所有 role 共享）
├── commitment/eval.yaml          ← What：声明式评估标准
├── flow/                         ← How：
│   ├── flow.yaml                 ← action 注册表（控制哪个 role 能用哪些 skill）
│   └── {skill}/SKILL.md          ← 每个 skill 一个子目录
├── adapters/                     ← 平台适配器（Claude/Codex/Kimi）
│   └── base.py                   ← BaseAdapter + RoleConfig
├── deploy.sh                     ← 编译四原语 → .runtime/
└── start.sh                      ← 统一启动入口
```

### 2. 文件如何被使用

```
agent/ 四原语文件
     │
     │ deploy.sh 编译
     ▼
.runtime/agents/{role}/
├── SOUL.md                ← scope/SOUL.md + role/{name}/SOUL.md 合并
├── eval.yaml              ← 复制自 commitment/eval.yaml
├── flow.yaml              ← 复制自 flow/flow.yaml
└── .claude/skills/        ← 符号链接（只链接 flow.yaml 允许该 role 使用的 skill）
     │
     │ start.sh 启动
     ▼
Agent Runtime（Claude Code / Codex / Kimi Code）
├── 读取 SOUL.md → 作为系统提示词（Agent 知道自己是谁、能做什么）
└── 读取 .claude/skills/ → 作为可用技能（Agent 知道遇到什么情况该怎么做）
     │
     │ 用户对话
     ▼
Agent 按 SOUL.md 约束 + SKILL.md 步骤执行
```

**SOUL.md 和 SKILL.md 是"剧本"，Agent Runtime 是"演员"。** 换 Runtime 不影响逻辑。

### 3. flow.yaml — action 注册表

```yaml
# 状态机（有流转的 action）
flows:
  F1:
    name: task_lifecycle
    transitions:
      - { from: _none_, action: create_task, to: draft, role: [admin] }
      - { from: draft,  action: submit,      to: submitted, role: [submitter] }

# 直接 action（无状态机）
direct_actions:
  - { action: check_health, role: [default, dev], description: "Check app health" }
  - { action: setup_claude, role: [dev], description: "Configure Claude Code" }
```

deploy.sh 读取 flow.yaml，**只为每个 role 符号链接它被允许使用的 skill**。

---

## 第二部分：AgentForge 需求设计

### 1. AgentForge 是什么

AgentForge 是一个通过 `create-my-socialware.py` 创建的 Socialware App 实例。

```bash
# 创建
uv run scripts/create-my-socialware.py \
    --room my-team --app agentforge --description "Agent 创建与管理"

# 进入 workspace
cd .socialware/workspace/my-team/agentforge

# 编译 & 启动
./agent/deploy.sh
./agent/start.sh --role agentforge
```

启动后，它是一个 Agent Runtime 进程（Claude Code / Codex / Kimi），加载了 AgentForge 专属的 SOUL.md 和管理类 Skill。用户通过对话告诉它要创建什么 Agent，它自动生成四原语文件。

### 2. AgentForge 解决什么问题

QUICKSTART 中创建 Agent 的手动步骤：

```bash
# 手动创建 role
mkdir agent/role/task-manager
vim agent/role/task-manager/SOUL.md

# 手动创建 skill
mkdir -p agent/flow/create_task
cat > agent/flow/create_task/SKILL.md << 'EOF'
...
EOF

# 手动注册 action
vim agent/flow/flow.yaml   # 添加 action → role 映射

# 手动编译
./agent/deploy.sh
```

**AgentForge 用对话替代以上所有 `vim` 操作。**

### 3. AgentForge 的工作范围

| AgentForge 做的事 | AgentForge 不做的事 |
|---|---|
| 创建 `role/{name}/SOUL.md` | 不关心 Agent 启动后做什么 |
| 创建 `flow/{skill}/SKILL.md` | 不监控 Agent 运行状态 |
| 更新 `flow/flow.yaml`（注册 action） | 不代理用户和 Agent 之间的对话 |
| 更新 `commitment/eval.yaml` | 不评估 Agent 做得好不好 |
| 更新 `scope/SOUL.md` | 不管理进程（启停由用户手动执行） |
| **生成 `src/app.py` 中对应的 API 端点代码** | — |
| 触发 `./agent/deploy.sh` | — |

> **重要**：每加一个 Skill，通常需要同时生成对应的 API 端点（src/app.py）。这是示例文档中的核心模式：**SKILL.md + API 端点 + flow.yaml 注册** 三件套。

**Agent 创建完后做什么、做得好不好，由四原语本身约束，不是 AgentForge 的事。**

### 4. AgentForge 不需要后端 API

P1 阶段，AgentForge 是一个 Agent Runtime 进程，天然具备文件操作能力：

```
Agent Runtime 内置能力：
├── 读文件（Read）
├── 写文件（Write / Edit）
├── 执行命令（Bash → deploy.sh）
└── 理解自然语言（对话引导）
```

不需要 HTTP API 就能完成所有四原语文件操作。`src/app.py` 保持 `/health` 即可。

### 5. AgentForge 的四原语配置

```
.socialware/workspace/my-team/agentforge/
└── agent/
    ├── role/
    │   └── agentforge/
    │       └── SOUL.md           ← "你是 Agent 管理者，负责创建和编辑四原语文件"
    ├── scope/
    │   └── SOUL.md               ← AgentForge 的能力边界
    ├── commitment/
    │   └── eval.yaml             ← 验证生成的文件结构是否合法
    ├── flow/
    │   ├── flow.yaml             ← AgentForge 自己的 action 注册
    │   ├── create_role/
    │   │   └── SKILL.md          ← 创建新 role 的步骤
    │   ├── create_skill/
    │   │   └── SKILL.md          ← 创建新 skill 的步骤
    │   ├── edit_primitives/
    │   │   └── SKILL.md          ← 修改已有四原语的步骤
    │   ├── export_bundle/
    │   │   └── SKILL.md          ← 导出 role bundle 的步骤
    │   └── import_bundle/
    │       └── SKILL.md          ← 导入 role bundle 的步骤
    ├── deploy.sh
    └── start.sh
```

### 6. AgentForge 的 Skill 定义

#### 6.1 create_role — 创建新 Role

```
触发：用户说"创建一个任务管理 Agent"、"新建 role"等

步骤：
1. 询问 role 名称 → 例："task-manager"
2. 询问能力描述 → 生成 role/{name}/SOUL.md
3. 询问需要哪些工作流（可跳过）→ 对每个工作流调用 create_skill
4. 询问评估标准（可跳过）→ 在 commitment/eval.yaml 中添加条目
5. 执行 ./agent/deploy.sh

文件操作：
├── mkdir agent/role/{name}/
├── Write agent/role/{name}/SOUL.md
├── 可选：调用 create_skill 创建若干 skill
├── 可选：Edit agent/commitment/eval.yaml
└── Bash: ./agent/deploy.sh
```

#### 6.2 create_skill — 创建新 Skill

```
触发：用户说"添加一个创建任务的技能"、"新建 skill"等

步骤：
1. 询问 skill 名称 → 例："create_task"
2. 询问触发条件 → "用户说创建任务时"
3. 询问执行步骤 → "1. 获取标题 2. 调用 API 3. 返回结果"
4. 询问绑定哪些 role → 例：[default, admin]
5. 生成 SKILL.md 文件
6. 生成对应的 API 端点代码到 src/app.py
7. 在 flow.yaml 中注册 action → role 映射
8. 执行 ./agent/deploy.sh

文件操作（三件套 + deploy）：
├── mkdir agent/flow/{skill_name}/
├── Write agent/flow/{skill_name}/SKILL.md    ← 教 Agent 怎么做
├── Edit src/app.py                            ← 给 Agent 一个可调用的 API
├── Edit agent/flow/flow.yaml                  ← 告诉系统谁能用
└── Bash: ./agent/deploy.sh
```

> **核心模式**：每个 Skill = SKILL.md + API 端点 + flow.yaml 注册。参见 progressive-dev-guide-example.md Step 2.1~2.3。

#### 6.3 edit_primitives — 修改已有四原语

```
触发：用户说"修改 task-manager 的 SOUL"、"更新 flow.yaml"、"改一下 eval 标准"等

步骤：
1. 确认修改目标（role/scope/commitment/flow 中的哪个文件）
2. 读取当前内容展示给用户
3. 根据用户描述修改内容
4. 如果修改了 flow.yaml 或 skill 文件，执行 deploy.sh

文件操作：
├── Read 目标文件
├── Edit 目标文件
└── 可选：Bash: ./agent/deploy.sh
```

#### 6.4 export_bundle — 导出 Role Bundle

```
触发：用户说"导出 task-manager"、"打包 role"等

步骤：
1. 确认要导出的 role 名称
2. 收集相关文件：
   - role/{name}/SOUL.md
   - flow.yaml 中该 role 绑定的 action 列表
   - 对应的 flow/{skill}/SKILL.md 文件
   - commitment/eval.yaml 中相关条目
3. 复制到 {name}.bundle/ 目录

文件操作：
├── Read agent/flow/flow.yaml → 解析该 role 绑定的 action
├── mkdir {name}.bundle/
├── 复制 role/{name}/SOUL.md
├── 复制 flow/{skill}/SKILL.md（只复制该 role 绑定的 skill）
├── 提取 commitment/eval.yaml 相关条目
└── 生成 bundle/flow.yaml（只包含该 role 的 action 注册）
```

#### 6.5 import_bundle — 导入 Role Bundle

```
触发：用户说"导入 /path/to/task-manager.bundle"等

步骤：
1. 读取 bundle 目录
2. 冲突检测：
   - role/ 下是否已存在同名目录
   - flow/ 下是否有同名 skill
   - flow.yaml 中是否有同名 action
3. 有冲突 → 询问用户（覆盖 / 跳过 / 重命名）
4. 复制文件到 agent/ 对应位置
5. 将 bundle 的 flow.yaml 条目合并到现有 flow.yaml
6. 执行 deploy.sh

文件操作：
├── Read bundle 目录结构
├── Read agent/flow/flow.yaml → 检测冲突
├── 复制 role/{name}/SOUL.md
├── 复制 flow/{skill}/SKILL.md
├── Edit agent/flow/flow.yaml → 合并 action 注册
├── 可选：Edit agent/commitment/eval.yaml → 合并 eval 条目
└── Bash: ./agent/deploy.sh
```

### 7. AgentForge flow.yaml

```yaml
direct_actions:
  - action: create_role
    role: [agentforge]
    description: "Create a new role with SOUL.md"

  - action: create_skill
    role: [agentforge]
    description: "Create a new skill with SKILL.md and register in flow.yaml"

  - action: edit_primitives
    role: [agentforge]
    description: "Edit existing four primitive files"

  - action: export_bundle
    role: [agentforge]
    description: "Export a role and its skills as a bundle directory"

  - action: import_bundle
    role: [agentforge]
    description: "Import a role bundle into the current project"

  - action: check_health
    role: [agentforge]
    description: "Check app health status"
```

### 8. 用户旅程

```
用户对话                              AgentForge 操作                     产出物

"创建一个任务管理 Agent"
  │
  ├─ "名字？" → "task-manager"        mkdir role/task-manager/            role/task-manager/SOUL.md
  ├─ "描述？" → "管理团队任务"          Write SOUL.md
  ├─ "工作流？" → "创建、分配、查看"     mkdir flow/create_task/             flow/create_task/SKILL.md
  │                                    Write SKILL.md                      flow/assign_task/SKILL.md
  │                                    Edit src/app.py (加 API 端点)        flow/view_progress/SKILL.md
  │                                    ...                                  src/app.py (新增端点)
  ├─ "评估标准？" → "跳过"
  ├─ 更新 flow.yaml                    Edit flow.yaml                      flow/flow.yaml (更新)
  └─ 编译                              Bash: ./agent/deploy.sh             .runtime/agents/task-manager/

"导出 task-manager"
  │
  └─ 打包                              复制文件到 bundle/                   task-manager.bundle/

"给 task-manager 加个优先级排序"
  │
  ├─ 创建 skill                        mkdir flow/prioritize_task/         flow/prioritize_task/SKILL.md
  ├─ 生成 API 端点                      Edit src/app.py                     src/app.py (新增端点)
  ├─ 更新注册                           Edit flow.yaml                      flow/flow.yaml (更新)
  └─ 编译                              Bash: ./agent/deploy.sh             .runtime/ (更新)
```

### 9. 设计约束

- AgentForge 是 **runtime-agnostic** 的——SOUL.md 和 SKILL.md 是指令，任何支持文件操作的 Agent Runtime 都能执行
- P1 阶段**不需要后端 API**——Agent Runtime 内置的文件操作能力即可
- AgentForge 操作 `agent/` 目录下的四原语文件，同时生成 `src/app.py` 中对应的 API 端点代码（`.runtime/` 由 deploy.sh 生成，不直接操作）
- 所有破坏性操作（删除 role、覆盖导入）需要在对话中确认
- 导出的 bundle 不包含 `.runtime/`，接收方通过 deploy.sh 重新编译

---

## 第三部分：Phase 2 — 完善 Flow（Chat UI + Chat API + Adapter Query）

### 目标

为 Socialware 提供浏览器 Chat 界面。Chat 本身是一个简单的 IM 窗口，用户输入 `/agentforge` 命令后连接 Agent Runtime，开始和 AgentForge 对话。

### 核心理念

- **Chat 是 IM，不依赖 Agent** — 没有 Agent 环境也能打开 Chat 窗口
- **Agent 按需注册** — 用户输入斜杠命令（如 `/agentforge`）时才检测环境、连接 Runtime
- **单 session** — 一次只对接一个 role
- **不管对话历史持久化** — 对话历史由 Agent Runtime（Claude Code/Codex/Kimi）自己管理，AgentForge 只管 session

### 触发条件

P1 的 Agent 只能通过终端 TUI 对话，用户需要浏览器界面时进入 P2。

### Adapter 扩展

BaseAdapter 新增 `query()` 和 `is_available()` 方法：

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
        """Send a prompt to Agent Runtime, return response messages.
        Returns: [{"type": "text", "text": "..."}]
        """
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this adapter's runtime is installed."""
        ...
```

三个 adapter 各自实现 query()：

| Adapter | query() 实现 | is_available() 检测 |
|---------|-------------|-------------------|
| Claude | `claude_code_sdk.query()` | `shutil.which("claude")` |
| Codex | openai agents SDK | `shutil.which("codex")` |
| Kimicode | kimi CLI subprocess | `shutil.which("kimi")` |

### 后端 API

```
# 已有
GET  /health                     ← 健康检查

# Session 管理（Agent 按需连接）
POST   /session                  ← 创建 Agent session（指定 role + adapter）
GET    /session                  ← 获取当前 session 信息
DELETE /session                  ← 关闭当前 session

# Chat（需要活跃 session）
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

工作流程：

```
浏览器                         后端 src/app.py              Agent Runtime
  │                                │                             │
  │ 用户输入 /agentforge            │                             │
  │                                │                             │
  │ GET /adapters                  │                             │
  │───────────────────────────────>│ 检测可用 adapter              │
  │ {adapters: [{name:"claude",    │                             │
  │   available: true}, ...]}      │                             │
  │<───────────────────────────────│                             │
  │                                │                             │
  │ POST /session                  │                             │
  │ {role:"agentforge",            │                             │
  │  adapter:"claude"}             │                             │
  │───────────────────────────────>│ 加载 adapter + role 配置     │
  │ {status:"created"}             │                             │
  │<───────────────────────────────│                             │
  │                                │                             │
  │ POST /chat                     │                             │
  │ {message:"创建一个..."}         │                             │
  │───────────────────────────────>│ adapter.query(message)      │
  │                                │────────────────────────────>│
  │                                │                             │ 执行 Skill
  │                                │         Agent 回复           │
  │                                │<────────────────────────────│
  │ {messages:[{type:"text",       │                             │
  │   text:"好的，请确认..."}]}     │                             │
  │<───────────────────────────────│                             │
```

### 前端 Chat UI

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

页面交互：

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

交互规则：
1. 初始状态 — Chat 窗口打开，未连接 Agent，输入框可用
2. 用户输入 `/agentforge` — 检测 adapter → POST /session → 连接成功
3. 连接后输入普通消息 → POST /chat → 显示 Agent 回复
4. 未连接时输入普通消息 → 只在本地显示（不发送）
5. 输入 `/disconnect` → DELETE /session → 断开连接

### 开发顺序

```
Step 1: BaseAdapter 加 query() + is_available() + 三个 adapter 实现 → 单元测试
Step 2: 后端 API（/session, /chat, /adapters, 四原语查询） → curl 测试
Step 3: 前端 Next.js 项目初始化 + Chat UI 组件 → 浏览器联调
```

---

## 第四部分：Phase 3 — 完善 Commitment（加评估标准 + 监控端点）

### 目标

定义评估标准（eval.yaml），添加监控 API 端点（/metrics），让系统能衡量 Agent 的表现。

### 触发条件

App 能用了（P2），但不知道用得好不好。用户抱怨"提交了任务没人审核"→ 需要定义 SLA 标准并监控。

### 需要实现

#### Eval 执行引擎

```python
# src/eval.py — 评估执行器
class EvalRunner:
    def run(self, commitment_id: str) -> EvalResult:
        """读取 eval.yaml 中的标准，执行评估，返回结果"""
        ...
```

#### Eval 触发方式

| 方式 | 说明 | 示例 |
|------|------|------|
| 手动触发 | 用户说"评估 task-manager" | AgentForge Skill |
| 定时触发 | Cron 定期执行 | 每天检查一次 |
| 事件触发 | 某个 action 完成后自动评估 | 任务完成后检查满意度 |

#### eval.yaml 增强

```yaml
commitments:
  C1:
    description: "Customer satisfaction ≥ 4.5"
    metric: customer_rating
    threshold: ">=4.5"
    eval_method: sql                 ← 新增：评估方法
    eval_query: >                    ← 新增：具体查询
      SELECT AVG(rating) FROM feedback
      WHERE created_at > datetime('now', '-7 days')
  C2:
    description: "Task completion within 72h"
    metric: time_to_complete
    threshold: "72h"
    eval_method: api                 ← 新增
    eval_endpoint: "GET /tasks/metrics/completion_time"
```

#### Eval 结果存储

```
.runtime/data/Sqlite/socialware.db
└── eval_results                     ← 评估结果历史
    ├── commitment_id
    ├── result (pass/fail)
    ├── value (实际值)
    ├── threshold (目标值)
    └── evaluated_at
```

#### AgentForge 新增 Skill

```
flow/evaluate/SKILL.md               ← 手动触发评估
flow/eval_report/SKILL.md            ← 生成评估报告
```

---

## 第五部分：Phase 4 — 扩大 Scope（扩展能力边界 + 多 Workspace + Evolve）

### 目标

App 的能力边界扩大——scope/SOUL.md 描述更多能力，添加更多面向团队的功能。同时支持多租户（Workspace），Evolve 机制自动发现改进并通过 PR 回馈主库。

### 触发条件

App 核心功能已稳定（P2+P3），但需要覆盖更广的场景。例如：从个人任务管理扩展到团队协作（分配、通知、排序）。

### scope/SOUL.md 随阶段更新

```markdown
# AgentForge（P4 扩展后）

Agent 创建与管理平台。

## Capabilities

- 创建 Agent role（SOUL.md）
- 创建 Agent skill（SKILL.md + API 端点 + flow.yaml 注册）
- 修改已有四原语文件
- 导出/导入 Agent bundle                    ← P4 新增
- 多 workspace 管理                          ← P4 新增
- Agent 配置自动优化（Evolve）                ← P4 新增

## Boundaries

- 只管理 agent/ 和 src/ 文件，不管理 .runtime/
- 不监控 Agent 运行状态
```

### 需要实现

#### Socialware Dashboard

一个 Web 界面管理 Workspace 的 CRUD：

```
┌─ Socialware Dashboard ──────────────────────────────┐
│                                                      │
│  Workspaces                              [+ Create]  │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ default      │  │ cinnox       │                  │
│  │ ✓ running    │  │ ○ stopped    │                  │
│  │ 3 roles      │  │ 2 roles      │                  │
│  │ [Open]       │  │ [Open]       │                  │
│  └──────────────┘  └──────────────┘                  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

| 操作 | 后端 | 说明 |
|------|------|------|
| Create | `POST /workspaces` | 新 branch + worktree + 复制模板 + deploy |
| Delete | `DELETE /workspaces/{name}` | 清理 worktree + .runtime |
| Update | `POST /workspaces/{name}/sync` | merge / rebase from main |
| List | `GET /workspaces` | 列出所有 workspace |

#### Evolve Skill 落地

```
flow/evolve/SKILL.md                 ← Evolve 技能

触发：用户说"evolve"、定时触发

步骤：
1. 读取 eval_results（P3 的评估结果）
2. 分析 Workspace DB 中的数据
3. 识别改进机会
4. 修改四原语文件
5. 路由判断：
   - 修改在 .runtime/ → 租户特定适配，不触发 PR
   - 修改在 agent/ → 通用改进，自动创建 PR 回 main
```

#### Evolve 产出物路由

```
Evolve 结果
    │
    ├── 修改 .runtime/ 中的数据？
    │   └── YES → 租户特定，留在 Workspace DB
    │
    └── 修改 agent/ 四原语文件？
        └── YES → 通用改进
            ├── 检测 git diff
            ├── 自动创建 branch
            └── 自动创建 PR → main
                └── main 合并后，所有 workspace merge/rebase 获得改进
```

---

## 第六部分：Phase 5 — 扩充 Role（多 Role + 状态机协作）

### 目标

单个 App 内多个 Role 协作完成复杂任务。通过 flow.yaml 状态机定义角色间的工作流转。

### 触发条件

当一个 role 无法独立完成所有工作时——例如 AgentForge 创建的 Agent 配置需要有人审核后才能生效。

### 需要实现

#### 新增 Role

```bash
mkdir agent/role/reviewer
vim agent/role/reviewer/SOUL.md       # Agent 配置审核者
```

#### 多 Role 协作

```yaml
# flow.yaml — 状态机定义多 role 协作
flows:
  F1:
    name: agent_review
    description: "Agent 创建需要 reviewer 审核"
    transitions:
      - { from: _none_,    action: create_role,  to: draft,    role: [agentforge] }
      - { from: draft,     action: review,       to: reviewed, role: [reviewer] }
      - { from: reviewed,  action: approve,      to: approved, role: [reviewer] }
      - { from: reviewed,  action: reject,       to: draft,    role: [reviewer] }
      - { from: approved,  action: deploy,       to: deployed, role: [agentforge] }
```

新增 role 示例：

```
agent/role/
├── agentforge/SOUL.md     ← Agent 创建者
├── reviewer/SOUL.md       ← Agent 配置审核者
└── dev/SOUL.md            ← 开发者（环境配置）
```

---

## 第七部分：Phase 0 — ZChat 互联

### 目标

多个 Socialware App 之间的 Agent 可以直接通信。AgentForge 创建的 Agent 可以被其他 App 调用。

### 需要实现

#### ZChat 通信层

```
┌──────────────┐                    ┌──────────────┐
│  AgentForge  │  ←── /zchat ───>   │  TaskArena   │
│              │  Agent 间 P2P      │              │
│  "创建一个   │  Zenoh 通信         │  "我需要一个 │
│   Agent"     │                    │   新的 role"  │
└──────────────┘                    └──────────────┘
```

#### /zchat 协议

```yaml
# ZChat 消息格式
zchat_message:
  from: taskarena.socialware.app/default
  to: agentforge.socialware.app/agentforge
  intent: create_role
  payload:
    name: "notifier"
    description: "发送通知的 Agent"
  reply_to: "zenoh://taskarena/inbox"
```

#### 三种交互模式全部落地

| # | 模式 | 实现方式 | 阶段 |
|---|------|----------|------|
| 1 | 页面 / API | HTTP 调用 src/app.py | P2 |
| 2 | /ask-agent | 浏览器 Chat UI 直接和 Agent 对话 | P2 |
| 3 | /zchat | Zenoh P2P，Agent 间直连 | P0 |

#### AgentForge 作为 ZChat 服务方

其他 Socialware App 可以通过 /zchat 请求 AgentForge 创建 Agent：

```
TaskArena Agent → /zchat → AgentForge Agent
"我需要一个 notifier role 来发送任务提醒"

AgentForge 执行 create_role Skill：
1. 创建 role/notifier/SOUL.md
2. 创建 flow/send_notification/SKILL.md
3. 更新 flow.yaml
4. deploy.sh
5. 通过 /zchat 回复 TaskArena："notifier 已创建"
```

#### SOUL.md 可发现性

每个 Socialware App 的 `scope/SOUL.md` 作为公开描述，供其他 Agent 发现和理解该 App 的能力：

```
AgentForge 的 scope/SOUL.md：
  "我可以创建和管理 Agent 的四原语配置"

TaskArena 的 scope/SOUL.md：
  "我可以管理和跟踪团队任务"
```

其他 Agent 读取 SOUL.md 后，知道该向谁请求什么服务。

---

## 阶段总览

```
P1  纯 CLI/Chat               P2  完善 Flow               P3  完善 Commitment
┌──────────────┐             ┌──────────────┐            ┌──────────────┐
│ AgentForge   │             │ 加 Skill     │            │ eval.yaml    │
│ 5 个 Skill   │────────────>│ 加 API 端点  │───────────>│ /metrics 端点│
│ 直接操作文件  │             │ Chat UI      │            │ 监控 + 提醒  │
│ 终端 TUI     │             │ 对话历史     │            │              │
└──────────────┘             └──────────────┘            └──────────────┘
                                                              │
P0  ZChat 互联               P5  扩充 Role              P4  扩大 Scope
┌──────────────┐             ┌──────────────┐            ┌──────────────┐
│ Zenoh P2P    │             │ 加 role      │            │ scope 扩展   │
│ Agent 间直连  │<────────────│ 状态机协作    │<───────────│ Dashboard    │
│ SOUL.md 发现 │             │ flow.yaml    │            │ Evolve Skill │
│ 跨 App 协作  │             │ 角色权限     │            │ 多租户隔离   │
└──────────────┘             └──────────────┘            └──────────────┘
```

### 阶段详情

| 阶段 | 触发条件 | 核心交付 | AgentForge 的变化 |
|------|----------|----------|-------------------|
| **P1** | 项目创建后 | 5 个 Skill + 终端 TUI | 直接操作 agent/ + src/ 文件 |
| **P2** | Agent 说"我不会" | 加 Skill + API 端点 + Chat UI | 可通过浏览器对话，Biz 层随 Skill 增长 |
| **P3** | 用户抱怨质量 | eval.yaml + /metrics + 提醒 Skill | 新增 evaluate / eval_report Skill |
| **P4** | 需要更广的能力 | scope 扩展 + Dashboard + Evolve | 多 workspace 管理，evolve 自动优化 |
| **P5** | 一个 role 忙不过来 | 加 role + flow.yaml 状态机 | 新增 reviewer role，支持审核流程 |
| **P0** | 触达 App 边界 | ZChat + SOUL.md 发现 | 其他 App 可通过 /zchat 请求创建 Agent |

### 每个 Phase 的核心模式

```
edit agent/     →  edit src/app.py  →  deploy.sh  →  start.sh
(四原语文件)        (API 端点)          (编译)        (启动)
```

每次 App 成长 = 加 SKILL.md + 加 API 端点 + 注册 flow.yaml。Biz 层（src/app.py）随四原语同步增长。
