# MCP 基础：无状态请求与 JSON-RPC

> 现代 MCP 没有握手，也没有协议会话。每个请求都必须自带足够的元数据，以便被独立地理解、授权、路由和重试。

**Type:** Learn
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 01 至 05 课
**Time:** ~55 分钟

## Learning Objectives

- 区分 MCP 的服务端原语与它的客户端侧特性。
- 为 MCP `2026-07-28` 构建合法的 JSON-RPC 2.0 请求与响应。
- 在每次请求上附带协议版本、客户端 capabilities 与客户端身份。
- 使用 `server/discover`，并在没有握手的情况下处理 `UnsupportedProtocolVersionError`。
- 追踪一个独立请求，从校验一直到完整结果。

## 问题场景

一个 MCP server 可能在同一进程或 HTTP worker 上，连续收到来自不同客户端、具有不同 capabilities 的两个请求。如果 server 记住上一个请求声明过的内容，它就可能施加错误的权限，或返回错误的线上格式（wire shape）。

MCP `2026-07-28` 消除了这种歧义。协议核心是无状态的。server 必须依据当前请求本身来决定如何处理当前请求，而不是依据连接历史。

这改变了心智模型。旧的顺序是先连接、再握手、最后执行操作。现代的顺序更简单：

1. 客户端发送一个自描述的请求。
2. server 校验该请求的版本与 capabilities。
3. server 处理该方法。
4. server 返回带类型的结果，或一个 JSON-RPC 错误。

下一个请求会从零开始重复同样的过程。

## 核心概念

### 服务器原语

MCP server 暴露三类主要原语：

1. **Tools** 是模型可控的动作，通过 `tools/list` 发现，通过 `tools/call` 调用。
2. **Resources** 是 URI 寻址的数据，通过 `resources/list` 发现，通过 `resources/read` 获取。
3. **Prompts** 是可复用模板，通过 `prompts/list` 发现，通过 `prompts/get` 渲染。

Roots、sampling 与 logging 出于兼容性仍保留在 `2026-07-28` schema 中，但已弃用。新实现应使用显式的 tool 或 resource 输入来替代 roots，使用模型提供方的直接 API 来处理 sampling，使用 stderr 或 OpenTelemetry 来处理 logging。Elicitation 仍可通过 Multi Round-Trip Requests 使用：server 返回一个输入请求，客户端重试原始操作。现代 server 从不主动发起独立的 JSON-RPC 请求。

### JSON-RPC 信封

MCP 使用 JSON-RPC 2.0：

- 请求：`{jsonrpc, id, method, params}`
- 响应：`{jsonrpc, id, result}` 或 `{jsonrpc, id, error}`
- 通知：`{jsonrpc, method, params}`，不带 `id`

请求的 `id` 只用于关联一个响应。它不会创建协议会话。

### 必需的请求元数据

每个现代请求都会在 `params` 内携带一个 `_meta` 对象：

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/list",
  "params": {
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

协议版本与客户端 capabilities 是必需的。客户端身份是推荐的。它是自报的展示与调试数据，不是安全凭据。

server 不得仅凭先前的请求、stdio 进程、HTTP 连接或传输层头部来推断上述任何值。

### 完整结果与服务器身份

每个成功的现代结果都包含 `resultType`。正常的最终结果使用 `"complete"`。server 还应在结果元数据中标明自身：

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "resultType": "complete",
    "tools": [],
    "ttlMs": 30000,
    "cacheScope": "public",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "notes-server",
        "version": "1.0.0"
      }
    }
  }
}
```

`tools/list`、`resources/list`、`prompts/list`、`resources/templates/list`、`resources/read` 和 `server/discover` 是可缓存结果。它们包含 `ttlMs` 与 `cacheScope`。安全的默认值是 `ttlMs: 0` 和 `cacheScope: "private"`。列表项应具有确定性排序，这样等价响应会产生稳定的缓存键和稳定的模型上下文。

### 无需握手的发现

每个现代 server 都必须实现 `server/discover`。客户端可以在调用其他方法之前先调用它，以获取：

- `supportedVersions`
- server `capabilities`
- 可选的用法 `instructions`
- 结果 `_meta` 中的 server 身份
- 缓存提示

发现机制很有用，但它不是一道关卡。客户端可以直接先发送 `tools/list`，因为该请求本身已经携带了协议版本与 capabilities。

如果请求的版本不受支持，server 返回 JSON-RPC 错误码 `-32022`，并附带：

```json
{
  "requested": "2027-01-01",
  "supported": ["2026-07-28"]
}
```

客户端选择一个双方都支持的现代版本，并用新的 JSON-RPC 请求 id 重试。

### 单个请求的生命周期

按以下顺序追踪一个现代请求：

1. 解析一个 JSON-RPC 信封。
2. 确认 `jsonrpc` 为 `"2.0"`、存在 `id`、`method` 是字符串、`params` 是对象。
3. 要求 `params._meta` 中存在版本字符串与 capability 对象；格式错误或缺失的元数据返回 `-32602`。
4. 在 HTTP 边界上，将版本、方法和适用的 name 头部与请求体比对。即使两个版本值中有一个不受支持，不一致也返回 `-32020`。
5. 在确认相等之后，对于匹配但不受支持的版本，返回 `-32022`。
6. 检查必需的 capabilities，然后按 `method` 路由并校验方法特有的参数。
7. 在 handler 运行之前，对具体操作进行身份认证与授权。
8. 返回带 server 身份的完整结果。
9. 遗忘请求作用域的协议元数据。

这个顺序能防止两个组件对不同的调用做出不同的解读。网关不得在放行 `Mcp-Name: notes.read` 的同时，让源站执行 `params.name: notes.delete`。它还能让格式错误的输入、头部混淆、版本协商、capability 失败、授权失败和 handler 失败保持为各自独立的证据。

关闭 stdin 或一个 HTTP 响应会结束传输层活动。它不会终止协议会话，因为现代 MCP 没有协议会话。

### 显式的旧版兼容

截至 `2025-11-25` 的版本使用 `initialize`、`notifications/initialized`、连接作用域的 capabilities，以及在更早的 Streamable HTTP 上可选的协议会话。当一个双时代客户端与旧 server 通信时，这些行为仍然相关。

把两个时代清楚分开。现代请求由必需的逐请求元数据来识别。旧版连接只能通过文档化的回退路径选择。不要把 `initialize` 作为 `2026-07-28` server 的默认发送内容。

因此，"无状态" 有一个与时代相关的含义。在 `2026-07-28` 中，它是一条协议不变量：每个普通请求都可被独立解读，且不存在 MCP 会话。在截至 `2025-11-25` 的版本中，初始化与协商出的 capabilities 属于某个连接，所以兼容适配器可以保留那份旧版连接状态。双时代实现不是一台宽松的状态机。它是在隔离的旧版适配器旁边放置一个无状态的现代核心，并且在任一解析器运行之前就做出明确的选择。

这两种含义都不禁止持久化的应用状态。一个 workflow、task 或 draft 可以存放在共享存储中，由不透明句柄引用。客户端将该句柄作为普通输入发送，每个副本都会对其使用进行认证与授权。协议上下文不得泄漏到该存储中，作为已被移除的会话的替代品。

```figure
mcp-tool-call
```

## Use It

`code/main.py` 不使用任何框架，完成现代 MCP 消息的构造、校验、追踪与分发。运行：

```bash
python3 code/main.py
python3 -m unittest discover code/tests -v
```

注意输出中的三条不变量：

- 每个请求都会重复其 `_meta` 字段。
- 每个成功结果都是 `resultType: "complete"`，并包含 server 身份。
- 列表结果具有确定性排序，并带有显式的缓存提示。

## Ship It

本课交付 `outputs/skill-mcp-handshake-tracer.md`。该文件名保持了历史稳定性，但这个工件如今是一个无状态请求追踪器。它逐条独立审计每个消息，并且只在旧版握手流量确实存在时才将其标记出来。

## Exercises

1. 把某个请求的协议版本改成 `2027-01-01`。确认错误码是 `-32022`，且 data 中通告了受支持的版本。
2. 从第二个请求中移除 `io.modelcontextprotocol/clientCapabilities`。确认 server 不会复用第一个请求的 capabilities。
3. 反转内存中的 tool 注册表。确认 `tools/list` 仍然返回相同的确定性顺序。
4. 把 `cacheScope` 从 `public` 改为 `private`。解释在两种情况下，哪些授权上下文可以复用该响应。
5. 增加一个省略 `clientInfo` 的可选测试。请求应当仍然合法，因为客户端身份是推荐的，不是必需的。

## Key Terms

| 术语 | 含义 |
|------|---------|
| 无状态协议 | 每个请求都提供解读它自身所需的元数据 |
| 请求元数据 | `params._meta` 中的版本、客户端 capabilities 与推荐的客户端身份 |
| `server/discover` | 强制实现的 server 方法，用于提供版本、capabilities、instructions 与身份 |
| `resultType` | 每个成功的现代结果上的判别字段 |
| 可缓存结果 | 包含必需的 `ttlMs` 与 `cacheScope` 提示的结果 |
| 协议时代 | 现代的逐请求元数据，或旧版的连接作用域初始化 |
| 传输生命周期 | 进程、连接或响应流的生命周期，而不是协议会话状态 |
| `-32022` | 不受支持的协议版本错误，携带请求版本与支持版本 |

## Further Reading

- [MCP 架构](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [MCP 基础协议](https://modelcontextprotocol.io/specification/2026-07-28/basic)
- [MCP 服务器发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP 2026-07-28 变更日志](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
