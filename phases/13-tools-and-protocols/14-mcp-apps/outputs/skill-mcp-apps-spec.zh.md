---
name: mcp-apps-spec
description: 在无状态的 2026-07-28 协议上设计与审查一份 MCP App 契约。
version: 2.0.0
phase: 13
lesson: 14
tags: [mcp, apps, stateless, ui-resources, csp, sandbox]
---

给定一个可能需要交互式视图的 MCP 工具，产出一份与框架无关的契约。

## 所需输入

- 工具名称、参数、普通文本结果和结构化结果。
- 视图必须支持的用户交互。
- 数据敏感度，以及响应是否随授权上下文变化。
- 视图所需的浏览器权限和外部 origin。
- 为不支持 Apps 的宿主准备的纯文本行为。

## 产出

1. 当前核心信封。给出 `2026-07-28`、逐请求的 `protocolVersion`、`clientCapabilities`、建议的 `clientInfo`、相互匹配的 `Mcp-Method` 与 `Mcp-Name` 头，以及 `resultType` 响应。
2. Discovery 条目。在 `server/discover` 中宣告 `io.modelcontextprotocol/ui`，并给出保守的 `ttlMs` 和 `cacheScope`。
3. 工具声明。在 `tools/list` 返回的工具上放置嵌套的 `_meta.ui.resourceUri`。不要等到 `tools/call` 才揭示 UI。
4. 资源契约。在 `resources/read` 之前给出确定性的 `resources/list` 元数据。提供一个规范的 `ui://` URI、稳定的 name 与 description、`text/html;profile=mcp-app`、缓存提示、CSP 域名列表（`connectDomains`、`resourceDomains`、`frameDomains`、`baseUriDomains`），以及最小的 permissions 对象。
5. 结果契约。无论宿主是否渲染 App，都返回有用的文本与结构化数据。
6. 桥接契约。列出每一个 Apps `ui/*` 或代理方法、精确的消息 origin、参数 schema、结果 schema 和宿主侧的同意检查。
7. 回退。描述当 client 省略 Apps 扩展能力时的工具与结果。
8. 验证表。覆盖路由前的 HTTP 400 `-32020` 头部不一致、HTTP 400 `-32022` 与精确的 supported 和 requested 版本数据、HTTP 400 `-32021` 与 `data.requiredCapabilities`、HTTP 404 `-32601`、202 空 body notification、CSP 违规、不可信内容、未授权的桥接调用和文本回退。
9. 传输边界。如果实现接收的是已解析的请求与头部，把它标注为进程内协议模型，并接到第 09 课完整的 Streamable HTTP 适配器上。真实适配器必须要求 JSON Content-Type，以及同时包含 JSON 与 SSE 的 Accept 值。

## 硬性拒绝

- 把核心的 `initialize`、`notifications/initialized` 或 `Mcp-Session-Id` 路径当作当前 MCP。
- 通配的 `postMessage` 目标 origin，或跳过 `event.origin` 校验的接收方。
- 只在工具运行之后才揭示的 UI 绑定。
- 通配的 CSP 域名列表、无界的网络 origin，或没有可见功能支撑的权限。
- 在未定义消毒边界的情况下插入用户可控的 HTML。
- 把 iframe 点击当作宿主授权的有后果 UI 动作。
- 宣告了 resources 却省略 `resources/list` 的 server。
- 为没有 `id` 的 notification 返回任何 JSON-RPC 响应 body。

## 兼容边界

旧的扁平 UI 元数据可以作为回退读取，但新输出使用嵌套的 `_meta.ui.resourceUri`。只有当被明确标识为 Apps 的 postMessage 握手时，才允许 `ui/initialize`。它绝不能替代已被移除的 MCP 核心初始化。

## 输出格式

返回一份紧凑的设计，使用以下标题：Core Wire、Discovery、Tool、Resource、Result、Bridge、Security、Fallback、Verification。最后给出单个风险最高的 origin、权限或同意假设。
