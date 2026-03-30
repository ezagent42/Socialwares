# Socialwares 框架重构 — 打包与分发设计

## 一、定位

Socialwares 是一个 Python 框架（pip 包），用于构建可安装到 IRC 频道的 Socialware App。

类比：
- `git` (CLI) → GitHub (平台)
- `socialwares` (pip 包 = Python 框架 + CLI) → SocialwareHub (平台，未来)

两种用户：

| 角色 | 做什么 | 用什么 |
|------|--------|--------|
| **模板开发者** | 定义 App，发布到 git | `socialwares` pip 包 |
| **OPC 用户** | 从 git 下载 App，安装到 IRC 频道 | `socialwares` CLI / 未来 SocialwareHub |

---

## 二、整体架构

```
┌────────────────────────────────────────────────────────┐
│  Git 仓库（分发）                                        │
│  github.com/xxx/task-review                             │
│  github.com/xxx/customer-service                        │
├────────────────────────────────────────────────────────┤
│  Socialware App（一个具体的业务应用）                       │
│  = socialware.py + agent/ 内容文件 + src/ 后端 + app/ UI │
├────────────────────────────────────────────────────────┤
│  socialwares 框架（pip 包 = Python 框架 + CLI）            │
│  编译器 / 适配器 / Runner / CLI                           │
├────────────────────────────────────────────────────────┤
│  zchat IRC 总线（已建成，不在本项目范围）                    │
├────────────────────────────────────────────────────────┤
│  LLM（Claude / GPT / Kimi / DeepSeek）                   │
└────────────────────────────────────────────────────────┘
```

基础 App（并行开发，其他 App 可通过 IRC @mention 协作）：
- **TaskArena** — 统一任务管理
- **AgentForge** — Agent 配置管理 + 沙箱试用
- **ResPool** — 计算资源管理

未来 **SocialwareHub** 是管理 Socialware App 的 Socialware（类比 GitHub 之于 git），不在当前范围。

---

## 三、pip 包

### 包结构

```
socialwares/
├── __init__.py           ← App 类导出
├── app.py                ← App 声明式 API（App, Flow, ...）
├── compiler.py           ← 编译器（socialware.py + agent/ → .runtime/）
├── runner.py             ← Agent 启动器
├── cli.py                ← CLI（new / deploy / start / install / assign）
├── adapters/             ← LLM 适配器
│   ├── base.py
│   ├── claude/
│   ├── codex/
│   └── kimicode/
└── templates/            ← socialwares new 的项目模板
```

### pyproject.toml（框架包）

```toml
[project]
name = "socialwares"
version = "0.2.0"
dependencies = ["pyyaml>=6.0", "click>=8.0"]

[project.scripts]
socialwares = "socialwares.cli:main"
```

`pip install socialwares` → 同时得到 Python 框架和 CLI 命令。

### pip 包 vs 用户项目

| pip 包（工具，`pip upgrade` 升级） | 用户项目（内容，用户拥有） |
|-----------------------------------|------------------------|
| 编译器 | `socialware.py`（关系定义） |
| 适配器 | `agent/role/*.md`（角色内容） |
| Runner | `agent/scope/scope.md`（边界内容） |
| CLI | `agent/flow/*/SKILL.md + scripts/`（skill 内容 + 脚本） |
| 项目模板 | `src/api.py`（后端）、`app/`（前端） |

---

## 四、用户项目结构

`socialwares new task-review` 生成有内容的项目：

```
task-review/
├── socialware.py                     ← 关系定义（唯一的结构入口）
│
├── agent/                            ← 内容文件
│   ├── role/                         ← 角色描述
│   │   ├── default.md
│   │   ├── reviewer.md
│   │   └── evolver.md
│   ├── scope/                        ← 能力边界
│   │   └── scope.md
│   └── flow/                         ← Skill（业务 + evolve，结构完全一样）
│       ├── check_health/
│       │   └── SKILL.md
│       ├── create_task/
│       │   └── SKILL.md
│       ├── review_task/
│       │   └── SKILL.md
│       ├── evolve_structure_check/
│       │   ├── SKILL.md
│       │   ├── scripts/check_structure.py
│       │   └── references/
│       ├── evolve_api_check/
│       │   ├── SKILL.md
│       │   ├── scripts/run_eval.py
│       │   ├── references/
│       │   └── eval_cases.yaml
│       ├── evolve_session_diagnose/
│       │   ├── SKILL.md
│       │   ├── scripts/diagnose.py
│       │   └── references/
│       ├── evolve_improve/
│       │   ├── SKILL.md
│       │   ├── scripts/save_report.py
│       │   └── references/
│       └── evolve_auto/
│           ├── SKILL.md
│           ├── scripts/run_auto.py
│           ├── references/
│           └── conversation_tests/
│               └── default.yaml
│
├── src/api.py                        ← FastAPI 后端
├── app/                              ← 前端 UI
├── pyproject.toml                    ← 依赖 socialwares + 项目配置
└── .runtime/                         ← 编译产物（gitignore）
```

### 项目配置

静态配置放 `pyproject.toml`，动态定义放 `socialware.py`：

```toml
# pyproject.toml
[project]
name = "task-review"
version = "0.1.0"
dependencies = ["socialwares>=0.2.0", "fastapi>=0.115.0", "uvicorn>=0.32.0"]

[tool.socialwares]
agent_dir = "agent"          # 四原语内容目录
adapter = "claude"           # 默认适配器
api_port = 8001              # 后端端口
ui_port = 3000               # 前端端口
```

### 分工

- **`pyproject.toml [tool.socialwares]`**：静态配置（路径、端口、适配器）
- **`socialware.py`**：关系定义（谁能做什么、状态怎么转、什么约束）
- **`agent/` 下的文件**：内容定义（角色描述、能力边界、skill 执行方式）
- **三者不重复**

---

## 五、socialware.py — 声明式 API

编译器通过 `importlib.util.spec_from_file_location` 加载当前目录的 `socialware.py`，获取 `app` 对象。

```python
from socialwares import App

app = App("task-review", description="Task review workflow")

# ── 内容引用（从文件读，不在 Python 里写内容）──

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("reviewer", file="agent/role/reviewer.md")
app.role("evolver", file="agent/role/evolver.md")

# ── 关系定义（action → role 映射）──
# 约定：action 名 = agent/flow/ 下的目录名
# 编译器自动找 agent/flow/{action}/SKILL.md，找不到报错

app.action("check_health", role=["default", "reviewer"])
app.action("create_task", role=["default"])
app.action("list_tasks", role=["default", "reviewer"])
app.action("review_task", role=["reviewer"])

# evolve skill 和业务 skill 一样注册
app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

# ── 状态机 ──

flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
flow.transition("reviewed", "close_task", "closed", role=["default"])

# ── 约束 ──

app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

也支持内联字符串（简单场景不想建文件时）：

```python
app.scope("Create and manage tasks")
app.role("default", "You are the task management agent.")
```

---

## 六、编译

```bash
socialwares deploy
```

读 `socialware.py` + `agent/` 文件 → 生成 `.runtime/`：

```
.runtime/
├── agents/
│   ├── default/
│   │   ├── SOUL.md               ← scope + default role 合并
│   │   └── .claude/skills/       ← check_health/, create_task/, list_tasks/
│   ├── reviewer/
│   │   ├── SOUL.md               ← scope + reviewer role 合并
│   │   └── .claude/skills/       ← review_task/, list_tasks/
│   └── evolver/
│       ├── SOUL.md               ← scope + evolver role 合并
│       └── .claude/skills/       ← evolve_*/ skills
├── flow.yaml                     ← 从 socialware.py 的 action/flow 定义生成
├── commitment.yaml               ← 从 socialware.py 的 commitment 定义生成
└── compile_manifest.yaml         ← 来源追溯
```

**编译器对所有角色一视同仁**——evolver 和 default 的编译逻辑完全一样。

---

## 七、两种启动模式

### 本地开发：`socialwares start`

启动 Claude Code 进程 + 加载 role 配置。是**创建 agent**。

```bash
# 单角色
socialwares start --role default

# 多角色（tmux 多窗格）
socialwares start --role default,reviewer,evolver
```

### IRC 频道：`socialwares install` + `socialwares assign`

agent 已经在 zchat 里跑着。不创建新 agent，只**配置已有 agent**。

```bash
# install：git clone + 编译 + 启动后端（不启动 agent）
socialwares install git@github.com:xxx/task-review.git --channel "#support"
#  → git clone
#  → socialwares deploy（编译 .runtime/）
#  → 启动 FastAPI 后端（共享，所有角色用同一个）

# assign：把 role 配置 symlink 到已有 agent 的 workspace（不重启 agent）
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign bob-reviewer   --role reviewer --channel "#support"
socialwares assign alice-evolver  --role evolver  --channel "#support"
#  → 找到 agent 的 workspace 目录（zchat 管理）
#  → symlink .runtime/agents/{role}/ 的内容到 workspace
#  → agent 下次收到消息时自动读取新的 SOUL.md + skills
```

| 命令 | 做什么 | 启动什么 |
|------|--------|---------|
| `socialwares start` | 本地创建 agent | Claude Code 进程 |
| `socialwares install` | 部署 App 到频道 | FastAPI 后端 |
| `socialwares assign` | 配置已有 agent | 不启动，只 symlink |
| `socialwares uninstall` | 卸载 App | 停 FastAPI，清 symlink |

---

## 八、使用方式

### A. 开发

```bash
socialwares new task-review       # 生成有内容的项目
cd task-review

# 编辑内容
vim agent/role/default.md         # 角色描述
vim agent/scope/scope.md          # 能力边界
vim agent/flow/create_task/SKILL.md  # skill 执行方式
vim src/api.py                    # 后端 API

# 编辑关系
vim socialware.py                 # action→role、状态机、commitment

# 编译 + 测试
socialwares deploy
uvicorn src.api:api --port 8001
socialwares start --role default  # 本地启动，测试业务
socialwares start --role evolver  # 本地启动，测试进化

# 发布
git init && git push
```

### B. 安装到 IRC 频道

```bash
socialwares install git@github.com:xxx/task-review.git --channel "#support"
socialwares assign alice-support  --role default  --channel "#support"
socialwares assign bob-reviewer   --role reviewer --channel "#support"
socialwares assign alice-evolver  --role evolver  --channel "#support"

# 日常
#   IRC: @alice-support 创建任务: 修复首页bug
#   UI:  localhost:8001 看仪表盘
#   进化: @alice-evolver diagnose

# 卸载
socialwares uninstall task-review --channel "#support"
```

### C. 进化

Evolver 是普通角色，三种触发方式：

| 方式 | 命令 | 场景 |
|------|------|------|
| 本地交互 | `socialwares start --role evolver` | 开发时 |
| IRC | `@alice-evolver diagnose` | 生产时 |
| CI | `socialwares start --role evolver --run-all` | 自动化 |

加自定义 evolve 检查 = 加业务 skill：
1. 创建 `agent/flow/evolve_xxx/SKILL.md + scripts/`
2. 在 `socialware.py` 注册 `app.action("evolve_xxx", role=["evolver"])`
3. `socialwares deploy`

---

## 九、分发

### 发布

```bash
git init && git add . && git commit -m "initial"
git remote add origin git@github.com:xxx/task-review.git
git push
```

### 获取

```bash
socialwares install git@github.com:xxx/task-review.git --channel "#support"
# 或手动：
git clone ... && cd task-review && socialwares deploy
```

### 预留接口

| 接口 | 当前 | 未来扩展 |
|------|------|---------|
| `socialwares install <source>` | git clone | SocialwareHub registry |
| `socialwares publish` | git push（手动） | 推送到 registry |
| `socialwares search` | 未实现 | 搜索 registry |
| `socialwares update` | git pull | 自动检查更新 |

---

## 十、现有代码迁移

### 搬入 pip 包

| 现有文件 | → pip 包位置 |
|---------|-------------|
| `agent/deploy.sh` (358 行) | `socialwares/compiler.py`（Python 重写） |
| `agent/start.sh` (135 行) | `socialwares/runner.py` |
| `src/start_agent.py` (127 行) | `socialwares/runner.py`（合并） |
| `scripts/create-my-socialware.py` (192 行) | `socialwares/cli.py` |
| `agent/adapters/*` | `socialwares/adapters/*` |

### 搬入模板

整个 `agent/` 目录（role + scope + flow + 所有 skill 含 evolve + scripts）+ `src/app.py` 搬入 `templates/`。

### 删除

| 文件 | 原因 |
|------|------|
| `Makefile` + `agent/Makefile.template` | CLI 替代 |
| `claude.sh` | `socialwares start` 替代 |
| `.socialware/workspace/` | 不再需要 |
| `agent/flow/flow.yaml` | 变成编译产物 |
| `agent/commitment/commitment.yaml` | 变成编译产物 |

### 新增

| 文件 | 说明 |
|------|------|
| `socialwares/app.py` | App 声明式 API |
| `socialwares/compiler.py` | 编译器 |
| `socialwares/runner.py` | 启动器 |
| `socialwares/cli.py` | CLI |

---

## 十一、仓库结构变化

```
现在:                                重构后:
Socialwares/ (git 模板仓库)          Socialwares/ (pip 包仓库)
├── agent/                           ├── src/socialwares/
│   ├── role/                        │   ├── app.py        ← 声明式 API
│   ├── scope/                       │   ├── compiler.py   ← 编译器
│   ├── commitment/                  │   ├── runner.py     ← 启动器
│   ├── flow/ (skills+evolve)        │   ├── cli.py        ← CLI
│   ├── adapters/                    │   ├── adapters/
│   ├── deploy.sh                    │   └── templates/    ← 项目模板
│   └── start.sh                     │       ├── socialware.py.j2
├── scripts/                         │       ├── agent/
├── src/                             │       ├── src/
├── Makefile                         │       └── app/
└── pyproject.toml                   ├── tests/
                                     ├── pyproject.toml
                                     └── docs/
```
