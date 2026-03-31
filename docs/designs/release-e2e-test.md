# Release E2E Test Plan — Socialwares v0.2.0

基于 `pip install socialwares` 的完整功能验证。覆盖从安装框架到创建、编译、启动、安装到 IRC 频道的全流程。

## 前置条件

```bash
# 安装框架
pip install socialwares
# 或开发模式：
cd Socialwares && uv pip install -e .

# 验证安装
socialwares --help
python -c "from socialwares import App; print('OK')"
```

---

## Phase 1: 项目创建

### 1.1 socialwares new 基础功能

| | |
|---|---|
| **操作** | `socialwares new task-review` |
| **目的** | 验证项目模板正确生成 |
| **预期** | 创建 task-review/ 目录，包含完整的四原语结构 |

```bash
socialwares new task-review
cd task-review

# 检查项目结构
ls                          # socialware.py  agent  src  app  pyproject.toml
ls agent/role/              # default.md  evolver.md
ls agent/scope/             # scope.md
ls agent/flow/              # check_health  evolve_structure_check  evolve_api_check  ...
ls agent/flow/evolve_structure_check/  # SKILL.md  scripts/  references/
```

### 1.2 App 声明文件渲染

| | |
|---|---|
| **操作** | 检查生成的 socialware.py |
| **目的** | 验证 {{APP_NAME}} 占位符被正确替换 |
| **预期** | 包含 `App("task-review")` |

```bash
cat socialware.py | grep 'App("task-review")'  # 应该匹配
cat socialware.py | grep '{{APP_NAME}}'         # 不应该匹配
cat pyproject.toml | grep 'name = "task-review"'
```

### 1.3 重复创建阻止

| | |
|---|---|
| **操作** | 在同一目录再次 `socialwares new task-review` |
| **目的** | 验证不会覆盖已有项目 |
| **预期** | 报错 "already exists" |

```bash
cd ..
socialwares new task-review   # Error: task-review/ already exists
```

---

## Phase 2: App 声明式 API

```bash
cd task-review
```

### 2.1 修改 socialware.py 添加业务逻辑

| | |
|---|---|
| **操作** | 编辑 socialware.py，添加角色、action、流转、commitment |
| **目的** | 验证声明式 API 被编译器正确读取 |

```python
# socialware.py
from socialwares import App

app = App("task-review", description="Task review workflow")

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("dev", file="agent/role/dev.md")
app.role("reviewer", "You review and approve tasks.")
app.role("evolver", file="agent/role/evolver.md")

app.action("check_health", role=["default", "reviewer"])
app.action("create_task", role=["default"])
app.action("list_tasks", role=["default", "reviewer"])
app.action("review_task", role=["reviewer"])

app.action("inspect", role=["dev", "evolver"])
app.action("setup_claude", role=["dev"])

app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
flow.transition("reviewed", "close_task", "closed", role=["default"])

app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

### 2.2 创建业务 skill

| | |
|---|---|
| **操作** | 为新 action 创建 SKILL.md |
| **目的** | 编译器校验 action 必须有对应的 SKILL.md |

```bash
# 创建业务 skill 目录
mkdir -p agent/flow/create_task
cat > agent/flow/create_task/SKILL.md << 'EOF'
---
name: create_task
description: "Create a new task"
---
# Create Task
## Trigger
User says "create task", "新建任务" etc.
## Flow
1. Ask for task title
2. POST /api/tasks {"title": "..."}
3. Return task ID
EOF

mkdir -p agent/flow/list_tasks
cat > agent/flow/list_tasks/SKILL.md << 'EOF'
---
name: list_tasks
description: "List all tasks"
---
# List Tasks
## Trigger
User says "list tasks", "任务列表" etc.
## Flow
1. GET /api/tasks
2. Display task list
EOF

mkdir -p agent/flow/review_task
cat > agent/flow/review_task/SKILL.md << 'EOF'
---
name: review_task
description: "Review a task"
---
# Review Task
## Trigger
User says "review task", "审核任务" etc.
## Flow
1. GET /api/tasks?status=submitted
2. Review and approve/reject
3. POST /api/tasks/{id}/review
EOF

# submit_task 和 close_task 在 flow transitions 中也需要
mkdir -p agent/flow/submit_task
echo "# Submit Task" > agent/flow/submit_task/SKILL.md

mkdir -p agent/flow/close_task
echo "# Close Task" > agent/flow/close_task/SKILL.md

mkdir -p agent/flow/remind_review
echo "# Remind Review" > agent/flow/remind_review/SKILL.md
```

---

## Phase 3: 编译

### 3.1 socialwares deploy 基础

| | |
|---|---|
| **操作** | `socialwares deploy` |
| **目的** | 编译四原语 → .runtime/ |
| **预期** | 4 个角色目录，各有正确的 SOUL.md + skills |

```bash
socialwares deploy

# 检查输出
ls .runtime/agents/          # default  dev  reviewer  evolver
ls .runtime/agents/default/.claude/skills/
# check_health  close_task  create_task  list_tasks  submit_task
ls .runtime/agents/dev/.claude/skills/
# inspect  setup_claude
ls .runtime/agents/reviewer/.claude/skills/
# check_health  list_tasks  review_task
ls .runtime/agents/evolver/.claude/skills/
# evolve_api_check  evolve_auto  evolve_improve  evolve_session_diagnose  evolve_structure_check  inspect
```

### 3.2 SOUL.md 合并验证

| | |
|---|---|
| **操作** | 检查 SOUL.md 内容 |
| **目的** | scope + role 正确合并，workflow 正确注入 |

```bash
# default 的 SOUL.md 应包含 scope + role + workflow
grep -c -- "---" .runtime/agents/default/SOUL.md  # 至少 2 个分隔符
cat .runtime/agents/default/SOUL.md | grep "Workflows"  # 应存在
cat .runtime/agents/default/SOUL.md | grep "submit_task"  # 应存在

# evolver 的 SOUL.md 不应包含 workflow（不参与 task_lifecycle）
cat .runtime/agents/evolver/SOUL.md | grep "Workflows"  # 不应存在
```

### 3.3 Skills symlink 验证

| | |
|---|---|
| **操作** | 检查 skills symlink 指向 |
| **目的** | symlink 正确指向 agent/flow/ 目录 |

```bash
readlink .runtime/agents/default/.claude/skills/check_health
# 应指向 ../../../../../../agent/flow/check_health 或类似相对路径

# default 不应有 review_task（分配给 reviewer）
ls .runtime/agents/default/.claude/skills/ | grep review_task  # 不应存在

# evolver 不应有业务 skill
ls .runtime/agents/evolver/.claude/skills/ | grep create_task  # 不应存在
```

### 3.4 编译产物验证

| | |
|---|---|
| **操作** | 检查生成的 flow.yaml / commitment.yaml / manifest |
| **目的** | 从 socialware.py 正确生成 |

```bash
# flow.yaml
cat .runtime/flow.yaml
# direct_actions 应包含 check_health, create_task, list_tasks（非 transition 的）
# flows.task_lifecycle 应包含 transitions

# commitment.yaml
cat .runtime/commitment.yaml
# commitments[0].id = C1

# manifest
cat .runtime/compile_manifest.yaml
# app: task-review, roles: default/dev/reviewer/evolver
```

### 3.5 Flow 校验错误

| | |
|---|---|
| **操作** | 注册 action 但不创建 SKILL.md |
| **目的** | 编译器正确报错 |

```bash
# 在 socialware.py 中添加一个不存在的 action
# app.action("nonexistent_action", role=["default"])
socialwares deploy  # Error: action 'nonexistent_action': 目录不存在
```

### 3.6 适配器切换

| | |
|---|---|
| **操作** | `socialwares deploy --adapter codex` |
| **目的** | 不同适配器生成不同配置 |

```bash
socialwares deploy --adapter codex

# codex 使用 AGENTS.md 而不是 SOUL.md
ls .runtime/agents/default/AGENTS.md  # 应存在
ls .runtime/agents/default/SOUL.md    # 不应存在

# codex 使用 .agents/skills/ 而不是 .claude/skills/
ls .runtime/agents/default/.agents/skills/  # 应存在

# 恢复 claude
socialwares deploy
```

---

## Phase 4: 本地启动

### 4.1 单角色启动

| | |
|---|---|
| **操作** | `socialwares start --role default` |
| **目的** | 启动 Claude Code TUI |
| **预期** | Claude Code 启动，加载 SOUL.md + skills |

```bash
# 先杀掉之前可能残留的后端进程
fuser -k 8001/tcp 2>/dev/null || true

# 启动后端（端口来自 pyproject.toml [tool.socialwares] api_port）
uvicorn src.api:app --port 8001 &

# 启动 agent（adapter 自动从 pyproject.toml 读取，无需 --adapter）
socialwares start --role default
# Claude Code 打开，SOUL.md 加载（含 Backend: http://localhost:8001）
# 输入 "check health" → 验证 skill 可用
# Ctrl+C 退出
```

### 4.2 多角色启动

| | |
|---|---|
| **操作** | `socialwares start --role default,reviewer,evolver` |
| **目的** | tmux 多窗格启动 |
| **预期** | tmux session 创建，3 个窗格各一个角色 |

```bash
socialwares start --role default,reviewer,evolver
# 3 个 tmux pane
# 可以在不同 pane 测试不同角色
# tmux kill-session 退出
```

### 4.3 Evolver 交互

| | |
|---|---|
| **操作** | 启动 evolver，执行各项检测 |
| **目的** | 验证 evolve skills 完整可用 |

```bash
socialwares start --role evolver
# "check structure"     → 四原语一致性报告
# "evaluate"            → API 测试结果
# "diagnose"            → 对话数据分析
# "improve"             → 改进建议
```

---

## Phase 5: IRC 频道安装

### 5.1 socialwares install

| | |
|---|---|
| **操作** | 将项目作为 git 仓库安装 |
| **目的** | git clone + 编译 |

```bash
# 先把项目初始化为 git 仓库（在 task-review 目录下）
cd task-review
git init && git add -A && git commit -m "init"
cd ..

# 安装（在仓库根目录执行）
socialwares install ./task-review --channel "#test"
# ✓ Installed task-review to #test

# 验证安装
socialwares list
# task-review (#test) — roles: default, dev, reviewer, evolver

# 验证 app 目录
ls .socialware/workspace/test/apps/task-review/.runtime/agents/
# default  dev  reviewer  evolver
```

### 5.2 socialwares assign

| | |
|---|---|
| **操作** | 分配角色到 agent |
| **目的** | 验证文件正确注入到 workspace/{channel}/agents/ |

```bash
# 在仓库根目录执行
socialwares assign alice-support  --role default  --channel "#test"
socialwares assign bob-reviewer   --role reviewer --channel "#test"
socialwares assign alice-evolver  --role evolver  --channel "#test"

# 验证 agent workspace
ls .socialware/workspace/test/agents/alice-support/
# SOUL.md  flow.yaml  commitment.yaml  .claude/

ls .socialware/workspace/test/agents/alice-support/.claude/
# settings.local.json  skills

# 验证 settings.local.json merge（保留 permissions + 追加 hooks）
cat .socialware/workspace/test/agents/alice-support/.claude/settings.local.json
# {"permissions": {"allow": []}, "hooks": {"UserPromptSubmit": [...], "PreToolUse": [...]}}

# 验证 skills 是逐个 symlink（不是整个目录替换）
ls -la .socialware/workspace/test/agents/alice-support/.claude/skills/
# check_health -> .../task-review/.runtime/agents/default/.claude/skills/check_health
```

### 5.3 socialwares uninstall

| | |
|---|---|
| **操作** | 卸载 App |
| **目的** | 清理注入的文件 |

```bash
socialwares uninstall task-review --channel "#test"
# ✓ Uninstalled task-review from #test

socialwares list
# No apps installed.

# 验证 agent workspace 已清理
ls .socialware/workspace/test/agents/alice-support/
# SOUL.md 应该不存在，skills symlink 已清除
```

---

## Phase 6: Evolve Skills 验证

### 6.1 evolve_structure_check

| | |
|---|---|
| **操作** | evolver 运行结构检查 |
| **预期** | 检查四原语一致性，报告通过/失败 |

```bash
socialwares start --role evolver
# "check structure"
# ✓ All actions have SKILL.md
# ✓ All roles have actions
# ✓ Flow graph valid
```

### 6.2 evolve_api_check

| | |
|---|---|
| **操作** | evolver 运行 API 测试 |
| **前置** | 后端运行中，eval_cases.yaml 已配置 |

```bash
# 确保后端运行
uvicorn src.api:app --port 8001 &

# 编辑 eval_cases.yaml（在 agent/flow/evolve_api_check/）
socialwares start --role evolver
# "evaluate"
# Running X API checks...
# [PASS/FAIL] 结果
```

### 6.3 evolve_session_diagnose

| | |
|---|---|
| **操作** | 先产生一些对话数据，再诊断 |
| **前置** | hooks 记录了 prompts |

```bash
# 先和 default agent 对话几轮（产生 .runtime/data/prompts/ 数据）
socialwares start --role default
# "create task: test" / "list tasks" / "submit task" 等

# 再用 evolver 诊断
socialwares start --role evolver
# "diagnose"
# 检查 commitment C1 的履行情况
```

### 6.4 evolve_improve

| | |
|---|---|
| **操作** | evolver 给出改进建议 |
| **预期** | 基于诊断结果，提出四原语改进 |

```bash
socialwares start --role evolver
# "improve"
# 建议: ...
```

### 6.5 自定义 evolve skill

| | |
|---|---|
| **操作** | 添加自定义 evolve 检查 |
| **目的** | 验证用户扩展能力 |

```bash
# 创建自定义 evolve skill
mkdir -p agent/flow/evolve_review_quality/scripts
cat > agent/flow/evolve_review_quality/SKILL.md << 'EOF'
---
name: evolve_review_quality
description: "Check review quality"
---
# Review Quality Check
## Trigger
User says "check review quality"
## Flow
1. Read review data from prompts
2. Check comment length > 10 chars
3. Report quality score
EOF

cat > agent/flow/evolve_review_quality/scripts/check_quality.py << 'EOF'
#!/usr/bin/env python3
print("Review quality: OK")
EOF

# 在 socialware.py 注册
# app.action("evolve_review_quality", role=["evolver"])

socialwares deploy
ls .runtime/agents/evolver/.claude/skills/ | grep review_quality  # 应存在
```

---

## Phase 7: pip 包构建与分发

### 7.1 构建

| | |
|---|---|
| **操作** | `uv build` |
| **预期** | 生成 .tar.gz 和 .whl |

```bash
cd Socialwares  # 框架仓库根目录
uv build
ls dist/
# socialwares-0.2.0.tar.gz
# socialwares-0.2.0-py3-none-any.whl
```

### 7.2 从 wheel 安装验证

| | |
|---|---|
| **操作** | 在干净环境安装 wheel |
| **预期** | socialwares 命令可用 |

```bash
# 创建临时 venv
python -m venv /tmp/test-sw-venv
source /tmp/test-sw-venv/bin/activate
pip install dist/socialwares-0.2.0-py3-none-any.whl

socialwares --help
socialwares new test-from-wheel
ls test-from-wheel/  # 应有完整项目结构

deactivate
rm -rf /tmp/test-sw-venv
```

### 7.3 从 git 安装验证

| | |
|---|---|
| **操作** | `pip install git+...` |
| **预期** | 等同于 wheel 安装 |

```bash
pip install git+https://github.com/ezagent42/Socialwares.git
socialwares --help
```

---

## Phase 8: pyproject.toml 配置

### 8.1 adapter 配置

| | |
|---|---|
| **操作** | 修改 [tool.socialwares] adapter |
| **预期** | deploy 使用指定适配器 |

```toml
# pyproject.toml
[tool.socialwares]
adapter = "codex"
```

```bash
socialwares deploy  # 使用 codex 适配器（不需要 --adapter 参数）
ls .runtime/agents/default/AGENTS.md  # codex 格式
```

### 8.2 agent_dir 配置

| | |
|---|---|
| **操作** | 修改 agent_dir |
| **预期** | 编译器从指定目录读取四原语 |

```toml
[tool.socialwares]
agent_dir = "my-agent"
```

```bash
mv agent my-agent
socialwares deploy  # 应从 my-agent/ 读取
```

---

## 测试完成检查清单

- [ ] Phase 1: `socialwares new` 生成完整项目
- [ ] Phase 2: `socialware.py` 声明式 API 可用
- [ ] Phase 3: `socialwares deploy` 正确编译（SOUL.md、skills symlink、flow.yaml、commitment.yaml、hooks、manifest）
- [ ] Phase 3: 适配器切换（claude/codex）生成不同格式
- [ ] Phase 3: 缺失 SKILL.md 报错
- [ ] Phase 4: 单角色 / 多角色本地启动
- [ ] Phase 4: Evolver 交互可用
- [ ] Phase 5: `socialwares install` git clone + 编译
- [ ] Phase 5: `socialwares assign` 注入文件到 workspace（JSON merge 正确）
- [ ] Phase 5: `socialwares uninstall` 清理
- [ ] Phase 6: 5 个内置 evolve skill 可用
- [ ] Phase 6: 自定义 evolve skill 可注册可编译
- [ ] Phase 7: `uv build` 构建成功
- [ ] Phase 7: wheel 安装后 CLI 可用
- [ ] Phase 8: pyproject.toml 配置生效
