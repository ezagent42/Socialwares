---
name: dev
description: "Socialwares 开发者技能 — 项目开发工作流、四原语参考、自举指南"
---

# Socialwares Dev Skill

Socialwares 项目开发专用技能。

## 开发工作流

1. **创建 App**: 在 `apps/{name}/` 下创建新 SW App
2. **定义四原语**: 在 `agent/skills/{name}/config.yaml` 中定义 Role/Flow/Commitment/Arena
3. **写 SKILL.md**: 在 `agent/skills/{name}/SKILL.md` 中写技能文档
4. **写 scripts/**: 在 `agent/skills/{name}/scripts/` 中写 API 调用脚本
5. **测试**: `uv run pytest tests/`
6. **自举**: 用已开发的 skills 管理后续开发

## 自举循环

```
Iteration 0: 基础 Claude Code 配置
Iteration 1: TaskArena → 用 /taskarena 管理开发任务
Iteration 2: AgentForge → 用 /agentforge 管理开发 agent
Iteration 3: adapters → 用 launch.sh 启动 headless agent
```

## 新建 SW App Checklist

- [ ] `apps/{name}/pyproject.toml`
- [ ] `apps/{name}/src/{name}/__init__.py`
- [ ] `agent/skills/{name}/SKILL.md`
- [ ] `agent/skills/{name}/config.yaml` (四原语定义)
- [ ] `agent/skills/{name}/scripts/` (CRUD 脚本)
- [ ] `agent/tools/{name}-api.yaml` (MCP 工具定义)
- [ ] `tests/test_{name}.py`
