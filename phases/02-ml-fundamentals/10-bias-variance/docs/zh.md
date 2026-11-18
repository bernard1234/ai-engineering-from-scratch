# 偏差-方差权衡

> 每个模型误差来自三个来源之一：偏差、方差或噪声。你只能控制前两个。

**Type:** Learn
**Language:** Python
**Prerequisites:** Phase 2, Lessons 01-09 (ML 基础、回归、分类、评估)
**Time:** ~75 minutes

## Learning Objectives

- 推导预期预测误差的偏差-方差分解，并解释不可约噪声的作用
- 用训练和测试误差的模式诊断模型是高偏差还是高方差
- 解释正则化技术（L1、L2、Dropout、早停）如何用偏差换方差
- 实现可视化不同复杂度模型的偏差-方差权衡实验

## 问题场景

你训练了一个模型。它在测试数据上有一些误差。误差从哪来？

如果你的模型太简单（用直线拟合曲线数据集），它会一贯地错过真实模式。这是偏差。如果你的模型太复杂（用 20 次多项式拟合 15 个数据点），它完美拟合训练数据但在新数据上给出剧烈波动的预测。这是方差。

对于固定的模型容量，你不能同时最小化两者。压低偏差方差上升，压下方差偏差上升。理解这个权衡是机器学习里最有用的诊断技能。它告诉你该让模型更复杂还是更简单，该拿更多数据还是做更好的特征工程，该加更多正则化还是减正则化。

## 核心概念

### 偏差：系统性误差

偏差衡量你模型的平均预测离真实值有多远。如果你在同一个分布上训练很多不同的训练集，然后取预测的平均，偏差就是这个平均和真相之间的差距。

高偏差意味着模型太死板，抓不住真实模式。用直线拟合抛物线永远会错过曲线，不管给它多少数据。这是欠拟合。

```
高偏差（欠拟合）：
  模型总是预测大致相同的错误值。
  训练误差：高
  测试误差：高
  两者差距：小
```

### 方差：对训练数据的敏感度

方差衡量你在不同数据子集上训练时预测变了多少。训练集里的小改动导致模型的大变化，说明方差高。

高方差意味着模型在拟合训练数据里的噪声，而不是底层信号。20 次多项式会穿过每个训练点，但在点之间剧烈震荡。这是过拟合。

```
高方差（过拟合）：
  模型完美拟合训练数据但在新数据上翻船。
  训练误差：低
  测试误差：高
  两者差距：大
```

### 分解

对任意点 x，平方损失下的预期预测误差精确分解为：

```
预期误差 = 偏差² + 方差 + 不可约噪声

其中：
  偏差²   = (E[f_hat(x)] - f(x))²
  方差     = E[(f_hat(x) - E[f_hat(x)])²]
  噪声     = E[(y - f(x))²]             (σ²)
```

- `f(x)` 是真实函数
- `f_hat(x)` 是你的模型预测
- `E[...]` 是对不同训练集的期望
- `y` 是观测标签（真实函数加噪声）

噪声项不可约。任何模型在有噪声的数据上都不可能好于 σ²。你的任务是在偏差²和方差之间找到正确平衡。

### 模型复杂度 vs 误差

（mermaid 图保留）

经典 U 型曲线：

| 复杂度 | 偏差 | 方差 | 总误差 |
|--------|------|------|--------|
| 太低 | 高 | 低 | 高（欠拟合） |
| 刚好 | 中 | 中 | 最低 |
| 太高 | 低 | 高 | 高（过拟合） |

### 正则化作为偏差-方差控制

正则化刻意增加偏差来降低方差。它约束模型，让它不能追着噪声跑。

- **L2（Ridge）**：把所有权重往 0 收缩。保留所有特征但减小它们的影响。
- **L1（Lasso）**：把一些权重精确推到 0。自动做特征选择。
- **Dropout**：训练时随机关掉神经元。强制产生冗余表示。
- **早停**：模型完全拟合训练数据之前就停掉训练。

正则化强度（λ、dropout rate、epoch 数）直接控制你在偏差-方差曲线上的位置。越多正则化 = 越多偏差，越少方差。

### 双下降：现代视角

经典理论说：过了最佳点，更多复杂度只会更糟。但 2019 年以来的研究发现了意想不到的东西。如果你把模型容量继续增加，远超过插值阈值（模型有足够参数完美拟合训练数据的那个点），测试误差可以再次下降。

（mermaid 图保留）

这个"双下降"现象解释了为什么严重过参数化的神经网络（参数远多于训练样本）仍然泛化得好。经典偏差-方差权衡没错，但对现代训练机制来说不完整。

关于双下降的关键观察：
- 在线性模型、决策树和神经网络里都发生
- 在插值区域更多数据反而可能有害（样本级双下降）
- 更多训练 epoch 也可能导致它（epoch 级双下降）
- 正则化把峰值抹平但不消除它

为什么会这样？在插值阈值处，模型刚好有足够容量拟合所有训练点。它被迫进入一个穿过每个点的特定解，数据上的微小扰动会导致拟合的大变化。这是方差的峰值。过了阈值之后，模型有很多可能的解都能完美拟合数据。学习算法（比如隐式正则化的梯度下降）倾向于在它们中选最简单的那个。这种朝向简单解的隐式偏好就是为什么过参数化模型能泛化。

| 机制 | 参数 vs 样本 | 行为 |
|------|--------------|------|
| 欠参数化 | p ≪ n | 经典权衡适用 |
| 插值阈值 | p ~ n | 方差峰值，测试误差尖刺 |
| 过参数化 | p ≫ n | 隐式正则化生效，测试误差下降 |

实际考虑：如果你在用神经网络或大型树集成，别在插值阈值就停。要么待在它下面（加显式正则化），要么远远超过它。最糟糕的位置就是刚好在阈值上。

### 诊断你的模型

（mermaid 图保留）

| 症状 | 诊断 | 修复 |
|------|------|------|
| 训练误差高、测试误差高 | 偏差 | 更多特征、复杂模型、减正则化 |
| 训练误差低、测试误差高 | 方差 | 更多数据、正则化、更简单模型、Dropout |
| 训练误差低、测试误差低 | 拟合好 | 上线 |
| 训练误差在降、测试误差在升 | 正在过拟合 | 早停 |

### 实用策略

**偏差是问题时：**
- 加多项式或交互特征
- 用更灵活的模型（树集成代替线性）
- 减正则化强度
- 训练更久（如果还没收敛）

**方差是问题时：**
- 拿更多训练数据
- 用 Bagging（随机森林）
- 加正则化（更高 λ、更多 Dropout）
- 特征选择（去掉噪声特征）
- 用交叉验证尽早发现

### 集成方法和方差缩减

集成方法是对抗方差最实用的工具。

**Bagging（Bootstrap Aggregating）**在训练数据的不同 bootstrap 样本上训练多个模型，然后平均它们的预测。每个单独模型有高方差，但平均之后方差就低多了。随机森林就是 Bagging 套在决策树上。

数学上为什么有效：如果你平均 N 个独立预测，每个方差 σ²，平均的方差就是 σ² / N。模型不是真正独立的（它们都看相似的数据），所以缩减量小于 1/N，但仍然很可观。

**Boosting** 通过顺序构建模型来减少偏差，每个新模型聚焦于当前集成的错误。梯度提升和 AdaBoost 是主要例子。Boosting 如果加太多模型会过拟合，所以你需要早停或正则化。

| 方法 | 主要效果 | 偏差变化 | 方差变化 |
|------|----------|----------|----------|
| Bagging | 减方差 | 不变 | 减小 |
| Boosting | 减偏差 | 减小 | 可能增大 |
| Stacking | 两者都减 | 取决于元学习器 | 取决于基模型 |
| Dropout | 隐式 Bagging | 略微增加 | 减小 |

**实用规则**：如果你的基模型方差高（深树、高次多项式），用 Bagging。如果你的基模型偏差高（浅树桩、简单线性模型），用 Boosting。

### 学习曲线

学习曲线把训练和验证误差画成训练集大小的函数。它们是你手头最实用的诊断工具。不像单次 train/test 比较，学习曲线展示模型的轨迹，告诉你更多数据有没有帮助。

（mermaid 图保留）

怎么读它们：

| 场景 | 训练误差 | 验证误差 | 差距 | 意味着什么 | 该做什么 |
|------|----------|----------|------|------------|----------|
| 高偏差 | 高 | 高 | 小 | 模型抓不住模式 | 更多特征、复杂模型、减正则化 |
| 高方差 | 低 | 高 | 大 | 模型在记数据 | 更多数据、正则化、更简单模型 |
| 拟合好 | 中 | 中 | 小 | 模型泛化好 | 上线 |
| 高方差、在改善 | 低 | 随更多数据下降 | 在缩小 | 方差问题可以用数据解决 | 去收更多数据 |
| 高偏差、平坦 | 高 | 高且平坦 | 小且平坦 | 更多数据没用 | 换模型架构 |

关键洞察：如果两条曲线都已平台，差距小但误差都高，更多数据没用。你需要更好的模型。如果差距大且还在缩，更多数据有帮助。

### 怎么生成学习曲线

有两种方式：

**方式 1：变训练集大小，固定模型。** 模型和超参数不变。在越来越大的训练数据子集上训练。在每个大小上测训练误差和验证误差。这是标准学习曲线。

**方式 2：变模型复杂度，固定数据。** 数据不变。扫一个复杂度参数（多项式次数、树深度、层数）。在每个复杂度上测训练误差和验证误差。这是验证曲线，直接展示偏差-方差权衡。

两种方式互为补充。第一种告诉你更多数据有没有帮助。第二种告诉你换模型有没有帮助。做决策前两个都跑。

（mermaid 图保留）

```figure
bias-variance
```

## Build It

`code/bias_variance.py` 里的代码跑完了完整的偏差-方差分解实验。方法如下：

### 第 1 步：从已知函数生成合成数据

用 `f(x) = sin(1.5x) + 0.5x` 加高斯噪声。知道真实函数让我们算精确的偏差和方差。

```python
def true_function(x):
    return np.sin(1.5 * x) + 0.5 * x

def generate_data(n_samples=30, noise_std=0.5, x_range=(-3, 3), seed=None):
    rng = np.random.RandomState(seed)
    x = rng.uniform(x_range[0], x_range[1], n_samples)
    y = true_function(x) + rng.normal(0, noise_std, n_samples)
    return x, y
```

### 第 2 步：Bootstrap 采样和多项式拟合

对每个多项式次数，我们抽很多 bootstrap 训练集，拟合多项式，然后在固定测试网格上记录预测。这给了我们每个测试点上的预测分布。

```python
def fit_polynomial(x_train, y_train, degree, lam=0.0):
    X = np.column_stack([x_train ** d for d in range(degree + 1)])
    if lam > 0:
        penalty = lam * np.eye(X.shape[1])
        penalty[0, 0] = 0
        w = np.linalg.solve(X.T @ X + penalty, X.T @ y_train)
    else:
        w = np.linalg.lstsq(X, y_train, rcond=None)[0]
    return w
```

### 第 3 步：计算偏差² 和方差分解

有了 200 组预测之后，我们能直接从定义计算分解：

```python
mean_pred = predictions.mean(axis=0)
bias_sq = np.mean((mean_pred - y_true) ** 2)
variance = np.mean(predictions.var(axis=0))
total_error = np.mean(np.mean((predictions - y_true) ** 2, axis=1))
```

- `mean_pred` 是从 bootstrap 样本估计的 E[f_hat(x)]
- `bias_sq` 是平均预测和真相之间的平方差
- `variance` 是 bootstrap 样本之间预测的平均散布
- `total_error` 应该约等于 bias² + variance + noise

### 第 4 步：学习曲线

```python
def demo_learning_curves():
    sizes = [10, 15, 20, 30, 50, 75, 100, 150, 200, 300]
    degree = 5

    for n in sizes:
        train_errors = []
        test_errors = []
        for seed in range(50):
            x_train, y_train = generate_data(n_samples=n, seed=seed * 100)
            w = fit_polynomial(x_train, y_train, degree)
            train_pred = predict_polynomial(x_train, w)
            train_mse = np.mean((train_pred - y_train) ** 2)
            test_pred = predict_polynomial(x_test, w)
            test_mse = np.mean((test_pred - y_test) ** 2)
            train_errors.append(train_mse)
            test_errors.append(test_mse)
        # 对多次运行取平均给出学习曲线点
```

对高方差模型（次数 5、小数据），你会看到：
- 训练误差从低开始，随着更多数据让记忆变难而升高
- 测试误差从高开始，随着模型获得更多信号而下降
- 差距随更多数据缩小

对高偏差模型（次数 1），两条误差很快收敛到同一个高值，更多数据没用。

### 第 5 步：正则化扫描

代码也包含 `demo_regularization_sweep()`，固定一个高次多项式（次数 15），扫 Ridge 正则化强度从 0.001 到 100。这从另一个角度展示偏差-方差权衡：不是变模型复杂度，而是变约束强度。

```python
def demo_regularization_sweep():
    alphas = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
    for alpha in alphas:
        results = bias_variance_decomposition([15], lam=alpha)
        r = results[15]
        print(f"alpha={alpha:.3f}  bias={r['bias_sq']:.4f}  var={r['variance']:.4f}")
```

低 alpha 时，次数 15 多项式几乎不受约束。方差主导，因为模型在每个 bootstrap 样本上追噪声。高 alpha 时，惩罚强到模型实际上变成近常数函数。偏差主导。最优 alpha 在这两个极端之间。

这和变多项式次数的 U 型曲线是同一个东西，但由连续旋钮控制而不是离散旋钮。实践中，正则化是控制权衡首选方式，因为它允许精细调整而不改变特征集。

## Use It

sklearn 提供了 `learning_curve` 和 `validation_curve` 来自动化这些诊断，不用手写 bootstrap 循环。

### 验证曲线：扫模型复杂度

```python
from sklearn.model_selection import validation_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge

degrees = list(range(1, 16))
train_scores_all = []
val_scores_all = []

for d in degrees:
    pipe = make_pipeline(PolynomialFeatures(d), Ridge(alpha=0.01))
    train_scores, val_scores = validation_curve(
        pipe, X, y, param_name="polynomialfeatures__degree",
        param_range=[d], cv=5, scoring="neg_mean_squared_error"
    )
    train_scores_all.append(-train_scores.mean())
    val_scores_all.append(-val_scores.mean())
```

直接给你偏差-方差权衡曲线。验证分数相对训练分数最差时，方差主导。两者都差时，偏差主导。

### 学习曲线：扫训练集大小

```python
from sklearn.model_selection import learning_curve

pipe = make_pipeline(PolynomialFeatures(5), Ridge(alpha=0.01))
train_sizes, train_scores, val_scores = learning_curve(
    pipe, X, y, train_sizes=np.linspace(0.1, 1.0, 10),
    cv=5, scoring="neg_mean_squared_error"
)
train_mse = -train_scores.mean(axis=1)
val_mse = -val_scores.mean(axis=1)
```

画 `train_mse` 和 `val_mse` vs `train_sizes`。形状告诉你关于模型的一切。

### 带正则化扫描的交叉验证

```python
from sklearn.model_selection import cross_val_score

alphas = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
for alpha in alphas:
    pipe = make_pipeline(PolynomialFeatures(10), Ridge(alpha=alpha))
    scores = cross_val_score(pipe, X, y, cv=5, scoring="neg_mean_squared_error")
    print(f"alpha={alpha:>7.3f}  MSE={-scores.mean():.4f} +/- {scores.std():.4f}")
```

固定模型复杂度扫正则化强度。你会看到同样的偏差-方差权衡：低 alpha 意味着高方差，高 alpha 意味着高偏差。

### 合在一起：完整诊断工作流

实际中，你按顺序跑这些诊断：

1. 训练模型。算 train 和 test 误差。
2. 如果都高：你有偏差问题。跳到第 4 步。
3. 如果 train 低但 test 高：你有方差问题。生成学习曲线看更多数据有没有帮助。如果没有，加正则化。
4. 生成验证曲线扫主要复杂度参数。找最佳点。
5. 在最佳点生成学习曲线。如果差距还大，你需要更多数据或正则化。
6. 用不同 α 值试 Ridge/Lasso，用 `cross_val_score` 选交叉验证误差最低的 α。

对大部分表格数据集这花 10-15 分钟算力，但能省你几小时瞎猜。

## Ship It

本课产出：`outputs/prompt-model-diagnostics.md`

## Exercises

1. 用 `noise_std=0`（无噪声）跑分解。不可约误差项会怎样？最优复杂度变了吗？
2. 训练集大小从 30 增到 300。这对方差成分有什么影响？最优多项式次数移动了吗？
3. 在实验里加 L2 正则化（Ridge 回归）。固定一个高次多项式（次数 15），λ 从 0 扫到 100。画出偏差² 和方差作为 λ 的函数。
4. 把真实函数从多项式换成 `sin(x)`。偏差-方差分解怎么变？还有清晰的最优次数吗？
5. 实现简单的 bootstrap aggregating（Bagging）包装器：在 bootstrap 样本上训练 10 个模型然后平均预测。展示这怎么在不明显增加偏差的情况下降低方差。

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| Bias | "模型太简单" | 错误假设导致的系统性误差。平均模型预测和真相之间的差距。 |
| Variance | "模型在过拟合" | 对训练数据敏感度导致的误差。预测在不同训练集之间变化多大。 |
| Irreducible error | "数据里的噪声" | 真实数据生成过程里的随机性导致的误差。任何模型都消不掉。 |
| Underfitting | "没学到足够" | 模型高偏差。它在训练数据上都抓不住真实模式。 |
| Overfitting | "记住了数据" | 模型高方差。它拟合了训练数据里的噪声。 |
| Regularization | "约束模型" | 加惩罚来降低模型复杂度，用偏差换更低方差。 |
| Double descent | "更多参数反而有用" | 模型容量远超过插值阈值时测试误差再次下降。 |
| Model complexity | "模型有多灵活" | 模型拟合任意模式的能力。由架构、特征或正则化控制。 |

## Further Reading

- [Hastie, Tibshirani, Friedman: Elements of Statistical Learning, Ch. 7](https://hastie.su.domains/ElemStatLearn/) — 偏差-方差分解的权威论述
- [Belkin et al., Reconciling modern ML practice and the bias-variance trade-off (2019)](https://arxiv.org/abs/1812.11118) — 双下降原论文
- [Nakkiran et al., Deep Double Descent (2019)](https://arxiv.org/abs/1912.02292) — epoch 级和样本级双下降
- [Scott Fortmann-Roe: Understanding the Bias-Variance Tradeoff](http://scott.fortmann-roe.com/docs/BiasVariance.html) — 清晰的可视化解释
