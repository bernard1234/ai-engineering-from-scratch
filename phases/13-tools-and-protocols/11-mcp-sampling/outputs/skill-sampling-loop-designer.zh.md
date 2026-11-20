---
name: sampling-loop-designer
description: 把模型辅助的 MCP 工具迁移到直接推理，或迁移到带受约束兼容 sampling 的无状态 2026-07-28 MRTR。
version: 2.0.0
phase: 13
lesson: 11
tags: [mcp, mrtr, sampling, stateless, migration]
---

为一个面向协议版本 `2026-07-28` 的 MCP server 设计模型辅助行为。

从一项决策开始：这个 server 能否直接与模型提供方集成？Sampling 对新设计已弃用。除非使用客户端的模型和凭据是明确的产品需求，否则优先选择直接集成。

产出：

1. 架构决策。选择直接推理或兼容 Sampling，并说明理由。
2. Discovery 契约。给出 `server/discover`，包含精确的 `supportedVersions`、宣告的 capabilities、`ttlMs` 和 `cacheScope`。如果宣告了 tools，就要包含强制的确定性 `tools/list` 描述符，带合法的对象 `inputSchema`、`resultType: "complete"`、server 身份元数据和缓存提示。
3. 请求信封。在每个请求的 `_meta` 中包含协议版本和客户端能力。版本缺失或不是字符串时用 `-32602`；版本不受支持时用 `-32022` 并给出精确的 `supported` 和 `requested` 数据；缺少 Sampling 时用 `-32021` 并给出 `requiredCapabilities` 对象。客户端身份元数据仅作信息参考。绝不要为没有 id 的 notification 发出 JSON-RPC 响应；被接受的 HTTP notification 返回不带 body 的 `202`。
4. 轮次表。对每一轮 MRTR，列出 `inputRequests` 键、内嵌请求方法、期望的响应 schema、校验和预算。
5. 重试契约。要求使用原始方法和参数、新的 JSON-RPC id、当前轮的 `inputResponses`，以及逐字节一致的 `requestState`。
6. 状态保护。把 HMAC 或认证加密绑定到已认证的 principal、方法、参数摘要、阶段和较短的过期时间。
7. 安全策略。定义审批、最大轮数、token 与字节限制、响应校验、日志记录和拒绝行为。
8. 移除计划。如果保留 Sampling，写明用直接集成替换它的条件和日期。

硬性拒绝：

- 在没有成文需求的情况下，新设计采用已弃用的 Sampling。
- 2026-07-28 的 server 把 `sampling/createMessage` 作为实时的 server 到 client 请求发送。
- 任何对 `initialize`、`notifications/initialized`、`Mcp-Session-Id` 或隐藏协议会话状态的使用。
- 影响授权、资源访问或业务逻辑的未签名 `requestState`。
- 重试时复用原始 JSON-RPC id 或改动原始参数。
- 没有能力检查、审批策略、校验和硬性轮数上限的客户端模型循环。
- `includeContext: "allServers"` 或隐式的跨 server 上下文。

拒绝规则：

- 拒绝隐蔽的模型调用，或任何向用户隐瞒 server 意图的设计。
- 拒绝把模型输出当作身份、授权或用户同意的证据。
- 当一次确定性的工具调用就已足够时，拒绝多轮设计。
- 拒绝对 client 和 server 元数据称其为已认证的身份。

输出一份单页架构，包含决策、wire 流程、轮次表、签名 state 的内容、安全预算、失败情形和迁移计划。最后给出结论：`direct inference`、`temporary MRTR compatibility` 或 `no model required`。
