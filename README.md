# Socialwares

Socialware App 脚手架模板 — Agent 交互可视化的 Web 应用。

> 传统 App: UI → API → DB (数据库 CRUD 可视化)
> Socialware: UI → Chat → Agent (Agent 交互可视化，从对话中渐进生长)

## 快速开始

```bash
# 1. 克隆模板
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares

# 2. 配置 Claude Code 环境 (首次运行自动安装 agent-setup 插件)
./claude.sh
# 进入 Claude Code 后执行 /agent-setup:init 完成配置，然后退出

# 3. 安装依赖
uv sync

# 4. 创建你的 App (workspace/{room}/{app}/ 结构)
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "任务管理"

# 5. 启动后端 API
uv run uvicorn src.app:app --port 8001 &

# 6. 启动 agent (CLI 模式，新终端)
./agent/start.sh --role default --workspace .socialware/workspace/my-team/task-manager

# 或直接用模板 (不创建 workspace)
./agent/deploy.sh
./agent/start.sh --role default
```

## 目录结构

```
socialwares/
├── app/                      ← 前端 (Next.js: UI + Chat)
├── src/                      ← 后端 (FastAPI: API + Agent SDK 启动)
│   ├── app.py                ← FastAPI 入口
│   └── start_agent.py        ← 生产模式 Agent 启动
├── agent/                    ← 四原语 + 工具链
│   ├── role/                 ← Who: Subagent 身份与权限
│   │   └── default/SOUL.md
│   ├── scope/                ← Where: App 能力声明
│   │   └── SOUL.md
│   ├── commitment/           ← What: Eval 指标
│   │   └── eval.yaml
│   ├── flow/                 ← How: Skills (操作定义)
│   │   └── check_health/SKILL.md
│   ├── deploy.sh             ← 编译四原语 → .runtime/
│   ├── start.sh              ← CLI 模式启动入口
│   └── adapters/             ← 平台适配 (Claude/Codex/Kimi)
├── scripts/
│   ├── create-my-socialware.py  ← 创建新 App 实例
│   └── evolve.sh                ← Workspace 进化 → PR
├── .socialware/workspace/    ← Workspace 实例
│   └── default/.gitkeep
├── tests/                    ← 测试
└── docs/                     ← 设计文档
```

## 四原语

每个 Socialware App 通过四个原语定义 Agent 行为。每个原语对应 `agent/` 下的一个目录：

### Role — Who

定义 Subagent 身份。每个角色一个子目录，包含 `SOUL.md` 描述身份和权限。

```
agent/role/
├── admin/SOUL.md      ← 管理员 agent 身份
└── reviewer/SOUL.md   ← 审核者 agent 身份
```

### Scope — Where

定义 App 级别的能力声明。`SOUL.md` 描述 Agent 能做什么、边界在哪。

- 对内: Agent 操作边界
- 对外: 公开描述，供其他 Agent 读取

### Commitment — What

定义可追踪的承诺和评估标准。声明式 — 描述"什么算达标"，不规定"怎么检查"。

```yaml
commitments:
  C1:
    description: "客户满意度 ≥ 4.5"
    metric: customer_rating
    threshold: ">=4.5"
```

执行方式由 App 的 Biz 层决定 (API middleware / cron / eval 脚本)。

### Flow — How

定义 Agent 可执行的操作。每个操作一个子目录，包含 `SKILL.md` (Claude Code skill 格式)。

```
agent/flow/
├── create_task/SKILL.md
├── review_task/SKILL.md
└── query_task/SKILL.md
```

> 状态机由 App (`src/`) 管理，权限由 App API 检查。Flow 只定义"怎么做"。

## 工作流

### deploy.sh — 编译四原语

将 `agent/` 四原语编译为可运行的 `.runtime/` 结构：

```bash
./agent/deploy.sh                    # 编译到默认 workspace
./agent/deploy.sh .socialware/workspace/my-app   # 编译到指定 workspace
```

生成结构：

```
.runtime/
├── data/                    ← 共享数据 (Files/ + Sqlite/)
└── agents/
    └── {role}/              ← 每个 role 的 $PROJECT_DIR
        ├── .claude/skills/  ← 软连接自 agent/flow/
        ├── SOUL.md          ← 合并: scope/SOUL.md + role/{name}/SOUL.md
        └── eval.yaml        ← 复制自 agent/commitment/eval.yaml
```

### start.sh — 启动 Agent

```bash
# 开发模式: Claude TUI
./agent/start.sh --role default
./agent/start.sh --role admin --adapter codex
./agent/start.sh --role admin,reviewer              # 多 role → tmux

# 指定 workspace
./agent/start.sh --role admin --workspace .socialware/workspace/my-app

# 生产模式: SDK
python src/start_agent.py --role admin
python src/start_agent.py --role admin --adapter codex
```

### create-my-socialware — 创建新 App

```bash
# 交互式
uv run scripts/create-my-socialware.py

# 命令行参数
uv run scripts/create-my-socialware.py --room my-team --app task-manager --description "任务管理"
```

执行:
1. 复制模板 (src/, app/, agent/ 四原语) → `.socialware/workspace/{room}/{app}/`
2. 定制 scope/SOUL.md 和 role/SOUL.md
3. 自动运行 deploy.sh

### evolve.sh — Workspace 进化

```bash
# 检查变更
./scripts/evolve.sh my-team/task-manager --check

# 创建 PR (将 workspace 改进回馈到模板)
./scripts/evolve.sh my-team/task-manager --pr
```

进化路由:
- 修改在 `.runtime/` → workspace 特定适配，不触发 PR
- 修改在 `agent/` → 通用改进，自动创建 PR 回 main

## 平台适配

| 平台 | 命令 | 工作目录 | 权限跳过 |
|------|------|---------|---------|
| Claude Code | `claude` | `cd $dir` | `--dangerously-skip-permissions` |
| Codex | `codex` | `--cd $dir` | `--full-auto` |
| Kimi Code | `kimi` | `--work-dir $dir` | `--yolo` |

## 渐进生长

```
P1 定义 Agent → P2 完善 Flow → P3 完善 Commitment → P4 扩大 Scope → P5 扩充 Role
                                                                          ↓
                                    P0 ← 触达单体边界 ← 创建新 App 或 /zchat 连接
```

每次改进 materialize 为 Biz 层 (API + UI + DB) 增长。

## 开发

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest -v

# 启动后端
uv run uvicorn src.app:app --port 8001

# 启动 agent
./agent/deploy.sh && ./agent/start.sh --role default
```

## License

MIT
