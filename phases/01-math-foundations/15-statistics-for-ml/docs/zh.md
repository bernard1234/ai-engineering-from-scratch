# 机器学习的统计学

> 统计学能告诉你，你的模型是真的有效，还是只是运气好。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 06 (Probability and Distributions), 07 (Bayes' Theorem)
**Time:** ~120 minutes

## 学习目标

- 从零开始计算描述统计量、Pearson/Spearman 相关系数以及协方差矩阵
- 执行假设检验（t 检验、卡方检验），并正确解读 p 值与置信区间
- 使用 bootstrap 重采样为任意指标构造置信区间，且不依赖分布假设
- 利用效应量区分统计显著性与实际显著性

## 问题

你训练了两个模型。模型 A 在测试集上得分 0.87，模型 B 得分 0.89。你部署了模型 B。三周后，线上指标比之前更差了。发生了什么？

模型 B 并没有真正优于模型 A。那 0.02 的差距只是噪声。你的测试集太小了，或者方差太高，又或者两者兼有。你把随机性包装成了改进并上线了。

这种情况反复发生：Kaggle 排行榜的震荡、无法复现的论文、仅凭几百个样本就宣布赢家的 A/B 测试。根本原因始终相同：有人跳过了统计学。

统计学给你区分信号与噪声的工具。它告诉你差异何时是真实的、你应该有多大的信心、以及需要多少数据才能信任一个结果。每条机器学习流水线、每次模型比较、每个实验都需要统计学。没有它，你只是在瞎猜。

## 概念

### 描述性统计：概括你的数据

在对任何东西建模之前，你需要先了解你的数据长什么样。描述性统计把数据集压缩成几个能刻画其形态的数字。

**集中趋势的度量**回答“中间在哪里？”这个问题：

```
Mean:   sum of all values / count
        mu = (1/n) * sum(x_i)

Median: middle value when sorted
        Robust to outliers. If you have [1, 2, 3, 4, 1000], the mean is 202
        but the median is 3.

Mode:   most frequent value
        Useful for categorical data. For continuous data, rarely informative.
```

均值是平衡点，中位数是正中间的位置。当两者出现偏离时，说明你的分布是偏斜的。收入分布的均值 >> 中位数（亿万富翁造成的右偏）。训练过程中的损失分布常常均值 << 中位数（简单样本造成的左偏）。

**离散程度的度量**回答“数据有多分散？”这个问题：

```
Variance:   average squared deviation from the mean
            sigma^2 = (1/n) * sum((x_i - mu)^2)

Standard deviation:  square root of variance
                     sigma = sqrt(sigma^2)
                     Same units as the data, so more interpretable.

Range:      max - min
            Sensitive to outliers. Almost never useful alone.

IQR:        Q3 - Q1 (interquartile range)
            The range of the middle 50% of the data.
            Robust to outliers. Used for box plots and outlier detection.
```

**百分位数**把排序后的数据分成 100 等份。第 25 百分位（Q1）意味着 25% 的取值落在这个点以下。第 50 百分位就是中位数。第 75 百分位是 Q3。

```
For latency monitoring:
  P50 = median latency        (typical user experience)
  P95 = 95th percentile       (bad but not worst case)
  P99 = 99th percentile       (tail latency, often 10x the median)
```

在机器学习中，你会因为推理延迟、预测置信度分布和理解误差分布而关心百分位数。一个平均误差很低、但 P99 误差很差的模型，对安全关键型应用来说可能是毫无用处的。

**样本统计量 vs 总体统计量。** 用样本计算方差时，要除以 (n-1) 而不是 n。这就是贝塞尔校正。它补偿了“样本均值并非真实总体均值”这一事实。用 n 作分母时，你会系统性地低估真实方差。用 (n-1) 时，估计是无偏的。

```
Population variance: sigma^2 = (1/N) * sum((x_i - mu)^2)
Sample variance:     s^2     = (1/(n-1)) * sum((x_i - x_bar)^2)
```

实践中：如果 n 很大（数千个样本），这个差异可以忽略。如果 n 很小（几十个样本），它就很重要。

### 相关性：变量如何一起变动

相关性衡量两个变量之间线性关系的强度和方向。

**Pearson 相关系数**衡量线性关联：

```
r = sum((x_i - x_bar)(y_i - y_bar)) / (n * s_x * s_y)

r = +1:  perfect positive linear relationship
r = -1:  perfect negative linear relationship
r =  0:  no linear relationship (but there might be a nonlinear one!)

Range: [-1, 1]
```

Pearson 假设关系是线性的，且两个变量都大致服从正态分布。它对异常值敏感。一个极端点就能把 r 从 0.1 拉到 0.9。

**Spearman 秩相关**衡量单调关联：

```
1. Replace each value with its rank (1, 2, 3, ...)
2. Compute Pearson correlation on the ranks

Spearman catches any monotonic relationship, not just linear.
If y = x^3, Pearson gives r < 1 but Spearman gives rho = 1.
```

**各自的使用时机：**

```
Pearson:    Both variables are continuous and roughly normal.
            You care about the linear relationship specifically.
            No extreme outliers.

Spearman:   Ordinal data (rankings, ratings).
            Data is not normally distributed.
            You suspect a monotonic but not linear relationship.
            Outliers are present.
```

**黄金法则：** 相关不等于因果。冰淇淋销量与溺水死亡人数相关，是因为两者都在夏季上升。你模型的准确率与参数数量相关，但增加参数并不会自动提升准确率（参见：过拟合）。

### 协方差矩阵

两个变量之间的协方差衡量它们如何一起变动：

```
Cov(X, Y) = (1/n) * sum((x_i - x_bar)(y_i - y_bar))

Cov(X, Y) > 0:  X and Y tend to increase together
Cov(X, Y) < 0:  when X increases, Y tends to decrease
Cov(X, Y) = 0:  no linear co-movement
```

对于 d 个特征，协方差矩阵 C 是一个 d x d 的矩阵，其中 C[i][j] = Cov(feature_i, feature_j)。对角线元素 C[i][i] 是每个特征的方差。

```
C = | Var(x1)      Cov(x1,x2)  Cov(x1,x3) |
    | Cov(x2,x1)  Var(x2)      Cov(x2,x3) |
    | Cov(x3,x1)  Cov(x3,x2)  Var(x3)     |

Properties:
  - Symmetric: C[i][j] = C[j][i]
  - Positive semi-definite: all eigenvalues >= 0
  - Diagonal = variances
  - Off-diagonal = covariances
```

**与 PCA 的关联。** PCA 对协方差矩阵做特征分解。特征向量就是主成分（最大方差的方向）。特征值告诉你每个成分捕获了多少方差。这正是第 10 课所讲的内容，但现在你明白了为什么协方差矩阵是应该被分解的对象：它编码了数据中所有成对的线性关系。

**与相关性的关联。** 相关矩阵是标准化变量（每个变量除以各自的标准差）的协方差矩阵。相关性对协方差做了归一化，使所有取值落在 [-1, 1] 之间。

### 假设检验

假设检验是在不确定性下做决策的框架。你先提出一个论断，收集数据，然后判断数据是否与该论断一致。

**基本设定：**

```
Null hypothesis (H0):        the default assumption, usually "no effect"
Alternative hypothesis (H1): what you are trying to show

Example:
  H0: Model A and Model B have the same accuracy
  H1: Model B has higher accuracy than Model A
```

**p 值**是在假设 H0 为真的前提下，观察到与你所见同样极端的数据的概率。它**不是** H0 为真的概率。这是统计学中最常见的误解。

```
p-value = P(data this extreme | H0 is true)

If p-value < alpha (typically 0.05):
    Reject H0. The result is "statistically significant."
If p-value >= alpha:
    Fail to reject H0. You do not have enough evidence.
    This does NOT mean H0 is true.
```

**置信区间**给出某个参数的合理取值范围：

```
95% confidence interval for the mean:
    x_bar +/- z * (s / sqrt(n))

where z = 1.96 for 95% confidence

Interpretation: if you repeated this experiment many times, 95% of the
computed intervals would contain the true mean. It does NOT mean there
is a 95% probability the true mean is in this specific interval.
```

置信区间的宽度告诉你精度如何。区间宽意味着不确定性高。区间窄意味着你的估计很精确（但如果数据有偏，也未必准确）。

### t 检验

t 检验用于比较均值。它有好几种变体。

**单样本 t 检验：** 总体均值是否不同于某个假设值？

```
t = (x_bar - mu_0) / (s / sqrt(n))

degrees of freedom = n - 1
```

**双样本 t 检验（独立）：** 两组均值是否不同？

```
t = (x_bar_1 - x_bar_2) / sqrt(s1^2/n1 + s2^2/n2)

This is Welch's t-test, which does not assume equal variances.
Always use Welch's unless you have a specific reason for equal variances.
```

**配对 t 检验：** 当测量值成对出现时（同一个模型在相同的数据划分上评估）：

```
Compute d_i = x_i - y_i for each pair
Then run a one-sample t-test on the d_i values against mu_0 = 0
```

在机器学习中，配对 t 检验很常见：你把两个模型跑在相同的 10 折交叉验证上，然后逐对比较它们的得分。

### 卡方检验

卡方检验检查观测频数是否与期望频数一致。适用于类别数据。

```
chi^2 = sum((observed - expected)^2 / expected)

Example: does a language model's output distribution match the
training distribution across categories?

Category    Observed   Expected
Positive       120        100
Negative        80        100
chi^2 = (120-100)^2/100 + (80-100)^2/100 = 4 + 4 = 8

With 1 degree of freedom, chi^2 = 8 gives p < 0.005.
The difference is significant.
```

### 机器学习模型的 A/B 测试

机器学习中的 A/B 测试与网页 A/B 测试不是一回事。模型比较有它特有的挑战：

```
1. Same test set:    Both models must be evaluated on identical data.
                     Different test sets make comparison meaningless.

2. Multiple metrics: Accuracy alone is not enough. You need precision,
                     recall, F1, latency, and fairness metrics.

3. Variance:         Use cross-validation or bootstrap to estimate
                     the variance of each metric, not just point estimates.

4. Data leakage:     If the test set was used during model selection,
                     your comparison is biased. Hold out a final test set.
```

**流程：**

```
1. Define your metric and significance level (alpha = 0.05)
2. Run both models on the same k-fold cross-validation splits
3. Collect paired scores: [(a1, b1), (a2, b2), ..., (ak, bk)]
4. Compute differences: d_i = b_i - a_i
5. Run a paired t-test on the differences
6. Check: is the mean difference significantly different from 0?
7. Compute a confidence interval for the mean difference
8. Compute effect size (Cohen's d) to judge practical significance
```

### 统计显著性与实际显著性

一个结果可能统计上显著，但在实际上毫无意义。只要有足够多的数据，哪怕是微不足道的差异也会变得统计显著。

```
Example:
  Model A accuracy: 0.9234
  Model B accuracy: 0.9237
  n = 1,000,000 test samples
  p-value = 0.001

Statistically significant? Yes.
Practically significant? A 0.03% improvement is not worth the
engineering cost of deploying a new model.
```

**效应量**量化差异有多大，且与样本量无关：

```
Cohen's d = (mean_1 - mean_2) / pooled_std

d = 0.2:  small effect
d = 0.5:  medium effect
d = 0.8:  large effect
```

始终同时报告 p 值和效应量。p 值告诉你差异是否真实，效应量告诉你差异是否重要。

### 多重比较问题

当你检验许多假设时，其中一些会“碰巧”显著。如果你在 alpha = 0.05 下检验 20 件事，即使什么都不真实，你也预期会有 1 个假阳性。

```
P(at least one false positive) = 1 - (1 - alpha)^m

m = 20 tests, alpha = 0.05:
P(false positive) = 1 - 0.95^20 = 0.64

You have a 64% chance of at least one false positive.
```

**Bonferroni 校正：** 把 alpha 除以检验次数。

```
Adjusted alpha = alpha / m = 0.05 / 20 = 0.0025

Only reject H0 if p-value < 0.0025.
Conservative but simple. Works when tests are independent.
```

在机器学习中，当你跨多个指标比较一个模型、测试许多超参数配置、或在多个数据集上评估时，这一点很重要。

### Bootstrap 方法

Bootstrap 通过从你的数据中有放回地重采样，来估计某个统计量的抽样分布。它不需要对底层分布做任何假设。

**算法：**

```
1. You have n data points
2. Draw n samples WITH replacement (some points appear multiple times,
   some not at all)
3. Compute your statistic on this bootstrap sample
4. Repeat B times (typically B = 1000 to 10000)
5. The distribution of bootstrap statistics approximates the
   sampling distribution
```

**Bootstrap 置信区间（百分位法）：**

```
Sort the B bootstrap statistics
95% CI = [2.5th percentile, 97.5th percentile]
```

**Bootstrap 对机器学习为何重要：**

```
- Test set accuracy is a point estimate. Bootstrap gives you
  confidence intervals.
- You cannot assume metric distributions are normal (especially
  for AUC, F1, precision at k).
- Bootstrap works for ANY statistic: median, ratio of two means,
  difference in AUC between two models.
- No closed-form formula needed.
```

**用于模型比较的 Bootstrap：**

```
1. You have predictions from Model A and Model B on the same test set
2. For each bootstrap iteration:
   a. Resample test indices with replacement
   b. Compute metric_A and metric_B on the resampled set
   c. Store diff = metric_B - metric_A
3. 95% CI for the difference:
   [2.5th percentile of diffs, 97.5th percentile of diffs]
4. If the CI does not contain 0, the difference is significant
```

这比配对 t 检验更稳健，因为它不做任何分布假设。

### 参数检验 vs 非参数检验

**参数检验**假设数据服从特定分布（通常是正态分布）：

```
t-test:         assumes normally distributed data (or large n by CLT)
ANOVA:          assumes normality and equal variances
Pearson r:      assumes bivariate normality
```

**非参数检验**不做任何分布假设：

```
Mann-Whitney U:     compares two groups (replaces independent t-test)
Wilcoxon signed-rank: compares paired data (replaces paired t-test)
Spearman rho:       correlation on ranks (replaces Pearson)
Kruskal-Wallis:     compares multiple groups (replaces ANOVA)
```

**何时使用非参数检验：**

```
- Small sample size (n < 30) and data is clearly non-normal
- Ordinal data (ratings, rankings)
- Heavy outliers you cannot remove
- Skewed distributions
```

**何时使用参数检验：**

```
- Large sample size (CLT makes the test statistic approximately normal)
- Data is roughly symmetric without extreme outliers
- More statistical power (better at detecting real differences)
```

在机器学习实验中，你的 n 通常很小（5 或 10 折交叉验证），因此像 Wilcoxon 符号秩检验这样的非参数检验往往比 t 检验更合适。

### 中心极限定理：实践意义

中心极限定理（CLT）指出，随着 n 增大，样本均值的分布会趋近于正态分布，无论底层总体分布如何。

```
If X_1, X_2, ..., X_n are iid with mean mu and variance sigma^2:

    X_bar ~ Normal(mu, sigma^2 / n)    as n -> infinity

Works for n >= 30 in most cases.
For highly skewed distributions, you might need n >= 100.
```

**这对机器学习为何重要：**

```
1. Justifies confidence intervals and t-tests on aggregated metrics
2. Explains why averaging over cross-validation folds gives stable
   estimates even when individual folds vary wildly
3. Mini-batch gradient descent works because the average gradient
   over a batch approximates the true gradient (CLT in action)
4. Ensemble methods: averaging predictions from many models gives
   more stable output than any single model
```

**CLT 不能做什么：**

```
- Does NOT make your data normal. It makes the MEAN of samples normal.
- Does NOT work for heavy-tailed distributions with infinite variance
  (Cauchy distribution).
- Does NOT apply to dependent data (time series without correction).
```

### 机器学习论文中常见的统计错误

1. **在训练集上测试。** 必然导致过拟合。始终留出模型在训练期间从未见过的数据。

2. **没有置信区间。** 只报告一个孤零零的准确率数值而不报告不确定性，会让结果无法复现、无法验证。

3. **忽略多重比较。** 测试 50 个配置，不做校正就报告最好的那个，会抬高假阳性率。

4. **混淆统计显著性与实际显著性。** 在 0.01% 的准确率提升上得到 0.001 的 p 值，是没有意义的。

5. **在不平衡数据上使用准确率。** 在一个 99% 都是负类的数据集上得到 99% 的准确率，说明模型什么都没学到。请使用精确率、召回率、F1 或 AUC。

6. **挑选指标。** 只报告你模型胜出的那个指标。诚实的评估会报告所有相关指标。

7. **在训练/测试划分间泄露信息。** 在划分之前做归一化，或用未来数据预测过去。

8. **测试集太小且没有方差估计。** 在 100 个样本上评估后声称有 2% 的提升，那是噪声，不是信号。

9. **在数据不独立时假设独立。** 同一患者的医学影像、同一文档中的多个句子。组内的观测是相关的。

10. **p 值操纵（p-hacking）。** 不断尝试不同的检验、子集或排除标准，直到得到 p < 0.05。这个结果只是搜索过程的产物。

## 动手实现

你将实现：

1. **从零开始的描述统计**（均值、中位数、众数、标准差、百分位数、IQR）
2. **相关函数**（Pearson 和 Spearman，以及协方差矩阵）
3. **假设检验**（单样本 t 检验、双样本 t 检验、卡方检验）
4. **Bootstrap 置信区间**（适用于任意统计量，无需任何假设）
5. **A/B 测试模拟器**（生成数据、做检验、检查 I 类与 II 类错误）
6. **统计显著性与实际显著性演示**（展示大 n 如何让一切都变得“显著”）

全部从零开始，只使用 `math` 和 `random`。不用 numpy，不用 scipy。

```figure
f3-bootstrap-resample
```

## 关键术语

| 术语 | 定义 |
|---|---|
| Mean | 数值之和除以个数。对异常值敏感。 |
| Median | 排序后数据的中间值。对异常值稳健。 |
| Standard deviation | 方差的平方根。以原始单位衡量离散程度。 |
| Percentile | 有给定百分比的数据落在其下的那个值。 |
| IQR | 四分位距。Q3 减去 Q1。中间 50% 数据的离散范围。 |
| Pearson correlation | 衡量两个变量之间的线性关联。取值范围 [-1, 1]。 |
| Spearman correlation | 使用秩衡量单调关联。 |
| Covariance matrix | 所有特征之间两两协方差构成的矩阵。 |
| Null hypothesis | “无效应或无差异”的默认假设。 |
| p-value | 在原假设为真的前提下，数据达到如此极端的概率。 |
| Confidence interval | 在给定置信水平下，某个参数合理取值的范围。 |
| t-test | 检验均值是否显著不同。使用 t 分布。 |
| Chi-squared test | 检验观测频数是否不同于期望频数。 |
| Effect size | 差异的幅度，与样本量无关。常用 Cohen's d。 |
| Bonferroni correction | 将显著性阈值除以检验次数，以控制假阳性。 |
| Bootstrap | 有放回地重采样，以估计抽样分布。 |
| Type I error | 假阳性。在 H0 为真时拒绝了 H0。 |
| Type II error | 假阴性。在 H0 为假时未能拒绝 H0。 |
| Statistical power | 正确拒绝一个错误的 H0 的概率。检验效能 = 1 减去 II 类错误率。 |
| Central limit theorem | 随着样本量增大，样本均值收敛到正态分布。 |
| Parametric test | 对数据假设特定分布（通常是正态分布）。 |
| Non-parametric test | 不做分布假设。基于秩或符号工作。 |
