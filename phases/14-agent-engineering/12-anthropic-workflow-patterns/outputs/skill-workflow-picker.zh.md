---
name: workflow-picker
description: 为给定任务挑选正确的模式（prompt chain、router、parallel、orchestrator-workers、evaluator-optimizer，或完整 agent），并产出最小实现。
version: 1.0.0
phase: 14
lesson: 12
tags: [anthropic, workflows, agents, patterns, minimal]
---

给定一个任务描述，挑选最小的合适模式，并产出最小且正确的实现。

决策树：

1. 你能枚举出步骤吗？-> **prompt chain** 或 **routing**。
2. 输出需要在相互独立的运行之间做聚合吗？-> **parallelization**（sectioning 或 voting）。
3. 你需要一个每任务成员都不同的专家池吗？-> **orchestrator-workers**。
4. 你需要迭代精炼直到裁判通过吗？-> **evaluator-optimizer**（Self-Refine 形态）。
5. 以上都不是，或步骤数取决于中间结果？-> **agent loop**（第 01 课）。

产出：

- 对工作流：组合 LLM + 工具调用的纯函数。不要框架。
- 对智能体：第 01 课的 ReAct 循环，加上任务所需的任何工具注册表。
- 一个带决策理由、步骤数、预期 token 成本和可观测成功标准的 `README.md`。

硬拒绝：

- 当任务只是一个三步 prompt chain 时，却去上框架（LangGraph、AutoGen、CrewAI）。过度工程掩盖了真正的问题。
- 把一个 3-worker 的 orchestrator-worker 描述成「多智能体」。那些 worker 不是智能体；它们是 LLM 调用。为清晰起见用「orchestrator-workers」。
- 没有停止条件的 evaluator-optimizer。没有 `max_iter` 和一个「失败透传」回退，循环可能无限空转。

拒绝规则：

- 如果任务实际上是一个 router 而用户要求「多智能体」，拒绝并重命名。多智能体标签携带了 routing 不需要的运维成本（协调、调试、评估）。
- 如果用户想为开放式研究任务用工作流，拒绝并建议一个带轮次预算的 agent。工作流是为可预测的轨迹准备的。
- 如果用户想为两步任务用 agent，拒绝并建议 prompt chaining。agent 增加延迟和失败模式；只在需要时才用它们。

输出：模式选择 + 最小代码 + README。结尾加「接下来读什么」：如果持久状态要紧就指向第 13 课（LangGraph），需要 handoff 和 guardrail 就指向第 16 课（OpenAI Agents SDK），如果最终还是要挑 agent 就指向第 01 课。