---
name: crew-or-flow
description: 为给定任务在 CrewAI 的 Crew 与 Flow 之间做出选择，并搭建最小实现。
version: 1.0.0
phase: 14
lesson: 15
tags: [crewai, crews, flows, multi-agent, role-based]
---

给定一个任务描述，选择 Crew（自治）还是 Flow（确定性），然后搭建。

决策：

1. 任务是否有 SLA、合规或确定性重放要求？-> Flow。
2. 任务是否是探索性的（研究、初稿、头脑风暴）？-> Crew。
3. 任务是否有 4 个以上专家、且顺序由 LLM 决定？-> Hierarchical Crew。
4. 任务是否只有 <=3 个专家且顺序固定？-> Sequential Crew 或 Flow——优先 Flow。

对于 Crews，产出：

1. Agent 定义：role、goal、backstory（精简、<=200 字）、tools。
2. Task 定义：description、expected_output、agent。
3. 使用正确 Process（Sequential | Hierarchical）的 Crew。
4. 一个测试 harness，在示例输入上运行 Crew，并检查是否产出了 expected_outputs。

对于 Flows，产出：

1. `@start` 入口函数。
2. 构成 DAG 的 `@listen(topic)` 步骤。
3. 显式的事件 topic；不做魔法广播。
4. 一个重放 harness：给定 kickoff payload，可确定性地重新运行。

硬拒绝：

- 没有 backstories 的 Crews。Backstories 是承重结构。
- 没有显式 topic 名称的 Flows。“隐式链式”违背了审计目的。
- 只有 2 个专家的 Hierarchical Crews。manager 的开销不划算。

拒绝规则：

- 如果用户要求在一个纯生产合规任务上用 Crew，拒绝并迁移到 Flow。
- 如果用户要求在一个开放式研究任务上用 Flow，拒绝并迁移到 Crew。
- 如果 backstory 超过 200 字，拒绝并要求删减。上下文预算是有限的。

输出：`agents.py`、`tasks.py`、`crew.py` 或 `flow.py`，以及带决策理由的 `README.md`。结尾的“接下来读什么”指向：若需要观测则看第 24 课（Langfuse/AgentOps），若 Flow 需要持久化恢复语义则看第 13 课。