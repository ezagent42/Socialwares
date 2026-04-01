---
name: manage_commitment
description: "View and update an Agent's eval metrics"
---

# Manage Commitment

## Trigger

用户提到查看或修改某个 Agent 的评估指标时触发。

## Flow

### Get
1. 调用 `commitment_crud.get_commitment(agent_id)`

### Update
1. 修改 commitment.yaml，遵循 unified schema:
   ```yaml
   commitments:
     C1:
       from: { role: X, action: Y }
       to:   { role: A, action: B }
       condition: "自然语言评估标准"
       on_violation: null
   ```
2. 调用 `commitment_crud.update_commitment(agent_id, commitment_yaml)`

## Structured Response

- type: "commitment"
- action: "updated"
