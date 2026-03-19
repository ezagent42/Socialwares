# Socialwares 快速入门

从零开始，5 分钟创建并运行一个 Socialware App。

## 前置条件

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- [Claude Code](https://claude.ai/code) 或其他支持的 AI 编码工具 (Codex / Kimi Code)
- Git

## 第一步：获取模板

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

## 第二步：理解四原语

Socialware 通过四个原语定义 Agent 行为，全部位于 `agent/` 目录：

| 原语 | 目录 | 作用 | 核心文件 |
|------|------|------|---------|
| **Role** (Who) | `agent/role/` | 定义 Agent 身份和权限 | `SOUL.md` |
| **Scope** (Where) | `agent/scope/` | 定义 App 能力边界 | `SOUL.md` |
| **Commitment** (What) | `agent/commitment/` | 定义评估指标 | `eval.yaml` |
| **Flow** (How) | `agent/flow/` | 定义可执行操作 | `SKILL.md` |

## 第三步：直接启动 (使用默认模板)

最简启动 — 不创建 workspace，直接使用模板默认配置：

```bash
# 编译四原语到 .runtime/
./agent/deploy.sh

# 启动 agent (开发模式, Claude Code TUI)
./agent/start.sh --role default
```

`start.sh` 会自动检测 `.runtime/`，如果不存在会先执行 `deploy.sh`。

## 第四步：创建自己的 App

```bash
# 交互式创建
uv run scripts/create-my-socialware.py

# 或用命令行参数
uv run scripts/create-my-socialware.py \
    --name my-app \
    --role admin \
    --description "我的任务管理应用"
```

这会在 `.socialware/workspace/my-app/` 下生成完整的 App 实例。

## 第五步：定制你的 Agent

### 编辑 Role (身份)

```bash
# 编辑 agent 身份描述
vim agent/role/default/SOUL.md
```

内容示例：

```markdown
# Default Agent

你是一个任务管理助手。你可以帮助用户创建、查询和管理任务。

## 权限
- 可以读写 data/ 目录
- 可以调用所有 flow 中定义的操作
```

### 编辑 Scope (能力边界)

```bash
vim agent/scope/SOUL.md
```

### 添加 Flow (操作)

```bash
# 创建新操作
mkdir -p agent/flow/create_task
```

编辑 `agent/flow/create_task/SKILL.md`：

```markdown
# create_task

创建一个新任务。

## 步骤
1. 获取任务标题和描述
2. 写入 data/tasks.json
3. 返回任务 ID
```

### 重新编译

修改四原语后需要重新 deploy：

```bash
./agent/deploy.sh
```

## 第六步：使用不同平台

```bash
# Claude Code (默认)
./agent/start.sh --role default

# Codex
./agent/start.sh --role default --adapter codex

# Kimi Code
./agent/start.sh --role default --adapter kimicode
```

## 第七步：多 Role 启动

```bash
# 用逗号分隔多个 role，自动打开 tmux 多 pane
./agent/start.sh --role admin,reviewer
```

## 第八步：启动后端 API

```bash
# 启动 FastAPI 后端
uv run uvicorn src.app:app --port 8001
```

## 第九步：运行测试

```bash
uv run pytest -v
```

## 第十步：进化

当你在 workspace 中改进了 Agent，可以将改进回馈到模板：

```bash
# 检查 workspace 变更
./scripts/evolve.sh my-app --check

# 创建 PR
./scripts/evolve.sh my-app --pr
```

## 常见问题

### Q: deploy.sh 报错 "No role found"

确保 `agent/role/` 下至少有一个角色目录（如 `default/`），且包含 `SOUL.md` 文件。

### Q: start.sh 找不到 adapter

检查 `--adapter` 参数是否为支持的值：`claude`、`codex`、`kimicode`。

### Q: 如何切换到生产模式？

使用 SDK 模式启动：

```bash
python src/start_agent.py --role admin
```

## 下一步

- 阅读 [README.md](../README.md) 了解完整架构
- 查看 `docs/designs/` 下的设计文档了解架构决策
- 在 `agent/flow/` 中添加更多操作来扩展 Agent 能力
