---
name: check_health
description: "Check App health status"
---

# Check Health Status

## Trigger

User says "check status", "health check", "is the App running", etc.

## Flow

1. Call the App API: `GET /health`
2. Return status information

## API

```bash
curl http://localhost:8001/health
```
