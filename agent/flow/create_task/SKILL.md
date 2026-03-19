---
name: create_task
description: "创建新任务 — 调用 TaskArena API 创建任务并设为 draft 状态"
---

# 创建任务

## 触发

用户说 "创建任务"、"新建任务"、"添加任务" 等。

## 流程

1. 从用户输入提取: 标题、描述、预算 (可选)
2. 调用 API: `POST /tasks`
3. 返回创建结果

## API

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -H "X-Identity: $IDENTITY" \
  -d '{"title": "...", "description": "..."}'
```
