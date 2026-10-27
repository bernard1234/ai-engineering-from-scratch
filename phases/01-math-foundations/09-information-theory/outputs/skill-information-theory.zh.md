---
name: skill-information-theory
description: 将信息论概念应用于 ML 损失函数、模型评估和特征选择
version: 1.0.0
phase: 1
lesson: 9
tags: [information-theory, entropy, loss-functions]
---

# 面向 ML 的信息论

在机器学习系统中，何时使用熵、交叉熵、KL 散度和互信息。

## 决策清单

1. 度量单个分布的不确定性？用**熵**。
2. 度量模型对真实标签的拟合有多好？用**交叉熵**（这就是你的分类损失）。
3. 度量两个分布之间的距离？用 **KL 散度**。
4. 检查两个变量是否相关？用**互信息**。
5. 报告语言模型的质量？用**困惑度**（交叉熵的指数）。
6. 把一个模型蒸馏进另一个模型？最小化从教师到学生的 **KL 散度**。

## 何时使用每种度量

| 度量 | 公式 | 适用场景 | ML 应用 |
|---|---|---|---|
| 熵 H(P) | -sum(p log p) | 这个分布有多不确定？ | 数据复杂度、最大熵模型 |
| 交叉熵 H(P,Q) | -sum(p log q) | 模型 Q 预测真实 P 有多好？ | 分类损失、语言模型损失 |
| KL 散度 D(P\|\|Q) | sum(p log(p/q)) | P 和 Q 有多大差异？ | VAE 损失（ELBO）、知识蒸馏、RLHF |
| 互信息 I(X;Y) | H(X) - H(X\|Y) | Y 能告诉我们多少关于 X 的信息？ | 特征选择、表征学习 |
| 困惑度 | exp(H(P,Q)) 或 2^H | 模型有多困惑？ | 语言模型评估 |
| 条件熵 H(X\|Y) | -sum(p(x,y) log p(x\|y)) | 知道 Y 之后 X 中剩余的不确定性 | 特征的信息量 |

## 关键关系

```
Cross-entropy  = Entropy + KL divergence
H(P, Q)        = H(P)   + D_KL(P || Q)

Since H(P) is constant during training:
  Minimizing cross-entropy = Minimizing KL divergence

Mutual information = Entropy - Conditional entropy
I(X; Y) = H(X) - H(X|Y) = H(Y) - H(Y|X)

Perplexity = exp(cross-entropy in nats)
           = 2^(cross-entropy in bits)
```

## 快速参考：公式与单位

| 公式 | 比特（以 2 为底） | 奈特（以 e 为底） |
|---|---|---|
| 信息量：-log(p) | -log2(p) | -ln(p) |
| 熵：-sum(p log p) | bits | nats |
| 1 nat = | 1.4427 bits | 1 nat |
| PyTorch 默认 | -- | nats |
| 信息论论文 | bits | -- |

## 解读数值

| 熵值 | 含义 |
|---|---|
| 0 | 确定性的。有一个结果的概率为 1。 |
| log(n) | 最大不确定性。n 个结果上的均匀分布。 |
| 低 | 分布尖锐。模型很确信。 |
| 高 | 分布平坦。模型不确定。 |

| 困惑度值 | 语言模型质量 |
|---|---|
| 1 | 完美预测（实践中从不发生） |
| 10 | 平均而言在约 10 个等可能的 token 中做选择 |
| 50 | 标准基准上的 GPT-2 水平 |
| < 10 | 表现充分的领域的最先进水平 |

## 常见错误

- 计算 KL 散度却把它当作对称的。D_KL(P||Q) != D_KL(Q||P)。如需对称度量，使用 Jensen-Shannon 散度：JS = 0.5 * KL(P||M) + 0.5 * KL(Q||M)，其中 M = 0.5*(P+Q)。
- 忘记带 one-hot 标签的交叉熵会简化为 -log(p_true_class)。当真实分布是 one-hot 时，你不需要对所有类别求和。
- 在代码里用 2 为底的对数，却报告奈特（或反过来）。PyTorch 默认使用自然对数。乘以 log2(e) = 1.4427 即可把奈特换算成比特。
- 计算空事件或零概率事件的熵。惯例：0 * log(0) = 0，因为 lim(p->0) p*log(p) = 0。
- 跨不同词表比较困惑度。词表大小为 50k、困惑度为 30 的模型，不能直接和词表大小为 10k、困惑度为 30 的模型比较。

## 每个概念在生产 ML 中出现的位置

| 概念 | 你在哪里见到它 |
|---|---|
| 交叉熵损失 | 每一个分类模型（nn.CrossEntropyLoss） |
| KL 散度 | VAE ELBO、PPO 裁剪、知识蒸馏 |
| 熵正则化 | RL 中的探索奖励（熵越高 = 探索越多） |
| 互信息 | 特征选择、InfoNCE 损失（对比学习） |
| 困惑度 | 语言模型基准（越低 = 越好） |
| 标签平滑 | 用软目标代替 one-hot，降低交叉熵的过度自信 |
| 温度缩放 | 在 softmax 之前把 logits 除以 T，控制输出的熵 |