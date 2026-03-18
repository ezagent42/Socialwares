# Socialware 核心概念

## Socialware App

Socialware App 是面向 agent 的协作应用。每个 App 是独立软件，
通过 HTTP API 暴露功能，agent 通过四原语进行调用。

## 四原语

- **Role**: 谁能做什么 (权限)
- **Flow**: 事情怎么推进 (状态机)
- **Commitment**: 什么时候必须做完 (SLA)
- **Arena**: 谁能看到 (作用域)

## 三层架构

- **L0 感知层**: Side Panel 提示，#CRUD 标注
- **L1 组织层**: /action 命令，pre_send 权限检查，Flow 状态机
- **App 工具层**: /action:func 命令，工具实际执行

## 当前 Apps

- **TaskArena**: 任务 CRUD + 审核流程
- **AgentForge**: Agent 生命周期管理 + 多平台适配
