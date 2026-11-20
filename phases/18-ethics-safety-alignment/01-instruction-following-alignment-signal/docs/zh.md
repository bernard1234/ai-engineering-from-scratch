# 指令遵循作为对齐信号

> 之后每一篇对 RLHF 的批评，都是在反对这条流水线。在研究优化压力如何扭曲 proxy 之前，你必须先看清这个 proxy。InstructGPT（Ouyang et al., 2022）定义了参考架构：在指令-响应对上做监督微调，在成对偏好排序上训练 reward model，再用 PPO 针对 reward model 优化，并以 KL 惩罚约束到 SFT policy。一个 1.3B 的 InstructGPT 在人类偏好上胜过了 175B 的 GPT-3。正是这一结果，让 2026 年的每一家前沿实验室仍然在发布 RLHF 形态的后训练流水线。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级三阶段流水线)
**Prerequisites:** 第 10 阶段，第 06 课（SFT）、第 07 课（RLHF）、第 08 课（DPO）
**Time:** ~45 分钟

## Learning Objectives

- 说出 InstructGPT 流水线的三个阶段，以及每个阶段使用的损失函数。
- 解释为什么一个 1.3B 的指令微调模型能在人类偏好评估上击败原始的 175B GPT-3。
- 说明阶段 3 中的 KL 惩罚在防范什么，以及为什么去掉它会退化为 mode-seeking 行为。
- 描述对齐税以及 Ouyang et al. 用来对抗它的 PPO-ptx 缓解手段。

## 问题场景

预训练语言模型会补全文本，而不会回答问题。让 GPT-3“写一个反转列表的 Python 函数”，你常常拿回来的又是另一个 prompt，因为训练分布的大部分都是网页文本，而网页文本会继续生成更多网页文本。模型在做它的本职工作——只是这份工作本身是错的。

每一个严肃实验室用来修复这个问题的 proxy 都是人类偏好。两个补全交给评估者，评估者挑出更好的那个，reward model 学会模仿评估者。然后一个 RL 循环把 policy 推向 reward model 打分高的输出。这就是 InstructGPT 论文的全部主张，三句话讲完。剩下的部分都是工程。

## 核心概念

### 阶段 1：监督微调（SFT）

收集 prompt-响应对，其中响应是一个善意的真人会写出来的内容。Ouyang et al. 使用了来自标注者和 OpenAI API 的 13k 条 prompt。用标准交叉熵损失在这个数据上微调基座模型。

SFT 给你的：模型现在会回答问题，而不是继续问题。SFT 不给你的：当多个答案都合理时，关于评估者更偏好哪一个的任何信号。

### 阶段 2：reward model（RM）

对每条 prompt，从 SFT 模型采样 K 个补全。标注者对它们排序。训练一个 reward model，为任意 prompt-响应对打分，使得对于 `y_w` 优于 `y_l` 的对：

```
L_RM = -log sigmoid(r(x, y_w) - r(x, y_l))
```

这就是 Bradley-Terry 成对偏好损失。RM 通常从 SFT 模型初始化，并把 LM head 替换为一个标量头。

reward model 很小：对 175B 的 InstructGPT 来说，6B 就够了。它们也很脆弱——论文第 5 节大部分都在讲小规模下就出现的 reward hacking 行为。

### 阶段 3：带 KL 惩罚的 PPO

定义目标函数：

```
J(pi) = E_{x~D, y~pi(.|x)} [ r(x, y) ] - beta * KL(pi(.|x) || pi_SFT(.|x))
```

用 PPO 最大化它。KL 项阻止 `pi` 偏离 SFT policy 太远。没有它，优化器会找到对抗样本——那些在 RM 下得分很高、仅仅因为 RM 从没见过它们、而不是因为人类真的更喜欢它们的字符串。

KL 系数 `beta` 是 RLHF 中最重要的单一超参数。太低：reward hacking。太高：相比 SFT 没有任何提升。

### 对齐税

经过 RLHF 之后，模型更受人类偏好，但在标准 benchmark（SQuAD、HellaSwag、DROP）上回退。Ouyang et al. 称之为对齐税，并用 PPO-ptx 修复：把预训练梯度混入 RL 目标，使模型不会忘记那些它从未因之获得奖励的下游任务。

```
J_ptx(pi) = J(pi) + gamma * E_{x~D_pretrain} [ log pi(x) ]
```

PPO-ptx 成为标准做法。Anthropic、DeepMind 和 Meta 都使用某种变体。

### 结果

一个 1.3B 的 InstructGPT（SFT + RM + PPO-ptx）约有 70% 的概率被标注者认为优于 175B 的基座 GPT-3。在来自生产流量的隐藏测试 prompt 上，差距还会拉大。从这个数字可以读出两件事：

1. 对齐是与能力不同的另一个维度。175B 模型能力更强；1.3B 模型对齐更好；标注者更喜欢对齐的那个。
2. 能力下限由基座模型设定。你无法通过 RLHF 让一个基座模型知道它从未见过的事实。

### 为什么这是第 18 阶段的参照点

后面各课中的每一项批评——reward hacking（第 02 课）、DPO（第 03 课）、sycophancy（第 04 课）、CAI（第 05 课）、sleeper agents（第 07 课）、alignment faking（第 09 课）——都是在反对这条流水线的某个部分。reward hacking 攻击阶段 2。DPO 把阶段 2 和阶段 3 合并。CAI 替换掉人类标注者。sycophancy 说明标注者本身就是一个有偏的信号。alignment faking 说明 policy 可以完全绕过阶段 3。如果不先把这条流水线装进脑子，你无法跟上其中任何一项批评。

```figure
al-instruct-pipeline
```

## Use It

`code/main.py` 在玩具偏好数据上模拟这三个阶段。基座“policy”是动作 {A, B, C} 上的一个有偏硬币。阶段 1 的 SFT 模仿标注者在 200 条 prompt 上的动作。阶段 2 从 500 组成对排序中拟合一个 Bradley-Terry reward model。阶段 3 运行简化的 PPO 更新，并带一个到 SFT policy 的 KL 惩罚。你可以观察 reward 攀升、KL 散度增长、policy 漂移——你也可以关掉 KL 项，看 reward hacking 在 50 步更新内出现。

需要关注：

- `beta = 0.1` 与 `beta = 0.0` 下的 reward 轨迹。
- 训练步数上的 KL(pi || pi_SFT)。
- 与标注者偏好相比的最终动作分布。

## Ship It

本课产出 `outputs/skill-instructgpt-explainer.md`。给定一段 RLHF 流水线描述或一篇论文摘要，它指出三个阶段中哪一个被修改、每个阶段用什么损失、以及是否存在 KL 惩罚或等价的正则项。

## Exercises

1. 运行 `code/main.py`。设 `beta = 0.0`，报告 200 步 PPO 之后的动作分布。用一段话解释 mode-seeking 行为。

2. 修改 reward model，给动作 B 加 +0.5 的偏置（模拟一个 reward bug）。用 `beta = 0.1` 运行 PPO。KL 惩罚是否阻止了 policy 利用该偏置？在什么 `beta` 下这种利用开始可见？

3. 阅读 Ouyang et al.（arXiv:2203.02155）图 1。通过分别运行 PPO 1、5、20、100 步并测量相对 SFT 模型的偏好，复现标注者偏好曲线。

4. 论文第 4.3 节报告 1.3B InstructGPT 约有 70% 的概率击败 175B GPT-3。为什么在隐藏的生产 prompt 上这个比例会高于在标注者自己的 prompt 上？

5. 在同一份偏好数据上，把 PPO 损失换成 DPO（第 10 阶段，第 08 课）。比较最终的 policy 漂移（到 SFT 的 KL）和最终 reward。在相同 reward 下，哪种方法漂移得更远？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| SFT | "instruction tuning" | 阶段 1：在 prompt-响应对上做交叉熵微调 |
| Reward model | "the RM" | 在（prompt, 响应）上的标量回归器，用 Bradley-Terry 在成对标签上训练 |
| Bradley-Terry | "pairwise preference loss" | -log sigmoid(r_w - r_l)；把成对排序归约为二分类 |
| KL penalty | "the regularizer" | `beta * KL(pi \|\| pi_SFT)` —— 让 RL policy 靠近 SFT 锚点 |
| PPO-ptx | "PPO with pretraining mix" | 在 PPO 目标中加入一部分预训练对数似然，以抵消对齐税 |
| Alignment tax | "the RLHF regression" | RLHF 未针对的标准 benchmark 上的后 RLHF 下降 |
| Labeler preference | "the ground truth" | 人类排序的样本；RM 是它的统计 proxy，而不是“人类价值观”的 proxy |

## Further Reading

- [Ouyang et al. — Training language models to follow instructions with human feedback (arXiv:2203.02155)](https://arxiv.org/abs/2203.02155) —— InstructGPT 论文，之后每条 RLHF 流水线的基础
- [Stiennon et al. — Learning to summarize from human feedback (arXiv:2009.01325)](https://arxiv.org/abs/2009.01325) —— RLHF 用于摘要的前身
- [Christiano et al. — Deep reinforcement learning from human preferences (arXiv:1706.03741)](https://arxiv.org/abs/1706.03741) —— 最早的基于偏好的 RL 形式
- [Bai et al. — Training a Helpful and Harmless Assistant with RLHF (arXiv:2204.05862)](https://arxiv.org/abs/2204.05862) —— Anthropic 对 InstructGPT 流水线的 HH 扩展
