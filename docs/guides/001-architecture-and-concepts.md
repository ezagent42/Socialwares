# Architecture and Concepts

## What is a Socialware App?

A web application for Agent interaction visualization. Users see a normal UI + Chat box; Agents drive everything underneath.

> Traditional App: UI → API → DB (database CRUD visualization)
> Socialware: UI → Chat → Agent (Agent interaction visualization)

## Runtime Model

```
User → Login → Session (role assigned)
  → Chat message → Backend receives
  → Backend spawns agent with user's role
  → Agent processes → calls API → state transitions → response back to chat
  → Hooks record prompts + tool calls → evolver's diagnose.py analyzes later
```

## Framework vs App

Socialwares 是一个 Python 框架（pip 包），用于构建 Socialware App。

| 概念 | 说明 |
|------|------|
| **socialwares** (pip 包) | Python 框架 + CLI，提供编译器、适配器、Runner |
| **Socialware App** (用户项目) | 一个具体的业务应用，包含 `socialware.py` + `agent/` + `src/` |

类比：`Django` (pip 包) → Django 项目 / `Rails` (gem) → Rails 项目

## Directory Structure — 用户项目

`socialwares new task-review` 生成的项目结构：

```
task-review/
├── socialware.py                     ← App 声明文件（关系定义：action→role, 状态机, commitment）
│
├── agent/                            ← 内容文件（四原语）
│   ├── role/                         ← 角色描述（一个 .md 文件一个角色）
│   │   ├── default.md
│   │   ├── reviewer.md
│   │   └── evolver.md
│   ├── scope/                        ← 能力边界
│   │   └── scope.md
│   └── flow/                         ← Skill（业务 + evolve，结构完全一样）
│       ├── check_health/SKILL.md
│       ├── create_task/SKILL.md
│       ├── review_task/SKILL.md
│       ├── evolve_structure_check/
│       │   ├── SKILL.md
│       │   ├── scripts/check_structure.py
│       │   └── references/
│       ├── evolve_session_diagnose/
│       │   ├── SKILL.md
│       │   ├── scripts/diagnose.py
│       │   └── references/
│       ├── evolve_api_check/
│       │   ├── SKILL.md
│       │   ├── scripts/run_eval.py
│       │   ├── references/
│       │   └── eval_cases.yaml
│       ├── evolve_improve/
│       │   ├── SKILL.md
│       │   ├── scripts/save_report.py
│       │   └── references/
│       └── evolve_auto/
│           ├── SKILL.md
│           ├── scripts/run_auto.py
│           ├── references/
│           └── conversation_tests/
│
├── src/api.py                        ← FastAPI 后端
├── app/                              ← 前端 UI
├── pyproject.toml                    ← 依赖 socialwares + 项目配置 [tool.socialwares]
└── .runtime/                         ← 编译产物（gitignore）
```

### 关键分工

| 文件 | 定义什么 | 举例 |
|------|---------|------|
| `socialware.py` | 关系定义 | action→role 映射、状态机、commitment |
| `agent/` 下的文件 | 内容定义 | 角色描述、能力边界、skill 执行方式 |
| `pyproject.toml [tool.socialwares]` | 静态配置 | 适配器、端口、agent_dir 路径 |

三者不重复。

### pyproject.toml 配置

```toml
[project]
name = "task-review"
dependencies = ["socialwares>=0.2.0", "fastapi>=0.115.0"]

[tool.socialwares]
agent_dir = "agent"          # 四原语内容目录
adapter = "claude"           # 默认适配器
api_port = 8001              # 后端端口
ui_port = 3000               # 前端端口
```

## Four Primitives

Every Socialware App defines Agent behavior through four primitives:

| Primitive | Directory | Key File | Purpose |
|-----------|-----------|----------|---------|
| **Role** (Who) | agent/role/ | {name}.md | Agent identities + permissions |
| **Scope** (Where) | agent/scope/ | scope.md | App capability boundary + public identity |
| **Commitment** (What) | socialware.py | `app.commitment(...)` | Evaluation standards on flow edges |
| **Flow** (How) | agent/flow/ + socialware.py | SKILL.md + `app.action(...)` | Actions the agent can execute |

**注意**：`flow.yaml` 和 `commitment.yaml` 不再是源文件，而是由 `socialwares deploy` 从 `socialware.py` 编译生成到 `.runtime/` 的产物。

## Compile Products

`socialwares deploy` 读取 `socialware.py` + `agent/` 文件 → 生成 `.runtime/`：

```
.runtime/
├── agents/
│   ├── default/
│   │   ├── SOUL.md               ← scope + default role 合并
│   │   └── .claude/skills/       ← check_health/, create_task/ 等
│   ├── reviewer/
│   │   ├── SOUL.md               ← scope + reviewer role 合并
│   │   └── .claude/skills/       ← review_task/, list_tasks/ 等
│   └── evolver/
│       ├── SOUL.md               ← scope + evolver role 合并
│       └── .claude/skills/       ← evolve_*/ skills
├── flow.yaml                     ← 从 socialware.py 的 action/flow 定义生成
├── commitment.yaml               ← 从 socialware.py 的 commitment 定义生成
└── compile_manifest.yaml         ← 来源追溯
```

编译器对所有角色一视同仁——evolver 和 default 的编译逻辑完全一样。

## Roles

开发者自行定义角色。默认模板提供两个角色：

| Role | Purpose | Skills |
|------|---------|--------|
| `default` | App user | check_health |
| `evolver` | Diagnose + improve | evolve_structure_check, evolve_api_check, evolve_session_diagnose, evolve_improve, evolve_auto |

Evolver 是普通角色，与业务角色使用完全相同的 skill 结构和编译逻辑。可以自由添加更多角色（如 `reviewer`、`admin`）。

## Progressive Growth

```
P1 Define Agent → P2 Refine Flow → P3 Refine Commitment → P4 Expand Scope → P5 Expand Role
                                                                               ↓
                                         P0 ← Reach boundary ← New App or /zchat
```

Each phase: edit `socialware.py` + `agent/` → `socialwares deploy` → grow `src/` → repeat.

## Two Startup Modes

### 本地开发：`socialwares start`

启动 Claude Code 进程 + 加载 role 配置。是**创建 agent**。

```bash
socialwares start --role default                      # 单角色
socialwares start --role default,reviewer,evolver     # 多角色（tmux 多窗格）
```

### IRC 频道：`socialwares install` + `socialwares assign`

agent 已经在 zchat 里跑着。不创建新 agent，只**配置已有 agent**。

```bash
socialwares install git@github.com:xxx/task-review.git --channel "#support"
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign bob-reviewer   --role reviewer --channel "#support"
```

| 命令 | 做什么 | 启动什么 |
|------|--------|---------|
| `socialwares start` | 本地创建 agent | Claude Code 进程 |
| `socialwares install` | 部署 App 到频道 | FastAPI 后端 |
| `socialwares assign` | 配置已有 agent | 不启动，只 symlink |
| `socialwares uninstall` | 卸载 App | 停 FastAPI，清 symlink |
