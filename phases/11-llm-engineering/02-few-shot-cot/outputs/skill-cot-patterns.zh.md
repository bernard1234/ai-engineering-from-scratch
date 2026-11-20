---
name: skill-cot-patterns
description: 根据任务复杂度、准确率要求和成本约束，选择合适推理技术的决策框架
version: 1.0.0
phase: 11
lesson: 02
tags: [chain-of-thought, few-shot, self-consistency, tree-of-thought, react, reasoning, prompting]
---

# 推理技术选择指南

当你需要让 LLM 推理一个问题时，先选技术，再写 prompt。技术决定推理架构。prompt 负责填充。

## 快速决策树

1. 任务是简单的事实查询或单步分类吗？
   - 是：用 **zero-shot**。CoT 只增加成本，不提升准确率。
   - 否：继续。

2. 任务需要多步推理（数学、逻辑、规划）吗？
   - 是：用 **Chain-of-Thought**。继续第 3 步。
   - 否：如果格式重要就用 **few-shot**，格式不重要就用 zero-shot。

3. 单个推理错误可以接受吗？
   - 可以：用 **few-shot CoT**（单样本，temperature 0.0）。
   - 不可以：用 **self-consistency**（N=5，temperature 0.7）。继续第 4 步。

4. 问题是存在大量可能路径的搜索/规划问题吗？
   - 是：用 **Tree-of-Thought**。
   - 否：self-consistency 就够了。

5. 任务需要外部信息或计算吗？
   - 是：用 **ReAct**（推理 + 工具调用）。
   - 否：纯推理技术就足够了。

## 技术矩阵

| 技术 | 准确率提升 | 成本倍数 | 延迟 | 最适合 |
|-----------|--------------|-----------------|---------|----------|
| Zero-shot | 基线 | 1x | ~1s | 简单任务、事实问答 |
| Few-shot | +5-15% | 1.2x | ~1s | 格式匹配、分类 |
| Zero-shot CoT | +10-20% | 1.3x | ~1.5s | 快速提升推理能力 |
| Few-shot CoT | +15-25% | 1.5x | ~2s | 数学、逻辑、多步任务 |
| Self-Consistency (N=5) | 相对 CoT +2-5% | 5x | ~5s | 高风险的推理 |
| Self-Consistency (N=10) | 相对 N=5 +1-2% | 10x | ~10s | 仅用于关键决策 |
| Tree-of-Thought | 取决于任务 | 10-40x | ~30s+ | 搜索、规划、谜题 |
| ReAct | 取决于任务 | 3-10x | ~5-15s | 需要知识支撑的任务 |
| Prompt Chaining | 相对单次调用 +5-10% | 2-5x | ~5-10s | 复杂多环节任务 |

## 模型特定指引

### GPT-4o / GPT-4.1
- 基线推理强。zero-shot CoT 通常就够了。
- 3 个示例的 few-shot CoT 在 GSM8K 上能达到 95%。
- self-consistency 带来的增益很小（95% 到 97%）——只有关键任务才值得用。
- 原生支持 structured outputs，便于抽取答案。

### Claude 3.5 Sonnet / Claude 3.7 Sonnet
- 非常擅长遵循结构化 prompt 格式（XML 标签）。
- 用 XML 分隔示例的 few-shot CoT 效果最好。
- extended thinking（Claude 3.7）本身就是原生 CoT——无需再提示它去做。
- self-consistency 有效，因为 Claude 在 temperature 0.7 下的推理路径多样性较好。

### Llama 3.1/3.3 70B
- 从 few-shot CoT 中获益最多（相对 zero-shot 的准确率差距更大）。
- 推理任务建议用 N=5 的 self-consistency。
- 比商用模型需要更显式的格式指令。
- ToT 在本地推理上很贵——只考虑用于批处理。

### Gemini 2.5 Pro
- 开箱即具备很强的多步推理能力。
- thinking 模式内置 CoT，无需 prompt engineering。
- few-shot 示例更多是帮助格式一致性，而非提升准确率。
- 大 context window（1M）让示例密集的 few-shot 变得实用。

## 反模式

**简单任务用 CoT**：问"2+2 等于几？让我们一步步思考"是在浪费 token。简单算术不需要推理过程模型也能算对。当有 3 步以上时 CoT 才有帮助。

**temperature 0.0 下用 self-consistency**：全部 N 个样本都会一模一样。你必须用 temperature > 0（建议 0.5-0.8）才能得到多样的推理路径。

**什么都用 ToT**：ToT 需要 O(b^d) 次 LLM 调用，其中 b=分支因子，d=深度。b=3、d=3 的树最多需要 39 次调用。留给那些更便宜的技术解决不了的问题。

**用坏示例做 few-shot**：含推理错误的示例会教模型犯这些错误。每个示例都必须验证过。一个错误示例造成的准确率损失，可能比零示例还大。

**答案抽取没有统一格式**：self-consistency 需要在样本之间比较答案。如果答案格式不统一（"$18"、"18 dollars"、"eighteen"），投票就会失败。始终强制："The answer is [number]."

## 成本优化

对于一个每天处理 10,000 次查询、按 GPT-4o 定价（输入 $2.50/1M，输出 $10/1M）的生产系统：

| 技术 | 平均 token/查询 | 每日成本 | 准确率 |
|-----------|-----------------|------------|----------|
| Zero-shot | ~200 | ~$5 | 78% |
| Few-shot CoT | ~600 | ~$15 | 95% |
| Self-Consistency (N=5) | ~3,000 | ~$75 | 97% |
| ToT (b=3, d=2) | ~6,000 | ~$150 | 取决于任务 |

对大多数应用而言的成本最优策略：从 few-shot CoT 开始。只对置信度低的查询追加 self-consistency（即"Build It"一节中的升级模式）。

## 与 prompt chaining 的结合

推理技术可以与 prompt chaining 组合：

**链步骤 1**（抽取）：zero-shot，temperature 0.0
**链步骤 2**（推理）：few-shot CoT，temperature 0.0
**链步骤 3**（验证）：N=3 的 self-consistency，temperature 0.7

这条三步链的成本约为单次 CoT 调用的 3 倍，但能捕获抽取错误和推理错误，并能从验证步骤得到置信度分数。

## 何时该超越 prompting

如果你花在 engineering prompt 上的时间已经超过写应用代码的时间，考虑：

1. **Fine-tuning**：如果你有 500 个以上标注示例，且任务范围狭窄
2. **DSPy 编译**：如果你想要自动化的 prompt 优化
3. **Agent 框架**：如果任务需要多轮工具使用（Phase 14）
4. **RAG**：如果模型需要访问私有/最新知识（Lessons 06-07）

prompting 技术是基础。它们适用于任何模型、任何 provider，且不需要训练数据。但它们有极限。知道何时升级到下一层，和掌握这些技术本身同样重要。
