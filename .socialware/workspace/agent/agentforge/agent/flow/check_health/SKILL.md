---
name: check_health
description: "Check App health status"
---

# Check Health Status

Checks whether the App backend is running and responding correctly.

## Trigger

User says "check status", "health check", "is the App running", etc.

## Flow

1. Call the health API to check if the App is running
2. Return status information to the user

## Available APIs

Check App health:

```bash
curl http://localhost:8001/health
# → {"status": "ok"}
```

Check available adapters (extended health check):

```bash
curl http://localhost:8001/adapters
# → {"adapters": [{"name": "claude", "available": true}, ...]}
```

Check active session:

```bash
curl http://localhost:8001/session
# → {"active": true/false, "role": "...", "adapter": "..."}
```

## File Operations

This skill does not modify files. All data is retrieved via APIs.
