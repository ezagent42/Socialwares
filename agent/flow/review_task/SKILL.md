---
name: review_task
description: "审核任务 — 审核提交的任务，批准或拒绝"
---

# 审核任务

## 触发

用户说 "审核任务"、"review task"、"批准/拒绝 task-xxx" 等。

## 流程

1. 查询待审核任务: `GET /tasks?status=under_review`
2. 展示任务详情给用户
3. 获取用户决定 (approve/reject + reason)
4. 调用 API: `POST /tasks/{id}/review`
5. 返回审核结果

## API

```bash
curl -X POST http://localhost:8001/tasks/{id}/review \
  -H "Content-Type: application/json" \
  -H "X-Identity: $IDENTITY" \
  -d '{"decision": "approve|reject", "reason": "..."}'
```
