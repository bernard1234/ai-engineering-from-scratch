# Handoff 与 Routine —— 无状态编排

> OpenAI 的 Swarm（2024 年 10 月）把 multi-agent 编排蒸馏为两个原语：**routine**（作为 system prompt 的指令 + 工具）与 **handoff**（一个返回另一个 Agent 的工具）。没有状态机，没有分支 DSL —— LLM 通过调用正确的 handoff 工具来完成路由。OpenAI Agents SDK（2025 年 3 月）是它的生产级继任者。Swarm 本身仍是最干净的概念参考 —— 它的全部源码只有几百行。这个模式之所以流行，是因为 API 表面大致是“agent = prompt + tools；handoff = 返回 agent 的函数”。局限：无状态，因此记忆是调用方的问题。

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** 第 16 阶段，第 04 课（Primitive Model）
**Time:** ~60 分钟

## 问题场景

每个 multi-agent 框架都想让你学它的 DSL：LangGraph 的 node 与 edge、CrewAI 的 crew 与 task、AutoGen 的 GroupChat 与 manager。这些 DSL 是真实的抽象，但它们让整件事显得比实际需要的更笨重。

Swarm 朝相反方向推：利用模型本来就具备的 tool call 能力。handoff 变成 tool call。orchestrator 就是当前持有对话的那个 agent。状态机隐含在 agent 的 system prompt 里。

## 核心概念

### 两个原语

**Routine。** 一段 system prompt，定义 agent 的角色与可用工具。把它想成一组有作用域的指令：“你是一个 triage agent；如果用户问退款，就 handoff 给退款 agent。”

**Handoff。** 一个 agent 可以调用的 tool，它返回一个新的 Agent 对象。Swarm 运行时检测到 Agent 返回值，就为下一轮切换 active agent。

这就是全部的抽象。

```
def transfer_to_refunds():
    return refund_agent  # Swarm sees Agent return → switch active agent

triage_agent = Agent(
    name="triage",
    instructions="Route the user to the right specialist.",
    functions=[transfer_to_refunds, transfer_to_sales, transfer_to_support],
)
```

triage agent 的 system prompt 让它根据用户消息选择正确的 handoff。路由由 LLM 的 tool call 完成。

### 为什么它流行

- **API 小。** 只需学两个概念。
- **利用模型已经会做的事。** tool call 在各家 provider 上早已达到生产级。
- **没有状态机负担。** 你不用描述图；agent 的 prompt 自己描述它把控制权 handoff 给谁。

### 无状态的取舍

Swarm 在不同 run 之间显式地无状态。框架在一次 run 期间保留 message 历史，但不持久化任何东西。记忆、连续性、长时间运行的任务 —— 都是调用方的问题。

在生产环境（OpenAI Agents SDK，2025 年 3 月）中，这是发生变化的主要方面之一：SDK 增加了内置的 session 管理、guardrail 和 tracing，同时保留 handoff 原语。

### Swarm/handoff 适用的场景

- **Triage 模式。** 一线 agent 把用户路由给专家。
- **基于 skill 的 handoff。** “如果任务需要写代码，就调用 coder；如果需要研究，就调用 researcher。”
- **简短、有界的对话。** 客服支持、从 FAQ 到工单、简单工作流。

### Swarm 吃力的场景

- **带共享 memory 的长 session。** handoff 会把对话状态重置为新 agent 的 prompt 加历史。没有调用方管理的 memory，跨 agent 就不存在持久状态。
- **并行执行。** handoff 一次只发生一个 —— active agent 会切换。并行需要调用方编排多个 Swarm run。
- **审计与重放。** 无状态的 run 很难精确重放；LLM 的 handoff 选择不是确定性的。

### OpenAI Agents SDK（2025 年 3 月）

生产级继任者增加了：

- **Session 状态。** 跨 run 的持久 thread。
- **Guardrail。** 输入/输出校验钩子。
- **Tracing。** 每次 tool call 和 handoff 都会记录。
- **Handoff filter。** 控制 handoff 时哪些 context 会转移。

handoff 原语保留下来；生产级的易用性围绕它叠加。

### Swarm 对比 GroupChat

两者都用 LLM 驱动的路由，但区别在于**由谁决定下一步**：

- GroupChat：由外部的选择器（函数或 LLM）挑选下一个发言者。
- Swarm：当前 agent 通过调用 handoff 工具来挑选自己的继任者。

Swarm 是“agent 决定下一步”；GroupChat 是“manager 决定下一步”。Swarm 的决策存在于 active agent 的 tool call 中；GroupChat 的决策存在于 `GroupChatManager` 中。

```figure
sw-handoff-routing
```

## Build It

`code/main.py` 从零实现 Swarm：一个 Agent dataclass、一个 handoff 机制（tool 返回 Agent），以及一个检测 agent 切换的 run loop。

演示：一个 triage agent 路由到 refund、sales 或 support 专家。每个专家有自己的工具。run loop 会打印每一次 handoff。

运行：

```
python3 code/main.py
```

## Use It

`outputs/skill-handoff-designer.md` 为给定任务设计 handoff 拓扑：存在哪些 agent、它们能调用哪些 handoff、哪些 context 会转移。

## Ship It

检查清单：

- **Handoff 日志。** 每次 handoff 写入一个 trace 事件，包含 from-agent、to-agent、context snapshot。
- **Context 转移规则。** 决定 handoff 时哪些内容会移动：完整历史（昂贵）、最近 N 条 message，或一份摘要。
- **Handoff 上的 guardrail。** 向拥有不同 tool 权限的专家发起 handoff 必须经过认证 —— 否则 prompt injection 可以强制触发不想要的 handoff。
- **循环检测。** 两个 agent 来回 handoff 是常见故障；用简单的 last-K 环形检查来检测。
- **Fallback agent。** 如果 handoff 目标不存在，回退到一个安全的默认 agent。

## Exercises

1. 运行 `code/main.py`，让 triage 转给 refund agent。确认第二轮的 active agent 是 refund。
2. 添加一条循环检测规则：如果同样的两个 agent 连续 handoff 了 3 次，就强制退出。设计 fallback。
3. 阅读 OpenAI Agents SDK 关于 handoff filter 的文档。实现一个“handoff 时摘要”的版本：在接手方 agent 接管之前，交出方 agent 把 context 压缩成要点摘要。
4. 把 Swarm 的 handoff 与 GroupChatManager 的选择器做比较。哪种模式会让 prompt injection 更严重，为什么？
5. 阅读 Swarm cookbook（https://developers.openai.com/cookbook/examples/orchestrating_agents）。找出 Swarm 做出的一个明确设计决策，OpenAI Agents SDK 是改变了它还是保留了它。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Routine | “agent 的 prompt” | system prompt + tool 列表。定义角色和可用的 handoff。 |
| Handoff | “转交给另一个 agent” | 一个 active agent 能调用的 tool，它返回一个新的 Agent。运行时切换 active agent。 |
| Stateless | “run 之间没有记忆” | Swarm 不做任何持久化；记忆是调用方的责任。 |
| Active agent | “现在谁在说话” | 当前持有对话的那个 agent。handoff 会改变它。 |
| Context transfer | “handoff 时迁移什么” | 决定接手方 agent 能看到哪些历史的策略：完整、最近 N 条，或摘要。 |
| Handoff loop | “agent 互相打乒乓” | 两个 agent 不断互相 handoff 的故障模式。 |
| OpenAI Agents SDK | “生产版 Swarm” | 2025 年 3 月的继任者；在 handoff 原语之上增加 session、guardrail、tracing。 |
| Handoff filter | “转移时的闸门” | SDK 特性，在 handoff 边界检查并修改 context。 |

## Further Reading

- [OpenAI cookbook —— Orchestrating Agents: Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents) —— 参考性阐述
- [OpenAI Swarm 仓库](https://github.com/openai/swarm) —— 原始实现，作为概念参考保留
- [OpenAI Agents SDK 文档](https://openai.github.io/openai-agents-python/) —— 带 session 和 tracing 的生产级继任者
- [Anthropic 关于 Claude 中 handoff 的笔记](https://docs.anthropic.com/en/docs/claude-code) —— Claude Code subagent 如何通过 `Task` 使用类似 handoff 的模式
