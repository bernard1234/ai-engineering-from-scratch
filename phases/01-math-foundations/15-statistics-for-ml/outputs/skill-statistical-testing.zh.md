---
name: skill-statistical-testing
description: 为比较机器学习模型和评估实验选择正确的统计检验
version: 1.0.0
phase: 1
lesson: 15
tags: [statistics, hypothesis-testing, model-comparison]
---

# 面向机器学习的统计检验

在比较模型、运行 A/B 实验或验证结果时，如何挑选正确的检验方法。

## 决策检查清单

1. 你在比较什么？均值、比例、分布，还是相关性？
2. 有几组？单样本对照参考值、两组，还是多组？
3. 观测是配对的（相同的测试集、相同的折），还是独立的？
4. 数据是否服从正态分布？如果 n < 30 且明显不正态，使用非参数检验。
5. 数据是连续的、有序的，还是类别的？
6. 你要跑多少次检验？如果不止一次，要施加校正。

## 决策树

```text
Comparing means?
  Two groups?
    Paired (same data splits)? --> Paired t-test (or Wilcoxon signed-rank if non-normal)
    Independent? --> Welch's t-test (or Mann-Whitney U if non-normal)
  Multiple groups?
    Paired? --> Repeated measures ANOVA (or Friedman test)
    Independent? --> One-way ANOVA (or Kruskal-Wallis)

Comparing proportions?
  Two groups? --> Chi-squared test or Fisher's exact test (small n)
  Multiple groups? --> Chi-squared test

Comparing distributions?
  Is one distribution a reference? --> Kolmogorov-Smirnov test
  Are both empirical? --> Two-sample KS test

Measuring association?
  Both continuous, roughly normal? --> Pearson correlation
  Ordinal or non-normal? --> Spearman rank correlation
  Categorical x Categorical? --> Chi-squared test of independence

Running many tests?
  Apply Bonferroni correction: alpha_adjusted = alpha / number_of_tests
  Or use Holm-Bonferroni (less conservative, still controls family-wise error)
```

## 各检验的使用时机

| 检验 | 数据类型 | 假设 | ML 用例 |
|---|---|---|---|
| 配对 t 检验 | 连续、配对 | 差值正态 | 在相同的 k 折划分上比较 2 个模型 |
| Wilcoxon 符号秩检验 | 连续/有序、配对 | 无（非参数） | 比较 2 个模型，k 较小（5-10 折） |
| Welch's t 检验 | 连续、独立 | 大致正态 | 在两个独立数据集上比较模型 |
| Mann-Whitney U | 连续/有序、独立 | 无 | 比较延迟分布 |
| ANOVA | 连续、3+ 组 | 正态、方差相等 | 比较多个模型架构 |
| Kruskal-Wallis | 连续/有序、3+ 组 | 无 | 比较多个模型，非正态指标 |
| 卡方检验 | 类别计数 | 期望计数 >= 5 | 比较类别分布、混淆矩阵 |
| Fisher 精确检验 | 类别计数 | 小样本 | 稀有事件比较 |
| KS 检验 | 连续 | 无 | 检查预测是否服从期望分布 |
| Bootstrap 置信区间 | 任意统计量 | 无 | AUC、F1 或任意指标的置信区间 |
| McNemar 检验 | 配对二值 | 无 | 在相同测试集上比较两个分类器 |

## 模型比较配方

1. 在跑实验之前，先定义指标和显著性水平（alpha = 0.05）。
2. 把两个模型跑在相同的 k 折交叉验证划分上（k = 5 或 10）。
3. 收集配对得分：(a_1, b_1), (a_2, b_2), ..., (a_k, b_k)。
4. 计算差值：d_i = b_i - a_i。
5. 跑配对检验（k <= 10 用 Wilcoxon，k > 10 或差值正态时用配对 t 检验）。
6. 报告：p 值、均值差、95% 置信区间、效应量（Cohen's d）。
7. 如果 p < alpha 且效应量有意义，那么这个差异是真实的，也值得采取行动。

## 常见错误

- 数据配对却用了独立检验。如果两个模型是在相同的测试折上评估的，你必须用配对检验。独立检验会丢掉配对信息，损失统计功效。
- 只报告 p < 0.05 而不报告效应量。一个统计显著的 0.1% 准确率提升不值得部署。始终计算 Cohen's d 或原始均值差。
- 在不同的测试集上比较模型。两个模型的测试集必须完全相同。测试集不同会让比较失去意义。
- 跑 20 次比较，不做 Bonferroni 校正就报告最好的那个。在 alpha = 0.05 下做 20 次检验，你碰巧预期会有 1 个假阳性。
- 在不平衡数据上使用准确率。在 99% 的多数类上，一个平凡的分类器就能达到 99%。请使用 F1、precision-recall AUC 或 Matthews 相关系数。
- 把交叉验证折当作独立样本。它们共享训练数据，这违反了独立性假设。校正后的重采样 t 检验可以处理这一点。

## 快速参考：效应量解读

| Cohen's d | 解读 |
|---|---|
| 0.2 | 小效应 |
| 0.5 | 中效应 |
| 0.8 | 大效应 |
| > 1.0 | 非常大的效应 |

| 报告什么 | 为什么 |
|---|---|
| p 值 | 差异是真的吗？ |
| 置信区间 | 差异可能有多大？ |
| 效应量（Cohen's d） | 差异有意义吗？ |
| 样本量（n 或 k 折） | 我们能信任这个结果吗？ |
