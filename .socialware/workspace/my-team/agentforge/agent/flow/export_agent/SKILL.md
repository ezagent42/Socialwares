---
name: export_agent
description: "Export Agent config to shareable package"
---

# Export Agent

## Trigger

用户提到导出、发布某个 Agent 时触发。

## Flow

1. 确定目标 Agent
2. 调用 `export.export_agent(agent_id, output_dir)`
3. 从 DB 读取配置，生成标准四原语文件结构:
   - roles 表 → agent/role/{name}.md
   - scopes 表 → agent/scope/scope.md
   - skills 表 → agent/flow/{name}/SKILL.md
   - commitments 表 → agent/commitment/commitment.yaml
   - flow.yaml 自动生成
4. 返回导出结果

## Structured Response

- type: "deploy"
- action: "exported"
- data: { agent_name, output_dir, files_generated }
