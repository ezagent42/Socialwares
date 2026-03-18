---
name: taskarena
description: "TaskArena Socialware App — 任务 CRUD、状态机、角色权限、SLA 追踪"
---

# TaskArena

任务管理 Socialware App。通过四原语 (Role/Flow/Commitment/Arena) 管理任务生命周期。

## Commands

| 命令 | 说明 | 需要角色 |
|------|------|----------|
| /taskarena create | 创建任务 | R2 (提交者) |
| /taskarena update | 更新任务 | R2 (提交者) |
| /taskarena review | 审核任务 | R3 (审核者) |
| /taskarena query | 查询任务 | 所有角色 |
| /taskarena close | 关闭任务 | R1 (管理员) |

## 四原语

### Role (角色)

- R1 管理员: propose, assign, review, close, force_resolve
- R2 提交者: propose, submit, update
- R3 审核者: review, comment

### Flow (状态机)

```
draft → [propose] → submitted → [review] → under_review
     → [approve] → approved → [close] → closed
     → [reject] → rejected → [resubmit] → submitted
```

### Commitment (承诺)

- C1: 审核者在任务提交后 72h 内完成审核
- C2: 管理员在 C1 违约后 24h 内 force_resolve

### Arena (作用域)

- min: 2 人
- 基于 Room 成员身份

## Usage

```bash
# 创建任务
uv run agent/skills/taskarena/scripts/create_task.py --title "GPS采购" --budget 300000

# 查询任务
uv run agent/skills/taskarena/scripts/query_task.py --id task-001

# 审核任务
uv run agent/skills/taskarena/scripts/review_task.py --id task-001 --decision approve

# 更新任务
uv run agent/skills/taskarena/scripts/update_task.py --id task-001 --status under_review
```
