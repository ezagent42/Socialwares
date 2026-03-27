---
name: OneSystem Integration
description: OneSystem 平台职能、资源模型、HTTP API、EventBus 事件参考。其他项目对接 OneSystem 时使用。
---

# OneSystem Integration Overview

## 平台职能

OneSystem 是 **混合基础设施统一管理平台**，核心职责：

| 职能 | 说明 |
|------|------|
| **资源声明式管理** | 以 K8s 风格 YAML 声明物理机、虚拟机、容器、密钥等资源 |
| **多租户隔离** | Namespace + RBAC（viewer/editor/admin）实现资源隔离 |
| **密钥管理** | SOPS 加密存储，owner-only 解密策略 |
| **SSH 远程访问** | 密码/Teleport 证书双模式，SSHFS 反向隧道 |
| **EventBus 扩展** | 资源生命周期事件驱动外部系统同步（Teleport、Incus）|
| **统一 CLI** | `one` CLI 工具覆盖所有操作（详见 `onesystem-cli.md`）|
| **RBAC 权限控制** | 三层权限模型（详见 `rbac-permissions.md`）|

---

## 资源模型（KRM 风格）

所有资源遵循 Kubernetes Resource Model，统一结构：

```yaml
apiVersion: v1
kind: <PascalCase Kind>    # 必须为注册表中的合法 Kind
metadata:
  name: <string>           # 资源名，同 kind+namespace 下唯一
  namespace: <string>      # 所属 namespace（默认 user-<username>）
  owner: <string>          # 自动设为创建者
  labels:                  # 可选标签
    env: prod
    role: worker
spec: { ... }              # 资源规格（因 Kind 而异）
status: { ... }            # 运行时状态（可选）
data: { ... }              # 仅 Secret 使用，SOPS 加密
```

### 资源唯一键

`kind + metadata.name + metadata.namespace` 三元组全局唯一。

### 注册的资源类型

| Kind (body) | Resource (URL) | CLI 别名 | 用途 |
|-------------|---------------|----------|------|
| `Secret` | `secrets` | `secret`, `sec` | SSH 密码、凭证，SOPS 加密存储 |
| `VM` | `vms` | `vm` | 虚拟机 |
| `Container` | `containers` | `container` | Docker 容器 |
| `Machine` | `machines` | `machine`, `mach` | 通用节点 |
| `BareMetalServer` | `baremetalservers` | `bms` | 物理服务器 |
| `Config` | `configs` | `config`, `cfg` | 配置项 |
| `HostNode` | `hostnodes` | `node`, `hn` | 物理/虚拟主机节点 |
| `IncusInstance` | `incusinstances` | `incusinstance`, `ii` | Incus LXC/VM |
| `ECS` | `ecs` | — | 云主机（阿里云 ECS 等）|
| `User` | `users` | `user` | 用户 |
| `Allocation` | `allocations` | `alloc` | ResPool 资源分配 |
| `Document` | `documents` | `doc` | 文档（设计文档、合同、报告）|
| `Image` | `images` | `img` | 图片（截图、设计稿、诊断图）|
| `Dataset` | `datasets` | `ds` | 数据集（训练数据、日志归档）|
| `Artifact` | `artifacts` | `art` | 构建产物（二进制、模型权重）|
| `License` | `licenses` | `lic` | 许可证（软件 License、证书）|

> **规则**: YAML body 中 `kind` 必须为 PascalCase（如 `Secret`），API URL 使用小写复数形式（如 `/secrets`）。

---

## HTTP API 参考

**Base URL**: `https://api.h2os.cloud/api/v1` (或自定义 `SERVER_HOST:SERVER_PORT`)

### 认证

所有 API（除 auth 和 health）需 Bearer Token：

```
Authorization: Bearer <access_token>
```

Token 通过 OneAuth OAuth2 流程获取（详见 `oneauth-integration.md`）。

---

### Auth 接口（公开）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/auth/login-native` | 原生登录（仅内部/开发） |
| `POST` | `/api/v1/auth/refresh` | 刷新 Token |
| `POST` | `/api/v1/auth/logout` | 登出 |
| `GET` | `/api/v1/auth/me` | 获取当前用户信息（需认证） |

---

### Resource CRUD 接口（需认证）

所有资源类型共享统一的 REST 接口，URL 中 `{resource}` 为小写资源名（如 `secrets`、`machines`）。

| Method | Path | 说明 | 请求体 |
|--------|------|------|--------|
| `POST` | `/api/v1/{resource}` | 创建资源 | 完整资源 YAML/JSON |
| `GET` | `/api/v1/{resource}` | 列出资源 | Query: `?page=&size=&fields=` |
| `GET` | `/api/v1/{resource}/{name}` | 获取单个资源 | Query: `?fields=metadata,spec` |
| `PUT` | `/api/v1/{resource}/{name}` | 更新资源 | 完整资源 YAML/JSON |
| `DELETE` | `/api/v1/{resource}/{name}` | 删除资源 | — |
| `POST` | `/api/v1/{resource}/{name}/move` | 跨 Namespace 转移 | `{"to_namespace":"x","from_namespace":"y"}` |
| `POST` | `/api/v1/resources/search` | OneQL 搜索 | `{"kind":"*","query":"label.env:prod"}` |

#### 创建资源示例

```bash
curl -X POST https://api.h2os.cloud/api/v1/secrets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "v1",
    "kind": "Secret",
    "metadata": {"name": "db-password", "namespace": "team-ops"},
    "data": {"password": "mySecretPass"}
  }'
```

#### OneQL 搜索语法

```bash
curl -X POST https://api.h2os.cloud/api/v1/resources/search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "kind": "BareMetalServer",
    "query": "namespace:team-ops label.env:prod spec.cpu>=4"
  }'
```

OneQL 支持的操作符：`:` (等于), `!=`, `>`, `>=`, `<`, `<=`, `~` (包含)
支持的字段：`namespace`, `owner`, `name`, `label.<key>`, `spec.<key>`（spec 支持任意深度嵌套，如 `spec.pricing.unit_price`）

**排序**：在 query 中加 `--sort field:asc,field2:desc`

---

### Secret 工具接口（需认证）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/secrets/encrypt` | SOPS 加密 |
| `POST` | `/api/v1/secrets/decrypt` | SOPS 解密 |
| `POST` | `/api/v1/secrets/generate-password` | 生成随机密码 |
| `POST` | `/api/v1/secrets/generate-keypair` | 生成 SSH 密钥对 |

> **安全规则**: Secret 资源的 `data` 字段中 `__sops__` 元数据仅对 owner 可见。非 owner 获取 Secret 时 `__sops__` 字段会被过滤。

---

### SSH 证书接口（需认证，Teleport）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/ssh/cert` | 请求 SSH 证书（Teleport Certificate Bridge） |
| `GET` | `/api/v1/ssh/health` | 证书服务健康检查 |

---

### Namespace 接口（需认证）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/namespaces` | 创建 Namespace |
| `GET` | `/api/v1/namespaces` | 列出可见 Namespace |
| `GET` | `/api/v1/namespaces/{name}` | 获取 Namespace 详情 |
| `POST` | `/api/v1/namespaces/{name}/members` | 添加成员 |
| `DELETE` | `/api/v1/namespaces/{name}/members/{userId}` | 移除成员 |
| `DELETE` | `/api/v1/namespaces/{name}` | 删除 Namespace（仅 owner） |

---

### 健康检查（公开）

```bash
curl https://api.h2os.cloud/health
# {"status":"healthy","version":"v1.0.0"}
```

---

## EventBus 事件

外部系统可通过 EventBus 订阅资源生命周期事件：

| 事件 | 触发时机 | Payload |
|------|----------|---------|
| `resource.created` | 资源创建后 | `*models.Resource` |
| `resource.updated` | 资源更新后 | `*models.Resource` |
| `resource.deleted` | 资源删除后 | `*models.Resource` |
| `allocation.released` | Allocation 释放（含自动过期） | `*models.Resource` |
| `namespace.member_added` | 成员加入 NS | `{namespace, user_id, role}` |
| `namespace.member_removed` | 成员移除 NS | `{namespace, user_id}` |

---

## 集成指南

### 方式一：HTTP API 对接

1. 通过 OneAuth 获取 Access Token（详见 `oneauth-integration.md`）
2. 使用 Bearer Token 调用上述 REST API
3. 资源数据格式遵循 KRM YAML/JSON 规范

### 方式二：CLI 脚本集成

```bash
# 在 CI/CD 中使用
one apply -f deployment-resources/*.yaml -n production
one get secret db-creds -o json | jq '.data.password'
```

完整 CLI 参考见 `onesystem-cli.md`。
