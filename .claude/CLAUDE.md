# CLAUDE.md — Socialwares

## Project Overview

Socialwares MonoRepo — 面向 agent 的协作应用集合。

每个 App（TaskArena、AgentForge 等）是独立 Python 服务，暴露 API，
agent 通过 Role/Flow/Commitment/Arena 四原语进行调用。

## Directory Structure

- `apps/` — Socialware App 本体 (Python API server)
- `agent/` — GitAgent 格式的 agent 定义
- `agent/skills/` — Agent 技能 (per-skill symlinked to .claude/skills/)
- `agent/adapters/` — SDK 启动模板 (Claude, Codex, KimiCode)
- `scripts/` — 运维和适配脚本
- `scenarios/` — 多 agent 场景编排
- `docs/` — 文档

## Conventions

- Python packages: use `uv`, not `pip`
- JavaScript packages: use `pnpm`, not `npm`/`npx`
- Python 3.12+, strict type hints
- 中文文档，英文变量名
- Tests: pytest, target >90% coverage

## Four Primitives (四原语)

Every SW App exposes its API through:
- **Role**: 角色定义与权限检查
- **Flow**: 状态机定义与转换
- **Commitment**: SLA 承诺与超时追踪
- **Arena**: 作用域（谁能看到、谁能参与）

## Development

```bash
# Run tests
uv run pytest

# Run specific app
uv run --package taskarena pytest

# Launch agent
./scripts/launch.sh --adapter claude
```
