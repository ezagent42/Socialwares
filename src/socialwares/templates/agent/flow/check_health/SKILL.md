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
Call the app's health endpoint: `GET /health`

The base URL and port depend on your app configuration (see `src/app.py`).
The agent should discover the correct URL from the project configuration.
