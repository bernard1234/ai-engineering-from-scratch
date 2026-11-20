# MCP Resources 与 Prompts：为无状态 server 提供可寻址的上下文

> Tools 执行操作。Resources 暴露可寻址的内容。Prompts 打包由用户选择的消息模板。一个良好的 MCP server 会让这些契约保持分离且可预测。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课（构建 MCP Server），第 13 阶段，第 09 课（MCP 传输）
**Time:** ~60 分钟

## Learning Objectives

- 依据消费者的意图在 tools、resources 与 prompts 之间做选择。
- 通过强制性的 `server/discover` 通告 resource 与 prompt 的能力面。
- 构建确定性的 `resources/list` 与 `prompts/list` 结果。
- 应用 `ttlMs` 与 `cacheScope`，同时不泄漏特定用户的数据。
- 对于非法或未知的资源 URI，返回 JSON-RPC 错误 `-32602`。
- 打开一条 `subscriptions/listen` POST 响应流，并按 subscription ID 关联每个事件。
- 把资源内容与 prompt 模板视为不可信的 server 输出。

## 从消费者出发

误用 MCP 最简单的方式，就是从实现代码出发。因为函数很熟悉，就把一个数据库查询做成 tool。因为某个可复用工作流存储在一个文件里，就把它做成 resource。因为 host 可以注入，就把一个 prompt 变成隐藏策略。

要从"由谁选择"和"他们期望什么"出发。

| 原语 | 主要意图 | 选择者 | 典型结果 |
|---|---|---|---|
| Tool | 执行一个操作 | 模型或应用 | 结构化的动作结果 |
| Resource | 读取某个 URI 的内容 | Host、应用或用户 | 文本或二进制内容 |
| Prompt | 启动一个可复用的消息工作流 | 用户通过 host UI | 一条或多条 prompt 消息 |

`notes://note-1` 处的一条 note 是 resource，因为它是可寻址的内容。`delete_note` 是 tool，因为它改变状态。`review_note` 是 prompt，因为用户选择了一个预先准备好的 review 工作流。

不要为了让接口看起来完整，就把同一个操作同时暴露成这三种原语。每多一个能力面，都需要发现、授权、缓存、错误处理、测试与文档。

## 2026-07-28 无状态信封

本课面向 MCP 协议修订版 `2026-07-28`。在这个 profile 中没有初始化握手，也没有协议会话。每个请求都在保留的 `_meta` 键中携带其协议版本与客户端 capabilities。

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

server 必须实现 `server/discover`。它的结果会通告受支持的
版本、resource 与 prompt capabilities、实现身份，以及
缓存提示。客户端可以直接调用其他方法，但发现能让它在构建 UI 之前
先得到一个稳定的快照。

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "resources": {"listChanged": true, "subscribe": true},
    "prompts": {"listChanged": true}
  },
  "ttlMs": 3600000,
  "cacheScope": "public"
}
```

普通结果会声明 `"resultType": "complete"`。响应 `_meta` 通过 `io.modelcontextprotocol/serverInfo` 标识提供服务的实现。这些信息对诊断很有用。它不是认证身份。携带不受支持修订版的请求会返回 `-32022`，并同时给出所请求的修订版本与 server 支持的修订版本。

无状态契约会改变你的设计直觉。列表不能依赖某条连接上一次先前的调用。授权可以改变可见集合，因为凭据是请求输入，但连接历史绝不能影响它。

## 资源是稳定的 URI 契约

resource 是由 URI 标识的内容。先设计 URI，再写 handler。

良好的 URI 特性：

- 足够稳定，可以被书签保存或在请求之间传递。
- 以自己的 server 域作为命名空间。
- 独立于进程 ID 或连接。
- 在访问存储之前先经校验。
- 每次读取都进行授权。

`notes://note-1` 比 `note-1` 更好，因为它的命名空间是显式的。文件 server 可以使用 `file://` URI，但在解析符号链接与相对路径段之后，仍必须检查已配置的目录边界。

`resources/list` 返回当前对调用者可见的资源。按稳定的键（例如 URI）排序。确定性排序能避免嘈杂的缓存未命中、快照漂移，以及 host UI 在刷新之间跳动。

```json
{
  "resultType": "complete",
  "resources": [
    {
      "uri": "notes://note-1",
      "name": "Architecture decision",
      "description": "Why the service uses a stateless boundary",
      "mimeType": "text/markdown"
    }
  ],
  "ttlMs": 300000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "notes-server",
      "version": "2.0.0"
    }
  }
}
```

`resources/read` 返回一个或多个内容项。未知 URI 并不是一次成功的空读取。当前的 Resources 规范把非法或未知的资源 URI 归为 JSON-RPC invalid parameters，错误码 `-32602`。

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32602,
    "message": "Unknown or invalid resource URI",
    "data": {
      "uri": "notes://missing"
    }
  }
}
```

这种区分让客户端能把"不存在"与"合法的空文档"分开。它还能防止意外回退到更宽泛的查找。

### 资源模板

资源模板描述一族参数化的 URI。当逐个列出所有具体条目成本过高或数量无界时，就使用模板。例如，`notes://projects/{project}/decisions/{decision}` 告诉客户端如何构造一个合法地址，而不必返回每一条 decision。

模板不会削弱校验。解析变量、施加授权、强制长度与字符限制，并用带类型的参数构造存储查询。绝不要把任意 URI 尾部拼接到文件系统路径或数据库语句中。

### 内容不是可信指令

资源文本可能包含 prompt injection、机密、误导性命令或格式错误的标记。host 应保留来源信息，并把资源内容当作数据。server 应限制内容大小、返回准确的 MIME 类型、对调用者无权访问的字段做脱敏，并避免返回无关记录。

## Prompt 是用户可控的模板

MCP prompt 是为显式用户选择而设计的。host 可以把它们渲染成斜杠命令、菜单项或 workflow 按钮。协议并不规定某一种 UI。

对于同一请求授权，`prompts/list` 应是确定性的。每个 prompt 都需要稳定的 name、有用的 description，以及能让 host 在 `prompts/get` 之前收集输入的 argument 声明。

```json
{
  "resultType": "complete",
  "prompts": [
    {
      "name": "review_note",
      "title": "Review a note",
      "description": "Review one note for a named concern",
      "arguments": [
        {
          "name": "uri",
          "description": "The note resource URI",
          "required": true
        }
      ]
    }
  ],
  "ttlMs": 600000,
  "cacheScope": "public"
}
```

`prompts/get` 把参数解析为消息。它不会取代 host 的 system instructions。host 决定返回的消息如何进入模型上下文，并让自己的可信策略保持更高优先级。

在 server 边界校验 prompt 参数。一个 prompt URI 应通过与直接读取 resource 相同的授权检查。不要把 prompt 变成绕过 resource 访问的侧信道。

## 缓存提示是正确性的一部分

`ttlMs` 告诉客户端一个结果可以被复用的时长。`cacheScope` 描述谁可以共享该缓存值。

| 范围 | 含义 | 典型用途 |
|---|---|---|
| `public` | 在授权允许时可跨用户复用 | 公开的 prompt 目录 |
| `private` | 绑定到发起请求的用户或凭据上下文 | 用户自有的 note 内容 |

根据数据的变化速率与陈旧带来的损害来选择 TTL。五分钟可能适合一个公开的 prompt 目录。一次私有 note 读取可能使用一分钟。

MCP 只把 `public` 与 `private` 定义为 `cacheScope` 的取值。对于携带机密或快速变化的结果，返回 `cacheScope: "private"` 且 `ttlMs: 0`，然后在 host 缓存策略中施加任何更严格的 no-store 规则。`no-store` 本身并不是 MCP `cacheScope` 的取值。

缓存提示永远不会取代授权。缓存键必须包含每个会改变可见性的请求维度，包括 tenant、user、scope、locale 与分页游标。如果共享缓存无法安全地表达这些维度，就使用 `private` 加零 TTL，并在 host 层施加 no-store 策略。

## 订阅使用客户端开启的响应流

现代订阅模式取代了以前的 `resources/subscribe` RPC 与旧的 HTTP GET 事件端点。

客户端把 `subscriptions/listen` 作为普通 JSON-RPC 请求发送。在 Streamable HTTP 上，这是一个响应保持打开为 SSE 流的 POST。`notifications` 对象是一份允许列表。server 不得投递未被请求的通知类型。

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "subscriptions/listen",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      }
    },
    "notifications": {
      "resourcesListChanged": true,
      "promptsListChanged": true,
      "resourceSubscriptions": [
        "notes://note-1"
      ]
    }
  }
}
```

请求 ID 就是 subscription ID。在任何被请求的事件之前，server 会发送 `notifications/subscriptions/acknowledged`。它的过滤器只包含 server 所接受的子集。

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/subscriptions/acknowledged",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": 17
    },
    "notifications": {
      "resourcesListChanged": true,
      "resourceSubscriptions": [
        "notes://note-1"
      ]
    }
  }
}
```

该流上此后的每个事件都携带同样的元数据。

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": 17
    },
    "uri": "notes://note-1"
  }
}
```

该通知表示资源发生了变化。客户端会在当前授权约束下通过 `resources/read` 再次读取它。它不会假设该事件包含新文档。

多个订阅可以共享一条 stdio 通道。subscription ID 让客户端能够对它们进行解复用。在 HTTP 上，关闭响应流即取消订阅。正常结束该流的 server 会返回一个与原始请求关联的最终 `resultType: "complete"` 响应。

不要把订阅流当作协议会话。后续的读取仍然是一个完整请求，可以到达任意健康的 server 实例。

```figure
t3-primitive-sort
```

## 交互实验

使用这张图，对一个项目追踪器中的五项能力进行分类：issue 详情、创建 issue、sprint 评审模板、项目策略，以及关闭 issue。然后判断哪些列表可以公开缓存、哪些读取必须保持私有，以及哪些资源值得发送更新通知。

对每个分类，指出选择者。如果由模型执行动作，就用 tool。如果 host 读取 URI 寻址的内容，就用 resource。如果用户启动一个预先准备好的消息工作流，就用 prompt。

## 练习实验

从仓库根目录运行模拟器：

```bash
cd phases/13-tools-and-protocols/10-mcp-resources-and-prompts/code
python3 main.py
python3 -m unittest discover tests -v
```

按以下顺序检查 transcript：

1. 确认 `server/discover` 通告了当前修订版与两类 capabilities。
2. 确认两个列表结果都已排序，并使用了 `resultType: "complete"`。
3. 确认列表与读取结果都带有刻意设置的缓存提示。
4. 把读取 URI 改为 `notes://missing`，观察 `-32602`。
5. 确认订阅确认消息先于资源事件出现。
6. 确认事件与正常关闭都携带 subscription ID `5`。

这个 Python 模型不会打开真实的 HTTP 连接。它表示的是 SDK 必须放到请求作用域响应流上的那些消息。在生产环境中，使用官方 SDK 处理分帧与传输。

## 交付工件

`outputs/skill-primitive-splitter.md` 是一份可复用的 MCP 原语选择设计评审。它现在会检查确定性发现、缓存范围、非法 URI 行为以及现代订阅过滤器。

本课还交付 `assets/primitive-split.svg`，它是原语与订阅边界的静态版本，供离线学习使用。

## 验证

```bash
cd phases/13-tools-and-protocols/10-mcp-resources-and-prompts/code
python3 main.py
python3 -m unittest discover tests -v
```

预期结果：主程序打印出一份 JSON transcript，测试命令报告至少十二个通过的测试。

## Capstone 衔接

当你的 capstone server 在动作旁边暴露可寻址的知识时，使用这套契约。包含一份确定性的目录快照、一次已授权的资源读取、一次 prompt 解析、一个非法 URI 用例，以及一份订阅 transcript。

你的证据应表明：没有任何列表依赖连接历史，并且订阅事件绝不会授予对底层资源的访问权限。

## Exercises

1. 添加一个 `notes://projects/{project}/notes/{id}` 资源模板，并校验两个变量。
2. 为 `resources/list` 添加分页，同时保持确定性顺序。
3. 把某个资源改为 `cacheScope: "private"` 且 `ttlMs: 0`，添加 host 层 no-store 策略，并解释为这两个控制项提供依据的威胁。
4. 添加一个 prompt 列表变更订阅，并证明当过滤器省略 `promptsListChanged` 时不会发送任何事件。
5. 创建两个同时存在的订阅，并证明每个事件都携带正确的请求 ID。
6. 为读取 handler 添加授权主体，并证明某个缓存条目不能跨主体使用。

## Key Terms

- **Resource：** 由 MCP server 暴露的 URI 寻址内容。
- **Prompt：** 由 MCP server 暴露的用户可控消息模板。
- **确定性列表：** 对于相同请求输入，成员与顺序都稳定的发现结果。
- **`ttlMs`：** 以毫秒为单位的缓存新鲜度时长。
- **`cacheScope`：** 缓存结果的共享边界。
- **`subscriptions/listen`：** 一条长时间存活的请求，其响应流投递经过显式过滤的通知。
- **Subscription ID：** 原始的 listen 请求 ID，在通知元数据中重复出现。
- **Invalid parameters：** JSON-RPC 错误 `-32602`，用于非法或未知的资源 URI。
- **Unsupported protocol version：** JSON-RPC 错误 `-32022`，包含 `supported` 与 `requested` 修订版本。
- **`server/discover`：** 强制性的 server 方法，返回受支持的修订版本、capabilities、身份以及可选的缓存提示。

## Further Reading

- [MCP 2026-07-28 Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [MCP 2026-07-28 Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MCP 2026-07-28 订阅](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [MCP 2026-07-28 缓存](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching)
