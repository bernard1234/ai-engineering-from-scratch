---
name: primitive-mapper
description: 把任何 multi-agent 框架或代码库映射到四个 primitive 轴（agent、handoff、共享状态、orchestrator）。
version: 1.0.0
phase: 16
lesson: 04
tags: [multi-agent, primitives, framework-comparison, architecture]
---

给定一个 multi-agent 框架（或使用它的代码库），产出四 primitive 映射，让读者用一段话就能理解该框架。

产出：

1. **Agent 定义。** agent 如何构造？有哪些参数？它携带什么状态？指出确切的类或工厂。
2. **Handoff 机制。** 它使用三种 handoff 模式中的哪一种——函数返回、图边，还是发言者选择？如果是混合，哪一种是主要的？给出触发一次 handoff 的最小代码。
3. **共享状态模型。** 全量消息池还是投影视图？内存内还是持久化（checkpoint）？对并发写入是否线程安全？谁负责调和冲突？
4. **Orchestrator 类型。** 静态、LLM 选择、handoff 驱动，还是队列驱动？如果是 LLM 选择，默认用哪个模型？如果是静态，图是有环的还是 DAG？
5. **跨轴权衡。** 各用一句话说明：确定性、扩展性上限、可调试性、典型失败模式。

硬性拒绝：

- 任何声称某个抽象是“新的”的映射，却没有证明它不能归约为四个 primitive 之一。如果你无法归约，精确指出缺口，而不是发明第五个 primitive。
- 只引用营销文档的框架比较。永远要引用框架仓库或官方 cookbook 中的具体代码示例。
- 诸如“框架 X 更适合 agent”的陈述，却不指明该框架优化的是哪个 primitive。

拒绝规则：

- 如果框架是闭源的，且公开文档没有暴露 agent-handoff-state-orchestrator 这一面，说明没有内部实现就不可能做映射。
- 如果用户提供了代码库但没有框架（手写 agent），改为映射这套自定义实现，并标出哪个 primitive 设计不足。
- 如果框架早于 2024 年（最初的 AutoGen v0.2、Swarm 之前）且已不再维护，加一句说明它的后继者是否保留了这套映射。

输出：一份单页框架简报。先用一句话总结（“框架 X 把 handoff 固定为图边，并通过 reducer 暴露共享状态。”），然后是上述五个部分，最后用一段话指出这个框架的 primitive 最适合哪个生产项目。
