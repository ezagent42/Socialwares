# Evolve V3 — Hook + Deploy + SDK + Evolver Improvement Plan

> Based on discussions about commitment execution, evolver mechanism, agent startup modes, and cross-platform compatibility.

---

## 0. 三平台配置对照（已查实）

| 配置项 | Claude Code | Codex CLI | Kimi Code |
|--------|-------------|-----------|-----------|
| **Skills 目录** | `.claude/skills/` | `.agents/skills/` | `.agents/skills/` (首选) 或 `.claude/skills/` |
| **System prompt 文件** | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` |
| **System prompt 注入** | `--append-system-prompt-file` | 自动读 `AGENTS.md` | 自动读 `AGENTS.md` |
| **Hook 配置文件** | `.claude/settings.local.json` | `.codex/hooks.json` | ❌ 无 |
| **Hook 格式** | `{ "hooks": { ... } }` | `{ "hooks": { ... } }` (几乎一致) | — |
| **Hook feature gate** | 默认启用 | 需 `config.toml` 加 `codex_hooks = true` | — |
| **项目配置** | `.claude/settings.json` (JSON) | `.codex/config.toml` (TOML) | 无项目级配置 |
| **SDK** | `claude_agent_sdk` | `openai-agents` (内置 tracing) | ❌ 无 |
| **支持的 Hook 类型** | SessionStart, PreToolUse, PostToolUse, UserPromptSubmit | SessionStart, PreToolUse, UserPromptSubmit, Stop | — |

---

## 1. deploy.sh 改进 — 按 adapter 生成配置

### 当前问题

deploy.sh 硬编码 `.claude/` 目录。只对 Claude Code 有效。

### 改进方案

deploy.sh 接收 `--adapter` 参数，根据平台生成不同的目录结构和配置。

```bash
./agent/deploy.sh                    # 默认 claude
./agent/deploy.sh --adapter codex
./agent/deploy.sh --adapter kimi
```

### 每个 adapter 生成什么

**Claude Code (`--adapter claude`):**
```
.runtime/agents/{role}/
├── .claude/
│   ├── skills/{action}/  → symlink to agent/flow/{action}/
│   ├── hooks/
│   │   ├── log_prompt.sh    (UserPromptSubmit)
│   │   └── log_tool.sh      (PreToolUse)
│   └── settings.local.json  (注册 hooks)
├── SOUL.md                  (merged scope + role)
├── .workspace_root
├── commitment.yaml
└── flow.yaml
```

**Codex CLI (`--adapter codex`):**
```
.runtime/agents/{role}/
├── .agents/
│   └── skills/{action}/  → symlink to agent/flow/{action}/
├── .codex/
│   ├── hooks.json           (注册 hooks，格式同 Claude 但文件不同)
│   └── config.toml          (加 codex_hooks = true)
├── AGENTS.md                (从 SOUL.md 复制，改名)
├── .workspace_root
├── commitment.yaml
└── flow.yaml
```

**Kimi Code (`--adapter kimi`):**
```
.runtime/agents/{role}/
├── .agents/
│   └── skills/{action}/  → symlink to agent/flow/{action}/
├── AGENTS.md                (从 SOUL.md 复制，改名)
├── .workspace_root
├── commitment.yaml
└── flow.yaml
# 无 hooks（Kimi 不支持）
```

### deploy.sh 内部结构

```bash
# 通用部分（所有 adapter 都做的）
merge_soul()          # scope.md + role.md → SOUL.md/AGENTS.md
copy_commitment()     # commitment.yaml
copy_flow_yaml()      # flow.yaml
write_workspace_root() # .workspace_root
link_skills()         # symlink skills（目标目录由 adapter 决定）

# adapter 专有部分
case "$ADAPTER" in
  claude)
    SKILLS_DIR=".claude/skills"
    PROMPT_FILE="SOUL.md"
    generate_claude_hooks()    # settings.local.json + hook scripts
    ;;
  codex)
    SKILLS_DIR=".agents/skills"
    PROMPT_FILE="AGENTS.md"
    generate_codex_hooks()     # .codex/hooks.json + .codex/config.toml + hook scripts
    ;;
  kimi)
    SKILLS_DIR=".agents/skills"
    PROMPT_FILE="AGENTS.md"
    # 无 hooks
    ;;
esac
```

### Hook 生成（Claude 和 Codex 共用脚本，不同注册方式）

**两个 hook 脚本是一样的**（平台无关的 bash 脚本）：

`log_prompt.sh` (UserPromptSubmit):
```bash
#!/usr/bin/env bash
# 收到 stdin: { "prompt": "用户输入", "session_id": "...", "cwd": "..." }
INPUT=$(cat)
# 提取 prompt，写入 JSONL
python3 -c "
import json, sys
from datetime import datetime, timezone
data = json.loads(sys.stdin.read())
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'user_prompt',
    'content': data.get('prompt', ''),
    'session_id': data.get('session_id', ''),
}
# 写入 .runtime/data/prompts/
..." <<< "$INPUT"
```

`log_tool.sh` (PreToolUse):
```bash
#!/usr/bin/env bash
# 收到 stdin: { "tool_name": "Bash", "tool_input": {...}, "session_id": "..." }
INPUT=$(cat)
python3 -c "
import json, sys
from datetime import datetime, timezone
data = json.loads(sys.stdin.read())
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'tool_call',
    'tool': data.get('tool_name', ''),
    'input': data.get('tool_input', {}),
    'session_id': data.get('session_id', ''),
}
..." <<< "$INPUT"
```

**注册方式不同：**

Claude — `.claude/settings.local.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "/path/log_prompt.sh" }] }],
    "PreToolUse": [{ "hooks": [{ "type": "command", "command": "/path/log_tool.sh" }] }]
  }
}
```

Codex — `.codex/hooks.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "/path/log_prompt.sh" }] }],
    "PreToolUse": [{ "hooks": [{ "type": "command", "command": "/path/log_tool.sh" }] }]
  }
}
```

Codex 还需要 `.codex/config.toml`:
```toml
[features]
codex_hooks = true
```

### Makefile.template 更新

```makefile
# 默认 adapter
ADAPTER ?= claude

deploy: $(STAMP)

$(STAMP): $(SOURCES)
	./$(AGENT_DIR)/deploy.sh --adapter $(ADAPTER)
	@mkdir -p $(RUNTIME)
	@touch $@

start: deploy
	./$(AGENT_DIR)/start.sh --role $(or $(ROLE),default) --adapter $(ADAPTER)

run: deploy  ## SDK mode: make run ROLE=default
	uv run src/start_agent.py --role $(or $(ROLE),default) --adapter $(ADAPTER)
```

### 需要实现

| 文件 | 操作 |
|------|------|
| `agent/deploy.sh` | 重写：加 --adapter 参数，按平台生成不同目录/配置 |
| `agent/Makefile.template` | 加 ADAPTER 变量 + run target |
| `agent/start.sh` | 已有 --adapter 支持，保持 |
| 测试 | 更新 test_deploy.py（测试不同 adapter 输出） |

---

## 2. Agent 启动模式

### 两种模式

| | TUI 模式 | SDK 模式 |
|---|---|---|
| **用途** | 开发调试 | 业务运行 / evolver 自动测试 |
| **启动** | `make start` → start.sh → shell adapter | `make run` → start_agent.py → SDK adapter |
| **交互** | 人在终端对话 | 程序发消息、收回复 |
| **数据采集** | hooks (Claude/Codex) 或 无 (Kimi) | Python wrapper 保存完整对话 |

### TUI 模式 — shell adapter

```
start.sh --role X --adapter Y → agent/adapters/Y/shell.sh
```

| adapter | 命令 | prompt 注入 |
|---------|------|-----------|
| claude | `claude --dangerously-skip-permissions --append-system-prompt-file SOUL.md` | SOUL.md (CLI flag) |
| codex | `codex --cd $dir --full-auto` | 自动读 AGENTS.md |
| kimi | `kimi --work-dir $dir --yolo` | 自动读 AGENTS.md |

shell adapter 不需要大改——只是 deploy 生成的目录/文件名不同。

### SDK 模式 — Python adapter

```
start_agent.py --role X --adapter Y → agent/adapters/Y/sdk.py
```

**Claude SDK adapter:**
```python
class ClaudeAdapter(BaseAdapter):
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        from claude_agent_sdk import query, ClaudeAgentOptions
        options = ClaudeAgentOptions(
            cwd=str(self.config.project_dir),
            system_prompt=self.config.soul,
            setting_sources=["project", "local"],  # 加载 .claude/ (hooks + skills)
        )
        async for message in query(prompt=prompt, options=options):
            yield message
```

**Codex SDK adapter:**
```python
class CodexAdapter(BaseAdapter):
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        from agents import Agent, Runner
        agent = Agent(
            name=self.config.name,
            instructions=self.config.soul,
        )
        # OpenAI Agents SDK 内置 tracing，自动记录到 OpenAI dashboard
        # 本地保存需要 add_trace_processor()
        result = await Runner.run(agent, prompt)
        yield result
```

**Kimi adapter:**
```python
class KimiCodeAdapter(BaseAdapter):
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        raise NotImplementedError(
            "Kimi Code has no SDK. Use TUI mode (make start)."
        )
```

### BaseAdapter 接口

```python
class BaseAdapter(abc.ABC):
    def __init__(self, config: RoleConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def launch_shell(self) -> None:
        """TUI mode — interactive terminal."""

    @abc.abstractmethod
    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """SDK mode — programmatic, yields messages."""
```

### 对话保存

SDK wrapper（在 `start_agent.py` 层面）保存完整 session：

```
.runtime/data/sessions/
└── {role}_session_{YYYYMMDD_HHMMSS}.json
```

```json
{
  "session_id": "session_20260324_120000",
  "role": "default",
  "adapter": "claude",
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
| `agent/adapters/base.py` | launch_sdk 改为 async generator |
| `agent/adapters/claude/sdk.py` | 重写：用 claude_agent_sdk + setting_sources |
| `agent/adapters/claude/shell.sh` | 保持（deploy 已生成正确的 SOUL.md） |
| `agent/adapters/codex/sdk.py` | 重写：用 openai-agents + tracing |
| `agent/adapters/codex/shell.sh` | 保持（deploy 已生成正确的 AGENTS.md） |
| `agent/adapters/kimicode/sdk.py` | 标注 NotImplementedError |
| `agent/adapters/kimicode/shell.sh` | 保持（deploy 已生成正确的 AGENTS.md） |
| `src/start_agent.py` | 改为 async + 保存 session JSON |
| `agent/Makefile.template` | 加 `ADAPTER` 变量 + `run` target |

---

## 3. Evolver 完整功能

### 数据来源

| 来源 | 由谁产生 | 格式 | 位置 | 平台支持 |
|------|---------|------|------|---------|
| Hook 日志 | TUI 的 hook | JSONL (prompt + tool) | `.runtime/data/prompts/{role}.jsonl` | Claude ✅ Codex ✅ Kimi ❌ |
| SDK 完整对话 | SDK wrapper | JSON (full session) | `.runtime/data/sessions/*.json` | Claude ✅ Codex ✅ Kimi ❌ |
| 自动测试 trace | evolve_auto 的 SDK | JSON (test traces) | `.runtime/data/auto_tests/*.json` | Claude ✅ Codex ✅ Kimi ❌ |

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
  3. 分析完整对话 (如有): scope 外请求？失败的操作？
  4. 更新 cursor + 写 violations
输出:
  诊断报告 (stdout)
  .runtime/data/violations/*.jsonl
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
  SDK adapter (通过 start_agent.py 调用)
需要: app 运行 + SDK 可用
做什么:
  1. 对每个 conversation_check:
     a. SDK 启动 agent (指定 role)
     b. 发送 input
     c. 收集 trace
     d. 检查: 选了 expected_skill？结果正确？
  2. 打分
  3. 失败 trace → 分析原因 → 建议改进
输出:
  自动测试报告
  .runtime/data/auto_tests/*.json (traces)
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
| TUI 启动 | ✅ `claude` | ✅ `codex` | ✅ `kimi` |
| SDK 启动 | ✅ `claude_agent_sdk` | ✅ `openai-agents` | ❌ 无 SDK |
| Skills 目录 | `.claude/skills/` | `.agents/skills/` | `.agents/skills/` |
| Prompt 文件 | `SOUL.md` (CLI flag) | `AGENTS.md` (自动读) | `AGENTS.md` (自动读) |
| Hook 配置 | `.claude/settings.local.json` | `.codex/hooks.json` + `config.toml` | ❌ 无 |
| Hook: UserPromptSubmit | ✅ | ✅ (需 feature gate) | ❌ |
| Hook: PreToolUse | ✅ | ✅ (需 feature gate) | ❌ |
| **TUI 数据采集** | ✅ 两个 hook | ✅ 两个 hook | ❌ 不支持 |
| **SDK 数据采集** | ✅ wrapper | ✅ 内置 tracing | ❌ 不支持 |
| **Commitment 评估** | ✅ | ✅ | ❌ 无数据来源 |

**Kimi Code 限制：** 无 hook、无 SDK、无项目级配置。TUI 模式下只有 skills 和 AGENTS.md 工作。Commitment 评估不可用。

---

## 5. 执行顺序

```
Phase 1: deploy.sh 重写
  - 加 --adapter 参数
  - 按平台生成不同目录 (.claude/ vs .agents/ vs .codex/)
  - 按平台生成 hook 注册 (settings.local.json vs hooks.json vs 无)
  - SOUL.md vs AGENTS.md 根据平台选择
  - 更新 Makefile.template (ADAPTER 变量)

Phase 2: SDK adapter 重写
  - claude/sdk.py (claude_agent_sdk + setting_sources)
  - codex/sdk.py (openai-agents + tracing)
  - kimi/sdk.py (NotImplementedError)
  - base.py (async generator 接口)
  - start_agent.py (async + session 保存)

Phase 3: Evolver 功能
  - 新增 evolve_check (结构检查)
  - 重写 diagnose.py (履约率 + cursor)
  - 重写 run_auto.py (SDK 自动对话)

Phase 4: 文档
  - 更新所有 guides + READMEs
  - 明确标注各平台限制
```
