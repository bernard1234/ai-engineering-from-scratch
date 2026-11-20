# multi-agent 的 primitive 模型

> 四个 primitive，仅此而已——agent、handoff、共享状态、orchestrator——张成一个四维设计空间，而 2026 年出货的主要 multi-agent 框架（AutoGen、LangGraph、CrewAI、OpenAI Agents SDK、Microsoft Agent Framework）都是这个空间中的点。本课从零构建它们，在四者之上运行一个玩具系统，然后把每个主要框架映射到同样的坐标轴上，让你用一段话就能读懂任何新发布。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** 第 14 阶段（Agent Engineering）、第 16 阶段，第 01 课（Why Multi-Agent）
**Time:** ~60 分钟

## 问题场景

每隔六个月就会出一个新的 multi-agent 框架。2023 年的 AutoGen。2024 年的 CrewAI。2024 年的 LangGraph 和 OpenAI Swarm。2025 年 4 月的 Google ADK。2026 年 2 月的 Microsoft Agent Framework RC。每一份新闻稿都声称自己是“正确的抽象”。

如果你试图逐个学习，你会精疲力竭。API 看起来各不相同。文档对“agent”是什么意见不一。一个框架把共享内存叫作“blackboard”，另一个叫作“message pool”，第三个叫“StateGraph”。你开始怀疑这个领域只是在原地打转。

并非如此。在营销话术之下，这四个 primitive 是稳定的。学一次，就能用一段话读懂每个新框架。

## 核心概念

### 四个 primitive

1. **Agent**——一份 system prompt 加一个工具列表。无状态；每次运行都从其 system prompt 和当前消息历史开始。
2. **Handoff**——从一个 agent 到另一个 agent 的结构化控制转移。机制上，是一个返回新 agent 的 tool call，或一条按条件跳转的图边。
3. **共享状态**——任何可被多个 agent 读取（有时写入）的数据结构。消息池、blackboard、键值存储、向量内存。
4. **Orchestrator**——决定谁下一个发言的那个东西。选项有：显式的图（确定性）、LLM speaker-selector（软性）、最后发言者的 handoff 调用（OpenAI Swarm），或队列上的调度器（swarm 架构）。

这就是整个设计空间。每个框架为每个轴选择默认值；其余都只是表层语法。

### 2026 年的每个框架如何映射到它

| 框架 | Agent | Handoff | 共享状态 | Orchestrator |
|-----------|-------|---------|--------------|--------------|
| OpenAI Swarm / Agents SDK | `Agent(instructions, tools)` | 工具返回 Agent | 调用方的问题 | LLM 的下一次 handoff 调用 |
| AutoGen v0.4 / AG2 | `ConversableAgent` | GroupChat 上的 speaker-selector | 消息池 | selector 函数（LLM 或轮询） |
| CrewAI | `Agent(role, goal, backstory)` | `Process.Sequential / Hierarchical` | 串接的 Task 输出 | manager LLM 或静态顺序 |
| LangGraph | 节点函数 | 图边 + 条件 | `StateGraph` reducer | 图本身，确定性 |
| Microsoft Agent Framework | agent + 编排模式 | 模式相关 | thread / context | 模式相关 |
| Google ADK | agent + A2A card | A2A task | A2A artifacts | 由 host 决定 |

表层差异看似巨大。底下：同样的四个旋钮。

### 为什么这很重要

一旦你看到这些 primitive，框架比较就变成一份简短清单：

- orchestrator 是信任 LLM 来路由（Swarm），还是在代码里钉死路由（LangGraph）？
- 共享状态是全历史（GroupChat）还是投影视图（StateGraph reducer）？
- agent 能否修改彼此的 prompt（CrewAI manager），还是只能 handoff（Swarm）？

这三个问题能回答给定问题与框架匹配度的 80%。你不再四处挑选“最好的 multi-agent 框架”，而是开始为你真正关心的那个轴做设计。

### 无状态洞察

除共享状态外，每个 primitive 都是无状态的。Agent 是 (prompt, tools) 的函数。Handoff 是一次函数调用。Orchestrator 是一个调度器。**系统中唯一有状态的东西就是共享状态。** 所有有趣的 bug 都在那里：内存投毒（第 15 课）、消息顺序、版本化、写入竞争。

隐藏共享状态的框架（Swarm）把问题推给调用方。集中管理它的框架（LangGraph checkpoint、AutoGen 池）让它可检视，但把协调成本转移到共享状态的实现上。

### 单个 primitive 的解剖

#### Agent

```
Agent = (system_prompt, tools, model, optional_name)
```

没有记忆。没有状态。拥有相同 system prompt 和工具的两个 agent 可以互换。所有看起来像 per-agent 状态的东西，实际上都在共享状态或 handoff 协议里。

#### Handoff

```
Handoff = (from_agent, to_agent, reason, payload)
```

三种实现占据主导：

- **函数返回**——工具返回下一个 agent。这是 OpenAI Swarm 的模式。agent 在各自的工具 schema 中携带路由。
- **图边**——LangGraph。边是声明式的。LLM 产出一个值；条件选择下一个节点。
- **发言者选择**——AutoGen GroupChat。一个 selector 函数（有时本身是一次 LLM 调用）读取池子并挑选下一个发言者。

#### 共享状态

```
SharedState = { messages: [], artifacts: {}, context: {} }
```

至少是一个消息列表。通常更多：结构化产物（CrewAI Task 输出）、类型化 context（LangGraph reducer）、外部记忆（MCP、向量 DB）。

两种拓扑：**全量池**（每个 agent 看到每条消息）和**投影**（agent 看到按角色限定的视图）。全量池简单但扩展性差。投影池可扩展但需要前置的 schema 设计。

#### Orchestrator

```
Orchestrator = ({state, last_speaker}) -> next_agent
```

四种风味：

- **静态**——图在构建时固定（LangGraph 确定性、CrewAI Sequential）。
- **LLM 选择**——一个 LLM 读取池子并挑选下一个发言者（AutoGen、CrewAI Hierarchical）。
- **handoff 驱动**——当前 agent 通过调用 handoff 工具来决定（Swarm）。
- **队列驱动**——worker 从共享队列拉取；没有显式的下一发言者（swarm 架构、Matrix）。

### 框架之间变化的是什么

一旦 primitive 固定下来，剩余的设计决策就是：

- **记忆策略**——临时还是持久化 checkpoint（LangGraph checkpointer）。
- **安全边界**——谁可以批准一次 handoff（human-in-the-loop）。
- **成本核算**——每个 agent 的 token 预算。
- **可观测性**——追踪 handoff、持久化状态以便重放。

全都可以在 primitive 之上实现。没有一个是新的 primitive。

```figure
a5-primitive-radar
```

## Build It

`code/main.py` 用约 150 行 stdlib Python 实现这四个 primitive。没有真实 LLM——每个 agent 都是一个脚本化策略，让焦点保持在协调结构上。

该文件导出：

- `Agent`——一个 dataclass：name、system prompt、tools、policy 函数。
- `Handoff`——一个返回新 agent 的函数。
- `SharedState`——一个线程安全的消息池。
- `Orchestrator`——三个变体：`StaticOrchestrator`、`HandoffOrchestrator`、`LLMSelectorOrchestrator`（模拟）。

演示让同一条三 agent pipeline（research → write → review）跑遍三种 orchestrator 类型，并在最后打印消息池。你能看到输出的差异仅在于*谁挑选下一个*；agent 和共享状态在各次运行中完全相同。

运行：

```
python3 code/main.py
```

预期输出：三次 orchestrator 运行，每种模式一次。每次打印最终消息池。如果 researcher 提前判定完成，handoff 驱动的运行会触达更少的 agent——这就是 LLM 路由权衡的缩影。

## Use It

`outputs/skill-primitive-mapper.md` 是一个 skill，能读取任何 multi-agent 代码库或框架文档并返回四 primitive 映射。在新框架发布时运行它，在深入阅读文档之前先获得一段话的理解。

## Ship It

在采纳新框架之前，为它写出 primitive 映射。如果你写不出来，说明文档不完整，或者该框架正在发明第五个 primitive（罕见——检查是否存在你尚未见过的共享状态变体）。

把这份映射钉在你的架构文档里。当新成员加入时，先给他映射，再给 API 文档。当框架版本变化时，对比映射的差异，而不是更新日志的差异。

## Exercises

1. 用不同的 agent 策略运行 `code/main.py` 三次。观察 orchestrator 的选择如何改变哪些 agent 运行。
2. 实现第四种 orchestrator 类型：队列驱动，agent 轮询共享状态获取工作。会发生什么死锁，你如何检测它？
3. 拿 LangGraph quickstart（https://docs.langchain.com/oss/python/langgraph/workflows-agents）把它改写为四个 primitive。LangGraph 的哪些抽象是 1:1 映射，哪些是便利封装？
4. 阅读 OpenAI Swarm cookbook（https://developers.openai.com/cookbook/examples/orchestrating_agents）。指出 Swarm 让四个 primitive 中的哪一个最符合人体工程学，又把哪一个推给调用方。
5. 在这张表中找出一个完全隐藏共享状态的框架。解释当 agent 需要在 handoff 之间协调而又不能重读历史时，会出什么问题。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Agent | “一个带工具的 LLM” | 一个 `(system_prompt, tools, model)` 三元组。无状态。 |
| Handoff | “控制转移” | 一次结构化调用，指定下一个 agent 和可选负载。三种实现：函数返回、图边、发言者选择。 |
| Shared state | “记忆” / “context” | multi-agent 系统中唯一有状态的部分。消息池或 blackboard。 |
| Orchestrator | “协调者” | 决定下一个运行者是谁的那个东西。静态图、LLM selector、handoff 驱动或队列驱动。 |
| Primitive | “抽象” | 每个框架都会参数化的四条轴之一。不是框架特性。 |
| Message pool | “共享聊天历史” | 全历史的共享状态。易于推演，扩展性差。 |
| Projected state | “作用域视图” | 对共享状态的按角色视图。可扩展，需要 schema 设计。 |
| Speaker selection | “谁下一个说话” | orchestrator 模式：由一个函数（通常是 LLM）从一组中挑选下一个 agent。 |

## Further Reading

- [OpenAI cookbook: Orchestrating Agents — Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents)——对 handoff 驱动式编排最清晰的阐述
- [AutoGen stable docs](https://microsoft.github.io/autogen/stable/)——GroupChat + 发言者选择是 LLM 选择式编排的参考
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)——图边编排与基于 reducer 的共享状态
- [CrewAI introduction](https://docs.crewai.com/en/introduction)——role-goal-backstory 式 agent、Sequential / Hierarchical 流程
- [AG2 (community AutoGen continuation)](https://github.com/ag2ai/ag2)——微软把 v0.4 转入维护后仍活跃的 AutoGen v0.2 分支
