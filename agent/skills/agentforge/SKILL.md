---
name: agentforge
description: "AgentForge Socialware App — Agent 生命周期管理、模板、staffing、多平台适配"
---

# AgentForge

Agent 管理 Socialware App。管理 agent 的 spawn/sleep/wake/destroy 生命周期，
支持模板系统、parent-child 层级、和多平台适配 (Claude, Codex, KimiCode)。

## Commands

| 命令 | 说明 | 需要角色 |
|------|------|----------|
| /agentforge spawn | 从模板创建 agent | R2 (操作者) |
| /agentforge wake | 唤醒 sleeping agent | R2 (操作者) |
| /agentforge sleep | 休眠 agent | R2 (操作者) |
| /agentforge destroy | 销毁 agent | R2 (操作者) |
| /agentforge list | 查看 agent 列表 | 所有角色 |
| /agentforge config | 配置 agent | R1 (管理员) |
| /agentforge download | 下载 agent 模板 | R1 (管理员) |
| /agentforge generate | 从角色配置生成 agent | R1 (管理员) |

## 四原语

### Role (角色)

- R1 管理员 (af:admin): register-template, config, spawn, destroy, query, audit
- R2 操作者 (af:operator): spawn, destroy, sleep, wake, list, query
- R3 观察者: query, list

### Flow (状态机)

```
created → [spawn] → active ⇄ [sleep/wake] → sleeping
                        → [destroy] → destroyed
```

### Commitment (承诺)

- C1: Agent 响应 @mention 后 5min 内开始处理 (SLA)

### Arena (作用域)

- 基于 Room 成员身份
- parent-child: 子 agent 权限 ≤ 父 agent

## Usage

```bash
# 从模板创建 agent
uv run agent/skills/agentforge/scripts/spawn_agent.py --template code-reviewer --name reviewer-1

# 唤醒 agent
uv run agent/skills/agentforge/scripts/wake_agent.py --name reviewer-1

# 列出所有 agent
uv run agent/skills/agentforge/scripts/list_agents.py

# 下载 agent 模板
uv run agent/skills/agentforge/scripts/download_template.py --source "github:ezagent42/templates/code-reviewer"

# 从角色配置生成 agent
uv run agent/skills/agentforge/scripts/generate_from_roles.py --config ../taskarena/config.yaml
```
