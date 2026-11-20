---
name: task-store-designer
description: 用以当前 Tasks 扩展、无状态请求、显式所有权、轮询、输入更新和取消来设计持久的 MCP 工作。
version: 2.0.0
phase: 13
lesson: 13
tags: [mcp, tasks, extension, durable-state, stateless]
---

针对 `io.modelcontextprotocol/tasks` 扩展设计长时间运行的 MCP 工作。

产出：

1. 资格决策。说明该操作为何需要任务，而不是同步的 `tools/call`。
2. 能力契约。在 `server/discover` 中给出精确的 `supportedVersions`、capabilities、`ttlMs` 和 `cacheScope`，并在逐请求的客户端能力中给出 Tasks 扩展。如果宣告了 tools，就要包含强制的确定性 `tools/list` 描述符，带合法的对象 `inputSchema`、server 身份元数据和缓存提示。扩展缺失时用 `-32021` 并给出 `requiredCapabilities` 对象；版本不受支持时用 `-32022` 并给出精确的 `supported` 和 `requested` 数据。
3. 创建事务。持久化任务，直到 `tasks/get` 能够解析它，然后返回由 server 指定的 `resultType: "task"`。
4. 状态形状。包含 `taskId`、`status`、`statusMessage`、ISO 时间戳、`ttlMs`、`pollIntervalMs`、权威所有者、原始操作引用、结果或错误、未满足的输入请求，以及所有已发出的输入键。已完成任务内嵌的 `CallToolResult` 必须带 `resultType: "complete"`，且 SHOULD 包含自己的 `io.modelcontextprotocol/serverInfo` 元数据。
5. 当前方法。定义 `tasks/get`、`tasks/update` 和 `tasks/cancel`。对于 Streamable HTTP，每个请求都让 `Mcp-Name` 等于 `params.taskId`。不要引入 `tasks/status`、`tasks/result` 或 `tasks/list`。
6. 输入延续。把创建前的 MRTR 与创建后的 `tasks/get` 加 `tasks/update` 分开。要求输入键在生命周期内唯一，并处理部分响应。
7. 持久性方案。选择原子文件系统存储、事务型数据库，或共享队列加存储。包含 worker 租约与重启行为。
8. 所有权策略。每个任务方法及订阅都按租户和 principal 授权。绝不要把知道任务 id 当作权限。
9. 取消契约。写明确认是协作式的，可能不会导致 `cancelled`。
10. Notification 选项。在 POST 响应 SSE 流上使用 `subscriptions/listen` 和 `notifications/tasks`，并以轮询为基线。把 `io.modelcontextprotocol/subscriptionId`（等于 listen 请求 id）放进确认和每一条任务 notification。没有 id 的 notification 不收到 JSON-RPC 响应；被接受的 HTTP notification 收到不带 body 的 `202`。
11. 过期策略。从创建起解释 `ttlMs`，定义清除行为，并避免泄漏另一个租户的任务是否存在。
12. 迁移映射。把由 client 请求的任务标志和被移除的实验性方法替换为当前的扩展流程。

硬性拒绝：

- 在持久读可见性达成前返回任务句柄。
- 对未宣告该扩展的请求返回 `resultType: "task"`。
- 把 `params._meta.task.required`、`tasks/status`、`tasks/result` 或 `tasks/list` 当作当前 API。
- 用 `initialize`、`Mcp-Session-Id`、粘性路由或隐藏的传输会话状态作为任务存储。
- 把 `tasks/cancel` 的确认当作 worker 已停止的证据。
- 在一个任务生命周期内复用 `inputRequests` 键。
- 把任务返回给并非其权威所有者的调用方。
- 通过独立的 GET、会话 SSE 或 `Last-Event-ID` 重放来实现 notification 投递。

拒绝规则：

- 对于快速的确定性查询，拒绝创建任务，除非调用方给出具体的持久性需求。
- 当工作必须跨越进程重启存活时，拒绝仅内存的生产存储。
- 拒绝无界的结果载荷；把大型工件存到外部，并返回已授权的资源句柄。
- 拒绝没有显式租户所有权、过滤、分页和保留策略的历史端点。

输出一份单页设计，包含生命周期表、wire 方法、持久化事务、所有权规则、输入流程、轮询节奏、取消语义、订阅选项、过期清理、失败模型和旧版迁移映射。
