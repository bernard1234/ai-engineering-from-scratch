# 生产环境中的 MCP 认证：按 issuer 绑定的注册与 token

> 第 16 课搭建了 OAuth 2.1 状态机。本课强化它在 MCP 2026-07-28 下的生产边界：优先使用 Client ID Metadata Documents，动态注册仅作为已弃用的兼容手段，校验授权响应中的 issuer，按 issuer 为键保存 client 凭据，刷新 JWKS，并在每个无状态请求上绑定 audience 的 token。
>
> **Spec note (2026-07-28):** Dynamic Client Registration 已被弃用，改用 Client ID Metadata Documents。DCR 仍是兼容机制。使用它时，client 要声明正确的 `application_type`。client 校验存在的 RFC 9207 `iss` 值，并且绝不在不同 authorization server issuer 之间复用凭据。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** 第 13 阶段，第 16 课（OAuth 2.1 状态机）、第 13 阶段，第 17 课（gateways）
**Time:** ~90 分钟

## Learning Objectives

- 通过 RFC 8414 metadata 发现 authorization server 并验证该契约。
- 通过 Client ID Metadata Document 完成注册，并把已弃用的 DCR 隔离为回退路径。
- 校验 RFC 9207 `iss`，按 authorization server issuer 为键保存注册信息，并按 issuer 加 resource 为键保存绑定 resource 的 token。
- 按计划缓存和刷新 JWKS 密钥，使签名校验在密钥轮换期间仍然有效。
- 用 RFC 8707 resource indicators 把 token 固定到单一 MCP resource，并拒绝 confused deputy 式的复用。
- 选择 JWT 校验或 token introspection，定义撤销的新鲜度，并在身份依赖不可用时安全失败。
- 把 authorization server、resource server 和 client 分离，使每一方只执行自己的检查。
- 依据部署检查清单审计 authorization server，并拒绝不安全的注册或 token 复用。

## 问题场景

第 16 课的模拟器在内存中运行 OAuth 2.1。生产环境有三个只靠内存的模拟器看不到的运维缺口。

第一个缺口是注册与凭据隔离。真实组织可能运行数百个 MCP server 和数千个 MCP client。2026-07-28 修订版优先采用 **Client ID Metadata Document**：client 用它自己控制的、带路径的 HTTPS URL 作为标识符，authorization server 主动拉取 metadata。RFC 7591 动态注册仅作为已弃用的兼容路径保留。当 DCR 无法避免时，请求要声明正确的 `application_type`。client 把注册信息存在 authorization server issuer 之下，把 access token 存在 `(issuer, resource)` 对之下。issuer 变化意味着重新注册，resource 不同意味着另一个绑定 audience 的 token。

第二个缺口是密钥轮换。JWT 校验依赖 authorization server 的签名密钥，它们以 JSON Web Key Set（JWKS）形式发布。authorization server 按计划轮换这些密钥（通常是每小时，事件响应期间有时更快）。只在启动时拉取一次 JWKS 的 MCP server 在轮换窗口之前校验一切正常——然后每个请求都失败，直到重启。生产环境把 JWKS 接成缓存值，配合一个在旧密钥过期前覆盖缓存的刷新任务，以及在缓存未命中时触发的一次回退拉取，以应对用比缓存更新的密钥签发的 token 到达的情形。

第三个缺口是 audience 绑定。第 16 课引入了 RFC 8707 resource indicators。在生产中，该 indicator 变成每个请求上的硬性 claim 检查。MCP server 把 `token.aud` 与它自己的规范 resource URL 比较，不匹配就以 HTTP 401 拒绝。这是抵御上游 MCP server（或持有面向某个 server 的 token 的恶意 client）在同一信任网格内针对另一个 server 重放该 token 的唯一防线。

本课把每个缺口映射到接口面上的具体部分。metadata 文档是一个 HTTP endpoint。JWKS 缓存刷新是一个定时任务加一个 key-value 缓存。JWT 校验是 resource server 在 dispatch 任何 tool 之前运行的例程。保持三个角色分离，每一方只执行自己负责的检查：authorization server 签发并轮换密钥，resource server 缓存并校验，client 发现并注册。

## 范围：第 16 课之后的生产执行

[第 16 课：基于 OAuth 2.1 的 MCP 安全](../../16-mcp-security-oauth-2-1/docs/en.md) 负责授权码状态机、PKCE、protected-resource discovery、resource indicators 和 scope 决策。本课不定义第二套 OAuth 流程。它从这些契约已经存在之后开始，追问一个已部署的 resource server 如何在密钥轮换、不透明 token 校验、撤销、依赖失败、上线和事件响应期间持续执行它们。

生产边界更窄，也更偏运维：

- JWT 路径在每次请求上校验固定下来的 issuer、算法、签名密钥、audience、时间 claim 和 scope，同时安全地刷新 JWKS。
- 不透明 token 路径调用 issuer 经过认证的 introspection endpoint，并校验返回的 active 状态、audience 或 resource、过期时间、subject 和 scope。
- 撤销策略定义凭据必须在多短时间内停止生效，以及哪个缓存可能延迟这一事实。
- 失败策略决定当 discovery、JWKS、introspection 或撤销基础设施不可用时会怎样。
- 证据记录是哪些 issuer metadata、密钥集或 introspection 响应、token claim、策略版本和拒绝原因导致了结果，同时不存储 token。

这个划分让两课可以组合使用。第 16 课证明流程成立。第 18 课证明 token 在到达真实 MCP 请求路径之后仍然可信，或被拒绝。

## 核心概念

### RFC 8414 —— OAuth Authorization Server Metadata

位于 `/.well-known/oauth-authorization-server` 的文档描述了 client 所需的一切：

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "client_id_metadata_document_supported": true,
  "registration_endpoint": "https://auth.example.com/register",
  "authorization_response_iss_parameter_supported": true,
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "scopes_supported": ["mcp:tools.read", "mcp:tools.invoke"],
  "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"]
}
```

拿到 MCP resource URL 的 client 会串起发现链：先用 RFC 9728 的 `oauth-protected-resource`（resource server 的文档）找到 issuer，再用 `oauth-authorization-server`（本 RFC）找到每个 endpoint。client 永远不会硬编码 authorization URL。

对于带路径的 resource 标识符，要把 well-known 段插在该路径之前。例如 `https://mcp.example.com/team/server` 对应的 protected-resource metadata 位于 `https://mcp.example.com/.well-known/oauth-protected-resource/team/server`。在 resource 路径之后追加 `/.well-known/...` 是错误的。

在信任某个 IdP 服务于 MCP 之前要验证的契约：

- `code_challenge_methods_supported` 包含 `S256`（RFC 7636 的 PKCE）。规范明确指出：如果该字段**缺失**，authorization server 就不支持 PKCE，client **MUST** 拒绝继续。
- `grant_types_supported` 包含 `authorization_code`，并且拒绝 `password` 与 `implicit`。
- 至少有一条注册路径可用：`client_id_metadata_document_supported: true`（CIMD，优先）、预注册的 client，或 `registration_endpoint`（已弃用的 RFC 7591 兼容路径）。
- 如果 `authorization_response_iss_parameter_supported` 为 true，client 就要求返回 RFC 9207 的 `iss`，并在重定向之前与记录的 issuer 精确比较。
- 对 OAuth 2.1 而言，`response_types_supported` 恰好是 `["code"]`。

如果缺少 `S256`，MCP server 就拒绝针对该 IdP 部署——PKCE 没有降级模式。如果*两条*注册路径都未声明，而你也没有预注册的 `client_id`，同样无法注册；出错的是部署清单，而不是代码。

### RFC 9728（回顾）—— Protected Resource Metadata

第 16 课已经讲过 RFC 9728。生产中的增量是：这份文档是 client 寻找*本* MCP server 所信任的 authorization server 的唯一位置。一个 MCP server 可以接受来自多个 IdP 的 token（一个面向员工，一个面向合作伙伴）。RFC 9728 声明这个集合；RFC 8414 记录每个 IdP 支持什么。

```json
{
  "resource": "https://notes.example.com",
  "authorization_servers": ["https://auth.example.com", "https://partners.example.com"],
  "scopes_supported": ["mcp:tools.invoke"],
  "bearer_methods_supported": ["header"],
  "resource_documentation": "https://notes.example.com/docs"
}
```

### Client ID Metadata Documents（推荐的默认方式）

CIMD 把注册从*推送*反转为*拉取*。client 不再要求 authorization server 铸造 `client_id`，而是用它控制的 HTTPS URL **作为**自己的 `client_id`。该 URL 解析为一份 JSON metadata 文档；authorization server 在 OAuth 流程中按需拉取。信任根植于 DNS：如果 server 运营方信任 `app.example.com`，它就信任从 `https://app.example.com/client.json` 提供的 client。没有注册往返，没有会被耗尽的 `client_id` 命名空间，也没有需要保持同步的每 server 状态。

client 托管的 metadata 文档：

```json
{
  "client_id": "https://app.example.com/oauth/client.json",
  "client_name": "Example MCP Client",
  "client_uri": "https://app.example.com",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:7333/callback", "http://localhost:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

文档中的 `client_id` 值**MUST** 等于提供该文档的 URL（authorization server 会验证这一点，不匹配即被拒绝）。authorization server 在其 RFC 8414 metadata 中以 `client_id_metadata_document_supported: true` 声明支持。

就当前的 CIMD 契约而言，`client_id`、`client_name` 和非空的 `redirect_uris` 数组是必需的。client 标识符是一个带路径的绝对 HTTPS URL。`application_type` 可以包含，但它不是 CIMD 的强制字段。不要把它在 DCR 中的要求照搬到首选的 CIMD 路径上。

规范直言不讳的两个安全事实：

- **SSRF。** authorization server 会拉取攻击者提供的 URL。它必须防御服务端请求伪造（不得拉取内部或管理 endpoint）。
- **localhost 冒充。** 单靠 CIMD 无法阻止本地攻击者声明合法 client 的 metadata URL，并绑定任意 `localhost` redirect。authorization server **MUST** 在同意阶段清楚展示 redirect URI 的 hostname，并**SHOULD** 对仅 `localhost` 的 redirect 发出警告。

由于 CIMD 不需要服务端状态，也就没有 DCR 所要求的那种注册器需要搭建。client 侧是只读的：从一个静态 HTTPS endpoint 提供你的 metadata 文档，让 authorization server 去拉取。

如果 authorization server 运营方已经预置了 client 标识符，就优先使用这份 issuer 作用域的注册，再考虑自动注册。否则优先使用 CIMD。只有当 issuer 既不能使用预注册也不能使用 CIMD 时，才使用已弃用的 DCR。

### RFC 7591：已弃用的兼容注册

DCR 在 2026-07-28 修订版中已被弃用。只为那些无法消费 CIMD 且预注册不切实际的 authorization server 保留它。一个兼容 client 会发送：

```json
POST /register
Content-Type: application/json

{
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none",
  "scope": "mcp:tools.invoke",
  "client_name": "Cursor",
  "software_id": "com.cursor.cursor",
  "software_version": "0.42.0"
}
```

server 返回 `client_id` 和一个用于后续更新的 `registration_access_token`：

```json
{
  "client_id": "c_3e7f1a",
  "client_id_issued_at": 1769472000,
  "redirect_uris": ["http://127.0.0.1:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "registration_access_token": "regt_b2...",
  "registration_client_uri": "https://auth.example.com/register/c_3e7f1a"
}
```

`application_type` 不是装饰性的。loopback 桌面 client 声明 `native`；server 托管的 client 声明 `web` 并使用 HTTPS redirect URI。对公开的 native client 而言，`token_endpoint_auth_method: none` 是正确的默认值。它只拿到 `client_id`，由 PKCE 提供持有证明。

三个生产陷阱：

- 注册 endpoint 必须按源 IP 限流。否则，恶意行为者可以脚本化地发起数百万次虚假注册，耗尽 `client_id` 命名空间。在注册器处理请求之前先执行限流检查。
- 一些企业 IdP 要求 `software_statement`（一份用于担保 client 的签名 JWT）。本课的 mock 跳过了它；生产环境要接入一个校验步骤，拒绝来自 localhost redirect URI 之外的未签名注册。
- `registration_access_token` 必须以哈希形式存储，而非明文。该 token 被盗意味着攻击者可以改写 client 的 redirect URI。

### RFC 8707（回顾）—— Resource Indicators

第 16 课确立过它的形态。生产规则是：每个 token 请求都包含 `resource=<canonical-mcp-url>`，且 MCP server 在每次调用时校验 `token.aud` 与自己的 resource URL 匹配。规范 URI 是该 server *最具体*的标识符：scheme 和 host 用小写，不含 fragment，按惯例不带尾斜杠。按规则 path 组件**不会**被剥除——当需要区分单个 MCP server 时，规范会保留它。`https://mcp.example.com`、`https://mcp.example.com/mcp`、`https://mcp.example.com:8443` 和 `https://mcp.example.com/server/mcp` 都是合法的规范 URI。为每个 server 选定一个，并把 `aud` 精确固定到它。（本课的 mock 为简洁起见使用 `https://notes.example.com` 这样的裸 host audience；若部署在同一 origin 下共置多个 MCP server，则用 path 区分它们。）

### RFC 7636（回顾）—— PKCE

PKCE 在 OAuth 2.1 中是强制的。本课的授权码流程总是携带 `code_challenge` 和 `code_verifier`。server 拒绝任何没有 verifier、或 verifier 哈希后与存储的 challenge 不一致的 token 请求。

### MCP 2026-07-28 授权规范

当前 MCP 修订版在让 MCP transport 无状态的同时，保留了 OAuth 的 resource-server 边界。没有可用于缓存身份决策的协议 session。因此授权层独立校验每个请求：

- 实现 RFC 9728 protected-resource metadata，并通过 401 上的 `WWW-Authenticate: Bearer resource_metadata="..."` header **或** well-known URI `/.well-known/oauth-protected-resource` 提供其位置（SEP-985 让该 header 变为可选，并提供了 well-known 回退）。metadata 的 `authorization_servers` 字段**MUST** 至少给出一个 server。
- 只通过**每个**请求上的 `Authorization: Bearer ...` 接受 token——绝不在 query string 中，也绝不只在 session 开始时校验。
- 每个请求都校验 `aud`、`iss`、`exp` 和必需的 scope。server **MUST** 校验 token 是专门为它签发的（audience）；缺失或不匹配的 `aud` 一律拒绝，绝不当作通配。
- 在 401/403 时返回 `WWW-Authenticate: Bearer`，携带 `error=...`、`resource_metadata="<PRM-URL>"` 参数（该 metadata 文档的 URL，*而非*裸 resource），并在 `insufficient_scope`（403）时携带 `scope="..."`。注意：参数是 `resource_metadata`，一个发现指针——challenge 中没有 `resource` 参数。
- authorization-server 发现**同时**接受 RFC 8414 OAuth metadata **和** OpenID Connect Discovery 1.0；client 必须按优先级依次尝试两个 well-known 后缀。
- 由 client（而不是 server）防御 **mix-up 攻击**：client 在重定向之前记录预期的 `issuer`，并在兑换 code 之前校验实际授权响应中返回的 `iss` 值（RFC 9207）。仅靠 PKCE 无法阻止 mix-up，因为 client 会把 `code_verifier` 交给它被引导到的任何 token endpoint。
- 一份 client 凭据只属于一个 authorization server issuer。如果发现解析到不同的 issuer，client 要重新注册，而不是出示旧的 `client_id`、registration token 或 access token。
- CIMD 是首选的注册机制。DCR 已被弃用；兼容性的 DCR 请求仍要声明正确的 `application_type`。

OAuth 2.1 草案是基底；RFC 8414/7591/8707/9728/9207 + RFC 7636 + CIMD 是接口面；MCP 规范是 profile。

### 部署能力检查清单

厂商功能表很快就会过时。改为检查你实际要部署的 authorization server 返回的 metadata。这道门是机械性的：

| 检查项 | 要求的决策 |
|---|---|
| Discovered issuer | 策略预期的精确 HTTPS issuer |
| PKCE | 声明了 `S256`；否则停止 |
| Enrollment | 优先 CIMD，接受预注册，DCR 仅作已弃用的兼容路径 |
| Authorization response | 存在或已声明时校验 RFC 9207 `iss` |
| Resource binding | token 请求携带 `resource`；resource server 要求匹配的 `aud` |
| Credential storage | client ID 与注册凭据按 issuer 为键；access token 按 issuer 加 resource 为键 |
| DCR compatibility | 声明 `native` 或 `web`；拒绝不符合所声明 application type 的 redirect URI |

不要从产品名称或定价档位推断支持能力。把发现的文档写入部署证据，并在缺少强制字段时 fail closed。

### JWKS 刷新模式（在 AS 轮换，在 resource server 刷新）

把两个动词分开，混淆它们是一个真实的生产 bug：

- **Rotate（轮换）** 是 *authorization server* 做的事：铸造新的签名密钥，把它发布到 JWKS，稍后让旧密钥退役。resource server 不参与其中，也无法做到——它并不持有 IdP 的私钥。
- **Refresh（刷新）** 是 *resource server* 做的事：重新 `GET` 已发布的 JWKS 到自己的缓存。这是 resource server 唯一会执行的 JWKS 动作。

生产故障模式是缓存陈旧。用定时刷新任务加 key-value 缓存来解决。resource server 运行一个任务（cron、timer，或你的运行时提供的任何机制），按固定间隔拉取 `<issuer>/.well-known/jwks.json` 并覆盖 `cache[issuer] = {keys, fetched_at}`。校验器从该缓存读取。如果某个 token 的 `kid` 不在缓存中，就触发**一次**同步刷新作为回退，然后重新检查。这同时处理两种情况：定时刷新，以及密钥重叠窗口——用全新密钥签发的 token 在下一次定时刷新之前到达。

回退**必须是重新拉取，绝不是轮换**。如果你把缓存未命中路径接到 rotate-and-mint，会有两件事坏掉：(1) 铸造新密钥产生的 `kid` *仍然*不匹配该 token，所以查找照样失败；(2) 用随机 `kid` 值喷洒 token 的攻击者会迫使系统无界地创建密钥——一场自伤式 DoS。重新拉取是幂等的，所以一个伪造的 `kid` 最多只浪费一次拉取。

缓存形态：

```json
{
  "https://auth.example.com": {
    "keys": [
      {"kid": "k_2026_03", "kty": "RSA", "n": "...", "e": "AQAB", "alg": "RS256", "use": "sig"},
      {"kid": "k_2026_04", "kty": "RSA", "n": "...", "e": "AQAB", "alg": "RS256", "use": "sig"}
    ],
    "fetched_at": 1772668800
  }
}
```

同时存在两把密钥是常态。authorization server 通过先引入下一个密钥（`k_2026_04`）再让上一个（`k_2026_03`）退役来完成轮换，因此旧密钥签发的 token 在过期前仍然有效。缓存持有并集；校验器按 `kid` 挑选。

### 校验例程

MCP server 在 dispatch 任何 tool 之前运行校验。`code/main.py` 使用的形态是：

```python
result = server.validate(bearer_token, required_scope="mcp:tools.invoke")
if not result["valid"]:
    return {"status": result["status"], "WWW-Authenticate": result["www_authenticate"]}
```

`validate` 解码 JWT，从 JWKS 缓存解析签名密钥（未命中时刷新一次），校验签名，然后检查 `iss` 是否在 allow-list 中、`aud` 是否等于本 server 的规范 resource、`exp`，以及必需的 scope——在第一个失败处返回 `WWW-Authenticate` challenge。把它保持为 resource server 上的单一例程，意味着每个入口（每次 tool 调用、每种 transport）都经过相同的检查；不存在未经校验就到达 tool 的路径。

### 不透明 token 使用 introspection，而不是猜测

并非每个 access token 都是 JWT。如果 issuer 记录了不透明 token，resource server 就无法把它解码成可信 claim。它通过经过认证的后端通道把 token 发送到 issuer 的 RFC 7662 introspection endpoint，并要求 `active: true`、预期的 issuer 上下文、精确的 MCP audience 或 resource、未过期的时间 claim，以及具体 tool 所需的 scope。

按 issuer、单向 token 摘要和 MCP resource 缓存 introspection。绝不要用明文 token 作为日志或缓存标签。以 token 过期时间、issuer 缓存指引和部署的撤销新鲜度目标三者中最早者来界定正向缓存条目。负向缓存要足够短，以免新签发的 token 被错误地保持为非活跃。即使不透明 token 字符串完全相同，面向一个 resource 的结果也不能授权另一个 resource。

不要依据攻击者控制的 token 内容选择校验模式。把 JWT 还是 introspection 的行为固定到已验证的 issuer metadata 和部署配置上。在 JWT 路径上，固定可接受的算法和受信任的 `jwks_uri`；绝不跟随仅由 token header 选定的密钥 URL 或算法。

### 撤销是一份时效契约

RFC 7009 允许 client 要求 authorization server 撤销 token。该请求并不会抹除每个 resource server 已缓存的副本。定义可接受的最大撤销延迟，并让每个缓存遵守它。

不透明 token 部署可以通过在每次高风险调用时 introspect，或使用短暂的正向缓存，来实现更紧的撤销。自包含 JWT 部署通常把较短的 access token 生命周期与 refresh token 撤销、针对 issuer 级事件的密钥退役相结合，并可选地使用 subject、session 或 token-id 的拒止名单来实现紧急的本地拒绝。已签名的 JWT 在到期前始终在密码学上有效，除非 resource server 掌握当前的外部撤销证据；只有那种情况下它才会被提前拒绝。

登出、账户禁用、同意撤回和事件响应是不同的触发条件，但必须收敛到一句可度量的陈述：至多在声明的撤销窗口之后，每个副本都会拒绝该凭据。要通过负载均衡器测试这句陈述，而不只是对一个热进程测试。

### 依赖失败需要明确的既定决策

永远不要在异常处理器里即兴决定可用性策略。

| 失败情形 | 安全的生产行为 |
|---|---|
| 定时 JWKS 刷新失败，已知 `kid` 仍留在仍有效的有界缓存中 | 只在声明的 stale-on-error 窗口内继续，并输出降级健康证据 |
| token 带有未知 `kid`，且唯一允许的一次刷新失败 | 拒绝；绝不接受无法校验的签名 |
| introspection 不可用 | 对受保护调用 fail closed；不要把网络故障转换成 `active: true` |
| protected-resource 或 issuer metadata 意外变化 | 停止新的注册与 token 获取；只在有界事件策略下保留明确固定且未过期的配置 |
| 撤销 endpoint 不可用 | 把登出或撤销报告为未完成，尽可能在本地把凭据保留为不可用状态，且不要声称全局撤销成功 |
| 时钟源或 claim 类型无效 | 拒绝，而不是放宽偏差直到 token 通过 |

把失败与无效凭据分类开。依赖中断是运维错误，配有健康与重试策略。签名、issuer、audience、过期时间或 scope 错误是授权拒绝。两者都不会到达 tool handler，也都不应把 token 内容泄漏进审计证据。

### Audience 重放演示（access-token 权限限制）

Server A（`notes.example.com`）和 Server B（`tasks.example.com`）都在同一个 authorization server 上注册。Server A 被攻陷。攻击者取走某个用户的 notes token，并针对 Server B 重放它。

Server B 的校验器：

1. 解码 JWT，按 `kid` 拉取 JWKS，校验签名。
2. 对照其 protected-resource metadata 的 `authorization_servers` 检查 `iss`。（通过——同一个 IdP。）
3. 检查 `aud == "https://tasks.example.com"`。（失败——token 的 `aud` 是 `https://notes.example.com`。）
4. 返回 401，并附 `WWW-Authenticate: Bearer error="invalid_token", error_description="audience mismatch", resource_metadata="https://tasks.example.com/.well-known/oauth-protected-resource"`。

在协议层，audience claim 是抵御这种攻击的唯一防线。为性能跳过它是最常见的生产错误；校验器必须在每个请求上运行，而不只是在 session 开始时。规范称此为 **access-token 权限限制**：MCP server `MUST` 拒绝任何未在 audience 中指明自己的 token。

> **Naming note.** 规范把 *confused deputy* 一词保留给一个相关但不同的问题：MCP server 作为第三方 API 的 OAuth **代理**，使用静态 client ID，在未取得每 client 用户同意的情况下转发 token。audience 绑定修复了上面的重放；confused deputy 的修复是每 client 同意，**加上**绝不把入站 token 透传给上游 API（MCP server `MUST` 获取自己的独立上游 token）。

### Mix-up 攻击（server 无法提供的 client 侧防御）

client 在其生命周期内会与许多 authorization server 交互。恶意的 AS 可以试图让 client 在攻击者的 token endpoint 兑换诚实 AS 的授权码。audience 绑定在这里帮不上忙——攻击发生在任何 token 存在之前。防御在 client 中（RFC 9207）：

1. 在重定向之前，client 从已验证的 AS metadata 记录预期的 `issuer`。
2. 收到授权响应时，client 在把 code 发往任何地方之前，先把返回的 `iss` 参数与记录的 issuer 比较（简单字符串比较，不做归一化）。
3. 不匹配（或 AS 声明了 `authorization_response_iss_parameter_supported` 却缺少 `iss`）→ 拒绝，甚至不展示 `error` 字段。

仅靠 PKCE 无法阻止 mix-up，因为 client 会把 `code_verifier` 交给它被引导到的任何 token endpoint。这就是规范要求在每个请求中把 issuer 与 PKCE verifier 和 `state` 一并记录的原因。

### 失败模式

- **JWKS 陈旧。** AS 轮换密钥后，校验器拒绝有效 token。修复方式是上文所述的 cron 刷新加缓存未命中的重新拉取模式。永远不要在没有刷新任务的情况下缓存 JWKS。
- **以轮换作为回退。** 把缓存未命中路径接到 rotate-and-mint 而不是重新拉取是真实的 bug：它永远不会产生缺失的 `kid`，还会把攻击者控制的 `kid` 值变成密钥创建 DoS。回退必须是幂等的 `refresh-jwks`。
- **缺少 `aud` claim。** 有些 IdP 默认省略 `aud`，除非 token 请求中带有 `resource`。校验器必须拒绝缺少 `aud` 的 token，而不是把缺失当作通配。
- **缺少 `iss` 校验导致的 mix-up。** 如果 client 不把 RFC 9207 的 `iss` 授权响应参数与重定向前记录的 issuer 做校验，就可能被引导到攻击者的 token endpoint 兑换诚实 AS 的 code。这是 client 侧失败，resource server 无法弥补。
- **Scope 升级竞争。** 同一用户的两个并发 step-up 流程可能都成功，并产生两个 scope 不同的 access token。校验器必须使用请求上出示的 token，而不是查询“用户当前的 scope”——那会制造 TOCTOU 窗口。
- **Registration token 被盗。** 泄漏的 `registration_access_token` 让攻击者能够改写 redirect URI。静态存储时要哈希；要求 client 在每次更新时出示明文；一旦怀疑即轮换。
- **`iss` 未固定。** 接受任意 `iss` 的校验器，会让攻击者架起自己的 authorization server、为目标 audience 注册 client 并签发 token。protected-resource metadata 的 `authorization_servers` 列表就是 allow-list；必须执行它。
- **凭据或 token 缓存冲突。** 只按 resource 为键保存注册信息的 client，可能把一个 authorization server 的身份出示给另一个。只按 issuer 为键保存 access token 的 client，可能把 token 重放到错误的 audience。按已验证的 issuer 为键保存注册信息，按 `(issuer, resource)` 为键保存 access token，并在 issuer 变化时重新注册。

```figure
t3-jwks-rotate
```

## Use It

`code/main.py` 用 stdlib Python 和三个角色走完整的生产流程：`AuthorizationServer`、`ResourceServer` 和 `Client`。流程如下：

从仓库根目录运行：

```bash
cd phases/13-tools-and-protocols/18-mcp-auth-production
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

第一条命令打印按 issuer 绑定的注册与 token 校验记录。第二条报告十八项通过的检查。两条命令都不会打开网络监听器或写入凭据。

1. authorization server 在 `/.well-known/oauth-authorization-server` 发布 RFC 8414 metadata。
2. MCP client 调用该 metadata endpoint，检查其注册选项（CIMD 对应 `client_id_metadata_document_supported`，DCR 对应 `registration_endpoint`）以及 `S256` PKCE 支持。
3. client 检查是否存在 issuer 作用域的预注册，否则用其 HTTPS Client ID Metadata Document 注册。已弃用的 DCR 仍是可单独测试的兼容 method。
4. client 记录已验证的 issuer，创建 S256 challenge，收到一次性 authorization code 及 `iss`，校验返回的 issuer，并用原始 verifier 和 RFC 8707 `resource` indicator 兑换 code。
5. MCP client 用 `Authorization: Bearer ...` 在 MCP server 上调用某个 tool。
6. MCP server 运行 `validate`，从 JWKS 缓存解析签名密钥。
7. IdP 轮换一把密钥；定时刷新把 JWKS 重新拉入缓存。
8. 下一次调用针对刷新后的密钥完成校验，无需重启，而先前的 token 在重叠窗口内仍然有效。
9. 针对另一个 MCP resource 的 audience 重放尝试会收到 401，带有 `audience mismatch` 和一个 `resource_metadata` 指针。

这里的 JWT 使用共享 secret 的 HS256（以便本课只依赖 stdlib）。生产环境使用 RS256 或 EdDSA，配合上面的 JWKS 模式；校验逻辑其余部分完全相同。由于 IdP 和 resource server 同处一个进程，`refresh_jwks` 直接读取 authorization server 的密钥列表；在线上，它是一次对 `jwks_uri` 的 HTTP `GET`。

## Ship It

本课产出 `outputs/skill-mcp-auth.md`。给定 MCP server 配置和 IdP 能力集，该 skill 输出需要搭建的认证接口面——protected-resource metadata、要使用的注册路径（CIMD、预注册或 DCR 回退）、JWKS 刷新计划、scope 映射，以及在 IdP 不支持完整 RFC profile 时要施加的拒绝规则。

## Exercises

1. 运行 `code/main.py`。跟踪流程。注意 IdP 在第 6 步如何轮换密钥，定时的 `refresh_jwks` 如何重新拉取已发布的密钥集，以及旧 token（重叠窗口）和新 token 如何在不重启的情况下都通过校验。

2. 向 protected-resource metadata 的 `authorization_servers` 列表添加一个新的 IdP。签发一个由新 IdP 签名的 token，确认校验器接受它。签发一个由未列出的 IdP 签名的 token，确认校验器以 `WWW-Authenticate: Bearer error="invalid_token", error_description="iss not allowed"` 拒绝。

3. 给 `register_client` 添加一个限流检查，在注册器接受请求之前运行。用一个以 IP 为键的小 dict 保存按源 IP 的 token bucket。

4. 阅读 RFC 7591，找出本课 `/register` handler 未校验的两个字段，并补上校验。（提示：`software_statement` 和 `redirect_uris` 的 URI scheme。）

5. 添加第二个 authorization server。确认 client 保存了单独的按 issuer 为键的注册信息，并拒绝复用第一个 issuer 的 token 或 `client_id`。

6. 证明 DoS 修复有效。向校验器发送一个带随机 `kid` 的 token，确认 `refresh_jwks` 最多运行一次，且 authorization server 的密钥数量不增长。然后故意把回退接到 rotate-and-mint，观察密钥数量随每个伪造 token 攀升——之后恢复为重新拉取。

7. 用 `native` 和 `web` 两种 client 演练已弃用的 DCR。确认使用 HTTP redirect URI 的 web client，以及没有精确 loopback redirect 的 native client，都会被拒绝。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| ASM | “OAuth 元数据文档” | RFC 8414 的 `/.well-known/oauth-authorization-server` JSON |
| CIMD | “client 元数据 URL” | Client ID Metadata Document：用作 `client_id` 的 HTTPS URL；AS 主动拉取 JSON。MCP 2026-07-28 中首选的注册方式 |
| DCR | “自助式 client 注册” | RFC 7591 `POST /register`；对当前 MCP 已弃用，仅为兼容保留 |
| JWKS | “用于 JWT 校验的公钥” | JSON Web Key Set，从 `jwks_uri` 拉取，按 `kid` 索引 |
| Rotate vs refresh | “更新密钥” | *Rotate* = AS 铸造或退役签名密钥；*refresh* = resource server 重新拉取已发布的集合。resource server 只会 refresh |
| Resource indicator | “audience 参数” | RFC 8707 的 `resource` 参数，把 token 固定到单个 server |
| `aud` claim | “受众” | 校验器与规范 resource URL 比较的 JWT claim |
| Audience replay | “token 重放” | 把面向 Server A 签发的 token 出示给 Server B；由 audience 校验防御（规范称 access-token 权限限制） |
| Confused deputy | “代理 token 误用” | 使用静态 client ID、在无每 client 同意的情况下转发 token 的 MCP 代理；与 audience replay 不同 |
| Mix-up attack | “错误的 token endpoint” | client 被引导到攻击者的 endpoint 兑换诚实 AS 的 code；通过 RFC 9207 `iss` 在 client 侧防御 |
| `iss` allow-list | “受信任的 authorization server” | protected-resource metadata 的 `authorization_servers` 中给出的集合 |
| `resource_metadata` | “PRM 文档的位置” | 401/403 上指名 RFC 9728 metadata URL 的 `WWW-Authenticate` 参数 |
| Public client | “原生或浏览器 client” | 没有 `client_secret` 的 OAuth client；由 PKCE 补偿 |
| `WWW-Authenticate` | “401/403 响应头” | 携带驱动 client 恢复的 `Bearer error=...` 指令 |

## Further Reading

- [MCP 授权规范（2026-07-28）](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) - 当前的 MCP 授权规范
- [MCP 2026-07-28 变更日志](https://modelcontextprotocol.io/specification/2026-07-28/changelog) - CIMD、issuer 校验、DCR 弃用以及按 issuer 为键的凭据变更
- [OAuth Client ID Metadata Document (draft-ietf-oauth-client-id-metadata-document-00)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00) — CIMD
- [RFC 8414 — OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414) — 发现契约
- [RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591) — DCR（回退路径）
- [RFC 7636 — Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636) — public client 的持有证明
- [RFC 8707 — Resource Indicators for OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc8707) — audience 固定
- [RFC 9728 — OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728) — resource server 发现
- [RFC 9207 — OAuth 2.0 Authorization Server Issuer Identification](https://datatracker.ietf.org/doc/html/rfc9207) — 防御 mix-up 攻击的 `iss` 参数
- [RFC 7662: OAuth 2.0 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662)
- [RFC 7009: OAuth 2.0 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009)
