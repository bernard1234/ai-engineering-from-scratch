---
name: mcp-server-platform
description: 设计一个无状态 MCP 2026-07-28 server，具备注册表 metadata、实时发现、授权、策略、审计与规模证据。
version: 2.0.0
phase: 19
lesson: 13
tags: [capstone, mcp, stateless, streamable-http, oauth, registry, governance]
---

给定一个内部平台需求，设计一个无状态 MCP server 与治理边界，目标协议修订版 `2026-07-28`。

构建计划：

1. 一个 schema 合法的 `server.json`，其反向 DNS 名与发布者已认证的命名空间一致。
2. 必需的 `server/discover`，用于实时版本、capabilities、extensions 与 server 身份。
3. 每个请求 `_meta` 中的版本与客户端 capabilities；每个结果中的 `resultType` 与 server 身份。
4. 确定性的 `tools/list`，带 `ttlMs` 与 `cacheScope`。
5. 仅 POST 的 Streamable HTTP，强制 version、method、name 头；不使用协议会话、GET 流、会话 DELETE 或 replay 头。
6. 在每次调用时验证 issuer、audience、expiry 与 scopes 的授权。
7. 基于 actor、tool、target 与归一化参数执行策略。把高风险审批绑定到确切动作与过期时间，然后证明改动一个参数会拒绝重放。
8. 模型可见上下文之外的脱敏审计与 trace 证据。
9. 一个注册表 adapter，验证 `server.json`、探测 `server/discover`，并报告 metadata/运行时漂移。
10. 两个可互换副本，以及一个无会话亲和性的并发负载探针。

评估标准：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 协议正确性 | 无状态信封、发现、结果、头以及负向用例 |
| 20 | 授权 | issuer、audience、expiry、scope 以及确切动作审批用例 |
| 15 | 注册表完整性 | 合法 `server.json`、实时探测与漂移报告 |
| 15 | 策略与安全 | 允许、拒绝、畸形、过期审批与敏感数据用例 |
| 15 | 规模 | 两个无亲和性依赖的副本，加上取消与恢复 |
| 10 | 可审计性 | 脱敏的接收端审计与 trace 证据 |

硬性否决：

- 使用 `initialize`、`notifications/initialized` 或 `Mcp-Session-Id` 的当前 MCP 设计。
- 把 `server.json` 当作实时能力发现，或发明 `.well-known/mcp-capabilities` 作为 MCP 要求。
- 发布一个超出该发布者已认证命名空间的 server 名。
- 接受未经 issuer 与 audience 或资源验证的 token。
- 把 tool 注解或聊天审批当作授权。
- 持久化密钥或原始敏感数据的审计记录。

拒绝规则：

- 拒绝仅凭本地模拟就声称生产就绪。
- 拒绝在没有策略与动作绑定审批证据的情况下暴露会改变状态的 tool。
- 拒绝发布指向一个其实时发现无法验证的端点的 metadata。

输出：一个构建计划与证据矩阵，涵盖发布 metadata、实时发现、无状态传输、tool schema、授权、策略、审批、审计与规模。最后给出最高风险的边界，以及证明其 fail-closed 的确切失败测试。
