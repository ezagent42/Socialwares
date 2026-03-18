# 多 Agent 场景编排

YAML 格式定义多 agent 协作场景。

## 用法

```bash
./scripts/launch-scenario.sh scenarios/examples/task-review.yaml
```

## 格式

```yaml
name: scenario-name
description: "场景描述"

bus:
  type: local
  endpoint: localhost:8080

agents:
  - name: agent-name
    template: agent/agents/template-dir
    adapter: claude|codex|kimicode
    roles: [taskarena:R1]
    auto_start: true

workflow:
  - agent-name: "/command arg1 arg2"
```
