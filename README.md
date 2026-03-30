# Socialwares

构建可安装到 IRC 频道的 Socialware App 的 Python 框架。

## 概念

Socialware App = Agent 交互可视化的 Web 应用。用户看到普通界面 + Chat 框，底层 Agent 驱动一切。

```
传统 App:  UI → API → DB CRUD         （数据库可视化）
Socialware: UI → Chat → Agent ↔ API    （Agent 交互可视化）
```

每个 Socialware App 通过四原语定义：
- **Role** — 谁（角色描述）
- **Scope** — 边界（能力范围）
- **Flow** — 怎么做（action + 状态机）
- **Commitment** — 约束（评估标准）

## 安装

```bash
pip install socialwares
# 或从 git：
pip install git+https://github.com/ezagent42/Socialwares.git
```

## 快速开始

### 1. 创建项目

```bash
socialwares new my-app
cd my-app
```

生成的项目结构：

```
my-app/
├── socialware.py           ← App 声明（关系定义）
├── agent/                  ← 四原语内容
│   ├── role/               ← 角色描述 (.md)
│   ├── scope/              ← 能力边界 (.md)
│   └── flow/               ← Skill 目录（业务 + evolve）
├── src/api.py              ← FastAPI 后端
├── app/                    ← 前端 UI
└── pyproject.toml
```

### 2. 定义 App

编辑 `socialware.py`（关系定义）：

```python
from socialwares import App

app = App("my-app")

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("evolver", file="agent/role/evolver.md")

app.action("check_health", role=["default"])
app.action("evolve_structure_check", role=["evolver"])

flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed")
flow.transition("draft", "submit_task", "submitted", role=["default"])

app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
)
```

编辑 `agent/` 下的内容文件（角色描述、SKILL.md 等）。

### 3. 编译 + 启动

```bash
socialwares deploy                    # 编译四原语 → .runtime/
uvicorn src.api:api --port 8001       # 启动后端
socialwares start --role default      # 启动 agent
```

### 4. 进化

```bash
socialwares start --role evolver      # 启动 evolver
# "check structure" / "diagnose" / "evaluate" / "improve"
```

## 安装到 IRC 频道

```bash
# 安装
socialwares install git@github.com:xxx/my-app.git --channel "#support"

# 分配角色
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign alice-evolver  --role evolver  --channel "#support"

# 卸载
socialwares uninstall my-app --channel "#support"
```

## 四原语

| 原语 | 目录 | 定义方式 |
|------|------|---------|
| **Role** | `agent/role/*.md` | Markdown 文件 |
| **Scope** | `agent/scope/scope.md` | Markdown 文件 |
| **Flow** | `agent/flow/*/SKILL.md` | 每个 action 一个目录 |
| **Commitment** | `socialware.py` | Python 声明式 |

**关系定义**在 `socialware.py`：action → role、状态机、约束。
**内容定义**在 `agent/` 文件：角色描述、SKILL.md。

## Evolver

普通角色，内置 5 个检测 skill（structure_check / api_check / session_diagnose / improve / auto）。加自定义检查 = 加 skill 目录 + 注册 action。

## CLI

| 命令 | 功能 |
|------|------|
| `socialwares new <name>` | 创建项目 |
| `socialwares deploy` | 编译 |
| `socialwares start --role <role>` | 启动 agent |
| `socialwares install <url> --channel <ch>` | 安装到频道 |
| `socialwares assign <agent> --role <role> --channel <ch>` | 分配角色 |
| `socialwares uninstall <app> --channel <ch>` | 卸载 |
| `socialwares list` | 查看已安装 |

## 文档

- [架构与概念](docs/guides/001-architecture-and-concepts.md)
- [快速开始](docs/guides/002-quickstart.md)
- [四原语详解](docs/guides/003-four-primitives.md)
- [Commitment 与 Evolve](docs/guides/004-commitment-and-evolve.md)
- [开发指南](docs/guides/006-dev-guide.md)
