---
name: orchestration-picker
description: 为给定问题挑选一个编排拓扑（supervisor、swarm、hierarchical、debate，或不用拓扑），并以最小方式实现它。
version: 1.0.0
phase: 14
lesson: 28
tags: [orchestration, supervisor, swarm, hierarchical, debate]
---

给定一个产品领域和一个任务类别，挑选最小拓扑。

决策：

1. 1 个智能体 + workflow patterns（第 12 课）够吗？-> 完全不用拓扑。
2. 2-4 个职责各异的专家？-> **supervisor-worker**。
3. 延迟关键且专家能干净地 handoff？-> **swarm**。
4. 10+ 个专家，supervisor 的上下文预算失效？-> **hierarchical**。
5. 准确率比成本更重要，多提议者 + 批判有帮助？-> **debate**（第 25 课）。

产出：

1. 所选定拓扑的脚手架。
2. swarm 上的跳数计数器；hierarchical 上的嵌套深度限制；debate 上的轮次上限。
3. 每次 handoff 或每步的可观测性钩子（OTel GenAI spans，第 23 课）。
4. 一段「为什么是这个而不是那个」的 README 章节。

硬性拒绝：

- 把 3 次 LLM 调用串起来就称为「多智能体」。那是 prompt chain。
- 没有跳数计数器的 swarm。弹跳是必然的。
- 每个分支到底部只剩 1 个专家的 hierarchical。把它拍平。

拒绝规则：

- 如果用户想为一个单个 ReAct 循环就能处理的任务上多智能体，拒绝并建议第 01 课。
- 如果用户想为两步任务上 supervisor，拒绝并建议 prompt chaining（第 12 课）。
- 如果领域有合规 / 审计要求，拒绝 swarm 并建议 supervisor 或 hierarchical。

输出：拓扑脚手架 + 带决策理由的 README。结尾附「下一步读什么」，指向第 13 课（LangGraph）以了解 supervisor 实现、第 16 课（OpenAI Agents SDK）以了解 handoffs-as-tools，或第 25 课以了解 debate 的具体细节。