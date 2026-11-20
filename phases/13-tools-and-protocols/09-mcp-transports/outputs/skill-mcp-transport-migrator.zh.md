---
name: mcp-transport-migrator
description: 把旧版 MCP HTTP 传输迁移到无状态、仅 POST 的 2026-07-28 契约。
version: 2.0.0
phase: 13
lesson: 09
tags: [mcp, streamable-http, stateless, migration, headers]
---

给定一个基于会话的 Streamable HTTP 或 HTTP+SSE server，产出一份面向 MCP `2026-07-28` 的迁移 runbook。

产出：

1. 端点映射。定义一个接受 POST 的现代 MCP 端点。每个 JSON-RPC 请求或通知都收到一次新的 POST。
2. 响应映射。对单条响应用 `application/json`；对先发相关通知、后发最终响应的场景用请求作用域的 `text/event-stream`。
3. 已移除的行为。对现代 GET 与 DELETE 返回 `405`。忽略 `Mcp-Session-Id` 与 `Last-Event-ID`；绝不签发、回显、撤销或恢复它们。
4. 请求元数据。在每个请求体 `_meta` 中要求协议版本与客户端 capabilities，并附带推荐的客户端身份。
5. 头部校验。要求 `MCP-Protocol-Version`、`Mcp-Method` 以及按条件要求的 `Mcp-Name`。解码 Base64 哨兵，并将头部与请求体比对。不一致时返回 `-32020`。匹配但版本不受支持时返回 `-32022`，并带精确的数据键 `supported` 与 `requested`。
6. 订阅迁移。用 POST `subscriptions/listen` 取代独立 GET、`resources/subscribe` 与 `resources/unsubscribe`。给确认消息、每条通知与最终结果都打上 `io.modelcontextprotocol/subscriptionId`，其值等于 listen 请求 id。
7. 状态迁移。用绑定到已认证主体的显式不透明应用句柄，取代连接亲和性。
8. 兼容窗口。把较旧的端点分开保留并清楚标注。在任何旧版回退之前，必须先检查现代 POST 的错误。不要用 `301` 或 `302` 重定向 POST，因为方法体与请求体的保留并不安全。
9. 验证。测试 Origin 拒绝、POST 媒体类型协商、请求体元数据、镜像头部、JSON 响应、被接受通知的 `202` 无响应体、作用域化 SSE 订阅元数据、GET 与 DELETE 的 `405`、被忽略的已移除头部，以及流中断后用新 id 重试。

硬性拒绝：

- 把 session id、独立 GET、DELETE 或回放呈现为现代行为。
- 通过进程或连接内存共享逐请求的 capabilities。
- 发送 server 发起的 JSON-RPC 请求。
- 用 `Last-Event-ID` 恢复现代 SSE 流。
- 在可识别的现代错误之后回退到旧版。
- 在迁移期间用重定向移动一个 JSON-RPC POST。

拒绝规则：

- 在没有身份认证、授权与精确 Origin 策略的情况下，拒绝公开暴露。
- 拒绝把隐藏的粘性路由当作显式 workflow 状态的替代品。
- 在没有应用层幂等控制的情况下，拒绝自动重试非幂等操作。

输出一张前后对比的端点表、分阶段发布计划、回滚边界，以及一份可执行的合规清单。最后给出旧版路由将被移除的确切日期。
