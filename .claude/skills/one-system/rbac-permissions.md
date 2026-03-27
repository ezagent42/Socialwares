# OneSystem RBAC 权限模型参考

> 面向上层服务（AI Agent、集成平台、第三方客户端）的 OneSystem 角色、权限和操作行为完整参考。

---

## 角色体系概览

OneSystem 采用 **三层权限模型**：

| 层级 | 范围 | 角色 | 来源 |
|------|------|------|------|
| 全局角色 | 系统级 | `superadmin`, `admin`, `user` | Token 验证 + 角色解析 |
| Namespace 角色 | Namespace 级 | `admin`, `editor`, `viewer` | Namespace 成员表 |
| 资源所有权 | 资源级 | owner / non-owner | `metadata.owner` (OneAuth UUID) |

权限判定顺序：**全局角色 → Namespace 角色 → 资源所有权**

---

## 1. 全局角色 (Global Roles)

### `superadmin` — 超级管理员

**获取方式**：当前通过手机号硬编码匹配（`pkg/middleware/auth.go`），未来对接 OneAuth RBAC claims。

**权限范围**：

| 操作 | 权限 | 说明 |
|------|------|------|
| 创建任意资源 | ✅ 无限制 | 可在任意 namespace 创建 |
| 读取任意资源 | ✅ 无限制 | 跨 namespace 查看所有资源 |
| 更新任意资源 | ✅ 无限制 | 包括其他用户的资源 |
| 删除任意资源 | ✅ 无限制 | — |
| 解密 Secret | ✅ 无限制 | 可解密所有 Secret |
| 管理 Namespace | ✅ 无限制 | 创建、删除、管理成员 |
| 移动资源 | ✅ 无限制 | 跨 namespace 移动 |
| SSH 连接 | ✅ 无限制 | 可 SSH 到任意资源 |
| Teleport 证书 | ✅ 无限制 | 签发任意用户证书 |
| 查看所有 Namespace | ✅ | `one ns list` 返回全部 |
| `one get *` 通配查询 | ✅ | 全类型、全 namespace |

**API 行为**：
- `GET /resources` — 不附加 owner 过滤，返回所有资源
- `GET /namespaces` — 返回所有 namespace
- `POST /secrets/decrypt` — 无解密限制
- `POST /ssh/cert` — 可为任意用户签发证书

---

### `admin` — 管理员

**获取方式**：未来通过 OneAuth RBAC claims 分配，当前未启用（预留）。

**权限范围**：

| 操作 | 权限 | 说明 |
|------|------|------|
| 创建资源 | ✅ | 可在任意 namespace 创建 |
| 读取资源 | ✅ | 跨 namespace 查看所有资源 |
| 更新资源 | ✅ | 所有资源 |
| 删除资源 | ✅ | 所有资源 |
| 解密 Secret | ⚠️ 需所有权或 namespace 成员 | 非 superadmin 需额外校验 |
| 管理 Namespace | ✅ | — |
| RequireRole("admin") | ✅ | 通过 admin 级中间件 |
| RequireRole("superadmin") | ❌ | 不通过 |

**与 superadmin 区别**：`RequireRole("superadmin")` 不通过，Secret 解密需更细粒度校验。

---

### `user` — 普通用户（默认角色）

**获取方式**：所有未匹配 superadmin/admin 的用户默认为 `user`。

**权限范围**：

| 操作 | 权限 | 条件 |
|------|------|------|
| 创建资源 | ✅ | 仅在自己的 namespace 或有 editor+ 角色的 namespace |
| 读取自有资源 | ✅ | `metadata.owner` 匹配自己的 OneAuth UUID |
| 读取 namespace 资源 | ✅ | 是该 namespace 的成员（viewer+） |
| 更新资源 | ⚠️ | 需为 owner 或 namespace editor+ |
| 删除资源 | ⚠️ | 需为 owner 或 namespace admin |
| 解密 Secret | ⚠️ | 需为 owner 或 namespace editor+ |
| 管理 Namespace | ⚠️ | 仅管理自己创建的 namespace |
| 查看 Namespace | ⚠️ | 仅自己是成员的 namespace |
| SSH 连接 | ⚠️ | 仅有权限的资源 |
| `one get *` 通配查询 | ⚠️ | 仅返回自有 + namespace 可见资源 |
| `--all-namespaces` 跨 NS | ✅ | 返回个人 NS + 已加入共享 NS 的资源 |

**API 行为**：
- `GET /resources` — 自动附加 namespace 过滤
- `GET /resources?all_namespaces=true` — 返回个人 NS + 所有已加入共享 NS（`IN` 查询）
- `GET /namespaces` — 仅返回自己是成员的 namespace
- 默认 namespace 为 `user-{userID}` (个人 namespace)

---

## 2. Namespace 角色 (Namespace-Level Roles)

每个 Namespace 有独立的成员列表和角色：

| Namespace 角色 | 读取 | 写入 | 删除 Namespace | 管理成员 | 解密 Secret |
|----------------|------|------|----------------|----------|-------------|
| `viewer` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `editor` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ |

**注意**：Namespace 角色仅在该 Namespace 内生效，不影响其他 Namespace 或全局权限。

### Namespace 操作权限矩阵

| 操作 | superadmin | admin(全局) | ns-admin | ns-editor | ns-viewer | 非成员 |
|------|-----------|-------------|----------|-----------|-----------|--------|
| 查看 namespace 资源 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 创建资源 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 更新资源 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 删除资源 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 解密 Secret | ✅ | ⚠️ | ✅ | ✅ | ❌ | ❌ |
| 添加成员 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 删除 namespace | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 3. API 端点权限清单

### 公开端点（无需认证）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/auth/login-native` | POST | Native CLI 登录 |
| `/api/v1/auth/refresh` | POST | Token 刷新 |
| `/api/v1/auth/logout` | POST | 登出 |
| `/api/internal/policy/evaluate` | POST | Teleport 策略评估（内部） |

### 认证端点（需 Bearer Token）

| 端点 | 方法 | 最低权限 | 说明 |
|------|------|----------|------|
| `/api/v1/auth/me` | GET | user | 获取当前用户信息 + 角色 |
| `/api/v1/secrets/encrypt` | POST | user | 加密字符串 |
| `/api/v1/secrets/decrypt` | POST | user + 所有权 | 解密字符串 |
| `/api/v1/secrets/generate-password` | POST | user | 生成随机密码 |
| `/api/v1/secrets/generate-keypair` | POST | admin | Age 密钥对生成说明 |
| `/api/v1/ssh/cert` | POST | user | 签发 Teleport SSH 证书 |
| `/api/v1/ssh/health` | GET | user | Teleport 连接状态 |
| `/api/v1/sshca/cert` | POST | user | 签发 step-ca SSH 证书 |
| `/api/v1/sshca/health` | GET | user | step-ca 连接状态 |
| `/api/v1/sshca/ca-keys` | GET | user | 获取 CA 公钥（用于 sshd 配置） |
| `/api/v1/sshca/principals/:login` | GET | user | 解析 principal 列表（AuthorizedPrincipalsCommand） |
| `/api/v1/sshca/sessions` | POST | user | 上传 SSH 会话录制（asciinema .cast） |
| `/api/v1/sshca/sessions` | GET | user | 列出 SSH 会话录制 |
| `/api/v1/sshca/sessions/:id` | GET | user | 获取会话详情 |
| `/api/v1/sshca/sessions/:id/replay` | GET | user | 获取会话回放（.cast 文件） |
| `/api/v1/sshca/sessions/:id` | DELETE | user | 删除会话录制 |
| `/api/v1/resources/search` | POST | user | OneQL 全文搜索资源 |
| `/api/v1/:resource` | POST | user + 写权限 | 创建资源 |
| `/api/v1/:resource` | GET | user + 读权限 | 列出资源（自动过滤） |
| `/api/v1/:resource/:name` | GET | user + 读权限 | 获取单个资源 |
| `/api/v1/:resource/:name` | PUT | user + 写权限 | 更新资源 |
| `/api/v1/:resource/:name` | DELETE | user + 删除权限 | 删除资源 |
| `/api/v1/:resource/:name/move` | POST | user + 源/目标权限 | 移动资源 |
| `/api/v1/namespaces` | POST | user | 创建 namespace |
| `/api/v1/namespaces` | GET | user | 列出可访问的 namespace |
| `/api/v1/namespaces/:name` | GET | user | 获取 namespace 详情（含成员） |
| `/api/v1/namespaces/:name/members` | POST | ns-admin | 添加成员 |
| `/api/v1/namespaces/:name/members/:userId` | DELETE | ns-admin | 移除成员 |
| `/api/v1/namespaces/:name` | DELETE | ns-admin / owner | 删除 namespace |

### Admin 端点（需 admin/superadmin 角色）

> 使用 `AdminOnly()` 中间件，仅 `admin` 或 `superadmin` 角色可访问。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/admin/stats` | GET | 聚合资源统计（总数、按 kind、namespaces、users、活跃 allocations） |
| `/api/v1/admin/stats/capacity` | GET | ResPool 容量概览（按 namespace 聚合 CPU/Memory/GPU） |
| `/api/v1/admin/stats/namespaces` | GET | 各 namespace 资源数量统计 |
| `/api/v1/admin/audit-logs` | GET | 审计日志查询（支持 action/kind/namespace/user_id/from/to 过滤） |
| `/api/v1/admin/bulk/delete` | POST | 批量删除资源（按 ID 列表 + kind） |
| `/api/v1/admin/bulk/move` | POST | 批量移动资源到目标 namespace |
| `/api/v1/admin/drivers` | GET | 驱动健康状态（VM/Container/ECS/Incus/Machine/BMS） |
| `/api/v1/admin/eventbus/stats` | GET | EventBus 运行统计 |

### SPA 前端路由

| 路径 | 说明 |
|------|------|
| `/` | 重定向到 `/console` |
| `/console`, `/console/*` | 主控制台 SPA |
| `/admin`, `/admin/*` | 管理后台 SPA |

---

## 4. CLI 命令权限对照

### 所有角色可用

```bash
one login                    # 登录
one logout                   # 登出
one whoami                   # 查看当前身份和角色
one config ...               # 配置管理（纯本地）
one secret gen-key           # 生成密钥（纯本地）
one secret encrypt <text>    # 加密（服务端）
```

### user 角色（受限）

```bash
one apply -f resource.yaml          # 仅自有 namespace 或有 editor+ 角色
one get <type> [name]               # 仅自有 + namespace 可见资源
one get <type> --all-namespaces     # 查看个人 NS + 所有已加入共享 NS 的资源
one delete <type> <name>            # 仅自有资源
one edit <type> <name>              # 仅自有资源
one patch <type> <name> ...         # 仅自有资源
one label <type> <name> ...         # 仅自有资源
one ssh <name>                      # 仅有权限的资源
one secret decrypt <text>           # 仅自有 Secret
one ns create <name>                # 可创建
one ns list                         # 仅自己是成员的
one ns add-member ...               # 仅自己是 ns-admin 的
one ns use <name>                   # 仅自己是成员的
one move <type> <name> --to <ns>    # 需在源和目标 namespace 都有权限
one alloc create ...                # 仅自己有权限的 namespace 内资源
one alloc release ...               # 仅自己的 allocation
one pool list                       # 搜索 pool-config Config（需读权限）
one pool get <ns>                   # 查看池资源（需对该 namespace 有读权限）
```

### superadmin 角色（无限制）

```bash
one apply -f resource.yaml -n any-namespace   # 任意 namespace
one get <type>                                 # 全局无过滤
one get "*"                                    # 全类型通配
one delete <type> <name>                       # 任意资源
one ssh <name>                                 # 任意资源
one ssh --cert <name>                          # step-ca 证书（任意 namespace principal）
one secret decrypt <text>                      # 任意 Secret
one ns list                                    # 所有 namespace
one ns delete <name>                           # 任意 namespace
one ns add-member <ns> <user> --role admin     # 任意 namespace
one move <type> <name> --to <ns>               # 无限制跨 namespace
```

---

## 5. 资源所有权规则

### 自动赋予所有权

| 场景 | `metadata.owner` 值 |
|------|---------------------|
| `one apply` 创建资源 | 当前用户的 OneAuth UUID (`user_id`) |
| YAML 中指定 `metadata.owner` | 使用 YAML 中的值（superadmin 可指定他人） |
| JIT 用户创建（首次登录） | OneAuth UUID |

### 所有权判定逻辑

```
是否有权操作资源?
  ├─ 全局角色 = superadmin/admin? → ✅ 允许
  ├─ metadata.owner = 当前 user_id? → ✅ 允许
  ├─ 用户是资源所在 namespace 的成员?
  │   ├─ viewer → ✅ 读取 / ❌ 写入
  │   ├─ editor → ✅ 读写 / ❌ 删除
  │   └─ admin  → ✅ 全部
  └─ 以上都不满足 → ❌ 403 Forbidden
```

---

## 6. 特殊资源的权限规则

### Secret（机密资源）

| 操作 | 权限要求 |
|------|----------|
| 创建 | 标准写权限 |
| 列出（metadata only） | 标准读权限 |
| 获取（含解密） | owner 或 namespace editor+ 或 superadmin |
| 更新 | 标准写权限 |
| 删除 | 标准删除权限 |

**关键区别**：`viewer` 角色可看到 Secret 的元数据（name, labels），但 **不能解密** `stringData` 内容。

### HostNode（系统发现资源）

| 操作 | 权限要求 |
|------|----------|
| 自动发现（DiscoveryController） | 系统内部操作，无需用户权限 |
| 读取 | 已认证用户 |
| 删除/更新 | superadmin 或 admin |

### Allocation（资源分配）

| 操作 | 权限要求 |
|------|----------|
| `alloc create` | 需对目标资源有读权限 + namespace 写权限 |
| `alloc release` | owner 或 superadmin |
| `alloc approve` | superadmin 或资源 namespace admin |
| `alloc settle` | superadmin 或资源 namespace admin |
| `alloc dispute` | owner |

---

## 7. Teleport SSH 权限（AccessBinding 策略层）

Teleport 证书颁发通过独立的 **策略评估引擎**（`/api/internal/policy/evaluate`）控制：

```
用户请求 SSH 证书 → OneSystem 查询 AccessBinding → 返回 Teleport 角色列表 → 签发含角色的证书
```

### AccessBinding 模型

```yaml
apiVersion: v1
kind: AccessBinding
metadata:
  name: alice-gpu-access
spec:
  subject:
    kind: User
    name: <oneauth-uuid>      # 必须是 OneAuth UUID
  resource:
    kind: BareMetalServer
    labelSelector:
      matchLabels:
        env: gpu
  role:
    name: ssh-admin            # Teleport 角色名
```

**注意**：AccessBinding 仅影响 Teleport SSH 角色分配，不影响 OneSystem CRUD 权限。

---

## 8. 审计日志

所有资源和认证操作通过 EventBus → AuditAdapter 自动记录到 `audit_logs` 表。

### 记录的操作类型

| Action | 触发场景 |
|--------|---------|
| `create` | 资源创建 |
| `update` | 资源更新 |
| `delete` | 资源删除 |
| `login` | 用户登录 |
| `logout` | 用户登出 |
| `bulk_delete` | Admin 批量删除 |
| `bulk_move` | Admin 批量移动 |
| `namespace_create` | 创建 namespace |
| `namespace_delete` | 删除 namespace |
| `member_add` | 添加 namespace 成员 |
| `member_remove` | 移除 namespace 成员 |

### 审计日志字段

| 字段 | 说明 |
|------|------|
| `timestamp` | 操作时间 |
| `user_id` | OneAuth UUID |
| `user_email` | 用户邮箱 |
| `action` | 操作类型 |
| `kind` | 资源 Kind |
| `name` | 资源名称 |
| `namespace` | Namespace |
| `detail` | 附加上下文（JSONB） |
| `ip` | 客户端 IP |

### 查询审计日志

```bash
# 仅 admin/superadmin 可查询
# 支持过滤参数: action, kind, namespace, user_id, from, to
GET /api/v1/admin/audit-logs?action=delete&namespace=team-ops&from=2026-03-01T00:00:00Z
```

---

## 9. 错误响应参考

| HTTP 状态码 | 含义 | 常见原因 |
|-------------|------|----------|
| 401 Unauthorized | 未认证 | Token 缺失、过期、无效 |
| 403 Forbidden | 权限不足 | 角色不匹配、非 owner、非 namespace 成员 |
| 404 Not Found | 资源不存在 | 或无权限查看（对普通用户等同于不存在） |
| 409 Conflict | 资源冲突 | Allocation 容量不足、资源名重复 |

### 常见 403 排查

```bash
# 1. 确认当前角色
one whoami

# 2. 确认资源所有权
one get <type> <name> -o json | jq '.metadata.owner'

# 3. 确认 namespace 成员身份
one ns get <namespace>

# 4. superadmin 确认（手机号匹配）
# 当前硬编码在 pkg/middleware/auth.go
```

---

## 10. 当前限制与演进计划

### 当前限制

1. **角色来源**：superadmin 通过手机号硬编码匹配，未接入 OneAuth RBAC claims
2. **admin 角色**：已预留但当前无分配入口（OneAuth 不返回 role claim）
3. **AccessBinding**：仅用于 Teleport SSH 角色分配，不影响 CRUD 权限
4. **资源级 ACL**：无细粒度字段级权限（如只读某些 spec 字段）
5. **SSH 会话录制权限**：当前所有已认证用户均可上传/查看会话录制，无细粒度控制

### 演进方向

1. OneAuth v4 接入 RBAC claims → token 中携带角色
2. AccessBinding 扩展到 CRUD 权限控制
3. 组织（Organization）级权限层级
4. SSH 会话录制权限细化（按 namespace/owner 过滤）
