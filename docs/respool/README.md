# ResPool — 资源池管理 Socialware App

> 基于四原语的资源池管理应用，底层对接 OneSystem 混合基础设施平台。

## 定位

ResPool 是 OneSystem 资源分配能力的 **Agent 交互可视化层**。OneSystem 已实现全部后端逻辑（分配、容量、计费、状态机），ResPool 通过 `one` CLI 包装为对话式操作。

## 四原语概览

| 原语 | 文件 | 说明 |
|------|------|------|
| Scope | `agent/scope/scope.md` | ResPool 能力边界：资源池浏览、分配管理、费用查看 |
| Role | `agent/role/default.md` | 资源消费者（P1-P4），admin 在 P5 引入 |
| Commitment | `agent/commitment/commitment.yaml` | P3 阶段填入：分配响应时间、审批 SLA |
| Flow | `agent/flow/flow.yaml` + Skills | 渐进增长，P1 → P5 |

## 渐进路径

详见 [implementation-log.md](implementation-log.md)。

## 底层依赖

- OneSystem API：`https://one-system.h2os.cloud/api/v1`
- OneSystem CLI：`one`（需预先 `one login` 完成认证）
- 参考规范：`.claude/skills/one-system/`
