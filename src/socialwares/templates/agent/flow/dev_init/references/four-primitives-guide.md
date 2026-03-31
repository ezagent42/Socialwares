# 四原语构建参考

Socialware 用四个原语描述一个 Agent App 的完整结构。每个原语回答一个核心问题。

---

## 1. Scope（能力边界）—— "这个 App 能做什么？"

**为什么需要**：Scope 是 App 的契约边界。Agent 只做 scope 声明的事，不做没声明的事。这保证了 App 的可预测性和安全性。

**文件**：`agent/scope/scope.md`

**写法要点**：
- Capabilities：列出 App 实际能做的事（和 API 端点对应）
- Boundaries：明确 App 不做什么（比如"不直接操作数据库"）
- Connections：如果和其他 App 协作，声明通过 IRC @mention 的连接

```markdown
# Task Review App

帮助团队管理任务的创建、分配和审核流程。

## Capabilities
- 创建任务（POST /api/tasks）
- 查看任务列表（GET /api/tasks）
- 审核任务（POST /api/tasks/{id}/review）
- Health check（GET /health）

## Boundaries
- 不发送通知（通知由 @notification-bot 处理）
- 不管理用户权限

## Connections
- @notification-bot — 任务状态变更时通知相关人员
```

---

## 2. Role（角色）—— "谁在用这个 App？"

**为什么需要**：不同角色有不同的权限和视角。Agent 根据自己的 role 决定能用哪些 skill、以什么身份和用户对话。

**文件**：`agent/role/{name}.md`（每个角色一个文件）

**写法要点**：
- Identity：角色是谁，一句话说清
- Responsibilities：这个角色负责什么
- 语气和风格：技术型？友好型？严格型？

```markdown
# Reviewer Agent

负责审核和批准团队提交的任务。

## Identity
- 角色：任务审核员
- 权限：查看任务、审核任务、退回任务

## Responsibilities
1. 及时审核提交的任务（24h 内）
2. 给出清晰的审核意见
3. 退回不合格的任务并说明原因

## Style
- 严谨但友好
- 审核意见要具体，不要只说"不通过"
```

**内置角色**（模板自带，不需要手动创建）：
- `default` — 默认业务角色
- `dev` — 开发辅助角色（inspect, build, iterate, release）
- `evolver` — 分析和改进角色（structure check, evaluate, diagnose, improve）

---

## 3. Flow（操作）—— "每个角色能做什么？怎么做？"

**为什么需要**：Flow 定义了 Agent 的行为——收到什么指令时，执行什么步骤。每个操作对应一个 SKILL.md 文件。

**目录结构**：
```
agent/flow/{action}/
├── SKILL.md           ← 必须：触发条件 + 执行步骤
├── scripts/           ← 可选：自动化脚本
└── references/        ← 可选：参考文档
```

**SKILL.md 写法要点**：
- Trigger：用户说什么时触发（中英文都写）
- Flow：步骤化的执行流程，明确调用哪些 API
- Error Handling：出错时怎么处理

```markdown
---
name: create_task
description: "Create a new task"
---

# Create Task

## Trigger
User says "create task", "新建任务", "add task" etc.

## Flow
1. Ask user for task title and description
2. Call API: POST /api/tasks {"title": "...", "description": "..."}
3. If success: show task ID and confirm
4. If error: explain what went wrong

## Error Handling
- 400: "Task title is required"
- 500: "Server error, please try again"
```

**注册**：在 `socialware.py` 中 `app.action("create_task", role=["default"])`

**流转（可选）**：如果操作之间有固定的状态流转：
```python
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
```

---

## 4. Commitment（约束）—— "角色之间怎么协作？"

**为什么需要**：多角色协作时，需要约束来保证服务质量。比如"提交后 24h 内必须审核"——如果没有 commitment，evolver 就无法发现审核延迟的问题。

**定义位置**：在 `socialware.py` 中声明（不是单独文件）

**写法要点**：
- from_：触发方（哪个角色的哪个操作）
- to：响应方（哪个角色应该做什么）
- condition：自然语言条件（evolver 用 LLM 判断是否满足）
- on_violation：违反时的补救操作

```python
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

**含义**：当 default 角色执行了 submit_task 后，reviewer 角色应该在 24 小时内执行 review_task。如果没有，则触发 remind_review 操作。

**注意**：
- Commitment 只有 evolver 能看到和评估
- condition 是自然语言，evolver（LLM）负责判断
- 如果 App 只有一个角色，可以不写 commitment

---

## 四原语的关系

```
Scope    → 能力边界（App 做什么）
  ↓
Role     → 角色定义（谁来做）
  ↓
Flow     → 操作定义（怎么做）+ 流转（什么顺序做）
  ↓
Commitment → 协作约束（做了之后期望什么）
```

Scope 约束 Flow（不在 scope 里的功能不应该有对应的 action）。
Role 决定 Flow（每个 action 分配给哪些 role）。
Commitment 连接 Role（角色 A 做了什么后，角色 B 应该怎样响应）。
