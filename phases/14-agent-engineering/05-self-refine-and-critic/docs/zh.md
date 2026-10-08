# Self-Refine 与 CRITIC：迭代式输出改进

> Self-Refine（Madaan 等人，2023）在循环中用同一个 LLM 扮演三个角色——generate、feedback、refine。平均收益：7 个任务上 +20 绝对分。CRITIC（Gou 等人，2023）把反馈步骤加固，将验证路由经过外部工具。2026 年，这个模式以「evaluator-optimizer」（Anthropic）或 guardrail 循环（OpenAI Agents SDK）的形式出现在每个框架里。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 03 (Reflexion)
**Time:** ~60 minutes

## 学习目标

- 陈述 Self-Refine 的三个提示词（generate、feedback、refine），并解释为什么 history 对 refine 提示词至关重要。
- 解释 CRITIC 的关键洞见：没有外部锚定的 LLM 在自我验证上是不可靠的。
- 用标准库实现一个带 history 和可选外部验证器的 Self-Refine 循环。
- 把这个模式映射到 Anthropic 的「evaluator-optimizer」工作流和 OpenAI Agents SDK 的 output guardrails。

## 问题

一个智能体产出了一个几乎正确的答案。也许某行代码有语法错误。也许摘要太长。也许计划漏了一个边界情况。你想要的是：智能体批判自己的输出，然后修复它。

Self-Refine 表明这可以用单一模型做到，无需训练数据、无需 RL。但有一个陷阱：LLM 在硬事实上的自我验证很糟糕。CRITIC 点明了修复方式——把 verify 步骤路由经过外部工具（搜索、代码解释器、计算器、测试运行器）。

这两篇论文共同定义了 2026 年迭代式改进的默认做法：生成、验证（可能时用外部方式）、改进、验证器通过时停止。

## 概念

### Self-Refine（Madaan 等人，NeurIPS 2023）

一个 LLM，三个角色：

```
generate(task)            -> output_0
feedback(task, output_0)  -> critique_0
refine(task, output_0, critique_0, history) -> output_1
feedback(task, output_1)  -> critique_1
refine(task, output_1, critique_1, history) -> output_2
...
stop when feedback says "no issues" or budget exhausted.
```

关键细节：`refine` 看到完整 history——所有先前的输出和批判——这样它就不会重复犯错。论文做了消融：去掉 history，质量急剧下降。

头条数字：在 7 个任务（数学、代码、缩写、对话）上平均 +20 绝对分，包括 GPT-4。无训练、无外部工具、单一模型。

### CRITIC（Gou 等人，arXiv:2305.11738，v4 2024 年 2 月）

Self-Refine 的弱点：反馈步骤是一个 LLM 在给自己打分。对于事实性断言这是不可靠的（幻觉在产出它的模型眼里往往很有说服力）。CRITIC 把 `feedback(task, output)` 替换成 `verify(task, output, tools)`，其中 `tools` 包括：

- 一个用于事实性断言的搜索引擎。
- 一个用于代码正确性的代码解释器。
- 一个用于算术的计算器。
- 领域特定的验证器（单元测试、类型检查器、linter）。

验证器产出一份锚定在工具结果上的结构化批判。refiner 随后以这份批判为条件。

头条数字：CRITIC 在事实性任务上胜过 Self-Refine，因为批判是有锚定的。在没有外部验证器的任务上（创意写作、格式调整），CRITIC 退化为 Self-Refine。

### 停止条件

两种常见形态：

1. **验证器通过。** 外部测试返回成功。可用时优先（单元测试、类型检查器、guardrail 断言）。
2. **没有发出反馈。** 模型说「输出没问题」。更便宜但不可靠；搭配一个最大迭代上限。

2026 年的默认做法：把它们结合起来。「如果验证器通过，或（模型说没问题且迭代 >= 2），或迭代 >= max_iterations，就停止。」

### Evaluator-Optimizer（Anthropic，2024）

Anthropic 2024 年 12 月的帖子把这一模式列为五种工作流模式之一。两个角色：

- Evaluator：给输出打分并产出一份批判。
- Optimizer：根据批判修订输出。

循环直到 evaluator 通过。这就是 Anthropic 框架下的 Self-Refine/CRITIC。Anthropic 补充的关键工程细节：evaluator 和 optimizer 的提示词应当明显不同，这样模型才不会只是盖章通过。

### OpenAI Agents SDK 的 output guardrails

OpenAI Agents SDK 以「output guardrails」的形式发布这个模式。guardrail 是一个运行在智能体最终输出上的验证器。如果 guardrail 触发（抛出 `OutputGuardrailTripwireTriggered`），输出被拒绝，智能体可以重试。guardrail 可以调用工具（CRITIC 式），也可以是纯函数（Self-Refine 式）。

### 2026 年的坑

- **盖章循环。** 同一个模型用同一种提示词风格做生成和批判，会收敛到「我觉得挺好」。使用结构上不同的提示词，或用一个更小、更便宜的模型来做批判。
- **过度改进。** 每一轮 refine 都增加延迟和 token。预算 1–3 轮；之后升级到人工审查。
- **在琐碎任务上用 CRITIC。** 如果没有外部验证器，CRITIC 退化为 Self-Refine；别为一个桩验证器付出延迟代价。

```figure
self-refine
```

## Build It

`code/main.py` 在一个玩具任务上实现 Self-Refine 和 CRITIC：给定一个主题，产出一个简短的 bullet 列表。验证器检查格式（3 个 bullet，每个 60 字符以内）。CRITIC 增加一个外部「事实验证器」，惩罚已知的幻觉。

组成部分：

- `generate` —— 脚本化产出器。
- `feedback` —— LLM 式自我批判。
- `verify_external` —— CRITIC 式有锚定的验证器。
- `refine` —— 给定 history 重写输出。
- 停止条件 —— 验证器通过或最多 4 次迭代。

运行它：

```
python3 code/main.py
```

对比 Self-Refine 与 CRITIC 的运行。CRITIC 抓住了 Self-Refine 漏掉的一个事实错误，因为外部验证器有自我批判所没有的锚定。

## Use It

Anthropic 的 evaluator-optimizer 就是这套模式在 Claude 友好语言下的说法。OpenAI Agents SDK 的 output guardrails 是 CRITIC 形态的（guardrail 可以调用工具）。LangGraph 发布了一个读起来像 Self-Refine 的 reflection 节点。Google 的 Gemini 2.5 Computer Use 加了一个逐步安全评估器，它是 CRITIC 的一个变体：每一个动作在提交前都要被验证。

## Ship It

`outputs/skill-refine-loop.md` 给定任务形态、验证器可用性和迭代预算，配置一个 evaluator-optimizer 循环。产出 generator、evaluator/verifier 和 optimizer 的提示词，外加一个停止策略。

## 练习

1. 用 max_iterations=1 跑玩具。CRITIC 还有帮助吗？
2. 把外部验证器换成一个有噪声的（随机 30% 误报）。循环会怎么做？这就是 2026 年大多数 guardrail 技术栈的现实。
3. 实现一个「不同模型上的 generator-critic」变体：大模型生成，小模型批判。它胜过同模型吗？
4. 读 CRITIC 第 3 节（arXiv:2305.11738 v4）。说出三类验证工具类别，并为每类各举一个例子。
5. 把 OpenAI Agents SDK 的 `output_guardrails` 映射到 CRITIC 的 verifier 角色。SDK 哪里做错了，哪里做对了？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------|------------------|
| Self-Refine | 「会自我修复的 LLM」 | 在一个模型里做 generate -> feedback -> refine 循环，带 history |
| CRITIC | 「基于工具的验证」 | 用外部验证器（搜索、代码、计算、测试）替换 feedback |
| Evaluator-Optimizer | 「Anthropic 工作流模式」 | 两个角色——evaluator 打分、optimizer 修订——循环到收敛 |
| Output guardrail | 「事后检查」 | OpenAI Agents SDK 在智能体产出输出后运行的验证器 |
| Verify step | 「批判阶段」 | 承重的决策：有锚定还是自我打分 |
| Refine history | 「模型已经试过的」 | 前置到 refine 提示词里的先前输出 + 批判；去掉它质量就崩塌 |
| Rubber-stamp loop | 「自我认同失败」 | 同提示词的批判返回「看起来不错」；用结构上不同的提示词修复 |
| Stop condition | 「收敛测试」 | 验证器通过，或（无反馈且达到迭代上限）；绝不用单一条件 |

## 延伸阅读

- [Madaan 等人，Self-Refine（arXiv:2303.17651）](https://arxiv.org/abs/2303.17651)——经典原论文
- [Gou 等人，CRITIC（arXiv:2305.11738）](https://arxiv.org/abs/2305.11738)——基于工具的验证
- [Anthropic，Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)——evaluator-optimizer 工作流模式
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)——作为 CRITIC 形态验证器的 output guardrails
