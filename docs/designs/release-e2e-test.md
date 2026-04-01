# Release E2E Test Plan — Socialwares v0.2.0

基于 `pip install socialwares` 的完整功能验证。覆盖从安装框架到创建、编译、启动、安装到 IRC 频道的全流程。

## 前置条件

```bash
# 开发模式安装
cd Socialwares
uv pip install -e .

# 激活虚拟环境（否则 socialwares 命令不在 PATH 中）
source .venv/bin/activate

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
ls agent/role/              # default.md  dev.md  evolver.md
ls agent/scope/             # scope.md
ls agent/commitment/        # README.md
ls agent/flow/              # check_health  dev_define  dev_build  dev_release
                            # inspect  setup_claude
                            # evolve_structure_check  evolve_api_check  evolve_session_diagnose
                            # evolve_improve  evolve_auto
# 每个 skill 目录都有 SKILL.md + scripts/ + references/
ls agent/flow/evolve_structure_check/  # SKILL.md  scripts/  references/
ls agent/flow/dev_define/                # SKILL.md  scripts/  references/
```

### 1.2 App 声明文件渲染

| | |
|---|---|
| **操作** | 检查生成的 socialware.py |
| **目的** | 验证 {{APP_NAME}} 占位符被正确替换 |
| **预期** | 包含 `App("task-review")`，注册了 default/dev/evolver 角色和所有内置 action |

```bash
grep 'App("task-review")' socialware.py         # 应该匹配
grep '{{APP_NAME}}' socialware.py                # 不应匹配
grep 'name = "task-review"' pyproject.toml       # 应该匹配
grep 'dev_define' socialware.py                    # 应该匹配
grep 'dev_build' socialware.py                   # 应该匹配
grep 'dev_release' socialware.py                 # 应该匹配
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
cd task-review
```

---

## Phase 2: 通过 Dev 角色交互式定义四原语

### 2.1 启动 dev 角色，执行 init 引导

| | |
|---|---|
| **操作** | `socialwares start --role dev`，然后说 "define" |
| **目的** | 验证 dev_define skill 能交互式引导四原语定义 |
| **预期** | Agent 逐步引导完成 scope → role → flow → commitment |

```bash
socialwares deploy   # 先编译默认模板（让 dev 角色可用）
socialwares start --role dev
```

在 dev agent 中进行交互式引导：

```
你: "define"
Agent: 引导 Step 1 — Scope
你: "这是一个任务审核 App，功能包括创建任务、查看列表、提交审核、审核通过/退回"
Agent: 写入 agent/scope/scope.md，确认

Agent: 引导 Step 2 — Role
你: "两个角色：default 负责创建和提交任务，reviewer 负责审核任务"
Agent: 创建 agent/role/reviewer.md，注册到 socialware.py，确认

Agent: 引导 Step 3 — Flow（操作）
你: "default 能 create_task, list_tasks; reviewer 能 review_task, list_tasks; 都能 check_health"
Agent: 创建各 SKILL.md 目录（含 scripts/ + references/），注册到 socialware.py
Agent: "这些操作之间有没有固定的流转顺序？"
你: "有。draft → submit_task → submitted → review_task → reviewed → close_task → closed"
Agent: 定义 flow 流转到 socialware.py

Agent: 引导 Step 4 — Commitment
你: "提交后 24 小时内必须审核，否则提醒 reviewer"
Agent: 添加 commitment 到 socialware.py，用白话翻译确认

Agent: Step 5 — Deploy + 展示编译结果
```

Ctrl+C 退出 dev agent。

### 2.2 验证交互式定义的结果

| | |
|---|---|
| **操作** | 检查 dev_define 生成的文件 |
| **目的** | 确认四原语文件和 socialware.py 注册都正确 |

```bash
# 检查 socialware.py 包含了新注册的角色和 action
grep 'reviewer' socialware.py
grep 'create_task' socialware.py
grep 'flow.*task_lifecycle' socialware.py
grep 'commitment.*C1' socialware.py

# 检查角色文件
ls agent/role/          # default.md  dev.md  evolver.md  reviewer.md

# 检查 skill 目录（每个都应有 SKILL.md + scripts/ + references/）
ls agent/flow/create_task/    # SKILL.md  scripts/  references/
ls agent/flow/review_task/    # SKILL.md  scripts/  references/

# 检查 scope 内容被更新
cat agent/scope/scope.md      # 应包含 "任务审核" 相关描述
```

### 2.3 手动补齐（如果 Agent 遗漏）

| | |
|---|---|
| **操作** | 检查并补齐 dev_define 可能没覆盖的细节 |
| **说明** | Agent 可能不会自动创建所有 transition action 的 SKILL.md |

```bash
# 确保 flow transition 中引用的 action 都有 SKILL.md
for skill in submit_task close_task remind_review; do
    if [ ! -f "agent/flow/$skill/SKILL.md" ]; then
        mkdir -p agent/flow/$skill/{scripts,references}
        echo -e "---\nname: $skill\n---\n# ${skill//_/ }" > agent/flow/$skill/SKILL.md
        echo "  Created $skill"
    fi
done

# 重新编译验证
socialwares deploy
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
# dev_build  dev_define  dev_release  inspect  setup_claude

ls .runtime/agents/reviewer/.claude/skills/
# check_health  list_tasks  review_task

ls .runtime/agents/evolver/.claude/skills/
# evolve_api_check  evolve_auto  evolve_improve  evolve_session_diagnose  evolve_structure_check  inspect
```

### 3.2 SOUL.md 合并验证

| | |
|---|---|
| **操作** | 检查 SOUL.md 内容 |
| **目的** | scope + role 正确合并，workflow 正确注入，Backend 端口注入 |

```bash
# default 的 SOUL.md 应包含 scope + role + workflow + backend
grep -c -- "---" .runtime/agents/default/SOUL.md    # 至少 3 个分隔符
grep "Workflows" .runtime/agents/default/SOUL.md     # 应存在
grep "submit_task" .runtime/agents/default/SOUL.md   # 应存在
grep "localhost:8001" .runtime/agents/default/SOUL.md # Backend 端口注入

# reviewer 的 SOUL.md 应包含 inline 定义的内容
grep "review and approve" .runtime/agents/reviewer/SOUL.md  # 应存在

# reviewer 角色文件应被 inline 自动生成
ls agent/role/reviewer.md  # 应存在（编译器自动生成）

# evolver 的 SOUL.md 不应包含 workflow（不参与 task_lifecycle）
grep "Workflows" .runtime/agents/evolver/SOUL.md     # 不应存在
```

### 3.3 Skills symlink 验证

| | |
|---|---|
| **操作** | 检查 skills symlink 指向 |
| **目的** | symlink 正确指向 agent/flow/ 目录 |

```bash
readlink .runtime/agents/default/.claude/skills/check_health
# 应指向相对路径到 agent/flow/check_health

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
# flow.yaml — dict 格式，含 states
cat .runtime/flow.yaml
# direct_actions 应包含 check_health, create_task, list_tasks 等
# flows.task_lifecycle.states = [draft, submitted, reviewed, closed]
# flows.task_lifecycle.transitions 应有 3 条

# commitment.yaml — dict 格式（不是 list）
cat .runtime/commitment.yaml
# commitments.C1.condition = "within 24h"
# commitments.C1.from.role = default

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
# 临时在 socialware.py 中添加一行：
# app.action("nonexistent_action", role=["default"])
socialwares deploy  # Error: action 'nonexistent_action': 目录不存在
# 删掉这行后恢复正常
```

### 3.6 适配器切换（幂等验证）

| | |
|---|---|
| **操作** | `socialwares deploy --adapter codex` 然后切回 claude |
| **目的** | 不同适配器生成不同配置，切换后旧文件不残留 |

```bash
socialwares deploy --adapter codex

# codex 使用 AGENTS.md 而不是 SOUL.md
ls .runtime/agents/default/AGENTS.md     # 应存在
ls .runtime/agents/default/SOUL.md 2>/dev/null  # 不应存在（已清理）

# codex 使用 .agents/skills/
ls .runtime/agents/default/.agents/skills/  # 应存在
ls .runtime/agents/default/.claude/ 2>/dev/null  # 不应存在（已清理）

# 恢复 claude
socialwares deploy
ls .runtime/agents/default/SOUL.md       # 应存在
ls .runtime/agents/default/AGENTS.md 2>/dev/null  # 不应存在
ls .runtime/agents/default/.agents/ 2>/dev/null   # 不应存在
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

# 启动 agent（adapter 自动从 pyproject.toml 读取）
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
# 3 个 tmux pane，每个加载不同角色的 SOUL.md + skills
# tmux kill-session 退出
```

### 4.3 Evolver 交互 + 报告验证

| | |
|---|---|
| **操作** | 启动 evolver，执行各项检测，验证报告生成 |
| **目的** | 验证 evolve skills 完整可用 + 报告输出 |

```bash
socialwares start --role evolver
# "check structure"     → 四原语一致性报告
# "evaluate"            → API 测试结果（含覆盖率 suggestion）
# "diagnose"            → 对话数据分析
# "improve"             → 改进建议
# Ctrl+C 退出

# 验证报告输出
ls .runtime/data/evolve/reports/
# check_*.json  eval_*.json  diagnose_*.json

# 检查 eval 报告是否有覆盖率 suggestion
cat .runtime/data/evolve/reports/eval_*.json | grep "suggestions"
# 应包含未覆盖 action 的 suggestion（如 create_task, list_tasks 等）
```

### 4.4 Dev 角色

| | |
|---|---|
| **操作** | 启动 dev 角色 |
| **目的** | 验证 dev skills（inspect, setup_claude, dev_define, dev_build, dev_release） |

```bash
socialwares start --role dev
# "inspect"     → 展示项目结构
# "define"      → 定义/重新定义四原语
# "build"       → TDD 引导（写测试→实现→验证）
# "release"     → 定版发布引导（deploy→检查→commit→push）
# Ctrl+C 退出
```

### 4.5 SDK 模式

| | |
|---|---|
| **操作** | `socialwares start --role default --prompt "check health"` |
| **目的** | 验证 SDK 模式（非交互式，发送单条 prompt） |
| **预期** | 执行后输出结果，session 保存到 .runtime/data/sessions/ |

```bash
socialwares start --role default --prompt "check health"
# 应输出 health check 结果

# 验证 session 记录
ls .runtime/data/sessions/
# 应有 session_*.json 文件
```

---

## Phase 5: IRC 频道安装

### 5.1 socialwares install

| | |
|---|---|
| **操作** | 将项目作为 git 仓库安装 |
| **目的** | git clone + 编译到 .socialware/workspace/ |

```bash
# 先把项目初始化为 git 仓库
git init && git add -A && git commit -m "init"

# 回到仓库根目录执行安装
cd ..
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

# 验证 skills 是逐个 symlink
ls -la .socialware/workspace/test/agents/alice-support/.claude/skills/
# check_health -> .../default/.claude/skills/check_health
# create_task -> ...
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

# 验证 agent workspace 中注入的文件已清理
ls .socialware/workspace/test/agents/alice-support/SOUL.md 2>/dev/null  # 不应存在
ls .socialware/workspace/test/agents/alice-support/.claude/skills/ 2>/dev/null  # symlinks 已清除
```

---

## Phase 6: Evolve Skills 深度验证

### 6.1 evolve_structure_check

| | |
|---|---|
| **操作** | evolver 运行结构检查 |
| **预期** | 检查四原语一致性，报告 PASS，输出到 .runtime/data/evolve/reports/ |

```bash
# 回到 task-review 目录
cd task-review
socialwares start --role evolver
# "check structure"
# ✓ All actions have SKILL.md
# ✓ All roles have actions
# ✓ Flow graph valid（4 states, 3 transitions）
# ✓ Commitment references valid
# Report saved to .runtime/data/evolve/reports/check_*.json
```

### 6.2 evolve_api_check（含覆盖率）

| | |
|---|---|
| **操作** | evolver 运行 API 测试 |
| **前置** | 后端运行中 |
| **预期** | health check PASS + 未覆盖 action 的 suggestion |

```bash
fuser -k 8001/tcp 2>/dev/null || true
uvicorn src.api:app --port 8001 &

socialwares start --role evolver
# "evaluate"
# [PASS] Health check
# API Score: 1/1 (100%)
# suggestions 应包含: "Add eval case for action 'create_task'" 等
```

### 6.3 evolve_session_diagnose

| | |
|---|---|
| **操作** | 先产生对话数据，再诊断 |
| **前置** | hooks 记录了 prompts |

```bash
# 先和 default agent 对话几轮（产生 hook 日志）
socialwares start --role default
# "create task: test bug fix"
# "list tasks"
# Ctrl+C 退出

# 检查 hook 日志
ls .runtime/data/prompts/
# current.jsonl（应有记录）

# 再用 evolver 诊断
socialwares start --role evolver
# "diagnose"
# 检查 commitment C1 的履行情况
# Report saved to .runtime/data/evolve/reports/diagnose_*.json
```

### 6.4 evolve_improve

| | |
|---|---|
| **操作** | evolver 基于报告给出改进建议 |
| **前置** | .runtime/data/evolve/reports/ 下有报告 |

```bash
socialwares start --role evolver
# "improve"
# 应基于 check/eval/diagnose 报告提出建议
# 如："create_task 没有 eval case，建议添加"
```

### 6.5 evolve_auto（自动对话测试）

| | |
|---|---|
| **操作** | evolver 运行自动对话测试 |
| **前置** | conversation_tests 目录有测试 YAML |

```bash
socialwares start --role evolver
# "auto test"
# 运行 agent/flow/evolve_auto/conversation_tests/ 下的测试
```

### 6.6 Evolver 完整数据链路验证

| | |
|---|---|
| **操作** | 验证 hooks → prompts → diagnose → improve 完整链路 |
| **目的** | 端到端数据流 |

```bash
# 1. hooks 产生数据
ls .runtime/data/prompts/current.jsonl           # 应有内容
wc -l .runtime/data/prompts/current.jsonl        # 应有多行记录

# 2. diagnose 读取数据
ls .runtime/data/evolve/reports/diagnose_*.json  # 应有报告

# 3. improve 基于所有报告
ls .runtime/data/evolve/reports/                 # check + eval + diagnose 报告都在
```

### 6.7 自定义 evolve skill

| | |
|---|---|
| **操作** | 添加自定义 evolve 检查 |
| **目的** | 验证用户扩展 evolve 能力 |

```bash
# 创建自定义 evolve skill（遵循 SKILL.md + scripts/ + references/ 规范）
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

cat > agent/flow/evolve_review_quality/scripts/check_quality.py << 'EOF'
#!/usr/bin/env python3
print("Review quality: OK")
EOF

# 在 socialware.py 中添加：
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
cd ..  # 回到框架仓库根目录
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
python -m venv /tmp/test-sw-venv
source /tmp/test-sw-venv/bin/activate
pip install dist/socialwares-0.2.0-py3-none-any.whl

socialwares --help
socialwares new test-from-wheel
ls test-from-wheel/  # 应有完整项目结构

deactivate
rm -rf /tmp/test-sw-venv /tmp/test-from-wheel
```

### 7.3 从 git 安装验证（需要先 push）

| | |
|---|---|
| **操作** | `pip install git+...` |
| **前置** | `git push -u origin feat/release` |

```bash
pip install git+https://github.com/ezagent42/Socialwares.git@feat/release
socialwares --help
```

---

## Phase 8: pyproject.toml 配置

### 8.1 adapter 配置

| | |
|---|---|
| **操作** | 修改 [tool.socialwares] adapter |
| **预期** | deploy 使用指定适配器 |

```bash
cd task-review
# 编辑 pyproject.toml:
# [tool.socialwares]
# adapter = "codex"

socialwares deploy  # 使用 codex 适配器（不需要 --adapter 参数）
ls .runtime/agents/default/AGENTS.md  # codex 格式

# 改回 claude
# adapter = "claude"
socialwares deploy
```

### 8.2 agent_dir 配置

| | |
|---|---|
| **操作** | 修改 agent_dir |
| **预期** | 编译器从指定目录读取四原语 |

```bash
# 编辑 pyproject.toml:
# agent_dir = "my-agent"

mv agent my-agent
socialwares deploy  # 应从 my-agent/ 读取

# 恢复
mv my-agent agent
# agent_dir = "agent"
socialwares deploy
```

---

## 测试完成检查清单

- [ ] Phase 1: `socialwares new` 生成完整项目（含 dev 角色、5 个 dev skill）
- [ ] Phase 1: socialware.py 模板渲染正确（dev_build, dev_release 已注册）
- [ ] Phase 2: dev_define 交互式引导四原语定义
- [ ] Phase 2: 生成的 skill 按规范创建（SKILL.md + scripts/ + references/）
- [ ] Phase 3: `socialwares deploy` 正确编译（SOUL.md、skills symlink、flow.yaml、commitment.yaml、hooks、manifest）
- [ ] Phase 3: hooks 为 Python 脚本（.py，跨平台）
- [ ] Phase 3: inline role 自动生成 .md 文件
- [ ] Phase 3: Backend 端口注入到 SOUL.md
- [ ] Phase 3: commitment.yaml 为 dict 格式，flow.yaml 含 states
- [ ] Phase 3: 适配器切换幂等（旧文件/目录不残留）
- [ ] Phase 3: 缺失 SKILL.md 报错
- [ ] Phase 4: 单角色 / 多角色本地启动（Python launcher，跨平台）
- [ ] Phase 4: Evolver 交互 + 报告输出到 .runtime/data/evolve/reports/
- [ ] Phase 4: Dev 角色可用（inspect, dev_define, dev_build, dev_release）
- [ ] Phase 4: SDK 模式可用 + session 保存
- [ ] Phase 5: `socialwares install` 到 .socialware/workspace/{channel}/apps/
- [ ] Phase 5: `socialwares assign` 注入文件（JSON merge 正确，skills 逐个 symlink）
- [ ] Phase 5: `socialwares uninstall` 清理
- [ ] Phase 6: structure_check 读取 .runtime/ 中的 flow.yaml + commitment.yaml
- [ ] Phase 6: api_check 含覆盖率 suggestion
- [ ] Phase 6: session_diagnose 读取 hooks 日志
- [ ] Phase 6: evolve_auto 可用
- [ ] Phase 6: 完整数据链路验证（hooks → prompts → diagnose → improve）
- [ ] Phase 6: 自定义 evolve skill 可注册可编译
- [ ] Phase 7: `uv build` 构建成功
- [ ] Phase 7: wheel 安装后 CLI 可用
- [ ] Phase 8: pyproject.toml adapter/agent_dir 配置生效
