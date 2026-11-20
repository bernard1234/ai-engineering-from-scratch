# MCP 工具契约与内容

> 只有当发现、参数、结果、分页与传输元数据都遵循同一份契约时，一个工具才可以被安全地自动化。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07、09、10 课
**Time:** ~120 分钟

## Learning Objectives

- 使用 JSON Schema 2020-12 定义工具的输入与输出。
- 在不假设结构化结果一定是 JSON 对象的前提下校验它们。
- 在 text、image、audio、resource link 与 embedded resource 之间做出选择。
- 在工具抵达模型之前拒绝不安全的 `x-mcp-header` 定义。
- 对参数 header 的取值进行编码，并校验 header 与 body 的完全一致。
- 遍历游标分页，且不解释游标取值。
- 对 `completion/complete` 建议进行限界与授权。

## 问题场景

调用一个 Python 函数很简单。通过 AI 宿主调用一项远端能力则是一个契约问题。

服务器发布一个描述符。客户端把这个描述符转成模型上下文与用户界面。模型生成参数。网关可能依据镜像的 header 转发请求。服务器执行工具。随后客户端判断结果是否足够安全和有效，可以返回给模型。

任何一处薄弱的边界都会污染整条链。

考虑五种失败：

- 描述符声明结果是 object，但服务器返回了 array。
- 当 `nextCursor` 是空字符串时，客户端停止了分页。
- 一个 token 参数被镜像到 HTTP header 中，从而对中间方可见。
- 一个 Unicode 路由值以原始 header 形式发送，网关与源站对字节的解释不一致。
- completion 端点向一个无权访问生产环境的调用方建议了生产环境。

这些失败没有一个能靠更好的 prompt 修复。它们需要显式的协议契约与应用契约。

## 契约流水线

把每次工具调用视为五道门：

1. **发现。** 读取一个确定性的、分页的工具列表。
2. **准入。** 校验每个描述符，并应用本地安全策略。
3. **调用。** 校验参数并构建传输元数据。
4. **执行。** 运行 handler，并正确归类失败。
5. **消费。** 在模型使用之前校验内容块与结构化输出。

```figure
mcp-contract-pipeline
```

准入门与消费门归宿主所有。服务器无法强迫客户端信任它的注解、schema 或输出。

## JSON Schema 是运行时边界

在 MCP `2026-07-28` 中，`inputSchema` 与 `outputSchema` 使用 JSON Schema。当 `$schema` 缺失时，默认方言是 2020-12。

输入 schema 必须是一个 schema 对象。一个没有参数的工具也应当明确说明它接受什么：

```json
{
  "type": "object",
  "additionalProperties": false
}
```

这比接受任意属性的 `{ "type": "object" }` 更严格。

输出 schema 是可选的。一旦服务器发布了它，每一个完整的工具结果都承诺返回符合该 schema 的 `structuredContent`，包括 `isError: true` 的结果。错误标志用于归类执行结果；它并不豁免已发布的输出契约。客户端应当校验结果，而不是信任描述符。

### structuredContent 可以是任意 JSON 值

不要把 `structuredContent` 硬编码为字典。它可以是：

- 一个 object；
- 一个 array；
- 一个 string；
- 一个 number；
- 一个 boolean；
- `null`。

这个工具返回一个 array：

```json
{
  "name": "tag_catalog",
  "inputSchema": {
    "type": "object",
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

它成功时的结果是有效的：

```json
{
  "resultType": "complete",
  "content": [
    {
      "type": "text",
      "text": "[\"contracts\", \"mcp\", \"stateless\"]"
    }
  ],
  "structuredContent": ["contracts", "mcp", "stateless"],
  "isError": false
}
```

为兼容性起见，结构化结果还应当在 text 块中包含序列化后的 JSON。文本不是校验来源，`structuredContent` 才是。

### 一个小型校验器也能教会这条边界

本课刻意使用 JSON Schema 的一个子集，因为它必须留在 Python 标准库之内。它检查示例工具所使用的机制：

- object、array、string、integer、number、boolean 与 null 类型；
- 必需属性；
- `additionalProperties: false`；
- array items；
- enum 取值；
- 字符串最小长度。

这不是完整生产级校验器的替代品。可复用的经验在于校验发生的位置：描述符在发现之后、参数在执行之前、结构化结果在消费之前。

## 内容块承载着不同的代价

`content` 数组可以组合多种内容类型。

| 类型 | 用于 | 主要边界 |
|------|------------|---------------|
| `text` | 人和模型可读的摘要 | 把文本视为不可信输出 |
| `image` | 以 base64 编码的视觉证据 | 校验媒体类型与大小 |
| `audio` | 以 base64 编码的语音或录音输出 | 校验媒体类型与时长限制 |
| `resource_link` | 客户端稍后可获取的 URI | 对后续的资源读取重新授权 |
| `resource` | 直接嵌入结果中的数据 | 立即强制载荷与内容限制 |

resource link 并不证明该资源出现在 `resources/list` 中。它是本次工具调用返回的一个引用。当客户端跟随该 URI 时，仍需应用自己的资源策略。

embedded resource 避免又一次往返，但会增大当前响应的大小。对体积较大或独立变化的工件使用 links。对必须与结果原子性地一起传输的小型证据使用 embedded resources。

本课的 `evidence_bundle` 结果包含全部五种类型。客户端在接受结果之前会逐个校验每个块。

## x-mcp-header 是路由元数据

`inputSchema` 内部的一个属性可以声明 `x-mcp-header`。在 Streamable HTTP 之上，客户端会把该参数镜像到 `Mcp-Param-{name}`。

```json
{
  "region": {
    "type": "string",
    "x-mcp-header": "Region"
  }
}
```

当 `region: "eu-west"` 时，传输层可以发出：

```http
Mcp-Param-Region: eu-west
```

这个注解的存在，是为了让负载均衡器、网关或策略引擎无需解析 JSON body 就能路由。它不是放置凭据的地方。

协议对该注解施加了限制：

- header 名称非空，并遵循 HTTP field-name token 语法；
- header 名称在不区分大小写的情况下唯一；
- 属性类型为 string、integer 或 boolean；
- 不允许 `number`；
- 该注解只出现在 `inputSchema.properties` 的直接成员上；
- 整数值保持在 `-9007199254740991` 到 `9007199254740991` 之间。

位置规则是语法性的，且失败关闭。请遍历整棵 schema 树，而不只是你的校验器恰好理解的 properties。拒绝嵌套对象 `properties` 下的注解、`oneOf` 分支内的注解、`items` 内的注解、由 `$ref` 到达的定义内的注解，以及任何 output schema 中的注解。解析引用并不会把被引用的节点变成直接顶层属性。

本课增加了一条部署策略：拒绝那些镜像 `password`、`secret`、`token`、`api_key` 或 `authorization` 等名称的描述符。官方规范建议服务器作者不要镜像敏感参数。客户端可以把这条建议变成一条硬性准入规则。

审计 header 名称，而不是它的值。示例代码记录 `Mcp-Param-Region`，同时让 `eu-west` 不出现在审计事件中。

### 在构建 HTTP header 之前先编码取值

一个参数值只有这样才可以按纯文本传输：它是一个非空字符串，由从 `!` 到 `~` 的可见 ASCII 字符组成，并且看起来不像编码哨兵。其他所有情况都使用这个确切形式：

```text
=?base64?{Base64UTF8}?=
```

`Base64UTF8` 是对确切 UTF-8 字节做标准 base64。不要先裁剪、规范化或替换取值。对 Unicode、空字符串、空格、制表符、控制字符、CR 或 LF、首尾空白，以及任何以 `=?base64?` 开头的取值进行编码。把看起来像哨兵的取值再编码一次，恰恰能让接收方还原字面原文，而不是把它当作传输语法来解码。

布尔值渲染为小写的 `true` 或 `false`。整数以 10 进制渲染，并且必须落在 JavaScript 安全整数范围内。超出该范围的取值会被拒绝，而不是被中间方四舍五入。

### 服务器校验镜像的副本

header 生成只是客户端的那一半。在 Streamable HTTP 边界上，服务器必须：

1. 在不区分 header 名称大小写的情况下找到已识别的 `Mcp-Param-*` 名称；
2. 在存在时解码确切的 base64 哨兵形式；
3. 把解码后的文本与 JSON body 中对应的参数完全比较；
4. 在派发之前拒绝缺失的、重复的、意外的、畸形的或不匹配的已识别 header。

拒绝的形式是 HTTP `400`，并带有 JSON-RPC 错误码 `-32020`。body 取值及其编码后的 header 形式都不应出现在审计记录中。只记录已识别的 header 名称和拒绝类别。

`code/main.py` 直接建模了这条边界。[第 09 课](../../09-mcp-transports/) 覆盖了更完整的 Streamable HTTP 校验顺序，包括方法与协议版本的一致性。

## 分页游标是不透明的

MCP 的列表操作使用游标分页。服务器选择页大小与游标格式。客户端只有一个决策：

```python
if result.get("nextCursor") is None:
    break
cursor = result["nextCursor"]
```

不要这样写：

```python
if not result.get("nextCursor"):
    break
```

空字符串是合法游标。真假值判断会过早停止。

客户端不得解码游标、对它做自增、把它与之前的游标比较排序，或推断页码。服务器可以对游标签名、把它绑定到某个 catalog 版本，或把它映射到私有状态。那是服务器的实现细节。

示例服务器在首页之后刻意返回 `""`。客户端必须在第二次请求中发送这个确切取值。它的 trace 是：

```text
<first request with no cursor>
<second request with cursor "">
```

无效游标会产生 JSON-RPC invalid params，错误码 `-32602`。

## completion 是一个授权面

`completion/complete` 为 prompt 参数和资源模板参数提供建议。它适用于交互式表单，但也可能泄露普通列表方法所保护的名称。

一次 completion 请求会指明一个 reference 以及正在补全的参数：

```json
{
  "method": "completion/complete",
  "params": {
    "ref": {
      "type": "ref/prompt",
      "name": "deployment_review"
    },
    "argument": {
      "name": "environment",
      "value": "st"
    }
  }
}
```

结果最多返回 100 个取值，并可能报告 `total` 与 `hasMore`。

应用与被引用的 prompt 或 resource 相同的授权边界。示例中的 analyst 收到 `development` 与 `staging`。只有 operator 才能收到 `production`。

生产环境的 completion 还需要：

- 输入校验；
- 感知调用方的过滤；
- 客户端侧的请求防抖；
- 服务器侧的速率限制；
- 有界的结果数量；
- 不暴露敏感建议取值的日志。

completion 是辅助功能，不是绕过发现的通道。

## 两层错误

把协议错误与工具执行错误分开。

当 MCP 请求无法被正确派发时，使用 JSON-RPC 错误：

- 未知的工具名称；
- 畸形的请求结构；
- 缺失的请求元数据；
- 无效的游标。

当调用已经到达工具，且工具报告了一个可处理的失败时，使用带 `isError: true` 的完整工具结果：

- 某个报告来源不可用；
- 某个日期超出支持范围；
- 某条业务规则拒绝了所请求的操作。

模型往往能够修复工具执行错误。它们无法修复一个违反自身输出 schema 的服务器。

如果工具声明了输出 schema，就要在该 schema 之内建模可处理的失败。示例中的 `route_report` 失败会随人类可读的错误文本和 `isError: true` 一起，返回它被请求的 region 与 `accepted: false`。

## Build It

`code/main.py` 用 Python 标准库构建了这条边界的双方。

服务器实现了：

- 逐请求的 MCP 元数据校验；
- 带 tools 与 completions 能力的 `server/discover`；
- 确定性的 `tools/list` 分页；
- 四个工具描述符，其中包含一个必须被拒绝的；
- array 结构化输出；
- 当前所有工具内容块类型；
- 一道 Streamable HTTP 一致性门，解码已识别的参数 header，并在不匹配时返回 HTTP `400` 加 JSON-RPC `-32020`；
- 经授权并限速的 completion。

客户端实现了：

- 描述符准入；
- 全树 `x-mcp-header` 位置校验与敏感字段策略；
- 精确的纯可见 ASCII 或 base64 UTF-8 取值编码；
- 跟随空字符串的不透明游标循环；
- 参数与结果校验；
- 内容块校验；
- 只包含名称、不含取值的 header 审计事件。

那个刻意不安全的描述符是教学数据。它证明一个被拒绝的工具不会阻止有效工具加载。

## Use It

从仓库根目录：

```bash
cd phases/13-tools-and-protocols/28-mcp-tool-contracts-and-content/code
python3 main.py
python3 -m unittest discover tests -v
```

这个 demo 会打印已准入的工具、被拒绝的描述符、两次分页请求、结构化 array 内容、内容块类型、镜像后的 header 名称、取值是否需要编码、HTTP 一致性状态，以及按调用方过滤后的 completion 取值。

## 交互实验

打开 `code/main.py`，找到 `TOOLS`。

1. 把 `tag_catalog.outputSchema.type` 从 `array` 改为 `object`。
2. 运行 demo。客户端应当拒绝返回的 array。
3. 恢复该 schema。
4. 让首页的 `nextCursor` 保持为 `""`，然后让最后一页返回 `nextCursor: None`，而不是省略该字段。
5. 运行测试并比较游标 trace。
6. 给一个字符串属性添加 `x-mcp-header: "Authorization"`。
7. 确认描述符准入在调用之前就拒绝了它。
8. 尝试 `region` 取值包含 Unicode、换行符、首尾空格，以及字面文本 `=?base64?SGVsbG8=?=`。逐个解码发出的 header，并证明原始取值被精确保留。
9. 把该注解移动到 `oneOf`、`items` 或某个 `$ref` 定义之下。即使该分支从未被 demo 使用，也要确认每个描述符都被拒绝。
10. 移除已识别的 header，或改动其解码后的取值。确认 HTTP 边界返回状态 `400` 与 JSON-RPC 错误码 `-32020`。

重点不是记住某种 JSON 形状，而是观察每道门在拥有它的边界上失败。

## 练习实验

用一个 `search_evidence` 工具扩展这个契约实验。

要求：

1. 它的输入 schema 接受 `query`、`limit` 和一个安全的 `region` 路由字段。
2. 它的输出 schema 是一个由包含 `uri`、`title` 与 `score` 的对象组成的 array。
3. 结果包含兼容性文本，以及每一项对应的 resource link。
4. 参数拒绝未知属性。
5. `limit` 由应用校验限界。
6. 无权访问某个 URI 的调用方，永远不会通过 completion 或工具输出看到该 URI。
7. 测试包含一个不符合 schema 的 score、一个非法的 header 注解，以及一个两页的列表。
8. Header 取值的测试覆盖可见 ASCII、Unicode、控制字符、空白、看起来像哨兵的文本，以及 JavaScript 安全整数的两个边界。
9. HTTP fixture 接受不区分大小写的 header 名称，但对缺失或不匹配的已识别取值以状态 `400` 和错误码 `-32020` 拒绝。

## 交付工件

`outputs/skill-mcp-contract-reviewer.md` 是一个扁平的、可复用的评审 skill。给它一份工具描述符、若干示例结果、分页行为和 completion 策略，它会返回准入决定、结果校验计划、header 策略以及具体的失败测试。

## 验证

当以下陈述都为真时，本课完成：

- `tools/list` 在重复调用时返回相同的逻辑顺序。
- 当 `nextCursor` 为 `""` 时，客户端会发起第二次请求。
- 不安全的敏感 header 描述符被排除，而其他工具仍然可用。
- 一个 array 能通过其 array 输出 schema。
- 一个 object 无法通过同一个 array schema。
- 错误结果不能省略或违反已发布的输出 schema。
- text、image、audio、resource link 与 embedded resource 块都能通过校验。
- Header 审计事件只包含名称，不包含取值。
- 纯可见 ASCII 保持原样；Unicode、控制、带填充、空以及看起来像哨兵的取值都能通过精确的 base64 UTF-8 编码往返。
- 超出 JavaScript 安全范围的镜像整数会被拒绝。
- `oneOf`、`items`、嵌套对象、`$ref` 定义或输出 schema 之下的注解会在准入阶段被拒绝。
- 不区分大小写的已识别 header 名称只有在解码后的取值与 body 完全匹配时才通过；缺失或不匹配的副本会产生 HTTP `400` 与 JSON-RPC `-32020`。
- analyst 的 completion 永远不会返回 `production`。
- 工具失败使用 `isError: true`；畸形的协议调用使用 JSON-RPC `error`。

## 生产失败模式

| 失败 | 学习者看到什么 | 正确的应对 |
|---------|-----------------------|------------------|
| 客户端假设输出是 object | 合法的 array 失败或被静默包装 | 按已发布的 schema 校验，不要只支持 object 类型 |
| 空游标被当作假值 | 最后一页消失 | 只要 `nextCursor` 存在且非 null 就继续 |
| 敏感取值被镜像 | 密钥出现在代理、WAF 或 trace 数据中 | 拒绝该描述符，把密钥留在受保护的请求数据中 |
| 原始 Unicode 或空白被镜像 | 网关与源站不一致，或取值被规范化 | 使用精确的 base64 UTF-8 哨兵编码，并在解码后比较 |
| 注解藏在 schema 分支里 | 客户端在准入时漏掉路由元数据 | 遍历整棵 schema 树，只允许直接顶层属性 |
| 大整数被镜像 | JavaScript 中间方对路由取值做了舍入 | 拒绝超出 JavaScript 安全整数范围的取值 |
| header 与 body 不一致 | 网关路由到一个目标，源站却执行另一个 | 在派发之前以 HTTP `400` 与 JSON-RPC `-32020` 拒绝 |
| 输出 schema 被忽略 | 下游代码消费了损坏的结构 | 在模型或应用使用之前校验 |
| resource link 被自动信任 | 调用方跟随了一个未授权的 URI | 对每一次资源读取重新授权 |
| completion 共享全局建议 | 隐藏的租户名称泄露 | 按调用方、reference 和授权进行过滤 |
| 把工具注解当作策略 | 破坏性操作绕过了确认 | 在注解之外强制授权与审批 |
| 一个畸形工具破坏发现 | 整个服务器变得不可用 | 拒绝坏描述符，并独立地准入有效工具 |

## Capstone 关联

第 13 阶段的 capstone 需要一个能够合并多个服务器工具的网关。本课提供了它的准入核心。

用这份工件给四类 capstone 证据评分：

- 确定性且完整的分页发现；
- 在暴露给模型之前的描述符校验；
- 经过校验的结构化输出加上有界的内容块；
- 保持授权边界的 completion 与路由元数据。

不要仅凭一次成功的 `tools/call` 就声称网关兼容。要采集描述符、分页 trace、已准入工具集、被拒绝工具集，以及一个经过校验的结果。

## Key Terms

| 术语 | 含义 |
|------|---------|
| `inputSchema` | 定义可接受的工具参数的 JSON Schema 对象 |
| `outputSchema` | 可选的定义 `structuredContent` 的 JSON Schema |
| `structuredContent` | 工具结果产出的任意 JSON 值 |
| Content block | 带类型的 text、image、audio、resource link 或 embedded resource |
| `x-mcp-header` | 把某个原始类型参数镜像到 Streamable HTTP 元数据的 schema 注解 |
| Opaque cursor | 由服务器签发的分页令牌，客户端不解释其取值 |
| Completion reference | 正在补全其参数的 prompt 名称或资源 URI/模板 |
| Admission | 客户端针对某个已发现描述符做出的暴露或拒绝决定 |

## Further Reading

- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Completion](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/completion)
- [MCP Pagination](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/pagination)
- [MCP Streamable HTTP Parameter Headers](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#custom-headers-from-tool-parameters)
