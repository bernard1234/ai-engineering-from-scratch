# MCP 可靠性、取消与流量控制

> 一个 request ID 只能关联一条消息。它既不能让副作用变得安全，也停不下 worker，更保护不了一条流免受慢消费者拖累。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 13 阶段，第 09 课和第 13 课
**Time:** ~120 分钟

## Learning Objectives

- 为 stdio 和 Streamable HTTP 实现正确的 cancellation 信号。
- 在取消之后不再发送任何消息的前提下，解决完成与取消之间的竞态。
- 将请求 cancellation 与持久的 `tasks/cancel` 语义区分开。
- 基于副作用和显式的 idempotency key 构建重试决策。
- 在保留最终响应的同时为 progress 队列设定上界。
- 通过重连、重新拉取和带 jitter 的退避来恢复流。

## 问题场景

正常路径会掩盖分布式系统中最昂贵的缺陷。

客户端调用一个工具。服务端开始工作。progress 陆续到达。一个代理缓冲了这条流。客户端到达超时并断开连接。服务端在一毫秒之后完成。客户端用一个全新的 JSON-RPC id 重试。变更被执行了两次。

每个组件在本地都表现正常。系统在全局层面却失败了。

MCP 定义了消息与传输行为，但你的应用仍然要负责：

- 时间预算；
- 业务幂等性；
- 有界队列；
- 重试分类；
- 持久任务状态；
- 重连与重新拉取策略。

本课把这些决策构建进一个确定性模拟器。这里没有 sleep、socket，也没有随机故障。你直接控制 cancellation 事件的顺序。一个同步线程测试会强制两个账本客户端争抢同一个 idempotency key。

## 请求取消是传输相关的

在每种传输上意图都相同：客户端不再需要某个在途结果。但 wire 信号不同。

### stdio

stdio 使用一条共享的双向通道。客户端发送一条通知：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/cancelled",
  "params": {
    "requestId": 41,
    "reason": "User closed the operation"
  }
}
```

这条通知是 fire-and-forget 的。服务端不会对它发出任何 JSON-RPC 响应。

服务端应当停止工作、释放资源，并且避免为被取消的请求发送响应。当请求未知、已经完成或无法安全停止时，它可以忽略 cancellation。

格式错误、未知以及已经完成的 cancellation 通知一律被忽略。把这些竞态转成新的错误只会制造更多竞态。

### Streamable HTTP

现代 Streamable HTTP 为每个请求提供独立的 HTTP 响应流或 SSE 响应流。客户端通过关闭该请求的响应流来取消。

对于普通的 HTTP 请求，不要 POST `notifications/cancelled`。流的关闭本身就是 cancellation 信号。

一旦服务端观察到断开，它应当停止工作，并且不得再为该请求发送更多消息。

### 服务端发起的取消范围很窄

服务端不会用 `notifications/cancelled` 去取消任意的客户端调用。在 stdio 上，服务端发起的 cancellation 仅保留用于终止一个 `subscriptions/listen` 请求。请把这条路径与普通客户端请求的 cancellation 分开。

## 取消是一场竞态

两种事件顺序都是合法的。

### 取消胜出

```text
request starts
client sends cancellation signal
server marks request cancelled
worker reaches completion
server suppresses the response
```

### 完成胜出

```text
request starts
worker commits the result
server sends the response
cancellation arrives late
server ignores the late notification
```

对于自己已经放弃的请求，客户端同样必须忽略迟到的响应。网络延迟意味着任何一方都无法证明对方先观察到了哪个事件。

```figure
mcp-reliability-race
```

本课的 `RequestCoordinator` 只保存一个终态。cancellation 之后 `complete()` 不再返回响应。迟到的 cancellation 无法改变一条已完成的记录。

## 超时需要两个时钟

只有单个不活跃计时器是不够的。

使用两个限制：

1. **Idle timeout。** 请求允许在多长时间内没有产生任何有用的活动。
2. **Maximum timeout。** 从请求开始算起的绝对墙钟预算。

progress 可以重置 idle 时钟。它绝不能移除 maximum 截止时间。

```text
start: 0 ms
progress: 400 ms
progress: 800 ms
progress: 1200 ms
idle timeout: 500 ms
maximum timeout: 2000 ms
```

在 1500 ms 时，请求仍然活跃，因为最近一次 progress 只过去了 300 ms。而在 2000 ms 时，即使又有一个 progress 事件在 1999 ms 到达，maximum 截止时间也会取消它。

progress 是可选的。服务端可以接受一个 progress token 却一个更新都不发。永远不要因为 token 存在就把它当成无限超时。

MCP 的 progress 值必须递增。通知在完成或取消之后停止。要对 progress 限速，使快速工作的 worker 无法淹没传输层。

## 请求取消不是 `tasks/cancel`

这两套机制解决的是不同的生命周期。

| 机制 | 目标 | 信号 | 成功的含义 |
|-----------|--------|--------|--------------------|
| stdio 上的请求取消 | 一个在途 RPC | `notifications/cancelled` | 客户端放弃了该请求；服务端应在可行时停止 |
| HTTP 上的请求取消 | 一条在途响应流 | 关闭该流 | 客户端放弃了该请求；服务端应在可行时停止 |
| `tasks/cancel` | 一个持久 Task | 普通 MCP 请求 | 服务端确认了取消意图 |

一次成功的 `tasks/cancel` 结果并不能证明 worker 已经停止。任务可能仍处于 `working`，直到某个 worker checkpoint 观察到该标志。工作也可能在这个 checkpoint 之前就完成了。

不要因为 HTTP 连接关闭就抹掉持久任务状态。创建 Task 的理由正是它的生命周期要比一个请求和一条连接更长久。

## 新的 JSON-RPC ID 不是幂等性

JSON-RPC id 用于关联请求与响应。它们并不标识一个业务操作。

假设客户端提交了一笔 id 为 `41` 的扣款，丢失了响应，然后用 id `42` 重试。服务端看到的是两条不同的消息。如果没有应用层的 key，它无法知道这两条消息代表同一次结算。

idempotency key 标识的是业务意图：

```json
{
  "name": "charge_account",
  "arguments": {
    "account": "acct-7",
    "cents": 1200,
    "idempotencyKey": "checkout-7"
  }
}
```

服务端存储：

- 该 key；
- 操作参数的指纹；
- 已提交的结果。

相同的 key 与相同的参数会返回已存储的结果。相同的 key 搭配不同的参数会被拒绝。这可以防止意外的 key 复用去变更另一个业务操作。

### 账本边界必须是原子且持久的

下面这个顺序是不安全的：

```text
check key
run mutation
store result
```

两个 worker 可能都观察到 key 缺失，于是都执行了变更。在副作用之后、存储之前发生崩溃，也会在重试时造成同样的歧义。

本课使用一个基于文件的 SQLite 账本。`BEGIN IMMEDIATE` 把 key 检查、模拟的业务副作用、执行计数器和结果存储串行化进同一个事务。因此，两个独立的账本连接用同一个 key 竞争时，只会观察到一个已提交结果和一次执行。关闭并重新打开账本也会保留该记录。

每个返回值都从存储的 JSON 重建。调用方永远不会拿到账本持有的可变对象，因此修改返回的字典不会破坏后续的重放结果。

模拟器的业务副作用是同一个 SQLite 事务内的收据与执行计数器。真实的支付、部署或外部 API 调用，并不会仅仅因为写了一张本地表就变得原子。生产环境需要持久化的共享数据库事务、transactional outbox，或一个同样强制执行 idempotency key 的上游服务商。单靠进程锁既保护不了多个副本，也扛不住重启。

### 重试矩阵

在实现重试之前先对它们分类。

| 类别 | 示例 | 重试规则 |
|------|---------|------------|
| Safe | 无副作用的确定性读取 | 在理解了故障边界之后，用一个新 JSON-RPC id 重试 |
| Conditional | 带有持久 idempotency key 的变更 | 用同一个 key 和完全相同的参数重试 |
| Unsafe | 没有业务去重的变更 | 不要自动重试；先做对账 |

像 `readOnlyHint` 和 `idempotentHint` 这样的工具注解仍然只是不可信的提示。真正决定重试安全性的是应用契约与服务端实现。

## Backpressure 是正确性的一部分

SSE 生产者生成 progress 的速度，可能快于客户端、代理或网络的消费速度。无界队列会把“慢”转化为“内存耗尽”。

使用有界队列，并明确哪些内容可以被丢弃。

progress 是可替换的。对于同一个 token，较晚的 progress 值会取代较早的值。而最终的 JSON-RPC 响应不可替换。

本课的缓冲区采用如下策略：

1. 合并同一个 token 相邻的 progress。
2. 容量达到上限时丢弃最旧的 progress。
3. 把该流标记为需要权威重新拉取。
4. 保留最终响应。
5. 拒斥这样一种状态：保留最终响应必须以丢弃另一个最终响应为代价。

这是带有显式恢复的有界丢失。静默丢失不是一种策略。

### 代理缓冲

服务端可以正确地流式发送，而反向代理却把事件扣在缓冲区里。

对于 SSE 响应，要发送：

```http
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

2026 版 Streamable HTTP 规范建议使用 `X-Accel-Buffering: no`，这样兼容的代理会立即投递事件。

对于安静的长寿命流，要周期性地发出一个 SSE 注释：

```text
:
```

客户端会忽略注释行。中间层则能看到流量，因此更不容易关闭一条空闲连接。

keepalive 不是 progress。不要仅仅因为到达了一条传输层注释，就重置某个操作的语义 idle timeout。

## 重连意味着重新拉取

现代 Streamable HTTP 不支持通过 `Last-Event-ID` 恢复 SSE。

当 `subscriptions/listen` 流中断之后：

1. 用一个新 JSON-RPC id 打开一个新的 listen 请求。
2. 恢复期望的订阅过滤器。
3. 从权威方法重新拉取受影响的 tools、resources、prompts 或 Tasks。
4. 按稳定标识符对应用状态去重。
5. 不要仅仅因为某个不安全变更的响应丢失就重放它。

示例恢复计划显式地把 `sendLastEventId` 设为 false，并列出需要重新拉取的资源。

### 防止重连惊群

如果一万个客户端在同一秒重连，正在恢复的服务端会再次失败。

使用带 jitter 和上限的指数退避。本课从客户端 id 和尝试次数计算确定性的 jitter，使测试保持可复现：

```text
attempt 0: up to 250 ms
attempt 1: up to 500 ms
attempt 2: up to 1000 ms
...
cap: 8000 ms
```

生产环境可以使用密码学安全的随机数或运行时随机数。真正的不变量是分布，而不是某个具体公式。

## Build It

`code/main.py` 构建了五个小型可靠性组件。

### `RequestCoordinator`

- 以 idle 和 maximum 截止时间启动一个在途请求；
- 发出单调递增的 progress 通知；
- 产生正确的 stdio 或 HTTP cancellation 信号；
- 忽略无效的 cancellation 通知；
- 把取消与完成之间的终态竞态显式表达出来；
- 把服务端发起的 cancellation 限定为 stdio 订阅。

### `MutationLedger`

- 证明两个 JSON-RPC id 在没有业务 key 的情况下会执行两次；
- 对 key 检查、模拟副作用、执行计数器和结果提交使用一个基于文件的 SQLite 事务；
- 在相互独立的账本连接之间，按同一个 idempotency key 对相同参数去重；
- 拒绝一个被复用于不同参数的 key；
- 返回防御性副本，并在重新打开后保留已提交记录。

### `DurableTaskService`

- 确认一个取消请求；
- 让任务保持在 `working`，直到某个 worker checkpoint；
- 演示为什么确认不等于最终状态。

### `BoundedSseBuffer`

- 在压力下合并或丢弃 progress；
- 记录需要权威重新拉取；
- 永不丢弃最终响应。

### 恢复辅助函数

- 返回对代理安全的 SSE 头和 keepalive 注释；
- 生成重连与重新拉取计划；
- 用确定性的指数退避和 jitter 来分散重试。

## Use It

从仓库根目录执行：

```bash
cd phases/13-tools-and-protocols/29-mcp-reliability-cancellation-and-flow-control/code
python3 main.py
python3 -m unittest discover tests -v
```

演示会跑出核心竞态的双方，在一个临时文件账本中执行一次事务化去重的变更，让一个有界 progress 缓冲区过载，并展示一个持久 Task 从“已确认取消”走向“已被 worker 观察到的取消”。

## 交互实验

在不增加 sleep 的前提下运行四种事件顺序。

1. 启动请求 `A`，取消它，然后调用 `complete()`。
2. 启动请求 `B`，让它完成，然后投递 cancellation。
3. 启动请求 `C`，在每个 idle 截止时间之前发出 progress，然后越过 maximum 截止时间。
4. 通过 Streamable HTTP 启动请求 `D`，并关闭它的响应流。

为每个场景记录：

- 终态请求状态；
- 是否存在最终响应；
- 放到 wire 上的 cancellation 信号；
- 客户端应当忽略哪个事件。

然后把 `D` 改成 stdio。操作完全相同，但 cancellation 信号必须不同。

## 练习实验

给 `MutationLedger` 增加一个 `reserve_inventory` 变更。

要求：

1. key 绑定 SKU、数量、租户和操作名。
2. 用同一个 key 和相同参数重试，返回第一次的预留。
3. 用被改动的数量重试会失败，且不会产生新的预留。
4. 已经提交但丢失了响应的执行，可以按 key 对账。
5. 结果中不记录任何密钥或支付数据。
6. 客户端未提供 key 时，自动重试被禁用。
7. 增加一次模拟的订阅中断，并在决定下一步之前先重新拉取库存记录。
8. 在同一个屏障处启动两个账本连接，并发提交同一个 key，断言只提交了一次预留。
9. 修改第一个返回的预留对象。用同一个 key 重放，证明存储的结果没有变化。
10. 关闭并重新打开账本文件，然后按 key 对账该预留。

保持实验诚实：如果库存存放在另一个服务中，要说明该服务是否接受同一个 idempotency key，或者是否需要 transactional outbox 把本地提交与远端副作用桥接起来。

## 交付工件

`outputs/skill-mcp-reliability-reviewer.md` 是一个扁平化的可靠性评审 skill。给它一个 MCP 操作、传输方式、超时策略、重试行为、队列策略和恢复计划，它会返回竞态表、重试分类、幂等边界、流控检查和故障夹具。

## 验证清单

当以下陈述都成立时，本课即完成：

- stdio cancellation 发送 `notifications/cancelled` 且不接收响应。
- Streamable HTTP cancellation 关闭请求流，且不发送 cancellation POST。
- 先取消后完成会抑制最终响应。
- 先完成后取消会保留响应并忽略迟到的 cancellation。
- progress 可以重置 idle timeout，但永远不能重置 maximum timeout。
- 仅有一个新的 JSON-RPC id 会使变更再次执行。
- 在并发的双连接竞态下，同一个 idempotency key 和相同参数只执行一次。
- 已提交记录在重新打开后仍然存在，重放返回防御性副本。
- 修改某个返回结果不会改变已存储的结果。
- 有界缓冲区保持在容量上限之内并保留最终响应。
- 重连使用新请求、不发送 `Last-Event-ID`，并重新拉取受影响的状态。
- `tasks/cancel` 的确认会让任务保持非终态，直到 worker 观察到它。

## 生产失败模式

| 故障 | 可观察的症状 | 正确的响应 |
|---------|--------------------|------------------|
| HTTP 客户端 POST cancellation 通知 | 服务端与客户端对请求生命周期产生分歧 | 关闭该请求的 SSE 响应流 |
| 服务端在已接受取消后仍发送响应 | 客户端收到不可用的迟到结果 | 当取消胜出时停止工作并抑制后续消息 |
| progress 重置了每一个截止时间 | 卡死的工作可以永远存活 | 保留一个独立的绝对 maximum timeout |
| 把新 RPC id 当作去重 | 扣款、部署或删除执行了两次 | 增加持久化的应用 idempotency key |
| key 检查与副作用是分离的 | 并发 worker 都观察到 key 缺失 | 原子地提交 key 占用、副作用记录与结果 |
| 跨副本使用内存账本 | 重启或另一个 worker 忘记先前的提交 | 使用共享持久存储或上游幂等 |
| 直接返回存储的可变结果 | 调用方的修改破坏了后续重放 | 序列化已提交结果并返回防御性副本 |
| key 被复用于不同参数 | 一个 key 别名指向两个业务意图 | 存储并比较参数指纹 |
| 无界 progress 队列 | 内存随慢消费者上涨 | 在有界范围内合并并丢弃可替换的 progress |
| 压力下丢弃了最终响应 | 客户端无法得知请求结果 | 预留容量或驱逐 progress，绝不丢弃最终响应 |
| 代理缓冲 SSE | progress 成批到达或超时之后才到达 | 禁用缓冲并配置兼容的代理超时 |
| 假定 `Last-Event-ID` 可用 | 客户端从服务端不支持的状态恢复 | 用新请求重连并重新拉取 |
| 每个客户端都立即重连 | 恢复过程制造出又一次故障 | 使用带 jitter 且设上限的指数退避 |
| 把 Task 确认当作最终取消 | UI 显示已停止，worker 仍在运行 | 轮询 Task 直到终态 |

## 毕业项目衔接

工具生态毕业项目应当把可靠性当作可执行证据，而不是架构图里的一段文字。

要求以下工件：

- 每种传输各一份 cancellation 竞态记录；
- 针对每个对外暴露的变更的重试表；
- 一份 idempotency-key 记录和不匹配夹具；
- 一份并发同 key 记录、一次重开检查和一次变更别名检查；
- 一次有界缓冲过载结果；
- 反向代理的 SSE 头与 idle 策略；
- 一份点名权威重新拉取方法的重连计划；
- 当毕业项目使用 Tasks 时，提供一份持久 Task 取消轨迹。

本地进程里一个绿色的请求只证明了正常路径。只有当丢失的响应、迟到的 cancellation、慢消费者和重连惊群都有确定性结果时，毕业项目才算达到生产就绪。

## Key Terms

| 术语 | 含义 |
|------|---------|
| Request cancellation | 放弃一个在途的 MCP 请求 |
| Cancellation race | 终态完成事件与取消事件之间的竞争 |
| Idle timeout | 自上一次有用的请求活动以来的限制 |
| Maximum timeout | 从请求开始算起的绝对限制，不受 progress 影响 |
| Idempotency key | 用于对某一个业务意图去重的应用标识符 |
| Atomic ledger | 把 key 占用、副作用记录和结果作为一个单元提交的持久边界 |
| Backpressure | 当生产者超过消费者时施加的控制 |
| Progress coalescing | 用更新的权威值替换旧 progress |
| Refetch | 在流出现缺口之后重新读取当前状态 |
| Jitter | 把重试在时间上分散开的有意扰动 |

## Further Reading

- [MCP 取消机制](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)
- [MCP Progress 通知](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)
- [MCP Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP Tasks 扩展](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)
