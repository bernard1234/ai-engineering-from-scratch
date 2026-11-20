# MCP 传输：stdio 与无状态的 Streamable HTTP

> 传输层负责承载 MCP 消息。它不提供缺失的协议状态。在 `2026-07-28` 中，本地 stdio 与远程 Streamable HTTP 都承载自描述请求。

**Type:** Learn
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 与 08 课
**Time:** ~65 分钟

## Learning Objectives

- 为本地子进程选择 stdio，为网络服务选择 Streamable HTTP。
- 实现现代的单一端点、仅 POST 的 Streamable HTTP 契约。
- 将 MCP 版本、方法与 name 头部与 JSON-RPC 请求体互相镜像并校验。
- 正确地投递请求作用域的 SSE 与长时间存活的 `subscriptions/listen` 流。
- 迁移基于会话的以及旧版 HTTP+SSE 部署，同时不把旧版行为呈现为现代行为。

## 问题场景

更早的 Streamable HTTP 修订版把协议协商与连接、会话行为混在一起。server 可以签发 `Mcp-Session-Id`、暴露独立的 GET 流、接受 DELETE 来终止会话，并用 `Last-Event-ID` 恢复 SSE。

MCP `2026-07-28` 从现代线上契约中移除了这些机制。每个请求都可以落到任意健康的 worker 上，因为它的协议版本与客户端 capabilities 都在请求体内传递。HTTP 头部为路由与策略而镜像选定的字段，但 server 在执行之前会用请求体校验这些头部。

结果是更容易扩展，也更容易推理。这也意味着，一个把 2025 传输当作当前方案来教授的 server，教的是错误的失败模型与安全模型。

## 核心概念

### stdio

stdio 绑定面向由客户端启动的子进程：

- 客户端每行向 stdin 写入一条 UTF-8 编码的 JSON-RPC 消息。
- server 每行向 stdout 写入一条 UTF-8 编码的 JSON-RPC 消息。
- server 把诊断信息写入 stderr。
- server 在 stdin EOF 时立即退出。
- 每个现代请求都在 `params._meta` 中携带版本与客户端 capabilities。

进程可以存活很多次调用，但它不是现代协议会话。如果它意外退出，在途请求就会丢失。重启进程、重新发现、重新列出、重新打开订阅，并用新的请求 id 重试安全操作。

### 2026-07-28 中的 Streamable HTTP

现代 server 暴露一个 MCP 端点，例如 `/mcp`，它接受 POST。

每个 JSON-RPC 请求或通知都是一个全新的 HTTP POST。请求体包含一条 JSON-RPC 消息。客户端不向 server 发送 JSON-RPC 响应。

对于一个请求，server 返回以下之一：

- `Content-Type: application/json`，携带一条 JSON-RPC 响应；或
- `Content-Type: text/event-stream`，携带与该请求相关的通知，随后是最终的 JSON-RPC 响应。

对于已被接受的通知，server 返回 `202 Accepted`，且无响应体。

客户端对两种响应类型都进行声明：

```http
Accept: application/json, text/event-stream
```

### 仅 POST 就是仅 POST

现代 Streamable HTTP 没有独立的 GET 流，也没有 DELETE 会话端点。

- `GET /mcp` 返回 `405 Method Not Allowed`。
- `DELETE /mcp` 返回 `405 Method Not Allowed`。
- `Mcp-Session-Id` 被忽略，且永远不会被签发或回显。
- `Last-Event-ID` 被忽略，因为现代流不可恢复。

如果请求作用域的流在最终响应之前中断，客户端就失去了那条在途请求。当重试安全时，它可以用新的 JSON-RPC id 发起新请求。它绝不能尝试恢复流。

### Origin 校验

server 在校验入站连接时检查 `Origin`，以防止 DNS rebinding。如果该头部存在且未被显式允许，返回 `403 Forbidden`。非浏览器客户端可以省略 `Origin`，官方传输规则允许这样做。

本地 server 应绑定到 `127.0.0.1`，而不是所有网络接口。网络服务仍然需要对每个请求进行身份认证与授权。Origin 校验不是认证。

在完成规范化配置之后，使用精确的 origin 匹配。像 `origin.startswith("https://trusted.example")` 这样的前缀检查是不安全的，因为它可能接受攻击者控制的后缀。

### 必需的 HTTP 元数据头部

每个现代 POST 请求都包含：

```http
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes_search
```

头部规则：

- `MCP-Protocol-Version` 是必需的，且必须等于 `params._meta.io.modelcontextprotocol/protocolVersion`。
- `Mcp-Method` 是必需的，且必须等于 JSON-RPC 的 `method`。
- `Mcp-Name` 对 `tools/call`、`resources/read` 与 `prompts/get` 是必需的。
- `Mcp-Name` 等于 `params.name`，对于 `resources/read` 则等于 `params.uri`。
- 头部值区分大小写，尽管头部名称不区分大小写。

不安全或非 ASCII 的 `Mcp-Name` 值使用精确的 UTF-8 Base64 哨兵：

```text
=?base64?{Base64EncodedValue}?=
```

server 在将它与请求体比对之前先解码该值。

缺失、格式错误或不匹配的镜像头部返回 HTTP `400`，并带 JSON-RPC 错误码 `-32020`。如果头部与请求体在某个 server 不支持的版本上一致，返回 HTTP `400` 与 `-32022`，并使用精确的错误数据，例如 `{"supported":["2026-07-28"],"requested":"2027-01-01"}`。

未知的现代方法返回 HTTP `404` 与 JSON-RPC 错误码 `-32601`。JSON-RPC 响应体很重要，因为双时代客户端会用它将现代错误与旧版端点的未命中区分开。

### 请求作用域 SSE

server 可以为某一个长时间运行的请求选择 SSE：

```text
POST tools/call id=41
  <- notifications/progress related to id=41
  <- notifications/progress related to id=41
  <- JSON-RPC response id=41
stream closes
```

server 不得在这条流上发送独立的 JSON-RPC 请求。Sampling、elicitation 与 roots 交互使用 Multi Round-Trip Request 结果。关闭响应流会取消该请求。

不要为回放添加 SSE 事件 id。`Last-Event-ID` 恢复不属于现代修订版。

### 长时间存活的变更使用 subscriptions/listen

变更通知使用客户端打开的请求，而不是独立的 GET：

```json
{
  "jsonrpc": "2.0",
  "id": "listen-1",
  "method": "subscriptions/listen",
  "params": {
    "notifications": {
      "toolsListChanged": true,
      "resourceSubscriptions": ["notes://note-1"]
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      }
    }
  }
}
```

POST 响应是一条长时间存活的 SSE 流。它的第一条协议消息是 `notifications/subscriptions/acknowledged`。确认消息、每条变更通知以及最终结果都在 `_meta` 中携带 `io.modelcontextprotocol/subscriptionId`，其值等于 listen 请求 id。server 可以发送 SSE 注释作为 keepalive。当流断开时，客户端用新的请求 id 重新发起 `subscriptions/listen`，并重新获取受影响的数据。

`resources/subscribe` 与 `resources/unsubscribe` 属于旧版时代。不要在现代连接上使用它们。

### 显式的应用状态

移除协议会话并不禁止有状态的 workflow。server 可以签发一个不透明的状态句柄，并将其作为普通 tool 结果返回。客户端在后续调用中把该句柄作为显式参数传入。

把句柄绑定到已认证的主体，让它们不可猜测，为它们设置过期时间，并对每次使用进行授权。这使状态在应用层可见，而不是隐藏在传输亲和性中。

由隐藏副本状态引发的故障是机械性的：

1. 请求 A 到达副本 1，并在该进程的内存中创建一个 draft。
2. 响应没有返回 draft 句柄，因为实现假设连接本身就标识了该 draft。
3. 请求 B 是一次全新的 POST，到达副本 2。
4. 副本 2 拥有合法的协议元数据，却无法命名或加载该 draft，因此 workflow 失败或读到了错误的本地对象。
5. 粘性路由看似修复了症状，直到重启、发布、重新调度或故障转移把下一个请求移走。

正确的边界包含两部分。协议上下文留在每个请求中。持久应用状态位于共享存储中，由 server 签发、返回给客户端的句柄引用。下一次调用提供该句柄，任意副本都会加载同一条记录，授权把该记录绑定到已认证的主体与租户。副本内存可以缓存一条记录，但它不能成为正确性所依赖的唯一副本。

按生命周期选择状态机制。请求局部变量只能服务于一次调用。简短的 MRTR 续作可以使用受完整性保护的 `requestState`。draft 或持久 task 需要显式句柄，外加共享持久化、过期、并发控制与幂等性。这些对象中没有一个属于 MCP 协议会话。

### HTTP 双时代兼容

同时支持现代与旧版 server 的客户端会先尝试现代 POST。如果收到 HTTP `400`、`404` 或 `405`，它会检查响应体：

- 可识别的现代 JSON-RPC 错误证明 server 是现代 server。修正请求，或重试一个已通告的版本。不要降级。
- 空响应体或无法识别的响应，可能表示一个旧版 HTTP+SSE server。只有这时才尝试旧的 GET 端点，并期待它发出旧版 `endpoint` 事件。

在迁移期间，server 可以通过把现代元数据路由到现代的仅 POST 实现、同时为旧客户端保留独立的旧版端点，来同时支持两个时代。绝不把旧版 GET、DELETE、session id 或回放行为描述为 `2026-07-28` 的一部分。

```figure
tp-transport-handshake
```

## Use It

`code/main.py` 用 Python 标准库实现了一个有限的现代 Streamable HTTP server。它校验 Origin 与镜像头部，忽略已移除的会话头部，对普通调用返回 JSON，并演示一条有限的 `subscriptions/listen` SSE 流。

```bash
cd code
python3 main.py --probe
python3 -m unittest discover tests -v
```

探测会检查：

- 非法的 Origin 会被拒绝；
- 在没有 session id 的情况下发现仍然成功；
- `Mcp-Session-Id` 与 `Last-Event-ID` 被忽略；
- 头部不一致返回 `-32020`；
- 不受支持的版本返回 `-32022`，并带精确的 `supported` 与 `requested` 数据；
- 一条被接受的无 id 通知返回 HTTP `202` 且无响应体；
- GET 与 DELETE 返回 `405`；
- `subscriptions/listen` 是一条 POST 响应流，其确认、通知与最终结果都携带它的 subscription id。

## Ship It

本课交付 `outputs/skill-mcp-transport-migrator.md`。它会移除现代协议会话、添加头部-请求体校验、用 `subscriptions/listen` 取代独立 GET，并把任何旧版桥接保持为明显分离。

## Exercises

1. 从某个 POST 中移除 `Mcp-Method`。确认返回 HTTP `400` 与错误 `-32020`。
2. 发送头部与请求体版本匹配的 `2027-01-01`。确认返回 HTTP `400`、错误 `-32022`，以及精确数据 `{"supported":["2026-07-28"],"requested":"2027-01-01"}`。
3. 为一个非 ASCII 的资源 URI 发送使用 Base64 哨兵的 `Mcp-Name`。确认解码后的值与 `params.uri` 进行了比对。
4. 在有限的 listen 流返回最终响应之前中断它。用新的 JSON-RPC id 重新发起，并重新获取 tools。
5. 在 ping tool 中加入一个显式 workflow 句柄。把它绑定到某个授权主体，而不使用连接亲和性。

## Key Terms

| 术语 | 含义 |
|------|---------|
| stdio | 在客户端启动的子进程上按换行分隔的 JSON-RPC |
| Streamable HTTP | 单一端点，每条现代消息都是一次新的 POST |
| 请求作用域 SSE | 包含相关通知与最终响应的 POST 响应流 |
| `subscriptions/listen` | 用于按需选择变更通知的长时间存活 POST 请求 |
| 头部不一致 | 镜像头部与请求体不一致时返回 HTTP `400` 与 JSON-RPC `-32020` |
| Origin 校验 | 针对入站连接的 DNS rebinding 防御，不是认证 |
| 显式状态句柄 | 作为普通参数传递的应用层令牌，而非隐藏的会话状态 |
| 旧版桥接 | 仅为兼容而保留的、分离的更早时代行为 |

## Further Reading

- [MCP 传输概览](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [MCP stdio 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP 订阅](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [MCP 2026-07-28 变更日志](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
