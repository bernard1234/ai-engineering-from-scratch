# MCP 授权：CIMD、issuer 绑定、PKCE 与 step-up

> 远程 MCP 请求是无状态的，但它的授权并非匿名。把每个凭据绑定到签发它的 issuer，把每个 token 绑定到接收它的 resource。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 09 课（transports）、第 13 阶段，第 15 课（security）
**Time:** ~90 分钟

## Learning Objectives

- 通过 protected-resource metadata 发现 authorization server。
- 优先使用 Client ID Metadata Documents，而不是已弃用的 Dynamic Client Registration。
- 当不得不走 DCR 兼容路径时，声明正确的 `application_type`。
- 校验授权响应中的 `iss`，并按 issuer 隔离凭据。
- 使用 PKCE、resource indicators、audience 校验和增量 scope。
- 在没有协议 session 的情况下发送已授权的 MCP 2026-07-28 请求。

## 问题场景

远程 MCP server 可能读取私有记录、写入外部系统，或触发代价高昂的工作。认证只能告诉它谁出示了凭据。授权还必须回答：

- 该凭据由哪个 authorization server 签发？
- 该 token 面向哪个 MCP resource？
- 哪个 client 和哪个 redirect URI 完成了这次流程？
- 用户批准了哪些操作？
- 当前这个具体请求是否仍在批准的范围内？

2026-07-28 授权规范强化了 client 注册与 issuer 处理：优先使用 Client ID Metadata Documents，弃用 Dynamic Client Registration，在 DCR 中要求正确的 `application_type`，校验 RFC 9207 issuer 响应，并禁止跨 issuer 复用凭据。

这些规则是无状态核心的补充，它们并不会恢复核心握手或 `Mcp-Session-Id`。

## 核心概念

### 认识三个角色

- **MCP client：** 代表 resource owner 发送请求。
- **MCP resource server：** 接收 access token 并提供 MCP endpoint。
- **Authorization server：** 认证 resource owner、收集同意并签发 token。

resource server 和 authorization server 可以由同一方运营，但两者的标识符和校验职责必须保持分离。

### 授权仅适用于 HTTP

MCP 授权规范适用于基于 HTTP 的 transport。本地 stdio server 运行在进程与操作系统的信任边界之内。不要仅仅为了对称，就给 stdio 强行加一套浏览器 OAuth 流程。

对于远程 Streamable HTTP，在每个请求的 `Authorization` header 中发送 bearer token。永远不要把它放进 URL。

### 从 protected-resource metadata 开始

resource server 发布 RFC 9728 metadata：

```json
{
  "resource": "https://notes.example.com/mcp",
  "authorization_servers": ["https://auth.example.com"],
  "scopes_supported": ["notes:delete", "notes:read", "notes:write"]
}
```

client 从 MCP resource URL 出发，获取这份文档，选择一个文件中声明的 authorization server，然后获取该 server 的 OAuth 或 OpenID Connect metadata。

构造 RFC 9728 well-known URL 时要保留 resource 的路径。对于 resource `https://notes.example.com/mcp`，本课使用 `https://notes.example.com/.well-known/oauth-protected-resource/mcp`。丢掉 `/mcp` 后缀，可能选中同一 origin 上另一个受保护 resource 的 metadata。

不要根据 hostname 猜测 authorization server。不要跟随从未经校验的错误响应体中发现的 issuer。为 client 愿意信任哪些 issuer 维护一份策略。

### 验证 authorization server metadata

该 metadata 应公开 endpoint 和所支持的控制项：

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "code_challenge_methods_supported": ["S256"],
  "authorization_response_iss_parameter_supported": true,
  "client_id_metadata_document_supported": true
}
```

PKCE 必须要求 S256。记录精确的 issuer 字符串。这个精确值将成为注册与 token 存储的键。

### 遵循注册优先级

如果 client 与选定的 issuer 之间已存在明确关系，就使用预注册的 client 信息。否则，在 authorization server 声明支持时优先使用 Client ID Metadata Documents。只有在作为已弃用的兼容回退时才使用 DCR；如果这些机制都不可用，则提示用户提供 client 信息。

### 优先使用 Client ID Metadata Documents

Client ID Metadata Document 给 authorization server 一个 HTTPS URL，它既是 client 标识符，也是其 metadata 的位置：

```json
{
  "client_id": "https://client.example.com/oauth/metadata.json",
  "client_name": "Notes desktop client",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:8765/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"]
}
```

authorization server 负责获取并校验这份文档。`client_id` 必须是带路径的 HTTPS URL，且文档内的该值必须与 URL 完全一致。文档的必填字段是 `client_id`、`client_name` 和 `redirect_uris`。`application_type` 出现在这个示例中，但它不是 CIMD 的必需项；它新的强制性用途专属于 DCR 路径。

获取该文档应被视为对 SSRF 敏感的操作。解析并校验目标地址，拒绝 loopback、私有、链路本地以及其他不允许的地址，在重定向和 DNS 变化后重新检查，限制重定向次数、字节数和时间，要求内容为 JSON，并且只依据经过校验的 HTTP 缓存控制来缓存。把 `client_name` 和其他展示字段当作不可信文本处理。

CIMD 免去了为每一次首次接触铸造全新动态标识符的需要，但它不免除 redirect URI 校验、issuer 策略和用户同意。

### DCR 是兼容路径

Dynamic Client Registration 仍然可供较旧的 authorization server 使用，但对新的 MCP 实现而言它已被弃用。

使用 DCR 时，声明 `application_type`：

```json
{
  "client_name": "Notes desktop client",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:8765/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"]
}
```

- 桌面、移动、命令行和 loopback client 使用 `native`。
- 远程托管的浏览器应用使用 `web` 和远程 HTTPS redirect。

省略该字段时，OpenID Connect 注册实现可能默认成 `web`，从而让合法的 loopback redirect 失败。

把 DCR 代码放在一个显式的回退决策之后。不要在任意 CIMD 校验失败后静默回退，那可能把一次安全失败变成一条更弱的注册路径。

### 将凭据绑定到 issuer

按精确的 issuer 存储由 issuer 铸造的注册材料：

```text
issuer_credentials[issuer] = pre_registered_or_dcr_client
tokens[(issuer, resource)] = access_token
```

如果 protected-resource 发现的结果从 `https://auth-one.example` 变成 `https://auth-two.example`，就要重新评估信任。绝不要把第一个 issuer 的 client secret、DCR client id、registration access token、refresh token 或 access token 发送给第二个 issuer。预注册 client 和 DCR client 必须使用为新 issuer 签发的凭据。

CIMD 的 client id 不同，因为它是自托管的 HTTPS URL，而不是 authorization server 铸造的凭据。同一个 CIMD URL 是可移植的：新的受信任 issuer 可以获取并校验这份文档，无需重新做 DCR 注册。但授权响应和 token 仍要按新 issuer 进行校验和存储。

### 使用 PKCE 的授权码流程

交互式流程如下：

1. 生成高熵的 `code_verifier`。
2. 推导出 S256 `code_challenge`。
3. 发送授权请求，携带精确的 `client_id`、`redirect_uri`、`scope`、`code_challenge` 和 `resource`。
4. 收到包含 `code` 的授权响应，以及（若提供）`iss`。
5. 在使用响应中的任何字段之前，先用记录的精确 issuer 校验 `iss`。
6. 用 `code_verifier`、相同的 redirect URI 和相同的 `resource` 兑换 code。
7. 把得到的 token 存储到 `(issuer, resource)` 下。

来自 RFC 8707 的 `resource` 参数同时出现在授权请求和 token 请求中，它标识 MCP server 的规范 URI。

### 精确校验 `iss`

RFC 9207 防止来自一个 issuer 的授权响应与来自另一个 issuer 的响应混淆。

当 `iss` 存在时，将它和记录的 issuer 比较，不做大小写折叠、尾斜杠变更、默认端口移除或百分号编码归一化。一旦不匹配，不要对 code 采取任何动作，甚至不要显示来自该响应的、受攻击者控制的错误细节。

包含 `iss` 的 authorization server 会声明 `authorization_response_iss_parameter_supported: true`。即便缺少该声明，当前 client 仍要校验存在的 `iss`。

### 在 MCP server 校验 audience

resource server 只接受签发给它自己的 token：

```text
token.issuer == configured_authorization_server
token.audience == canonical_mcp_resource
```

无效、过期、issuer 错误或 audience 错误的 token 一律收到 401。MCP server 不得接受或转发面向其他服务的 token。

### 请求当前所需的最小 scope

从当前需要的 scope 开始。如果后续某个 tool 需要更多权限，server 返回 403 并附上权威的 scope challenge：

```text
WWW-Authenticate: Bearer error="insufficient_scope",
  scope="notes:delete",
  resource_metadata="https://notes.example.com/.well-known/oauth-protected-resource/mcp"
```

client 解释新增权限，取得用户同意，用合并后的 scope 集合执行一次新的授权流程，然后用新的 JSON-RPC id 重试该 MCP 请求。

不要假定 challenge 中的 scope 是 `scopes_supported` 的子集。对于当前操作，challenge 才是权威。

### 授权与无状态的 MCP 线协议

一次已授权的 tool 调用仍然携带完整的当前请求信封：

```text
POST /mcp
Authorization: Bearer <access-token>
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.delete
```

```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "method": "tools/call",
  "params": {
    "name": "notes.delete",
    "arguments": {"id": "note-7"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "oauth-lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

token 授权的是 principal，请求 metadata 协商的是协议行为。两者不能互相替代。

按固定顺序校验线协议：先校验 JSON-RPC 和 metadata 类型，再校验 header 与 body 的一致性，最后校验协议支持。路由或版本 header 不匹配返回 HTTP 400 和 `-32020`。如果 header 与 body 一致地指向一个不受支持的版本，返回 HTTP 400 和 `-32022`，且 `data` 精确为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。未知 method 返回 HTTP 404 和 `-32601`。

任何请求错误，包括 401 无效 token 和 403 scope 不足，都是带原始请求 `id` 的 JSON-RPC 错误信封。结构化的恢复信息放在可选的错误 `data` 中；`WWW-Authenticate` 仍然是 HTTP 响应 header。notification 没有 `id`，因此不会收到 JSON-RPC body。被接受的 HTTP notification 返回 202 和空 body。

该 server 实现了 `server/discover` 并声明了 tools，因此它也必须实现强制的 `tools/list` method。它的 tool descriptor 具有稳定的 name、description 和对象根 `inputSchema`。列表是确定性的，返回 `resultType`、server 身份 metadata、有界的 `ttlMs` 以及 `cacheScope`。discovery 和与用户无关的 tool 列表可以在授权之前就可用。如果二者随 principal 变化，就需要应用常规策略和私有缓存。

### 禁止 token 透传

MCP server 不得把 client 的 MCP access token 转发给下游 API。应获取一个具有正确 audience 的独立下游 token，或采用显式的 token exchange 设计。只有当服务拒绝为他方铸造的 token 时，audience 校验才会生效。

### Refresh token

refresh token 是可选的。若签发，应保密存储，并以 issuer 和 resource 为键。不要假定它一定存在。当 authorization server 支持轮换时进行轮换，并检测已失效值的复用。

```figure
t3-scope-stepup
```

## Build It

`code/main.py` 是一个进程内的协议与授权模拟器。它实现了 protected-resource discovery、authorization server metadata、CIMD 注册、按版本门控的 DCR 回退、application type 检查、PKCE、issuer 校验、resource 绑定的 token、scope step-up、`server/discover`、`tools/list`，以及一次无状态 tool 请求。

该模型接收已解析的请求 body 和路由 header。它不是完整的 HTTP adapter，也不解析 `Content-Type` 或 `Accept`。请将它接到第 09 课的 Streamable HTTP adapter 上，后者要求 `Content-Type: application/json`，且 `Accept` 值同时包含 `application/json` 和 `text/event-stream`。

运行它：

```bash
cd phases/13-tools-and-protocols/16-mcp-security-oauth-2-1
python3 code/main.py
python3 -m unittest discover code/tests -v
```

输出会先展示 discovery，然后是 CIMD 注册、一次普通的读取、两次独立的 scope step-up，以及按 issuer 为键的凭据存储。

## Use It

把模拟器中的对象映射到生产组件：

- `ResourceServer.protected_resource_metadata` 对应 RFC 9728 endpoint。
- `AuthorizationServer.metadata` 对应 RFC 8414 或 OpenID Connect discovery。
- `Client.enroll` 对应 CIMD 解析加上一条显式的 DCR 兼容分支。
- issuer 铸造的 client 凭据和 `tokens_by_issuer_resource` 对应加密记录。CIMD URL 可以保持可移植，但其授权结果仍然绑定 issuer。
- `ResourceServer.handle` 对应中间件：在 dispatch 之前校验当前 MCP header、token 和 tool scope，同时让每个请求错误都落在匹配的 JSON-RPC 信封中。

## Ship It

本课交付 `outputs/skill-oauth-scope-planner.md`。它现在设计注册优先级、按 issuer 绑定的凭据存储、application type、PKCE、resource indicators、scope challenge 以及当前的无状态请求边界。

## Exercises

1. 添加 refresh token 轮换，并拒绝复用上一个 refresh token。
2. 添加 issuer allowlist。当 issuer 变化时，只复用可移植的 CIMD URL；拒绝此前所有由 issuer 铸造的凭据和 token。
3. 给 authorization code 添加过期时间，并确认延迟兑换会失败。
4. 构建一个使用远程 HTTPS redirect 的 web client 变体，并将其 DCR metadata 与 native client 做对比。
5. 在同一 issuer 下添加第二个 resource。确认它的 access token 无法用于第一个 resource。

## Key Terms

| 术语 | 含义 |
|------|---------|
| Protected-resource metadata | RFC 9728 文档，用于标识 resource 和 authorization server |
| CIMD | 以其 URL 作为 OAuth client 标识符的 HTTPS metadata 文档 |
| DCR | 为兼容性保留的、已弃用的动态 client 注册 |
| `application_type` | `native` 或 `web`，用于校验 redirect URI 规则 |
| PKCE | 保护被截获 authorization code 的 verifier 与 S256 challenge |
| `iss` | RFC 9207 授权响应中的 issuer 标识符 |
| Resource indicator | RFC 8707 参数，把 token 请求绑定到某个 MCP resource |
| Audience | token 对其有效的 resource |
| Step-up | 为当前操作所需的额外 scope 重新取得同意并签发 token |
| Issuer-bound credentials | 按精确 authorization server issuer 隔离的注册与 token 记录 |

## Further Reading

- [MCP 2026-07-28 授权规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728)
- [RFC 8707: Resource Indicators for OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8707)
- [RFC 9207: OAuth 2.0 Authorization Server Issuer Identification](https://www.rfc-editor.org/rfc/rfc9207)
- [OAuth Client ID Metadata Document 草案](https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/)
