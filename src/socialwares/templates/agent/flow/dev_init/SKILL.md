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
3. Ask: "这些操作之间有没有固定的流转顺序？"
   - If yes, define flow in `socialware.py`

### Step 4: Commitment — 定义协作约束

1. Ask user: "角色之间有没有需要遵守的协作规则？比如'提交后 24 小时内必须审核'"
2. For each commitment, add to `socialware.py`:
   ```python
   app.commitment("C1", from_=(...), to=(...), condition="...")
   ```

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
