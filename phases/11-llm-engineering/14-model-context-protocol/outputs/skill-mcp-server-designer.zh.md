---
name: mcp-server-designer
description: 设计一个无状态的 MCP 2026-07-28 server，并明确 discovery、state、transport 与 safety 契约。
version: 2.0.0
phase: 11
lesson: 14
tags: [llm-engineering, mcp, stateless, tool-use]
---

给定一个领域（内部 API、数据库、文件源）以及将要挂载该 server 的 host，输出：

1. Primitive 映射。哪些能力成为 `tools`（动作），哪些成为 `resources`（只读数据），哪些成为 `prompts`（用户调用的模板）。每个 primitive 一行。
2. Discovery 契约。起草 `server/discover`，写明实现支持的确切版本、capabilities、server 身份、instructions、`ttlMs` 与 `cacheScope`。
3. 请求契约。要求每个请求的 `params._meta` 中都携带字符串类型的协议版本和对象类型的 client capabilities。建议同时提供 client 身份。必需元数据缺失或类型不对时返回 Invalid Params（`-32602`）。仅当客户端提供了 server 未实现的版本文本时，才返回 `UnsupportedProtocolVersionError`（`-32022`），并带上 `data.supported` 与 `data.requested`。
4. 结果契约。为每个适用的结果加上 `resultType`、server 身份元数据、确定性的列表顺序与 cache 策略。
5. MRTR 方案。`input_required` 只用于 `tools/call`、`resources/read` 或 `prompts/get`。必须至少包含 `inputRequests` 或 opaque 的 `requestState` 之一；用新的 JSON-RPC ID、在被要求时带上对应的 input 响应、以及在存在时带上完全一致的 state 值，重试原方法。
6. State 方案。对每个多调用工作流，定义一个由 server 铸造的 opaque handle，作为普通 tool 参数传入。不要把 state 藏在连接或协议 session 背后。
7. Transport 与 auth 方案。选择 stdio 或 2026-07-28 Streamable HTTP POST endpoint。若用 HTTP，定义 Origin 校验与按请求的鉴权。POST 请求必须带 `MCP-Protocol-Version`，JSON-RPC 请求必须带 `Mcp-Method`，`Mcp-Name` 只用于 `tools/call`、`resources/read` 与 `prompts/get`。被接受的 notification POST 返回 HTTP 202 且无 body。
8. Schema 草稿。为每个 tool 参数写 JSON Schema，描述的措辞要利于模型选择，并对不可信输入给出明确的边界。
9. 破坏性操作清单。每个会改动状态的 tool 都标上 `destructiveHint: true`，并要求人工审批。
10. 验证方案。覆盖以下情形：notification 不产生 JSON-RPC 响应、畸形 envelope 与 request ID、元数据拒绝、discovery、确定性列表、版本不匹配、cache 字段、header 与 body 不一致、鉴权、审批，以及一个 prompt injection 案例。

拒绝把 `initialize`、`notifications/initialized`、`Mcp-Session-Id`、独立 HTTP GET、HTTP DELETE 或 `Last-Event-ID` 当作现代路径的设计。这些机制只允许放在一个明确隔离的 adapter 内，仅用于 2025-11-25 及更早的协议版本。不要在新实现中加入已废弃的 Roots、Sampling 或 Logging；兼容性支持必须明确标注，且 Roots 或 Sampling 的输入必须走 MRTR。拒绝任何未经鉴权、校验与审批路径就写磁盘或调用外部 API 的 server。
