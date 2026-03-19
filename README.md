# Socialwares

Socialware App 脚手架模板 — Agent 交互可视化的 Web 应用。

> 传统 App: UI → API → DB (数据库 CRUD 可视化)
> Socialware: UI → Chat → Agent (Agent 交互可视化，从对话中渐进生长)

## 快速开始

```bash
# 克隆模板
git clone https://github.com/ezagent42/Socialwares.git my-app
cd my-app

# 编译四原语 → .runtime/
./agent/deploy.sh

# 启动 agent (开发模式)
./agent/start.sh --role admin

# 或启动完整 App (前端 + 后端 + agent)
pnpm start
```

## 目录结构

```
socialwares/
├── app/                  ← 前端 (Next.js: UI + Chat)
├── src/                  ← 后端 (FastAPI: API + start_agent.py)
├── agent/                ← 四原语 + 工具链
│   ├── role/             ← Who: Subagent 身份 + 权限
│   ├── scope/            ← Where: SOUL.md 能力声明
│   ├── commitment/       ← What: Eval 指标
│   ├── flow/             ← How: Skills (操作定义)
│   ├── deploy.sh         ← 编译四原语 → .runtime/
│   ├── start.sh          ← 开发模式启动
│   └── adapters/         ← 平台适配 (Claude/Codex/KimiCode)
├── .socialware/workspace/← Workspace 实例
└── docs/                 ← 设计文档
```

## 四原语

每个 Socialware App 通过四个原语定义 Agent 行为:

- **Role** (Who) — Subagent 身份与权限
- **Scope** (Where) — SOUL.md 能力边界声明
- **Commitment** (What) — Eval 指标与 SLA
- **Flow** (How) — Skills, 操作定义

## 渐进生长

```
P1 定义 Agent → P2 完善 Flow → P3 完善 Commitment → P4 扩大 Scope → P5 扩充 Role → P0 跨 App
```

详见 `docs/designs/2026-03-19-socialwares-architecture-v3.md`
