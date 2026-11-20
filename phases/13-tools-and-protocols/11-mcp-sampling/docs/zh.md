# MCP 模型输入：Sampling 迁移与无状态 MRTR

> MCP 2026-07-28 为新设计弃用 Sampling，并移除了 server 到 client 的请求通道。如果既有工作流仍然需要客户端的模型，server 就返回一个 `input_required` 结果，由 client 带上模型输出重试最初的请求。推理循环因此在协议层变成显式的、有界的、无状态的。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课（MCP server）、第 13 阶段，第 10 课（resources 与 prompts）
**Time:** ~75 分钟

## Learning Objectives

- 解释 Sampling 为何在 MCP 2026-07-28 中被弃用，并为新 server 选择直接集成模型的默认做法。
- 实现一条兼容工作流，把 `sampling/createMessage` 通过 Multi Round-Trip Requests（MRTR）传递。
- 在每个请求的 `_meta` 对象中放入协议版本和客户端能力。
- 返回 `resultType: "input_required"`，并用新的 JSON-RPC id 重试原始方法。
- 为 `requestState` 提供完整性保护，并把它绑定到 principal、方法、参数和过期时间。
- 用能力检查、审批、响应校验和轮数上限来约束模型辅助的循环。

## 协议之前要先做的决策

像 `summarize_repo` 这样的工具需要两类工作：

1. 确定性工作：列出文件、读取被允许的文件、校验路径、拼装内容。
2. 模型工作：挑选代表性文件并综合成摘要。

现在你有两种都成立的架构。

### 新 server：直接与模型提供方集成

这是当前的默认做法。server 自己负责模型选择、凭据、预算、重试和可观测性。它向 MCP client 返回一个普通的 `tools/call` 结果。

当 server 本身已是托管服务，或者可预测的模型行为比使用宿主的模型更重要时，选择这条路径。

### 既有 Sampling 工作流：迁移到 MRTR

Sampling 在弃用窗口期内仍然存在。面向 2026-07-28 的 server 不能把实时的 `sampling/createMessage` 请求发回 client，而是把该请求内嵌到一个 `InputRequiredResult` 中。

只有当使用客户端的模型和凭据是真实的产品需求时，才选择这条兼容路径。请记录一份移除计划，因为新实现不应再采用已弃用的 Sampling。

## 无状态契约

2026 年 7 月的协议没有 `initialize` 交换，没有 `notifications/initialized`，也没有 `Mcp-Session-Id`。每个请求都携带过去存放在握手阶段的信息：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "summarize_repo",
    "arguments": {"audience": "developer"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {"sampling": {}},
      "io.modelcontextprotocol/clientInfo": {
        "name": "lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

server 在每个请求上都校验版本。版本缺失或不是字符串属于无效参数，返回 `-32602`。字符串不受支持时返回 `-32022`，`data` 必须精确为 `{"supported":["2026-07-28"],"requested":"<client version>"}`。缺少 Sampling 能力时返回 `-32021`，并把 `data.requiredCapabilities` 置为 `{"sampling":{}}`。

没有 JSON-RPC `id` 的信封是 notification。接收方可以处理它，但既不发成功响应，也不发错误响应。对于被接受的 notification，Streamable HTTP 适配器返回不带 body 的 `202 Accepted`。

server 还要实现 `server/discover`，带上精确的 `supportedVersions` 键、capabilities、`ttlMs` 和 `cacheScope`，这样 client 就能在调用工具之前获知并缓存 server 的契约。由于 discovery 宣告了 `tools`，server 还必须实现强制的 `tools/list`。其确定性的 `summarize_repo` 描述符包含一个合法的对象 `inputSchema`、`resultType: "complete"`、server 身份元数据以及公开缓存提示。

每个成功的现代结果都有一个判别字段：

- `resultType: "complete"` 表示操作已完成。
- `resultType: "input_required"` 表示 client 必须满足内嵌请求并重试。
- 扩展可以定义更多结果类型。Tasks 扩展会在第 13 课引入 `"task"`。

## 一次 MRTR 往返

server 在处理请求的过程中不能回调 client，而是返回这样的结果：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "pick_files": {
        "method": "sampling/createMessage",
        "params": {
          "messages": [
            {
              "role": "user",
              "content": {
                "type": "text",
                "text": "Choose three representative files and return a JSON array."
              }
            }
          ],
          "systemPrompt": "Return only the requested value.",
          "modelPreferences": {
            "costPriority": 0.8,
            "intelligencePriority": 0.2
          },
          "maxTokens": 400
        }
      }
    },
    "requestState": "opaque-integrity-protected-value"
  }
}
```

client 确认自己支持 Sampling，套用自己的审批与模型策略，拿到模型响应。随后它用一个不同的 JSON-RPC id 发送新请求：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "summarize_repo",
    "arguments": {"audience": "developer"},
    "inputResponses": {
      "pick_files": {
        "role": "assistant",
        "content": {
          "type": "text",
          "text": "[\"README.md\", \"server.py\", \"docs/intro.md\"]"
        },
        "model": "host-model",
        "stopReason": "endTurn"
      }
    },
    "requestState": "opaque-integrity-protected-value",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {"sampling": {}}
    }
  }
}
```

这次重试不是某个协议会话的延续。它是一个新请求：重复最初的方法和参数，只附上当前轮的 `inputResponses`，并逐字节回显 `requestState`。

MRTR 只允许用于 `tools/call`、`prompts/get` 和 `resources/read`。server 不得从无关的方法返回 `input_required`。

## 多轮状态

本课需要两次模型调用：

1. `pick_files` 返回一个 JSON 数组。
2. `summary` 返回最终的成文摘要。

每次重试只携带该轮的响应。因此 server 要把阶段和已校验的中间数据放进下一个 `requestState`。

要把这个值视为攻击者可控。只对阶段名字签名并不够。把 state 绑定到：

- 已认证的 principal，而不是自报的 `clientInfo`；
- 发起请求的方法；
- 原始参数的摘要；
- 一个较短的过期时间；
- 当前阶段和已校验的中间值。

当不需要机密性时使用 HMAC。当 client 不能读取 state 时使用认证加密。签名错误、值过期、principal 改变或参数改变，都返回 `-32602` 拒绝。

client 不得解析或修改 `requestState`。它唯一的职责是在重试时原样回显该字符串。

## 模型偏好只是提示

`costPriority`、`speedPriority` 和 `intelligencePriority` 是彼此独立的偏好。它们不是概率分布，也不要求和为一。client 可以忽略它们，因为模型策略由 client 掌握。

如果你维护着旧版 Sampling 流程，就把 `includeContext` 保持为 `"none"`。其他上下文模式会增加泄漏风险，而且它们本身也已弃用。在请求中传递最小的显式上下文。

## 安全不变量

对于内嵌的 Sampling 请求，client 是信任边界。

- 当策略要求审批时，向用户展示 server 要求模型做什么。
- 为 MRTR 轮数设置上限。否则恶意 server 可以制造一个模型花费循环。
- 在把每个 sampling 响应用作文件名、URL 或工具输入之前，先校验它。
- 限制每轮的字节数和 token 数。
- 拒绝当前客户端能力中未声明的 input request。
- 让模型输出远离授权决策。
- 记录发起方法和 input-request 键，但不要记录敏感的 prompt 内容。

`clientInfo` 和 `serverInfo` 只是展示与诊断用的元数据。绝不能把其中任何一个当作已认证的身份。

```figure
t3-sampling-flip
```

## Build It

`code/main.py` 在不引入任何第三方包的情况下实现了完整的两轮流程：

- `server/discover` 返回 `supportedVersions`，宣告工具支持，并返回缓存提示。
- `tools/list` 返回确定性的、可缓存的 `summarize_repo` 描述符，带一个对象型 input schema。
- `tools/call` 校验逐请求的元数据。
- 第一个结果内嵌用于挑选文件的 `sampling/createMessage`。
- 第一次重试校验模型结果，并内嵌第二个请求。
- 受 HMAC 保护的 `requestState` 在相互独立的请求之间携带阶段信息。
- 最终结果使用 `resultType: "complete"`。

伪宿主模型让示例保持确定性。接入真实宿主时只需要替换 `fake_host_model`。server 端的状态机应保持确定且可测试。

## Use It

从仓库根目录：

```bash
cd phases/13-tools-and-protocols/11-mcp-sampling/code
python3 main.py
python3 -m unittest discover tests -v
```

预期检查点：

- discovery 返回一个完整结果，带 `ttlMs` 和 `cacheScope`。
- 工具发现返回同一个排序稳定的描述符，带 `resultType`、server 身份和缓存提示。
- 缺失能力与不支持的版本分别使用精确的 `-32021` 和 `-32022` 错误数据。
- 没有 id 的 notification 不产生任何 JSON-RPC 响应。
- 请求 id 为 `[1, 2, 3]`，证明每个 MRTR 轮次都是独立的。
- 前两个结果是 `input_required`。
- 最终结果是 `complete`，包含所选文件和摘要。
- 在重试时改动原始参数会让 request-state 校验失败。

## Ship It

`outputs/skill-sampling-loop-designer.md` 现在是一份迁移规划器。它先判断是否应当移除 Sampling、改用直接模型集成。如果必须兼容，它会产出 MRTR 轮次、状态绑定、能力门禁、预算、校验和移除计划。

## Exercises

1. 把文件选择响应改成非法 JSON。确认 server 返回 `-32602`，而不是信任模型输出。
2. 在首次调用和重试之间改变 `audience`。解释为什么密封的 state 会阻止跨请求复用。
3. 增加第三轮，请宿主对摘要做评审。把此前的摘要放进签名 state，并把整个流程限制在最多三轮。
4. 移除 Sampling，用 server 自有的模型适配器替换伪宿主回调。列出哪些审批、计费和可观测性职责转移到了 server。
5. 增加一个过期测试，使用一个刚过期一秒的 state 值。

## Key Terms

| 术语 | 在 2026-07-28 中的含义 |
|------|------------------------|
| Sampling | 已弃用的特性，用于向客户端的模型请求一次 completion |
| MRTR | 在请求处理过程中需要客户端输入时使用的无状态重试模式 |
| `InputRequiredResult` | 带 `resultType: "input_required"` 的结果 |
| `inputRequests` | 由 server 分配的映射，存放内嵌的 elicitation、sampling 或 roots 请求 |
| `inputResponses` | 当前轮客户端结果的映射，键与 `inputRequests` 对应 |
| `requestState` | 不透明的 server 状态，由 client 原样回显并由 server 校验 |
| `resultType` | 现代 MCP 结果必需的判别字段 |
| Direct model integration | 需要模型推理的新 server 所推荐的替代方案 |
| Capability gate | 防止发送客户端未宣告的内嵌请求的规则 |
| Loop budget | 该操作允许的最大轮数、token 数、字节数、时间和花费 |

## 旧版兼容

固定在 2025-11-25 的 client 仍可通过活动连接使用旧式的由 server 发起的 `sampling/createMessage` 流程。只把该行为保留在版本专属的适配器中。不要让有会话的路径成为 2026-07-28 server 的架构。

官方 SDK 可以为旧对端翻译现代的 `input_required` 处理器。这个 shim 是兼容边界，而不是允许你新增依赖会话的逻辑。

## Further Reading

- [MCP 2026-07-28 多次往返请求（MRTR）](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP 2026-07-28 变更日志](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MCP Sampling 弃用说明](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
- [MCP 2026-07-28 server 发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
