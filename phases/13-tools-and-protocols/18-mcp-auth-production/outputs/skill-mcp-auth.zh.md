---
name: mcp-auth-wiring
description: 设计基于 issuer 绑定注册、CIMD、protected-resource metadata、JWKS 刷新、audience 固定和每请求校验的 MCP 2026-07-28 授权方案。
version: 2.0.0
phase: 13
lesson: 18
tags: [mcp, oauth, cimd, dcr, jwks, rfc8414, rfc7591, rfc8707, rfc7636, rfc9728, rfc9207]
---

给定 MCP server 配置和 IdP 能力集，输出构成生产级 MCP 授权层的认证接口面与拒绝规则。

输入：

- `mcp_resource_url` —— 规范 resource URL（最具体的标识符；仅当需要区分共置的 server 时才保留路径），用作 `aud` 和 protected-resource metadata 的 `resource` 值。
- `idp_metadata_url` —— IdP 的 `/.well-known/oauth-authorization-server`（或 OpenID Connect Discovery）URL。
- `idp_capabilities`：观察到的 `issuer`、`code_challenge_methods_supported`、`grant_types_supported`、`client_id_metadata_document_supported`、已弃用的 `registration_endpoint`、`response_types_supported` 和 `authorization_response_iss_parameter_supported` 取值。
- `pre_registered_client_ids`：可选的 issuer 到 client ID 映射，由 authorization server 运营方预置。优先使用这份 issuer 作用域的身份，其次是 CIMD，最后才把已弃用的 DCR 作为兼容路径。
- `application_type`：`native` 或 `web`，在选择已弃用的 DCR 兼容路径时必需。
- `credential_store`：client ID 和注册凭据按 authorization server issuer 为键，access token 按 `(issuer, mcp_resource_url)` 为键。
- `tools`：MCP tool 列表，以及每个 tool 所需的 scope。

产出：

1. **拒绝门。** 任何硬性条件不满足，就拒绝接线并停止：
   - `code_challenge_methods_supported` 中缺少 `S256`（PKCE 没有降级模式）。
   - `grant_types_supported` 中缺少 `authorization_code`。
   - `response_types_supported` 不是恰好 `["code"]`。
   - 不存在任何注册路径：预注册的 `client_id`、`client_id_metadata_document_supported: true`、已弃用的 DCR 兼容 endpoint 三者皆无。
   - 选择了 CIMD，但其 `client_id` 不是带路径的绝对 HTTPS 文档 URL、与文档 URL 不一致，或文档缺少非空的 `client_name` 或 `redirect_uris` 数组。`application_type` 对 CIMD 是可选的。
   - 返回的 RFC 9207 `iss` 与重定向前记录的 issuer 不一致，或在 server 声明支持该参数时缺失。
   - 已弃用的 DCR 未声明 `application_type`，或其 redirect URI 策略与 `native` 或 `web` 冲突。

2. **MCP server 的 protected-resource metadata 文档**（RFC 9728）。对于带路径的 resource，把 well-known 段插在该路径之前：`https://host/team/mcp` 映射到 `https://host/.well-known/oauth-protected-resource/team/mcp`。包含 `resource`、`authorization_servers`（issuer allow-list）、`scopes_supported` 和 `bearer_methods_supported: ["header"]`。

3. **HTTP endpoint。**
   - `GET /.well-known/oauth-protected-resource` —— 返回 (2) 中的文档。
   - `POST /mcp`（无状态 MCP transport）：在任何 tool dispatch 之前，为当前请求校验 bearer token。
   - 仅 DCR 兼容路径：`POST /register`，在其之前加入 application type 检查和限流检查。

4. **后台任务与例程。**
   - 定时的 JWKS 刷新，把 `jwks_uri` 重新拉入缓存 `{keys, fetched_at}`。幂等；绝不铸造密钥。AS 负责轮换；resource server 只负责刷新。默认 `0 */6 * * *`；对高轮换频率的 IdP 收紧到 `*/15 * * * *`。
   - 一个 `validate` 例程——检查 `iss` allow-list、对照缓存 JWKS 的签名、`aud == mcp_resource_url`、`exp`、必需 scope。
   - 一条 step-up 签发路径——仅当 tool 列表中存在受某个 scope 门控、而用户最初未授予该 scope 的操作时才需要。

5. **缓存方案。** 每个被接受的 issuer 一条条目，以 `issuer` 为键，保存 `{keys, fetched_at}`。说明读取模式：校验器读取缓存，并在 `kid` 未命中时回退到一次同步刷新（重新拉取，而不是轮换——重新拉取是幂等的，无法被变成密钥创建 DoS）。

6. **Scope 映射。** 把每个 tool 映射到它所需的 scope。输出一张表：
   `| tool | required_scope | rationale |`。把破坏性 tool 归入各自独立的 scope；绝不复用读 scope 来覆盖写 tool。

7. **运行时的拒绝规则**（校验器必须实现这些）：
   - `aud != mcp_resource_url` 时拒绝 → 401 `Bearer error="invalid_token", error_description="audience mismatch", resource_metadata="<prm_url>"`。
   - `iss not in authorization_servers` 时拒绝。
   - 在一次重新拉取回退之后 `kid` 仍不在缓存的 JWKS 中时拒绝。
   - 缺少必需 scope 时拒绝 → 403 `Bearer error="insufficient_scope", scope="<required>", resource_metadata="<prm_url>"`。
   - 拒绝任何没有 S256 `code_challenge` 的授权请求，并拒绝任何 `code_verifier`、client、redirect URI 或 `resource` 与一次性授权码记录不匹配的 token 请求。
   - 拒绝任何 issuer 与其凭据存储键不匹配的凭据或 token。issuer 变化要求重新注册。

硬性拒绝（绝不接上以下任何一项——拒绝该请求并记录原因）：

- 以明文存储 `client_secret`。public client 使用 `token_endpoint_auth_method: none`；confidential client 使用 `private_key_jwt`。静态存储和注册响应日志中都不得出现明文共享 secret。
- 在校验器上跳过 `aud` 检查。audience 绑定（access-token 权限限制）正是 RFC 8707 + RFC 9728 存在的全部理由。
- 把 JWKS 缓存未命中的回退接到 rotate-and-mint，而不是重新拉取。它永远不会产生缺失的 `kid`，还会让攻击者控制的 `kid` 值迫使系统无界地创建密钥。回退必须是幂等的刷新。
- 允许无 PKCE 的授权码请求。OAuth 2.1 禁止这种做法；校验器必须拒绝任何其存储的授权码记录缺少 `code_challenge` 的 `/token` 兑换。
- 在没有刷新任务的情况下缓存 JWKS。要么定时刷新上线，要么认证接口面不部署。
- 在没有 allow-list 的情况下信任 `iss` claim。任何接受来自任意 `iss` 的 token 的校验器，都会让攻击者架起自己的 IdP 并伪造 token。
- 把入站 MCP token 转发给上游 API（token 透传）。如果 MCP server 调用上游 API，它 MUST 获取自己的独立 token；透传会造成 confused deputy 问题。
- 以明文存储 `registration_access_token`。静态时哈希；每次更新都要求明文出示。
- 把 MCP 请求 metadata 或已移除的协议 session 当作授权状态。2026-07-28 的 transport 是无状态的；要对每个请求做认证与授权。

输出：一份单页方案，包含 protected-resource 文档、按 issuer 为键的注册布局、按 issuer 与 resource 为键的 token 布局、选定的注册路径、HTTP endpoint、JWKS 刷新任务、scope 映射以及运行时拒绝规则。结尾给出在 authorization server 实际 metadata 中发现的第一个未满足的部署门。
