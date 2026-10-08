---
name: refine-loop
description: 给定任务、验证器可用性和迭代预算，配置一个 evaluator-optimizer（Self-Refine / CRITIC）循环。
version: 1.0.0
phase: 14
lesson: 05
tags: [self-refine, critic, evaluator-optimizer, guardrails, iteration]
---

给定任务、迭代预算和可用的验证器（工具锚定或仅自评），为 evaluator-optimizer 循环产出 prompts 和停止策略。

产出：

1. 生成器 prompt。首个输出的确定性生产者。明确陈述任务、输出格式和约束。
2. 评估器/验证器 prompt。如果有工具可用（搜索、代码运行、测试、计算器、类型检查），指定如何调用它们以及如何产出结构化批评（JSON 含：pass/fail、violations[]、suggested_fixes[]）。如果只有自评可用，明确标注 Self-Refine 的「橡皮图章」风险，并使用结构上不同的 prompt 风格（例如对抗式的「至少找出一个缺陷」）。
3. 精炼器 prompt。必须引用先前的输出和批评（历史）。声明「不得重复先前迭代中已标记的失败模式」是强制的。
4. 停止策略。合取式：验证器通过 OR（自评说没问题 AND 迭代数 >= 2）OR 迭代数 >= max_iterations。绝不单条件。
5. 可观测性钩子。按 Lesson 23 把每次迭代记录为 OpenTelemetry GenAI span（evaluate、optimize），使完整 refine 轨迹可审计。

硬拒绝：

- 生成器和 critic 用同一个 prompt。橡皮图章风险——模型只会自我附和。
- 没有迭代上限。无限 refine 循环烧 token；默认始终设上限为 4。
- 请求自由文本散文反馈的验证器 prompt。只用结构化 JSON——pass/fail 加逐项 violations。
- 从精炼器 prompt 中丢掉历史。论文表明没有它质量会崩塌。

拒绝规则：

- 如果任务没有验证器且无法构建，拒绝 CRITIC 并说明 Self-Refine 是可用的较弱选项——警告用户橡皮图章风险。
- 如果 max_iterations >= 10，拒绝并建议重新架构任务。超过 3-4 轮才收敛通常是生成器 prompt 有问题的信号。
- 如果验证器调用破坏性工具（shell、git write），拒绝并要求沙箱边界（Lesson 09）。

输出：一个包含所有 prompts、停止策略和工具列表的单一配置块，外加「what to read next」说明，按部署目标指向 Lesson 16（OpenAI Agents SDK guardrails）、Lesson 12（Anthropic evaluator-optimizer）或 Lesson 30（eval-driven agent development）。