# Evolve V3 — Hook + SDK + Evolver Improvement Plan

> Based on discussions about commitment execution, evolver mechanism, and agent startup modes.

---

## 1. Hook 改进

### 当前状态

| Hook | 文件 | 问题 |
|------|------|------|
| PostToolUse (`log_action.sh`) | 全量记录 tool calls | 不需要全量，只需记录 commitment 相关的；缺少 output 字段 |
| SessionStart (`check_violations.sh`) | 报告 violations 给各 role | 不需要——violations 是 evolver 的改进输出，不需要广播给业务 role |
| settings.local.json | 注册两个 hook | 需要精简 |

### 改进方案

**保留 1 个 hook：PostToolUse (commitment 数据采集)**

```
deploy.sh 生成:
  1. commitment_watch.yaml (per role, 从 commitment.yaml 提取)
  2. log_commitment.sh (PostToolUse hook, 读 commitment_watch.yaml)
  3. settings.local.json (只注册 PostToolUse)
```

**去掉 SessionStart hook。** violations 由 evolver 管理，不需要 hook 广播。

**PostToolUse hook 逻辑：**
```bash
# log_commitment.sh (替代 log_action.sh)
INPUT=$(cat)
TOOL_NAME=$(parse tool_name from INPUT)

# 读 commitment_watch.yaml
# 如果 TOOL_NAME 匹配某个 commitment 的 action → 记录
# 如果不匹配 → 跳过（不记录）
```

**commitment_watch.yaml 生成逻辑：**
```python
# deploy.sh 读 commitment.yaml
# 对每个 role，找出 from.action 或 to.action 与该 role 的 flow action 匹配的 commitment
# 生成 watch 列表
```

**输出格式** (.runtime/data/commitment_log/{role}.jsonl)：
```json
{"timestamp":"...","commitment":"C1","action":"review_code","role":"pm","tool":"Bash","input":{...},"output":{...}}
```

注意：这个 hook 对所有平台都有效——只要平台支持 PostToolUse hook 和 settings.local.json 格式。目前 Claude Code 支持。Codex/Kimi 需要确认是否支持相同的 hook 机制（如果不支持，这些平台的 commitment 数据只能通过 SDK wrapper 采集）。

### 需要实现

| 文件 | 操作 |
|------|------|
| `agent/deploy.sh` | 重写 hook 生成：去掉 SessionStart hook，PostToolUse 改为只记录 commitment 匹配的 tool calls。生成 commitment_watch.yaml |
| `agent/deploy.sh` | settings.local.json 只注册 PostToolUse |
| 测试 | 更新 test_deploy.py (去掉 SessionStart hook 测试)，更新 test_hooks.py (测试 commitment 匹配逻辑) |

---

## 2. Agent 启动模式改进

### 两种模式明确区分

| | TUI 模式 | SDK 模式 |
|---|---|---|
| **用途** | 开发调试 | 业务运行 |
| **启动方式** | `start.sh --role X` | `start_agent.py --role X` |
| **交互** | 人在终端里对话 | 程序调 API 发消息 |
| **对话保存** | hook 保存 commitment 相关 tool calls | Python wrapper 保存完整对话 |
| **谁用** | 开发者 | app 后端 / evolver 自动测试 |

### TUI 模式（保持现有）

`start.sh` → adapter shell.sh → `exec claude/codex/kimi`

配置加载：
- Claude: 自动读 .claude/ (skills + hooks + settings.local.json)
- Codex: `--cd` 进入 project dir，读 .codex/ 或类似配置（需确认）
- Kimi: `--work-dir` 进入 project dir（需确认 hook 支持）

### SDK 模式（需要重写）

当前 `launch_sdk()` 是空壳。需要参考 autoservice 实现真正的 SDK wrapper。

**Claude SDK adapter 重写：**
```python
class ClaudeAdapter(BaseAdapter):
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Launch via Claude Agent SDK with full conversation logging."""
        from claude_agent_sdk import query, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            cwd=str(self.config.project_dir),
            system_prompt=self.config.soul,
            setting_sources=["project", "local"],  # 加载 .claude/ 配置 (hooks + skills)
        )

        session_log = []
        async for message in query(prompt=prompt, options=options):
            session_log.append(message)
            yield message

        # 保存完整 session
        self._save_session(session_log)

    def _save_session(self, messages: list) -> None:
        """Save complete conversation to .runtime/data/sessions/"""
        sessions_dir = self.config.project_dir.parent.parent / "data" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        # 写入带时间戳的 session JSON
```

**关键：`setting_sources=["project", "local"]` 让 SDK 也加载 hooks——commitment 数据采集在两种模式下都工作。**

**Codex SDK adapter：**
```python
class CodexAdapter(BaseAdapter):
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        from agents import Agent, Runner
        agent = Agent(name=self.config.name, instructions=self.config.soul)
        # OpenAI Agents SDK 的对话机制
        # 需要确认是否支持 hook
```

**Kimi adapter：** 无独立 SDK，SDK 模式 fallback 到 shell。

### BaseAdapter 接口变更

```python
class BaseAdapter(abc.ABC):
    @abc.abstractmethod
    def launch_shell(self) -> None:
        """TUI mode — interactive, dev use."""
        ...

    @abc.abstractmethod
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """SDK mode — programmatic, with full conversation logging."""
        ...
```

`launch_sdk` 改为 async generator，返回消息流。调用方（start_agent.py 或 evolver）负责消费和保存。

### start.sh vs start_agent.py

```
start.sh        → TUI 模式（exec shell adapter）
start_agent.py  → SDK 模式（import SDK adapter）
Makefile:
  make start    → start.sh (TUI)
  make run      → start_agent.py (SDK)  ← 新增
```

### 需要实现

| 文件 | 操作 |
|------|------|
| `agent/adapters/base.py` | launch_sdk 改为 async generator + 加 _save_session |
| `agent/adapters/claude/sdk.py` | 参考 autoservice 重写，用 claude_agent_sdk，加 setting_sources |
| `agent/adapters/codex/sdk.py` | 确认 OpenAI Agents SDK 的对话机制，实现或标注 TODO |
| `agent/adapters/kimicode/sdk.py` | 无 SDK，保持 fallback |
| `src/start_agent.py` | 改为 async，消费 launch_sdk 的消息流，保存 session |
| `agent/Makefile.template` | 加 `run` target |

---

## 3. Evolver 完整功能

### 功能清单

每个功能对应一个 skill + 一个脚本。不存在的脚本标注为 TODO。

#### 3.1 evolve_check — 结构一致性检查（纯静态）

**Skill:** `agent/flow/evolve_check/SKILL.md`（新增）
**Script:** `agent/flow/evolve_check/scripts/check_structure.py`（新增）

```
输入: agent/ 目录 (flow.yaml + role/*.md + scope.md + commitment.yaml)
做什么:
  1. flow.yaml 每个 action → 检查 flow/{action}/SKILL.md 存在
  2. commitment.yaml 每个 commitment → 检查 from.role, to.role, on_violation.role 存在于 role/
  3. commitment.yaml 每个 commitment → 检查 from.action, to.action 存在于 flow.yaml
  4. scope.md 声明的能力 → 列出，供人工确认是否有对应的 flow action
输出: 结构检查报告 (text)
不需要: app 运行
```

#### 3.2 evolve_api_test — API 连通性测试

**Skill:** `agent/flow/evolve_eval/SKILL.md`（已有，合并功能）
**Script:** `agent/flow/evolve_eval/scripts/run_eval.py`（已有，api_checks 部分）

```
输入: eval_cases.yaml 的 api_checks + 运行中的 app
做什么:
  1. 读 eval_cases.yaml 的 api_checks
  2. 对每个 case: HTTP 调用 → 对比 expected_status / expected_body
  3. 报告 pass/fail
输出: API 测试报告 + 分数
需要: app 运行 (uvicorn)
```

#### 3.3 evolve_diagnose — 对话分析

**Skill:** `agent/flow/evolve_diagnose/SKILL.md`（已有，需重写）
**Script:** `agent/flow/evolve_diagnose/scripts/diagnose.py`（已有，需重写）

```
输入:
  .runtime/data/commitment_log/*.jsonl (hook 采集的 commitment 相关 tool calls)
  .runtime/data/sessions/*.json (SDK 完整对话, 如果有)
  agent/commitment/commitment.yaml
  .runtime/data/evolve_state.yaml (上次分析的 cursor)
做什么:
  1. 读 cursor → 只分析新数据
  2. 对每个 commitment:
     - 从 commitment_log 找 from.action 事件和 to.action 事件
     - 检查 condition 是否满足 (时间差 / 前置条件)
     - 计算履约率
  3. 从 sessions/ 分析完整对话 (如果有):
     - agent 选了对的 skill 吗？
     - 有没有 scope 外的请求？
     - 有没有失败的 tool call？
  4. 更新 cursor
输出:
  诊断报告 (text)
  .runtime/data/violations/ (违约记录, 如果发现)
  .runtime/data/evolve_state.yaml (更新 cursor)
```

#### 3.4 evolve_improve — 对话式改进

**Skill:** `agent/flow/evolve_improve/SKILL.md`（已有）
**Script:** 无（evolver agent 自身通过对话执行改进）

```
输入: diagnose 报告 + eval 分数
做什么 (evolver agent 在对话中执行):
  1. 读诊断报告
  2. 映射问题到四原语:
     低履约率 → 改 flow (加 skill) 或 改 commitment (调标准)
     缺 API → 建议开发者加 endpoint
     scope 外请求 → 改 scope
  3. 提出具体修改建议
  4. 开发者批准 → evolver 编辑 agent/ 文件 → deploy
```

#### 3.5 evolve_auto — 自动对话测试

**Skill:** `agent/flow/evolve_auto/SKILL.md`（已有，需重写）
**Script:** `agent/flow/evolve_auto/scripts/run_auto.py`（需重写）

```
输入:
  eval_cases.yaml 的 conversation_checks
  SDK adapter (用于程序化发消息给 agent)
做什么:
  1. 读 conversation_checks
  2. 对每个 case:
     a. 通过 SDK adapter 启动 agent (该 role)
     b. 发送 case.input
     c. 收集 agent 的完整 trace (tool calls + 回复)
     d. 检查: agent 选了 expected_skill 吗？结果匹配吗？
  3. 打分: pass/fail per case
  4. 失败的 trace → 分析原因 → 建议改进 (参考 EvoSkill proposer 模式)
输出:
  自动测试报告 (pass/fail + 分数)
  失败 trace 分析
  改进建议 (具体到哪个 SKILL.md 要改什么)
需要:
  app 运行 + SDK adapter 可用
  eval_cases.yaml 有 conversation_checks
```

### Evolver 使用流程

```
开发者完成一轮开发 (P2 加了 skills + API)
  ↓
make start ROLE=evolver
  ↓
"check structure"
  → 跑 check_structure.py
  → 报告: 所有引用完整吗？有 gap 吗？
  ↓
"evaluate" (需要 app 运行)
  → 跑 run_eval.py (api_checks)
  → 报告: API 连通性，分数
  ↓
"diagnose"
  → 跑 diagnose.py
  → 报告: commitment 履约率、对话问题、违约
  ↓
"improve"
  → evolver 读报告 → 提出修改建议 → 开发者批准
  ↓
"auto-test" (需要 app 运行 + SDK)
  → 跑 run_auto.py (conversation_checks)
  → 报告: agent 行为测试通过率
  → 失败的 → 分析 → 建议改 skill
```

### evolve_state.yaml 格式

```yaml
last_analysis:
  timestamp: "2026-03-24T10:00:00Z"
  commitment_log_cursor:
    default: { file: "default.jsonl", line: 142 }
    reviewer: { file: "reviewer.jsonl", line: 38 }
  sessions_cursor: "session_20260324_090000.json"
  results:
    fulfillment:
      C1: { fulfilled: 7, total: 10, rate: 0.7 }
      C2: { fulfilled: 19, total: 20, rate: 0.95 }
    api_score: 0.85
    auto_score: 0.6
```

### 需要实现

| 文件 | 操作 | 状态 |
|------|------|------|
| `agent/flow/evolve_check/SKILL.md` | 新增 | TODO |
| `agent/flow/evolve_check/scripts/check_structure.py` | 新增 | TODO |
| `agent/flow/evolve_diagnose/scripts/diagnose.py` | 重写: 加 commitment 履约率计算 + cursor | TODO |
| `agent/flow/evolve_auto/scripts/run_auto.py` | 重写: SDK 自动对话 + trace 收集 | TODO |
| `agent/flow/evolve_eval/scripts/run_eval.py` | 保持: api_checks 部分已可用 | 已完成 |
| `agent/flow/evolve_improve/SKILL.md` | 保持: 对话式改进 | 已完成 |
| `agent/flow/flow.yaml` | 加 evolve_check action | TODO |

---

## 4. 跨平台兼容性

| 功能 | Claude Code | Codex | Kimi Code |
|------|-------------|-------|-----------|
| TUI 启动 | ✅ shell.sh | ✅ shell.sh | ✅ shell.sh |
| SDK 启动 | ✅ claude_agent_sdk | ⚠️ openai-agents (需确认) | ❌ 无 SDK |
| PostToolUse hook | ✅ settings.local.json | ❓ 需确认机制 | ❓ 需确认机制 |
| skills 加载 | ✅ .claude/skills/ | ❓ .codex/skills? | ❓ 需确认 |
| SOUL.md 注入 | ✅ --append-system-prompt-file | ❓ 需确认 | ❓ 需确认 |

**对于不支持 hook 的平台：** commitment 数据只能通过 SDK wrapper 采集（SDK wrapper 在 Python 层面记录，不依赖平台 hook）。

---

## 5. 执行顺序

```
Phase 1: Hook 改进
  - 重写 deploy.sh 的 hook 生成 (去掉 SessionStart，PostToolUse 改为 commitment 匹配)
  - 更新测试

Phase 2: SDK 模式
  - 重写 claude/sdk.py (参考 autoservice)
  - 更新 base.py 接口
  - 更新 start_agent.py

Phase 3: Evolver 功能
  - 新增 evolve_check (结构检查)
  - 重写 diagnose.py (commitment 履约率 + cursor)
  - 重写 run_auto.py (SDK 自动对话)

Phase 4: 文档
  - 更新所有 guides
  - 写 docs/discuss/evolver.md
```
