---
name: create_task
description: "Create a new task"
---
# Create Task
## Trigger
User says "create task", "新建任务" etc.
## Flow
1. Ask for task title
2. POST /api/tasks {"title": "..."}
3. Return task ID
