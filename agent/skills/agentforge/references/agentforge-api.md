# AgentForge API Reference

## Endpoints

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | /agents/spawn | 从模板创建 agent | R2 |
| GET | /agents | 列出所有 agent | any |
| GET | /agents/{name} | 查询单个 agent | any |
| POST | /agents/{name}/wake | 唤醒 sleeping agent | R2 |
| POST | /agents/{name}/sleep | 休眠 agent | R2 |
| POST | /agents/{name}/destroy | 销毁 agent | R2 |
| PUT | /agents/{name}/config | 配置 agent | R1 |
| GET | /templates | 列出可用模板 | any |

## Flow State Machine

```
created → active ⇄ sleeping → destroyed
```

## Request/Response Examples

### Spawn Agent

```json
POST /agents/spawn
{
  "template": "code-reviewer",
  "name": "reviewer-1",
  "adapter": "claude"
}

Response:
{
  "name": "reviewer-1",
  "template": "code-reviewer",
  "status": "created",
  "adapter": "claude",
  "owner": "alice:Alice@local",
  "parent": null,
  "created_at": "2026-03-18T10:00:00Z"
}
```
