# ResPool Demo 测试流程

> 从零开始走完 ResPool 全流程的分步指南，包含测试数据、环境准备和验证步骤。

---

## 目录

- [环境要求](#环境要求)
- [Step 0: 准备 OneSystem 测试数据](#step-0-准备-onesystem-测试数据)
- [Step 1: Deploy + 启动 ResPool](#step-1-deploy--启动-respool)
- [Step 2: P1 — 浏览资源池](#step-2-p1--浏览资源池)
- [Step 3: P2 — 搜索 + 分配 + 释放](#step-3-p2--搜索--分配--释放)
- [Step 4: P3 — 监控 + Commitment 验证](#step-4-p3--监控--commitment-验证)
- [Step 5: P4 — 批量分配 + 费用报表 + 推荐](#step-5-p4--批量分配--费用报表--推荐)
- [Step 6: P5 — Admin 审批 + 结算 + 争议](#step-6-p5--admin-审批--结算--争议)
- [清理](#清理)

---

## 环境要求

### 必需

| 组件 | 要求 | 检查命令 |
|------|------|----------|
| Python | >= 3.12 | `python --version` |
| uv | 最新版 | `uv --version` |
| OneSystem CLI | `one` 已安装 | `one --version` |
| OneSystem 服务端 | 可访问（本地或远程） | `one login` 后 `one whoami` |
| Claude Code | 已安装（TUI 模式需要） | `claude --version` |

### OneSystem 认证

```bash
# 配置上下文（如果首次使用）
one config set-context demo \
  --server https://one-system.h2os.cloud \
  --oneauth-url https://one-auth.h2os.cloud \
  --user <your-username>

# 登录
one login -u <your-username> -p <your-password>

# 验证
one whoami
```

### 如果没有 OneSystem 服务端

本 demo 的对话测试仍然有效——Agent 会尝试执行 `one` 命令，根据返回结果（成功或失败）做出相应回复。你可以验证 Agent 是否正确调用了对应的 CLI 命令。

---

## 关于启动方式的说明

本 demo 使用的是 **Dev 调试模式**（`cd workspace && make start`），直接进入 workspace 目录启动 Agent TUI。这是当前项目的实际状态。

在 Socialware 的最终用户体验中，ResPool 应该通过以下方式被使用（**尚未实现**）：

```
最终用户体验（待建）:
  用户打开 Chat → "/respool show pools" → Agent 已加载 ResPool 能力 → 返回结果

App 间协作（待建）:
  TaskArena Agent → "/zchat respool: 帮我查 GPU 资源" → ResPool Agent 响应

App 发现（待建）:
  Dashboard 或 "/socialware list" → 列出所有已注册的 App（ResPool, TaskArena, ...）
```

当前缺少的层：

| 层 | 状态 | 说明 |
|---|------|------|
| Dev 调试（`cd` + `make start`） | ✅ 本 demo 使用 | 开发者直接操作 workspace |
| 用户路由（`/respool`） | ❌ 待建 | 通过路径唤起特定 App 的 Agent |
| App 注册 + 发现 | ❌ 待建 | 多个 App 的集中注册和列表 |
| App 间通信（`/zchat`） | ❌ 待建 | Agent 间 P2P 委派 |

这些属于 Socialware 平台层能力（P0 回环），不是 ResPool 单个 App 的职责。当平台层就绪后，本 demo 的测试步骤可直接复用，只是启动方式从 `make start` 变为平台路由唤起。

---

## Step 0: 准备 OneSystem 测试数据

### 0.1 创建测试 Namespace

```bash
one ns create demo-pool
one ns use demo-pool
```

### 0.2 导入测试资源

本目录提供了完整的测试资源 YAML，一键导入：

```bash
# 从项目根目录执行
one apply -f docs/respool/demo/resources/ -n demo-pool
```

或逐个导入：

```bash
one apply -f docs/respool/demo/resources/gpu-servers.yaml -n demo-pool
one apply -f docs/respool/demo/resources/datasets.yaml -n demo-pool
one apply -f docs/respool/demo/resources/licenses.yaml -n demo-pool
one apply -f docs/respool/demo/resources/pool-config.yaml -n demo-pool
one apply -f docs/respool/demo/resources/quotas.yaml -n demo-pool
```

### 0.3 验证数据

```bash
# 查看池
one pool list

# 查看资源
one get bms -n demo-pool
one get ds -n demo-pool
one get lic -n demo-pool

# 查看配额
one get cfg -q "label.respool.type:quota" -n demo-pool
```

---

## Step 1: Deploy + 启动 ResPool（Dev 调试模式）

```bash
# 进入 ResPool workspace（Dev 调试模式：直接进目录操作）
cd .socialware/workspace/h2os/respool

# 安装依赖
uv sync

# 部署四原语 → .runtime/
make deploy

# 验证部署
ls .runtime/agents/
# 预期: default/  dev/  evolver/  admin/

# 启动 Agent（default 角色）
make start ROLE=default
```

---

## Step 2: P1 — 浏览资源池

在 Agent 对话中输入以下内容，验证响应：

### 测试 2.1: 健康检查

```
> check health
```

**预期**：Agent 调用 `GET /health`，返回 `{"status": "ok"}`

### 测试 2.2: 查看资源池

```
> show me available pools
```

**预期**：Agent 执行 `one pool list`，展示 demo-pool 及其资源概况

### 测试 2.3: 查看池内资源

```
> what resources are in demo-pool?
```

**预期**：Agent 执行 `one pool get demo-pool`，展示 GPU 服务器、数据集、License 列表

---

## Step 3: P2 — 搜索 + 分配 + 释放

### 测试 3.1: 搜索资源

```
> find GPU servers with at least 4 available capacity
```

**预期**：Agent 执行 `one get bms -q "spec.capacity.available>=4"`，展示 gpu-farm-01 和 gpu-farm-02

### 测试 3.2: 费用估算

```
> how much would 4 A100-hours cost on gpu-farm-01?
```

**预期**：Agent 读取 gpu-farm-01 的 `spec.pricing`（per_unit, 8 USDT/A100-hour），计算 4 × 8 = 32 USDT

### 测试 3.3: 创建分配

```
> allocate 4 A100s from gpu-farm-01 for 2 hours, purpose: LLM training
```

**预期**：
1. Agent 先展示费用估算（32 USDT），请求确认
2. 确认后执行 `one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --duration 2h --purpose "LLM training"`
3. 展示分配名称（如 alloc-xxxxxx）、租约时间、费用

### 测试 3.4: 查看分配

```
> show my allocations
```

**预期**：Agent 执行 `one alloc list`，展示刚创建的分配（phase: active）

### 测试 3.5: 分配详情

```
> show details of alloc-xxxxxx
```
（替换为实际分配名）

**预期**：Agent 执行 `one alloc get alloc-xxxxxx`，展示完整信息

### 测试 3.6: 释放分配

```
> release alloc-xxxxxx, I'm done
```

**预期**：
1. Agent 请求确认释放
2. 执行 `one alloc release alloc-xxxxxx --reason completed`
3. 展示最终账单（invoice_amount）和释放确认

### 测试 3.7: 容量不足场景

```
> allocate 100 A100s from gpu-farm-01
```

**预期**：Agent 尝试创建，OneSystem 返回 409（capacity insufficient），Agent 告知用户可用容量并建议减少数量

---

## Step 4: P3 — 监控 + Commitment 验证

### 测试 4.1: 容量预警

```
> check capacity alerts
```

**预期**：Agent 执行 `one pool list` + `one pool get`，检查每个资源的 available/total 比率，报告是否有低容量资源

### 测试 4.2: 租约提醒

先创建一个带 duration 的分配：
```
> allocate 2 A100s from gpu-farm-01 for 30 minutes
```

然后：
```
> check for expiring allocations
```

**预期**：Agent 列出即将到期的分配及剩余时间

### 测试 4.3: Pending 审批提醒

如果 gpu-farm-03 设置了 `require_manual_confirm: true`：
```
> allocate 1 unit from gpu-farm-03
```

```
> any overdue pending approvals?
```

**预期**：Agent 显示 pending 状态的分配及等待时间

---

## Step 5: P4 — 批量分配 + 费用报表 + 推荐

### 测试 5.1: 资源推荐

```
> I need to train an LLM model, budget is 100 USDT, need at least 4 GPUs for 4 hours
```

**预期**：Agent 搜索可用资源，按价格/容量排序，推荐 top 3 选项

### 测试 5.2: 批量分配

```
> allocate 4 A100s from gpu-farm-01 for 2 hours AND 1 access to imagenet-2024
```

**预期**：
1. Agent 展示两项费用估算
2. 确认后逐一创建分配
3. 汇总展示成功/失败

### 测试 5.3: 费用报表

```
> show my cost report
```

**预期**：Agent 列出所有分配按 phase 分组，展示 active/released/settled 的费用汇总

---

## Step 6: P5 — Admin 审批 + 结算 + 争议

### 6.0 切换到 Admin 角色

```bash
# 另起一个终端
cd .socialware/workspace/h2os/respool
make start ROLE=admin
```

### 测试 6.1: 审批 Pending 分配

在 admin Agent 中：
```
> show pending allocations and approve them
```

**预期**：Agent 列出 pending 分配，逐个审批（`one alloc approve <name>`）

### 测试 6.2: 结算 Released 分配

```
> settle all released allocations
```

**预期**：Agent 列出 released 分配，逐个标记 settled（`one alloc settle <name>`）

### 测试 6.3: 配额管理

```
> set quota for alice to max 3 active allocations
```

**预期**：Agent 创建 Config 资源 `respool-quota-alice`，`spec.max_active_allocations: 3`

```
> show all quotas
```

**预期**：Agent 查询 `one get cfg -q "label.respool.type:quota"`，展示所有配额

### 测试 6.4: 争议流程

回到 default 角色 Agent：
```
> dispute alloc-xxxxxx, reason: overcharged, actual usage was less
```

**预期**：Agent 执行 `one alloc dispute alloc-xxxxxx --reason "overcharged"`

回到 admin Agent：
```
> show disputed allocations and resolve them
```

**预期**：Admin 查看争议原因，决定后重新 settle

---

## 清理

```bash
# 删除测试分配
one alloc list -n demo-pool -o json | jq -r '.items[].metadata.name' | xargs -I{} one alloc release {} 2>/dev/null
one alloc list --phase released -n demo-pool -o json | jq -r '.items[].metadata.name' | xargs -I{} one alloc settle {}

# 删除测试资源
one delete -f docs/respool/demo/resources/gpu-servers.yaml
one delete -f docs/respool/demo/resources/datasets.yaml
one delete -f docs/respool/demo/resources/licenses.yaml
one delete -f docs/respool/demo/resources/pool-config.yaml
one delete -f docs/respool/demo/resources/quotas.yaml

# 删除测试 namespace
one ns delete demo-pool
```
