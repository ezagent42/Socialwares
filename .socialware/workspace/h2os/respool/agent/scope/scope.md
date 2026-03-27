# ResPool — 资源池管理

资源池管理 Socialware App，底层对接 OneSystem 混合基础设施平台。用户通过对话管理计算资源的分配、使用和释放。

## Capabilities

- 资源池浏览：查看所有可用资源池及容量状态
- 资源搜索：按类型、标签、容量、价格搜索可分配资源
- 分配管理：创建、查看、释放资源分配
- 费用查看：分配的费用估算和历史账单
- 容量预警：资源池余量不足时主动提醒

## Boundaries

- 不直接操作底层资源（BareMetalServer/VM/Container 的创建删除由 OneSystem admin 完成）
- 不管理用户权限（RBAC 由 OneSystem Namespace 机制处理）
- 不处理支付（费用计算由 OneSystem 完成，结算走外部流程）
- 不管理 Secret（密钥管理由 OneSystem Secret 机制处理）
- 不执行 SSH 远程访问（由 OneSystem `one ssh` 完成）

## Connections

- OneSystem API (`https://api.h2os.cloud/api/v1`) — 资源 CRUD + 分配操作
- OneSystem CLI (`one`) — Agent 通过 Bash 调用 `one` 命令操作资源
- OneAuth — 用户认证（`one login` 预先完成）
