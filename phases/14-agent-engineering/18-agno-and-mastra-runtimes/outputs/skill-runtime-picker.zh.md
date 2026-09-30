---
name: runtime-picker
description: 针对给定的技术栈、延迟预算和运营形态，选择一个生产级 agent 运行时（Agno、Mastra、LangGraph、提供商 SDK）。
version: 1.0.0
phase: 14
lesson: 18
tags: [agno, mastra, langgraph, runtime, selection]
---

给定技术栈、延迟预算、所需原语和运营形态，选择一个运行时。

决策：

1. Python + FastAPI + 每秒数千个短生命周期 agent → **Agno**。
2. TypeScript + Next.js/Vercel + 统一多提供商 → **Mastra**。
3. 持久化状态、显式图、失败后可恢复 → **LangGraph**（第 13 课）。
4. Claude 优先的产品、想要 Claude Code 的 harness 形态 → **Claude Agent SDK**（第 17 课）。
5. OpenAI 优先的产品、想要 handoffs + guardrails + tracing → **OpenAI Agents SDK**（第 16 课）。
6. 多 agent 团队、actor 模型并发、故障隔离 → **AutoGen v0.4** / **Microsoft Agent Framework**（第 14 课）。
7. 基于角色的协作或事件驱动的确定性工作流 → **CrewAI** 的 Crew 或 Flow（第 15 课）。
8. 以上都不适用 → 直接 API 调用 + 第 01 课的标准库循环。

产出：

- 一份简短的决策文档：技术栈、延迟目标、所需原语、观察到的权衡。
- 在所选定运行时中的最小脚手架。
- 如果今天还在使用别的运行时，给出一份迁移计划。

硬性拒绝：

- 当工作负载是每个请求一次慢速调用时，纯粹因为「性能」而选择 Agno 或 Mastra。性能很少是瓶颈。
- 在没有理由的情况下，在 Python monorepo 中选择 TypeScript 运行时。混合语言的 agent 代码是一种运维税。
- 为无状态的短任务选择 LangGraph。checkpointer 带来的开销，一个简单工作流（第 12 课）即可避免。

拒绝规则：

- 如果用户想要「五种运行时都来，以便比较」，拒绝。在你自己的工作负载上做基准测试；框架厂商的基准测试只是方向性参考。
- 如果用户想自托管 Mastra 的 `ee/` 特性，拒绝并指向许可证条款。
- 如果产品需要长时程异步工作（数小时到数天），拒绝自托管，转而路由到 Claude Managed Agents 或基于队列的架构（第 29 课）。

输出：决策文档 + 脚手架 + README。结尾以「接下来读什么」指向第 24 课（可观测性）和第 29 课（生产运行时），即框架之上的运营层。
