# 四原语构建参考

## Scope（能力边界）

文件：`agent/scope/scope.md`

```markdown
# App Name

Description of what this app does.

## Capabilities
- Capability 1
- Capability 2

## Boundaries
- What the app does NOT do

## Connections
- External apps via IRC @mention
```

## Role（角色）

文件：`agent/role/{name}.md`

```markdown
# {Name} Agent

One-line description.

## Identity
- Role: {name}
- Permissions: list

## Responsibilities
1. Responsibility 1
2. Responsibility 2
```

## Flow（操作）

目录：`agent/flow/{action}/SKILL.md`

```markdown
---
name: {action_name}
description: "One-line description"
---

# Action Name

## Trigger
User says "...", "..." etc.

## Flow
1. Step 1
2. Call API: POST /api/endpoint
3. Return result to user

## Error Handling
- If API returns error: explain to user
```

注册：`socialware.py` 中 `app.action("name", role=[...])`

## Commitment（约束）

在 `socialware.py` 中声明：

```python
app.commitment("C1",
    from_=("role_a", "action_a"),
    to=("role_b", "action_b"),
    condition="within 24h",
    on_violation=("role_c", "escalate"),
)
```
