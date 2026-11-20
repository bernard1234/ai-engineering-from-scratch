---
name: framework-picker
description: 通过让抽象匹配问题形态，为 agent 任务在 LangGraph、CrewAI、AutoGen、Agno 或纯 Python 之间做选择。
version: 1.0.0
phase: 11
lesson: 17
tags: [langgraph, crewai, autogen, agno, agent-framework, orchestration, decision-matrix]
---

给定任务描述（问题形态、每次运行的总 LLM 调用数、分支模式、持久化与恢复需求、human-in-the-loop 检查点、并行 fanout、session memory、预期每日运行量），输出：

1. 形态匹配。用一句话点出合适的抽象：graph（类型化 state、命名 transition）、org chart（专家角色、manager 路由的交接）、chat（agent 相互对话直到完成）、带 tool 的单个 agent。如果你选不出一个，说明这个任务还不是 agent 形态；停下来做拆解。
2. 分支决策权。谁选择下一步：开发者（显式 edge）、manager LLM（CrewAI 分层模式）、对话式涌现（AutoGen GroupChat）、tool call 自路由（Agno）。若适用，请指出由 LLM 选择路由的每轮 token 成本。
3. State 预算。确认是否需要重启后恢复、time-travel 或人工中断。若需要，LangGraph 在 state 优先的抽象上胜出；Agno 只覆盖 session 级 memory。
4. 框架选择。输出 langgraph、crewai、autogen、agno、plain_python 之一。附上一句话论证，把形态与 state 的答案映射到该框架的核心抽象上。
5. 逃生通道。若每日运行量超过 10_000，或任务不超过两次 LLM 调用且无 state，则建议用纯 Python + provider SDK。任务小的时候，没有框架才是最快的框架。

拒绝对已知 DAG 的确定性工作流推荐 AutoGen；GroupChatManager 要花 token 去挑选发言者，而开发者本可以静态接好。CrewAI 确实通过 `output_pydantic` / `output_json` 支持结构化任务输出（见 [docs.crewai.com/en/concepts/tasks](https://docs.crewai.com/en/concepts/tasks)），但它的 `context` 通道仍然要经由下一个任务的 prompt 字符串流转。当工作流依赖裸 `context` 跨任务传递结构化 state、却没有接上上述任一输出 schema 时，要回绝 CrewAI。对两次调用的 summarizer 回绝 LangGraph；StateGraph 的开销是纯税。当任务以 reducer 语义 fanout 到超过 4 个并行 sub-worker 时回绝 Agno；Agno 提供一个 `Parallel` block，其输出汇入一个以 step 名为 key 的 dict（见 [docs-v1.agno.com/workflows_2/overview](https://docs-v1.agno.com/workflows_2/overview) 与 [docs.agno.com/workflows/access-previous-steps](https://docs.agno.com/workflows/access-previous-steps)），但它没有暴露与 LangGraph 相当的 Send 式 fanout-and-reduce API。

示例输入："长时研究流程：制定计划，fanout 到三个 retriever，综合，人工批准 brief，写报告，引用来源。崩溃后必须能恢复。面向生产，每天 50 次运行。"

示例输出：
- Shape：graph。类型化 plan，三个并行 retriever，synthesize 与 write 之间有命名 transition。
- 分支：由开发者通过条件 edge 决定。没有每轮的 manager LLM。
- State：需要恢复与人工中断。LangGraph 是必须的。
- Framework：langgraph。state、Send fanout、interrupt_before 与 PostgresSaver 都是一等公民。
- 逃生通道：不适用。每天 50 次远低于纯 Python 阈值，且工作流的状态化程度太高，不能不上框架。
