# Model Context Protocol（MCP）

> MCP 给 AI host 提供一套统一的协议，用来发现和调用 tool、resource 和 prompt。2026-07-28 修订版让这套协议变成无状态的：能力与版本上下文随每个请求一起传递，而不是放在与连接绑定的握手里。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 · 09 (Function Calling), Phase 11 · 03 (Structured Outputs)
**Time:** ~75 分钟
## Learning Objectives

- 区分 MCP host、client、server、transport 和 server primitive。
- 构造一个带有 MCP 2026-07-28 所要求 metadata 的 JSON-RPC 请求。
- 用 `server/discover` 检查版本、身份和能力。
- 从 tool、resource 和 prompt 返回带类型且 cache-aware 的结果。
- 解释现代无状态 MCP 如何与握手时代的 server 互操作。
- 为 server 选择安全的状态、transport 和审批边界。

## 问题场景

你的应用需要一个数据库查询、一个日历操作和一个文件读取器。没有共享协议，每个 AI host 都得为这些相同的能力各自实现发现、调用、错误处理、transport 和授权胶水。

MCP 压缩了这张集成矩阵。server 发布一个标准的 JSON-RPC 接口面。一个兼容的 client 就能发现这个接口面、把它呈现给模型或用户、发起调用并解释结果，无需针对特定 server 写适配器。

有一个重要边界很容易被忽略。MCP 只标准化通信。它不决定模型应该调用哪个 tool，不让不可信内容变安全，也不会把无状态请求变成持久化的应用状态。这些决策仍然由你的 host 和 server 负责。

## 核心概念

![MCP host、无状态请求与 server primitive](../assets/mcp-architecture.svg)

### 三种 server primitive

1. **Tool** 是可调用的动作。每个 tool 有名字、描述、JSON Schema 输入和 handler。
2. **Resource** 是具名的、以 URI 寻址的内容，client 可以读取。
3. **Prompt** 是可复用的模板，host 可以暴露给用户。

host 就是那个 AI 应用。host 内部的 MCP client 与某一个 server 通信。transport 在两者之间传递 JSON-RPC 消息。

### 无状态请求取代握手

MCP 2026-07-28 移除了 `initialize` 和 `notifications/initialized`。它也移除了协议级 session。每个请求都在 `params._meta` 里携带解释它所需的上下文：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

协议版本与 client 能力是必填的。client 身份是建议填写的。缺失 `_meta`、缺失必填字段，或必填字段类型错误，都算格式错误，返回 Invalid Params（`-32602`）。版本字符串格式正确但 server 不支持，则返回 `UnsupportedProtocolVersionError`（`-32022`）。server 无需恢复先前的协商记录，也能处理合法请求。

无状态并不意味着应用永远不能维护状态。它意味着状态不会藏在 MCP 连接或 `Mcp-Session-Id` 后面。如果某个工作流需要连续性，server 铸出一个不透明句柄，client 在后续调用中把它当作普通 tool 参数传回。授权仍然必须在每个请求上检查。

### Discovery 与版本选择

每一个现代 server 都实现 `server/discover`。结果会通告支持的版本、能力和 server 身份：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "supportedVersions": ["2026-07-28"],
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "ttlMs": 3600000,
    "cacheScope": "public",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "demo-server",
        "version": "1.0.0"
      }
    }
  }
}
```

client 可以直接调用其他方法并自行处理版本错误，但 discovery 让能力展示和版本选择变得显式。遇到不支持的版本会返回 `UnsupportedProtocolVersionError`，错误码 `-32022`。它的 data 里包含 `supported`（server 修订版数组）和 `requested`（被拒绝的修订版）。

在 stdio 上，双时代 client 用 `server/discover` 做探测。discovery 结果或可识别的现代错误（例如 `UnsupportedProtocolVersionError`）都表明这是现代 server。任何无法识别为现代的错误或超时，都允许回退到 2025-11-25 的 `initialize` 流程。旧行为只是兼容代码，不是现代默认。

### 结果是显式的

2026-07-28 的每一个核心结果都带 `resultType`：

- `complete` 表示操作已完成。
- `input_required` 表示 server 需要通过 Multi Round-Trip Requests 模式再走一个来回。核心 server 只能从 `tools/call`、`resources/read` 或 `prompts/get` 返回它。

client 必须把省略 `resultType` 的旧式结果视为 complete。

server 应当在每个结果的 `_meta` 里包含 `io.modelcontextprotocol/serverInfo`。这个身份是自报的，只用于展示、日志和调试，不用于安全决策。

list 和 read 结果还携带 `ttlMs` 和 `cacheScope`。确定性的 `tools/list` 顺序加上新鲜度提示，让 client 可以安全地缓存 discovery，并提升 prompt-cache 的稳定性。`cacheScope: public` 允许共享缓存；`private` 把复用限制在调用上下文内。

### 线格式与 transport

MCP 通过 stdio 或 Streamable HTTP 使用 JSON-RPC 2.0。

- 请求包含 `jsonrpc`、`id`、`method` 和 `params`。
- 响应包含匹配的 `id`，以及 `result` 或 `error`。
- notification 没有 `id`，也不需要响应。

现代 Streamable HTTP 暴露一个接受 POST 的端点。每条 JSON-RPC 消息独占一次 POST。请求 POST 收到的是一个 JSON 对象，或是一条以最终响应结尾的请求级 Server-Sent Events 流。被接受的 notification POST 返回 HTTP 202，无响应体；这个核心修订版在 Streamable HTTP 上没有定义任何 client-to-server notification。

在 2026-07-28 中，不存在独立的 MCP GET 流、DELETE session 端点、`Mcp-Session-Id` 或 `Last-Event-ID` 重放。长期存活的变更通知使用 `subscriptions/listen` POST，其响应作为 SSE 流保持打开。

### 没有 server 主动请求时的客户端输入

较早的修订版允许 server 通过流发送 `sampling/createMessage`、`roots/list` 或 `elicitation/create` 之类的请求。当前协议改用 Multi Round-Trip Requests。一次符合条件的 tool 调用、resource 读取或 prompt 获取会返回 `resultType: input_required`，并至少带上 `inputRequests` 或 `requestState` 之一。client 收集所有被请求的输入，用新的 JSON-RPC ID 和对应的 `inputResponses` 重试原方法，并在提供了 `requestState` 时原样回传。如果原本没有 `inputRequests`，重试时省略 `inputResponses`。

Roots、Sampling 和 Logging 仍然可用，但已被废弃，因此新的实现不应采纳它们。既有的 Roots 或 Sampling 请求要放在 MRTR 的 `inputRequests` 里传递，绝不能作为独立的 server-to-client JSON-RPC 请求。优先使用显式的文件或目录参数、resource URI、server 配置和直接的 model-provider 集成。stdio 诊断写 stderr，生产 telemetry 用 OpenTelemetry。

```figure
mcp-nxm-collapse
```

## Build It

### 第 1 步：注册服务端接口面

尽管请求契约变了，注册依然简单：

```python
server = MCPServer("demo-server")

@server.tool(
    "add",
    "Add two integers.",
    {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"}
        },
        "required": ["a", "b"]
    }
)
def add(a: int, b: int) -> dict:
    return {"sum": a + b}
```

`code/main.py` 里随课附带的实现还注册了一个 resource 和一个 prompt。它刻意只用标准库，这样你能看清每一个 envelope，而不是把协议交给某个 SDK。

### 第 2 步：为每个请求附加 metadata

```python
def request(method, params=None):
    body_params = dict(params or {})
    body_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {
            "name": "demo-client",
            "version": "1.0.0"
        }
    }
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": body_params
    }
```

不要把这份 metadata 只缓存在某个连接对象里。server 会在每个请求上校验它。

### 第 3 步：可选地先 discover 再 list

调用 `server/discover`，选一个受支持的版本，然后调用 `tools/list`。如果你已经知道版本并能处理 `-32022`，直接调 `tools/list` 也是合法的。

demo 按名称顺序返回 tool 列表，并附带 `ttlMs`、`cacheScope`、`resultType` 和 server 身份。tool 调用返回 complete 且不可缓存的结果，因为它的输出可能取决于当前状态。

### 第 4 步：把同一请求映射到 HTTP

远程的 `tools/call` POST 会带上与 JSON-RPC body 对应的 header：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: add
```

`MCP-Protocol-Version` header 必须与 `_meta` 里的版本一致。`Mcp-Method` 在每个 JSON-RPC 请求上都是必需的，且必须与 `method` 一致。`Mcp-Name` 只对 `tools/call`、`resources/read` 和 `prompts/get` 必需，其值必须与 tool 名、resource URI 或 prompt 名一致。缺失必需的 header 或出现不一致，会返回 HTTP 400 和 `HeaderMismatch` 错误码 `-32020`。

### 第 5 步：在 protocol state 之外强制安全

- 对每个 HTTP 请求校验授权和受众（audience）。
- 把本地 server 绑定到 localhost，并在 Streamable HTTP 上校验 `Origin`。
- 用 `destructiveHint: true` 标记有副作用的 tool，并要求 host 审批。
- 显式传入目录和文件范围，而不是依赖已废弃的 Roots。
- 把 resource 和 tool 输出一律当作不可信数据。
- 在 stdio 下把 stdout 留给 JSON-RPC；诊断信息写入 stderr。

## Use It

在课程目录里运行：

```bash
python3 code/main.py
cd code
python3 -m unittest discover tests -v
```

第一行应当报告发现 `demo-server`，协议版本为 `2026-07-28`。然后去看 `MCPClient.request`：它为每次调用重建 `_meta`。把某个请求里的 metadata 去掉，观察 server 如何拒绝它。

## Ship It

`outputs/skill-mcp-server-designer.md` 把一个业务领域转化为无状态 MCP 设计。它的验收门槛要求有 discovery 结果、逐请求的 metadata 策略、确定性的 cache-aware 列表、显式状态句柄、transport header、授权和审批规则。

## 继续深入 MCP

这一课给你协议模型。Phase 13 把四个生产边界拆成独立的构建与验证课程：

1. [MCP Tool Contracts and Content](../../../13-tools-and-protocols/28-mcp-tool-contracts-and-content/docs/en.md) 覆盖封闭的输入 schema、结构化 content、路由 metadata、不透明分页、completion 授权，以及协议错误与 tool 领域错误的区别。
2. [MCP Reliability, Cancellation, and Flow Control](../../../13-tools-and-protocols/29-mcp-reliability-cancellation-and-flow-control/docs/en.md) 覆盖请求取消、持久任务取消、deadline、幂等、backpressure、代理缓冲和重连行为。
3. [MCP Registry Supply Chain, Admission, Drift, and Rollback](../../../13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift/docs/en.md) 覆盖 namespace 证明、构建产物溯源、不可变 pin、线上漂移、Registry 状态、准入证据和回滚。
4. [MCP Conformance Engineering](../../../13-tools-and-protocols/31-mcp-conformance-versioning-and-operations/docs/en.md) 覆盖黄金与负向线报文、严格的版本时代、SDK 差分、代理证据、脱敏、健康门禁和发布回滚。

当 server 要跨越团队或信任边界时，按顺序阅读它们。四课合起来，把你从“这个方法能跑通”带到“这份契约在部署全程都保持安全、可诊断”。

## Exercises

1. 添加一个 `subtract` tool，确认 `tools/list` 仍然按字母顺序排列。
2. 去掉 protocol-version 键，验证 Invalid Params（`-32602`）。然后发送格式正确但不受支持的版本 `2025-11-25`，验证 `-32022`，确认 `requested` 回显了该修订版，并从 `supported` 中选择。
3. 给 create 操作加一个由 server 铸出的 `draftId`，然后要求 update 必须以它作为参数。解释为什么这属于应用状态，而不是协议 session。
4. 从一个需要用户确认的 tool 返回 `input_required`。用新的 ID、一条 `inputResponses` 和原样的 `requestState` 重试原调用，而不是发明一个 server-to-client JSON-RPC 请求。
5. 设计一个双时代 stdio client 的草图。把结果或可识别的现代错误视为现代，只对无法识别的错误或超时允许回退到 `initialize`。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| MCP | "LLM 的 tool 协议" | 用于 server 发现、tool、resource、prompt 和扩展的 JSON-RPC 协议 |
| Host | "那个 AI 应用" | 拥有模型和 UI，并挂载一个或多个 MCP client |
| Client | "连接器" | 代表 host 与某一个 server 说 MCP |
| Stateless MCP | "没有 session" | 每个请求携带版本和能力；没有任何协议状态以连接为 key |
| `server/discover` | "能力探测" | 必需的服务端方法，通告版本、能力和身份 |
| `resultType` | "结果状态" | 把结果标记为 `complete` 或 `input_required` |
| State handle | "工作流 id" | 由 server 铸出的应用标识符，作为普通参数传递 |
| Streamable HTTP | "远程 transport" | 一个 POST 端点，返回 JSON 或请求级 SSE 响应 |
| MRTR | "先问再重试" | 输入请求嵌在结果里，随后重试原操作 |

## Further Reading

- [MCP 2026-07-28 key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MCP server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP deprecated features](https://modelcontextprotocol.io/specification/2026-07-28/deprecated)
