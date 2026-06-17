---
name: import_agent
description: "Import Agent config from shared package"
---

# Import Agent

## Trigger

用户提到导入某个 Agent 配置包时触发。

## Flow

1. 接收导入来源
2. 解析配置包，提取四原语:
   - agent/role/*.md → roles 表
   - agent/scope/scope.md → scopes 表
   - agent/flow/*/SKILL.md + flow.yaml → skills + skill_roles 表
   - agent/commitment/commitment.yaml → commitments 表
3. 检查名称冲突
4. 写入数据库
5. 返回导入结果

## Structured Response

- type: "agent"
- action: "created"
- data: { id, name, source: "imported" }

## Error Handling

- 名称冲突: 提示重命名
- 格式错误: 提示缺失的必要文件
