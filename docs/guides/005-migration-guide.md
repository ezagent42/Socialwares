# 从 v0.1.0 迁移到 v0.2.0

## v0.1.0 架构回顾

v0.1.0 **不是一个 pip 包**，而是一个 monorepo 模板：

```
Socialwares/                          ← 整个仓库就是模板
├── Makefile                          ← make create / make deploy / make start
├── claude.sh                         ← Claude Code 启动器（tmux + worktree）
├── scripts/create-my-socialware.py   ← 创建 App（复制模板到 workspace）
├── agent/
│   ├── deploy.sh                     ← bash 编译脚本
│   ├── start.sh                      ← bash 启动脚本
│   ├── adapters/claude/shell.sh      ← 适配器（bash）
│   ├── flow/flow.yaml                ← 手工编辑的 flow 定义
│   ├── flow/evolve_*/                ← evolve skill（直接在项目中）
│   ├── commitment/commitment.yaml    ← 手工编辑的 commitment 定义
│   ├── role/                         ← 角色描述
│   └── scope/                        ← 能力边界
├── src/start_agent.py                ← Python 启动入口
└── .socialware/workspace/            ← App 实例目录
```

核心特征：
- **Makefile + bash 脚本** 驱动一切（`make create`、`agent/deploy.sh`、`agent/start.sh`）
- **flow.yaml / commitment.yaml 手工编写**（没有 `socialware.py` 声明式 API）
- **所有 skill 在项目中**（evolve_* 等直接在 `agent/flow/` 下）
- **没有 pip 包**，克隆仓库即用
- **没有 `socialwares` CLI**

---

## v0.2.0 核心变化

| 方面 | v0.1.0 | v0.2.0 |
|------|--------|--------|
| **分发方式** | git clone 整个仓库 | `pip install socialwares`（框架 pip 包） |
| **项目创建** | `make create ROOM=x APP=y` | `socialwares new my-app` |
| **四原语定义** | 手编 flow.yaml + commitment.yaml | `socialware.py` 声明式 Python API |
| **编译** | `agent/deploy.sh`（bash） | `socialwares deploy`（Python Compiler） |
| **启动** | `agent/start.sh` / `claude.sh` | `socialwares start --role x` |
| **适配器** | `agent/adapters/*/shell.sh`（bash） | `launch.py`（Python） |
| **Hook** | `.sh` bash 脚本 | `.py` Python 脚本（`uv run --no-project`） |
| **内置 skill** | 复制到项目中 | 框架包内，deploy 时 symlink |
| **assign** | 直接覆盖 | merge 策略（幂等，多 App 共存） |
| **新增角色** | 无 | `dev` 角色（引导式开发） |

---

## 迁移步骤

### 第一步：安装框架

```bash
# v0.1.0 不需要安装，v0.2.0 需要
pip install git+ssh://git@github.com/ezagent42/Socialwares.git

# 验证
socialwares --help
```

### 第二步：创建新项目

**不建议在旧 workspace 原地升级**。推荐创建新项目，迁移内容：

```bash
# 新建项目
socialwares new my-app
cd my-app
```

### 第三步：迁移四原语内容

从旧项目复制内容文件（不是整个目录）：

```bash
# Scope
cp ../old-workspace/agent/scope/scope.md agent/scope/scope.md

# Role（如果有自定义角色）
cp ../old-workspace/agent/role/default.md agent/role/default.md
cp ../old-workspace/agent/role/evolver.md agent/role/evolver.md

# 用户自定义 skill（非 evolve_* / dev_* / inspect / setup_claude）
cp -r ../old-workspace/agent/flow/check_health agent/flow/check_health
# 其他自定义 skill 同理
```

**如果旧项目修改过内置 skill**（如 `evolve_structure_check` 的脚本），用 `eject` 将内置 skill 复制到项目中再覆盖：

```bash
socialwares eject evolve_structure_check
# 然后将旧项目的修改合并到 agent/flow/evolve_structure_check/
```

### 第四步：编写 socialware.py

旧版的 `flow.yaml` 和 `commitment.yaml` 是手写的，新版需要转为 `socialware.py` 声明：

**旧 flow.yaml：**
```yaml
flows:
  F1:
    name: task_lifecycle
    resource: task
    states: [draft, submitted, reviewed]
    transitions:
      - { from: draft, action: submit, to: submitted, role: [default] }
direct_actions:
  - { action: check_health, role: [default] }
```

**新 socialware.py：**
```python
from socialwares import App

app = App("my-app")
app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("dev", file="agent/role/dev.md")
app.role("evolver", file="agent/role/evolver.md")

# 直接操作
app.action("check_health", role=["default"])

# 状态机
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed")
flow.transition("draft", "submit", "submitted", role=["default"])

# 注册 dev 和 evolver 的内置 action（模板已包含，照抄即可）
app.action("inspect",     role=["dev", "evolver"])
app.action("setup_claude", role=["dev"])
app.action("dev_define",  role=["dev"])
app.action("dev_build",   role=["dev"])
app.action("dev_release", role=["dev"])

app.action("evolve_structure_check",   role=["evolver"])
app.action("evolve_api_check",         role=["evolver"])
app.action("evolve_session_diagnose",  role=["evolver"])
app.action("evolve_improve",           role=["evolver"])
app.action("evolve_auto",             role=["evolver"])
```

**旧 commitment.yaml 同理**，改为 `app.commitment(...)` 调用。

### 第五步：迁移后端代码

```bash
# 复制 FastAPI 代码
cp ../old-workspace/src/api.py src/api.py

# 复制前端（如果有）
cp -r ../old-workspace/app/* app/
```

### 第六步：编译并验证

```bash
socialwares deploy

# 检查
ls .runtime/agents/                    # default/  dev/  evolver/
ls -la .runtime/agents/evolver/.claude/skills/  # 内置 skill 应是 symlink → 框架包
ls .runtime/agents/default/.claude/hooks/ # 应有 .py 文件
```

---

## 不需要迁移的内容

| 内容 | 原因 |
|------|------|
| `evolve_*` skill 文件 | 框架内置，自动 symlink |
| `agent/deploy.sh` | 已被 `socialwares deploy`（Python）替代 |
| `agent/start.sh` | 已被 `socialwares start`（Python）替代 |
| `claude.sh` | 已被 `socialwares start --adapter claude` 替代 |
| `Makefile` | 已被 `socialwares` CLI 替代 |
| `scripts/create-my-socialware.py` | 已被 `socialwares new` 替代 |
| `agent/flow/flow.yaml` | 编译产物，从 `socialware.py` 生成 |
| `agent/commitment/commitment.yaml` | 编译产物，从 `socialware.py` 生成 |

---

## 常见问题

### Q: 旧项目的 .runtime/ 数据（prompts、reports）能保留吗？

可以。直接把 `.runtime/data/` 目录复制到新项目的 `.runtime/data/` 下。hook 日志和 evolve 报告的格式兼容。

### Q: 能在旧仓库里直接升级吗？

不建议。v0.1.0 的项目结构（Makefile + deploy.sh + 无 socialware.py）和 v0.2.0 差异太大。建议用 `socialwares new` 创建新项目后迁移内容。

### Q: 同事还在用 v0.1.0 怎么办？

v0.1.0 的代码仍在 `main` 分支的 `v0.1.0` tag 上。同事可以继续使用，按自己的节奏迁移：
```bash
# 同事保持旧版
git checkout v0.1.0

# 准备好了再迁移
pip install git+ssh://git@github.com/ezagent42/Socialwares.git
socialwares new my-app
# 按上面的步骤迁移
```
