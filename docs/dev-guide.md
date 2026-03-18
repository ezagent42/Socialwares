# Socialwares 开发指南

## 概览

Socialwares 是面向 agent 的协作应用 MonoRepo。每个 App 通过四原语
(Role/Flow/Commitment/Arena) 暴露 API，agent 通过 skills 和 adapters 调用。

## 项目结构

```
Socialwares/
├── apps/                   ← SW App 本体 (Python FastAPI server)
│   ├── taskarena/          ← 任务管理
│   └── agentforge/         ← Agent 管理
├── agent/                  ← GitAgent 格式 agent 定义
│   ├── agent.yaml          ← 身份和模型配置
│   ├── SOUL.md             ← Agent 人格
│   ├── skills/             ← 技能 (SKILL.md + config.yaml + scripts/)
│   ├── adapters/           ← SDK 启动模板 (Claude/Codex/KimiCode)
│   ├── tools/              ← MCP 工具定义
│   ├── agents/             ← 子 agent 定义 (从 AgentForge 下载)
│   └── knowledge/          ← 参考文档
├── scenarios/              ← 多 agent 场景编排
├── scripts/                ← 运维和适配脚本
└── docs/                   ← 文档
```

## 快速开始

### 1. 环境配置

```bash
gh repo clone ezagent42/Socialwares
cd Socialwares

# 配置 Claude Code (创建 .claude/skills/ symlink)
./scripts/setup-claude.sh

# 安装依赖
uv sync
```

### 2. 启动 Mock 服务

```bash
# TaskArena (端口 8001)
uv run --package taskarena uvicorn taskarena.app:app --port 8001

# AgentForge (端口 8002)
uv run --package agentforge uvicorn agentforge.app:app --port 8002
```

### 3. 开发模式 (Claude Code CLI)

```bash
claude
# 然后在 Claude Code 里使用 /taskarena /agentforge 命令
```

### 4. Agent 模式 (SDK)

```bash
# 单 agent
./scripts/launch.sh --adapter claude

# 多 agent 场景
./scripts/launch-scenario.sh scenarios/examples/task-review.yaml
```

## 四原语开发规范

每个 SW App 必须定义四原语，在 `agent/skills/{app}/config.yaml` 中声明：

### Role (角色)

```yaml
roles:
  R1:
    name: admin
    label: "管理员"
    permissions: [create, read, update, delete, close]
```

- 每个角色有唯一 ID (R1, R2, ...)
- permissions 列表定义允许的操作
- pre_send hook 根据角色检查权限

### Flow (状态机)

```yaml
flow:
  name: entity_lifecycle
  states: [draft, active, closed]
  transitions:
    - from: draft
      to: active
      action: activate
      role: R1
```

- 每个 transition 指定 from/to/action/role
- 非法 transition 被 API 拒绝 (HTTP 409)
- 状态机图推荐用 Mermaid 画在 SKILL.md 里

### Commitment (承诺)

```yaml
commitments:
  C1:
    description: "描述承诺内容"
    trigger_state: submitted
    deadline_hours: 72
    escalation_role: R1
```

- trigger_state: 哪个状态触发计时
- deadline_hours: 超时时间
- escalation_role: 超时后升级给谁

### Arena (作用域)

```yaml
arena:
  min_members: 2
  scope: room        # room | global | custom
  open: false        # 是否允许外部加入
```

## 创建新 SW App

### Checklist

1. `apps/{name}/pyproject.toml` — 项目配置
2. `apps/{name}/src/{name}/app.py` — FastAPI 应用
3. `agent/skills/{name}/SKILL.md` — 技能文档
4. `agent/skills/{name}/config.yaml` — 四原语定义
5. `agent/skills/{name}/scripts/` — API 调用脚本
6. `agent/tools/{name}-api.yaml` — MCP 工具定义
7. `agent/skills/{name}/references/` — API 参考文档
8. `tests/test_{name}.py` — 测试

### 步骤

```bash
# 1. 创建 App 目录
mkdir -p apps/myapp/src/myapp
touch apps/myapp/src/myapp/__init__.py

# 2. 创建 skill 目录
mkdir -p agent/skills/myapp/{scripts,references}

# 3. 定义四原语 (编辑 config.yaml)
cat > agent/skills/myapp/config.yaml << 'EOF'
domain: myapp
api_url: http://localhost:8003
roles:
  R1: {name: admin, label: "管理员", permissions: [all]}
  R2: {name: user, label: "用户", permissions: [read, create]}
flow:
  name: myapp_lifecycle
  states: [draft, active, closed]
  transitions: []
commitments: {}
arena: {scope: room}
EOF

# 4. 写 SKILL.md
# 5. 写 scripts/
# 6. 写测试
# 7. 自举: 用 /taskarena 追踪这些开发任务
```

## Agent 适配

### 支持的平台

| 平台 | 适配器 | SDK | 状态 |
|------|--------|-----|------|
| Claude | `agent/adapters/claude/` | claude-agent-sdk | Mock |
| Codex | `agent/adapters/codex/` | openai-agents | Mock |
| KimiCode | `agent/adapters/kimicode/` | kimicode-sdk | Mock |

### 添加新适配器

1. 创建 `agent/adapters/{name}/launcher.py`
2. 继承 `agent/adapters/base.py:BaseAdapter`
3. 实现 `build_system_prompt()`, `launch()`, `launch_headless()`
4. 创建 `requirements.txt`
5. 在 `agent/skills/agentforge/config.yaml` 的 adapters 中注册

### SKILL.md 的 allowed-tools 字段

SKILL.md frontmatter 支持可选的 `allowed-tools` 字段，用于声明该技能需要的工具权限：

```yaml
---
name: taskarena
description: "TaskArena Socialware App"
allowed-tools: "Bash"
---
```

当前项目使用 `bypassPermissions` 模式，所以 `allowed-tools` **不需要设置**。
但如果将来切换到更严格的权限模式，需要在每个 SKILL.md 中添加此字段。

常见值:
- `"Bash"` — 允许执行 bash 命令 (scripts/)
- `"Bash(taskarena:*)"` — 只允许特定命名空间的命令
- `"Read,Grep,Bash"` — 多个工具用逗号分隔

## 多 Agent 场景

### 场景 YAML 格式

```yaml
name: scenario-name
description: "描述"
bus: {type: local, endpoint: localhost:8080}
agents:
  - name: agent-name
    template: agent/agents/template-dir
    adapter: claude
    roles: [app:R1]
    auto_start: true
workflow:
  - agent-name: "/command args"
```

### 从角色自动生成 Agent

```bash
# 从 TaskArena 角色配置生成 agent 定义
uv run agent/skills/agentforge/scripts/generate_from_roles.py \
  --config agent/skills/taskarena/config.yaml

# 生成的 agent 在 agent/agents/
ls agent/agents/
# taskarena-admin/  taskarena-submitter/  taskarena-reviewer/
```

## 自举开发模式

```
Iteration 0: 基础环境 → Claude Code 写代码
Iteration 1: TaskArena 可用 → /taskarena 管理开发任务
Iteration 2: AgentForge 可用 → /agentforge 管理开发 agent
Iteration 3: Adapters 可用 → launch.sh 启动 headless agent
```

每一步都在用上一步的产出开发下一步。这就是 Socialware 的自举。

## 常用命令

```bash
# 开发
uv sync                                           # 安装依赖
uv run pytest                                     # 运行测试
uv run --package taskarena uvicorn taskarena.app:app --port 8001  # 启动 TA

# Agent
./scripts/setup-claude.sh                         # 配置 Claude Code
./scripts/launch.sh --adapter claude              # 启动单 agent
./scripts/launch-scenario.sh scenarios/xxx.yaml   # 多 agent 场景

# 生成
uv run agent/skills/agentforge/scripts/generate_from_roles.py --config ...
```
