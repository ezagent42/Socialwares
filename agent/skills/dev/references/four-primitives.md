# 四原语参考

## Role (角色)

角色定义参与者的权限。每个 SW App 定义自己的角色。

```yaml
roles:
  R1:
    name: admin
    permissions: [create, read, update, delete, close]
  R2:
    name: operator
    permissions: [create, read, update]
  R3:
    name: observer
    permissions: [read]
```

pre_send hook 根据角色检查权限：发送者没有权限 → 消息被拒绝。

## Flow (状态机)

状态机定义实体的生命周期。

```yaml
flow:
  name: entity_lifecycle
  states: [draft, active, closed]
  transitions:
    - from: draft
      to: active
      action: activate
      role: R1
```

每个 transition 指定: from 状态、to 状态、触发 action、需要的 role。

## Commitment (承诺)

SLA 定义和超时追踪。

```yaml
commitments:
  C1:
    description: "审核者在提交后 72h 内完成审核"
    trigger_state: submitted
    deadline_hours: 72
    escalation_role: R1
```

L1 层: 记录违约但不自动追踪。
App 层: Verifier Node 自动追踪超时并升级。

## Arena (作用域)

定义谁能参与、谁能看到。

```yaml
arena:
  min_members: 2
  scope: room        # room | global | custom
  open: false        # 是否允许非成员加入
```
