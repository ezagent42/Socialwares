# ResPool 实施记录

> 记录每个 Phase 的规划、创建的文件、变更内容。

---

## Phase 规划总览

| Phase | 目标 | 新增 Skill | 状态 |
|-------|------|-----------|------|
| **P1** | 最小可用：能查资源池 | list_pools | ✅ 完成 |
| **P2** | 核心分配功能 | search_resources, request_allocation, list_allocations, get_allocation, release_allocation, estimate_cost | ✅ 完成 |
| **P3** | Commitment + 监控 | capacity_alert, lease_reminder | ✅ 完成 |
| **P4** | 扩大能力 | batch_allocate, cost_report, recommend_resource | ✅ 完成 |
| **P5** | Admin 角色 + 管理 | approve_allocation, settle_allocation, dispute_allocation, manage_quota | ✅ 完成 |

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

## P2: 核心分配功能（2026-03-28）

### 目标

从"只能看"到"能用"——用户可以搜索资源、创建分配、查看分配、释放分配、估算费用。启用 Allocation 状态机。

### 创建的文件

```
新增（workspace 实例 .socialware/workspace/h2os/respool/）:
  agent/flow/search_resources/SKILL.md      — 按类型/标签/容量/价格搜索资源
  agent/flow/request_allocation/SKILL.md    — 创建资源分配
  agent/flow/list_allocations/SKILL.md      — 列出分配（支持 phase/consumer 过滤）
  agent/flow/get_allocation/SKILL.md        — 查看分配详情
  agent/flow/release_allocation/SKILL.md    — 释放分配（触发计费）
  agent/flow/estimate_cost/SKILL.md         — 费用估算（不创建分配）

修改（workspace 实例）:
  agent/flow/flow.yaml                      — 注册 6 个新 action + 启用 F1 状态机
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 状态机执行层 | OneSystem 服务端 | 状态转换由 OneSystem API 强制执行（违反返回 400），flow.yaml 中的 F1 是声明性的 |
| request 前确认 | Agent 先展示估价再创建 | 避免误操作，分配创建后即扣减容量 |
| release 前确认 | Agent 确认当前用量和费用 | 释放不可逆，且触发最终计费 |
| estimate 独立 Skill | 不合并到 request 中 | 用户可能只想看价格，不一定要分配 |
| 状态机 transitions 含 admin 操作 | 声明但 P2 不实现 admin Skill | 声明完整路径，admin Skill 在 P5 实现 |

### 新增 6 个 Skill：

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

## P3: Commitment + 监控（2026-03-28）

### 目标

从"能用"到"有保障"——填充 commitment 评估标准，新增容量预警和租约提醒。

### 创建的文件

```
新增:
  agent/flow/capacity_alert/SKILL.md        — 资源池容量预警
  agent/flow/lease_reminder/SKILL.md        — 租约到期 + pending 审批超时提醒

修改:
  agent/commitment/commitment.yaml          — 填入 C1-C5 真实 commitment
  agent/flow/flow.yaml                      — 注册 capacity_alert, lease_reminder
```

### Commitment 定义

| ID | 条件 | 触发违规 |
|----|------|----------|
| C1 | 新建分配 5s 内出现在列表中 | evolver diagnose |
| C2 | 释放后 10s 内 invoice 计算完成 | evolver diagnose |
| C3 | 分配创建前展示费用估算 | — |
| C4 | pending 分配 24h 内审批 | lease_reminder |
| C5 | 有 lease.end 的分配到期前释放 | lease_reminder |

---

## P4: 扩大能力（2026-03-28）

### 目标

从"基础分配"到"完整工作流"——批量分配、费用报表、智能推荐。

### 创建的文件

```
新增:
  agent/flow/batch_allocate/SKILL.md        — 一次分配多个资源
  agent/flow/cost_report/SKILL.md           — 费用报表（按 phase/类型/时间分组）
  agent/flow/recommend_resource/SKILL.md    — 基于需求和预算推荐资源

修改:
  agent/flow/flow.yaml                      — 注册 batch_allocate, cost_report, recommend_resource
  agent/scope/scope.md                      — 新增推荐、批量、报表能力
```

---

## P5: Admin 角色 + 管理（2026-03-28）

### 目标

从"消费者视角"到"完整管理"——新增 admin 角色，实现审批/结算/争议/配额管理。

### 创建的文件

```
新增:
  agent/role/admin.md                       — 资源池管理员角色
  agent/flow/approve_allocation/SKILL.md    — 审批 pending 分配
  agent/flow/settle_allocation/SKILL.md     — 标记 released 为 settled
  agent/flow/dispute_allocation/SKILL.md    — 发起账单争议
  agent/flow/manage_quota/SKILL.md          — 查看/设置/删除配额

修改:
  agent/flow/flow.yaml                      — 注册 4 个 admin Skill + admin 角色权限
```

### 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| admin 角色权限 | 只管理分配生命周期和配额 | 底层资源（BMS/VM 创建删除）仍由 OneSystem admin 完成 |
| dispute 发起者 | default 角色 | 消费者对自己的账单提出争议 |
| dispute 解决者 | admin 重新 settle | F1 状态机：disputed → settled |
| 配额存储 | Config 资源 + label respool.type:quota | 复用 OneSystem 原生资源模型 |
