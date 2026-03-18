# agent/ — Placeholder

**Status: DO NOT IMPLEMENT YET**

This module is reserved for the Agent logic layer. Implementation is pending the
GitAgent interface definition from the team.

## Why this exists

`api/agent_bridge.py` currently calls the Anthropic SDK directly. Once the Agent
interface is defined, `agent_bridge.invoke()` will delegate to this module instead
of calling the SDK directly.

## Interface Contract

When implementing this module, export:

```python
from agent_bridge import AgentRequest, AgentResponse

async def invoke(request: AgentRequest) -> AgentResponse:
    ...
```

The `AgentRequest` / `AgentResponse` types in `api/agent_bridge.py` are the stable
contract. Do not change them without coordinating with the API layer.

## Directory Structure (RSCF)

| Directory | RSCF Primitive | Purpose |
|---|---|---|
| `Role/` | Role | Agent capability envelopes |
| `Scope/` | Arena | Boundary and permission configs |
| `Commitment/` | Commitment | Delivery obligation templates |
| `Flow/` | Flow | State machine / process definitions |
