---
name: mcp-request-tracer
description: 逐条审计 MCP transcript，覆盖现代无状态时代与显式旧版协议时代。
version: 2.0.0
phase: 13
lesson: 06
tags: [mcp, json-rpc, stateless, metadata, compatibility]
---

给定一串 MCP JSON-RPC 信封，参照 MCP `2026-07-28` 逐条独立审计每个消息。检测旧版流量，但绝不假设存在握手或协议会话。

产出：

1. 消息注解。说明方向、JSON-RPC kind、method、原语、请求 id 与检测到的时代。
2. 现代元数据检查。对每个请求，校验 `params._meta.io.modelcontextprotocol/protocolVersion` 与 `params._meta.io.modelcontextprotocol/clientCapabilities`。记录推荐的 `clientInfo` 是否存在。
3. 结果检查。校验每个现代成功结果都有 `resultType: "complete"` 或其他指定的结果类型，并且结果 `_meta` 中带有推荐的 server 身份。
4. 发现与版本检查。校验现代 server 实现了 `server/discover`。把 `-32022` 解读为现代证据，并检查 `data.requested` 与 `data.supported`。
5. 缓存检查。对于 `server/discover`、列表方法与 `resources/read`，要求包含 `ttlMs` 与 `cacheScope`。标记非确定性的列表排序。
6. 方向检查。在现代流量中拒绝 server 发起的 JSON-RPC 请求。允许与请求相关的通知以及客户端打开的 `subscriptions/listen` 流。
7. 兼容性检查。仅把 `initialize` 与 `notifications/initialized` 标记为旧版。不要在现代流量中要求它们。

硬性拒绝：

- 把 stdio 进程、HTTP 连接或 `Mcp-Session-Id` 当作现代协议状态。
- 从更早的请求推断客户端 capabilities。
- 在收到 `-32020`、`-32021` 或 `-32022` 这类可识别的现代错误后回退到旧版。
- 接受没有 `resultType` 的现代成功结果。

拒绝规则：

- 如果 transcript 不是 JSON-RPC 2.0，停止并指出不兼容的信封。
- 如果被要求悄悄改写证据，拒绝。保留原始 transcript，并另外产出一个修正后的示例。

按到达顺序，每个消息输出一行：

```text
[request/modern/tools] id=7 tools/list metadata=valid
```

最后给出 modern、legacy、invalid 与 ambiguous 消息的计数，随后给出第一项纠正措施。
