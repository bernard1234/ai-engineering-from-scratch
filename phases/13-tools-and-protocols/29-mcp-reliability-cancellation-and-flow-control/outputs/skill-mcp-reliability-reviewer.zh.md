---
name: mcp-reliability-reviewer
description: 审查 MCP cancellation 竞态、截止时间、重试、幂等性、SSE 流控与重连行为。
version: 1.0.0
phase: 13
lesson: 29
tags: [mcp, reliability, cancellation, idempotency, sse, backpressure]
---

从请求开始直到故障恢复，审查一个 MCP 操作。

如果以下输入缺失，请主动索取：

1. 传输方式：stdio 或 Streamable HTTP。
2. 操作语义与副作用。
3. Idle timeout 与绝对 maximum timeout。
4. progress-token 行为与速率限制。
5. 重试策略与业务幂等存储。
6. SSE 缓冲区、代理、keepalive 与重连设置。
7. 如果该操作使用 Tasks 扩展，则需说明持久 Task 行为。

产出以下各节。

## 取消的 wire 信号

- 对于 stdio，要求客户端发送的 `notifications/cancelled` 通知引用一个活跃的请求 id。
- 对于 Streamable HTTP，要求关闭该请求的响应流。拒绝普通的 cancellation POST。
- 要求不对 cancellation 通知发送任何 JSON-RPC 响应。
- 把服务端发送的 `notifications/cancelled` 仅保留给 stdio `subscriptions/listen` 的拆除。
- 说明当 cancellation 未知、格式错误、迟到或无法执行时会发生什么。

## 竞态表

为以下情况给出确定性结果：

| 事件顺序 | 服务端终态 | 最终响应 | 客户端行为 |
|------------|-----------------------|----------------|-----------------|
| 先取消后完成 | 已取消 | 已抑制 | 继续恢复流程 |
| 先完成后取消 | 已完成 | 已保留 | 忽略迟到的 cancellation |
| 超时后收到迟到响应 | 取决于传输的 cancellation | 按观察到的顺序忽略或抑制 | 在不安全重试之前先对账 |
| progress 期间断开 | 在途请求已取消 | 无可恢复的流 | 重连并重新拉取 |

## 截止时间策略

要求同时具备 idle timeout 和绝对 maximum timeout。只有当 progress 有效、单调且受限速时才可重置 idle 时间。keepalive 注释不算作语义 progress。maximum timeout 永不重置。

## 重试分类

为每个操作返回一个类别：

- `SAFE`：应用契约证明没有副作用。
- `CONDITIONAL`：变更拥有一个持久的 idempotency key，并以相同参数复用。
- `UNSAFE`：变更缺少权威去重。

永远不要把新的 JSON-RPC id、工具注解或传输重连当作业务幂等。

对于条件式重试，要求存储参数指纹与已提交结果。拒绝同一个 key 被复用于不同参数。

要求 key 占用、参数指纹、业务副作用记录和已提交结果共用同一个原子的、持久的账本边界。进程内字典或锁不是持久的，也无法协调多个副本。可以接受共享数据库事务、transactional outbox，或一个同样强制该 key 的上游服务商。要说明哪个副作用真正位于该边界之内。

返回已提交结果的防御性副本。永远不要暴露账本持有的可变对象。用并发同 key 夹具、重开夹具和变更别名夹具来证明这两点。

## 流控

- 设置明确的按流或按客户端容量。
- 合并可替换的 progress。
- 把被丢弃的 progress 标记为需要权威重新拉取。
- 保留最终的 JSON-RPC 响应。
- 为 SSE 设置 `Content-Type: text/event-stream`、`Cache-Control: no-cache` 和 `X-Accel-Buffering: no`。
- 把 keepalive 节奏与操作 progress 分开定义。
- 拒绝无界队列。

## 重连计划

- 用一个新 id 打开新请求。
- 恢复订阅过滤器。
- 对 MCP 2026-07-28 不要使用 `Last-Event-ID`。
- 重新拉取受影响的 resources、lists、prompts 或 Tasks。
- 不要自动重放不安全变更。
- 使用带 jitter 且设上限的指数退避。

## 持久 Tasks

当存在 Task 时，要把 `tasks/cancel` 与请求 cancellation 分开。完整的确认只能证明取消意图被接受。轮询或监听，直到持久任务进入终态。

## 必需夹具

至少返回以下可执行场景：

1. stdio 在完成前取消；
2. stdio 在迟到取消之前完成；
3. HTTP 在完成前关闭流；
4. progress 重置 idle timeout，但 maximum timeout 仍然触发；
5. 用两个 JSON-RPC id 且无 idempotency key 的重复变更；
6. 用一个 key 与相同参数的重复变更；
7. 用不同参数复用同一个 key；
8. 慢消费者超出 progress 缓冲区；
9. 流中断之后新建订阅并权威重新拉取；
10. `tasks/cancel` 确认之后 worker 延迟取消。
11. 两个独立的账本连接在同一个 key 与相同参数上竞争；
12. 调用方修改返回结果，随后从持久记录进行干净重放。

当重试策略只被描述为“超时后重试”、账本是进程内的、外部副作用位于所声称的原子边界之外且没有 outbox 或上游 key、返回记录别名指向可变存储，或者队列容量未指明时，拒绝给出生产就绪的结论。
