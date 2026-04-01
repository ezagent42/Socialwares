# Release E2E Test Plan — Socialwares v0.2.0

完整功能验证。按真实开发流程组织：创建 → 定义 → 编译 → 开发 → 测试 → 部署。

## 前置条件

```bash
# 开发模式安装
cd Socialwares
uv pip install -e .
source .venv/bin/activate

# 验证
socialwares --help
python -c "from socialwares import App; print('OK')"

# 清理旧测试数据
rm -rf task-review .socialware/workspace/
```

---

## Phase 1: 项目创建

### 1.1 socialwares new

| | |
|---|---|
| **操作** | `socialwares new task-review` |
| **预期** | 完整的四原语项目结构 |

```bash
socialwares new task-review
cd task-review

# 项目结构
ls                          # socialware.py  agent  src  app  pyproject.toml
ls agent/role/              # default.md  dev.md  evolver.md
ls agent/scope/             # scope.md
ls agent/commitment/        # README.md
ls agent/flow/              # check_health  dev_define  dev_build  dev_release
                            # inspect  setup_claude
                            # evolve_structure_check  evolve_api_check  evolve_session_diagnose
                            # evolve_improve  evolve_auto
# skill 规范：每个目录都有 SKILL.md + scripts/ + references/
ls agent/flow/dev_define/   # SKILL.md  scripts/  references/
```

### 1.2 模板渲染

```bash
grep 'App("task-review")' socialware.py         # 应匹配
grep '{{APP_NAME}}' socialware.py                # 不应匹配
grep 'dev_define' socialware.py                  # 应匹配
grep 'dev_build' socialware.py                   # 应匹配
grep 'name = "task-review"' pyproject.toml       # 应匹配
```

### 1.3 重复创建阻止

```bash
cd ..
socialwares new task-review   # Error: task-review/ already exists
cd task-review
```

---

## Phase 2: 定义四原语（Dev 角色交互式引导）

### 2.1 首次编译 + 启动 dev

```bash
socialwares deploy   # 编译默认模板，让 dev 角色可用
socialwares start --role dev
```

### 2.2 dev_define 交互式引导

| | |
|---|---|
| **操作** | 在 dev agent 中说 "define" |
| **预期** | Agent 严格逐步引导：每步只问一个原语，确认后才继续 |

```
你: "define"

── Step 0: Agent 检查当前状态 ──
Agent: "当前是模板默认状态，3 个内置角色，1 个 check_health action。从头开始定义。"

── Step 1: Scope ──
Agent: "What does this App do? What are the main features? And what does it NOT do?"
你: "任务审核 App。创建任务、查看列表、提交审核、审核通过/退回、关闭任务。不管权限不发通知。"
Agent: 写入 scope.md（只有 Capabilities + Boundaries），展示结果
你: "OK"

── Step 2: Role ──
Agent: "Who uses this App? What are each role's responsibilities?"
你: "default 负责创建和提交任务，reviewer 负责审核任务"
Agent: 创建 agent/role/reviewer.md，注册到 socialware.py
你: "OK"

── Step 3: Flow ──
Agent: "What actions can each role perform?"
你: "default: create_task, list_tasks; reviewer: review_task, list_tasks; 都能 check_health"
Agent: 创建 SKILL.md 目录（含 scripts/ + references/），注册到 socialware.py
Agent: "Is there a fixed order between these actions?"
你: "有。draft → submit_task → submitted → review_task → reviewed → close_task → closed"
Agent: 定义 flow 到 socialware.py
你: "OK"

── Step 4: Commitment ──
Agent: "Are there collaboration constraints between roles?"
你: "提交后 24h 内必须审核，否则提醒 reviewer"
Agent: 添加 commitment，用白话翻译确认
你: "OK"

── Step 5: Deploy ──
Agent: 执行 socialwares deploy，展示结果
Agent: "Four primitives defined. Say 'build' to start developing frontend and backend."
```

Ctrl+C 退出 dev agent。

### 2.3 验证结果

```bash
# socialware.py 注册正确
grep 'reviewer' socialware.py
grep 'create_task' socialware.py
grep 'task_lifecycle' socialware.py
grep 'commitment' socialware.py

# 角色文件
ls agent/role/          # default.md  dev.md  evolver.md  reviewer.md

# skill 目录规范
ls agent/flow/create_task/    # SKILL.md  scripts/  references/
ls agent/flow/review_task/    # SKILL.md  scripts/  references/

# scope 内容
cat agent/scope/scope.md      # 应有 Capabilities + Boundaries，无 Connections
```

### 2.4 手动补齐（如果 Agent 遗漏）

```bash
# flow transition 中引用的 action 都要有 SKILL.md
for skill in submit_task close_task remind_review; do
    if [ ! -f "agent/flow/$skill/SKILL.md" ]; then
        mkdir -p agent/flow/$skill/{scripts,references}
        echo -e "---\nname: $skill\n---\n# ${skill//_/ }" > agent/flow/$skill/SKILL.md
        echo "  Created $skill"
    fi
done
socialwares deploy
```

---

## Phase 3: 编译验证

### 3.1 deploy 输出

```bash
socialwares deploy

ls .runtime/agents/          # default  dev  reviewer  evolver

ls .runtime/agents/default/.claude/skills/
# check_health  close_task  create_task  list_tasks  submit_task

ls .runtime/agents/dev/.claude/skills/
# dev_build  dev_define  dev_release  inspect  setup_claude

ls .runtime/agents/reviewer/.claude/skills/
# check_health  list_tasks  review_task

ls .runtime/agents/evolver/.claude/skills/
# evolve_api_check  evolve_auto  evolve_improve  evolve_session_diagnose  evolve_structure_check  inspect
```

### 3.2 SOUL.md 验证

```bash
# default: scope + role + workflow + backend 端口
grep -c -- "---" .runtime/agents/default/SOUL.md    # 至少 3 个分隔符
grep "Workflows" .runtime/agents/default/SOUL.md     # 应存在
grep "submit_task" .runtime/agents/default/SOUL.md   # 应存在
grep "localhost:8001" .runtime/agents/default/SOUL.md # Backend 端口注入

# reviewer: scope + role (由 dev_define 创建的 file= 方式)
cat .runtime/agents/reviewer/SOUL.md | head -20       # 应有 reviewer 角色描述

# evolver: 不应有 workflow（不参与 task_lifecycle）
grep "Workflows" .runtime/agents/evolver/SOUL.md     # 不应存在
```

### 3.3 Hook 脚本验证

```bash
# hooks 是 Python 脚本（跨平台）
ls .runtime/agents/default/.claude/hooks/
# log_prompt.py  log_tool.py（注意是 .py 不是 .sh）

# hook command 使用 uv run --no-project
cat .runtime/agents/default/.claude/settings.local.json | grep "uv run --no-project"
# 应匹配

# 验证 hook 脚本语法正确
python -c "compile(open('.runtime/agents/default/.claude/hooks/log_prompt.py').read(), 'test', 'exec')"
```

### 3.4 Skills symlink

```bash
readlink .runtime/agents/default/.claude/skills/check_health
# 应指向相对路径到 agent/flow/check_health

# default 不应有 review_task
ls .runtime/agents/default/.claude/skills/ | grep review_task  # 不应存在

# evolver 不应有业务 skill
ls .runtime/agents/evolver/.claude/skills/ | grep create_task  # 不应存在
```

### 3.5 编译产物格式

```bash
# flow.yaml — 含显式 states 列表
cat .runtime/flow.yaml
# flows.task_lifecycle.states: [draft, submitted, reviewed, closed]
# flows.task_lifecycle.transitions: 3 条

# commitment.yaml — dict 格式（不是 list）
cat .runtime/commitment.yaml
# commitments:
#   C1:
#     condition: within 24h
#     from: {role: default, action: submit_task}

# manifest
cat .runtime/compile_manifest.yaml
# app: task-review, roles: default/dev/reviewer/evolver
```

### 3.6 编译错误

```bash
# 临时在 socialware.py 中添加：app.action("nonexistent", role=["default"])
socialwares deploy  # Error: 目录不存在
# 删掉后恢复正常
```

### 3.7 适配器切换幂等

```bash
socialwares deploy --adapter codex

# codex 格式
ls .runtime/agents/default/AGENTS.md                    # 应存在
ls .runtime/agents/default/SOUL.md 2>/dev/null          # 不应存在
ls .runtime/agents/default/.agents/skills/              # 应存在
ls .runtime/agents/default/.claude/ 2>/dev/null         # 不应存在（已清理）

# 切回 claude
socialwares deploy
ls .runtime/agents/default/SOUL.md                      # 应存在
ls .runtime/agents/default/AGENTS.md 2>/dev/null        # 不应存在
ls .runtime/agents/default/.agents/ 2>/dev/null         # 不应存在（已清理）
```

### 3.8 Inline role 自动生成文件（编译器功能验证）

```bash
# 临时测试：用 inline 方式定义角色
# 在 socialware.py 中临时添加：app.role("tester", "A test role for QA")
socialwares deploy
ls agent/role/tester.md  # 应存在（编译器 _sync_inline_content 自动生成）
cat agent/role/tester.md # 内容: "A test role for QA"
# 删掉 tester 相关行后恢复
```

---

## Phase 4: 开发（Dev 角色 TDD）

### 4.1 启动后端 + dev 角色开发

```bash
fuser -k 8001/tcp 2>/dev/null || true
uvicorn src.api:app --port 8001 &

socialwares start --role dev
# "build"
# Agent 检查无报告 → 引导从零 TDD 开发
# 写测试 → 实现 API → 验证 → deploy
# Ctrl+C 退出
```

### 4.2 启动 default 角色手动测试

```bash
socialwares start --role default
# "check health"    → 验证 skill 可用
# "create task: test bug fix"
# "list tasks"
# Ctrl+C 退出
```

### 4.3 多角色启动

```bash
socialwares start --role default,reviewer,evolver
# tmux session，3 个窗格
# tmux kill-session 退出
```

### 4.4 SDK 模式

```bash
socialwares start --role default --prompt "check health"
# 应输出 health check 结果

ls .runtime/data/sessions/
# 应有 session_*.json 文件
```

---

## Phase 5: Evolve 测试

### 5.1 structure_check

```bash
socialwares start --role evolver
# "check structure"
# ✓ All actions have SKILL.md
# ✓ All roles have actions
# ✓ Flow graph valid (4 states, 3 transitions)
# ✓ Commitment references valid
# Report saved to .runtime/data/evolve/reports/check_*.json
# Ctrl+C 退出
```

### 5.2 api_check（含覆盖率）

```bash
fuser -k 8001/tcp 2>/dev/null || true
uvicorn src.api:app --port 8001 &

socialwares start --role evolver
# "evaluate"
# [PASS] Health check
# suggestions 应包含未覆盖 action 的建议
# Ctrl+C 退出
```

### 5.3 session_diagnose

```bash
# 确认 hook 数据存在（Phase 4.2 产生）
ls .runtime/data/prompts/current.jsonl    # 应有记录
wc -l .runtime/data/prompts/current.jsonl # 应有多行

socialwares start --role evolver
# "diagnose"
# 读取 prompts 数据 + commitment.yaml
# Report saved to .runtime/data/evolve/reports/diagnose_*.json
# Ctrl+C 退出
```

### 5.4 improve

```bash
socialwares start --role evolver
# "improve"
# 基于 check + eval + diagnose 报告提出建议
# Ctrl+C 退出
```

### 5.5 完整数据链路验证

```bash
ls .runtime/data/prompts/current.jsonl           # hooks 产生数据
ls .runtime/data/evolve/reports/check_*.json     # structure check
ls .runtime/data/evolve/reports/eval_*.json      # api check
ls .runtime/data/evolve/reports/diagnose_*.json  # diagnose
# 三种报告都应存在
```

### 5.6 Dev 角色读报告改进

```bash
socialwares start --role dev
# "build"
# Agent 检测到 .runtime/data/evolve/reports/ 有报告
# 先读报告、列出待修项，再引导 TDD 修复
# Ctrl+C 退出
```

### 5.7 自定义 evolve skill

```bash
mkdir -p agent/flow/evolve_review_quality/{scripts,references}

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

# 在 socialware.py 注册：app.action("evolve_review_quality", role=["evolver"])
socialwares deploy
ls .runtime/agents/evolver/.claude/skills/ | grep review_quality  # 应存在
```

---

## Phase 6: IRC 频道安装

### 6.1 install

```bash
# 初始化 git 仓库
git init && git add -A && git commit -m "init"

# 回到仓库根目录
cd ..
socialwares install ./task-review --channel "#test"
# ✓ Installed task-review to #test

socialwares list
# task-review (#test) — roles: default, dev, reviewer, evolver

ls .socialware/workspace/test/apps/task-review/.runtime/agents/
# default  dev  reviewer  evolver
```

### 6.2 assign

```bash
socialwares assign alice-support  --role default  --channel "#test"
socialwares assign bob-reviewer   --role reviewer --channel "#test"
socialwares assign alice-evolver  --role evolver  --channel "#test"

# 验证 agent workspace
ls .socialware/workspace/test/agents/alice-support/
# SOUL.md  flow.yaml  commitment.yaml  .claude/

# settings.local.json merge（hooks 追加）
cat .socialware/workspace/test/agents/alice-support/.claude/settings.local.json
# 应有 hooks.UserPromptSubmit 和 hooks.PreToolUse

# skills 逐个 symlink
ls -la .socialware/workspace/test/agents/alice-support/.claude/skills/
# check_health -> .../default/.claude/skills/check_health
```

### 6.3 uninstall

```bash
socialwares uninstall task-review --channel "#test"
# ✓ Uninstalled task-review from #test

socialwares list
# No apps installed.

ls .socialware/workspace/test/agents/alice-support/SOUL.md 2>/dev/null  # 不应存在
```

---

## Phase 7: pip 包构建

### 7.1 构建

```bash
cd ..  # 回到框架仓库根目录
uv build
ls dist/
# socialwares-0.2.0.tar.gz  socialwares-0.2.0-py3-none-any.whl
```

### 7.2 wheel 安装验证

```bash
python -m venv /tmp/test-sw-venv
source /tmp/test-sw-venv/bin/activate
pip install dist/socialwares-0.2.0-py3-none-any.whl

socialwares --help
socialwares new test-from-wheel
ls test-from-wheel/  # 应有完整项目结构

deactivate
rm -rf /tmp/test-sw-venv
```

### 7.3 git 安装验证

```bash
pip install git+ssh://git@github.com/ezagent42/Socialwares.git@feat/release
socialwares --help
```

---

## Phase 8: pyproject.toml 配置

### 8.1 adapter 配置

```bash
cd task-review
# pyproject.toml: [tool.socialwares] adapter = "codex"
socialwares deploy  # 应使用 codex 适配器
ls .runtime/agents/default/AGENTS.md  # codex 格式

# 改回 claude
socialwares deploy
```

### 8.2 agent_dir 配置

```bash
# pyproject.toml: agent_dir = "my-agent"
mv agent my-agent
socialwares deploy  # 应从 my-agent/ 读取

# 恢复
mv my-agent agent
socialwares deploy
```

---

## 测试完成检查清单

**Phase 1: 创建**
- [ ] `socialwares new` 生成完整项目（3 内置角色、5 dev skill、5 evolve skill）
- [ ] 模板渲染正确（APP_NAME 替换、skill 注册）
- [ ] 重复创建被阻止

**Phase 2: 定义**
- [ ] dev_define 逐步引导（每步一个原语，确认后继续）
- [ ] scope.md 只有 Capabilities + Boundaries
- [ ] 生成的 skill 按规范（SKILL.md + scripts/ + references/）
- [ ] socialware.py 注册正确（role + action + flow + commitment）

**Phase 3: 编译**
- [ ] SOUL.md 合并正确（scope + role + workflow + backend port）
- [ ] hooks 为 .py 脚本，command 用 `uv run --no-project python`
- [ ] Skills symlink 正确指向 agent/flow/
- [ ] flow.yaml dict 格式含 states，commitment.yaml dict 格式
- [ ] 适配器切换幂等（旧文件/目录不残留）
- [ ] 缺失 SKILL.md 报错
- [ ] inline role 自动生成 .md 文件

**Phase 4: 开发**
- [ ] dev build TDD 引导可用
- [ ] default 角色可交互
- [ ] 多角色 tmux 启动
- [ ] SDK 模式 + session 保存

**Phase 5: Evolve**
- [ ] structure_check 报告 PASS
- [ ] api_check 含覆盖率 suggestion
- [ ] session_diagnose 读取 hooks 日志
- [ ] improve 基于报告建议
- [ ] 完整数据链路（hooks → prompts → diagnose → improve）
- [ ] dev build 读报告驱动改进
- [ ] 自定义 evolve skill 可注册可编译

**Phase 6: 部署**
- [ ] install 到 .socialware/workspace/{channel}/apps/
- [ ] assign 注入文件（JSON merge + skills 逐个 symlink）
- [ ] uninstall 清理

**Phase 7: 构建**
- [ ] uv build 成功
- [ ] wheel 安装后 CLI 可用

**Phase 8: 配置**
- [ ] adapter 配置生效
- [ ] agent_dir 配置生效
