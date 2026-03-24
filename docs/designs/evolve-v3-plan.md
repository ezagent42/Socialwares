# Evolve V3 — Hook + SDK + Evolver Improvement Plan

> Based on discussions about commitment execution, evolver mechanism, and agent startup modes.

---

## 1. Hook 改进

### 设计原则

- Hook 用于 TUI 模式的数据采集（commitment 评估数据）
- 只使用跨平台通用的 hook 类型
- SDK 模式不依赖 hook（Python wrapper 自己记录）

### 跨平台 Hook 兼容性（已查实）

| Hook | Claude Code | Codex CLI | Kimi Code | 收到什么 |
|------|-------------|-----------|-----------|---------|
| **UserPromptSubmit** | ✅ | ✅ | ❌ | `{ prompt }` — 用户输入文本 |
| **PreToolUse** | ✅ | ✅ | ❌ | `{ tool_name, tool_input }` — 工具调用 |
| PostToolUse | ✅ | ❌ | ❌ | `{ tool_name, tool_input, tool_response }` |
| SessionStart | ✅ | ✅ | ❌ | `{ session_id, cwd }` |

**选择 UserPromptSubmit + PreToolUse**（Claude + Codex 通用）。不用 PostToolUse（Codex 不支持）。

**Kimi 不支持任何 hook** — TUI 模式无法自动采集数据。Kimi 用户只能通过 SDK 模式（如果有）或手动导出对话。需在文档中明确标注。

### 两个 Hook 的职责

**UserPromptSubmit — 记录用户意图**
```bash
# log_prompt.sh
# 收到: { "prompt": "submit my code for review" }
# 写入: .runtime/data/prompts/{role}.jsonl
{"timestamp":"2026-03-24T10:00:00Z","role":"coder","type":"user_prompt","content":"submit my code for review"}
```

**PreToolUse — 记录工具调用**
```bash
# log_tool.sh
# 收到: { "tool_name": "Bash", "tool_input": {"command": "curl -X POST /tasks/submit"} }
# 写入: .runtime/data/prompts/{role}.jsonl (追加到同一文件)
{"timestamp":"2026-03-24T10:00:05Z","role":"coder","type":"tool_call","tool":"Bash","input":{"command":"curl -X POST /tasks/submit"}}
```

两个 hook 写入同一个 JSONL 文件，按时间序排列：

```jsonl
{"timestamp":"...","role":"coder","type":"user_prompt","content":"submit my code for review"}
{"timestamp":"...","role":"coder","type":"tool_call","tool":"Bash","input":{"command":"curl -X POST /tasks/submit"}}
{"timestamp":"...","role":"pm","type":"user_prompt","content":"review the submitted code"}
{"timestamp":"...","role":"pm","type":"tool_call","tool":"Bash","input":{"command":"curl -X POST /tasks/review"}}
```

Evolver 读这个文件 → LLM 匹配 commitment 的 from/to action → 计算履约率。不需要 commitment_watch.yaml（LLM 直接从自然语言匹配）。

### 当前 → 改进

| 当前 | 改进 |
|------|------|
| PostToolUse: log_action.sh (全量记录) | **替换为** PreToolUse: log_tool.sh |
| SessionStart: check_violations.sh | **删除**（violations 由 evolver 管理，不需要 hook 广播） |
| 无 UserPromptSubmit | **新增** UserPromptSubmit: log_prompt.sh |
| settings.local.json 注册 2 个 hook | **改为** 注册 UserPromptSubmit + PreToolUse |

### deploy.sh 生成内容

```
每个 role 的 .runtime/agents/{role}/:
  .claude/hooks/log_prompt.sh        ← UserPromptSubmit hook
  .claude/hooks/log_tool.sh          ← PreToolUse hook
  .claude/settings.local.json        ← 注册这两个 hook
```

不再生成 commitment_watch.yaml（不需要）。

### 需要实现

| 文件 | 操作 |
|------|------|
| `agent/deploy.sh` | 重写 hook 生成：log_prompt.sh + log_tool.sh，去掉 check_violations.sh |
| `agent/deploy.sh` | settings.local.json 改为注册 UserPromptSubmit + PreToolUse |
| 测试 | 重写 test_hooks.py（测试新 hook），更新 test_deploy.py |

---

## 2. Agent 启动模式

### 两种模式

| | TUI 模式 | SDK 模式 |
|---|---|---|
| **用途** | 开发调试 | 业务运行 / evolver 自动测试 |
| **启动** | `make start ROLE=X` → start.sh → shell adapter | `make run ROLE=X` → start_agent.py → SDK adapter |
| **交互** | 人在终端对话 | 程序发消息、收回复 |
| **数据采集** | hook (UserPromptSubmit + PreToolUse) | Python wrapper 保存完整对话 |
| **配置加载** | 自动读 .claude/ | 需要 `setting_sources=["project","local"]` |

### TUI 模式（保持现有 + 更新 hook）

```
start.sh → adapter/shell.sh → exec claude/codex/kimi
```

- Claude/Codex: hooks 自动工作，采集 prompt + tool 数据
- Kimi: 无 hook，TUI 不采集数据（文档标注）

### SDK 模式（需要重写 adapter）

参考 autoservice 实现。SDK wrapper 完整记录对话。

**Claude SDK adapter:**
```python
async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
    from claude_agent_sdk import query, ClaudeAgentOptions
    options = ClaudeAgentOptions(
        cwd=str(self.config.project_dir),
        system_prompt=self.config.soul,
        setting_sources=["project", "local"],  # hooks + skills 都加载
    )
    async for message in query(prompt=prompt, options=options):
        yield message
```

**Codex SDK adapter:**
```python
async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
    from agents import Agent, Runner
    agent = Agent(name=self.config.name, instructions=self.config.soul)
    result = await Runner.run(agent, prompt)
    # OpenAI Agents SDK 内置 tracing，自动记录
    yield result
```

**Kimi adapter:**
```python
async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
    raise NotImplementedError("Kimi Code has no SDK. Use TUI mode.")
```

### Skill 目录兼容性（已查实）

| 平台 | Skill 目录 |
|------|-----------|
| Claude Code | `.claude/skills/` |
| Codex CLI | `.agents/skills/` |
| Kimi Code | `.agents/skills/` 或 `.claude/skills/` |

deploy.sh 当前生成到 `.claude/skills/`。对于 Codex/Kimi 需要同时生成到 `.agents/skills/`（或用 symlink）。

### BaseAdapter 接口变更

```python
class BaseAdapter(abc.ABC):
    @abc.abstractmethod
    def launch_shell(self) -> None:
        """TUI mode — interactive, dev use."""

    @abc.abstractmethod
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """SDK mode — programmatic, full conversation capture."""
```

### 对话保存

SDK 模式保存完整 session 到 `.runtime/data/sessions/`:
```json
{
  "session_id": "session_20260324_120000",
  "role": "default",
  "started_at": "2026-03-24T12:00:00Z",
  "messages": [
    {"role": "user", "content": "submit my code"},
    {"role": "assistant", "content": "Submitting...", "tool_calls": [...]},
    {"role": "tool", "content": "200 OK"}
  ]
}
```

### 需要实现

| 文件 | 操作 |
|------|------|
| `agent/adapters/base.py` | launch_sdk 改为 async generator + 加 save_session |
| `agent/adapters/claude/sdk.py` | 重写：用 claude_agent_sdk，加 setting_sources |
| `agent/adapters/codex/sdk.py` | 重写：用 openai-agents，内置 tracing |
| `agent/adapters/kimicode/sdk.py` | 标注 NotImplementedError |
| `src/start_agent.py` | 改为 async，消费 launch_sdk |
| `agent/Makefile.template` | 加 `run` target (SDK 模式) |
| `agent/deploy.sh` | 为 Codex/Kimi 同时生成 .agents/skills/ |

---

## 3. Evolver 完整功能

### 数据来源

| 来源 | 由谁产生 | 格式 | 位置 |
|------|---------|------|------|
| Hook 日志 | TUI 模式的 hook | JSONL (prompt + tool) | `.runtime/data/prompts/{role}.jsonl` |
| SDK 完整对话 | SDK 模式的 wrapper | JSON (full session) | `.runtime/data/sessions/*.json` |
| Evolver 自动测试 | evolve_auto 通过 SDK | JSON (test traces) | `.runtime/data/auto_tests/*.json` |

### 功能清单

#### 3.1 evolve_check — 结构一致性检查

**Skill:** `agent/flow/evolve_check/SKILL.md`（新增）
**Script:** `agent/flow/evolve_check/scripts/check_structure.py`（新增）

```
输入: agent/ 目录
不需要: app 运行
做什么:
  1. flow.yaml 每个 action → SKILL.md 存在？
  2. commitment.yaml 每个 from/to 的 role → role/*.md 存在？
  3. commitment.yaml 每个 from/to 的 action → flow.yaml 存在？
  4. scope.md 声明的能力 → 列出供人工确认
输出: 结构检查报告 (stdout)
```

#### 3.2 evolve_eval — API 连通性测试

**Skill:** `agent/flow/evolve_eval/SKILL.md`（已有）
**Script:** `agent/flow/evolve_eval/scripts/run_eval.py`（已有）

```
输入: eval_cases.yaml 的 api_checks
需要: app 运行
做什么: HTTP 调用 → 对比 expected → 报告 pass/fail
输出: API 测试报告 + 分数
```

#### 3.3 evolve_diagnose — 对话分析 + 履约率

**Skill:** `agent/flow/evolve_diagnose/SKILL.md`（已有，需重写）
**Script:** `agent/flow/evolve_diagnose/scripts/diagnose.py`（已有，需重写）

```
输入:
  .runtime/data/prompts/*.jsonl (hook 数据)
  .runtime/data/sessions/*.json (SDK 完整对话)
  agent/commitment/commitment.yaml
  .runtime/data/evolve_state.yaml (cursor)
做什么:
  1. 读 cursor → 只分析新数据
  2. 对每个 commitment: 从数据中匹配 from/to action → 计算履约率
  3. 分析完整对话: scope 外请求？失败的操作？
  4. 更新 cursor + 写 violations
输出:
  诊断报告 (stdout)
  .runtime/data/violations/*.jsonl (如发现违约)
  .runtime/data/evolve_state.yaml (更新 cursor)
```

#### 3.4 evolve_improve — 对话式改进

**Skill:** `agent/flow/evolve_improve/SKILL.md`（已有）
**Script:** 无（evolver agent 自身执行）

```
输入: diagnose 报告 + eval 分数
做什么: evolver 在对话中提出改进建议 → 开发者批准 → 编辑文件 → deploy
```

#### 3.5 evolve_auto — 自动对话测试

**Skill:** `agent/flow/evolve_auto/SKILL.md`（已有，需重写）
**Script:** `agent/flow/evolve_auto/scripts/run_auto.py`（需重写）

```
输入:
  eval_cases.yaml 的 conversation_checks
  SDK adapter
需要: app 运行 + SDK 可用
做什么:
  1. 对每个 conversation_check:
     a. SDK 启动 agent
     b. 发送 input
     c. 收集 trace (tool calls + 回复)
     d. 检查: 选了 expected_skill？结果正确？
  2. 打分
  3. 失败 trace → 分析原因 → 建议改进
输出:
  自动测试报告
  .runtime/data/auto_tests/*.json (traces)
```

### Evolver 使用时机

```
开发完一轮 (P2 加了 skills + API)
  → "check structure" (纯静态)
  → "evaluate" (API 测试，需 app 运行)

运行一段时间后 (有 hook/SDK 数据)
  → "diagnose" (分析对话 + 履约率)
  → "improve" (根据诊断改进)

主动改进 (有 eval_cases + SDK)
  → "auto-test" (自动对话测试)
```

### evolve_state.yaml

```yaml
last_analysis:
  timestamp: "2026-03-24T10:00:00Z"
  prompts_cursor:
    coder: { file: "coder.jsonl", line: 142 }
    pm: { file: "pm.jsonl", line: 38 }
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
| `agent/flow/evolve_diagnose/scripts/diagnose.py` | 重写 | TODO |
| `agent/flow/evolve_auto/scripts/run_auto.py` | 重写 | TODO |
| `agent/flow/flow.yaml` | 加 evolve_check | TODO |

---

## 4. 平台兼容性总结

| 功能 | Claude Code | Codex CLI | Kimi Code |
|------|-------------|-----------|-----------|
| TUI 启动 | ✅ | ✅ | ✅ |
| SDK 启动 | ✅ claude_agent_sdk | ✅ openai-agents | ❌ 无 SDK |
| Hook (UserPromptSubmit) | ✅ | ✅ | ❌ |
| Hook (PreToolUse) | ✅ | ✅ | ❌ |
| Skills 目录 | .claude/skills/ | .agents/skills/ | .agents/skills/ 或 .claude/skills/ |
| **TUI 数据采集** | ✅ 两个 hook | ✅ 两个 hook | ❌ 不支持 |
| **SDK 数据采集** | ✅ wrapper | ✅ 内置 tracing | ❌ 不支持 |
| **Commitment 评估** | ✅ | ✅ | ❌ 无数据来源 |

**Kimi Code 限制：** 无 hook、无 SDK，TUI 模式下无法自动采集数据。Commitment 评估不可用。如需 commitment 功能，建议使用 Claude Code 或 Codex。

---

## 5. 执行顺序

```
Phase 1: Hook 改进
  - deploy.sh: 替换为 log_prompt.sh + log_tool.sh
  - 删除 check_violations.sh + SessionStart 注册
  - 更新测试

Phase 2: SDK 模式
  - 重写 adapters (claude/codex/kimi)
  - 更新 base.py + start_agent.py
  - 对话保存到 .runtime/data/sessions/

Phase 3: Evolver 功能
  - 新增 evolve_check
  - 重写 diagnose.py (履约率 + cursor)
  - 重写 run_auto.py (SDK 自动对话)

Phase 4: deploy.sh 跨平台
  - 为 Codex/Kimi 生成 .agents/skills/ (除 .claude/skills/ 外)

Phase 5: 文档
  - 更新所有 guides + READMEs
  - 明确标注 Kimi 限制
```
