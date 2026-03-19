---
name: query_task
description: "查询任务 — 列出或查询特定任务"
---

# 查询任务

## 触发

用户说 "查看任务"、"我的任务"、"任务列表" 等。

## 流程

1. 确定查询方式: 全部 / 按 ID / 按状态
2. 调用 API: `GET /tasks` 或 `GET /tasks/{id}`
3. 格式化展示结果

## API

```bash
# 全部
curl http://localhost:8001/tasks

# 按 ID
curl http://localhost:8001/tasks/task-001

# 按状态
curl http://localhost:8001/tasks?status=submitted
```
