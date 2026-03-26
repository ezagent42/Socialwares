# AgentForge 双交互模式实现详解

> 版本: v1.1 | 日期: 2026-03-26
> 关联文档: [agentforge-cms-design.md](./2026-03-26-agentforge-cms-design.md) §2.3

## 1. 核心思路

AgentForge 有两种用户交互方式，但底层共用同一条通道：

```
模式 A: 用户在 Chat 输入框打字 → 自然语言 → Agent
模式 B: 用户在 UI 上点击按钮 → UIAction 结构化指令 → Agent
```

**关键：模式 B 不是绕过 Agent 直接调 API，而是把 UI 操作序列化为结构化指令，走 Chat 通道交给 Agent 理解和执行。**

**为什么不用 Prompt 模板映射表？**

早期设计中考虑过前端维护一个 `UIAction → 自然语言 prompt` 的映射表（如 `{entity:"agent", action:"delete"} → "删除 Agent X"`）。但这种方案存在明显局限：

| 场景 | 映射表方案的问题 |
|------|---------------|
| 多选批量删除 | 需要新增 `batch_delete` 模板 |
| 多选批量导出 | 需要新增 `batch_export` 模板 |
| 带条件的操作 | "导出选中的 3 个 Agent，但跳过没有 skill 的" — 映射表无法表达 |
| 新增操作类型 | 每次都要改前端代码 |
| 复合操作 | "先导出再删除" — 映射表组合爆炸 |

**改进方案：直接发送 UIAction 结构化指令，让 Agent 自己理解。**

Agent 通过 SKILL.md 中的指令理解 UIAction 的含义，就像理解自然语言一样。这是 Socialware 的核心理念——Agent 是唯一的决策者，前端只负责收集用户意图。

好处：
- Agent 始终是唯一决策者，保证行为一致性
- 对话历史完整，UI 操作也有记录可追溯
- 不需要为 UI 操作单独写后端接口
- **新增操作只需改 SKILL.md，不需要改前端代码**
- **天然支持多选、批量、复合操作**

---

## 2. 实现分层

```
┌──────────────────────────────────────────────────────────────┐
│                        前端实现                               │
│                                                              │
│  Layer 1: UI 组件层                                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  AgentCard / RoleCard / SkillCard / ConfirmDialog    │    │
│  │  每个组件上有操作按钮 (删除/编辑/导出/确认/取消)        │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │ onClick → UIAction                  │
│  Layer 2: UIAction 序列化层                                   │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │  serializeUIAction(action)                           │    │
│  │  UIAction → JSON 结构化指令（不做自然语言翻译）         │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │ JSON string                         │
│  Layer 3: 消息发送层                                          │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │  ChatStore.sendMessage(payload, source: "ui_action") │    │
│  │  → 添加到消息列表                                      │    │
│  │  → POST /api/chat/send                               │    │
│  │  → 监听 SSE 响应                                      │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         │ SSE events                          │
│  Layer 4: 响应处理层                                          │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │  ResponseParser                                      │    │
│  │  → 解析 text / structured 事件                        │    │
│  │  → 更新 Chat Store (messages + entities)              │    │
│  │  → 触发 UI 重新渲染                                    │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Layer 1: UI 组件层 — 按钮如何触发操作

### 3.1 ActionButton 组件

所有 Card 上的操作按钮统一使用 `ActionButton` 组件，点击后直接发送 UIAction 结构化指令：

```tsx
// app/src/components/action-button.tsx

import { useChatStore } from "@/lib/chat-store";
import { serializeUIAction, UIAction } from "@/lib/ui-action";

interface ActionButtonProps {
  entity: string;        // "agent" | "role" | "skill"
  action: string;        // "delete" | "edit" | "export" | "detail"
  data: Record<string, any>;  // 实体数据 (name, agent_name, id 等)
  label: string;
  variant?: "default" | "danger";
}

function ActionButton({ entity, action, data, label, variant }: ActionButtonProps) {
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  const isLoading = useChatStore((s) => s.session.loading);

  function handleClick() {
    sendUIAction({ entity, action, targets: [data] });
  }

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className={variant === "danger" ? "text-red-500" : "text-gray-600"}
    >
      {label}
    </button>
  );
}
```

### 3.2 BatchActionBar — 批量操作栏

当用户在 Dashboard 中多选 Card 时，出现批量操作栏：

```tsx
// app/src/components/batch-action-bar.tsx

function BatchActionBar() {
  const selected = useChatStore((s) => s.selected);  // 选中的实体列表
  const sendUIAction = useChatStore((s) => s.sendUIAction);

  if (selected.length === 0) return null;

  return (
    <div className="flex items-center gap-2 p-2 bg-blue-50 rounded">
      <span className="text-sm">已选中 {selected.length} 项</span>
      <button onClick={() => sendUIAction({
        entity: selected[0].entity,
        action: "export",
        targets: selected,
      })}>
        批量导出
      </button>
      <button onClick={() => sendUIAction({
        entity: selected[0].entity,
        action: "delete",
        targets: selected,
      })} className="text-red-500">
        批量删除
      </button>
    </div>
  );
}
```

### 3.3 Card 组件中使用 ActionButton

以 AgentCard 为例（增加了多选 checkbox）：

```tsx
// app/src/components/cards/agent-card.tsx

function AgentCard({ data }: { data: AgentData }) {
  const toggleSelect = useChatStore((s) => s.toggleSelect);
  const isSelected = useChatStore((s) => s.selected.some(s => s.id === data.id));

  return (
    <div className={`border rounded-lg p-4 ${isSelected ? "border-blue-500 bg-blue-50" : ""}`}>
      <div className="flex justify-between items-start">
        <div className="flex gap-2 items-start">
          {/* 多选 checkbox */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleSelect({ entity: "agent", ...data })}
          />
          <div>
            <h3 className="font-bold">{data.name}</h3>
            <p className="text-sm text-gray-500">{data.description}</p>
            <div className="flex gap-2 mt-1 text-xs text-gray-400">
              <span>Roles: {data.roles?.length ?? 0}</span>
              <span>Skills: {data.skills?.length ?? 0}</span>
            </div>
          </div>
        </div>

        {/* 单个操作按钮 */}
        <div className="flex gap-1">
          <ActionButton entity="agent" action="detail" data={data} label="详情" />
          <ActionButton entity="agent" action="export" data={data} label="导出" />
          <ActionButton entity="agent" action="delete" data={data} label="删除" variant="danger" />
        </div>
      </div>
    </div>
  );
}
```

### 3.4 ConfirmDialog — Agent 请求确认时的交互组件

当 Agent 返回需要用户确认的响应时（如删除操作），前端渲染确认对话框：

```tsx
// app/src/components/confirm-dialog.tsx

interface ConfirmDialogProps {
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

function ConfirmDialog({ message, confirmLabel = "确认", cancelLabel = "取消" }: ConfirmDialogProps) {
  const sendUIAction = useChatStore((s) => s.sendUIAction);

  return (
    <div className="border rounded-lg p-4 bg-amber-50">
      <p>{message}</p>
      <div className="flex gap-2 mt-3">
        <button
          onClick={() => sendUIAction({ entity: "_dialog", action: "confirm", targets: [] })}
          className="px-3 py-1 bg-red-500 text-white rounded"
        >
          {confirmLabel}
        </button>
        <button
          onClick={() => sendUIAction({ entity: "_dialog", action: "cancel", targets: [] })}
          className="px-3 py-1 bg-gray-200 rounded"
        >
          {cancelLabel}
        </button>
      </div>
    </div>
  );
}
```

**何时渲染 ConfirmDialog？**

Agent 返回的结构化数据中，通过 `action: "confirm_required"` 触发：

```json
{
  "type": "agent",
  "action": "confirm_required",
  "data": {
    "message": "确定删除 Agent task-manager？将同时删除 2 个角色和 5 个技能。",
    "confirm_label": "确认删除",
    "cancel_label": "取消"
  }
}
```

---

## 4. Layer 2: UIAction 序列化 — 让 Agent 自己理解 UI 操作

### 4.1 设计理念：为什么不用 Prompt 模板映射表

传统方案是前端维护一个 `UIAction → 自然语言` 的映射表（如 `delete + agent → "删除 Agent X"`）。但这有根本性缺陷：

```
映射表方案：
  前端定义了 Agent 能理解什么 → Agent 只是执行者
  （前端越来越胖，每加一种操作都要改映射表）

Agent 理解方案：
  前端只描述 "发生了什么" → Agent 自己决定怎么做
  （前端永远只做序列化，Agent 通过 SKILL.md 理解一切）
```

**这正是 Socialware 的核心理念：Agent 是决策者，UI 只是输入通道。**

### 4.2 UIAction 结构定义

```typescript
// app/src/lib/ui-action.ts

/**
 * UIAction 是前端 UI 操作的结构化描述
 * 不做自然语言翻译，直接序列化为 JSON 发给 Agent
 */
export interface UIAction {
  entity: string;               // "agent" | "role" | "skill" | "scope" | "commitment" | "_dialog"
  action: string;               // "delete" | "edit" | "export" | "detail" | "confirm" | "cancel"
  targets: TargetItem[];        // 操作目标列表（支持单选和多选）
  context?: Record<string, any>; // 可选的额外上下文
}

export interface TargetItem {
  id: string;
  name: string;
  entity: string;                // 实体类型（批量操作中可能混合类型）
  [key: string]: any;            // 其他实体属性
}

/**
 * 序列化 UIAction 为发送给 Agent 的消息
 * 使用特殊标记让后端/Agent 识别这是结构化指令而非自然语言
 */
export function serializeUIAction(action: UIAction): string {
  return `\`\`\`ui_action\n${JSON.stringify(action, null, 2)}\n\`\`\``;
}
```

### 4.3 UIAction 序列化示例

**单个操作：**

```json
// 点击 AgentCard 的 [删除]
{
  "entity": "agent",
  "action": "delete",
  "targets": [
    { "id": "a1", "name": "task-manager", "entity": "agent" }
  ]
}

// 点击 RoleCard 的 [编辑]
{
  "entity": "role",
  "action": "edit",
  "targets": [
    { "id": "r2", "name": "reviewer", "entity": "role", "agent_name": "task-manager" }
  ]
}
```

**批量操作：**

```json
// 多选 3 个 Agent 后点击 [批量导出]
{
  "entity": "agent",
  "action": "export",
  "targets": [
    { "id": "a1", "name": "task-manager", "entity": "agent" },
    { "id": "a2", "name": "chatbot", "entity": "agent" },
    { "id": "a3", "name": "code-assistant", "entity": "agent" }
  ]
}

// 多选后点击 [批量删除]
{
  "entity": "agent",
  "action": "delete",
  "targets": [
    { "id": "a1", "name": "task-manager", "entity": "agent" },
    { "id": "a3", "name": "code-assistant", "entity": "agent" }
  ]
}
```

**确认/取消：**

```json
// 点击 ConfirmDialog 的 [确认]
{
  "entity": "_dialog",
  "action": "confirm",
  "targets": []
}
```

### 4.4 Agent 如何理解 UIAction — 通过 SKILL.md

Agent 不需要额外代码来解析 UIAction，只需要在 SKILL.md 中说明如何处理。以 `manage_agent` 为例，在 SKILL.md 中增加 UIAction 处理说明：

```markdown
## UIAction 处理

当收到 ```ui_action 代码块时，按以下规则处理：

### 单个目标 (targets.length === 1)

与自然语言指令等效，按 entity + action 执行对应操作。

### 多个目标 (targets.length > 1)

批量操作：
- action: "delete" → 逐个确认后批量删除，先列出所有目标让用户确认
- action: "export" → 批量导出，每个 Agent 导出到各自的目录
- action: "detail" → 返回所有目标的概要信息表格

### 确认/取消 (_dialog)

- action: "confirm" → 执行上一轮请求确认的操作
- action: "cancel" → 取消上一轮操作，不执行
```

**优势：新增任何操作场景，只需修改 SKILL.md，不需要改前端代码。**

例如将来要支持 "选中 3 个 Agent，合并为一个"：
- 前端：不需要改（UIAction 已经支持多选）
- 后端：不需要改（Chat 通道不变）
- 只改：SKILL.md 中增加 `action: "merge"` 的处理说明 + CRUD 中增加 merge 函数

### 4.5 后端解析 UIAction

后端在收到消息时，识别 `ui_action` 代码块并将其作为 Agent 输入的一部分：

```python
# src/session.py

import re
import json

def parse_message(raw_message: str) -> dict:
    """
    解析用户消息，识别 ui_action 代码块

    普通消息: { "type": "text", "content": "帮我创建一个 Agent" }
    UI 操作:  { "type": "ui_action", "content": "...", "action": {...} }
    """
    ui_action_match = re.search(r'```ui_action\n(.*?)\n```', raw_message, re.DOTALL)

    if ui_action_match:
        action_json = json.loads(ui_action_match.group(1))
        return {
            "type": "ui_action",
            "content": raw_message,  # 完整消息（含代码块）传给 Agent
            "action": action_json,
        }

    return { "type": "text", "content": raw_message }
```

Agent 收到包含 `ui_action` 代码块的消息后，根据 SKILL.md 中的指导自行理解和执行。

---

## 5. Layer 3: 消息发送层 — ChatStore 如何统一处理

### 5.1 ChatStore 核心实现

```typescript
// app/src/lib/chat-store.ts

import { create } from "zustand";
import { UIAction, serializeUIAction } from "./ui-action";

interface ChatStore {
  user: User | null;
  messages: Message[];
  entities: EntityStore;
  selected: TargetItem[];  // 多选列表
  session: { connected: boolean; loading: boolean };

  // 核心方法
  sendMessage: (content: string, source: "chat" | "ui_action") => Promise<void>;
  sendUIAction: (action: UIAction) => Promise<void>;  // UI 操作专用入口
  toggleSelect: (item: TargetItem) => void;            // 多选切换
  clearSelection: () => void;                          // 清空选择
  setUser: (user: User | null) => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  user: null,
  messages: [],
  entities: { agents: {}, roles: {}, skills: {} },
  selected: [],
  session: { connected: false, loading: false },

  setUser: (user) => set({ user }),

  toggleSelect: (item) => {
    const { selected } = get();
    const exists = selected.some(s => s.id === item.id);
    set({ selected: exists ? selected.filter(s => s.id !== item.id) : [...selected, item] });
  },

  clearSelection: () => set({ selected: [] }),

  /**
   * UI 操作专用入口
   * 将 UIAction 序列化后通过 sendMessage 发送
   */
  sendUIAction: async (action: UIAction) => {
    const serialized = serializeUIAction(action);
    // Chat 中显示简洁的操作描述，而非 JSON
    const displayText = formatUIActionDisplay(action);
    await get().sendMessage(serialized, "ui_action", displayText);
    // 发送后清空多选
    get().clearSelection();
  },

  /**
   * 发送消息 — 统一入口
   *
   * @param content     - 实际发送内容 (自然语言或序列化的 UIAction)
   * @param source      - "chat" 或 "ui_action"
   * @param displayText - 可选，Chat 中显示的文本（UI 操作时用简洁描述替代 JSON）
   */
  sendMessage: async (content: string, source: "chat" | "ui_action", displayText?: string) => {
    const { messages } = get();

    // 1. 立即将用户消息加入列表 (乐观更新)
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: displayText ?? content,  // Chat 中显示 displayText，发送 content
      rawContent: content,              // 实际发送的内容（含 ui_action JSON）
      timestamp: Date.now(),
      source,
    };
    set({ messages: [...messages, userMsg], session: { connected: true, loading: true } });

    // 2. 发送给后端（发送实际内容，不是 displayText）
    await fetch("/api/chat/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: content }),  // content 含 ui_action JSON
      credentials: "include",
    });

    // 3. 监听 SSE 流获取 Agent 响应
    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      source: "chat",  // Agent 响应始终标记为 chat
    };

    const eventSource = new EventSource("/api/chat/stream", { withCredentials: true });

    eventSource.addEventListener("text", (e) => {
      // 4a. 流式追加文本
      const data = JSON.parse(e.data);
      assistantMsg.content += data.content;
      set({ messages: [...get().messages.filter(m => m.id !== assistantMsg.id), { ...assistantMsg }] });
    });

    eventSource.addEventListener("structured", (e) => {
      // 4b. 收到结构化数据
      const structured: StructuredData = JSON.parse(e.data);
      assistantMsg.structured = structured;

      // 4c. 同步更新 entities (供 Dashboard 使用)
      const entities = updateEntities(get().entities, structured);
      set({ entities });
    });

    eventSource.addEventListener("done", () => {
      // 5. 流结束
      set({
        messages: [...get().messages],
        session: { connected: true, loading: false },
      });
      eventSource.close();
    });

    eventSource.addEventListener("error", (e) => {
      set({ session: { connected: true, loading: false } });
      eventSource.close();
    });
  },
}));
```

### 5.2 UIAction 显示格式化

UI 操作在 Chat 中显示为简洁的操作描述（不是 JSON）：

```typescript
// app/src/lib/ui-action.ts (续)

/**
 * 将 UIAction 格式化为 Chat 中的显示文本
 * 这只是展示用，不影响发送给 Agent 的内容
 */
export function formatUIActionDisplay(action: UIAction): string {
  const names = action.targets.map(t => t.name).join(", ");
  const count = action.targets.length;

  if (action.entity === "_dialog") {
    return action.action === "confirm" ? "确认" : "取消";
  }

  if (count === 0) return `${action.action}`;
  if (count === 1) return `${action.action} ${action.entity}: ${names}`;
  return `${action.action} ${count} 个 ${action.entity}: ${names}`;
}
```

Chat 中的显示效果：

```
单个操作:  🔧 delete agent: task-manager
批量操作:  🔧 export 3 个 agent: task-manager, chatbot, code-assistant
确认:      🔧 确认
```

### 5.3 Entity 更新函数

```typescript
// app/src/lib/entity-updater.ts

interface EntityStore {
  agents: Record<string, AgentData>;
  roles: Record<string, RoleData>;
  skills: Record<string, SkillData>;
}

/**
 * 根据 Agent 返回的结构化数据更新实体索引
 * Dashboard 从这个索引渲染 Card 列表
 */
export function updateEntities(current: EntityStore, event: StructuredData): EntityStore {
  const next = { ...current };
  const { type, action, data } = event;

  switch (type) {
    case "agent":
      if (action === "created" || action === "updated") {
        next.agents = { ...next.agents, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.agents;
        next.agents = rest;
      } else if (action === "listed") {
        // listed 替换整个列表
        next.agents = {};
        for (const agent of data.agents ?? []) {
          next.agents[agent.id] = agent;
        }
      }
      break;

    case "role":
      if (action === "created" || action === "updated") {
        next.roles = { ...next.roles, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.roles;
        next.roles = rest;
      } else if (action === "listed") {
        // 只替换该 agent 下的 roles
        const otherRoles = Object.fromEntries(
          Object.entries(next.roles).filter(([_, r]) => r.agent_id !== data.agent_id)
        );
        next.roles = { ...otherRoles };
        for (const role of data.roles ?? []) {
          next.roles[role.id] = { ...role, agent_id: data.agent_id };
        }
      }
      break;

    case "skill":
      // 同 role 逻辑
      if (action === "created" || action === "updated") {
        next.skills = { ...next.skills, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.skills;
        next.skills = rest;
      } else if (action === "listed") {
        const otherSkills = Object.fromEntries(
          Object.entries(next.skills).filter(([_, s]) => s.agent_id !== data.agent_id)
        );
        next.skills = { ...otherSkills };
        for (const skill of data.skills ?? []) {
          next.skills[skill.id] = { ...skill, agent_id: data.agent_id };
        }
      }
      break;

    // scope, commitment 不需要维护列表索引（它们是 agent 的子属性）
    // deploy 也不需要
  }

  return next;
}
```

---

## 6. Layer 4: 响应处理层 — 如何渲染 Agent 返回的内容

### 6.1 StructuredBlockRenderer — 核心分发器

```tsx
// app/src/components/structured-block-renderer.tsx

import { AgentCard } from "./cards/agent-card";
import { RoleCard } from "./cards/role-card";
import { SkillCard } from "./cards/skill-card";
import { AgentTable } from "./cards/agent-table";
import { RoleTable } from "./cards/role-table";
import { SkillTable } from "./cards/skill-table";
import { MarkdownPreview } from "./markdown-preview";
import { YamlPreview } from "./yaml-preview";
import { DeployLog } from "./deploy-log";
import { ConfirmDialog } from "./confirm-dialog";
import { DeleteResult } from "./delete-result";

const COMPONENT_MAP: Record<string, Record<string, React.ComponentType<any>>> = {
  agent: {
    created:          AgentCard,
    updated:          AgentCard,
    listed:           AgentTable,       // 表格展示多个 Agent
    deleted:          DeleteResult,     // 删除成功提示
    confirm_required: ConfirmDialog,    // 确认对话框
  },
  role: {
    created:          RoleCard,
    updated:          RoleCard,
    listed:           RoleTable,
    deleted:          DeleteResult,
    confirm_required: ConfirmDialog,
  },
  skill: {
    created:          SkillCard,
    updated:          SkillCard,
    listed:           SkillTable,
    deleted:          DeleteResult,
    confirm_required: ConfirmDialog,
  },
  scope: {
    updated:          MarkdownPreview,  // 展示更新后的 SOUL.md
  },
  commitment: {
    updated:          YamlPreview,      // 展示更新后的 eval.yaml
  },
  deploy: {
    exported:         DeployLog,        // 展示导出日志
  },
};

export function StructuredBlockRenderer({ structured }: { structured: StructuredData }) {
  const Component = COMPONENT_MAP[structured.type]?.[structured.action];
  if (!Component) return null;
  return <Component data={structured.data} />;
}
```

### 6.2 MessageBubble — 消息气泡渲染

```tsx
// app/src/components/message-bubble.tsx

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isUIAction = message.source === "ui_action";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[80%] ${isUser ? "order-last" : ""}`}>

        {/* 用户消息 */}
        {isUser && (
          <div className={
            isUIAction
              ? "text-sm text-gray-400 italic text-right"   // UI 触发 → 轻量样式
              : "bg-blue-500 text-white rounded-lg px-4 py-2" // 手动输入 → 正常气泡
          }>
            {isUIAction && <span className="mr-1">🔧</span>}
            {message.content}
          </div>
        )}

        {/* Agent 消息 */}
        {!isUser && (
          <div className="bg-gray-100 rounded-lg px-4 py-2">
            {/* 文本部分 */}
            {message.content && (
              <div className="prose prose-sm">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}

            {/* 结构化数据部分 → 渲染 Card/Table/Dialog */}
            {message.structured && (
              <div className="mt-2">
                <StructuredBlockRenderer structured={message.structured} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 6.3 UI 触发消息的渲染对比

```
手动输入 (source: "chat"):
┌──────────────────────────────────┐
│                 ┌───────────────┐│
│                 │帮我创建一个    ││
│                 │task-manager   ││  蓝色气泡，正常大小
│                 └───────────────┘│
└──────────────────────────────────┘

UI 触发 (source: "ui_action"):
┌──────────────────────────────────┐
│          🔧 删除 Agent task-manager│  灰色斜体，轻量显示
└──────────────────────────────────┘
```

---

## 7. 完整交互循环示例

### 7.1 场景：用户通过 Chat 创建 Agent → 通过 UI 单个删除

```
时间线:

T1. 用户在 Chat 输入: "创建一个 task-manager Agent"
    source: "chat"
    ↓
    POST /api/chat/send { message: "创建一个 task-manager Agent" }

T2. Agent 响应 (SSE):
    text: "已为你创建 Agent task-manager"
    structured: { type:"agent", action:"created", data:{id:"a1", name:"task-manager", ...} }
    ↓
    Chat Panel 渲染:
    ┌─────────────────────────────────────┐
    │ 🤖 已为你创建 Agent task-manager     │
    │ ┌─────────────────────────────────┐ │
    │ │ ☐ task-manager                  │ │
    │ │   管理团队任务                   │ │
    │ │   Roles: 1  Skills: 1          │ │
    │ │         [详情] [导出] [删除]     │ │  ← ActionButton + checkbox
    │ └─────────────────────────────────┘ │
    └─────────────────────────────────────┘
    ↓
    Dashboard 同步出现 task-manager Card

T3. 用户点击 Card 上的 [删除] 按钮
    ActionButton.handleClick()
    ↓
    sendUIAction({
      entity: "agent",
      action: "delete",
      targets: [{ id: "a1", name: "task-manager", entity: "agent" }]
    })
    ↓
    实际发送: ```ui_action { "entity":"agent", "action":"delete", "targets":[...] } ```
    Chat 显示: 🔧 delete agent: task-manager

T4. Agent 收到 ui_action，根据 SKILL.md 理解意图，响应 (SSE):
    text: "确定要删除 Agent task-manager 吗？将同时删除 1 个角色和 1 个技能。"
    structured: {
      type: "agent",
      action: "confirm_required",
      data: { message: "确定要删除？...", confirm_label: "确认删除", cancel_label: "取消" }
    }
    ↓
    Chat Panel 渲染 ConfirmDialog:
    ┌─────────────────────────────────────┐
    │ 🤖 确定要删除 Agent task-manager？   │
    │    将同时删除 1 个角色和 1 个技能     │
    │                                     │
    │    [确认删除]     [取消]              │
    └─────────────────────────────────────┘

T5. 用户点击 [确认删除]
    sendUIAction({ entity: "_dialog", action: "confirm", targets: [] })
    ↓
    Chat 显示: 🔧 确认

T6. Agent 执行删除，响应 (SSE):
    text: "已删除 Agent task-manager 及其所有关联数据。"
    structured: { type:"agent", action:"deleted", data:{id:"a1", name:"task-manager"} }
    ↓
    Dashboard 移除 task-manager Card
```

### 7.2 场景：多选批量导出

```
T1. 用户在 Dashboard 勾选 3 个 AgentCard 的 checkbox
    → selected: [
        { id:"a1", name:"task-manager", entity:"agent" },
        { id:"a2", name:"chatbot", entity:"agent" },
        { id:"a3", name:"code-assistant", entity:"agent" }
      ]
    → 出现 BatchActionBar: "已选中 3 项  [批量导出] [批量删除]"

T2. 用户点击 [批量导出]
    sendUIAction({
      entity: "agent",
      action: "export",
      targets: [
        { id:"a1", name:"task-manager", entity:"agent" },
        { id:"a2", name:"chatbot", entity:"agent" },
        { id:"a3", name:"code-assistant", entity:"agent" }
      ]
    })
    ↓
    Chat 显示: 🔧 export 3 个 agent: task-manager, chatbot, code-assistant

T3. Agent 收到 ui_action，理解为批量导出，响应:
    text: "正在导出 3 个 Agent..."
    (逐个导出，每完成一个发送一次 structured)
    structured: { type:"deploy", action:"exported", data:{agent_name:"task-manager", files_generated:12} }
    structured: { type:"deploy", action:"exported", data:{agent_name:"chatbot", files_generated:8} }
    structured: { type:"deploy", action:"exported", data:{agent_name:"code-assistant", files_generated:10} }
    text: "全部导出完成。"

T4. Dashboard 中各 Card 显示导出状态
    多选自动清空
```

### 7.3 场景：通过 UI 编辑角色 SOUL.md

```
T1. 用户点击 RoleCard 上的 [编辑] 按钮
    sendUIAction({
      entity: "role",
      action: "edit",
      targets: [{ id:"r2", name:"reviewer", entity:"role", agent_name:"task-manager" }]
    })
    ↓
    Chat 显示: 🔧 edit role: reviewer

T2. Agent 响应:
    text: "以下是 reviewer 角色当前的 SOUL.md 内容："
    structured: {
      type: "role",
      action: "editing",
      data: {
        id: "r2",
        agent_name: "task-manager",
        name: "reviewer",
        soul_md: "# Reviewer\n\n你是审核者..."
      }
    }
    ↓
    Chat Panel 渲染 MarkdownEditor (内联在对话流中):
    ┌─────────────────────────────────────┐
    │ 🤖 以下是 reviewer 当前的 SOUL.md：  │
    │ ┌─────────────────────────────────┐ │
    │ │ # Reviewer                      │ │
    │ │ 你是审核者...                    │ │
    │ └─────────────────────────────────┘ │
    │           [保存]     [取消]          │
    └─────────────────────────────────────┘

T3. 用户在编辑器中修改内容，点击 [保存]
    sendUIAction({
      entity: "role",
      action: "update",
      targets: [{ id:"r2", name:"reviewer", entity:"role", agent_name:"task-manager" }],
      context: { soul_md: "# Reviewer\n\n你是高级审核者..." }
    })

T4. Agent 响应:
    text: "已更新 reviewer 角色的 SOUL.md"
    structured: { type:"role", action:"updated", data:{...} }
```

---

## 8. 后端对双交互模式的支持

后端只需识别 `ui_action` 代码块，将完整消息传给 Agent。Agent 自行理解 UIAction 和自然语言。

```python
# src/app.py

@app.post("/api/chat/send")
async def chat_send(request: ChatSendRequest, user: User = Depends(get_current_user)):
    """
    接收用户消息（自然语言或含 ui_action 的结构化指令）
    统一传给 Agent，Agent 根据 SKILL.md 自行理解
    """
    session = await session_manager.get_or_create(user.id)
    await session.send(request.message)
    return {"status": "ok"}
```

**Agent 处理两种消息的统一逻辑（在 SKILL.md 中指导）：**

```
# Agent 收到的消息有两种形式:

形式 1: 自然语言
  "删除 Agent task-manager"
  → Agent 理解意图，执行对应操作

形式 2: UIAction 结构化指令
  ```ui_action
  { "entity":"agent", "action":"delete", "targets":[{"id":"a1", "name":"task-manager"}] }
  ```
  → Agent 解析 JSON，理解为 "用户要删除 targets 中列出的 Agent"

两种形式进入同一个 Skill 处理流程:
  → 危险操作先返回 confirm_required
  → 收到 { entity:"_dialog", action:"confirm" } 后执行
  → 收到 { entity:"_dialog", action:"cancel" } 后取消
  → 批量操作 (targets.length > 1) 逐个处理并汇报进度
```

**SKILL.md 中的 UIAction 处理指南（添加到每个 manage_* skill 中）：**

```markdown
## UIAction 处理

当消息中包含 ```ui_action 代码块时：

1. 解析 JSON 获取 entity, action, targets, context
2. targets.length === 1 → 等效于对应的单个操作
3. targets.length > 1 → 批量操作:
   - delete: 列出所有目标，请求用户确认后逐个删除
   - export: 逐个导出，每完成一个返回一次 structured
   - detail: 返回所有目标的汇总表格
4. entity === "_dialog" → 确认/取消上一轮操作
5. context 字段包含额外数据（如编辑后的 SOUL.md 内容）
```

---

## 9. 扩展 StructuredData — 新增 action 类型

为支持双交互模式，在原有 action 基础上扩展：

```typescript
interface StructuredData {
  type: "agent" | "role" | "skill" | "scope" | "commitment" | "deploy";
  action:
    | "created"            // 创建成功
    | "updated"            // 更新成功
    | "deleted"            // 删除成功
    | "listed"             // 列表查询
    | "exported"           // 导出成功
    | "confirm_required"   // 需要用户确认 (渲染 ConfirmDialog)
    | "editing";           // 进入编辑模式 (渲染 MarkdownEditor/YamlEditor)
  data: Record<string, any>;
}
```

对应的组件映射表更新：

```typescript
const COMPONENT_MAP = {
  agent: {
    created:          AgentCard,
    updated:          AgentCard,
    listed:           AgentTable,
    deleted:          DeleteResult,
    confirm_required: ConfirmDialog,      // 新增
  },
  role: {
    created:          RoleCard,
    updated:          RoleCard,
    listed:           RoleTable,
    deleted:          DeleteResult,
    confirm_required: ConfirmDialog,      // 新增
    editing:          MarkdownEditor,     // 新增
  },
  skill: {
    created:          SkillCard,
    updated:          SkillCard,
    listed:           SkillTable,
    deleted:          DeleteResult,
    confirm_required: ConfirmDialog,      // 新增
    editing:          MarkdownEditor,     // 新增
  },
  scope: {
    updated:          MarkdownPreview,
    editing:          MarkdownEditor,     // 新增
  },
  commitment: {
    updated:          YamlPreview,
    editing:          YamlEditor,         // 新增
  },
  deploy: {
    exported:         DeployLog,
  },
};
```

---

## 10. 文件清单

实现双交互模式需要创建/修改的文件：

```
app/src/
├── lib/
│   ├── chat-store.ts            # ChatStore (zustand) — 消息管理 + sendMessage + sendUIAction
│   ├── ui-action.ts             # UIAction 类型定义 + 序列化 + 显示格式化
│   ├── entity-updater.ts        # StructuredData → EntityStore 更新
│   └── types.ts                 # Message, StructuredData 等类型定义
│
├── components/
│   ├── chat-panel.tsx           # Chat 面板 (消息列表 + 输入框)
│   ├── message-bubble.tsx       # 消息气泡 (区分 chat/ui_action 来源)
│   ├── structured-block-renderer.tsx  # type+action → 组件分发器
│   ├── action-button.tsx        # 通用操作按钮 (Card 上使用，发送 UIAction)
│   ├── batch-action-bar.tsx     # 批量操作栏 (多选后显示)
│   ├── confirm-dialog.tsx       # 确认对话框 (Agent 请求确认时)
│   ├── delete-result.tsx        # 删除成功提示
│   ├── markdown-editor.tsx      # Markdown 编辑器 (编辑 SOUL.md/SKILL.md)
│   ├── markdown-preview.tsx     # Markdown 预览
│   ├── yaml-editor.tsx          # YAML 编辑器 (编辑 eval.yaml)
│   ├── yaml-preview.tsx         # YAML 预览
│   ├── deploy-log.tsx           # 部署日志
│   └── cards/
│       ├── agent-card.tsx       # Agent 卡片 (含 ActionButton)
│       ├── agent-table.tsx      # Agent 列表
│       ├── role-card.tsx        # Role 卡片 (含 ActionButton)
│       ├── role-table.tsx       # Role 列表
│       ├── skill-card.tsx       # Skill 卡片 (含 ActionButton)
│       └── skill-table.tsx      # Skill 列表
│
└── app/
    └── page.tsx                 # 单页面 (Login / Dashboard+Chat)
```
