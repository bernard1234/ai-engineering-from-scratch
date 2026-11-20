# Agent 框架取舍——Graph、Role 与 Actor 编排

> 每个框架都在卖同一个 demo（research agent 产出一份报告），也都在藏同一个 bug（state schema 与编排层打架）。选那个抽象与你问题形状匹配的框架；其余的一切都是你要写两遍的胶水代码。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 11 · 09 (Function Calling), Phase 11 · 16 (LangGraph)
**Time:** ~45 分钟
## 问题场景

你有一个需要不止一次 LLM 调用的任务。也许是一个研究工作流（计划、搜索、总结、引用）。也许是一条代码审查流水线（解析 diff、批评、打补丁、验证）。也许是一个多轮 assistant，能订机票、写邮件、提交报销单。你挑了一个框架。

三天后，你发现框架的抽象在泄漏。CrewAI 给了你 role，但当“researcher”需要把一份结构化计划交给“writer”时，它就开始跟你较劲。AutoGen 给了你 agent 之间的 chat，但没有一等 state，所以你的 checkpoint 变成了一段对话日志的 pickle。LangGraph 给了你 state graph，但强迫你在还不知道 agent 会做什么之前就命名每一次转移。Agno 给了你单 agent 抽象，你一想 fan out 到三个并发 worker，它就开始尖叫。

解决办法不是“挑最好的框架”，而是把框架的核心抽象匹配到你问题的形状上。本课就画这张地图。

## 核心概念

![Agent 框架矩阵：核心抽象 vs 问题形状](../assets/framework-matrix.svg)

2026 年的格局由四个框架主导。它们的核心抽象并不相同。

| 框架 | 核心抽象 | 最适合 | 最不适合 |
|-----------|------------------|----------|-----------|
| **LangGraph** | `StateGraph` —— 类型化 state、node、条件 edge、checkpointer。 | 具备显式 state 和 human-in-the-loop interrupt 的工作流；需要 time-travel 调试的生产 agent。 | 拓扑未知、松散的角色驱动头脑风暴。 |
| **CrewAI** | `Crew` —— role（goal、backstory）、task、process（sequential 或 hierarchical）。 | 带简短线性/层级计划的角色扮演或 persona 驱动工作流。 | 超出 crew 轮次历史的任何有状态场景；复杂分支。 |
| **AutoGen** | `ConversableAgent` 配对 —— 两个或多个 agent 轮流发言，直到某个退出条件。 | 多 agent *对话*（teacher-student、proposer-critic、actor-reviewer），思考从 chat 中涌现。 | 拓扑已知的确定性工作流（DAG）；任何需要跨重启持久 state 的场景。 |
| **Agno** | `Agent` —— 单个 LLM + tools + memory，可组合成 teams。 | 快速搭建的单 agent 和轻量 team；强大的多模态能力和内置 storage driver。 | 带自定义 reducer 的深度显式分支 graph。 |

### “abstraction”到底指什么

框架的核心抽象，是你向人介绍架构时画在白板上的那个东西。

- **LangGraph** → 你画一张图。node 是步骤，edge 是转移，每个点上的 state 对象都是有类型的。心智模型是状态机。
- **CrewAI** → 你画一张组织架构图。每个 role 有一份职位描述，一个 manager 来分配任务。心智模型是一支小规模的专家团队。
- **AutoGen** → 你画一条 Slack 私聊。两个 agent 互相发消息；需要主持人时再拉第三个进来。心智模型是 chat。
- **Agno** → 你画一个盒子，工具挂在盒子上。把几个盒子摆在一起就是一个 team。心智模型是“自带电池的 agent”。

### state 的问题

state 是大多数框架选型在生产中崩掉的地方。

- **LangGraph。** 类型化 state（`TypedDict` 或 Pydantic model），按字段的 reducer，一等 checkpointer（SQLite/Postgres/Redis）。resume、interrupt 和 time-travel 都是白送的。*（见 Phase 11 · 16。）*
- **CrewAI。** state 通过 `context` 字段以字符串形式在 task 之间流动，或者通过 `output_pydantic` 结构化。开箱没有按 crew 持久化的 store；如果 crew 必须扛过重启，你得自己外挂一个。
- **AutoGen。** state 就是 chat 历史加上任何用户定义的 `context`。对话转录会持久化；任意的 workflow state 则不会，除非你自己写 adapter。
- **Agno。** 内置 storage driver（SQLite、Postgres、Mongo、Redis、DynamoDB）通过 `storage=` 挂到 `Agent` 上——对话 session 和用户 memory 自动持久化。它不是完整的 graph checkpointer，而是 session store。

### 分支的问题

每一个非平凡的 agent 都会分支。关键是分支由谁决定。

- **LangGraph** —— 你决定，通过条件 edge。路由是一个带具名分支的 Python 函数。分支在已编译的 graph 里是一等公民；checkpointer 会记录走了哪条分支。
- **CrewAI** —— 在 hierarchical 模式下由 manager 决定；在 sequential 模式下你在构建时就决定了。路由隐含在 task 列表里；manager 的 prompt 之外没有一等的“if”。
- **AutoGen** —— agent 通过 chat 决定。分支从“下一个谁发言”中涌现。`GroupChatManager` 选择下一位发言人；你可以手写 `speaker_selection_method`，但默认是 LLM 驱动的。
- **Agno** —— agent 通过下一步调用哪个 tool 来决定。Team 有 coordinator/router/collaborator 模式；超出这些的分支是开发者的责任。

### observability 的问题

- **LangGraph** —— 通过 LangSmith 或任意 OTel exporter 实现 OpenTelemetry。每一次 node 转移都是一个 trace span；checkpoint 同时也是可重放的 trace。LangSmith 是官方方案；Langfuse/Phoenix 也有 adapter。
- **CrewAI** —— 自 2025 年末起提供一等 OpenTelemetry 支持；与 Langfuse、Phoenix、Opik、AgentOps 集成。
- **AutoGen** —— 通过 `autogen-core` 集成 OpenTelemetry；AgentOps 和 Opik 有 connector。追踪粒度是按 agent 消息，而不是按 node。
- **Agno** —— 内置 `monitoring=True` 开关加上 OpenTelemetry exporter；与 Langfuse 深度集成以追踪 session。

### 成本与延迟

四个框架都会带来按调用的开销（框架逻辑、校验、序列化）。开销从低到高大致是：Agno ≈ LangGraph < CrewAI ≈ AutoGen。差异主要取决于框架做了多少额外的 LLM 路由。CrewAI 的 hierarchical manager 花 token 决定下一个是谁；AutoGen 的 `GroupChatManager` 也一样。LangGraph 只在你写 `llm.invoke` 的地方花 token。Agno 的单 agent 路径很薄。

当每次运行的成本很关键时，优先选择显式路由（LangGraph 的 edge、AutoGen 的 `speaker_selection_method`）而不是 LLM 选择的路由。

### 互操作性

- **LangGraph** ↔ **LangChain** 的 tools、retrievers、LLMs。一等 MCP adapter（把 tools 作为 MCP server 导入）。
- **CrewAI** ↔ tools 继承自 `BaseTool`；LangChain tools、LlamaIndex tools 和 MCP tools 都能接入。通过 `allow_delegation=True` 实现 crew 之间的委派。
- **AutoGen** → `FunctionTool` 包装任意 Python callable；有 MCP adapter。在 agent 间模式上紧耦合 AG2 生态。
- **Agno** → `@tool` 装饰器或 BaseTool 子类；MCP adapter；tools 可以在 agent 和 team 之间共享。

## 技能

> 你能用一句话解释，为什么某个框架适合某个 agent 问题。

开工前的检查清单：

1. **画出形状。** 这是一个 graph（类型化 state、具名转移）？一场 role play（专家之间交接工作）？一段 chat（agent 一直聊到达成目标）？还是一个带 tools 的单 agent？
2. **决定谁分支。** 开发者决定分支 → LangGraph。manager agent 决定 → CrewAI hierarchical。chat 涌现 → AutoGen。tool 调用决定 → Agno。
3. **检查 state 预算。** 你需要从 checkpoint 恢复吗？需要 time-travel 吗？需要运行中途的人工 interrupt 吗？如果需要，默认选 LangGraph；Agno 的 session 覆盖会话范围的状态。
4. **检查成本预算。** LLM 选择的路由每一轮都要额外花 token。如果 agent 每天要跑几千次，优先显式路由。
5. **把框架开销纳入预算。** 每个框架都是又一个依赖。如果任务只是两次 LLM 调用加一个 tool，写 30 行纯 Python 就好；没有框架比有框架更便宜。

在你画得出 graph、org chart、chat 或 agent 盒子之前，拒绝伸手去拿框架。拒绝选一个会逼你为真正需要的东西跟它的 state 模型搏斗的框架。

## 决策矩阵

| 问题形状 | 首选框架 | 原因 |
|---------------|---------------------|-----|
| 带类型化 state、人工审批、长时间运行的 workflow DAG | LangGraph | 一等的 state、checkpointer、interrupt、time-travel。 |
| 角色分明的 research / writing 流水线 | CrewAI（sequential）或 LangGraph 子图 | 在 CrewAI 里按 task 配 role 表达成本很低；当分支变复杂时用 LangGraph 扩展。 |
| proposer-critic 或 teacher-student 对话 | AutoGen | 双 agent chat 就是它的原生形状。 |
| 带 tools、session、memory 的单 agent | Agno | 搭建最薄，内置 storage 和 memory。 |
| 带 reducer 的数千路并行 fanout | LangGraph + `Send` | 唯一提供一等并行派发 API 的框架。 |
| 快速原型，不承诺框架 | 纯 Python + provider SDK | 没有框架就是最快的框架。 |

```figure
l5-framework-fit
```

## Exercises

1. **简单。** 拿同一个任务——“研究 Anthropic 的总部、写一份 200 词的简报、引用来源”——在 LangGraph 里实现（四个 node：plan、search、write、cite），在 CrewAI 里实现（三个 role：researcher、writer、editor）。报告每次运行的 token 成本和代码行数。
2. **中等。** 在 AutoGen（researcher ↔ writer 对话，editor 通过 `GroupChat` 加入）和 Agno（单个 agent 带 `search_tools` 和 `write_tools`，外加一个 session store）里构建同一个任务。给四个实现按以下维度排序：(a) 每次运行成本，(b) 崩溃后恢复的能力，(c) 在写步骤之前注入人工审批的能力。
3. **困难。** 构建一个决策树脚本 `pick_framework.py`，它接收一段简短的问题描述（JSON：`{has_typed_state, has_roles, has_dialogue, has_parallel_fanout, needs_resume}`）并返回一个建议加一句理由。用你自己设计的六个用例验证它。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Orchestration | “agent 如何协同” | 决定下一个运行哪个 node/role/agent 的层。 |
| Durable state | “重启后能恢复” | 能扛过进程死亡的状态，挂在 checkpoint 或 session store 上。 |
| LLM-selected routing | “让模型决定” | 由 planner LLM 在每一轮挑选下一步；灵活，但每次决策都要花 token。 |
| Explicit routing | “开发者决定” | 由 Python 函数或静态 edge 挑选下一步；便宜且可审计。 |
| Crew | “一个 CrewAI 团队” | role + task + process（sequential 或 hierarchical）绑定成的单个 runnable。 |
| GroupChat | “AutoGen 的多 agent chat” | N 个 agent 之间由发言人选择器管理的托管对话。 |
| Team (Agno) | “多 agent 的 Agno” | 在一组 agent 之上以 route / coordinate / collaborate 模式运行。 |
| StateGraph | “LangGraph 的 graph” | 类型化 state、node、条件 edge、checkpointer 的抽象。 |

## Further Reading

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) —— StateGraph、checkpointer、interrupt、time-travel。
- [CrewAI documentation](https://docs.crewai.com/) —— Crews、Flows、Agents、Tasks、Processes。
- [AutoGen documentation](https://microsoft.github.io/autogen/) —— ConversableAgent、GroupChat、teams、tools。
- [Agno documentation](https://docs.agno.com/) —— Agent、Team、Workflow、storage、memory。
- [Anthropic — Building effective agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 与框架无关的模式库（prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer）。
- [Yao et al., "ReAct: Synergizing Reasoning and Acting" (ICLR 2023)](https://arxiv.org/abs/2210.03629) —— 每个框架都在包装的那个循环。
- [Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation" (2023)](https://arxiv.org/abs/2308.08155) —— AutoGen 的设计论文。
- [Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (UIST 2023)](https://arxiv.org/abs/2304.03442) —— CrewAI 式 persona 栈所基于的角色扮演 foundation。
- Phase 11 · 16（LangGraph）—— 本课用来做基准对比的框架。
- Phase 11 · 19（Reflexion）—— 一个能干净地映射到 LangGraph、却别扭地映射到 CrewAI 的模式。
- Phase 11 · 22（生产 observability）—— 如何给你选定的任何框架插桩。
