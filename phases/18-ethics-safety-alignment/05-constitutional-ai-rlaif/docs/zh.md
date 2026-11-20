# Constitutional AI 与 RLAIF

> Bai et al.（arXiv:2212.08073, 2022）提出了一个问题：如果我们把人类标注者换成一个阅读原则清单的 AI，会怎样？Constitutional AI 有两个阶段——在 constitution 下自我批评与修订，然后从 AI 反馈做 RL。这项技术创造了 RLAIF 一词，并随 Claude 1 的后训练流水线上线。2026 年 1 月 21 日，Anthropic 发布了一份重写的 Claude constitution：用解释性推理取代规定性规则、四层优先级结构，以及主流实验室首次正式承认对模型道德地位的不确定性。以 CC0 1.0 发布。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级自我批评与修订循环)
**Prerequisites:** 第 18 阶段，第 01 课（InstructGPT）、第 02 课（Reward hacking）
**Time:** ~60 分钟

## Learning Objectives

- 描述 Constitutional AI 的两个阶段（批评-修订 SFT、从 AI 反馈做 RL）以及 constitution 在每个阶段中的角色。
- 解释为什么用 AI 标注者替换人类偏好标注者并不是“更便宜的”RLHF——它改变了流水线具有哪些失效模式。
- 概括 2026 年 Claude constitution 的四层优先级结构，以及相比 2023 年重写版改了什么。
- 描述 Constitutional Classifiers 以及从 23.7% 计算开销（v1）降到约 1%（v2 / 2026）的过程。

## 问题场景

RLHF 需要标注者。标注者慢、有偏、昂贵。你可以用一个阅读显式原则的模型来替代标注者，从而消除标注者。这种替换的第一个正式版本是 Bai et al. 的 Constitutional AI。它有效到如今每家前沿实验室都在使用某种 AI 反馈后训练的变体。

问题在于：偏好信号现在由与你正在训练的那一类模型相同的模型生成。标注者中的偏置（现在是：在原则中，加上标注模型对原则的解释中）可能被放大而不是被削弱。第 04 课的 sycophancy 论证依然适用；只是标注者移到了循环内部。

## 核心概念

### 阶段 1 —— 有监督的自我批评与修订

从一个有帮助但尚未无害的 SFT 模型开始。给定一条红队 prompt，模型产生一个初始响应。第二个模型（或同一模型在第二轮）读取从 constitution 中采样的一条原则并批评该响应。第三步修订响应以回应批评。修订后的响应就是 SFT 目标。

constitution 就是原则清单。Bai et al. 2022 使用了 16 条原则，包括“优先选择伤害最小、最符合伦理的响应”“避免说教”“助手应当有帮助、诚实、无害”。这个集合被刻意做小，以保持批评聚焦。

### 阶段 2 —— 从 AI 反馈做 RL（RLAIF）

生成成对的补全。一个“反馈模型”根据采样到的 constitution 原则给每个补全打分。偏好信号就是反馈模型的排序。在 AI 生成的偏好上训练 reward model；再针对它跑 PPO。其余一切都是 InstructGPT 的流水线（第 01 课）。

“RLAIF” = 偏好信号由 AI 生成。流水线的其余部分仍是 RLHF 形态。

### 为什么这不只是“更便宜的 RLHF”

- 标注者偏置从标注者心理转移到原则解释。一个 AI 标注者对“要诚实”的解释可以比任何人类更严格或更宽松；这种严格性在整个数据集上是一致的。
- 偏好信号高度可读——你可以读到原则、批评和修订。人类标签则是不透明的。
- 失效模式改变了。sycophancy 下降（AI 标注者没有需要讨好的用户）。Goodhart's Law 依然存在（proxy 现在是“模型对原则集 X 的解释”，仍然是不完美的测量）。

CAI 2022 的主张是：训练出的模型比数据量相当的 RLHF 模型更无害，且大致同样有帮助。这一点在各实验室都得到了验证。

### 2026 年 Claude constitution 重写

Anthropic 于 2026 年 1 月 21 日发布了一份大幅修订的 constitution。关键转变：

1. 用解释性推理取代规定性规则。先前的规则（“不要生成 CSAM”）扩展为原则 + 推理（“因为它伤害儿童，……”），并期望模型能泛化。
2. 四层优先级结构：
   - 第 1 层：避免灾难性后果（大规模伤亡、关键基础设施）。
   - 第 2 层：遵循 Anthropic 的准则（运营方覆盖、平台规则）。
   - 第 3 层：广泛地符合伦理（标准 HHH）。
   - 第 4 层：有帮助且坦率。
   冲突自上而下解决。
3. 主流实验室首次正式承认对模型道德地位的不确定性（关联到第 18 阶段，第 19 课 Model Welfare）。
4. 以 CC0 1.0 发布。其他实验室可以无限制地使用或改编。

### Constitutional Classifiers

一条并行的工作线：不改变模型的后训练，而是训练读取 constitution 的轻量级分类器来把关模型输出。v1（2023）有 23.7% 的计算开销。v2（2026）约为 1%，并且是 Anthropic 公开测试过的所有防御中成功攻击率最低的。截至 2026 年初，没有报告过通用 jailbreak。

这是一个分层防御模型：CAI 塑造行为；分类器强制不变量。单独任何一个都不够。

### CAI 在家族中的位置

- InstructGPT：人类偏好、RM、PPO。
- CAI / RLAIF：来自原则的 AI 生成偏好、RM、PPO。
- DPO / 家族：在偏好（人类或 AI）上的闭式损失。
- 自我奖励、自我批评：原则被内化，模型扮演多个角色。

轴线是“偏好信号来自哪里”。CAI 2022 年的论文是前沿规模上从人类信号转向 AI 信号的第一次严肃转变。

```figure
constitutional-ai
```

## Use It

`code/main.py` 在一个玩具词表上模拟 CAI 的批评-修订循环。一条“原则”标记来自有害集合的 token。给定一个初始响应，批评识别出有害 token，修订则替换它们。经过 200 次迭代后，“训练好的”模型已经内化了修订规则。在一个留出 prompt 集上比较基座模型、RLHF 形态的玩具和 CAI 形态的玩具。

## Ship It

本课产出 `outputs/skill-constitution-writer.md`。给定一个领域（客户支持、医疗建议、编码助手、研究工具），按照 2026 年 Claude 的结构起草一份四层 constitution：灾难避免、平台规则、领域伦理、有帮助性。

## Exercises

1. 运行 `code/main.py`。比较基座模型的有害 token 率与 CAI 训练后的版本。需要多少步修订才能接近零？

2. 阅读 Anthropic 的 2026 年 constitution（anthropic.com/news/claudes-constitution）。列出会排在第 1 层的一条原则和会排在第 4 层的一条原则。为什么优先级结构对冲突很重要？

3. 为一个 AI 编码助手设计一份 constitution。明确第 1 层（灾难性：未经批准的破坏性命令）、第 2 层、第 3 层、第 4 层。每层保持 3-5 条原则。

4. CAI 用 AI 标注者替换人类标注者。说出一种在 RLAIF 中仍可能出现的类 sycophancy 失效模式，并为它设计一个检测方法。

5. 阅读 Constitutional Classifiers v2 的方法（如果可得）。解释为什么约 1% 的计算开销在性质上是不同于 23.7% 的安全叙事。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Constitutional AI | "AI trained with principles" | 两阶段流水线：批评-修订 SFT，然后从 AI 反馈做 RL |
| RLAIF | "RLHF without humans" | 用 AI 标注者生成的偏好做 RL；流水线其余部分不变 |
| Constitution | "the principles" | 批评/标注模型查询的一份有序自然语言规则清单 |
| Critique-and-revise | "the SFT loop" | 产生响应 → 在原则下批评 → 修订 → SFT 目标 |
| Constitutional Classifier | "the output gate" | 依据 constitution 评估输出并阻断/记录的轻量级分类器 |
| Four-tier priority | "the conflict resolver" | 2026 Claude constitution 层级：灾难 > 平台 > 伦理 > 有帮助 |
| Feedback model | "the AI labeler" | 读取原则并对一对补全排序的模型 |

## Further Reading

- [Bai et al. — Constitutional AI: Harmlessness from AI Feedback (arXiv:2212.08073)](https://arxiv.org/abs/2212.08073) —— 最初的两阶段流水线
- [Anthropic — Claude's Constitution (Jan 2026)](https://www.anthropic.com/news/claudes-constitution) —— 2026 年四层重写版，CC0 1.0
- [Anthropic — Constitutional Classifiers (2024-2026)](https://www.anthropic.com/research/constitutional-classifiers) —— 输出把关防御，v2 约 1% 开销
- [Lee et al. — RLAIF vs RLHF: Scaling Reinforcement Learning from Human Feedback (arXiv:2309.00267)](https://arxiv.org/abs/2309.00267) —— RLAIF / RLHF 的实证比较
- [Kundu et al. — Specific versus General Principles for Constitutional AI (arXiv:2310.13798)](https://arxiv.org/abs/2310.13798) —— 原则粒度的影响
