---
name: skill-sampling-strategy
description: 为生成、估计或推断选择正确的采样方法
version: 1.0.0
phase: 1
lesson: 16
tags: [sampling, mcmc, generation]
---

# 采样策略选择

如何为文本生成、贝叶斯推断、蒙特卡洛估计和训练挑选正确的采样方法。

## 决策检查清单

1. 你是在生成输出（文本、图像），还是在估计某个量（积分、期望）？
2. 你能直接从目标分布采样，还是只能求它的密度值？
3. 目标分布是离散的还是连续的？
4. 样本空间是多少维？低维（< 5）、中维（5-100），还是高维（> 100）？
5. 你需要精确样本还是近似样本？
6. 你需要采样操作的梯度吗？

## 各方法的使用时机

| Method | When to use | Complexity | Exact? |
|---|---|---|---|
| Direct sampling | You have the CDF or can use a library function | O(1) per sample | Yes |
| Inverse CDF | Known closed-form CDF inverse (exponential, Cauchy) | O(1) per sample | Yes |
| Box-Muller | Need normal samples without a library | O(1) per sample | Yes |
| Rejection sampling | Can evaluate target PDF, low dimension (1-3) | O(1/acceptance) per sample | Yes |
| Importance sampling | Need expectations, not individual samples | O(n) for n samples | Approximate |
| Stratified sampling | Monte Carlo estimation, want lower variance | O(n) for n samples | Approximate |
| Metropolis-Hastings | High-dimensional, can evaluate unnormalized density | O(1) per step + burn-in | Asymptotically |
| Gibbs sampling | Can sample from each conditional distribution | O(d) per full sweep | Asymptotically |
| HMC/NUTS | High-dimensional continuous, smooth density | O(L * d) per step | Asymptotically |
| Temperature sampling | LLM text generation, control creativity | O(V) for vocab size V | N/A |
| Top-k sampling | LLM generation, remove unlikely tokens | O(V log k) | N/A |
| Top-p (nucleus) | LLM generation, adaptive candidate set | O(V log V) | N/A |
| Reparameterization | Need gradients through Gaussian sampling (VAEs) | O(d) | Yes |
| Gumbel-Softmax | Need gradients through categorical sampling | O(k) for k classes | Approximate |

## LLM 生成设置

| Use case | Temperature | Top-p | Top-k | Notes |
|---|---|---|---|---|
| Factual Q&A | 0.0 (greedy) | -- | -- | Deterministic, no randomness |
| Code generation | 0.2-0.5 | 0.9 | -- | Low creativity, high coherence |
| General chat | 0.7 | 0.9 | -- | Balanced |
| Creative writing | 0.9-1.2 | 0.95 | -- | Higher diversity |
| Brainstorming | 1.0-1.5 | 0.95 | -- | Maximum diversity, may lose coherence |

温度和 top-p 可以组合使用。先应用温度（缩放 logits），再应用 top-p 过滤。

## MCMC 方法选择

| Property | Metropolis-Hastings | Gibbs | HMC/NUTS |
|---|---|---|---|
| Dimension | Any | Any (best < 100) | High (100+) |
| Requires conditionals | No | Yes | No |
| Requires gradient | No | No | Yes |
| Acceptance rate | Tune to ~23% | Always 100% | Tune to ~65% |
| Correlation | High (random walk) | Moderate | Low |
| Burn-in | Long | Moderate | Short |
| Best for | Exploration, simple models | Conjugate models, Bayesian networks | Continuous posteriors, deep probabilistic models |

## 常见错误

- 在高维下使用拒绝采样。接受率随维度指数级下降。超过 5 维就应切换到 MCMC。
- 把 MCMC 的提议方差设得过高或过低。过高：大多数提议被拒，链卡住。过低：所有提议都被接受，链移动缓慢。随机游走 MH 的目标接受率约为 23%。
- 忘记预热期（burn-in）。MCMC 的前 N 个样本受起点偏置。至少要丢弃 1000 步（复杂分布需要更多）。
- 用与目标分布差别很大的提议分布做重要性采样。少数样本会获得巨大权重，使估计不可靠。监控有效样本量：ESS = (sum w_i)^2 / sum(w_i^2)。
- 对需要确定性输出的任务（例如分类、结构化抽取）使用温度 > 0。改用贪心（T=0）或束搜索。
- 不把 top-p 与温度组合使用。温度本身无法从长尾中移除垃圾词元，top-p 可以。
- 对标准采样操作做反向传播。连续（高斯）用重参数化技巧，离散（分类）用 Gumbel-Softmax。

## 快速参考：方差缩减技术

| Technique | How it works | Variance reduction |
|---|---|---|
| Stratified sampling | Divide space into strata, sample each | Always <= standard MC |
| Antithetic variates | Use both U and 1-U | Works for monotone functions |
| Control variates | Subtract a known-mean variable | Proportional to correlation |
| Importance sampling | Reweight samples from a better proposal | Depends on proposal quality |
| Latin hypercube | Stratify each dimension independently | Better than stratified in high-d |
