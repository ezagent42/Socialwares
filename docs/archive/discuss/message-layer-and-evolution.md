# 共享消息层与软件自进化

## 1. 共享消息层

### 问题

当前 Socialware App 有两条操作路径：

- **聊天路径**：用户输入 → LLM 推理 → tool_call（curl POST /tasks）→ API → 结果
- **UI 路径**：按钮点击 → API → 结果

两条路径产生的数据格式不同。聊天路径是自然语言对话流（混杂着推理过程），UI 路径是 HTTP 请求/响应。前端需要分别处理。

### 方案：Action Event 作为共享格式

LLM 对话中已经包含结构化数据——`tool_call` 和 `tool_result`。提取它们作为共享消息格式：

```
Action Event (输入)
{
  "type": "create_task",
  "source": "agent" | "ui" | "api",
  "payload": {"title": "fix bug"},
  "timestamp": "2025-03-26T12:00:00Z",
  "trace_id": "uuid"
}

Result Event (输出)
{
  "type": "task_created",
  "source": "api",
  "payload": {"id": "task-001", "title": "fix bug", "status": "draft"},
  "timestamp": "2025-03-26T12:00:01Z",
  "trace_id": "uuid"
}
```

### 转化机制

```
聊天框                                  UI 按钮
  │                                       │
  ▼                                       │
LLM 推理                                  │
  │                                       │
  ▼                                       │
tool_call:                                │
  curl POST /tasks                        │  onClick:
  -d '{"title":"fix bug"}'                │  POST /tasks {"title":"fix bug"}
  │                                       │
  ├── 提取为 Action Event ◄───────────────┘
  │   {type: "create_task",
  │    payload: {title: "fix bug"}}
  │
  ▼
API Layer 执行
  │
  ▼
Result Event
  {type: "task_created",
   payload: {id: "task-001"}}
  │
  ├──► 聊天窗口：LLM 包装为自然语言 "Task #1 已创建"
  └──► UI 组件：直接渲染（表格加一行）
```

**转化规则**：

| 来源 | 转化为 Action Event | 说明 |
|------|-------------------|------|
| LLM tool_call | 解析 tool_name + tool_input → type + payload | Hook（PreToolUse）已经在拦截 tool_call |
| UI 按钮 | 前端直接构造 | 和 tool_call 同构 |
| 外部 API | 入站请求直接转化 | Webhook 等场景 |

**Hook 是天然的转化点**。现有的 `PreToolUse` hook 已经拦截了所有 tool_call 并记录到 `prompts/*.jsonl`。只需要额外将其发布到 Message Bus。

### Message Bus

```
                    ┌─────────────────┐
                    │   Message Bus    │
                    │   (Event Store)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         前端 (WS)      Agent (订阅)    持久化
         UI 更新        获取上下文       审计/回放
```

- **传输**：WebSocket（单机）或 NATS/Redis Streams（分布式）
- **持久化**：Event Store（append-only log，天然支持 CRDT）
- **P2P 场景**：每个节点本地 Event Store + CRDT 合并

---

## 2. 通过 Evolve 生成 Action Schema 加速 LLM

### 问题

LLM 每次处理 "create task: fix bug" 都要：
1. 读 SOUL.md 理解角色
2. 匹配 SKILL.md 找到正确的 skill
3. 推理出 API 调用方式
4. 构造 tool_call

步骤 2-4 对已知操作是确定性的，但 LLM 每次重新推理。

### 方案：Evolve 生成 Action Schema

Evolve 分析 `.runtime/data/` 中的历史 tool_call 记录，提取出稳定的 Action Schema：

```yaml
# .runtime/data/evolve/action_schema.yaml（deploy 时由 evolve 生成）
actions:
  create_task:
    method: POST
    endpoint: /tasks
    params:
      title: { type: string, required: true, extract_from: "user_input" }
      status: { type: string, default: "draft" }
    examples:
      - input: "create task: fix bug"
        payload: { title: "fix bug" }
      - input: "新建任务 写文档"
        payload: { title: "写文档" }
    confidence: 0.95  # 基于历史成功率
    sample_count: 47   # 观察到的样本数

  check_health:
    method: GET
    endpoint: /health
    params: {}
    confidence: 1.0
    sample_count: 120
```

### 生成流程

```
                    历史数据
                       │
     ┌─────────────────┼─────────────────┐
     ▼                 ▼                 ▼
prompts/*.jsonl   sessions/*.json   evolve/reports/
(tool_call 记录)  (完整对话)        (eval/diagnose 结果)
     │                 │                 │
     └─────────────────┼─────────────────┘
                       │
                       ▼
              evolve_auto 分析
              "create task: *" → POST /tasks
              成功率 95%, 47 次观察
                       │
                       ▼
              action_schema.yaml
                       │
                       ▼
              deploy.sh 注入到 SOUL.md
```

### 加速机制

Action Schema 注入 SOUL.md 后，LLM 不需要每次从 SKILL.md 推理 API 调用方式——直接看 Schema 就知道：

```markdown
## Action Schema (auto-generated, do not edit)

When user intent matches a known action, use the schema directly:

| Intent | Action | Method | Endpoint | Params |
|--------|--------|--------|----------|--------|
| create task: {title} | create_task | POST | /tasks | title={title}, status=draft |
| check health | check_health | GET | /health | (none) |
| list tasks | list_tasks | GET | /tasks | (none) |

For unknown intents, fall back to reading SKILL.md.
```

**效果**：LLM 从 "读 SKILL.md → 理解 → 推理 → 构造 tool_call" 变成 "查表 → 填参数 → tool_call"。推理步骤减少，token 消耗降低，响应更快。

---

## 3. Runtime 自进化

### 目标

将 evolve 机制从"开发者手动触发"升级为"运行时自动执行"，实现软件自进化循环。

### 三阶段生命周期

```
┌──────────────────────────────────────────────────────┐
│                    运行时自进化循环                      │
│                                                       │
│   ┌─────────┐    ┌──────────┐    ┌─────────────┐     │
│   │  Stage 1 │    │ Stage 2  │    │  Stage 3    │     │
│   │  观察    │───►│ 分析     │───►│  进化       │──┐  │
│   │ Observe  │    │ Analyze  │    │  Evolve     │  │  │
│   └─────────┘    └──────────┘    └─────────────┘  │  │
│        ▲                                           │  │
│        └───────────────────────────────────────────┘  │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Stage 1: 观察（Observe）

**已有机制，无需新增：**

- `log_prompt.sh` (UserPromptSubmit hook) → 记录用户输入
- `log_tool.sh` (PreToolUse hook) → 记录 tool_call
- `save_session()` → 记录完整 SDK 对话
- `save_violation.py` → 记录 commitment 违反

**新增**：将 tool_call 同时发布为 Action Event 到 Message Bus。

```
PreToolUse Hook
  │
  ├── 写入 prompts/*.jsonl（现有）
  └── 发布 Action Event 到 Bus（新增）
```

### Stage 2: 分析（Analyze）

**触发方式**：定时 cron 或 event 数量阈值。

```
分析流程：
  1. evolve_structure_check → 结构一致性
  2. evolve_api_check      → API 通过率
  3. evolve_session_diagnose → commitment 履行率
  4. evolve_auto            → 对话测试通过率
  │
  ▼
生成分析报告 → .runtime/data/evolve/reports/
```

**新增：Action Schema 提取**

```
从 prompts/*.jsonl 中提取:
  tool_call 频次统计
  (user_input, tool_call) 配对
  成功率计算
  │
  ▼
生成 action_schema.yaml
```

### Stage 3: 进化（Evolve）

根据分析结果，自动或半自动地改进系统：

```
分析报告
  │
  ├── Action Schema 置信度 > 0.9
  │   └── 自动：注入 SOUL.md，加速 LLM
  │
  ├── API 测试失败
  │   └── 半自动：生成 improve 报告，等开发者确认
  │
  ├── Commitment 违反
  │   └── 半自动：save_violation → 通知开发者
  │
  └── 新的稳定 (input, action) 模式
      └── 自动：更新 action_schema.yaml
```

### 完整运行时流程

```
App 运行
  │
  ▼
用户操作（聊天 / UI）
  │
  ├──► Action Event → Message Bus → 前端更新
  │
  └──► Hook 记录 → .runtime/data/
                        │
                  ┌─────┴──────┐
                  ▼            ▼
            积累到阈值    定时触发 (cron)
                  │            │
                  └─────┬──────┘
                        ▼
                   分析 (Stage 2)
                   evolve scripts
                        │
                        ▼
                  ┌─────┴──────┐
                  ▼            ▼
            自动进化        半自动进化
            (schema)       (improve 报告)
                  │            │
                  ▼            ▼
            make deploy    开发者审核
            热更新          → 修改 → deploy
```

### 自动 vs 半自动边界

| 操作 | 自动/半自动 | 原因 |
|------|-----------|------|
| 更新 action_schema.yaml | 自动 | 不改业务逻辑，只是观察到的事实 |
| 注入 Schema 到 SOUL.md | 自动 | deploy 级别操作，可回滚 |
| 修改 SKILL.md | 半自动 | 改变 agent 行为，需确认 |
| 修改 commitment.yaml | 半自动 | 改变评估标准，需确认 |
| 修改 src/app.py | 半自动 | 改变后端逻辑，需确认 |
| 添加新 role | 半自动 | 架构变更，需确认 |

---

## 实现路径

### Phase 1: Action Event 提取（基于现有 Hook）

改动最小。PreToolUse hook 已经拦截了 tool_call，只需要额外输出为统一的 Action Event 格式，写入 `.runtime/data/events/` 目录。

### Phase 2: Action Schema 生成

新增 evolve 脚本 `extract_schema.py`：读取 prompts/*.jsonl 中的 tool_call 记录，统计频次和成功率，输出 action_schema.yaml。deploy.sh 将 Schema 注入 SOUL.md。

### Phase 3: Message Bus 集成

引入轻量 Message Bus（单机用 SQLite + WebSocket 即可）。Action Event 和 Result Event 通过 Bus 分发。前端通过 WebSocket 订阅实时更新。

### Phase 4: Runtime Evolve Loop

添加 cron/watcher 触发 evolve 分析。高置信度的 Schema 更新自动 deploy。低置信度的改进生成报告等待人工确认。

---

## 和现有架构的关系

```
现有                              新增
────                              ────
四原语 (Role/Scope/               Action Event 格式
       Commitment/Flow)           Action Schema (auto-generated)
                                  Message Bus
deploy.sh → .runtime/             deploy.sh → .runtime/ + schema
Hook → prompts/*.jsonl            Hook → prompts/ + events/
Evolver (手动)                    Evolver (手动 + 自动触发)
SKILL.md (LLM 每次读)             Schema (LLM 查表) + SKILL.md (fallback)
```

不替换现有机制，只在其上叠加。SKILL.md 仍然是 agent 的完整说明书，Schema 是从使用数据中提炼的快速查找表。
