# OneAuth 集成开发规范

## 概述

OneAuth 是 OneSystem 的统一认证服务，提供 OAuth2 (Hydra)、身份管理 (Kratos)、原生 CLI 登录等多种认证方式。本文档基于 OneAuth 实际部署实现定义集成规范。

---

## 1. 架构设计

### 1.1 实际部署架构

所有外部请求统一经 **OneAuth API (:8080)** 处理，OneAuth API 内部再代理到 Hydra/Kratos。客户端永远不直接访问 Hydra 或 Kratos 端口。

```
外部客户端
    │  https://one-auth.h2os.cloud（单一域名）
    ▼
  Traefik（SSL 终止）
    │
    ├─ /oauth2/*, /.well-known/*, /userinfo  ──┐
    ├─ /oauth/*                                 │
    ├─ /api/*                                   ├──► OneAuth API :8080
    ├─ /self-service/*, /sessions/*             │         │
    └─ /health                                 ─┘         ├─► Hydra :4444（内部）
                                                          └─► Kratos :4433（内部）
    └─ /*  ──► OneAuth Web :80（SPA 前端）
```

**本地开发** (Docker Compose):
- OneAuth API: `http://localhost:8080`（直接访问）
- OneAuth Web: `http://localhost:80`（SPA + 代理层）

### 1.2 路径路由规则（Traefik 优先级）

| 优先级 | 路径前缀 | Traefik 后端 | OneAuth API 内部处理 |
|-------|---------|-------------|---------------------|
| 100 | `/oauth2/*`, `/.well-known/*`, `/userinfo` | OneAuth API :8080 | → 代理到 Hydra :4444 |
| 90 | `/oauth/*` | OneAuth API :8080 | 业务逻辑（CLI登录/Token验证）|
| 规则 | `/api/*` | OneAuth API :8080 | 业务逻辑 + `/api/oauth2/*`→Hydra, `/api/kratos/*`→Kratos |
| 规则 | `/self-service/*`, `/sessions/*` | OneAuth API :8080 | → 代理到 Kratos :4433 |
| catch-all | `/*` | OneAuth Web :80 | SPA 静态文件 |

### 1.3 关键原则

- **单一域名入口**: 客户端只需配置一个 `oneauth_url`，指向 `https://one-auth.h2os.cloud`
- **不直接访问** Hydra/Kratos 端口，所有外部请求经 OneAuth API 路由
- **OIDC Discovery 优先**: OAuth2 标准流程始终通过 `/.well-known/openid-configuration` 自动发现端点
- **OneAuth proxy 路径优先**: 业务后端程序化调用优先使用 `/api/oauth2/*`、`/api/kratos/*` 等 OneAuth 代理路径，而非直接使用 Hydra/Kratos 原生路径

---

## 2. 配置规范

### 2.1 CLI 配置结构

配置文件位置: `~/.one/config.json`

```json
{
  "current_context": "default",
  "contexts": {
    "default": {
      "server": "http://localhost:8090",
      "oneauth_url": "https://one-auth.h2os.cloud",
      "access_token": "",
      "refresh_token": "",
      "session_token": "",
      "client_id": "onesystem-cli",
      "user": "",
      "expires_at": 0
    }
  }
}
```

### 2.2 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server` | string | 是 | OneSystem API Server 地址 |
| `oneauth_url` | string | 是 | OneAuth 统一域名 (prod: `https://one-auth.h2os.cloud`) |
| `access_token` | string | 否 | OAuth2 访问令牌 (登录后自动填充) |
| `refresh_token` | string | 否 | OAuth2 刷新令牌 (登录后自动填充) |
| `session_token` | string | 否 | Kratos 会话令牌 (可选，用于 logout) |
| `client_id` | string | 否 | OAuth2 Client ID: 原生登录 `onesystem-cli`，浏览器 OAuth2 `onesystem-cli` |
| `user` | string | 否 | 当前用户名 (登录后自动填充) |
| `expires_at` | int64 | 否 | 令牌过期时间戳 (Unix 秒) |

### 2.3 配置优先级

```
命令行参数 (--oneauth-url) > 配置文件 > 默认值 (localhost:8080)
```

---

## 3. 客户端接入标准

> OneAuth 面向不同场景提供不同接入方式，选择正确的路径至关重要。

### 3.1 按场景选择接入方式

| 场景 | 推荐方式 | 关键路径 |
|------|---------|---------|
| CLI 工具 / 原生 App 密码登录 | Native Login | `POST /oauth/native/cli` |
| 浏览器 OAuth2 授权码 (PKCE) | OIDC Discovery | `GET /.well-known/openid-configuration` |
| 后端服务验证 Token | Token Verify | `POST /oauth/token/verify` |
| Token 刷新 | OAuth Refresh | `POST /api/oauth/refresh` |
| 登出 | OAuth Logout | `POST /api/oauth/logout` |
| 程序化查询用户会话 | OneAuth Proxy | `GET /api/kratos/sessions/whoami` |
| Web 前端会话管理 | Kratos Direct | `GET /sessions/whoami` |

---

### 3.2 OIDC Discovery（浏览器 OAuth2 必用）

所有 OAuth2 标准端点通过 Discovery 自动获取，**不要硬编码**端点 URL。

**端点**: `GET /.well-known/openid-configuration`

```json
{
  "issuer": "https://one-auth.h2os.cloud",
  "authorization_endpoint": "https://one-auth.h2os.cloud/oauth2/auth",
  "token_endpoint": "https://one-auth.h2os.cloud/oauth2/token",
  "userinfo_endpoint": "https://one-auth.h2os.cloud/userinfo",
  "revocation_endpoint": "https://one-auth.h2os.cloud/oauth2/revoke",
  "jwks_uri": "https://one-auth.h2os.cloud/.well-known/jwks.json"
}
```

---

### 3.3 原生 CLI 登录

**端点**: `POST /oauth/native/cli`
→ OneAuth API 封装完整 Hydra PKCE 流程，客户端无需实现授权码交换

```json
// Request
{
  "client_id": "onesystem-cli",
  "username": "user@example.com",
  "password": "...",
  "code_verifier": "<PKCE verifier>",
  "scope": "openid profile offline"
}

// Response
{
  "access_token": "ory_at_...",
  "refresh_token": "ory_rt_...",
  "id_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "sub": "<kratos-identity-id>",
  "username": "user@example.com"
}
```

---

### 3.4 Token 验证（后端服务）

**端点**: `POST /oauth/token/verify`
→ OneAuth API 内部调用 Hydra Admin Introspect，对外屏蔽 Hydra Admin 凭证

```json
// Request
{ "token": "ory_at_..." }

// Response (active)
{
  "active": true,
  "sub": "<kratos-identity-id>",
  "username": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890,
  "client_id": "onesystem-cli",
  "scope": "openid profile offline"
}

// Response (inactive/expired)
{ "active": false }
```

---

### 3.5 Token 刷新

**端点**: `POST /api/oauth/refresh`

```json
// Request
{
  "refresh_token": "ory_rt_...",
  "client_id": "onesystem-cli"
}

// Response: 同 3.3 的 Response 格式
```

---

### 3.6 登出

**端点**: `POST /api/oauth/logout`
→ 同时撤销 OAuth2 token 和 Kratos session（传什么撤什么）

```json
// Request
{
  "access_token": "ory_at_...",
  "refresh_token": "ory_rt_...",
  "session_token": "...",   // 可选，有则一并撤销 Kratos session
  "client_id": "onesystem-cli"
}

// Response
{ "success": true }
```

---

### 3.7 程序化 Kratos 访问（优先使用 OneAuth 代理路径）

> 推荐使用 `/api/kratos/*` 而非直接用 `/self-service/*` 或 `/sessions/*`，
> 原因：经 OneAuth 代理有统一日志和未来扩展空间。

| 推荐路径 | 原始 Kratos 路径 | 说明 |
|---------|----------------|------|
| `GET /api/kratos/sessions/whoami` | `GET /sessions/whoami` | 验证当前 session（需 Cookie 或 X-Session-Token） |
| `GET /api/kratos/self-service/login/flows` | `GET /self-service/login/flows` | 查询登录流程详情 |
| `GET /api/kratos/self-service/registration/flows` | `GET /self-service/registration/flows` | 查询注册流程详情 |

Web 前端（浏览器）因依赖 Cookie 重定向，可直接用原始路径 `/self-service/*`、`/sessions/*`。

---

### 3.8 UserInfo（OIDC 标准）

**端点**: `GET /userinfo`

```
Authorization: Bearer <access_token>
```

Response 包含 Hydra 授权的 claims（`sub`, `email`, `name` 等，取决于 scope）。

---

## 4. 代码规范

### 4.1 Auth Client 封装

所有 OneAuth 交互通过 `pkg/auth` 包的 Client:

```go
// 初始化 (oneauthURL 来自配置)
authClient := auth.NewClient(oneauthURL)

// 方法签名
GetOIDCConfiguration() (*OIDCConfiguration, error)
NativeLogin(username, password string) (*TokenResponse, error)
VerifyToken(token string) (*UserInfo, error)       // 带 5 分钟内存缓存
GetUserInfo(accessToken string) (*UserInfo, error) // OIDC /userinfo
RefreshToken(refreshToken, clientID string) (*TokenResponse, error)
Logout(accessToken, refreshToken, sessionToken, clientId string) error
```

### 4.2 Native Login 完整流程

```go
// pkg/auth/client.go 中 NativeLogin 内部实现:
// 1. 自动生成 PKCE code_verifier
verifier, _, _ := GeneratePKCEPair()

// 2. POST /oauth/native/cli (OneAuth 自动完成 Hydra PKCE 全流程)
req := NativeLoginRequest{
    ClientId:     "onesystem-cli",        // 固定值
    Username:     username,
    Password:     password,
    CodeVerifier: verifier,
    Scope:        "openid profile offline",
}

// 3. 返回 tokens，无需客户端手动完成授权码交换
```

### 4.3 OAuth2 Browser 流程 (PKCE)

```go
// cmd/one/commands/login.go 中的实现:
codeVerifier, codeChallenge, _ := cli.GeneratePKCEPair()
state, _ := cli.GenerateRandomString(32)

// 获取 OIDC 配置 (端点从 /.well-known/openid-configuration 获取)
oidcConfig, _ := authClient.GetOIDCConfiguration()

// 构建授权 URL (使用 OIDC Discovery 返回的端点)
authParams := url.Values{
    "client_id":             []string{"onesystem-cli"},  // 浏览器流程专用 client
    "redirect_uri":          []string{"http://localhost:8888/callback"},
    "response_type":         []string{"code"},
    "scope":                 []string{"openid profile offline"},
    "state":                 []string{state},
    "code_challenge":        []string{codeChallenge},
    "code_challenge_method": []string{"S256"},
}
authURL := oidcConfig.AuthorizationEndpoint + "?" + authParams.Encode()
```

### 4.4 Token 验证中间件

```go
// pkg/middleware/auth.go 中的实现:
// 1. 从 Authorization: Bearer <token> 提取
// 2. 调用 authClient.VerifyToken(token) → POST /oauth/token/verify
// 3. 设置 context: username, user_id (Sub), email
// 4. 注意: OneAuth 当前不返回 role 字段，默认设为 "user"
//    后续 RBAC 升级时需从 OneAuth UserInfo 或 claims 获取
```

### 4.5 错误处理规范

```go
// OneAuth API 错误响应格式 (JSON body)
// 状态码非 200 时读取 body 作为错误信息

if resp.StatusCode != http.StatusOK {
    bodyBytes, _ := io.ReadAll(resp.Body)
    return fmt.Errorf("auth error %d: %s", resp.StatusCode, string(bodyBytes))
}
```

---

## 5. 安全规范

### 5.1 必须遵守

- **PKCE**: OAuth2 公共客户端必须使用 PKCE (S256)
- **State 验证**: 必须验证 OAuth2 回调中的 state 参数防止 CSRF
- **HTTPS**: 生产环境必须使用 HTTPS (Traefik 自动配置 Let's Encrypt)
- **令牌存储**: 配置文件权限必须为 0600
- **Client ID**: 统一使用 `"onesystem-cli"`（原生登录和浏览器 OAuth2 共用同一个 Hydra public client）

### 5.2 禁止事项

- 禁止在日志中打印 access_token、refresh_token、password
- 禁止硬编码 Client Secret（CLI 使用公开客户端，无 secret）
- 禁止在 URL 参数中传递令牌（应使用 Authorization Header）
- 禁止直接访问 Hydra Admin API (:4445) 或 Kratos Admin API (:4434)
- 禁止跳过 `/.well-known/openid-configuration` 硬编码端点 URL

### 5.3 SSH 证书认证说明

OneSystem 支持两种 SSH 证书认证方式，均**不经过 OneAuth**，而是通过 OneSystem API Server 签发：

| 方式 | API 端点 | CA 后端 | 说明 |
|------|---------|---------|------|
| Teleport Certificate Bridge | `POST /api/v1/ssh/cert` | Teleport Auth Server | 签发 Teleport 证书，SSH port 3022 |
| step-ca SSH CA（推荐） | `POST /api/v1/sshca/cert` | step-ca | 签发标准 SSH 证书，SSH port 22 |

两者均需 OneAuth Bearer Token 认证（通过 `RequireAuth()` 中间件），但证书签发逻辑在 OneSystem 内部完成。

### 5.4 已知限制 (待改进)

- `ssh.InsecureIgnoreHostKey()` 目前用于内部 SSH Tunnel，生产环境应替换为已知 host key 验证
- OneAuth 当前版本不在 UserInfo 中返回 `role` 字段，`pkg/middleware/auth.go` 中默认为 `"user"`

### 5.5 请求认证

```go
// API 请求使用 Bearer Token
req.Header.Set("Authorization", "Bearer " + accessToken)

// Kratos 会话使用 Cookie（仅 Web 场景）
req.Header.Set("Cookie", "ory_kratos_session=" + sessionToken)
```

---

## 6. 测试规范

### 6.1 Mock OneAuth

测试时 mock `/oauth/token/verify` 端点（OneSystem 服务端验证 token 的核心路径）:

```go
func TestAuthMiddleware(t *testing.T) {
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        switch r.URL.Path {
        case "/oauth/token/verify":
            json.NewEncoder(w).Encode(map[string]interface{}{
                "active":   true,
                "sub":      "user-uuid-123",
                "username": "testuser",
                "exp":      time.Now().Add(time.Hour).Unix(),
            })
        case "/.well-known/openid-configuration":
            json.NewEncoder(w).Encode(map[string]string{
                "authorization_endpoint": server.URL + "/oauth2/auth",
                "token_endpoint":         server.URL + "/oauth2/token",
            })
        }
    }))
    defer server.Close()

    client := auth.NewClient(server.URL)
    // ...
}
```

### 6.2 环境配置

| 环境 | OneAuth URL | Client ID |
|------|-------------|-----------|
| 本地开发 | `http://localhost:8080` | `onesystem-cli` |
| CI/CD (Docker Compose) | `http://oneauth:8080` | `onesystem-cli` |
| 生产 | `https://one-auth.h2os.cloud` | `onesystem-cli` |

---

## 7. 常见问题

### Q1: OIDC Discovery 失败
```bash
curl https://one-auth.h2os.cloud/.well-known/openid-configuration
# 检查 Traefik 和 Hydra 是否正常运行
```

### Q2: `/oauth/native/cli` 返回 4xx
- 检查 `client_id` 是否为 `onesystem-cli`（需在 Hydra 中注册）
- 检查 `code_verifier` 格式是否正确（PKCE S256）
- 检查 Kratos 中用户是否存在且密码正确

### Q3: Token 验证返回 `token is not active`
- Token 已过期：调用 `RefreshToken()` 获取新 token
- Token 被撤销：重新登录
- OneAuth/Hydra 服务异常：检查健康状态

### Q4: 本地开发无法连接 OneAuth
```bash
# 本地使用 Docker Compose 启动
cd D:\Work\h2os.cloud\one-auth
docker compose up -d
# API 监听 :8080，Web 监听 :80
```

---

## 8. 参考资料

- [OneAuth 源码](../../../one-auth/internal/server/api.go)
- [Traefik 生产部署](../../../one-auth/deploy/prod/docker-compose.traefik.yml)
- [CLI Auth Client 实现](../pkg/auth/client.go)
- [Auth 中间件实现](../pkg/middleware/auth.go)
- [CLI Login 实现](../cmd/one/commands/login.go)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
