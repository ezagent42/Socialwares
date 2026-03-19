---
name: check_health
description: "检查 App 健康状态"
---

# 检查健康状态

## 触发

用户说 "检查状态"、"health check"、"App 是否正常" 等。

## 流程

1. 调用 App API: `GET /health`
2. 返回状态信息

## API

```bash
curl http://localhost:8001/health
```
