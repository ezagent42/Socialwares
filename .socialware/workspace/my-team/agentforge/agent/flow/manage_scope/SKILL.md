---
name: manage_scope
description: "View and update an Agent's scope definition"
---

# Manage Scope

## Trigger

用户提到查看或修改某个 Agent 的 scope / 能力边界时触发。

## Flow

### Get
1. 调用 `scope_crud.get_scope(agent_id)`
2. 返回当前 scope.md 内容

### Update
1. 根据用户指令修改
2. 调用 `scope_crud.update_scope(agent_id, soul_md)`

## Structured Response

- type: "scope"
- action: "updated"

## Notes

每个 Agent 只有一个 scope，无 create/delete 操作。
