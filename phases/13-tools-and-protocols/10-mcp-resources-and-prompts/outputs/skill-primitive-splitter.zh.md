---
name: primitive-splitter
description: 依据 2026-07-28 契约评审 MCP server 设计，并区分 tools、resources、prompts、缓存与订阅。
version: 2.0.0
phase: 13
lesson: 10
tags: [mcp, resources, prompts, subscriptions, caching]
---

从消费者的视角评审一个拟议的 MCP server。

产出：

1. 一个 `server/discover` 结果，通告修订版 `2026-07-28` 以及确切的 resource 与 prompt capabilities。
2. 一张包含 `name`、`chooser`、`primitive` 与 `reason` 的表格。
3. 稳定的资源 URI scheme，以及任何有边界的资源模板。
4. Prompt 的 name、description，以及必需或可选的 arguments。
5. 每个列表方法的确定性排序规则。
6. 针对每个可缓存结果的缓存策略，包含 `ttlMs` 与 `cacheScope`。
7. 一个 `subscriptions/listen` 过滤器，覆盖需要更新的资源或列表变更。
8. 一个返回 JSON-RPC `-32602` 的非法资源示例，外加一个返回 `-32022` 并带 `supported` 与 `requested` 的不受支持修订版本示例。

使用以下决策规则：

- 由模型选择的操作是 tool。
- Host 可读、URI 寻址的内容是 resource。
- 由用户选择的消息工作流是 prompt。
- 更新流由客户端通过 `subscriptions/listen` 打开。
- listen 请求 ID 会成为 `io.modelcontextprotocol/subscriptionId`。
- 确认消息必须先于该订阅上的所有事件。
- 通知绝不会为后续读取绕过授权。
- 即使客户端选择先调用另一个方法，`server/discover` 也是强制性的。

在以下情况下拒绝该设计：

- 列表因连接历史而不同。
- 私有结果被放入公开缓存。
- 资源 URI 未经解析、授权与边界检查就被接受。
- 设计使用了 `resources/subscribe`，或把订阅当作协议会话。
- 允许 prompt 覆盖可信的 host instructions。

返回一份一页式的契约评审。最后给出风险最高的原语、缓存或订阅错误，以及最小的修正措施。
