---
name: manage_skill
description: "Add, edit, list, delete skills for an Agent"
---

# Manage Skill

## Trigger

用户提到为某个 Agent 添加、编辑、查看、删除技能时触发。

## Prerequisites

必须先确定目标 Agent。

## Flow

### Create
1. 提取技能名称和描述
2. 确定角色权限（未指定则默认 default 角色）
3. 调用 `skill_crud.create_skill(agent_id, name, skill_md, role_ids, description)`

### Update
1. 支持更新 SKILL.md 内容和/或角色权限
2. 调用 `skill_crud.update_skill(skill_id, skill_md, role_ids)`

### List
1. 调用 `skill_crud.list_skills(agent_id)`（含关联角色）

### Delete
1. 调用 `skill_crud.delete_skill(skill_id)`

## Structured Response

- type: "skill"
- action: "created" | "updated" | "listed" | "deleted"

## Constraints

- 技能名在同一 Agent 内唯一
- 至少关联一个角色
