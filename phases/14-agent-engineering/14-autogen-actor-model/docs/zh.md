# 面向智能体的 Actor 模型——异步消息与类型化运行时

> 智能体作为 actor：异步消息交换、事件驱动处理器、故障隔离、天然并发。AutoGen v0.4（Microsoft Research，2025 年 1 月）围绕这个模型重新设计了智能体编排；该框架现已进入维护模式，其生产继任者是 Microsoft Agent Framework（2025 年 10 月公开预览）。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~75 minutes

## 学习目标

- 描述 actor 模型：智能体作为 actor、消息作为唯一的 IPC、按 actor 的故障隔离。
- 说出 AutoGen v0.4 的三层 API——Core、AgentChat、Extensions——以及每一层是做什么的。
- 解释为什么把消息投递与处理解耦能带来故障隔离和天然并发。
- 用 Python 实现一个标准库 actor 运行时，并把一个双智能体代码审查流程移植上去。

## 问题

大多数智能体框架是同步的：一个智能体生产，一个智能体消费，都在一个调用栈里。故障会压垮这个栈。并发是后补的。分布化需要重写。

AutoGen v0.4 的回答：actor 模型。每个智能体都是一个带私有收件箱（inbox）的 actor。消息是唯一的交互方式。运行时把投递与处理解耦。故障隔离到单个 actor。并发是天然的。分布化只是换了传输层。

## 概念

### Actors

一个 actor 有：

- 一份私有状态（从不被外部直接触碰）。
- 一个收件箱（消息队列）。
- 一个处理器：`receive(message) -> effects`，其中 effects 可以是「回复」「发给另一个 actor」「spawn 新的 actor」「更新状态」「停止自己」。

两个 actor 不能共享内存。它们只能互相发消息。

### 三层 API

AutoGen v0.4 把它的表面分成三层：

1. **Core。** 底层 actor 框架。`AgentRuntime`、`Agent`、`Message`、`Topic`。异步消息交换，事件驱动。
2. **AgentChat。** 任务驱动的高层 API（v0.2 的 ConversableAgent 的替代）。`AssistantAgent`、`UserProxyAgent`、`RoundRobinGroupChat`、`SelectorGroupChat`。
3. **Extensions。** 集成——OpenAI、Anthropic、Azure、工具、记忆。

### 为什么解耦要紧

在 v0.2 模型里，调用 `agent_a.chat(agent_b)` 会同步阻塞 agent_a，直到 agent_b 返回。在 v0.4 里，`send(agent_b, msg)` 把消息放进 agent_b 的收件箱就返回。运行时稍后投递。三个后果：

- **故障隔离。** Agent B 崩溃不会拖垮 Agent A——运行时在 B 的处理器里捕获失败并决定做什么（记录、重试、进入死信）。
- **天然并发。** 同时有大量消息在途；actor 并发处理各自的收件箱。
- **分布就绪。** 无论 actor 在同进程内还是在另一台主机上，收件箱 + 传输是同一个抽象。

### 拓扑

- **RoundRobinGroupChat。** 智能体按固定轮转依次发言。
- **SelectorGroupChat。** 一个 selector 智能体根据对话上下文挑选下一个是谁。
- **Magentic-One。** 面向网页浏览、代码执行、文件处理的参考多智能体团队。构建在 AgentChat 之上。

### 可观测性

OpenTelemetry 支持是内置的。每条消息发出一个 span；工具调用按 2026 年的 OTel GenAI 语义约定（第 23 课）携带 `gen_ai.*` 属性。

### 状态：维护模式

2026 年初：AutoGen v0.7.x 对研究和原型稳定。微软已把活跃开发转移到 Microsoft Agent Framework，即生产继任者（2025 年 10 月 1 日公开预览；1.0 GA 目标是 2026 年第一季度末）。AutoGen 的模式向前移植得很干净——actor 模型才是经久不衰的思想。

```figure
actor-mailbox
```

## Build It

`code/main.py` 实现了一个标准库 actor 运行时：

- `Message` —— 类型化载荷，带 `sender`、`recipient`、`topic`、`body`。
- `Actor` —— 抽象类，带 `receive(message, runtime)`。
- `Runtime` —— 带共享队列、投递、故障隔离的事件循环。
- 一个双 actor 演示：`ReviewerAgent` 审查代码，`ChecklistAgent` 跑检查清单；它们交换消息直到达成共识。

运行它：

```
python3 code/main.py
```

trace 展示消息投递、一个 actor 中一次被模拟的失败（不拖垮另一个），以及收敛到一个共享结论。

## Use It

- **AutoGen v0.4/v0.7**（维护）—— 对研究、原型、多智能体模式稳定。
- **Microsoft Agent Framework** —— 生产继任者（2025 年 10 月公开预览）；同样的 actor 模型思想装进一个刷新过的 API。
- **LangGraph swarm 拓扑**（第 13 课）—— 通过共享工具交接实现的相似模式。
- **自定义 actor 运行时** —— 当你需要特定传输（NATS、RabbitMQ、gRPC）时。

## Ship It

`outputs/skill-actor-runtime.md` 为给定的多智能体任务生成一个最小 actor 运行时加一个团队模板（RoundRobin 或 Selector）。

## 练习

1. 加一个死信队列：当处理器抛异常时，把失败消息暂存起来供人工检查。在你的玩具里 DLQ 被命中的频率是多少？
2. 实现 `SelectorGroupChat`：一个 selector actor 根据对话状态挑选谁处理下一条消息。
3. 加分布式传输：把进程内队列换成 JSON-over-HTTP 服务器，让 actor 能跑在独立进程里。
4. 给每条消息接一个 OTel span（或一个 no-op 占位）。按第 23 课发出 `gen_ai.agent.name`、`gen_ai.operation.name`。
5. 读 AutoGen v0.4 的架构文章。把你的玩具移植到真正的 `autogen_core` API。你跳过了哪些在生产中要紧的东西？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Actor | 「智能体」 | 私有状态 + 收件箱 + 处理器；没有共享内存 |
| Message | 「事件」 | 类型化载荷；actor 交互的唯一方式 |
| Inbox | 「邮箱」 | 每个 actor 的待处理消息队列 |
| Runtime | 「智能体宿主」 | 路由消息并隔离故障的事件循环 |
| Topic | 「通道」 | actor 之间命名的发布-订阅路由 |
| Fault isolation | 「让它崩」 | 一个 actor 失败不会拖垮其他 actor |
| RoundRobinGroupChat | 「固定轮转团队」 | 智能体按顺序依次发言 |
| SelectorGroupChat | 「上下文路由团队」 | selector 挑选下一个是谁 |
| Magentic-One | 「参考团队」 | 面向网页 + 代码 + 文件的多智能体小队 |

## 延伸阅读

- [AutoGen v0.4，Microsoft Research](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— 重新设计文章
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 图形状的替代
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— AutoGen 默认发出的 span