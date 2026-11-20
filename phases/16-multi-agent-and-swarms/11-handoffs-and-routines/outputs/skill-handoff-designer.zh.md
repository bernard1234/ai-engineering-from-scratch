---
name: handoff-designer
description: 为 Swarm/Agents-SDK 风格的系统设计 handoff 拓扑：存在哪些 agent、它们能调用哪些 handoff、哪些 context 会转移。
version: 1.0.0
phase: 16
lesson: 11
tags: [multi-agent, swarm, handoff, openai-agents-sdk]
---

给定一个面向用户的任务（通常是 triage 或基于 skill 的路由），产出一份可直接映射到 OpenAI Swarm 或 OpenAI Agents SDK 的 handoff 拓扑。

产出：

1. **Agent 清单。** 每个 agent：名称、一句话用途、工具，以及它能 handoff 给哪些其他 agent。
2. **Handoff 函数。** 每个 agent 的 tool 签名。每个 handoff 函数返回一个目标 Agent。
3. **Context 转移策略。** 在每条 handoff 边上：完整历史、最近 N 条 message，或摘要快照。给出理由。
4. **Guardrail。** 每个 agent 的输入校验（允许哪些 prompt 触发向敏感专家的 handoff），以及必要处的 handoff 认证。
5. **循环检测。** 检测乒乓（例如“A handoff 给 B；B 又 handoff 回 A”连续出现不止一次）的规则。
6. **Fallback 行为。** 如果 handoff 目标缺失（agent 被移除、认证失败），由哪个 agent 处理该 session。
7. **Session / memory 方案。** 使用 Agents SDK session、调用方管理的 memory，还是完全不用 memory。

硬性拒绝：

- 任何没有循环检测的 handoff 设计。
- 向拥有不同 tool 权限的专家传递完整历史的 handoff 函数（安全风险）。
- 假设 Swarm 的无状态行为、却又要求 multi-turn memory 的设计 —— 改用 Agents SDK session。

拒绝规则：

- 如果任务需要并行执行，拒绝 Swarm，改为推荐 supervisor（第 05 课）。
- 如果任务需要确定性的审计/重放，拒绝并推荐 LangGraph 静态图。
- 如果任务是简单的分阶段 DAG（research → code → review），改为推荐 CrewAI Sequential。

输出：一份一页纸的 handoff 简报。结尾附一段安全说明，讲 prompt injection 如何触发不想要的 handoff，以及哪些 guardrail 能拦住它。
