# 无状态 MCP Gateway 与 Registry 准入

> gateway 应当让每条路由都显式可见。2026-07-28 协议为它提供了 method、name、version、capability、identity、cache 和 trace 边界，而无需 transport session。

**Type:** Learn
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 15 课（security）、第 13 阶段，第 16 课（authorization）
**Time:** ~75 分钟

## Learning Objectives

- 在无 session 亲和性的情况下，把多个 MCP server 聚合到一个 2026-07-28 endpoint 之后。
- 在策略判定或转发之前校验每请求的 metadata 和路由 header。
- 用稳定的命名空间、确定性顺序、descriptor pin、RBAC 和私有缓存合并 tools。
- 把 registry 记录视为发现证据，它们仍然需要准入策略。
- 正确路由请求作用域的 SSE、`subscriptions/listen`、MRTR 重试和 Tasks 扩展调用。
- 把旧式握手与 session 支持同现代路径隔离开。

## 问题场景

把一个 client 直接接到一个 server 上很简单。规模更大的部署需要对更难的问题给出一致答案：

- 允许哪些 server？
- 哪个 principal 可以看到并调用每个 tool？
- 两个 backend 暴露同名 tool 时怎么办？
- descriptor 变更如何审核？
- 限流和审计事件在哪里施加？
- 任意一个实例都能处理下一个请求吗？

gateway 位于 client 和 backend MCP server 之间。它提供一个 MCP endpoint，施加横切策略，并转发获批的请求。

较早的 gateway 设计常常把一个 client session 多路复用成多个 backend session，并重写 `Mcp-Session-Id`。那是一种遗留兼容设计。2026-07-28 核心没有协议 session。

## 核心概念

### 现代 gateway 路径

对每个请求：

1. 根据 transport 授权认证 principal。
2. 校验 `MCP-Protocol-Version`、`Mcp-Method`、`Mcp-Name` 和 `params._meta`。
3. 对 principal、resource、method、tool 和 arguments 做授权。
4. 施加 descriptor、registry、限流和数据策略。
5. 为选定的 backend 创建一个全新的自包含请求。
6. 校验 backend 结果并返回 gateway 结果。
7. 记录审计事件，不记录 secret。

任何一步都不需要隐藏的协议 session。应用状态仍可存在于数据库、显式 handle、Tasks 或受完整性保护的 MRTR 状态中。

### 运行时策略是 gateway 的首要决策

准入决定哪个 backend 版本可以进入 gateway，它并不授权一次实时调用。对每个请求，gateway 都根据已认证的 principal、issuer 与 resource、tenant、匹配到的 method 与 name、归一化后的 arguments、已准入的 descriptor pin、当前 backend 健康状态、capability 交集、数据分级、限流状态以及任何与操作绑定的审批，重新计算策略。

这个顺序很重要。Registry 记录可以保持有效，而用户的角色已被撤销。descriptor 可以保持 pin，而某个目标参数越过了 tenant 边界。backend 可以保持已批准，而事件策略隔离了改变状态的操作。因此运行时策略才是准许或拒绝的首要决策，Registry 和 descriptor 证据只是输入。

不要在连接或已移除的 session 标识符之下缓存允许决策。如果策略不可用，就按操作类别遵循已声明的失败策略。一个安全的默认是：对状态变更和敏感读取 fail closed；只有在风险模型允许时，明确批准的公开只读路径才可以使用短时效的 last-known 策略。记录是哪个策略版本和哪条失败路径做出了决策，然后在返回前校验 backend 结果。

### 单一 POST endpoint

现代 Streamable HTTP 通过 POST 发送每一条 JSON-RPC 消息：

```text
POST /mcp
Authorization: Bearer <gateway-token>
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.search
Accept: application/json, text/event-stream
```

gateway 可以为该 POST 返回 JSON 或请求作用域的 SSE。对现代请求，GET 和 DELETE 返回 405。`Mcp-Session-Id` 和 `Last-Event-ID` 不会产生权威、亲和性或重放行为。

header 与 body 的值必须一致。在查找 backend 之前，用 `-32020` 拒绝不匹配。这样负载均衡器、gateway 和限流器无需解析完整 body 即可路由，同时保持端到端的完整性。

按一个精确顺序校验：先校验 JSON-RPC 和 metadata 类型，再校验 header 与 body 的一致性，最后校验对匹配版本的支持。不匹配返回 HTTP 400 和 `-32020`。如果 header 与 body 一致地指向不受支持的版本，返回 HTTP 400 和 `-32022`，且 `data` 精确为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。未知 method 返回 HTTP 404 和 `-32601`。

`ProtocolError` 携带可选的 `data`，gateway 会把它序列化进 JSON-RPC 错误对象。notification 没有 `id`，因此永远不会收到 JSON-RPC 成功或错误响应。被接受的 HTTP notification 返回 202 和空 body。

### 在每一层实现 discovery

gateway 为 client 实现 `server/discover`。它也会发现每个 backend，从而了解协议版本、capabilities 和扩展。

gateway 结果示例：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {"listChanged": true}
  },
  "ttlMs": 30000,
  "cacheScope": "private",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "enterprise-gateway",
      "version": "2.0.0"
    }
  }
}
```

只声明 gateway 能够端到端兑现的 capability 交集。backend 的特性并不自动意味着可以安全暴露；没有 backend 路径的 gateway 特性也不值得声明。

`serverInfo` 是自报的展示与诊断数据，不要把它当作 registry 或发布者的证明。

### 每请求的 client capabilities

每个被转发的请求都需要当前的 `_meta` 信封：

```json
{
  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
  "io.modelcontextprotocol/clientCapabilities": {},
  "io.modelcontextprotocol/clientInfo": {
    "name": "enterprise-gateway",
    "version": "1.0.0"
  }
}
```

不要盲目把外层 client 的 capabilities 复制给 backend。gateway 才是 backend 的 client，只声明 gateway 会正确中介的特性。

### 确定性的命名空间

在稳定的公开名称下合并 backend 的 tools：

```text
notes.search
notes.create
issues.list
issues.open
```

维护一份从公开名称到 backend 及原始 tool 名称的映射。永远不要选择冲突中的第一个或最后一个。公开名称是审批与审计契约的一部分，因此修改它属于迁移。

`tools/list` 必须是确定性的。当可见性因 principal 而异时，返回 `cacheScope: private`。有界的 `ttlMs` 可降低 backend discovery 负载，同时不允许用户特定列表跨授权上下文泄漏。

每个暴露的 tool descriptor 都包含稳定的 name、description 和对象根 `inputSchema`。命名空间化不能移除必需的 descriptor 字段。完整的列表结果还包括 `resultType`、server 身份 metadata 和缓存提示。

### 固定已批准的 descriptor

在准入时，把完整 descriptor 规范化，并将其摘要存储在该限定后的公开名称下。在列表和调用时，把实时 descriptor 与已批准的摘要比较。

如果它发生变化：

- 从 `tools/list` 中移除它。
- 拒绝直接调用。
- 生成审计事件。
- 在更新 pin 之前要求策略或人工重新审批。

gateway 是有用的集中执行点，但它不会把首次见到的 descriptor 变成安全的 descriptor。初次审核仍然必要。

### Registry 帮助发现，而非决策

Registry 的 `server.json` 提供发布 metadata。一条基于 package 的记录可能像这样：

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "com.example/notes",
  "description": "Example notes MCP server.",
  "version": "1.0.0",
  "packages": [
    {
      "registryType": "npm",
      "identifier": "@example/notes-mcp",
      "version": "1.0.0",
      "transport": {"type": "stdio"}
    }
  ]
}
```

发布 metadata 并不承载 gateway 的安全决策。把已验证的发布者和来源证据保存在独立的准入状态中：

```json
{
  "registryName": "com.example/notes",
  "registryVersion": "1.0.0",
  "publisher": {"namespace": "com.example", "status": "verified"},
  "provenance": {
    "source": "registry.modelcontextprotocol.io",
    "recordId": "com.example/notes@1.0.0"
  },
  "admission": {"status": "approved", "reviewedBy": "gateway-policy"}
}
```

gateway 检查 `server.json` 的结构，并把它与那份外部状态关联。gateway 仍然需要准入策略。

对每个已准入的 backend，记录：

- 精确的 registry 与记录标识符。
- 已验证的发布者命名空间或域名证据。
- 允许的 transport 和 endpoint。
- 固定的版本或已批准的升级策略。
- 工件或 descriptor 摘要。
- 授权 issuer 与 resource。
- 审核人、批准时间和过期时间。

不要因为 server 的展示名称像某个熟悉的产品就接受它。不要把登记在 registry 中当作一次运维安全审核。私有 server 即使从未出现在公共 registry 中，也可以通过同一套证据 schema 获得准入。

本课实现了 gateway 的这个接缝：在 backend 变得可路由之前，把发布证据与本地准入关联起来。[第 30 课：MCP Registry 供应链、准入、漂移与回滚](../../30-mcp-registry-supply-chain-and-drift/docs/en.md) 构建了完整的控制平面，涵盖精确的命名空间证明、工件来源、不可变 pin、实时 descriptor 漂移、Registry 状态对账、防篡改的准入账本以及有证据支撑的回滚。把那份供应链状态与上面的每请求运行时决策保持分离。

### 凭据中介

gateway 认证其调用方，并单独向 backend 认证。backend 的凭据永远不会到达 client。

明确保持这些绑定：

```text
outer principal -> gateway role and policy
backend issuer + resource -> backend registration and token
```

永远不要把外层 gateway token 传给 backend。永远不要在不同的 issuer 或 resource 处复用 backend token。如果某个 tool 代表最终用户行事，就通过设计好的 exchange 或 claims 模型保留这种委托关系，而不是用共享的 service 凭据冒充该用户。

### 无 session 的限流

按已认证的 principal、issuer、resource、公开 tool、成本类别和时间窗口作为限流键。session id 已不存在，即使存在也很容易被轮换。

在消耗昂贵工作之前施加廉价校验。决定被拒绝的调用是否计入滥用限额、业务配额，还是两者都计入。

### 审计决策链

记录足以重建一次调用的信息：

- 请求与 trace 标识符。
- 已认证的 principal 与 issuer。
- 公开 tool 与 backend 路由。
- descriptor pin 版本。
- 策略决策与原因。
- 时延与结果类别。
- 适用时的 MRTR 轮次或 task 标识符。

脱敏 bearer token、authorization code、refresh token、原始 secret 以及不必要的敏感参数。

### 请求作用域的 SSE

当工作在某一个请求期间流式输出时，普通的 POST 可以返回请求作用域的 SSE。关闭响应流即取消该在途的现代 HTTP 请求。

不要创建单独的 GET 流，也不要承诺 Last-Event-ID 重放。那些是更早的 transport 假设。

### 长时间运行的变更通知

对于列表和 resource 变更通知，当前 client 通过 POST 发送 `subscriptions/listen` 并收到 SSE 响应。通知过滤器使用精确的扁平字段 `toolsListChanged`、`promptsListChanged`、`resourcesListChanged` 和 `resourceSubscriptions`：

```json
{
  "jsonrpc": "2.0",
  "id": "listen-tools",
  "method": "subscriptions/listen",
  "params": {
    "notifications": {
      "toolsListChanged": true
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

第一个事件确认所支持的子集。它的订阅标识符就是打开该流的请求的 JSON-RPC id：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/subscriptions/acknowledged",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": "listen-tools"
    },
    "notifications": {
      "toolsListChanged": true
    }
  }
}
```

此后 gateway 只转发已确认的变更类型。该流上的每个 notification 都在 `params._meta` 中携带相同的 `io.modelcontextprotocol/subscriptionId`。不存在自动重放或自动重新监听。重连时，client 重新打开订阅并刷新它所依赖的列表。server 发起的优雅关闭会返回一个带有相同订阅 id 的最终 complete 结果。

现代路径取代了 `resources/subscribe`、`resources/unsubscribe` 以及未经请求的独立 GET 流。只把它们保留在按版本门控的旧路径中。

### 经由 gateway 的 MRTR

当 backend 返回 `resultType: input_required` 时，只有外层 client 支持所需的 input request，gateway 才能转发该结果。除非 gateway 有意终止并重新发起交互，否则要逐字节保留 `requestState`。

client 用全新的 JSON-RPC id 和 `inputResponses` 重试原来的公开 tool。gateway 对重试重新授权，检查同一公开路由，然后转发一个全新的 backend 请求。它不得假定先前某一轮已授予无限审批。

### Tasks 扩展的路由

Tasks 是由 `io.modelcontextprotocol/tasks` 标识的官方扩展，它们不是核心 session 的替代品。

client 在每请求的 client capabilities 中声明该扩展，gateway 只有在能够端到端保留其生命周期时才在 discovery 中声明它。对于受支持的 `tools/call`，由 backend 单方面决定返回普通结果还是 `resultType: task`。task 结果直接在结果中携带 `taskId`、`status`、时间戳、`ttlMs` 以及可选的 `pollIntervalMs`。在发送该结果之前，task 必须已经可持久读取。

gateway 为不透明的 task 标识符记录已认证的 principal 和 backend 路由。后续的 `tasks/get`、`tasks/update` 和 `tasks/cancel` 调用用 `params.taskId` 作为 `Mcp-Name`，这为中间层提供了路由键。`tasks/get` 返回 `resultType: complete` 及当前 task 状态，并在终态时内联最终结果或协议错误。`tasks/update` 为未决的 task input 发送带键的 `inputResponses`，并返回空的 complete 确认。`tasks/cancel` 是一种协作式意图，返回空的 complete 确认，并不保证工作停止。

不要实现新的 `tasks/list` 或 `tasks/result` method。它们属于更早的实验模型。需要输入的 task 通过 `tasks/get` 暴露完整的嵌入式请求；client 通过 `tasks/update` 回答这些请求，而不是重试原来的 tool 调用。client 仍然按建议的间隔轮询；task 的创建始终由 server 主导。

持久化的 task 路由状态是以 task handle 为键的应用数据，而不是协议 session。

### 兼容性边界

如果 gateway 必须服务较旧的 client 或 backend：

- 显式检测协议年代。
- 把 initialization、transport session、GET 流、resource 订阅和旧 task 词汇都留在 legacy adapter 内。
- 永远不要把 legacy session id 泄漏到现代路由或授权中。
- 优先使用有界的 discovery probe 和显式回退策略，而不是静默降级。

```figure
t3-gateway-funnel
```

## Build It

`code/main.py` 实现了一个进程内协议 gateway 和两个 backend server。每个 backend 都会收到一个全新的当前协议请求。gateway 提供 discovery、按用户过滤的确定性 `tools/list`、命名空间路由、Registry `server.json` 加外部准入状态、descriptor pin、RBAC、按 principal 为键的限流、审计决策，以及一个模拟的 `subscriptions/listen` SSE 确认。

该模型接收已解析的请求 body、路由 header 和一个已认证的 bearer 身份。它不是完整的 HTTP adapter，也不解析 `Content-Type` 或完整的 `Accept` 契约。请将它接到第 09 课的 Streamable HTTP adapter 上，后者要求 `Content-Type: application/json`，且 `Accept` 值同时包含 `application/json` 和 `text/event-stream`。

运行它：

```bash
cd phases/13-tools-and-protocols/17-mcp-gateways-and-registries
python3 code/main.py
python3 -m unittest discover code/tests -v
```

demo 会打印外层请求 id 和全新的 backend 请求 id，从而让无状态的跳跃清晰可见。

## Use It

用真实的当前协议 client 替换进程内的 backend 对象。保持相同的接缝：

- 连接之前的准入记录。
- 暴露 capability 之前的 backend discovery。
- 授权之前的限定的公开名称。
- 列表或调用之前的 descriptor pin。
- 转发之前的全新每请求 metadata。
- 返回之前的结果校验。

## Ship It

本课交付 `outputs/skill-gateway-bootstrap.md`。它产出一份现代 gateway 设计，涵盖 ingress、discovery、准入、命名空间、授权、缓存、流式、订阅、MRTR、Tasks、可观测性以及 legacy 隔离。

## Exercises

1. 给外层和转发请求的 metadata 添加 trace context，并在审计事件中记录这种关联。
2. 添加一个支持 Tasks 的 backend，并在 `Mcp-Name` 中按 task id 路由 `tasks/get`。
3. 修改某个 backend descriptor，证明 discovery 和直接调用都会被阻止。
4. 添加一个 principal 特定的 server capability，并解释为什么 discovery 必须保持私有缓存。
5. 编写一个 legacy adapter 接口，同时不向现代 `Gateway` 类添加任何 legacy 状态。

## Key Terms

| 术语 | 含义 |
|------|---------|
| MCP gateway | 位于 client 与 backend MCP server 之间的策略与路由 server |
| Admission record | 允许某个 backend 进入 gateway 的证据与策略决策 |
| Qualified tool name | 稳定的公开路由，例如 `notes.search` |
| Descriptor pin | 在 discovery 和 dispatch 期间校验的已批准摘要 |
| Private cache scope | 限于单个授权上下文的缓存结果 |
| Request-scoped SSE | 附着于单个 POST 请求的流式响应 |
| `subscriptions/listen` | 由 client 打开的 SSE 流，用于选定的长期变更通知 |
| Task route | 从不透明 task id 到其 backend 的应用映射 |
| Legacy adapter | 用于旧式握手与 session 行为的、显式按版本门控的边界 |

## Further Reading

- [Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [服务器发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [官方 Registry server.json 要求](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
- [MCP Tasks 扩展](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)
