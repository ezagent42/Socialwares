---
name: review_task
description: "Review a task"
---
# Review Task
## Trigger
User says "review task", "审核任务" etc.
## Flow
1. GET /api/tasks?status=submitted
2. Review and approve/reject
3. POST /api/tasks/{id}/review
