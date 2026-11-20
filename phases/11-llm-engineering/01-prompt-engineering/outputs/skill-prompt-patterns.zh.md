---
name: skill-prompt-patterns
description: 根据任务类型、可靠性要求和目标模型，选择合适 prompt 模式的决策框架
version: 1.0.0
phase: 11
lesson: 01
tags: [prompt-engineering, patterns, llm, temperature, cross-model, few-shot, chain-of-thought]
---

# Prompt 模式选择指南

构建 LLM 驱动的功能时，先选 prompt 模式，再写 prompt。模式决定结构。内容负责填充。

## 模式决策矩阵

| 任务类型 | 主模式 | 辅助模式 | Temperature | 是否需要 few-shot？ |
|-----------|----------------|-------------------|-------------|-----------------|
| 数据抽取 | Template Fill | Few-Shot | 0.0 | 需要（2-3 个示例） |
| 分类 | Few-Shot | Guardrail | 0.0 | 需要（3-5 个示例） |
| 摘要 | Persona + Template | Audience Adapt | 0.3 | 不需要 |
| 代码生成 | Persona | Chain-of-Thought | 0.0 | 可选 |
| 创意写作 | Persona | Critique | 0.7-1.0 | 不需要 |
| 多步推理 | Chain-of-Thought | Decomposition | 0.3 | 可选 |
| 问答 | Persona + Guardrail | Boundary | 0.3 | 不需要 |
| Prompt 生成 | Meta-Prompt | Critique | 0.7 | 需要（1-2 个示例） |
| 内容审核 | Guardrail + Boundary | Few-Shot | 0.0 | 需要（5 个以上示例） |
| 翻译/改编 | Audience Adapt | Few-Shot | 0.3 | 需要（2-3 个示例） |

## 各模式的适用场景

**Persona 模式**：作为基线用于每一个 prompt。唯一的问题是角色要写得多具体。通用任务用宽泛角色就够了。领域特定任务，角色应点名领域、资历层级和背景。

**Few-Shot 模式**：当输出格式比内容更重要时使用。如果模型需要产出特定 JSON 形状、CSV 格式或分类标签，示例比指令更有效。经验法则：简单格式用 2-3 个示例，复杂或有歧义的格式用 5 个以上。

**Chain-of-Thought 模式**：用于数学、逻辑、多步分析，以及任何需要模型"展示过程"的任务。在推理任务上把准确率提升 10-40%（Wei et al., 2022）。不要用于简单的事实查询或抽取——那会浪费 token。

**Template Fill 模式**：用于结构化抽取，且每个输出必须具有相同形状的场合。在 temperature=0.0 且对缺失字段显式处理 "N/A" 时效果最好。

**Critique 模式**：当质量比速度更重要时使用。模型先生成、再批判、然后改进。token 成本大约翻倍，但显著提升准确率和完整度。最适合高风险输出（报告、建议、面向公众的内容）。

**Guardrail 模式**：用于任何面向用户的系统。始终包含：范围边界、对越界请求的拒答行为、以及显式的"我不知道"处理。在应用侧配合输入校验一起使用。

**Meta-Prompt 模式**：用于为新任务生成 prompt。与其从零写 prompt，不如描述任务，让模型来写 prompt。然后测试并迭代。可节省初始 prompt 开发的时间。

**Decomposition 模式**：用于适合分而治之的复杂问题。模型把问题拆成若干部分，逐个求解，再合并。对含 3-7 个子问题的任务最有效。

**Audience Adapt 模式**：当同一份内容需要服务不同受众时使用。要显式指定受众——不要指望模型从上下文里去猜。

**Boundary 模式**：用于必须绝不对某类问题作答的生产系统。它比 guardrail 更强，因为它用一个精确的拒答消息定义了硬边界。对合规敏感的领域必不可少。

## 跨模型兼容性

以下模式按其在 GPT-4o、Claude 3.5 Sonnet、Gemini 1.5 Pro 和 Llama 3 上表现的一致性排序：

| 模式 | 跨模型一致性 | 说明 |
|---------|------------------------|-------|
| Few-Shot | 很高 | 示例在各模型间迁移效果好 |
| Template Fill | 很高 | 显式结构几乎不留偏离空间 |
| Chain-of-Thought | 高 | 所有主流模型都支持"think step by step" |
| Persona | 高 | 到处都能用，但不同模型对角色具体程度的要求不同 |
| Guardrail | 中等 | Claude 最严格地遵循 guardrail；GPT-4o 在长对话中有时会漂移 |
| Critique | 中等 | 自我批判的质量因模型差异明显 |
| Meta-Prompt | 中等 | GPT-4o 与 Claude 产出的 prompt 风格不同 |
| Boundary | 低-中等 | 拒答行为各不相同；需逐模型测试 |

## 常见错误

1. **什么任务都用 Chain-of-Thought**：CoT 会增加 token 和延迟。只在确实需要推理步骤时使用。
2. **约束太多**：超过 5-7 条约束，模型就开始丢掉其中一些。优先保留最重要的 3 条。
3. **Persona 与约束相互矛盾**："你是一位创意作家" + "绝不使用隐喻" 会让模型困惑。
4. **不指定 temperature**：需要确定性输出时，却把 temperature 留在默认值（通常是 1.0）。
5. **把 prompt 跨模型复制粘贴**：始终要测试。为 GPT-4o 调优的 prompt 在 Claude 上可能表现更差，反之亦然。
6. **忽视 system message**：把所有内容都塞进 user message，而不是用 system message 承载持久规则。
7. **过度依赖否定式约束**："不要做 X、Y、Z、A、B、C" 不如"只做 W"有效。正向表述给模型一个清晰的目标。

## 可靠性目标

| 用例 | 模式组合 | 预期准确率 | token 成本 |
|----------|-------------------|-------------------|------------|
| 生产抽取 | Template + Few-Shot | 95%+ | 低（500-1K） |
| 面向用户的问答 | Persona + Guardrail + Boundary | 90%+ | 中（1-2K） |
| 代码生成 | Persona + Chain-of-Thought | 85%+ | 中（1-3K） |
| 内容生成 | Persona + Critique | 90%+ 质量 | 高（2-4K，两轮） |
| 分类 | Few-Shot + Guardrail | 95%+ | 低（300-800） |
| 复杂分析 | Decomposition + Chain-of-Thought | 85%+ | 高（3-5K） |
