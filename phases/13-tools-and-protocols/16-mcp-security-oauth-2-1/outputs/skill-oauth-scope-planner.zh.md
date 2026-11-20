---
name: oauth-scope-planner
description: 设计基于 CIMD、issuer 隔离、resource indicators 和 step-up scope 的 MCP 2026-07-28 授权方案。
version: 2.0.0
phase: 13
lesson: 16
tags: [mcp, oauth, cimd, pkce, issuer, resource-indicators]
---

给定一个远程 HTTP MCP server 及其 tool 列表，设计完整的授权边界。

## 所需输入

- 规范的 MCP resource URI 与 protected-resource metadata 的位置。
- 允许的 authorization server issuer。
- client 运行时：native 或 web，以及精确的 redirect URI。
- tool 到 scope 的映射以及会产生后果的操作。
- token、refresh 和凭据存储方面的约束。
- 不支持 CIMD 的旧版 authorization server（如有）。

## 产出

1. Resource metadata。起草 RFC 9728 的 `resource`、`authorization_servers` 和 `scopes_supported`。保留 well-known 段之后的 resource 路径，例如对 `https://notes.example.com/mcp` 使用 `https://notes.example.com/.well-known/oauth-protected-resource/mcp`。
2. Issuer 策略。写明精确允许的 issuer、metadata 校验、变更处理和 RFC 9207 `iss` 比较。
3. Enrollment。可用时使用预注册，否则优先使用 Client ID Metadata Document。其带路径的 HTTPS URL 就是 `client_id`；要求精确的 redirect URI，并把展示用 metadata 视为不可信。`application_type` 在此为可选项。
4. DCR 回退。若必须使用，标注其已弃用，声明 `application_type`，并定义允许回退的精确条件。不要在通用的 CIMD 安全失败之后降级。
5. 凭据键。预注册和 DCR 凭据按 issuer 存储，token 按 `(issuer, resource)` 存储。禁止跨 issuer 复用。说明自托管的 CIMD URL 是可移植的，当受信任 issuer 变化时无需重新做 DCR 注册。
6. PKCE 流程。要求 S256、精确的 redirect URI、授权响应 issuer 校验，并在授权请求和 token 请求中使用相同的 resource。
7. Scope 模型。把每个 tool 映射到其最小 scope。把当前 `WWW-Authenticate` 的 scope challenge 视为权威。
8. Step-up 体验。指出额外 scope、面向用户的解释、同意点、新的授权，以及使用全新 MCP 请求 id 的重试。
9. Resource-server 检查。实现所声明的 `tools/list`，使用合法的对象根 schema、确定性顺序、result type、server 身份和缓存提示。在 tool dispatch 之前校验 issuer、audience、过期时间、scope、当前 MCP header 和请求 metadata。
10. Token 卫生。仅使用 bearer header，不得在 query 中携带 token，禁止 token 透传，refresh 凭据保密存储，并给出轮换计划。
11. 错误契约。把每个请求 id 都保留在 JSON-RPC 错误信封中，包括 OAuth 失败。要求在版本支持检查的 HTTP 400 `-32022` 之前，先对 header 不匹配返回 HTTP 400 `-32020`，给出精确的 supported 与 requested data，对未知 method 返回 HTTP 404 `-32601`，对被接受的 notification 返回 202 和空 body。
12. Transport 边界。把已解析 body 的示例标注为进程内协议模型，并把它们接到第 09 课完整的 Streamable HTTP adapter 上，以进行 JSON Content-Type 以及 JSON 加 SSE Accept 的校验。

## 硬性拒绝

- 把 DCR 当作首选的新注册机制。
- 未声明 `application_type` 的 DCR。
- issuer 变化后复用由 issuer 铸造的注册凭据、access token 或 refresh token。自托管的 CIMD URL 是可移植的例外，而不是 issuer 铸造的 secret。
- 在比较前对授权响应中的 `iss` 做归一化。
- 缺少 PKCE S256，或授权请求和 token 请求中缺少 `resource`。
- 接受面向其他 audience 的 token，或把 MCP token 转发给下游。
- 把 `clientInfo`、`serverInfo`、capabilities 或已移除的协议 session 当作认证依据。
- 仅仅为了模仿远程 HTTP 而给本地 stdio 加上 OAuth。
- 构造 RFC 9728 metadata URL 时丢掉受保护 resource 的路径。
- 对 MCP 请求错误返回纯文本或临时拼凑的对象，而不是带相同 id 的 JSON-RPC 信封。

## 输出格式

返回名为 Resource、Issuers、Enrollment、Credential Store、PKCE Flow、Scope Matrix、Step-Up、Server Validation、Token Hygiene 和 Compatibility 的章节。结尾给出触发 issuer 复核的确切事件，以及对 issuer 铸造的 client，触发重新注册的确切事件。
