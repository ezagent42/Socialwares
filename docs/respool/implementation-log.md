# ResPool 实施记录

> 记录每个 Phase 的规划、创建的文件、变更内容。

---

## Phase 规划总览

| Phase | 目标 | 新增 Skill | 状态 |
|-------|------|-----------|------|
| **P1** | 最小可用：能查资源池 | list_pools | 进行中 |
| **P2** | 核心分配功能 | search_resources, request_allocation, list_allocations, get_allocation, release_allocation, estimate_cost | 待开始 |
| **P3** | Commitment + 监控 | capacity_alert, lease_reminder | 待开始 |
| **P4** | 扩大能力 | batch_allocate, cost_report, recommend_resource | 待开始 |
| **P5** | 加 admin 角色 | approve_allocation, settle_allocation, dispute_allocation, manage_quota | 待开始 |

---

## P1: 最小可用（2026-03-27）

### 目标

从空壳 App 到"能查资源池的 ResPool"——用户可以通过对话查看可用资源池及容量。

### 规划内容

| 操作 | 文件 | 说明 |
|------|------|------|
| 更新 | `agent/scope/scope.md` | 填入 ResPool 定位、能力、边界 |
| 更新 | `agent/role/default.md` | 明确资源消费者角色 |
| 创建 | `agent/flow/list_pools/SKILL.md` | 查看资源池列表 |
| 更新 | `agent/flow/flow.yaml` | 注册 list_pools action |
| 创建 | `docs/respool/README.md` | ResPool 概览 |
| 创建 | `docs/respool/implementation-log.md` | 本文件 |

### 创建的文件

```
新增（template 根目录，设计文档）:
  docs/respool/README.md                    — ResPool 概览
  docs/respool/implementation-log.md        — 实施记录（本文件）

新增（workspace 实例 .socialware/workspace/h2os/respool/）:
  agent/flow/list_pools/SKILL.md            — 查看资源池 Skill

修改（workspace 实例）:
  agent/scope/scope.md                      — 填入 ResPool 定位
  agent/role/default.md                     — 明确资源消费者角色
  agent/flow/flow.yaml                      — 注册 list_pools

template 根目录的 agent/ 保持通用空壳不变。
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 调用方式 | `one` CLI（Bash） | OneSystem CLI 已有完整实现，无需重复开发 HTTP 封装 |
| 认证方式 | 预登录（`one login` 预先完成） | P1 简单可用，单 workspace |
| 是否加 API endpoint | 否 | Agent 直接用 `one` CLI，不经过 src/app.py |
| admin 角色 | 不引入 | P1 只需 default 消费者角色 |

### 验证方式

```bash
# deploy + 启动
make deploy && make start ROLE=default

# 用户对话
> "show me available pools"
> "list resource pools"
→ Agent 执行 one pool list → 返回格式化池列表
```

---

## P2: 核心分配功能（待开始）

### 预规划

新增 6 个 Skill：

| Skill | 触发词 | OneSystem 命令 |
|-------|--------|---------------|
| `search_resources` | "search for GPU", "find servers" | `one get <kind> -q "..."` |
| `request_allocation` | "allocate 4 GPUs", "request resources" | `one alloc create --resource <kind/name> --amount <n>` |
| `list_allocations` | "show my allocations", "what am I using" | `one alloc list [--phase] [--consumer]` |
| `get_allocation` | "show allocation details" | `one alloc get <name>` |
| `release_allocation` | "release my allocation", "I'm done" | `one alloc release <name>` |
| `estimate_cost` | "how much would it cost", "estimate" | 读取 `spec.pricing` + 计算 |

同步扩充：
- `eval_cases.yaml`：每个 Skill 一条 API 测试（通过 `one` CLI 输出验证）
- `conversation_tests/default.yaml`：每个 Skill 3 条（正向/边界/质量）
- `commitment.yaml`：暂不填入（P3 阶段）

### 预规划状态机

```yaml
# flow.yaml — P2 阶段启用
flows:
  F1:
    name: allocation_lifecycle
    resource: allocation
    description: "Resource allocation from request to settlement"
    states: [pending, active, released, settled, disputed]
    transitions:
      - { from: pending,  action: approve_allocation,  to: active,   role: [admin] }
      - { from: active,   action: release_allocation,  to: released, role: [default] }
      - { from: released, action: settle_allocation,   to: settled,  role: [admin] }
      - { from: settled,  action: dispute_allocation,  to: disputed, role: [default] }
      - { from: disputed, action: settle_allocation,   to: settled,  role: [admin] }
```

> 注：状态机在 OneSystem 服务端强制执行（违反返回 400）。flow.yaml 中的定义是声明性的，告诉 Agent 和 evolver 合法路径。

---

## P3: Commitment + 监控（待开始）

### 预规划

commitment.yaml 填入：
```yaml
commitments:
  C1:
    from: { role: default, action: request_allocation }
    to:   { role: default, action: allocation_confirmed }
    condition: "allocation creation response within 5 seconds"
  C2:
    from: { role: default, action: release_allocation }
    to:   { role: default, action: release_confirmed }
    condition: "release + invoice calculation within 10 seconds"
```

新增 Skill：
- `capacity_alert`：资源池余量低于阈值时提醒
- `lease_reminder`：分配即将到期时提醒

---

## P4/P5: 扩展（待开始）

P4：批量分配、费用报表、资源推荐
P5：admin 角色 + 审批/结算/争议/配额管理
