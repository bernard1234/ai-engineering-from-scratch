# MCP Tasks 扩展：无状态核心上的持久工作

> 无状态 MCP 并不意味着每个操作都必须在一次请求内完成。官方的 Tasks 扩展为长时间运行的工作提供了一个显式的持久句柄。server 可以从 `tools/call` 返回该句柄，任何实例都能回答 `tasks/get`，而客户端输入通过 `tasks/update` 到达，无需重振协议会话。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 09 课（transports）、第 13 阶段，第 11 课（无状态 MRTR）、第 13 阶段，第 12 课（elicitation）
**Time:** ~90 分钟

## Learning Objectives

- 区分无状态的协议传输与持久的应用任务状态。
- 在逐请求能力与 `server/discover` 中协商 `io.modelcontextprotocol/tasks` 扩展。
- 只有在持久化创建完成之后，才返回由 server 指定的 `CreateTaskResult`（`resultType: "task"`）。
- 用 `tasks/get` 轮询、用 `tasks/update` 满足任务输入、用 `tasks/cancel` 请求协作式取消。
- 移除旧有的 `tasks/status`、`tasks/result` 和 `tasks/list` 假设。
- 通过 POST 响应上的 SSE 流，用 `subscriptions/listen` 订阅可选的任务 notification。
- 正确建模任务过期、重启恢复、输入键去重和执行错误。

## 为什么 Tasks 是一个扩展

Tasks 最早在 2025-11-25 作为实验性的核心特性出现。2026 年 7 月的重新设计把它们移入官方的 `io.modelcontextprotocol/tasks` 扩展，这样 client 和 server 可以选择加入这套额外的生命周期，而不必为所有人扩展核心协议。

尽管该扩展已成为 Tasks 当前的官方归属，其规范仍是 draft 形态。请固定你的 SDK 支持的扩展版本，运行一致性场景，并把 wire 适配器与你的 worker 和存储领域隔离开。

当操作具备以下一项或多项属性时，使用任务：

- 它可能超出普通的请求超时。
- worker 队列或外部作业系统已经掌管执行。
- client 需要在自己的重启之后恢复。
- 操作在执行期间因用户或模型输入而暂停。
- 取消与持久的结果检索是产品需求。

不要为廉价的确定性查询创建任务。句柄、持久化、轮询、过期和取消都是实实在在的复杂度。

## 无状态核心，有状态应用

MCP 2026-07-28 移除了 `initialize`、`notifications/initialized`、协议会话和 `Mcp-Session-Id`。这并不禁止有状态的产品。

任务 id 是显式的应用状态：

- server 在返回它之前先持久化它。
- client 可以存储它，并在重启后再次轮询。
- 该 id 可以路由到由同一持久存储支撑的任何副本。
- 每个任务方法都会检查授权。
- 过期与删除由任务字段定义，而不是传输生命周期。

这在运维上不同于依附于连接的隐藏状态。

要把四种生命周期分开：

| 状态 | 生命周期 | 归属位置 |
|---|---|---|
| 协议元数据 | 单个请求 | `params._meta`，每次调用都重新校验 |
| 传输工作 | 单个 stdio 请求或 HTTP 响应 | 带有限期限的在途协调器 |
| MRTR 延续 | 一次重试序列 | 受完整性保护的 `requestState`，必要时加上重放控制 |
| 持久任务 | 跨越请求、副本、重启和重连 | 由已授权的 `taskId` 作为键的共享应用存储 |

把任务记录移入进程内存并不会让 MCP 变成有状态，它只会让应用变得不可靠。协议保持无状态，但此后路由到另一个副本的 `tasks/get` 无法取回该记录。在返回句柄之前先持久化，然后让每个任务方法都能在租户和 principal 检查下解析到同一条共享记录。

## 能力协商

client 在每个符合条件请求上宣告支持：

```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {
      "extensions": {
        "io.modelcontextprotocol/tasks": {}
      }
    },
    "io.modelcontextprotocol/clientInfo": {
      "name": "lesson-client",
      "version": "1.0.0"
    }
  }
}
```

server 从 `server/discover` 返回精确的 `supportedVersions`、capabilities、`ttlMs` 和 `cacheScope`，并在 capabilities 下带同一个扩展。由于宣告了 tools，它还实现强制的 `tools/list`。该结果返回确定性的 `generate_report` 描述符、合法的对象 `inputSchema`、`resultType: "complete"`、server 身份元数据和公开缓存提示。

如果 client 未声明该扩展却调用任务方法，则返回 `-32021`（Missing Required Client Capability），并把 `data.requiredCapabilities` 置为 `{"extensions":{"io.modelcontextprotocol/tasks":{}}}`。协议字符串不受支持时返回 `-32022`，并给出精确的 `supported` 和 `requested` 数据；版本缺失或不是字符串时返回 `-32602`。

没有 JSON-RPC `id` 的信封是 notification。接收方可以处理它，但不发出 JSON-RPC 结果或错误。对于被接受的 notification，Streamable HTTP 适配器返回不带 body 的 `202 Accepted`。

目前只有 `tools/call` 支持任务增强的执行。请设计你的内部抽象，使将来出现新的请求类型时不必重写存储。

## Server 指定的任务创建

旧的客户端标志 `params._meta.task.required` 已被移除。client 先声明扩展支持，再由 server 决定某次 `tools/call` 是否成为任务。

请求：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "generate_report",
    "arguments": {"size": "large"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

响应：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "task",
    "taskId": "tsk_786512e29e0d",
    "status": "working",
    "statusMessage": "Preparing report outline.",
    "createdAt": "2026-08-21T10:30:00Z",
    "lastUpdatedAt": "2026-08-21T10:30:00Z",
    "ttlMs": 900000,
    "pollIntervalMs": 1000
  }
}
```

在针对该 id 的 `tasks/get` 能够解析之前，server 不得返回这个句柄。在最终一致的存储中，要等待读可见性再作答。否则 client 可能拿到一个看起来合法的 id，却立刻得到 "not found"。

任务响应是"未经请求的"，意思是 client 并未主动请求任务模式。但它并非未经协商：当前请求仍然必须宣告该扩展。

## 任务的结构

每个任务携带：

- `taskId`：server 生成的稳定标识符；
- `status`：`working`、`input_required`、`completed`、`cancelled` 或 `failed`；
- `createdAt` 与 `lastUpdatedAt`：ISO 8601 时间戳；
- `ttlMs`：从创建起算的过期时长，或 `null` 表示没有宣告限制；
- 可选的 `pollIntervalMs`：server 当前建议的最小轮询节奏；
- 可选的 `statusMessage`：面向用户或面向模型的上下文。

特定于状态的字段只在相关时出现：

- `input_required` 包含 `inputRequests`。
- `completed` 包含原始请求的 `result` 形状。
- `failed` 包含一个 JSON-RPC `error` 对象。

client 应当遵循 `pollIntervalMs`。server 可以对更激进的轮询限速，并可能在任务生命周期内改变该间隔。

## 用 `tasks/get` 轮询

client 请求当前快照：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/get
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tasks/get",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

`tasks/get` 本身已完成，所以它的结果始终带 `resultType: "complete"`。内嵌的任务仍可能处于 `status: "working"` 或 `status: "input_required"`。

这一区分可以防止一个常见的解析器 bug：

```text
result.resultType = complete    means the tasks/get RPC finished
result.status = working        means the represented job is still running
```

没有 `tasks/result` 调用。当任务完成时，下一次 `tasks/get` 的响应会把原始的 `CallToolResult` 内联到 `result` 之下：

```json
{
  "resultType": "complete",
  "taskId": "tsk_786512e29e0d",
  "status": "completed",
  "createdAt": "2026-08-21T10:30:00Z",
  "lastUpdatedAt": "2026-08-21T10:34:12Z",
  "ttlMs": 900000,
  "result": {
    "resultType": "complete",
    "content": [
      {"type": "text", "text": "Generated large report with approved outline."}
    ],
    "structuredContent": {"size": "large", "approved": true},
    "isError": false,
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "tasks-demo",
        "version": "1.0.0"
      }
    }
  },
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "tasks-demo",
      "version": "1.0.0"
    }
  }
}
```

外层的 `resultType` 说明 `tasks/get` 这个 RPC 完成了。内嵌的 `result.resultType` 说明最初的工具调用完成了。这个内嵌判别字段是必需的。内嵌的 `CallToolResult` 还 SHOULD 携带自己的 `io.modelcontextprotocol/serverInfo`；本课选择包含它，而不是存储未分型的载荷。

没有 `tasks/list`。无会话的 server 无法安全地推断哪些任务属于某个连接范围的列表。需要历史记录的应用应当暴露一个已授权的领域工具，带显式过滤条件和所有权规则。

## 任务执行期间的输入

任务输入与核心 MRTR 看起来相似，但使用的延续机制不同。

### 任务创建之前需要的输入

从原始的 `tools/call` 返回核心的 `resultType: "input_required"`。client 满足它并重试那次原始调用。只有在这些同步的 MRTR 轮次结束之后，才创建任务。

### 任务创建之后需要的输入

把任务置为 `input_required`。`tasks/get` 会暴露尚未满足的 `inputRequests`，client 通过 `tasks/update` 发送响应。client 不重试原始的 `tools/call`。

快照：

```json
{
  "resultType": "complete",
  "taskId": "tsk_786512e29e0d",
  "status": "input_required",
  "createdAt": "2026-08-21T10:30:00Z",
  "lastUpdatedAt": "2026-08-21T10:31:00Z",
  "ttlMs": 900000,
  "inputRequests": {
    "approve_outline": {
      "method": "elicitation/create",
      "params": {
        "mode": "form",
        "message": "Approve the generated report outline?",
        "requestedSchema": {
          "type": "object",
          "properties": {"approved": {"type": "boolean"}},
          "required": ["approved"]
        }
      }
    }
  }
}
```

更新：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/update
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tasks/update",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "inputResponses": {
      "approve_outline": {
        "action": "accept",
        "content": {"approved": true}
      }
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

成功响应是一个空的确认，加上 `resultType: "complete"`。状态变更可能是最终一致的，因此 client 继续轮询或监听。

每个 `inputRequests` 键在整个任务生命周期内必须唯一。重复的 `tasks/get` 快照可能显示同一个尚未满足的键；client 在 UI 上去重，server 忽略针对未知、已被取代或已满足的键的响应。部分更新可能让任务停留在 `input_required`，直到所有必需的键都被回答。

## 取消是协作式的

`tasks/cancel` 表达意图，并返回一个空的 complete 确认。该确认并不保证 worker 已经停止。工作可能先完成、可能忽略取消，也可能稍后才转换状态。

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/cancel
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tasks/cancel",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

对全部三个任务方法，`Mcp-Name` 都镜像 `params.taskId`。它不重复 JSON-RPC 方法名。`code/main.py` 在 `make_http_request` 中集中实现这条规则。

本课的 worker 会立即响应取消，使重复调用幂等。生产环境的 client 仍必须把取消当作协作式的，而不是从确认中推断出最终任务状态。

不要用 `notifications/cancelled` 来取消任务。那个 notification 属于请求取消，而不是持久 Tasks。

这一区分在路由边界上很重要。请求取消针对一个在途的 JSON-RPC 操作或它请求范围内的 HTTP 响应。如果 `tools/call` 已经返回 `resultType: "task"`，该请求就已完成，关闭它的传输既无法命名也无法停止那个持久作业。`tasks/cancel` 是一个新的、需授权的 RPC。它携带 `params.taskId`，在 `Mcp-Name` 中镜像该 id，解析任务所属的后端，记录协作式取消意图，并返回确认而不声称 worker 已停止。

因此 gateway 必须把请求协调器和任务路由放在不同的表中。请求表可以在响应结束时消失。任务路由必须存活到终态和保留期过期。[第 29 课：MCP Reliability, Cancellation, and Flow Control](../../29-mcp-reliability-cancellation-and-flow-control/docs/en.md) 为两条路径构建了竞态、超时、幂等、背压和重试规则。

## 可选的 Notifications

轮询是基线。希望获得推送更新的 client 会带上任务 id 发送 `subscriptions/listen`。对于 Streamable HTTP，这是一个 POST，其响应是请求范围的 SSE 流。没有独立的 GET 事件流，也没有需要保活的协议会话。

server 用 `notifications/subscriptions/acknowledged` 确认被接受的 id，之后可以通过 `notifications/tasks` 发送完整快照。这个确认和每一条任务 notification 都在 `_meta` 中携带 `io.modelcontextprotocol/subscriptionId`，等于 `subscriptions/listen` 的请求 id。每条任务 notification 在其他方面等同于 `tasks/get` 在那一刻会返回的内容。

client 仍必须声明 Tasks 扩展。它们应当依靠持久的任务 id 重连并恢复，而不是依赖事件重放或 `Last-Event-ID`。

## 失败语义

正确使用两层错误。

### 协议错误

无效的方法参数或未知的任务 id 返回 JSON-RPC 错误，通常是 `-32602`。缺少扩展支持返回 `-32021`，并带上所需的能力对象。

### 任务执行结果

- 带 `isError: true` 的正常工具结果仍然是 `completed` 的任务，因为工具调用产出了它定义的结果。
- 延迟执行期间的 JSON-RPC 错误会让任务变为 `failed`，并把该 JSON-RPC 错误存放在 `error` 下。
- 用户拒绝可以产生 `cancelled`、一个已完成的拒绝结果，或另一个领域特有的安全结果。请写明所选的方案。

## 持久性、过期与所有权

至少持久化这些内容：任务 id、状态、时间戳、ttl、轮询间隔、原始操作的所有权、结果或错误、未满足的输入请求，以及所有已发出的输入键。

存储键必须包含或能解析出权威的租户和 principal。知道一个任务 id 不得因此获得访问权。在每次 `tasks/get`、`tasks/update`、`tasks/cancel` 和订阅时都检查所有权。

`ttlMs` 从创建起算，并且可能变化。当任务已停止产生可观察的更新时，client 可以把它当作兜底。server 可以让任务失败，并在之后删除过期任务。不要把它描述成"在完成后仍保留结果这么多毫秒"的承诺。

使用原子写或事务。本课写入临时文件，再原子地重命名。多副本服务应使用共享的持久存储，以及 worker 租约或等价的并发控制。

```figure
tp-task-lifecycle
```

## Build It

`code/main.py` 实现了一个确定性的任务服务：

- `server/discover` 返回 `supportedVersions`、缓存提示和 Tasks 扩展。
- `tools/list` 返回确定性的、可缓存的 `generate_report` 描述符，带合法的 input schema。
- `tools/call` 在返回 `resultType: "task"` 之前创建并持久化任务。
- 一个新的服务实例重新加载同一个任务，演示重启恢复。
- `tasks/get` 返回完整的任务快照。
- worker 从 `working` 进入 `input_required`。
- `tasks/update` 接受一个 form 响应，并返回空的 complete 确认。
- worker 存储一个内嵌的、带自身 `resultType` 和 server 身份的 `CallToolResult`，然后转入 `completed`。
- 在本实现中 `tasks/cancel` 是幂等的。
- HTTP 构造器在 `tasks/get`、`tasks/update` 和 `tasks/cancel` 中把 `Mcp-Name` 设为 `params.taskId`。
- notification 辅助函数使用 `notifications/subscriptions/acknowledged` 和 `notifications/tasks`，两者都带上 listen 请求 id。
- 没有 id 的 notification 不产生任何 JSON-RPC 响应。

worker 显式推进，而不是在后台线程中休眠。这让每次状态转换都确定，并让协议示例与队列机制保持分离。

## Use It

从仓库根目录：

```bash
cd phases/13-tools-and-protocols/13-mcp-async-tasks/code
python3 main.py
python3 -m unittest discover tests -v
```

预期的结果序列：

```text
id=0 resultType=complete status=ack
id=1 resultType=task status=working
id=2 resultType=complete status=working
id=3 resultType=complete status=input_required
id=4 resultType=complete status=ack
id=5 resultType=complete status=completed
```

同时验证：在现代服务中，`tasks/status`、`tasks/result` 和 `tasks/list` 都会返回 method-not-found。
验证 `tools/list` 是确定性的，且每个当前的 HTTP 任务方法都通过 `Mcp-Name` 镜像它的任务 id。

## Ship It

`outputs/skill-task-store-designer.md` 现在产出一份感知扩展的设计：能力协商、返回前持久化、当前方法、输入更新流程、所有权、过期、取消、订阅，以及从已移除的实验性方法迁移。

## Exercises

1. 增加第二个未满足的输入键。发送一次部分的 `tasks/update`，并证明任务在两个键都被回答前保持 `input_required`。
2. 给存储增加租户所有权，并拒绝由错误 principal 出示的合法任务 id。
3. 增加带过期的 worker 租约。证明两个服务实例无法并发完成同一个任务。
4. 为 `subscriptions/listen` 实现一个 POST 响应 SSE 适配器。不要添加 GET、`Last-Event-ID` 或会话头。
5. 增加过期清理。在不泄露跨租户存在性的前提下，区分过期任务与格式错误的任务 id。

## Key Terms

| 术语 | 在当前扩展中的含义 |
|------|----------------------------------|
| Tasks extension | 用于持久异步工作的可选 `io.modelcontextprotocol/tasks` 能力 |
| `CreateTaskResult` | 由 server 指定的 `resultType: "task"` 响应，回应一个符合条件的请求 |
| `tasks/get` | 轮询完整的当前任务快照，包括终态结果或待处理的输入 |
| `tasks/update` | 提交对任务未满足 `inputRequests` 的响应 |
| `tasks/cancel` | 确认协作式取消意图 |
| `input_required` | 表示客户端输入尚未满足的任务状态 |
| `pollIntervalMs` | server 建议的下一次轮询前的最小延迟 |
| `ttlMs` | 从任务创建起算的过期时长 |
| Durable-before-return | 任务 id 必须在句柄发出前即可解析的规则 |
| `notifications/tasks` | 在已订阅的 SSE 响应上投递的可选完整任务快照 |

## 旧版兼容

2025-11-25 的实验性接口使用由 client 请求的任务增强，以及 `tasks/status`、`tasks/result` 和可选的 `tasks/list`。只把这些名称保留在固定版本的 legacy 适配器内部。现代 client 使用扩展能力，接受由 server 指定的句柄，轮询 `tasks/get`，用 `tasks/update` 提交输入，并从任务快照中读取最终结果。

## Further Reading

- [官方 MCP Tasks 扩展](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)
- [MCP 2026-07-28 多次往返请求（MRTR）](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP 2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
