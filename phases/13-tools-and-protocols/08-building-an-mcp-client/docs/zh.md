# 构建 MCP Client：发现、路由与双时代回退

> 现代 MCP client 会在每个请求上重复其契约。它最难的兼容性决策，是判断一个旧 server 何时确实很旧，以及一个现代 server 何时在报告一个可纠正的错误。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课
**Time:** ~85 分钟

## Learning Objectives

- 用当前的元数据构建每个 MCP `2026-07-28` 请求。
- 用 `server/discover` 探测 stdio server，并选择一个双方都支持的版本。
- 仅对显式列入允许列表的 peer 授权一次有边界的旧版探测。
- 只有在为某个受支持的修订版本校验到正向的 `initialize` 结果之后，才接受旧版时代。
- 合并具有确定性的 tool 列表，但不要悄悄覆盖冲突项。
- 把调用路由到拥有该 tool 的 peer，同时不臆造协议会话。

## 问题场景

一个 agent host 通常要和不止一个 MCP server 通信。它必须发现每个 server、合并 tool 目录、解析重名、路由调用，并从传输失败中恢复。

`2026-07-28` 修订版让稳态更简单，因为每个请求都是自包含的。兼容性则让启动阶段更微妙。一个客户端可能遇到：

- 一个支持首选版本的现代 server；
- 一个返回可识别版本错误或头部错误的现代 server；
- 一个从未听说过 `server/discover` 的旧版 server；
- 一个在收到 `initialize` 之前一直保持沉默的旧版 server。

把每个探测错误都当作旧版是危险的。一个格式错误的现代请求、一个过载的 server、一个死掉的进程和一个旧 server，都可能产生相同的超时或连接关闭。这些信号是模糊的。客户端必须把显式的运维意图与正向的协议证据结合起来，才能选择旧版时代。

## 核心概念

### 一个 peer，而不是一个协议会话

为每个 server 进程或端点保留一条传输 peer 记录：

- 传输句柄或发送函数；
- 已选定的协议时代与版本；
- 最近一次发现的 server capabilities；
- 最近一次的确定性 tool 列表；
- 用于关联的待处理请求 id；
- 传输健康状况。

这是客户端的簿记信息。它不是协议会话状态。在现代 MCP 中，server 仍然会在每个请求上收到当前的版本与 capabilities。

### 从零构建每个现代请求

```python
def modern_request(request_id, method, params, version, capabilities):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            **params,
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientCapabilities": capabilities,
                "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
            },
        },
    }
```

不要把元数据只附加到连接对象上一次，然后假设它已经到达线上。要为最终序列化后的请求打标并检查。

### 现代发现

`server/discover` 返回受支持的版本、server capabilities、instructions、缓存提示以及推荐的 server 身份。客户端选择双方都支持的最高现代版本。

对于仅支持现代的客户端，发现是可选的，但在 stdio 上推荐使用。有些旧版 server 会在初始化之前接受操作，因此先发 `tools/list` 可能产生一个含义模糊的成功。`server/discover` 划出一条清晰的时代边界。

### stdio 兼容性探测

一个双时代 stdio 客户端会在任何其他请求之前，先带着自己首选的现代元数据发送 `server/discover`。结果有三类：

1. **DiscoverResult。** server 是现代 server。选择一个双方都支持的版本，并以逐请求元数据继续。
2. **可识别的现代错误。** server 是现代 server。对于 `-32022`，从 `data.supported` 中选择并用新的请求 id 重试。对于头部错误或 capability 错误，修正请求。不要发送 `initialize`。
3. **模糊信号。** 无法识别的 JSON-RPC 错误、超时、连接关闭或空响应，都无法确定时代。除非该确切 peer 配置了旧版兼容，否则按失败关闭处理（fail closed）。

可识别的现代协议错误包括：

- `-32020` HeaderMismatch
- `-32021` MissingRequiredClientCapability
- `-32022` UnsupportedProtocolVersion

即使 peer 位于旧版允许列表中，可识别的现代错误也仍然保持现代。一旦某个 server 证明它理解了现代错误词汇，发送 `initialize` 就会构成降级。

不要把 `-32601` 当作正向的旧版证据。它只是让一个显式列入允许列表的 peer 有资格接受一次旧版探测。同样的规则适用于超时、连接关闭或空响应。

### 允许列表是运维意图，而不是证据

旧版兼容必须是一个固定 peer 配置的显式属性：

```python
client.add_server("archive", archive_transport, allow_legacy=True)
```

把这一选择绑定到已配置的命令或端点。不要使用通配符，让任意 server 自行选择更弱的语义。没有 `allow_legacy=True` 的 peer，在遇到模糊的发现结果后就失败，并且永远不会收到 `initialize`。

允许列表授予的是探测的许可。它并不选择时代。客户端在传输层强制执行的期限内发送一次 `initialize`，随后要求以下全部条件成立：

- 一个 JSON-RPC `2.0` 响应，且请求 id 匹配；
- 恰好一个 `result`，且没有 `error`；
- `protocolVersion` 属于客户端已配置的旧版修订版本集合；
- `capabilities` 字段为对象值；
- `serverInfo` 对象中的 `name` 与 `version` 字段均为非空字符串。

超时、连接关闭、错误响应、格式错误的结果、id 不匹配或不受支持的修订版本，都按失败关闭处理。只有结构合法的正向结果才能选择旧版时代。代码把 `legacy_probe_timeout_ms` 传给传输适配器；真正的 stdio 或 HTTP 适配器必须强制该期限，而不是仅仅记录它。

为传输 peer 缓存已选定的时代。不要每次调用前都重新探测。

### 旧版是一条兼容分支

一旦有边界的探测返回了合法的正向旧版证据，客户端就严格按该修订版本的定义使用已选定的旧版版本：

1. 校验响应信封与关联 id。
2. 校验协商出的修订版本位于已配置的旧版集合中。
3. 记录已校验的 capabilities 与 server 身份。
4. 仅在所有检查都通过之后，才发送 `notifications/initialized`。
5. 在该传输生命周期内使用旧版请求形状。

这条分支是为了与已知 peer 互操作而存在。它不是新 server 或新请求的默认设计。如果传输重启或其端点发生变化，就丢弃 peer 时代缓存并重新协商。

### 发现并缓存 tools

对每个活跃 peer 调用 `tools/list`。现代结果包含 `resultType`、`ttlMs` 与 `cacheScope`。在正确的授权上下文中遵守新鲜度提示。在过期后或收到已订阅的列表变更事件后重新获取。

客户端必须把旧版 server 缺失的 `resultType` 视为 `"complete"`。对于来自更早协商时代的响应，不要要求现代缓存字段。

server 应返回确定性排序。客户端在合并前也应排序，这样本地注册表顺序不依赖进程启动时机。

### 冲突安全的命名空间合并

两个 server 可能都暴露 `search`。选择一条已声明的策略：

1. **冲突时加前缀。** 保留第一个规范名，后续冲突项以 `<server>/<tool>` 暴露。
2. **冲突时拒绝。** 不加载重复项，并抛出清晰的配置错误。
3. **静默覆盖。** 绝不使用。它会掩盖最终是哪个 server 接收了模型选择的动作。

同时存储规范名与本地名。模型看到的是规范名。发出的 `tools/call` 使用拥有该 tool 的 server 所声明的本地名。

### 路由一次调用

路由是一次纯粹的查表：

```text
canonical tool name
  -> peer name + local tool name
  -> new JSON-RPC request id
  -> modern request metadata or explicit legacy shape
  -> matching response id
```

当拥有该调用的传输不可用时，不要发送调用。重连或重启传输，然后重新执行发现与 `tools/list`。在传输断开时丢失的现代在途请求，只要操作的安全策略允许，就可以用新的 JSON-RPC id 重试。

### 通知与订阅

现代的列表与资源变更只会在客户端打开的 `subscriptions/listen` 流上到达。客户端发送通知过滤器，等待 `notifications/subscriptions/acknowledged`，并通过通知元数据中的 listen 请求 id 来关联事件。

断开连接时，打开一个新的 listen 请求，并重新获取相关的列表或资源。现代流不会用 `Last-Event-ID` 恢复。

### 不允许 server 发起的请求

现代 server 不会就 sampling、elicitation 或 roots 用独立的 JSON-RPC 请求去调用客户端。它们返回 `input_required`，客户端在完成内嵌的输入请求后重试原始请求。

在完成输入期间，不要阻塞该 peer 的响应读取器。保持关联关系，并为重试创建新的 JSON-RPC id。

```figure
tp-client-merge
```

## Use It

`code/main.py` 使用进程内的 peer 函数，让协议决策保持可见。它连接两个现代 peer 和一个刻意列入允许列表的旧版 peer，然后合并并路由它们的 tools。传输可调用对象会接收一个超时预算，这样兼容分支就无法隐藏一次无界探测。

```bash
cd code
python3 main.py
python3 -m unittest discover tests -v
```

这些测试证明了普通 Demo 容易遗漏的边界：

- 现代请求会重复其元数据；
- `-32022` 会重试现代发现，而不进行初始化；
- 可识别的现代错误绝不降级，即使是允许列表中的 peer；
- 超时、连接关闭、空响应与无法识别的错误，在没有允许列表时不会触发 `initialize`；
- 列入允许列表的 peer 只有在收到合法且受支持的 `initialize` 结果后，才变为旧版；
- 格式错误与不受支持的旧版结果会让该 peer 保持不可用；
- 成功选定的时代会在该传输生命周期内被缓存。

## Ship It

本课交付 `outputs/skill-mcp-client-harness.md`。它会搭建现代请求打标、stdio 时代协商、确定性命名空间合并、路由，以及一条失败关闭的旧版兼容分支。

## Exercises

1. 让一个假 server 返回 `-32022`，且没有任何双方共同支持的版本。确认客户端失败，而不是发送 `initialize`。
2. 把一个假的旧版 server 列入允许列表，让它有边界的 `initialize` 探测超时，并证明该 peer 保持 `unknown` 且不可用。
3. 为两个授权上下文添加 `cacheScope: "private"` 的 tool 列表。确认客户端绝不会把某个上下文缓存的结果共享给另一个。
4. 把冲突策略改为拒绝，并让启动失败，错误信息中包含两个 peer 名称。
5. 添加一个有限的 `subscriptions/listen` 模拟器。在流丢失时，用新的请求 id 重新监听并重新获取 tools。

## Key Terms

| 术语 | 含义 |
|------|---------|
| Peer | 客户端侧针对一个 server 传输及其已发现数据的记录 |
| 协议时代 | 现代的逐请求元数据，或旧版初始化语义 |
| 发现探测 | 用于识别 stdio 时代的首次 `server/discover` |
| 可识别的现代错误 | 证明现代行为、并禁止旧版回退的错误 |
| 旧版允许列表 | 允许对固定 peer 做一次有边界兼容探测的运维配置 |
| 正向旧版证据 | 针对显式受支持的旧版修订版本、合法且可关联的 `initialize` 结果 |
| 合并命名空间 | 跨所有活跃 peer 的规范 tool 名 |
| 冲突策略 | 针对重复 tool 名的加前缀或拒绝规则 |
| 时代缓存 | 为一个传输 peer 存储的已选定现代或旧版行为 |
| 传输恢复 | 重启或重连、重新发现、重新列出，并用新的 id 安全重试 |

## Further Reading

- [MCP 规范 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/)
- [MCP 服务器发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP stdio 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [MCP 版本管理](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
