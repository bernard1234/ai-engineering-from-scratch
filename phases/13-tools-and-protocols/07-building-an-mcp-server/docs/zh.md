# 构建 MCP Server：无状态的 Python 与 TypeScript

> 现代 MCP server 不记得握手。它在每个请求上校验元数据，运行一个 handler，返回一个带类型的结果。

**Type:** Build
**Languages:** Python, TypeScript
**Prerequisites:** 第 13 阶段，第 06 课
**Time:** ~85 分钟

## Learning Objectives

- 为 MCP `2026-07-28` 实现强制性的 `server/discover`。
- 在每个请求上校验协议版本与客户端 capabilities。
- 以确定性的列表顺序暴露 tools、resources 与 prompts。
- 在正确的结果上返回 `resultType`、server 身份与缓存提示。
- 在 Python 与 TypeScript 中，通过按换行分隔的 stdio 提供同一套无状态契约。

## 问题场景

在第一条消息之后存储客户端 capabilities 的 server 易于构建、难以运维。同一进程可能依次服务多个客户端。一个远程请求可能落到不同的 worker 上。过期的 capability 声明可能让行为跨授权边界泄漏。

MCP `2026-07-28` 通过让每个请求自描述，解决了该问题中协议层面的那部分。你的应用仍然可以保存持久化的 note、job 或显式状态句柄。它不能保留的是会改变后续请求解码方式的隐藏协议状态。

本课把 notes server 构建两遍。Python 与 TypeScript 版本在协议核心上只使用各自的标准库。两者暴露相同的方法，并强制执行相同的线上契约。

## 核心概念

### 现代分发循环

```text
read one JSON-RPC line
parse the envelope
if it is a notification, do not respond
validate params._meta for this request
route by method
wrap success with resultType and serverInfo
write one JSON-RPC response line
forget request-scoped metadata
```

三条 stdio 规则仍然重要：

- 只向 stdout 写 JSON-RPC 消息。把诊断信息发送到 stderr。
- 用换行分隔消息，并刷新每个响应。
- stdin 到达 EOF 时立即退出。

进程生命周期是一种传输生命周期。它不是现代 MCP 会话。

### 请求校验

每个请求必须包含：

```json
{
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "notes-client",
        "version": "1.0.0"
      }
    }
  }
}
```

前两个字段是必需的。`clientInfo` 是推荐的。校验存在的身份结构，但不要把它当作认证。

如果版本不受支持，返回错误码 `-32022`，并附带 `requested` 与 `supported`。缺少请求元数据属于 invalid params，错误码 `-32602`。绝不要用先前的调用填补缺失字段。

### 强制发现

现代 server 必须实现 `server/discover`。完整的发现结果包含受支持的现代版本、capabilities、可选的 instructions、缓存提示，以及结果 `_meta` 中的 server 身份：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {"listChanged": false},
    "resources": {"listChanged": false, "subscribe": false},
    "prompts": {"listChanged": false}
  },
  "ttlMs": 3600000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "notes-server",
      "version": "2.0.0"
    }
  }
}
```

发现并不会解锁 server。客户端可以不调用发现就直接调用 `tools/list`，因为 `tools/list` 已经携带同样的请求元数据。

### Tools

`tools/list` 返回确定性的 tool 描述符列表。稳定的排序能改善响应缓存，并让模型上下文保持稳定。该结果还要求 `ttlMs` 与 `cacheScope`。

`tools/call` 返回内容块与 `isError`。当协议信封或方法参数不合法时，使用 JSON-RPC 错误。当一次合法的 tool 调用运行了、但 tool 自身失败时，使用 `isError: true`。

Tool 注解仍然只是提示，不是强制执行：

- `readOnlyHint`
- `destructiveHint`
- `idempotentHint`
- `openWorldHint`

Host 应将它们用于确认与展示。Server 仍然必须强制执行真正的授权。

### Resources

`resources/list` 返回稳定的 URI 描述符。`resources/read` 返回带类型的内容。两者在 `2026-07-28` 中都可缓存，因此都包含 `ttlMs` 与 `cacheScope`。

对于特定用户的 note 数据，使用 `cacheScope: "private"`。共享缓存不得跨授权上下文复用私有响应。

现代的变更投递不使用 `resources/subscribe`。客户端打开 `subscriptions/listen`，并请求 `resourceSubscriptions` 或列表变更类别。第 10 课会构建该流程。

### Prompts

`prompts/list` 可缓存且具有确定性。`prompts/get` 用参数渲染一个具名 prompt。渲染出的 prompt 结果是 complete 的，但它不属于那些需要缓存提示的可缓存列表或读取结果。

### 每个成功结果都是带类型的

示例对所有成功都使用同一个包装器：

```python
def complete(payload):
    return {
        "resultType": "complete",
        **payload,
        "_meta": {SERVER_INFO_KEY: SERVER_INFO},
    }
```

列表、读取与发现 handler 会额外添加 `ttlMs` 与 `cacheScope`。把该包装器集中化，可以防止某个 handler 悄悄漏掉现代结果字段。

### 不允许 server 发起的请求

现代 server 可以发送与某个客户端请求相关的通知，或在客户端打开的 `subscriptions/listen` 流上发送通知。它绝不能发送自己的 JSON-RPC 请求。

当某个 handler 需要 sampling、elicitation 或 roots 输入时，它返回 `input_required` 结果。客户端完成内嵌的输入请求，并用新的请求 id 重试原始方法。第 11 课会覆盖这种 Multi Round-Trip Request 模式。

### 显式的旧版兼容

双时代 server 也可以在一条清楚隔离的旧版分支上实现 `2025-11-25` 握手。当出现必需的现代 `_meta` 字段时，它选择现代行为；当收到 `initialize` 时，它选择旧版行为。

不要把一个 `2026-07-28` 请求送进旧版握手路径。不要把现代的 `resultType` 字段盖到旧版初始化结果上。本课代码刻意只支持现代，以便其不变量保持可见。

```figure
t3-dispatch-loop
```

## Use It

运行 Python server 的有限 Demo 与测试：

```bash
cd code
python3 main.py --demo
python3 -m unittest discover tests -v
```

用 TypeScript runner 运行 TypeScript 版本：

```bash
npx tsx main.ts --demo
```

Demo 会发送 `server/discover`、列出每一类原语、调用 tools，并展示一个不受支持版本的错误。每个现代请求都会重复其元数据。每个成功结果都包含 server 身份。

## Ship It

本课交付 `outputs/skill-mcp-server-scaffolder.md`。它会产出一份现代 server 方案，包含发现契约、逐请求校验、确定性的可缓存列表，以及一个可选的隔离旧版适配器。

## Exercises

1. 从某个请求中移除 capabilities，并证明 server 不会复用上一个请求的声明。
2. 反转 `TOOLS`、`PROMPTS` 与 note 的插入顺序。确认所有列表结果保持稳定。
3. 添加一个带破坏性的 `notes_delete` tool，并在执行器内部要求授权检查。让 `destructiveHint` 仅作为 UX 提示保留。
4. 添加 `resources/templates/list`，包含 `ttlMs`、`cacheScope` 与确定性排序。
5. 为 `2025-11-25` 构建一个独立的旧版适配器。添加测试证明现代请求永远不会进入它。

## Key Terms

| 术语 | 含义 |
|------|---------|
| 无状态 server | 依据每个请求自身的元数据处理它，不保留协议会话记忆 |
| `server/discover` | 强制性的现代方法，用于通告版本与 capabilities |
| 完整结果 | `resultType: "complete"` 的成功现代结果 |
| 可缓存结果 | 带 `ttlMs` 与 `cacheScope` 的发现、列表或资源读取结果 |
| 确定性列表 | 相同的逻辑注册表产生相同的条目顺序 |
| Server 身份 | 结果 `_meta` 中推荐的 `io.modelcontextprotocol/serverInfo` |
| Tool 错误 | 合法的 tool 调用，但返回带 `isError: true` 的内容 |
| 协议错误 | 通过 `error` 返回的不合法 JSON-RPC 或 MCP 请求 |

## Further Reading

- [MCP 规范 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/)
- [MCP 服务器发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [MCP Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MCP stdio 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
