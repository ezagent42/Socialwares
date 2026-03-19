# Flow — How

定义 Agent 可执行的操作 (Skills)。

## 结构

每个操作一个子目录，包含 `SKILL.md`:

```
flow/
├── check_health/
│   └── SKILL.md
├── create_task/
│   ├── SKILL.md
│   └── scripts/       ← 可选: 辅助脚本
└── review_task/
    └── SKILL.md
```

## SKILL.md 格式

```yaml
---
name: action_name
description: "操作描述"
---
```

后面跟 Markdown 内容，描述:
- 触发条件 (用户说什么时触发)
- 执行流程 (步骤)
- API 调用 (curl 示例)
- 权限要求

## deploy.sh 处理

`flow/` 下每个 skill 目录会被软连接到
`.runtime/agents/{role}/.claude/skills/{skill_name}/`。

## 注意

- 状态机由 App (`src/`) 管理，不在 flow/ 中定义
- 权限由 App API 检查，flow/ 中的权限说明仅供 Agent 参考
