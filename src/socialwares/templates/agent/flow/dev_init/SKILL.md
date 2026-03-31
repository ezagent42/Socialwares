---
name: dev_init
description: "Guide first-time development — build four primitives step by step"
---

# Initialize App (First-time Development Guide)

## Trigger

User says "开始开发", "初始化", "guide me", "init", "get started" etc.

## Flow

Guide the user through building four primitives step by step:

### Step 1: Scope — 定义 App 能做什么

1. Ask user: "这个 App 是做什么的？主要功能有哪些？"
2. Based on response, write `agent/scope/scope.md`
3. Show the result, confirm with user

### Step 2: Role — 定义谁在用这个 App

1. Ask user: "有哪些角色会使用这个 App？每个角色的职责是什么？"
2. For each role, create `agent/role/{name}.md`
3. Register in `socialware.py`: `app.role("name", file="agent/role/name.md")`

### Step 3: Flow — 定义每个角色能做什么操作

1. Ask user: "每个角色能执行哪些操作？"
2. For each action:
   - Create directory: `agent/flow/{action}/` with `scripts/` and `references/` subdirs
   - Create `agent/flow/{action}/SKILL.md` with trigger + flow
   - Register in `socialware.py`: `app.action("name", role=[...])`
3. **引导理解流转**：问 "这些操作之间有没有固定的流转顺序？比如：任务必须先创建，再提交，再审核——不能跳过某个步骤。"
   - 用生活化的比喻帮助理解："就像做饭要先洗菜再切菜再炒菜，不能直接炒没洗的菜。"
   - If yes, help define:
     ```python
     flow = app.flow("task_lifecycle", resource="task")
     flow.states("draft", "submitted", "reviewed")  # 任务经过的阶段
     flow.transition("draft", "submit_task", "submitted", role=["default"])
     # 意思：任务在 draft 状态时，default 角色执行 submit_task，任务变为 submitted
     ```
   - If user is confused, explain: "状态就是任务现在在哪个阶段。流转就是谁能把它推到下一个阶段。没有流转的操作（比如查看列表）随时都能用。"
   - If no fixed order: skip this, all actions are direct actions (随时可用)
4. Note: SKILL.md 只需写基本的 trigger + flow 即可。详细编写可以后续用 skill-creator（通过 "setup claude" 获取）

### Step 4: Commitment — 定义协作约束

**这是最难理解的部分，需要耐心引导。**

1. 先判断是否需要 commitment：
   - 问 "App 里有没有需要多人协作的场景？比如一个人提交了东西，另一个人需要在一定时间内处理？"
   - If only one role or no time constraints: skip, 不需要 commitment
   - If yes: continue

2. 用具体场景引导：
   - "好的。现在想象一下：{角色A} 做了 {操作A}，你期望 {角色B} 在什么条件下做 {操作B}？"
   - 举例帮助理解："比如在外卖场景里：顾客下单后（from），骑手应该在 30 分钟内取餐（to + condition）。如果超时了，系统提醒骑手（on_violation）。"
   - 说明 commitment 的作用："这些规则你定了之后，evolver 角色会自动检测是否被遵守。违反时可以触发提醒操作。"

3. For each commitment, add to `socialware.py`:
   ```python
   app.commitment("C1",
       from_=("default", "submit_task"),     # 谁做了什么
       to=("reviewer", "review_task"),        # 谁应该做什么
       condition="within 24h",                # 什么条件下（自然语言，evolver 用 AI 判断）
       on_violation=("reviewer", "remind_review"),  # 违反了怎么办
   )
   ```

4. 确认用户理解：展示写好的 commitment，用白话翻译一遍："当 default 提交任务后，reviewer 应该在 24 小时内审核。如果没有，就触发 remind_review 提醒。"

### Step 5: Deploy + Verify

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

Show the compile result (roles, skills per role) and confirm everything looks correct.

## Important

- After each step, show the user what was written and ask for confirmation
- Don't write all files at once — go step by step
- Use the user's language (Chinese or English based on their input)
- After deploy, suggest: "现在可以用 `socialwares start --role default` 测试业务角色"
