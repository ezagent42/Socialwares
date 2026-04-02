---
name: manage_agent
description: "Create, list, view, delete Agent configurations"
---

# Manage Agent

## Trigger

用户提到创建、查看、列出、删除 Agent 时触发。

示例:
- "创建一个 task-manager"
- "列出所有 Agent"
- "删除 chatbot"
- "查看 task-manager 的详情"

## Flow

### Create

1. 从用户输入提取 name 和 description
2. 调用 `agent_crud.create_agent(user_id, name, description)`
   - 自动创建默认 scope（空模板）
   - 自动创建 default 角色（空 role md）
   - 自动注册 check_health 技能
3. 返回结构化数据

### List

1. 调用 `agent_crud.list_agents(user_id)`
2. 返回结构化数据（包含每个 Agent 的概要信息）

### Get

1. 确定目标 Agent（按名称查找）
2. 调用 `agent_crud.get_agent(user_id, agent_id)`
3. 返回结构化数据（包含 roles, skills, scope, commitment 详情）

### Delete

1. 确定目标 Agent
2. 向用户确认删除操作
3. 用户确认后调用 `agent_crud.delete_agent(user_id, agent_id)`
4. 返回结构化数据

## Structured Response

每次操作后返回 ```json:structured 代码块:
- type: "agent"
- action: "created" | "listed" | "deleted"
- data: { id, name, description, roles, skills }

## How to Execute

Use the CRUD CLI via Bash tool:

```bash
# Create
uv run python -m src.crud.cli create-agent --db "$DB_PATH" --user-id "$USER_ID" --name "xxx" --role-md "# xxx"

# List
uv run python -m src.crud.cli list-agents --db "$DB_PATH" --user-id "$USER_ID"

# Get
uv run python -m src.crud.cli get-agent --db "$DB_PATH" --user-id "$USER_ID" --agent-id "xxx"

# Delete
uv run python -m src.crud.cli delete-agent --db "$DB_PATH" --user-id "$USER_ID" --agent-id "xxx"
```

## Error Handling

- 名称重复: "Agent 'task-manager' 已存在，请使用其他名称"
- 不存在: "未找到名为 'xxx' 的 Agent"
