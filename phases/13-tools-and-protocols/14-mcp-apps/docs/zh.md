# 无状态协议上的 MCP Apps

> 交互式结果仍然是一次 MCP 工具与资源的交换。2026-07-28 的核心让这次交换自成一体，而 Apps 扩展在此之上增加了沙箱化的浏览器界面。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 07 课（MCP server）、第 13 阶段，第 10 课（resources）
**Time:** ~75 分钟

## Learning Objectives

- 通过 `server/discover` 与逐请求的扩展能力宣告 MCP Apps。
- 在工具被调用之前，就在工具定义上声明一个 `ui://` 资源。
- 在 2026-07-28 的无状态 wire 上返回完整的工具与资源结果。
- 把 Apps 的 `ui/initialize` 桥接消息与已被移除的 MCP 核心握手区分开。
- 落实 origin 校验、沙箱、CSP 与最小权限。

## 问题场景

一段文本结果可以描述一条时间线。它无法给用户一条可筛选、可查看、可操作的时间线。

MCP Apps 用一个可选扩展解决呈现问题。工具定义指向一个 `ui://` 资源。宿主可以在工具运行之前抓取并审查该资源，在沙箱化的 iframe 中渲染它，并通过 JSON-RPC 桥接中介应用的所有动作。

核心协议在 2026-07-28 发生了变化。不要用旧的连接生命周期包裹 App：

- 没有核心 `initialize` 请求或 `notifications/initialized` notification。
- 没有 `Mcp-Session-Id` 头。
- 每个请求都在 `params._meta` 中携带协议版本与客户端能力。
- server 实现 `server/discover`，使 client 能检查版本、核心能力和扩展。
- 每个成功结果都有一个 `resultType` 判别字段。
- Streamable HTTP 每个请求用一个 POST。现代 GET 与 DELETE 入口返回 405。

Apps 桥接仍有一个名为 `ui/initialize` 的方法。它属于 iframe 的 postMessage 方言。它不会重建核心 MCP 会话。

## 核心概念

### 两个协议，一个特性

把各层显式分开：

1. MCP 核心承载 `server/discover`、`tools/list`、`tools/call`、`resources/list` 和 `resources/read`。
2. MCP Apps 扩展声明 UI，并定义 iframe 到宿主的桥接。
3. 浏览器沙箱规则限制 UI 能触及的范围。

扩展标识符是 `io.modelcontextprotocol/ui`。双方都要选择加入。client 在每次请求的 capabilities 对象内发送扩展支持：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "server/discover",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/ui": {}
        }
      },
      "io.modelcontextprotocol/clientInfo": {
        "name": "timeline-host",
        "version": "1.0.0"
      }
    }
  }
}
```

建议包含 `clientInfo` 以用于诊断。它是自报的数据，不是授权身份。

### 渲染之前先 discover

server 的 discovery 结果宣告该扩展：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {},
    "resources": {},
    "extensions": {
      "io.modelcontextprotocol/ui": {}
    }
  },
  "ttlMs": 300000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "timeline-app-server",
      "version": "2.0.0"
    }
  }
}
```

server 必须支持 discovery。client 不必在每个动作前都调用 discovery，因为每个动作都自带能力。

### 在工具定义上声明 UI

现代 Apps 契约在 `tools/list` 中把 UI 绑定到工具：

```json
{
  "name": "notes_timeline",
  "description": "Render a timeline of notes.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  },
  "_meta": {
    "ui": {
      "resourceUri": "ui://notes/timeline.html"
    }
  }
}
```

这是刻意设计的调用前元数据。宿主可以在某个结果要求显示之前，预加载、缓存并安全审查这段 HTML。较旧的扁平元数据键可能被兼容代码接受，但新的 server 应发出嵌套的 `_meta.ui.resourceUri` 形式。

`tools/list` 在当前核心中是可缓存的。要包含确定性排序、`ttlMs` 和 `cacheScope`。当可见工具因用户或 token 而异时，使用 `private`。

### 返回数据，再让宿主绑定视图

工具调用返回普通内容加上结构化数据：

```json
{
  "resultType": "complete",
  "content": [
    {"type": "text", "text": "Timeline ready."}
  ],
  "structuredContent": {
    "notes": [
      {"id": "note-1", "title": "Discover", "created": "2026-07-28"}
    ]
  },
  "isError": false
}
```

宿主已经知道哪个视图属于该工具。不要为了重复 URI 而发明新的内容块。

### 把应用作为资源提供

server 在 discovery 中宣告 `resources`，因此它还要实现强制的 `resources/list` 操作。其确定性的列表条目包含规范 URI、稳定的 name、description 和 MIME 类型。列表结果包含 `resultType`、server 身份元数据、`ttlMs` 和 `cacheScope`，与确定性工具列表一样。

宿主发送 `resources/read`。在 Streamable HTTP 上，请求携带：

```text
POST /mcp
MCP-Protocol-Version: 2026-07-28
Mcp-Method: resources/read
Mcp-Name: ui://notes/timeline.html
```

头部值与 JSON-RPC body 必须一致。不一致属于协议错误 `-32020`。

结果包含 HTML 资源和缓存提示：

```json
{
  "resultType": "complete",
  "contents": [
    {
      "uri": "ui://notes/timeline.html",
      "mimeType": "text/html;profile=mcp-app",
      "text": "<!doctype html>...",
      "_meta": {
        "ui": {
          "csp": {
            "connectDomains": [],
            "resourceDomains": [],
            "frameDomains": [],
            "baseUriDomains": []
          },
          "permissions": {}
        }
      }
    }
  ],
  "ttlMs": 60000,
  "cacheScope": "public"
}
```

### 把 UI 资源当作可执行内容来缓存

App 资源不能与普通文本互换。它的缓存条目可以执行桥接代码、渲染工具数据、请求由宿主中介的动作。以规范的 `ui://` URI、准入的 server 身份与版本、资源内容摘要，以及（当 `cacheScope` 为 private 时）授权上下文作为键。绝不要跨 principal 复用私有 App 资源，因为即使 URI 相同，HTML 或其策略元数据也可能不同。

当 `ttlMs` 过期、工具的 `_meta.ui.resourceUri` 绑定变化、server 版本或准入描述符固定项变化、或某个已确认的资源变更订阅点名该 URI 时，作废该条目。在重新挂载之前重新抓取并重新施加 CSP 与权限审查。陈旧的 iframe 不能仅仅因为新资源版本尚未加载就保留更宽的权限。

### 在特性策略之前拒绝 wire 歧义

校验有刻意的顺序。首先校验 JSON-RPC 形状，要求字符串形式的协议元数据和一个对象型的客户端能力映射。接着比较路由头与 body。之后才判断匹配到的协议版本是否受支持。这个顺序防止代理与 server 对同一批请求做出不同解释。

| 条件 | HTTP | JSON-RPC 错误 |
|-----------|------|----------------|
| 头部与 body 的版本、方法或名称不一致 | 400 | `-32020` |
| 头部与 body 一致，但版本不受支持 | 400 | `-32022`，`data` 精确为 `{"supported":["2026-07-28"],"requested":"<actual>"}` |
| `resources/read` 缺少 Apps 扩展能力 | 400 | `-32021`，带 `data.requiredCapabilities.extensions.io.modelcontextprotocol/ui` |
| 方法未知 | 404 | `-32601` |

JSON-RPC notification 没有 `id`，因此 server 从不为它发出 JSON-RPC 响应。被接受的 HTTP notification 返回 202 和空 body。错误可以改变 HTTP 状态，但仍不能为 notification 构造出 JSON-RPC 错误 body。

### 沙箱是边界，不是信任裁决

宿主掌控 iframe。App 无法直接读取宿主的 cookie、本地存储或页面 DOM。所有特权工作都必须穿过桥接。

使用以下默认值：

- 所有 CSP 域名列表保持为空，然后只添加 App 需要的 origin。用 `connectDomains` 处理 fetch、XHR 和 WebSocket；用 `resourceDomains` 处理脚本、样式、图片和字体。
- 条件允许时打包代码与数据。
- 除非某个可见功能需要，否则不请求摄像头、麦克风或位置权限。
- 把 `postMessage` 固定到精确的对端 origin，拒绝来自其他任何 origin 的事件。
- 把工具参数、工具结果、资源文本和桥接消息都视为不可信输入。
- 把用户同意保留在宿主中。iframe 不能自行批准它有后果的动作。

不要把教程里固定的 `sandbox` 属性照抄进每个宿主。宿主必须根据 App 的 origin 模型和自身的隔离设计来选择标志。

被允许的域名仍然是一条外泄路径。`connectDomains: ["https://api.example.com"]` 意味着在 App 内执行的任何脚本都能把被允许的数据发到那里。精确的 origin 匹配可防止目标混淆，但它不判断载荷是否合适。默认把 connect 访问保持为空，避免把 bearer token 放进 iframe，条件允许时通过宿主代理窄范围操作，限制响应与请求大小，并审计每个出站请求是由哪次用户操作触发的。把 `resourceDomains` 与 `connectDomains` 分开对待；加载字体或脚本的权限不应授予任意数据上传的能力。

### Apps 桥接有自己的生命周期

Apps 桥接是运行在 `postMessage` 之上的 JSON-RPC 方言。它可以交换 `ui/initialize` 与 `ui/*` notification，也能代理诸如 `tools/call` 这类看起来像核心的方法。

View 发送 `ui/initialize`，带上 `appInfo` 和一个 `appCapabilities` 对象。宿主返回自己的能力与宿主上下文。只有在该响应之后，View 才发送 `ui/notifications/initialized`。宿主必须等到这条 Apps notification 之后，才向 View 发送消息。

这个本地握手在一个 iframe 与一个宿主 frame 之间建立桥接。它不协商 MCP 协议版本，不创建 server 状态，也不铸造传输会话。注意精确的前缀：核心的 `notifications/initialized` 已被移除，而 Apps 的 `ui/notifications/initialized` 保留下来。由桥接工具调用生成的核心请求，是一个新的、自带完整请求元数据和新 JSON-RPC id 的自洽请求。

### 宿主上下文、动作与撤销

桥接初始化之后，宿主仍然是权威。View 只能通过宿主宣告的能力来请求工具动作、导航、剪贴板使用或其他特权效果。宿主校验分型请求、当前用户、目标和参数，套用审批策略，并可以拒绝。按钮点击和合法的桥接消息只是表达意图；两者都不授予权限。

把主题、尺寸和无障碍视为持续变化的宿主上下文，而不是一次性的渲染输入：

- 应用宿主提供的颜色与排版 token，并在主题或对比度偏好变化时做出反应。
- 允许 View 上报期望尺寸，但由宿主限制并施加 iframe 大小，使内容无法溢出其布局或制造欺骗性的浮层。
- 在 iframe 内保持键盘顺序、可见焦点、无障碍名称、屏幕阅读器状态、足够对比度、缩放和减少动效行为。
- 在尺寸变化和重新渲染之后，重新测试宿主控件与 View 控件之间的焦点转移。

能力可以在 App 打开期间被撤销，因为用户切换了账号、策略变了、某个 server 被隔离，或宿主收窄了同意范围。在动作发生时检查能力与授权，而不只在 `ui/initialize` 时检查。发生撤销时，拒绝待处理的特权调用，停止不再符合策略的网络活动，清除敏感的已渲染状态，并在 UI 资源本身不再被准入时重新挂载或回退到文本。View 必须把拒绝当作正常结果，而不是一直重试直到宿主让步。

### 回退是契约的一部分

感知 Apps 的 server 仍可以服务不宣告 UI 扩展的宿主：

- 在 `tools/list` 中返回同一个工具，但不带 `_meta.ui`。
- 为 `tools/call` 保留可用的文本结果。
- 对 UI 的 `resources/read` 以缺少能力的错误拒绝。
- 在判断工具是否完成时，绝不假设存在 iframe。

```figure
t3-ui-sandbox
```

## Build It

`code/main.py` 在没有 SDK 的情况下构建了一个小的进程内协议模型。它校验当前的请求信封与 Streamable HTTP 路由值，通过 `server/discover` 宣告 Apps，列出工具与资源，执行工具，并提供一个自包含的 HTML 资源。

该模型接收已解析的 body 与路由头。它不是完整的 HTTP 适配器，也不解析 `Content-Type` 或 `Accept`。完整的 Streamable HTTP 适配器见第 09 课，它要求 `Content-Type: application/json` 以及同时包含 `application/json` 和 `text/event-stream` 的 `Accept` 值。

运行它：

```bash
cd phases/13-tools-and-protocols/14-mcp-apps
python3 code/main.py
python3 -m unittest discover code/tests -v
```

在输出中检查四件事：

1. 每次调用都是独立的。
2. 每个请求都有 `_meta` 能力。
3. `resources/list` 在任何资源读取之前返回稳定的描述符。
4. 每个结果都有 `resultType` 和 server 身份元数据。
5. 不出现任何核心会话标识符。

## Use It

从 `server/discover` 开始。确认 `io.modelcontextprotocol/ui` 出现在 server 的扩展映射中。然后调用两次 `tools/list`，一次带 Apps 能力，一次不带。第一个响应声明该资源。第二个仍然是可用的纯文本工具。

读取 `ui://notes/timeline.html`。在 HTML 中搜索 `hostOrigin` 和 `event.origin` 守卫。这两行是最低限度的可见证据，证明桥接没有使用通配目标。

## Ship It

本课交付 `outputs/skill-mcp-apps-spec.md`。在编写框架代码之前，用它审查一份 App 契约。它迫使作者写明当前核心信封、扩展协商、回退、UI 资源、缓存策略、CSP、权限、桥接方法和同意边界。

## Exercises

1. 把客户端能力改成空的扩展映射。确认 `tools/list` 保留该工具但移除 UI 绑定。
2. 发送 `Mcp-Name: ui://notes/other.html`，而 body 却读取时间线。确认返回错误 `-32020`。
3. 把资源改为 `cacheScope: private`。描述是哪种用户特定的条件使其合理。
4. 把脚本移到 `https://static.example.com/app.js`。把该 origin 加入 `resourceDomains`，并解释新的供应链风险。
5. 增加一个 `notes_open` 工具，并把按钮点击通过宿主路由。让用户审批保留在宿主中。

## Key Terms

| 术语 | 含义 |
|------|---------|
| MCP Apps | 由 MCP 宿主渲染交互式 HTML 的可选扩展 |
| `io.modelcontextprotocol/ui` | 由双方宣告的扩展标识符 |
| `ui://` | App 的 UI 模板所使用的资源 scheme |
| `text/html;profile=mcp-app` | MCP App HTML 的 MIME 类型 |
| `server/discover` | 用于协议与能力发现的当前 RPC |
| `resources/list` | 当 server 宣告 resources 时必须实现的资源列表方法 |
| `resultType` | 现代成功结果必需的判别字段 |
| `ui/initialize` | 第一个 Apps 桥接请求，与已被移除的核心初始化相互独立 |
| `ui/notifications/initialized` | 宿主响应之后由 Apps View 发送的就绪 notification |
| CSP | 限制脚本、样式、图片与网络 origin 的浏览器策略 |
| Text fallback | 为不支持 Apps 的宿主保留的工具行为 |

## Further Reading

- [MCP 2026-07-28 基础协议](https://modelcontextprotocol.io/specification/2026-07-28/basic)
- [MCP Apps 概览](https://modelcontextprotocol.io/extensions/apps/overview)
- [MCP Apps 构建指南](https://modelcontextprotocol.io/extensions/apps/build)
- [官方扩展支持矩阵](https://modelcontextprotocol.io/extensions/client-matrix)
