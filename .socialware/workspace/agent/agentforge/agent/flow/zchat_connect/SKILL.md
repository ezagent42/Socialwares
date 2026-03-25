---
name: zchat_connect
description: "Connect to another Socialware App via ZChat for inter-agent communication"
---

# ZChat Connect

Connects to another Socialware App via the ZChat protocol, discovers its capabilities, and sends inter-agent messages.

## Trigger

User says "connect to", "zchat", "talk to another app", "send message to", etc.

## Flow

1. Ask for the target App URL (e.g. https://taskarena.socialware.app)
2. Call the target App's discover endpoint to learn its capabilities
3. Display the target's soul (what it can do)
4. Ask what intent/message to send
5. Send the message via ZChat API
6. Display the response

## Available APIs

Discover another App's capabilities (call against the TARGET app's URL):

```bash
curl https://{target-app-url}/zchat/discover
# → {"app": "...", "soul": "..."}
```

Discover your own App's capabilities:

```bash
curl http://localhost:8001/zchat/discover
# → {"app": "...", "soul": "..."}
```

Send a message to another App:

```bash
curl -X POST http://localhost:8001/zchat/send \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://taskarena.socialware.app",
    "from": "agentforge.app/agentforge",
    "to": "taskarena.app/default",
    "intent": "create_role",
    "payload": {"name": "notifier"}
  }'
# → {"status": "sent"}
```

Receive a message from another App (handled automatically, but can be called directly):

```bash
curl -X POST http://localhost:8001/zchat/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from": "taskarena.app/default",
    "to": "agentforge.app/agentforge",
    "intent": "status_update",
    "payload": {"status": "complete"}
  }'
# → {"status": "received"}
```

## File Operations

This skill does not modify files. All communication is handled via APIs.
