# STaR、V-STaR、Quiet-STaR — 自学推理

> 最小的自我改进循环就藏在推理理由里。模型生成一条思维链，保留那些落在正确答案上的，然后在其上微调。这就是 STaR。V-STaR 增加一个 verifier，让推理时的选择更好。Quiet-STaR 把推理理由下推到每一个 token。三者都有效。它们也都不是魔法——循环会保留任何恰好触达正确答案的捷径。

**Type:** Learn
**Languages:** Python（stdlib，bootstrap 循环模拟器）
**Prerequisites:** 第 13 阶段，第 01–03 课（Reasoning and CoT）、第 15 阶段，第 01 课（long-horizon framing）
**Time:** ~60 分钟

## 问题场景

教模型推理最直接的办法是收集人类书写的推理轨迹。这既昂贵又缓慢，还受限于人类愿意写出多少高质量的思维链。

STaR（Self-Taught Reasoner，Zelikman 等，2022）提出：如果让模型自己写推理理由，并用已知答案给它们打分，会怎样？循环是：

1. 采样一条推理轨迹加答案。
2. 如果最终答案正确，保留该轨迹。
3. 在保留的轨迹上微调。
4. 重复。

它奏效了。GSM8K 和 CommonsenseQA 都在没有新增人工标注的情况下得到提升。但这个循环有内建偏差：任何得出正确答案的推理理由都会被保留，不管推理本身是否站得住。V-STaR（Hosseini 等，2024）用一个学习得到的 verifier 打了补丁；Quiet-STaR（Zelikman 等，2024）把这一想法推广到逐 token 的内部推理。

## 核心概念

### STaR：从做对的东西上自助

从一个具备一定弱推理能力的 base 模型出发。对每道训练题采样一条推理理由加答案。如果答案与标签一致，就保留这个（题目，推理理由，答案）三元组。在保留的集合上微调模型。重复。

有一个转折很重要。如果模型永远做不对某道题，循环就无法在它上面学习。STaR 加入了 **rationalization**：对模型做错的题，把正确答案作为提示注入，再重新 prompt 模型，让它产出通向该答案的推理理由。经过 rationalization 的推理理由会被加入训练集。

原始论文（Zelikman 等，2022）的结果：一个 GPT-J base 模型经过带 rationalization 的多轮 STaR，在 GSM8K 上从 5.8% 提升到 10.7%——绝对约 5 个百分点。在 CommonsenseQA 上，经 STaR 训练的 GPT-J 6B 达到 72.5%，与在人工标注推理理由上微调的 GPT-3 175B（约 73%）相当——后者大约大 30 倍。

### V-STaR：用 DPO 训练 verifier

STaR 会把错误的推理理由丢掉。Hosseini 等（2024）观察到这些同样是数据：每一对（推理理由，“是否正确”）都能训练一个 verifier。他们对正确和错误的解答一起使用 Direct Preference Optimization 来构建一个排序器。推理时采样 N 条推理理由，取 verifier 排序最高的那条。

报告中的提升：在 GSM8K 和 MATH 上比此前的自我改进基线高 4 到 17 个百分点，其中大部分收益来自用 verifier 做推理时选择，而不是用来进一步微调生成器。

### Quiet-STaR：逐 token 的内部推理

Zelikman 等（2024）提出：如果模型学会在每个 token 位置都生成一段简短的内部推理，而不仅仅在题目与答案之间，会怎样？Quiet-STaR 训练模型在预测每个 token 之前先发出一个隐藏的“thought”，再通过一个学习得到的权重，把带 thought 的预测与基线预测混合起来。

结果：Mistral 7B 在没有任务专属微调的情况下，GSM8K 的零样本成绩从 5.9% 绝对提升到 10.9%，CommonsenseQA 从 36.3% 提升到 47.2%。模型学会了“何时思考”——难的 token 会得到更长的内部推理，简单的几乎没有。

### 三者为何共有同一个安全隐忧

三种方法都用最终答案作为梯度信号。一条通过有缺陷的推理抵达正确答案的推理理由——利用捷径、靠猜、或使用无法泛化的模式——会得到正向强化。在同分布问题上，捷径有效。在分布外问题上，它会悄无声息地崩掉。

V-STaR 的 verifier 通过学习给推理理由排序来缓解这一点，但 verifier 是在同一套标签上训练的。它可能学会偏好格式漂亮但错误的推理，而不是诚实的不确定性。更安全的设计是把 STaR 式的数据与 (a) 过程监督的 reward model（奖励中间步骤，而不只是答案）以及 (b) 能打破简单捷径的留出 OOD eval 结合起来。

### 对比

| 方法 | 训练信号 | 推理成本 | 数据浪费 | 已知失败模式 |
|---|---|---|---|---|
| STaR | 正确则保留（推理理由，答案） | 1x | 丢弃所有错误推理理由 | 捷径式推理 |
| STaR + rationalization | 上述基础上加带正确答案提示的重试 | 1x | 较少 | rationalized 出的推理可能不合理 |
| V-STaR | STaR + 用两类样本训练的 DPO verifier | Nx（best-of-N） | 极少 | verifier 可能强化自信的错误 |
| Quiet-STaR | 逐 token 推理 + 混合权重 | 1.5–3x | 极少 | 仍是答案条件化的梯度 |

### 它在 2026 年技术栈中的位置

STaR 很老了。但这个模式在 2025–2026 年处处重现。可验证数学题上的 RL（DeepSeek-R1、Kimi-k1.5、o1）就是 STaR 的答案条件化梯度信号在更大规模上的版本。过程 reward model（Lightman 等，2023；OpenAI 的 "Let's verify step by step"）是过程监督的替代方案。AlphaEvolve（第 03 课）是面向代码的 STaR，用程序 evaluator 代替标签。Darwin Godel Machine（第 04 课）是面向 agent scaffold 本身的 STaR。

理解了 STaR，这些都会豁然开朗。它是最小可行的自我改进循环。

```figure
reflection-loop
```

## Use It

`code/main.py` 在一个玩具算术任务上运行模拟的 STaR 循环。你可以观察：

- 准确率如何在各轮自助中攀升。
- 捷径如何溜进来：模拟器包含一类“偷懒”的推理理由，它们有 40% 的概率得到正确答案，但泛化很差。观察 STaR 是否会保留它们。
- verifier（V-STaR 风格）如何在推理时帮忙，却无法完全剪除训练中引入的捷径。

## Ship It

`outputs/skill-star-loop-reviewer.md` 帮你在把算力投进去训练之前，审计一个拟议的自学推理流水线。

## Exercises

1. 运行模拟器。把捷径频率设为 0，再设为 0.4。尽管两次运行在训练分布上都超过 90%，最终准确率会相差多少？

2. 给模拟器加一个留出 OOD 测试。从不同分布抽取题目，在同分布和 OOD 两个集合上评估自助训练后的模型。量化差距。

3. 阅读 Quiet-STaR 论文（arXiv:2403.09629）第 3 节。分别用三句话解释 "end-of-thought" token 和混合权重头（mixing-weight head）。

4. 把 STaR 的“正确则保留”过滤器与一种过程监督的替代方案（对每个推理步骤独立给予奖励）作对比。指出标注成本差异和可能的质量差异。

5. 设计一个能捕捉已部署模型中捷径式推理理由的 eval。它不必完美——只要能打破 STaR 循环会强化的那些最简单捷径即可。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|---|---|---|
| STaR | “Self-Taught Reasoner” | 在模型生成的、能得到正确答案的推理理由上微调；重复 |
| Rationalization | “带提示重试” | 对 base 模型做错的题，注入正确答案并重新 prompt 让其给出推理理由 |
| V-STaR | “带 verifier 的 STaR” | 在正确与错误的推理理由上 DPO 训练 verifier，用于推理时选择 |
| Quiet-STaR | “逐 token 推理” | 在每个 token 位置生成隐藏 thought，并与基线预测混合 |
| 答案条件化梯度 | “基于结果的信号” | 训练循环奖励最终答案，而不是推理步骤 |
| 过程 reward model | “步骤级 verifier” | 按每步正确性而非结果训练的 reward model——与 STaR 形成对照 |
| 捷径式推理理由 | “答案对、推理错” | 通过无法泛化的模式触达标签的推理理由；STaR 会保留它们 |

## Further Reading

- [Zelikman et al. (2022). STaR: Bootstrapping Reasoning With Reasoning](https://arxiv.org/abs/2203.14465) — 原始论文。
- [Hosseini et al. (2024). V-STaR: Training Verifiers for Self-Taught Reasoners](https://arxiv.org/abs/2402.06457) — 增加 DPO verifier 用于推理时选择。
- [Zelikman et al. (2024). Quiet-STaR: Language Models Can Teach Themselves to Think Before Speaking](https://arxiv.org/abs/2403.09629) — 逐 token 的内部推理。
- [Lightman et al. (2023). Let's Verify Step by Step](https://arxiv.org/abs/2305.20050) — 过程 reward model，另一种梯度信号。
- [DeepSeek-R1 paper (arXiv:2501.12948)](https://arxiv.org/abs/2501.12948) — 可验证任务上的 RL，STaR 扩展到前沿训练规模。
