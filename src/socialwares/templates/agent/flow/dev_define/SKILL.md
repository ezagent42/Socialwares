---
name: dev_define
description: "Define or redefine four primitives — the core of socialware development"
---

# Define Four Primitives

**开发 Socialware = 定义四原语。** 人类做决策（定义什么），Agent 自动执行（写文件、注册、编译）。

## Trigger

User says "define", "定义", "init", "初始化", "重新定义", "修改原语", "redefine" etc.

## Flow

### Step 0: Assess Current State

先读取当前 `socialware.py` 和 `agent/` 目录，判断：
- **全新项目**（只有模板默认内容）→ 从头引导
- **已有定义**（已经有业务角色/action）→ 展示当前定义，问用户要修改哪部分

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
cat socialware.py
ls agent/role/ agent/scope/ agent/flow/
```

如果已有定义，展示摘要："当前有 X 个角色、Y 个操作、Z 个流转、W 个约束。你要修改哪部分？还是全部重新定义？"

### Step 1: Scope — "这个 App 能做什么？"

1. Ask user: "这个 App 是做什么的？主要功能有哪些？"
2. Based on response, write/update `agent/scope/scope.md`
3. Show the result, confirm with user
4. See `references/four-primitives-guide.md` for scope template

### Step 2: Role — "谁在用这个 App？"

1. Ask user: "有哪些角色会使用这个 App？每个角色的职责是什么？"
2. For each role:
   - Create/update `agent/role/{name}.md`
   - Register in `socialware.py`: `app.role("name", file="agent/role/name.md")`
3. Note: default, dev, evolver 是内置角色，不需要用户定义

### Step 3: Flow — "每个角色能做什么操作？"

1. Ask user: "每个角色能执行哪些操作？"
2. For each action:
   - Create directory: `agent/flow/{action}/` with `scripts/` and `references/` subdirs
   - Create `agent/flow/{action}/SKILL.md` with trigger + flow
   - Register in `socialware.py`: `app.action("name", role=[...])`
3. **引导理解流转**：问 "这些操作之间有没有固定的流转顺序？比如：任务必须先创建，再提交，再审核——不能跳过某个步骤。"
   - 用生活化的比喻："就像做饭要先洗菜再切菜再炒菜，不能直接炒没洗的菜。"
   - If yes, help define:
     ```python
     flow = app.flow("task_lifecycle", resource="task")
     flow.states("draft", "submitted", "reviewed")  # 任务经过的阶段
     flow.transition("draft", "submit_task", "submitted", role=["default"])
     # 意思：任务在 draft 状态时，default 角色执行 submit_task，任务变为 submitted
     ```
   - If confused: "状态就是任务现在在哪个阶段。流转就是谁能把它推到下一个阶段。没有流转的操作（比如查看列表）随时都能用。"
   - If no fixed order: skip, all actions are direct actions
4. SKILL.md 只需写基本的 trigger + flow。详细编写可用 skill-creator（通过 "setup claude" 获取）

### Step 4: Commitment — "角色之间怎么协作？"

**这是最难理解的部分，需要耐心引导。**

1. 先判断是否需要：
   - "App 里有没有需要多人协作的场景？比如一个人提交了东西，另一个人需要在一定时间内处理？"
   - If only one role or no time constraints: skip
   - If yes: continue

2. 用具体场景引导：
   - "想象一下：{角色A} 做了 {操作A}，你期望 {角色B} 在什么条件下做 {操作B}？"
   - 举例："比如外卖场景：顾客下单后（from），骑手应该在 30 分钟内取餐（to + condition）。超时了，系统提醒骑手（on_violation）。"
   - 说明作用："这些规则定了后，evolver 角色会自动检测是否被遵守。"

3. For each commitment:
   ```python
   app.commitment("C1",
       from_=("default", "submit_task"),     # 谁做了什么
       to=("reviewer", "review_task"),        # 谁应该做什么
       condition="within 24h",                # 什么条件下
       on_violation=("reviewer", "remind_review"),  # 违反了怎么办
   )
   ```

4. 用白话翻译确认："当 default 提交任务后，reviewer 应该在 24 小时内审核。没有就触发 remind_review。"

### Step 5: Deploy + Verify

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

Show compile result (roles, skills per role), confirm everything correct.

## Important

- **先看再改**：每次都先展示当前状态，再问要改什么
- After each step, show what was written, ask for confirmation
- Go step by step, don't write all files at once
- Use the user's language (Chinese or English based on input)
- After deploy: "现在可以用 `socialwares start --role default` 测试，或用 `socialwares start --role evolver` 检查质量"
