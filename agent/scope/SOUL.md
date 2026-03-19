# TaskArena

任务管理 Socialware App。通过 Agent 驱动的 Chat 界面管理任务生命周期。

## 能力

- 任务 CRUD (创建、查询、更新、关闭)
- 审核流程 (提交 → 审核 → 批准/拒绝)
- 角色权限管理 (admin, submitter, reviewer)
- SLA 追踪 (审核 72h 超时)

## 边界

- 仅管理任务生命周期，不涉及项目管理
- 不处理文件存储，通过 Arena 成员身份控制访问
- 跨 App 协作通过 /zchat 委托
