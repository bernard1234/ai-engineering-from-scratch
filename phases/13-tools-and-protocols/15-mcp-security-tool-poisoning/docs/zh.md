# MCP 安全：被投毒的元数据、路由与 MRTR 状态

> 无状态并不等于无信任。它意味着每个请求都会暴露 server 与 gateway 独立校验该调用所需的证据。

**Type:** Learn
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课（MCP server）、第 13 阶段，第 08 课（MCP client）
**Time:** ~60 分钟

## Learning Objectives

- 把工具描述、注解、client 信息和 server 信息视为不可信数据。
- 检测元数据投毒、描述符变更和跨 server 的名称冲突。
- 校验 2026-07-28 的请求元数据与 Streamable HTTP 路由头。
- 保护 MRTR 的 `requestState` 免受篡改，并把确认绑定到精确的参数。
- 对 principal（而不是已被移除的协议会话）施加授权与速率限制。

## 问题场景

模型读取工具描述来决定调用什么。路由器读取工具名称来决定请求发往哪里。用户读取标签来决定批准什么。一个恶意描述符可以同时针对这三者。

官方的 MCP 安全指引很直接：除非来自可信 server，否则描述与注解应视为不可信。即便来自可信 server，部署信任也可能变化。server 更新、被污染的包、registry 错误或 gateway 合并，都可能改变模型看到的内容。

当前协议也改变了安全边界。在 2026-07-28 中既没有核心握手，也没有传输会话。只按 `Mcp-Session-Id` 来索引审批、限速或审计历史的安全设计，不是当前的设计。

## 核心概念

### 七个值得检查的攻击面

用一份具体的清单代替"要小心"这样的笼统指示。

1. **元数据投毒。** 描述中包含与已声明工具行为无关的指令。
2. **描述符钓鱼（rug pull）。** 此前已批准的名称、描述、schema 或注解发生了变化。
3. **跨 server 遮蔽。** 两个后端暴露同一个未限定工具名，路由静默地选择了其中一个。
4. **头部与 body 混淆。** `Mcp-Method` 或 `Mcp-Name` 与 JSON-RPC 请求不一致。
5. **能力升级。** 对端声称具备某个扩展或客户端特性，而 server 把该声明误当作授权。
6. **MRTR 状态篡改。** 客户端改动 `requestState`、回答另一个问题，或用不同参数复用确认。
7. **供应链身份混淆。** 熟悉的显示名称被当作发布者或 server 身份的证明。

这些攻击面彼此重叠。哈希固定有助于发现描述符变更，但不能证明首个描述符就是安全的。静态扫描能抓住明显词句，却抓不住微妙的指令。命名空间能防止一类冲突，却挡不住恶意但已加命名空间的 server。要把这些控制叠加起来。

### 当前请求信封是证据，不是身份

每个 2026-07-28 请求都包含：

```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {
      "elicitation": {"form": {}}
    },
    "io.modelcontextprotocol/clientInfo": {
      "name": "security-lab",
      "version": "1.0.0"
    }
  }
}
```

在每个请求上校验版本和能力形状。用能力来选择兼容的响应形状。不要把 `clientInfo` 当作已认证的 principal。它是自报的。

同样的警告适用于结果元数据中的 `io.modelcontextprotocol/serverInfo`。它对日志和调试很有用。它不是证书、registry 证明或授权决策。

### 在策略之前校验路由

对于 `tools/call`，Streamable HTTP 包含：

```text
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.export
```

头部方法必须等于 body 方法。头部名称必须等于 `params.name`。在选择后端、施加 RBAC 或消耗限速令牌之前，就用 `-32020` 拒绝不一致。

这一顺序闭合了一个常见的歧义：一个组件按 body 授权，另一个组件却按头部路由。

wire 校验遵循一个精确序列。校验 JSON-RPC 与元数据类型，比较头部值与 body，然后检查匹配到的版本是否受支持。头部不匹配时返回 HTTP 400 和 `-32020`。如果头部与 body 一致但版本不受支持，返回 HTTP 400、`-32022`，并且 `data` 精确为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。方法未知时返回 HTTP 404 和 `-32601`。

当契约需要结构化的恢复信息时，每个错误对象都包含可选的 `data`。notification 没有 `id`，因此它永远不会收到 JSON-RPC 成功或错误响应。被接受的 HTTP notification 返回 202 和空 body。

### 固定整个描述符

只对描述做哈希会漏掉 schema 和注解的变化。把用户批准过的描述符字段做规范化并哈希：

```python
normalized = json.dumps(tool, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(normalized.encode()).hexdigest()
```

把摘要存放在诸如 `notes.export` 这样的限定键之下，并在此玩具示例之外附上发布者证据和批准时间。

每次刷新时：

- 未知键：隔离，等待审查。
- 相同键、不同摘要：作为 rug pull 隔离，等待重新批准。
- 重复的未限定名称：要求确定性命名空间。
- 扫描器命中：阻断并审查完整的描述符。

哈希相等只证明稳定，不证明安全。被投毒的描述符即使被完美固定，仍然是有毒的。

### 静态扫描是绊线

简单的模式可以标记出角色标签、指令覆盖、隐瞒、机密访问和模糊的网络目的地。它们足够廉价，可用于安装时和 CI。

它们不是语义证明。安全的描述可能在合法的警告中包含被标记的词句。恶意描述也可能避开每一个词句。把扫描器的输出当作审查证据，而不是自动的清白评分。

### 合并之前先加命名空间

假设两个 server 都暴露 `search`。绝不要让 discovery 顺序决定谁胜出。

```text
notes.search
issues.search
```

限定名称是公开的 gateway 名称。把后端映射单独记录。稳定的名称使审批、审计、哈希固定和 `Mcp-Name` 路由都指向同一个对象。

### 能力是兼容性声明

逐请求的 `clientCapabilities` 告诉 server：client 能处理哪些协议特性。它并不授予 client 对工具、数据或动作的访问权。

授权仍然来自已认证的 principal 和资源策略。顺序是：

1. 认证传输凭据。
2. 校验版本、头部和请求形状。
3. 检查能力兼容性。
4. 对 principal、工具、资源和参数授权。
5. 执行或请求用户输入。

### 保护无状态的 MRTR 确认

有后果的工具可能需要用户确认。当前 MCP 使用 Multi Round-Trip Requests，而不是 server 到 client 的回调。

第一个响应：

```json
{
  "resultType": "input_required",
  "inputRequests": {
    "confirm": {
      "method": "elicitation/create",
      "params": {
        "mode": "form",
        "message": "Export notes to archive?",
        "requestedSchema": {
          "type": "object",
          "properties": {
            "confirm": {"type": "boolean"}
          },
          "required": ["confirm"]
        }
      }
    }
  },
  "requestState": "opaque-integrity-protected-value"
}
```

client 获得输入，并用新的 JSON-RPC id 重试原始方法：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "notes.export",
    "arguments": {"query": "private", "destination": "archive"},
    "requestState": "opaque-integrity-protected-value",
    "inputResponses": {
      "confirm": {
        "action": "accept",
        "content": {"confirm": true}
      }
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {"form": {}}
      }
    }
  }
}
```

每个 `inputRequests` 值都是一个完整的、带 `method` 与 `params` 的内嵌请求。其键必须与 `inputResponses` 中对应的条目匹配。form elicitation 使用对象根的 `requestedSchema`，并且 server 发起请求之前，client 必须已声明 form elicitation 能力。

当前能力有两种合法的 form 声明。`{"elicitation":{}}` 隐式支持 form elicitation，而 `{"elicitation":{"form":{}}}` 显式声明它。像 `{"elicitation":{"url":{}}}` 这样仅声明 URL 的写法不支持 form 请求。此时 server 返回 HTTP 400、`-32021`，且 `data.requiredCapabilities` 等于 `{"elicitation":{"form":{}}}`。

把 `requestState` 当作敌意输入。对它签名或加密，校验它，并绑定到方法、工具、精确参数、用途、过期时间、principal，以及（当重放重要时）一次性 nonce。本课代码用 HMAC 和精确参数匹配让这条边界清晰可见。

nonce 台账不能只存在于一个 gateway 对象里。可运行的模型注入一个有界、按 TTL 修剪的重放存储，可被多个 gateway 实例共享。它的原子占用就是执行边界：只有校验过的接受或显式的终止性拒绝才会消费 state。格式错误的响应或 `cancel` 不执行任何操作，并在过期前保持可重试。生产集群需要在共享的持久存储中实现同样的条件占用。

不要把隐藏的确认上下文存进协议会话。任何 server 实例都应能够校验这次重试。

### 高风险调用的"二选二"规则

沿三个维度给一次调用分类：

- 它消费不可信输入。
- 它能访问敏感数据。
- 它会造成有后果的外部动作。

单个自动步骤不应同时具备三者。把它拆开、降低权限，或通过 MRTR 请求显式的用户输入。这是设计启发式，不是协议能力。

### 执行之前先削减权限

单靠无状态并不安全。它消除了隐藏的协议历史，但一个自洽的请求仍可能要求一个权限过大的处理器泄漏数据或做出不可逆的变更。安全来自在每个边界上削减权限：

1. **分型动词。** 暴露一个像 `archive_note` 这样的有界操作，而不是能表达无关能力的通用 `run` 或 `request` 工具。
2. **校验参数。** 条件允许时使用封闭 schema，拒绝未知字段，只归一化一次标识符，限制大小，并在策略评估之前校验目的地、租户和资源所有权。
3. **当前授权。** 把已认证的 principal 绑定到精确的动词、资源、环境和归一化参数。工具注解和客户端能力不授予这项权限。
4. **动作绑定的审批。** 对于有后果的调用，把审批绑定到分型动词与归一化参数的摘要，加上 principal、过期时间和一次性策略。任何字段变化都需要新的决定。
5. **一等公民式的拒绝。** 把拒绝、过期审批、用户拒绝和不安全目的地建模为不产生任何副作用的一等结果。不要把拒绝翻译成更弱的兜底工具。
6. **脱敏的审计证据。** 记录谁提出请求、使用了哪个准入描述符与策略版本、授权了哪个归一化目标、决定为何允许或拒绝，以及执行是否开始。存储摘要或脱敏值，而不是机密。

每一步都在收窄下一组件可做的事。最终处理器应当收到已校验的领域命令，而不是原始模型文本加上宽泛的凭据。在 MRTR 重试、任务更新或 gateway 转发的调用中，重复整条链路。更早的审批不会把后续请求变成可信的会话流量。

### 当前与旧版的交互路径

Roots、Sampling 和 Logging 对新的 2026-07-28 实现已弃用。gateway 只能把旧的请求通道代码保留为版本门控的兼容路径。

不要围绕逐会话的 sampling 限流器构建新的防御。把配额施加到已认证的 principal、签发方、资源、工具和时间窗口。对于当前的交互式工作，检查 MRTR 的 input request 与响应。

### 无状态传输检查

- 在单一 POST 端点上接受现代 MCP 消息。
- 对现代 GET 与 DELETE 返回 405。
- 不要铸造或依赖 `Mcp-Session-Id`。
- 忽略旧的会话头和重放头作为权限输入。
- 为该 POST 返回 JSON 或请求范围的 SSE。
- 仅对选择加入的长期变更通知使用 `subscriptions/listen`。

```figure
tp-tool-poisoning
```

## Build It

`code/main.py` 实现了一个小的进程内安全 gateway 模型。它规范化并固定完整的工具描述符，报告元数据投毒与遮蔽，校验现代请求信封与路由值，并用签名的 `requestState` 和注入的共享重放存储执行一个两轮确认的导出。

该模型在 HTTP 适配器解析完 JSON body 与路由头之后启动。它不校验 `Content-Type` 或 `Accept`。把同一个 dispatcher 接到第 09 课完整的 Streamable HTTP 适配器上，后者要求 `Content-Type: application/json` 以及同时包含 `application/json` 和 `text/event-stream` 的 `Accept` 值。

运行它：

```bash
cd phases/13-tools-and-protocols/15-mcp-security-tool-poisoning
python3 code/main.py
python3 -m unittest discover code/tests -v
```

示例会刻意变更一个描述符。扫描器与摘要比较产生相互独立的发现。随后导出演示 `input_required` 响应和无状态重试。

## Use It

用你自己已批准 server 的归一化快照替换 `SAFE_TOOLS`。让凭据和机密远离该快照。在更新每个新描述符或变更描述符的摘要之前，先审查它。

在 gateway 上，discovery 期间跑一遍这些检查，dispatch 之前再跑一遍。缓存可以减少 discovery 工作，但缓存的审批必须在描述符变化时过期或作废。

## Ship It

本课交付 `outputs/skill-mcp-threat-model.md`。它产出一份当前协议的威胁模型，覆盖元数据、路由、能力、授权、MRTR、缓存、registry 和兼容边界。

## Exercises

1. 把已认证的 principal 和当前授权决策绑定到密封的 MRTR state，然后拒绝在不同 principal 下的重试。
2. 把内存重放存储替换为持久的条件插入，并证明两个进程无法都占用同一个 nonce。
3. 在重放占用之后、模拟导出之前注入一次失败。定义并测试使恢复安全的事务或幂等规则。
4. 在不改变描述的前提下修改某个工具的 `inputSchema`。确认整描述符固定能够发现它。
5. 增加一条策略：当 `tools/list` 因 principal 而异时，拒绝公开缓存。
6. 在 gateway 之后建模一个较旧的 server。把所有握手与会话行为放到显式的 `2025-11-25` 兼容分支之后。

## Key Terms

| 术语 | 含义 |
|------|---------|
| Metadata poisoning | 嵌入工具描述符中的指令或欺骗性声明 |
| Rug pull | 对此前已批准描述符的改动 |
| Tool shadowing | 重复的未限定名称引起的路由歧义 |
| Header mismatch | 路由头与 JSON-RPC body 不一致，错误 `-32020` |
| Hash pin | 完整已批准描述符的摘要 |
| MRTR | 面向 server 请求输入的无状态响应与重试模式 |
| `requestState` | 必须视为不可信输入的不透明往返值 |
| Capability declaration | 对协议兼容性的声明，而非授权 |
| Implicit form support | 空的 `elicitation` 能力对象，等同于支持 form |
| Qualified tool name | 诸如 `notes.search` 的稳定 gateway 名称 |

## Further Reading

- [MCP 安全与信任指南](https://modelcontextprotocol.io/specification/2026-07-28#security-and-trust--safety)
- [多次往返请求（MRTR）](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [已弃用特性](https://modelcontextprotocol.io/specification/2026-07-28/deprecated)
