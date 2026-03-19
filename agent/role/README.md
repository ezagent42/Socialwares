# Role — Who

定义 Subagent 身份与权限。

## 结构

每个角色一个子目录，包含 `SOUL.md`:

```
role/
├── default/
│   └── SOUL.md      ← Agent 身份描述
├── admin/
│   └── SOUL.md
└── reviewer/
    └── SOUL.md
```

## SOUL.md 内容

描述该角色的:
- 身份和名称
- 拥有的权限 (哪些 action 可以触发)
- 职责说明

## deploy.sh 处理

`deploy.sh` 会为每个 role 生成独立的 `$PROJECT_DIR`:
- 合并 `scope/SOUL.md` + `role/{name}/SOUL.md` → `.runtime/agents/{name}/SOUL.md`
- 软连接 `flow/` 下所有 skill → `.runtime/agents/{name}/.claude/skills/`
