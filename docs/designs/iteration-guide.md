# Socialware 迭代指南

> 基于四原语的渐进生长实操手册 + Agent SDK 接入方案

---

## 目录

### Part I — 迭代策略

- [一、迭代总览：两阶段策略](#一迭代总览两阶段策略)
- [二、0→1 阶段：P1→P5 迭代执行](#二01-阶段p1p5-迭代执行)
- [三、>1 阶段：稳定 + 自动迭代](#三1-阶段稳定--自动迭代)

### Part II — 迭代执行

- [四、迭代决策：改 Skill 还是改原语？](#四迭代决策改-skill-还是改原语)
- [五、测试与迭代的关系](#五测试与迭代的关系)
- [六、迭代可观测性](#六迭代可观测性)
- [七、迭代 Checklist](#七迭代-checklist)

### Part III — Agent 接入与自治

- [八、Agent SDK Web 接入方案（通用模板）](#八agent-sdk-web-接入方案通用模板)
- [九、Agent 自迭代与渐进自治](#九agent-自迭代与渐进自治)

---

# Part I — 迭代策略

## 一、迭代总览：两阶段策略

```
0→1 (P1→P5)                           >1 (P0 回环 + Evolve)
┌──────────────────────────┐          ┌──────────────────────────┐
│ 优先改进四原语的"形"      │          │ 四原语的"形"冻结          │
│ (schema/格式/约定)        │          │ 改进发生在"内容"层        │
│                          │          │                          │
│ 驱动力：开发者手动迭代    │          │ 驱动力：Evolve Skill 自动 │
│ 反馈源：开发者体验        │          │ 反馈源：Commitment 指标   │
└──────────────────────────┘          └──────────────────────────┘
```

---

## 二、0→1 阶段：P1→P5 迭代执行

### 优先级

```
1. Flow — 最高优先     能力从 0 到有的核心驱动力
2. Scope — 随 Flow 同步  每新增能力，边界随之扩展
3. Role — 按需延后      初期一个 default 角色够用
4. Commitment — 最后补   没有真实负载，指标无意义
```

### P2 是迭代最密集的阶段

每一轮迭代只需三步：

```
① 写 SKILL.md          ← 5 min（复制模板，改 Trigger/Flow/API）
② 写 API endpoint      ← 10 min（src/app.py 加一个路由）
③ 注册 flow.yaml + deploy  ← 1 min
```

迭代信号来自用户对话：Agent 说"我不会" → 就是一个迭代触发点。

### P3 的触发点

P3 不是 Dev 主动发起，而是用户感知到了不满：

```
用户: "我三天前提交的任务还没人 review！"
  → Commitment 指标 C1 的需求来源
  → Dev 写 eval.yaml + remind_review Skill + /metrics endpoint
```

### P4/P5 是批量操作

- P4 扩大 Scope：一口气加 3-5 个新 Capabilities
- P5 增加 Role：从 default 里分裂出 reviewer/admin，flow.yaml 重新分配权限

### 0→1 阶段可改进的原语"形"

| 改进点 | 说明 |
|--------|------|
| SKILL.md schema | frontmatter 是否需要 `input_schema`、`error_handling` 等字段？ |
| flow.yaml 状态机表达力 | transitions 是否需要 guards、side-effects？ |
| deploy.sh 合并策略 | Scope + Role 合并是否需要冲突检测？ |
| eval.yaml 执行绑定 | 声明式定义如何绑定到 Biz 层（cron? middleware?） |

---

## 三、>1 阶段：稳定 + 自动迭代

### 优先级倒转

```
1. Commitment — 最高优先   有真实用户了，指标是生命线
2. Scope — 稳定边界       避免 scope creep，对外承诺不随意变
3. Flow — 稳定注册        新 Skill 走标准流程，格式不变
4. Role — 最小权限原则     新角色必须有明确边界
```

### 自动迭代引擎：Evolve Skill

```
eval.yaml 指标 → Biz 层实现评估 → /metrics API → Evolve Skill 分析 → 改进四原语内容
```

- 主库 evolve：分析所有 workspace Eval Metrics → 改进四原语内容 → 提交 main → 所有租户受益
- 租户 evolve：特定适配（改 .runtime/，不触发 PR）或通用改进（改 worktree，自动 PR）

> **注意**：Evolve 能改进的范围随自治等级逐步扩大（详见[第九章](#九agent-自迭代与渐进自治)）。初期（L1）仅限优化已有 Skill 内容，不能新增 Skill 或 API。

---

# Part II — 迭代执行

## 四、迭代决策：改 Skill 还是改原语？

### 核心矛盾

```
需求来了 → 改 Skill 还是改原语？

改 Skill:  在现有边界内解决问题（快，安全，局部）
改原语:    重新定义边界本身（慢，有风险，全局影响）
```

需求不会告诉你它属于哪一层。一个看似"加个功能"的需求，可能本质上是 Scope 边界不合理；一个看似"改 Scope"的冲动，可能只是 Skill 写得不好。

### 四层诊断流程

遇到需求变化时，按此顺序排查：

```
需求进来
    │
    ▼
① Skill 层能解决吗？（改执行策略）
    │ 不能 ↓
② Flow 层能解决吗？（改动作注册/状态机）
    │ 不能 ↓
③ Scope/Commitment 需要调整吗？（改边界/标准）
    │ 不能 ↓
④ Role 需要调整吗？（改组织结构）
```

#### ① 先看 Skill（最低成本）

```
信号：Agent 有这个能力，但执行得不好
判断：API endpoint 已存在，Skill 的 Trigger/Flow 描述需要优化

例：用户说"帮我查任务"，Agent 查了但返回格式乱
    → 改 query_task/SKILL.md 的 Flow 步骤，加格式化要求
    → 不需要动任何原语
```

#### ② 再看 Flow（中等成本）

```
信号：需要新的 Action，或现有状态机流转不对
判断：需要新建 SKILL.md + API endpoint，或修改 flow.yaml 的 transitions/权限

例1：用户说"帮我发邮件"，Agent 说"我不会"
     → 新增 send_email Skill + API → 注册 flow.yaml
     → Scope 的 Capabilities 同步更新（这是跟随更新，不是"改 Scope"）

例2：任务从 rejected 状态无法重新提交
     → flow.yaml 加 transition: { from: rejected, action: resubmit, to: submitted }
     → 状态机变了，但 Scope 边界没变
```

#### ③ 然后看 Scope/Commitment（需要慎重）

```
信号：出现"边界冲突"——需求合理但被当前边界拒绝，或边界太松导致 Agent 越界

判断方式——问自己两个问题：
  Q1: 这个需求是"App 本来就该做的事"还是"超出 App 定位的事"？
  Q2: 如果改了 Scope，对外公示（/zchat 其他 App 读取）会不会产生误解？
```

#### ④ 最后看 Role（最高成本）

```
信号：同一个 Agent 承担了互相冲突的职责
判断：一个角色既要"提交任务"又要"审核任务" → 需要分裂

例：default 角色又提交又审核，利益冲突
    → 分裂出 reviewer 角色 → flow.yaml 重新分配权限
    → 组织结构变化，影响面最大
```

### 六种典型场景

| # | 场景 | 表面看像 | 实际应该改 | 为什么 |
|---|------|----------|-----------|--------|
| 1 | Agent 做了但做得不好 | 改 Skill | **改 Skill** ✅ | 能力存在，执行策略不对 |
| 2 | Agent 说"我不会" | 改 Scope？ | **加 Skill + API** | 能力不存在，但在定位范围内 |
| 3 | Agent 做了不该做的事 | 改 Skill | **收紧 Scope** | Skill 没错，边界太松 |
| 4 | Agent 拒绝了合理请求 | 改 Scope | **先查 Skill 是否存在** | 可能只是没注册 flow.yaml |
| 5 | 同一功能多角色冲突 | 改 Flow 权限 | **拆 Role** | 权限分配解决不了职责冲突 |
| 6 | 质量持续不达标 | 改 Skill 策略 | **先查 Commitment 定义** | 阈值不合理改了也没用 |

### 边界压力的三种模式

#### 模式 A：从内向外撑破（最常见 — P4 正常生长）

```
Skill 越来越多 → Scope 跟不上 → 需要扩展 Scope

    ┌─ Scope ─────────────────┐
    │  Capabilities:          │
    │  · task CRUD            │
    │  · health check         │
    │                         │
    │    ┌─ Flow ──────────┐  │
    │    │ create_task  ✅  │  │
    │    │ list_tasks   ✅  │  │
    │    │ send_email   ⚠️ ─┼──┼── 撑到边界了！
    │    │ notify_slack ⚠️ ─┼──┼── Scope 没声明这些能力
    │    └─────────────────┘  │
    └─────────────────────────┘

决策：这是正常生长（P4 阶段该做的事）
做法：先加 Skill + API → 验证可行 → 再批量更新 Scope
顺序：Flow 先行，Scope 跟随（不要先改 Scope 再实现）
```

#### 模式 B：从外向内压缩（需求方向变了）

```
业务方向变了 → Scope 需要收缩 → 部分 Skill 需要废弃

    Scope（旧）                     Scope（新）
    · task CRUD                     · task CRUD
    · email notification    ──>     · slack only
    · slack notification
    · sms notification              Boundaries:
                                    · 不再支持 email/sms

决策：这是战略调整，不是技术问题
做法：
  1. 先改 Scope（声明新边界）
  2. 再改 flow.yaml（移除废弃 action 的权限）
  3. SKILL.md 和 API 可以保留但不注册（降低风险）
  4. Git commit 说明原因
顺序：Scope 先行，Flow 跟随（与模式 A 相反）
```

#### 模式 C：横向穿透（跨原语联动）

```
一个需求同时触碰多个原语，无法在单一层面解决

例："reviewer 必须在 24h 内完成 review，否则自动升级给 admin"

同时涉及：
  · Commitment: time_to_review <= 24h（从 72h 收紧）
  · Flow: 新增 auto_escalate action + 状态 transition
  · Role: admin 需要 force_resolve 权限
  · Scope: 新增"自动升级"能力声明

决策：这是系统性变更，作为一个整体来规划
做法顺序：
  Commitment（为什么）→ Flow（怎么做）→ Role（谁来做）→ Scope（对外说）
```

### 决策速查表

```
需求来了
  │
  ├─ "Agent 做得不好"
  │     └→ 改 Skill 内容（SKILL.md 的 Flow 步骤）
  │
  ├─ "Agent 不会做 X"
  │     ├─ X 在 App 定位内？  → 加 Skill + API + 注册 flow.yaml
  │     └─ X 超出 App 定位？  → 拒绝，或评估是否要扩 Scope（P4 决策）
  │
  ├─ "Agent 做了不该做的事"
  │     ├─ Skill 写错了？     → 改 Skill
  │     ├─ 权限给多了？       → 改 flow.yaml 的 role 列表
  │     └─ Scope 太松？       → 收紧 Scope Boundaries
  │
  ├─ "质量/效率不达标"
  │     ├─ Commitment 阈值合理？ → 改 Skill 策略 / 加新 Skill
  │     └─ 阈值不合理？         → 调 Commitment（需有数据支撑）
  │
  ├─ "角色职责冲突"
  │     └→ 拆 Role + 重新分配 flow.yaml 权限
  │
  └─ "需求涉及多个原语"
        └→ 按 Commitment → Flow → Role → Scope 顺序逐层处理
```

### 核心原则

> **能在低层解决的问题，不要上升到高层。能改 Skill 就不改 Flow，能改 Flow 就不改 Scope。**

```
改 Skill   →  影响一个 action 的执行方式     → 秒级回滚
改 Flow    →  影响 action 注册和状态机       → 需要 redeploy
改 Scope   →  影响 Agent 行为边界 + 对外承诺  → 需要通知相关方
改 Role    →  影响组织结构和权限分配          → 需要重新设计
```

但反过来，**如果低层反复打补丁还是解决不了，那就是高层该变的信号**。Skill 里堆了一堆 workaround → 说明 Scope 或 Flow 的设计有问题。

---

## 五、测试与迭代的关系

测试不是迭代的"验收"，而是迭代的"驱动力"：

```
传统:     写代码 → 写测试 → 测试通过 → 迭代完成
Socialware: 测试失败 → 暴露能力缺口 → 驱动下一轮迭代
```

### 三层测试模型

#### 第一层：基础设施测试（保障四原语管线）

```python
# tests/test_deploy.py（已有）
def test_runtime_structure():
    """deploy.sh 产物结构正确"""
    assert (runtime / "agents" / "default" / "SOUL.md").exists()

def test_skill_symlinks():
    """flow.yaml 权限正确映射到 skills"""
    default_skills = list(skills_dir.iterdir())
    assert "check_health" in [s.name for s in default_skills]
    assert "setup_claude" not in [s.name for s in default_skills]  # dev only
```

#### 第二层：Skill 端到端测试（驱动 P2 迭代）

```python
# tests/test_skills.py
async def test_create_task_skill():
    """模拟: 用户说 'create a task' → Agent 调 POST /tasks → 返回 task ID"""
    adapter = load_web_adapter("default")
    await adapter.create_session("test-001")
    events = [e async for e in adapter.send_message("test-001", "Create a task called GPS purchase")]
    tool_calls = [e for e in events if e.type == "tool_call"]
    assert any("POST /tasks" in tc.content for tc in tool_calls)

async def test_unknown_capability():
    """Agent 应诚实说'我不会'，不编造能力"""
    events = [e async for e in adapter.send_message("test-002", "Send an email to team")]
    final_text = "".join(e.content for e in events if e.type == "text_delta")
    assert "email" not in final_text.lower() or "无法" in final_text
```

**迭代闭环**：
```
test_unknown_capability("email") 通过 → Agent 说"不会" → P2 迭代信号
    → Dev 写 send_email Skill + API → test_send_email 通过 → 迭代完成
```

#### 第三层：Commitment 测试（P3+ 自动化指标检查）

```python
# tests/test_commitments.py
async def test_review_sla():
    """C1: 所有提交的任务在 72h 内收到 review"""
    metrics = (await client.get("/metrics")).json()
    assert metrics["time_to_review_avg_hours"] <= 72
```

### Dev 驱动迭代的三种方式

| 方式 | 流程 | 特点 |
|------|------|------|
| **对话驱动** | 开 Agent Chat → 发现"不会" → 写 Skill | 最直觉，不可回归 |
| **测试驱动** | 先写 test_xxx_skill → 红 → 写 Skill → 绿 | 可回归，每次 deploy 自动验证 |
| **指标驱动** | Commitment 指标下降 → 分析原因 → 改进 | 被动响应，有数据支撑 |

---

## 六、迭代可观测性

每次迭代需要在三个层面留痕：

### 对用户可见：Agent 能力清单

内置 `list_capabilities` Skill，读取当前角色的 `.claude/skills/` 目录，列出所有可用 Skill 的 name + description。

```
用户: "你能做什么？"
迭代前: "① check_health"
迭代后: "① check_health ② create_task ③ list_tasks"
```

### 对 Dev 可见：deploy 输出变更摘要

```
[deploy] ── Changes ──────────────────────────
[deploy]  + Skill added:   create_task  → [default]
[deploy]  + Skill added:   list_tasks   → [default]
[deploy]  ~ Scope updated: SOUL.md (2 new capabilities)
[deploy] ── Summary ──────────────────────────
[deploy]  default: 3 skills (was 1, +2)
[deploy]  dev:     2 skills (unchanged)
```

### 对项目可见：Git 提交标注 Phase

```
git log -- agent/flow/flow.yaml

P2: add create_task, list_tasks
P2: add submit_task, query_task
P3: add remind_review (commitment-driven)
P4: add assign_task, notify_team
P5: add reviewer role, approval flow
```

### 可见性矩阵

| 迭代产物 | 用户感知 | Dev 感知 | 项目感知 |
|----------|----------|----------|----------|
| 新 Skill | "你能做什么"列表变长 | deploy 输出 `+ Skill added` | git log flow.yaml |
| Scope 更新 | Agent 拒绝越界请求 | deploy 输出 `~ Scope updated` | git diff scope/SOUL.md |
| Commitment | Agent 主动提醒/监控 | /metrics API 有数据 | eval.yaml 从空到有 |
| 新 Role | 不同窗口 Agent 行为不同 | deploy 输出新 role + skill 数量 | git log role/ |

---

## 七、迭代 Checklist

### 每轮 P2 迭代

```
□ 用户需求明确（用户说了什么 Agent 做不到的？）
□ 写 agent/flow/{action}/SKILL.md（Trigger + Flow + API）
□ 写 src/app.py 对应 API endpoint
□ 注册 agent/flow/flow.yaml（action + role 权限）
□ deploy + 验证（start.sh → 用户再试一次 → 成功）
□ 更新 agent/scope/SOUL.md Capabilities 列表
□ Git commit 标注 Phase: "P2: add {action}"
```

### 迭代决策 Checklist（遇到非 P2 常规需求时）

```
□ 按四层诊断定位该改哪一层（第四章）
□ 如果改 Scope/Role：评估对外影响 + 准备回滚方案
□ 如果跨原语联动：按 Commitment → Flow → Role → Scope 顺序
□ 如果反复在 Skill 层打补丁：考虑是否高层设计有问题
```

---

# Part III — Agent 接入与自治

## 八、Agent SDK Web 接入方案（通用模板）

> 参照 autoservice 已验证的完整链路，设计跨平台通用 Agent Web 接入层

### 通用接入层设计

当前 `BaseAdapter` 只覆盖 **启动** 层（launch_shell / launch_sdk），缺少 **Web 交互** 层。
需要把 adapter 从"启动器"升级为"会话管理器"：

```python
# agent/adapters/base.py 扩展

@dataclass
class AgentEvent:
    """所有平台 adapter 统一返回的事件类型"""
    type: Literal[
        "text_delta",    # 流式文本片段
        "text_done",     # 完整文本（非流式平台）
        "tool_call",     # Agent 调用工具
        "tool_result",   # 工具返回结果
        "thinking",      # Agent 思考中
        "done",          # 本轮结束
        "error",         # 出错
    ]
    content: str = ""
    metadata: dict = field(default_factory=dict)  # model, session_id, token_usage 等

class BaseAdapter(abc.ABC):
    # --- 已有：启动 ---
    def launch_shell(self) -> None: ...
    def launch_sdk(self) -> None: ...

    # --- 新增：Web 会话管理 ---
    async def create_session(self, session_id: str) -> None: ...
    async def send_message(self, session_id: str, content: str) -> AsyncIterator[AgentEvent]: ...
    async def close_session(self, session_id: str) -> None: ...
```

### 跨平台 adapter 映射

| AgentEvent | Claude SDK | OpenAI API | Gemini API | 中国 LLM |
|------------|------------|------------|------------|----------|
| `text_delta` | `StreamEvent` | `chunk.choices[0].delta` | `chunk.text` | `chunk.choices[0].delta` |
| `tool_call` | `ToolUseBlock` | `tool_calls` | `function_call` | `tool_calls` |
| `done` | `ResultMessage` | `finish_reason="stop"` | `finish_reason` | `finish_reason` |
| session resume | `session_id` | `thread_id` | 手动拼 history | 手动拼 history |

> **关键发现**：通义千问、智谱 GLM、Moonshot Kimi、DeepSeek 基本都兼容 OpenAI API 格式。
> 实际只需三个 Web adapter：
> 1. `ClaudeWebAdapter` — claude_code_sdk（Agent 模式，tool use + session）
> 2. `OpenAIWebAdapter` — openai.chat.completions（通义/智谱/Moonshot/DeepSeek 复用，换 base_url + api_key）
> 3. `GeminiWebAdapter` — google.generativeai

### 通用 WebSocket Handler（与 adapter 无关）

```python
# src/app.py

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    init = await ws.receive_json()
    role = init.get("role", "default")

    # 加载 adapter（从 deploy 产物读取）
    adapter = load_web_adapter(role, adapter_name=settings.ADAPTER)

    session_id = init.get("session_id") or str(uuid4())
    await adapter.create_session(session_id)
    await ws.send_json({"type": "ready", "session_id": session_id})

    try:
        while True:
            msg = await ws.receive_json()
            if msg["type"] == "user_message":
                async for event in adapter.send_message(session_id, msg["content"]):
                    await ws.send_json({
                        "type": event.type,
                        "content": event.content,
                        **event.metadata,
                    })
    finally:
        await adapter.close_session(session_id)
```

**这段 handler 对所有平台通用** — 切换 `ADAPTER=claude` / `openai` / `gemini` 即切换底层 LLM。

### 交互架构

```
┌─ Frontend (app/) ─────────────────────────────────────────────┐
│  Chat UI (Next.js)                                             │
│  ├─ WebSocket 持久连接                                         │
│  ├─ Token-level streaming 渲染                                 │
│  ├─ 消息队列（Agent 响应中排队后续消息）                         │
│  └─ 状态指示器（连接/思考/搜索）                                 │
└───────────────────── ↓ WebSocket ──────────────────────────────┘

┌─ Backend (src/) ──────────────────────────────────────────────┐
│  FastAPI Server                                                │
│                                                                │
│  ┌─ WebSocket Handler (/ws/chat) ──────────────────────────┐  │
│  │  1. Auth: 验证用户 token                                 │  │
│  │  2. Init: adapter.create_session() (platform-agnostic)   │  │
│  │  3. Loop: 接收消息 → adapter.send_message() → Stream 回   │  │
│  │  4. 会话持久化 (.runtime/data/)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─ Biz API (/api/*) ─────────────────────────────────────┐  │
│  │  Agent 通过 Bash curl 调用的业务端点                      │  │
│  │  kb_search, route_query, save_lead, tasks CRUD ...       │  │
│  │  可选 in-process 拦截（0ms fast path）                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────── ↓ adapter (可切换) ──────────────────────┘

┌─ Agent Layer（通过 BaseAdapter 抽象）────────────────────────┐
│  adapter.send_message() 内部调用各平台 SDK:                    │
│  ├─ Claude:  claude_code_sdk.query()                          │
│  ├─ OpenAI:  openai.chat.completions.create() (streaming)     │
│  ├─ Gemini:  generativeai.GenerativeModel.generate_content()  │
│  ├─ 中国LLM: openai 兼容接口 (换 base_url + api_key)          │
│  共同约定:                                                     │
│  ├─ System Prompt = SOUL.md (Scope + Role 合并)               │
│  ├─ Skills = .claude/skills/ 或等效机制                        │
│  ├─ Tools = Bash only (curl 调本地 API)                        │
│  └─ 返回统一 AgentEvent 流                                     │
└───────────────────────────────────────────────────────────────┘
```

### Agent ↔ App 通信模式

Agent 只有一个工具：**Bash**。通过 `curl` 调用本地 API 端点：

```
Agent 执行 Skill → Bash: curl http://localhost:8001/api/tasks → 拿到结果 → 回复用户
```

SKILL.md 的 `## API` 段就是这个模式的体现：

```markdown
## API
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "description": "..."}'
```

### autoservice 已验证的关键设计决策

| 决策 | 做法 | 效果 |
|------|------|------|
| **Tool 极简** | 只暴露 Bash | Agent 不会误用其他工具，行为可控 |
| **curl 调本地 API** | Skill 里写 curl 命令 | Agent 和 App 通过 HTTP 接口解耦 |
| **in-process 拦截** | 识别 curl 命令 → 直接调 Python 函数 | 0ms 延迟，无需真的起 subprocess |
| **WebSocket streaming** | token-level delta 推送 | 用户实时看到 Agent 思考/输出 |
| **Model 策略切换** | 简单任务 haiku，复杂推理 sonnet | 成本和体验的平衡 |
| **Session 恢复** | session_id + JSON 持久化 | 刷新页面不丢对话 |

### 在 Socialwares 中落地的路径

**Phase 1 最小可用**：
1. `src/app.py` 加 WebSocket endpoint (`/ws/chat`)
2. 接入 `claude_agent_sdk`（参照 autoservice 的 `autoservice/claude.py`）
3. `app/` 写最简 Chat UI（WebSocket + streaming 渲染）
4. Agent system prompt = 部署后的 `.runtime/agents/{role}/SOUL.md`

**Phase 2 能力增长**：
- 每加一个 Skill → 对应加一个 `/api/*` endpoint
- Agent 通过 Bash curl 调用 → 用户在 Chat 里看到结果

**Phase 3+ 生产化**：
- in-process tool 拦截（0ms fast path）
- Model 策略切换（Commitment 驱动）
- Session 持久化到 `.runtime/data/Sqlite/`
- 多角色隔离（不同 WebSocket endpoint 或 role 参数）

---

## 九、Agent 自迭代与渐进自治

### 9.1 自迭代前提

```
1. Agent 能读取自己的表现数据   → /metrics API + eval.yaml
2. Agent 能修改四原语文件       → 有 Write/Edit 权限
3. Agent 能验证修改效果         → deploy + test + /metrics 对比
```

### 9.2 Evolve Skill

```yaml
# agent/flow/flow.yaml
direct_actions:
  - action: evolve
    role: [dev]    # 只有 dev 角色能触发
    description: "Analyze metrics and improve four primitives"
```

```markdown
# agent/flow/evolve/SKILL.md

## Trigger
- Dev says "evolve", "optimize", "improve"
- Cron 定时触发（生产环境）
- Commitment 指标低于阈值时自动触发

## Flow
1. **Collect**: GET /metrics → 与 eval.yaml 阈值比较 → 找出未达标指标
2. **Diagnose**: 读取相关 SKILL.md + 对话历史 → 分析哪个执行路径导致指标下降
3. **Apply**: 修改 SKILL.md 执行策略（如 HEAR → SPIN）/ 调整 flow.yaml 权限
4. **Verify**: deploy → pytest → /metrics 对比改进前后
5. **Commit or Rollback**: 指标改善 → git commit; 未改善 → git checkout -- agent/
```

### 9.3 两种自迭代模式

```
模式 A: 租户特定（不触发 PR）
  修改 .runtime/ 中的内容 → 只影响当前 Workspace
  例: CINNOX 发现"先确认 region"效果好 → 改 .runtime/ skill

模式 B: 通用改进（自动 PR 回 main）
  修改 agent/ worktree 中的源文件 → PR → Dev review → 合并 → 所有租户受益
  例: 分析所有租户 Metrics → SPIN 普遍优于 HEAR → 改 agent/flow/ → PR
```

### 9.4 自治光谱（L0 → L6）

终极目标是 Agent 完成全部自迭代，但需要渐进达成。每一级跳跃的关键不是"Agent 能不能做"，而是"凭什么相信它做对了"——**信任通过验证机制解锁**。

```
完全人工                                                    完全自治
Dev 做一切                                              Agent 做一切
 ├──────┼──────┼──────┼──────┼──────┼──────┤
 L0     L1     L2     L3     L4     L5     L6
 执行   优化   创建   写代码  改边界  造新App  自我演化
 Skill  Skill  Skill  (API)  (原语)  (P0)   (改自己)
```

#### L0: 执行 Skill（当前状态）

```
Agent 做: 按 SKILL.md 步骤，curl 调 API，回复用户
Dev 做:   写 Skill、写 API、定义原语、所有决策
信任门槛: 无（Agent 只是执行者）
```

#### L1: 优化 Skill 内容

```
Agent 做: 修改 SKILL.md 的 Flow 步骤（如 HEAR → SPIN）
Dev 做:   写 API、定义原语、review Agent 的修改
信任门槛: /metrics 改善 + 测试通过

解锁条件:
  ✅ /metrics API 已存在
  ✅ eval.yaml 有明确阈值
  ✅ pytest 能跑 Skill 端到端测试
  ✅ git diff 可 review（Agent 的修改留在 PR 里）
```

> **这一级现在就可以做**。Evolve Skill（9.2 节）已设计好，缺的是 /metrics endpoint 和 Commitment 测试。

#### L2: 创建新 Skill

```
Agent 做: 检测到"我不会" → 自己创建 SKILL.md → 注册 flow.yaml → deploy
Dev 做:   写对应的 API endpoint + review SKILL.md 质量
信任门槛: SKILL.md 通过格式校验 + 现有测试全绿 + endpoint 存在

解锁需要——Skill 自动校验器:
  · frontmatter 完整（name + description）
  · 必须有 ## Trigger + ## Flow + ## API
  · API 中的 endpoint 在 src/app.py 中存在
  · flow.yaml 修改不破坏现有 action
```

校验器通过 + 测试全绿 → Agent 创建的 Skill 可自动合并，Dev 只需事后抽查。

#### L3: 写 API 代码

```
Agent 做: 创建 SKILL.md + 对应 API endpoint（src/app.py）+ 单元测试
         完整闭环：发现缺口 → 写 Skill → 写 API → 注册 → deploy → 测试
Dev 做:   review PR（代码质量、安全性）
信任门槛: 类型标注 + 输入校验 + 单元测试 + 安全扫描 + 只新增不改已有代码

解锁需要:
  · API 代码模板化（输入 schema → 业务逻辑 → 输出 schema）
  · 沙箱验证（临时 branch + worktree + 独立 .runtime/）
  · PR 作为信任边界 → 随着 review 通过率上升 → 逐步放宽自动合并条件
```

> **这一级是关键跳跃**——Agent 从"操作者"变成"开发者"。

#### L4: 修改原语边界

```
Agent 做: 调整 Scope / Commitment / flow.yaml 权限 / 建议新 Role
Dev 做:   审批战略性变更（只介入"第一次"，之后同类变更可自动化）
信任门槛: 变更影响分析 + 回滚机制 + A/B 验证

解锁需要:
  · Agent 学会第四章的决策框架（四层诊断 + 三种边界压力模式）
  · 变更提案机制（原因 + 影响分析 + 回滚方案）
  · 提案通过率统计 → 通过率稳定 > 阈值 → 放开自动执行权限
```

#### L5: 创建新 App（P0 回环）

```
Agent 做: 检测到触达边界 → 创建新 Socialware 或 /zchat 连接 → 初始化四原语
Dev 做:   审批"是否真的需要新 App"
信任门槛: 正确判断"触达边界" vs "还能在当前 App 内解决"
         + 新 App 四原语定义质量足够好
         + /zchat 目标 App 确实能处理委派任务
```

#### L6: 自我演化（终极目标）

```
Agent 做: 修改 Evolve Skill 本身（改善自我改善的方法）
         修改 deploy.sh / SKILL.md schema / BaseAdapter 接口
         即：Agent 能改四原语的"形"，不仅仅是"内容"
Dev 做:   设定"不可变规则"（constitutional constraints）+ 偶尔审查
```

### 9.5 Dev 迭代 vs Agent 自迭代的能力边界

能力范围随自治等级逐步扩大：

| 操作 | Dev | L0 | L1 | L2 | L3 | L4+ |
|------|-----|----|----|----|----|-----|
| 执行 Skill | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 改 SKILL.md 内容 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 创建新 SKILL | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| 写 API endpoint | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 改 Scope/Commitment | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 拆/加 Role | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 改原语的"形" | ✅ | ❌ | ❌ | ❌ | ❌ | L6 |

### 9.6 渐进路径总览

```
            当前可做       近期可做       中期目标       远期愿景
            ────────      ────────      ────────      ────────
            L0 执行        L1 优化       L2-L3         L4-L6
                          Skill        创建+写代码     改边界+造App

需要什么     已有           /metrics     Skill 校验器   变更提案机制
                          + eval.yaml  + 沙箱测试     + A/B 验证
                          + Evolve     + PR 自动化    + 不可变规则
                          Skill        + 代码模板

Dev 参与度   100%          80%          40%           10%
Agent 自治   0%            20%          60%           90%

信任机制     无需           指标+测试    校验+PR+沙箱   提案+审批+回滚
```

### 9.7 解锁模式

每一级的解锁都遵循同一模式：

```
1. 先让 Agent 做，但结果必须经过验证门
2. 统计验证通过率
3. 通过率稳定 > 阈值 → 放宽验证门（从 Dev review → 自动合并）
4. 进入下一级
```

这与 Commitment 的理念一致——**用可度量的标准来决定自治边界的扩展**。

### 9.8 当前最优先的一步：L0 → L1

启动第一个自迭代闭环只需三件事：

```
1. 实现 /metrics endpoint       → 让 Agent 能读自己的表现
2. 填充 eval.yaml              → 给 Agent 一个达标标准
3. 创建 evolve Skill           → 给 Agent 一个自我改善的入口
```

完成后 Agent 就有了第一个自迭代闭环。后续每一级都是在这个闭环上叠加更强的验证机制。
