# TaskArena API Reference

## Endpoints

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | /tasks | 创建任务 | R2 |
| GET | /tasks | 查询任务列表 | any |
| GET | /tasks/{id} | 查询单个任务 | any |
| PUT | /tasks/{id} | 更新任务 | R2 |
| POST | /tasks/{id}/review | 审核任务 | R3 |
| POST | /tasks/{id}/close | 关闭任务 | R1 |

## Flow State Machine

```
draft → submitted → under_review → approved → closed
                                 → rejected → submitted (resubmit)
```

## Request/Response Examples

### Create Task

```json
POST /tasks
{
  "title": "GPS设备采购",
  "budget": 300000,
  "description": "采购50台车载GPS设备"
}

Response:
{
  "id": "task-001",
  "title": "GPS设备采购",
  "status": "draft",
  "created_by": "alice:Alice@local",
  "created_at": "2026-03-18T10:00:00Z"
}
```

### Review Task

```json
POST /tasks/task-001/review
{
  "decision": "reject",
  "reason": "缺安装售后条款"
}

Response:
{
  "id": "task-001",
  "status": "rejected",
  "review": {
    "decision": "reject",
    "reason": "缺安装售后条款",
    "reviewer": "bob:Bob@local",
    "reviewed_at": "2026-03-18T12:00:00Z"
  }
}
```
