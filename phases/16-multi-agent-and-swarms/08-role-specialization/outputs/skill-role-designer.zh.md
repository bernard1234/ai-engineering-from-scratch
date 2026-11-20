---
name: role-designer
description: 为多智能体系统产出一份角色名册，针对给定任务命名 planner/executor/critic/verifier，并给出显式的 I/O schema。
version: 1.0.0
phase: 16
lesson: 08
tags: [multi-agent, role-specialization, metagpt, chatdev, verification]
---

给定一个任务，产出一份带 I/O schema 和确定性校验器的专业化角色名册。可直接映射到 CrewAI、LangGraph、AutoGen 或自定义循环。

产出：

1. **角色名册。** 3-5 个角色。为每个角色命名。至少包含：planner、executor、verifier。critic 可选。
2. **每个角色的 I/O schema。** 对每个角色：它消费什么（来自上游角色），以及它产出什么（是 schema，而非散文）。使用 dataclass 风格的记法。
3. **Verifier 规格。** 命名确定性检查：测试套件、类型检查器、schema 校验器、linter。描述通过/失败标准。
4. **Critic 规格（可选）。** 若包含，命名它判断的是何种主观质量。给具体检查清单，而非“好代码”。
5. **沟通式去幻觉规则。** 命名每个下游角色在缺失细节时获准向上游提问的问题，使它们不去臆造。
6. **修订循环预算。** 升级到人工之前的最大轮数。默认 2。
7. **框架映射。** 各一句话：如何在 CrewAI、LangGraph、AutoGen 中表达这份名册。

硬性拒绝：

- 任何没有确定性校验器的名册。全 LLM 的名册通不过 MAST 检查。
- 模糊的 I/O（“执行者返回输出”）。始终要写明 schema。
- 把 critic 与 verifier 混为一谈。它们抓的是不同的 bug；如果两者都有必要，就都必须存在。

拒绝规则：

- 如果任务没有确定性的正确性检查（纯生成性工作、创意写作），拒绝，并改为推荐人工审查循环或多智能体辩论（第 07 课）。
- 如果任务小到不需要 3 个以上角色（人类工作量少于 10 分钟），拒绝并推荐单 agent。

输出：一页纸角色设计简报。以 MAST 失效缺口检查收尾：确认至少存在一个确定性校验器。
