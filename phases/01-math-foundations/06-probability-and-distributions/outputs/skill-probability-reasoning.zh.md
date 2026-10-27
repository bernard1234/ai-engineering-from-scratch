---
name: skill-probability-reasoning
description: 为给定的 ML 问题选择合适的概率分布
version: 1.0.0
phase: 1
lesson: 6
tags: [probability, distributions, modeling]
---

# 概率分布选择

在建模数据、设计损失函数或设置先验时，如何选择正确的分布。

## 决策清单

1. 结果是离散的（类别、计数）还是连续的（测量、分数）？
2. 结果是有界的（例如 [0, 1]）还是无界的？
3. 有多少种可能结果？两种？k 种？无限种？
4. 数据是对称的还是偏斜的？
5. 事件是独立的还是相关的？
6. 你在建模一个比率、一个计数、一个比例，还是一个测量值？

## 分布决策树

```
变量是离散的吗？
  是 --> 只有 2 种结果？ --> Bernoulli (p)
     |    k 种结果，单次试验？ --> Categorical (p1...pk)
     |    k 种结果，n 次试验？ --> Multinomial (n, p1...pk)
     |    n 次试验中成功的计数？ --> Binomial (n, p)
     |    每区间事件的计数？ --> Poisson (lambda)
     |    直到第一次成功所需的试验次数？ --> Geometric (p)
     |    直到 r 次成功所需的试验次数？ --> Negative Binomial (r, p)
  否 --> 对称、钟形？ --> Normal (mu, sigma)
     |   正值、右偏？ --> Log-normal 或 Exponential
     |   有界于 [0, 1]？ --> Beta (alpha, beta)
     |   正值、灵活形状？ --> Gamma (alpha, beta)
     |   事件之间的时间？ --> Exponential (lambda)
     |   需要重尾？ --> Student's t (nu) 或 Cauchy
     |   多变量、钟形？ --> Multivariate Normal
     |   在单纯形上（总和为 1）？ --> Dirichlet (alpha)
```

## 将真实世界的 ML 场景映射到分布

| 场景 | 分布 | 参数 |
|---|---|---|
| 二分类输出 | Bernoulli | p = sigmoid(logit) |
| 多分类输出 | Categorical | p = softmax(logits) |
| 语言模型中的 token 预测 | Categorical over vocab | 对词表用 softmax 得到 p |
| 像素强度（归一化） | Beta 或 Uniform [0, 1] | 取决于图像统计 |
| 文档中的词数 | Poisson | lambda = 平均词数 |
| 用户请求之间的时间 | Exponential | lambda = 请求率 |
| 测量误差 | Normal | mu = 0, sigma 来自数据 |
| 权重初始化 | Normal 或 Uniform | Kaiming/Xavier 规则 |
| VAE 潜在空间先验 | 标准正态 | mu = 0, sigma = 1 |
| 比例的贝叶斯先验 | Beta | alpha, beta 来自信念 |
| 类别权重的贝叶斯先验 | Dirichlet | alpha 向量 |
| 回归目标中的噪声 | Normal | mu = 0, sigma 估计 |
| 抗离群点的稳健回归 | Student's t | 低自由度 |
| 持续时间/寿命建模 | Weibull 或 Gamma | 形状和尺度 |
| 每文档的主题分布（LDA） | Dirichlet | 稀疏时 alpha < 1 |

## 当分布出错时

- 当数据有硬下界（例如价格、距离）时使用 Normal。正态分布会给负值赋非零概率。改用 log-normal 或 gamma。
- 当方差与均值不同时使用 Poisson。Poisson 假设均值 = 方差。如果方差 > 均值，使用 negative binomial。
- 对多分类问题使用 Bernoulli。Bernoulli 严格是二值的。k > 2 时使用 categorical。
- 在观测相关时假设独立。时间序列、空间数据和分组数据违反独立性。使用自回归或分层模型。

## 常见错误

- 把 PDF 值与概率混淆。PDF 可以超过 1。概率来自对区间上的 PDF 积分。
- 忘记 softmax 输出是 categorical 概率，而不是独立的 Bernoulli 概率。它们构造上就总和为 1。
- 当你有领域知识时使用均匀先验。信息先验如果在选取得当的情况下，可在不偏置结果的前提下降低方差。
- 把对数概率当作概率处理。对数概率总是负的（或零）。它们之和不为 1。

## 速查：分布性质

| 分布 | 支撑集 | 均值 | 方差 | 关键性质 |
|---|---|---|---|---|
| Bernoulli(p) | {0, 1} | p | p(1-p) | 最简单的离散分布 |
| Binomial(n, p) | {0..n} | np | np(1-p) | n 个 Bernoulli 之和 |
| Poisson(lam) | {0, 1, 2, ...} | lam | lam | 均值 = 方差 |
| Normal(mu, s^2) | (-inf, inf) | mu | s^2 | 给定均值/方差时熵最大 |
| Exponential(lam) | [0, inf) | 1/lam | 1/lam^2 | 无记忆性 |
| Beta(a, b) | [0, 1] | a/(a+b) | ab/((a+b)^2(a+b+1)) | Binomial 的共轭先验 |
| Gamma(a, b) | (0, inf) | a/b | a/b^2 | Poisson 的共轭先验 |
| Dirichlet(alpha) | 单纯形 | alpha_i/sum | （见公式） | Categorical 的共轭先验 |