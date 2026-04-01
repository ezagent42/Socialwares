---
name: manage_role
description: "Add, edit, list, delete roles for an Agent"
---

# Manage Role

## Trigger

用户提到为某个 Agent 添加、编辑、查看、删除角色时触发。

## Prerequisites

必须先确定目标 Agent。如果上下文不明确：
- 数据库中只有一个 Agent → 自动选中
- 多个 → 询问用户

## Flow

### Create
1. 提取角色名称
2. 调用 `role_crud.create_role(agent_id, name, soul_md)`
3. 返回结构化数据

### Update
1. 确定目标角色，获取当前内容
2. 调用 `role_crud.update_role(role_id, soul_md)`
3. 返回结构化数据

### List
1. 调用 `role_crud.list_roles(agent_id)`

### Delete
1. 确认不是唯一角色（至少保留一个）
2. 调用 `role_crud.delete_role(role_id)`

## Structured Response

- type: "role"
- action: "created" | "updated" | "listed" | "deleted"

## Constraints

- 每个 Agent 至少保留一个角色
- 角色名在同一 Agent 内唯一
