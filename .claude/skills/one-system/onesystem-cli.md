# OneSystem CLI (`one`) — 对接参考手册

> 面向第三方项目集成 OneSystem 的完整 CLI 参考。涵盖所有指令、参数、资源类型、YAML 格式及最佳实践。

---

## 安装与配置

### 配置文件位置
```
~/.one/config     # 默认配置文件（JSON）
```

### 初始化上下文
```bash
# 创建/更新上下文（先于 login 执行）
one config set-context [name] \
  --server <OneSystem API URL> \
  --oneauth-url <OneAuth URL> \
  --user <username>

# 默认值（本地开发）
# --server     http://localhost:8090
# --oneauth-url http://localhost:8080
# 生产环境示例
# --server     https://api.onesystem.example.com
# --oneauth-url https://one-auth.h2os.cloud
```

---

## 认证命令

### `one login`
```
one login [flags]
```

| Flag | 类型 | 说明 |
|------|------|------|
| `-u, --username` | string | 用户名（native 模式必填） |
| `-p, --password` | string | 密码（native 模式必填） |
| `--oneauth-url`  | string | OneAuth URL（默认从 config 读取） |
| `--server`       | string | OneSystem API URL（默认从 config 读取） |

**示例：**
```bash
# OAuth2 浏览器流（推荐交互式）
one login

# Native 登录（CI/自动化必选）
one login -u user@example.com -p mypassword

# 指定服务器
one login -u admin -p pass \
  --oneauth-url https://one-auth.h2os.cloud \
  --server https://api.onesystem.example.com
```

认证成功后 token 写入 `~/.one/config`，后续命令自动使用。

---

### `one logout`
```
one logout
```
清除当前 context 的认证 token，并执行服务端登出。无参数。

---

### `one whoami`
```
one whoami [flags]
```

| Flag | 说明 |
|------|------|
| `-v, --verbose` | 显示更多信息（session、token 到期时间等） |

---

## 上下文管理 (`one config`)

```bash
one config view                        # 查看当前配置（token 已脱敏）
one config get-contexts                # 列出所有上下文
one config use-context <name>          # 切换到指定上下文
one config set-context [name] [flags]  # 创建/更新上下文
```

`set-context` flags：

| Flag | 说明 |
|------|------|
| `--server` | OneSystem API Server URL |
| `--oneauth-url` | OneAuth URL |
| `--user` | 标识用户名 |

---

## 资源类型（Kind Registry）

所有 CRUD 命令的 `<type>` 参数支持以下值（大小写不敏感，支持别名）：

| Kind（YAML） | CLI type / 别名 | REST Resource |
|-------------|-----------------|---------------|
| `Secret` | `secret`, `sec`, `secrets` | `secrets` |
| `VM` | `vm`, `vms` | `vms` |
| `Container` | `container`, `containers` | `containers` |
| `Machine` | `machine`, `mach`, `machines` | `machines` |
| `BareMetalServer` | `baremetalserver`, `bms`, `baremetalservers` | `baremetalservers` |
| `Config` | `config`, `cfg`, `configs` | `configs` |
| `HostNode` | `hostnode`, `node`, `hn`, `hostnodes` | `hostnodes` |
| `IncusInstance` | `incusinstance`, `ii`, `incusinstances` | `incusinstances` |
| `ECS` | `ecs` | `ecs` |
| `User` | `user`, `users` | `users` |
| `Allocation` | `allocation`, `alloc`, `allocations` | `allocations` |
| `Document` | `doc`, `documents` | `documents` |
| `Image` | `img`, `images` | `images` |
| `Dataset` | `ds`, `datasets` | `datasets` |
| `Artifact` | `art`, `artifacts` | `artifacts` |
| `License` | `lic`, `licenses` | `licenses` |


> **通配查询**：`one get "*"` 支持全类型通配查询（`*`），不是独立 Kind。共 **16** 个注册 Kind。

---

## CRUD 命令

### `one apply` — 创建/更新资源
```
one apply -f <file|glob|dir> [-n <namespace>]
```

| Flag | 说明 |
|------|------|
| `-f, --filename` | YAML/JSON 文件路径，支持 glob（必填） |
| `-n, --namespace` | 目标 namespace（覆盖 YAML 中的 metadata.namespace 及 config 中的 active namespace） |

**优先级：** `-n` flag > YAML `metadata.namespace` > config 中的 active namespace

```bash
one apply -f resource.yaml
one apply -f resources/            # 递归应用目录下所有 .yaml/.yml/.json
one apply -f "resources/*.yaml"    # glob 模式
one apply -f resource.yaml -n team-ops
```

---

### `one get` — 查询资源
```
one get <type> [name] [-o format] [-q query] [--all-namespaces]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `-o, --output` | `json` | 输出格式：`json` \| `yaml` |
| `-q, --query` | — | OneQL 查询字符串 |
| `-n, --namespace` | — | 指定 namespace |
| `-A, --all-namespaces` | — | 跨 namespace 查询（admin：全部；普通用户：个人 NS + 已加入共享 NS） |
| `--fields` | — | 投影字段（逗号分隔），如 `name,kind,spec.cpu` |

```bash
one get secrets                         # 列出所有 secrets
one get secret my-db-secret             # 获取单个资源
one get secrets -o yaml                 # YAML 输出
one get bms -q "label.env:prod"         # 按 label 过滤
one get "*" -q "label.role:worker"      # 全类型通配查询
one get doc --all-namespaces            # 跨 NS 查看所有可见文档
one get ds -q "spec.format:tar.gz"      # 按 spec 字段查询数据集
one get lic -q "spec.vendor:JetBrains"  # 查询许可证
```

#### OneQL 查询语法（`-q`）
空格分隔的过滤条件：

| 过滤类型 | 语法示例 |
|---------|---------|
| 元数据 | `owner:alice`, `name:my-secret` |
| 标签 | `label.env:prod`, `label.role:web` |
| Spec 字段 | `spec.cpu:4`, `spec.memory>=8` |
| Spec 嵌套字段 | `spec.pricing.unit_price<=10`, `spec.capacity.available>=4` |

支持的操作符：`:` (等于) `!=` `>` `>=` `<` `<=` `~` (包含)

嵌套字段支持任意深度的点分路径，如 `spec.pricing.unit_price` 会生成 PostgreSQL JSONB 查询 `spec->'pricing'->>'unit_price'`。数值字段自动转为 `::numeric` 进行比较。

#### OneQL 排序（`--sort`）

在 `-q` 查询中使用 `--sort` 指定排序：

```
--sort <field>:<direction>[,<field>:<direction>...]
```

- `direction`: `asc`（默认）或 `desc`
- 支持元数据字段：`name`, `owner`, `namespace`, `kind`, `created_at`, `updated_at`
- 支持 spec 嵌套字段：`spec.pricing.unit_price`, `spec.capacity.available` 等

```bash
one get bms -q "label.env:demo"
one get secret -q "type:ssh-password owner:me"
one get ecs -q "spec.cpu>=2 spec.memory>4"
one get bms -q "spec.pricing.unit_price<=10 spec.capacity.available>=4"
one get alloc -q "label.respool.consumer:alice label.respool.phase:active"
one get "*" -q "label.role:worker" --fields name,kind
one get bms -q "--sort spec.pricing.unit_price:asc"
one get alloc -q "label.respool.phase:active --sort name:asc,spec.pricing.unit_price:desc"
```

---

### `one delete` — 删除资源
```
one delete <type> <name>
one delete -f <file>
```

| Flag | 说明 |
|------|------|
| `-f, --filename` | 从 YAML 文件读取 kind/name |

```bash
one delete secret my-secret
one delete bms old-server-01
one delete -f resource.yaml
```

---

### `one edit` — 交互式编辑资源
```
one edit <type> <name>
one edit -f <local-file>
```

打开 `$EDITOR`（默认 `vi`/`notepad`）编辑资源或本地 YAML 文件。

| Flag | 说明 |
|------|------|
| `-f, --filename` | 编辑本地 YAML 文件（不访问服务器） |

```bash
one edit secret my-secret
one edit bms server-01
one edit -f ./resource.yaml
```

---

### `one patch` — 更新资源字段
```
one patch <type> <name> [--set key=val]... [-p json-patch]
one patch -f <local-file> [--set key=val]...
```

| Flag | 说明 |
|------|------|
| `-p, --patch` | JSON Merge Patch 字符串（仅 server 模式） |
| `--set` | 点路径赋值，可多次使用（两种模式均支持） |
| `-f, --filename` | 本地 YAML 文件模式（保留注释） |

```bash
# Server 模式
one patch secret my-secret --set stringData.password=newpass
one patch bms server-01 --set spec.cpu=8 --set spec.memory=32
one patch vm my-vm -p '{"spec":{"replicas":3}}'

# 本地文件模式（保留 YAML 注释）
one patch -f ./resource.yaml --set spec.replicas=3
```

**点路径格式：** `parent.child.key=value`（支持 `true`/`false` boolean 自动转换）

---

### `one label` — 管理资源标签
```
one label <type> <name> [key=value]... [key-]...
one label -f <local-file> [key=value]... [key-]...
```

| Flag | 说明 |
|------|------|
| `--overwrite` | 覆盖已存在的标签（server 模式） |
| `-f, --filename` | 本地 YAML 文件模式 |

- `key=value` — 设置标签
- `key-` — 删除标签（末尾加 `-`）

```bash
one label secret my-secret env=prod
one label bms server-01 team=ops env=staging --overwrite
one label secret my-secret env-          # 删除标签 env
one label -f ./resource.yaml env=prod
```

---

## Allocation 命令 (`one alloc` / `one allocation`)

管理资源分配的完整生命周期。Allocation 追踪"谁在使用什么资源、多少量、多长时间、什么价格"。

### `one alloc create` — 创建资源分配
```
one alloc create --resource <kind/name> --amount <n> [flags]
```

| Flag | 类型 | 必需 | 说明 |
|------|------|------|------|
| `--resource` | string | 是 | 资源引用（格式：`kind/name` 或 `kind/name@namespace`） |
| `--amount` | float | 是 | 分配数量 |
| `--unit` | string | 否 | 单位（默认从资源 pricing.unit 读取） |
| `--duration` | string | 否 | 租约时长（如 `2h`, `30m`） |
| `--consumer` | string | 否 | 消费者标识 |
| `--purpose` | string | 否 | 用途描述 |

```bash
one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --duration 2h
one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --consumer alice --purpose "LLM training"
```

**行为**：
- 自动从目标资源的 `spec.pricing` 复制定价信息到 Allocation
- Kind 别名自动解析（`bms` → `BareMetalServer`）
- 服务端原子扣减 `capacity.available`（容量不足返回 409）
- 服务端配额检查（超额返回 403）
- 默认 `phase=active`（`require_manual_confirm=true` 时为 `pending`）

---

### `one alloc list` — 列出分配
```
one alloc list [--phase <phase>] [--consumer <name>]
```

| Flag | 说明 |
|------|------|
| `--phase` | 按阶段过滤：`pending` \| `active` \| `released` \| `settled` \| `disputed` |
| `--consumer` | 按消费者过滤 |

```bash
one alloc list
one alloc list --phase active
one alloc list --consumer alice
```

---

### `one alloc get` — 查看分配详情
```
one alloc get <name>
```

---

### `one alloc usage` — 更新用量
```
one alloc usage <name> --amount <n>
```

```bash
one alloc usage alloc-483689 --amount 2.5
```

---

### `one alloc release` — 释放分配
```
one alloc release <name> [--reason <reason>]
```

| `--reason` 取值 | 说明 |
|-----------------|------|
| `completed` | 正常完成（默认） |
| `cancelled` | 用户取消 |
| `timeout` | 超时 |
| `exhausted` | 用量耗尽 |

**行为**：服务端自动恢复 `capacity.available`，自动计算 `invoice_amount`：
- `per_unit`: usage × unit_price
- `fixed`: unit_price
- `tiered`: 阶梯计价（按 tiers 数组分段累加，最后一段 `up_to<=0` 表示不限量）

**自动过期释放**：当 `spec.lease.end` 过期时，后台定时任务（每 2 分钟）会自动释放 Allocation，恢复容量，计算账单，标记 `release_reason: lease_expired`。

```bash
one alloc release alloc-483689 --reason completed
```

---

### `one alloc approve` — 审批待定分配
```
one alloc approve <name>
```
将 `pending` 状态的 Allocation 转为 `active`，同时扣减容量。

---

### `one alloc settle` — 标记结算完成
```
one alloc settle <name>
```

---

### `one alloc dispute` — 发起争议
```
one alloc dispute <name> [--reason <reason>]
```

```bash
one alloc dispute alloc-483689 --reason "overcharged"
```

---

### Allocation 状态机

```
pending ──[approve]──► active ──[release]──► released ──[settle]──► settled ⇌ disputed
```

不可跳跃或回退。违反状态机返回 400。

---

## 资源池命令 (`one pool`)

管理资源池。资源池是启用了自动发现的 namespace，包含 `respool.type:pool-config` 标签的 Config 资源。

### `one pool list` — 列出所有资源池
```
one pool list [-o format]
```

```bash
one pool list              # 列出所有资源池（搜索 label respool.type:pool-config）
one pool list -o yaml
```

### `one pool get` — 查看资源池详情
```
one pool get <pool-namespace> [-o format]
```

返回池配置 + 该 namespace 下的 IncusInstance 资源列表。

```bash
one pool get team-gpu      # 查看 team-gpu 池的配置和资源
```

---

## TUI 命令 (`one ui`)

```
one ui
```

启动基于 Bubbletea 的交互式终端 UI，提供资源浏览、搜索等图形化操作。无参数。

---

## Namespace 命令 (`one ns` / `one namespace`)

```bash
one ns create <name>                               # 创建 namespace
one ns list                                        # 列出可访问的 namespaces
one ns get <name>                                  # 查看 namespace 详情
one ns delete <name>                               # 删除 namespace
one ns add-member <namespace> <user-id> [--role]   # 添加成员
one ns remove-member <namespace> <user-id>         # 移除成员
one ns use <name>                                  # 切换 active namespace
```

`add-member` 的 `--role` 取值：`viewer`（默认）| `editor` | `admin`

```bash
one ns create team-backend
one ns add-member team-backend user-uuid-123 --role editor
one ns use team-backend
one ns list
```

---

### `one move` — 跨 Namespace 移动资源
```
one move <type> <name> --to <namespace> [--from <namespace>]
```

| Flag | 说明 |
|------|------|
| `--to` | 目标 namespace（必填） |
| `--from` | 源 namespace（可选，默认 active namespace） |

```bash
one move machine gpu-node-1 --to team-ml
one move secret db-creds --from user-alice --to project-backend
```

---

## SSH 命令 (`one ssh`)

```
one ssh [type] <name> [flags]
```

| Flag | 默认 | 说明 |
|------|------|------|
| `--host` | `localhost` | 覆盖目标主机 IP/hostname |
| `--expose-fs` | false | 通过反向 SFTP 隧道将本地目录暴露给远端 |
| `--remote-port` | `22022` | 远端 SFTP 监听端口 |
| `--local-dir` | `.` | 暴露的本地目录 |
| `--teleport` | false | 使用 Teleport 证书认证（需已 `one login`） |
| `--cert` | false | 使用 step-ca SSH CA 证书认证（推荐） |
| `--ns` | — | step-ca 证书 principal 解析的 namespace（配合 `--cert` 使用） |

**自动发现：** 不指定 type 时，自动探测 Container → BareMetalServer。

```bash
one ssh my-node                           # 自动发现类型，密码认证
one ssh bms server-01                     # 指定类型
one ssh --teleport my-node                # Teleport 证书认证
one ssh --cert my-node                    # step-ca 证书认证（推荐）
one ssh --cert --ns team-a my-node        # step-ca + 指定 namespace 解析 principal
one ssh --expose-fs my-node               # 挂载本地目录到远端
one ssh --expose-fs --local-dir /data --remote-port 22033 my-node
one ssh container my-container --host 192.168.1.100
```

**认证模式（三选一）：**
- **默认（密码）**：从资源 `spec.auth.secretRef` 获取 Secret 中的密码，连接目标端口
- **`--teleport`**：通过 Teleport Certificate Bridge 获取 SSH 证书，直连节点 port `3022`
- **`--cert`（推荐）**：通过 step-ca SSH CA 获取证书，直连节点 port `22`。Principals 从用户 UUID + namespace 成员关系解析。`--ns` 可指定额外的 namespace 进行 principal 解析

**自动重连：** SSH 连接断开（非正常退出）时自动 3 秒后重连。

**Container SSH 要求：** 资源 `status.sshPort` 必须有值。

---

## Secret 工具命令 (`one secret`)

### 密钥管理
```bash
one secret gen-key [-o output-file]   # 生成 Age 密钥对
# 默认输出到 ~/.sops/age/keys.txt
```

### 字符串加解密
```bash
one secret encrypt <plaintext>        # 加密字符串
one secret decrypt <ciphertext>       # 解密字符串
```

### 文件加解密（SOPS/Age）
```bash
one secret encrypt-file <file> [-i]   # 加密 YAML 文件（-i: 原地替换）
one secret decrypt-file <file> [-i]   # 解密 YAML 文件（-i: 原地替换）
```

---

## YAML 资源格式

所有资源遵循 KRM (Kubernetes Resource Model) 风格。

### 通用结构
```yaml
apiVersion: v1
kind: <Kind>            # PascalCase（见 Kind Registry）
metadata:
  name: <name>          # 必填，唯一标识
  namespace: <ns>       # 可选，namespace 隔离
  owner: <user>         # 可选，所有者
  labels:               # 可选，自定义标签
    key: value
spec:                   # 资源配置（类型相关）
  ...
status:                 # 运行时状态（只读）
  ...
```

### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  labels:
    env: production
stringData:
  username: admin
  password: super-secret-password
  database_url: postgresql://...
```

### BareMetalServer / Machine
```yaml
apiVersion: v1
kind: BareMetalServer
metadata:
  name: server-01
  labels:
    zone: dmz
spec:
  hostname: 192.168.1.100
  sshPort: 22
  user: root
  auth:
    secretRef: my-ssh-secret    # 引用 Secret 资源名
```

#### BareMetalServer（含 ResPool 扩展字段）
```yaml
apiVersion: v1
kind: BareMetalServer
metadata:
  name: gpu-farm-01
  namespace: team-ops
  labels:
    env: prod
    role: gpu-compute
    respool.provider: infra-team
spec:
  hostname: 10.0.1.100
  sshPort: 22
  user: root
  auth:
    secretRef: gpu-ssh-key
  pricing:                        # [MAY] ResPool 定价信息
    model: per_unit               # fixed | per_unit | tiered
    unit_price: 8                 # per_unit/fixed 使用
    currency: USDT
    unit: A100-hour
    negotiable: false
    # tiered 模式使用 tiers 数组:
    # tiers:
    #   - { up_to: 10, unit_price: 8 }
    #   - { up_to: 50, unit_price: 6 }
    #   - { up_to: 0, unit_price: 4 }   # up_to<=0 = 不限量
  capacity:                       # [MAY] 容量追踪（available 由系统自动维护）
    total: 8
    available: 8
    unit: A100
  availability:                   # [MAY] 可用性信息
    schedule: "24/7"
    lead_time: "0"
```

### Allocation
```yaml
apiVersion: v1
kind: Allocation
metadata:
  name: alloc-001
  namespace: team-ops
  labels:
    respool.resource-kind: BareMetalServer
    respool.resource-name: gpu-farm-01
    respool.consumer: alice
spec:
  resource_ref:
    kind: BareMetalServer         # [MUST] 关联资源的 Kind（PascalCase）
    name: gpu-farm-01             # [MUST] 关联资源的 name
    namespace: team-ops           # [MUST] 关联资源的 namespace
  amount:
    value: 4                      # [MUST] 分配数量
    unit: A100-hour               # [MUST] 单位
  lease:
    start: "2026-03-09T06:00:00Z" # [MUST] RFC 3339 开始时间
    end: "2026-03-09T08:00:00Z"   # [MAY] 结束时间，null = 手动释放
  pricing:
    model: per_unit               # [MUST] 创建时从资源 spec.pricing 复制
    unit_price: 8
    currency: USDT
    unit: A100-hour
  purpose: "LLM training"        # [MAY]
status:
  phase: active                   # pending | active | released | settled | disputed
  usage_reported: 2.5             # 累计用量（Agent 定期更新）
  invoice_amount: 20              # release 时自动计算
  invoice_currency: USDT
  released_at: "2026-03-09T08:00:00Z"
  release_reason: completed       # completed | cancelled | timeout | exhausted
```

### Config（ResPool 配额）
```yaml
apiVersion: v1
kind: Config
metadata:
  name: respool-quota-alice
  namespace: team-ops
  labels:
    respool.type: quota
    respool.entity: alice
spec:
  max_active_allocations: 2       # 该实体最大活跃 Allocation 数
```

### Document（文档）
```yaml
apiVersion: v1
kind: Document
metadata:
  name: arch-design-v3
  namespace: team-eng
  labels:
    category: architecture
    format: pdf
spec:
  title: "OneSystem 微内核架构设计"
  format: pdf
  size_bytes: 2048576
  author: alice
  version: "3.0"
  tags: ["architecture", "microkernel"]
  storage_ref:
    backend: s3               # s3 | oss | minio | local | git
    bucket: docs-prod
    key: "arch/design-v3.pdf"
```

### Dataset（数据集 — 含 ResPool 扩展）
```yaml
apiVersion: v1
kind: Dataset
metadata:
  name: imagenet-2024
  namespace: data-lake
  labels:
    domain: cv
spec:
  title: "ImageNet 2024 Training Set"
  format: tar.gz
  size_bytes: 157286400000
  record_count: 14000000
  tags: ["cv", "training"]
  storage_ref:
    backend: s3
    bucket: datasets
    key: "cv/imagenet-2024.tar.gz"
    checksum: "sha256:a1b2c3..."
  pricing:                        # [MAY] ResPool 计费
    model: fixed
    unit_price: 500
    currency: USDT
    unit: quarter
  capacity:                       # [MAY] 并发访问限制
    total: 5
    available: 5
    unit: access-license
```

### License（许可证 — 含席位管理）
```yaml
apiVersion: v1
kind: License
metadata:
  name: jetbrains-team-2026
  namespace: team-eng
  labels:
    vendor: jetbrains
spec:
  vendor: "JetBrains"
  product: "IntelliJ IDEA Ultimate"
  license_type: team
  license_key_ref:
    secret: jetbrains-license-key  # 引用 Secret
  valid_from: "2026-01-01T00:00:00Z"
  valid_until: "2026-12-31T23:59:59Z"
  max_seats: 10
  pricing:
    model: fixed
    unit_price: 649
    currency: USD
    unit: seat-year
  capacity:
    total: 10
    available: 10
    unit: seat
```

### Artifact（构建产物）
```yaml
apiVersion: v1
kind: Artifact
metadata:
  name: onesystem-v2.1.0-linux-amd64
  namespace: releases
  labels:
    type: binary
    arch: amd64
spec:
  artifact_type: binary
  version: "2.1.0"
  format: tar.gz
  size_bytes: 52428800
  build_ref:
    commit: "abc123def"
    branch: "release/v2.1.0"
  storage_ref:
    backend: s3
    bucket: releases
    key: "onesystem/v2.1.0/onesystem-linux-amd64.tar.gz"
    checksum: "sha256:def456..."
```

### Image（图片资源）
```yaml
apiVersion: v1
kind: Image
metadata:
  name: gpu-node-monitor-01
  namespace: team-ops
  labels:
    category: monitoring
spec:
  format: png
  size_bytes: 524288
  resolution: "1920x1080"
  captured_at: "2026-03-10T14:00:00Z"
  storage_ref:
    backend: oss
    bucket: images-prod
    key: "screenshots/gpu-node-01.png"
```

### ECS（云主机）
```yaml
apiVersion: v1
kind: ECS
metadata:
  name: web-server-01
  labels:
    env: prod
    role: web
spec:
  provider: aliyun      # aliyun | aws | volcengine | ctyun
  region: cn-hangzhou
  instance_id: i-xxxxx
  public_ip: 1.2.3.4
  private_ip: 10.0.0.5
  access:
    ssh_port: 22
    ssh_user: root
    auth_secret_ref:
      name: my-ssh-key
```

### Container
```yaml
apiVersion: v1
kind: Container
metadata:
  name: my-container
  labels:
    node: server-01     # 关联到 Machine 资源
spec:
  image: ubuntu:22.04
  cpu: 2
  memory: 4096
status:
  sshPort: "2222"       # SSH 端口（必须，one ssh 使用）
```

### User
```yaml
apiVersion: v1
kind: User
metadata:
  name: alice
  labels:
    department: engineering
spec:
  email: alice@example.com
  oneauth_id: <uuid from OneAuth>
  role: user            # user | admin
  status: active        # active | disabled
```

---

## Namespace 隔离

资源通过 `metadata.namespace` 字段隔离。未指定时归属 `default` namespace。

```bash
# 切换默认 namespace（影响后续所有命令）
one ns use team-ops

# 临时覆盖 namespace
one apply -f resource.yaml -n team-backend

# 移动资源到其他 namespace
one move secret api-key --to team-frontend
```

---

## 输出格式

所有查询命令支持 `-o json`（默认）和 `-o yaml`：

```bash
one get secrets -o yaml | grep name
one get bms server-01 -o json | jq '.spec.hostname'
```

列表响应格式：
```json
{
  "items": [...],
  "total": 10,
  "page": 1,
  "size": 100
}
```

---

## 自动化/CI 集成模式

```bash
# 1. 设置上下文
one config set-context prod \
  --server https://api.onesystem.example.com \
  --oneauth-url https://one-auth.h2os.cloud

# 2. Native 登录
one login -u $ONESYSTEM_USER -p $ONESYSTEM_PASS

# 3. 执行操作
one apply -f ./deploy/resources/

# 4. 验证
one get secrets -q "label.env:prod" -o json

# 5. 登出（可选）
one logout
```

---

## 错误排查

| 场景 | 处理 |
|------|------|
| `not logged in` | 执行 `one login` |
| `unknown resource type` | 检查 Kind Registry，确认 `<type>` 拼写 |
| `context not found` | 执行 `one config set-context` 并 `one config use-context` |
| SSH `port not available` | Container `status.sshPort` 未设置，检查容器状态 |
| `label already exists` | `one label` 加 `--overwrite` |
| `--to <namespace> is required` | `one move` 必须指定 `--to` |
| `step-ca certificate` 失败 | 确认 API Server 配置了 `STEP_CA_URL` 和 `STEP_CA_JWK_KEY_FILE` |
| `Teleport certificate` 失败 | 确认 API Server 配置了 `TELEPORT_AUTH_SERVER` 和 `TELEPORT_BOT_IDENTITY_FILE` |
| `capacity insufficient` (409) | 目标资源 `capacity.available` 不足，释放已有 Allocation 后重试 |
| `quota exceeded` (403) | 消费者配额已满，检查 `respool-quota-{consumer}` Config |
