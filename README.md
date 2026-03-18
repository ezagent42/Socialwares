# Socialwares

Socialware App MonoRepo — 面向 agent 的协作应用。

## 快速开始

```bash
# 克隆仓库
gh repo clone ezagent42/Socialwares
cd Socialwares

# 配置 Claude Code 开发环境
./scripts/setup-claude.sh

# 启动开发
claude
```

## 目录结构

- `apps/` — Socialware App 本体 (TaskArena, AgentForge)
- `agent/` — GitAgent 格式的 agent 定义 (本机启动)
- `scripts/` — 运维和适配脚本
- `scenarios/` — 多 agent 场景编排
- `docs/` — 文档

## 四原语

每个 Socialware App 通过四个原语暴露 API:

- **Role** — 角色定义与权限
- **Flow** — 状态机与流程
- **Commitment** — 承诺与 SLA
- **Arena** — 作用域与可见性
