---
name: actor-runtime
description: 构建一个 AutoGen v0.4 形态的 actor 运行时，具备私有状态、每个 actor 独立 inbox、仅通过消息传递的 IPC、故障隔离以及死信队列。
version: 1.0.0
phase: 14
lesson: 14
tags: [autogen, actor-model, messaging, fault-isolation, dead-letter]
---

给定一个多智能体任务，产出一个 actor 运行时及所需的智能体 actor。

产出：

1. 一个 `Message` 类型，包含 `sender`、`recipient`、`topic`、`body`、`mid`。
2. 一个 `Actor` 基类，带 `receive(message, runtime)`。Actor 的状态是私有的。
3. 一个 `Runtime`，带共享队列、`send()`、`run_until_idle()` 以及死信队列。handler 中的异常进入 DLQ；不要向外传播。
4. 一个拓扑辅助：RoundRobin（固定轮转）、Selector（LLM 选择下一个），或自定义广播。
5. 每条消息的观测钩子：按第 23 课，发出带 `gen_ai.agent.name` 和 `gen_ai.operation.name` 的 OTel span。

硬拒绝：

- 同步消息传递（发送方阻塞等待接收方返回）。那是 v0.2 的模型；它会破坏故障隔离。
- 跨 actor 的共享可变状态。Actor 通过消息读取状态，或者根本不读取。
- 会传播 handler 异常的运行时。失败应进入 DLQ；让其他 actor 继续运行。

拒绝规则：

- 如果任务只有两个 actor 且是固定往返，拒绝 actor 框架，建议使用 prompt chain（第 12 课）。当有 >=3 个 actor 或需要异步并发时，actor 的成本才划算。
- 如果用户想要“同步模式”以便“更容易调试”，拒绝。建议改用 logging + tracing（第 23 课）。
- 如果领域是严格请求/响应、且只有一个专家，建议用 routing（第 12 课）而不是 actor 团队。

输出：`message.py`、`actor.py`、`runtime.py`、`teams.py`、`README.md`，说明 DLQ 策略、拓扑选择以及 OTel span 是如何接入的。结尾的“接下来读什么”指向：若 actor 需要协商则看第 25 课（multi-agent debate）、若需要 tracing 则看第 23 课（OTel）、若想要面向未来的运行时则看 Microsoft Agent Framework。