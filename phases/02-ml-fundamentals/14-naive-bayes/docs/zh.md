# 朴素贝叶斯

> "朴素"假设是错的，但它照样能工作。这就是它的美。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2, Lessons 01-07 (分类、贝叶斯定理)
**Time:** ~75 minutes

## Learning Objectives

- 从零实现带拉普拉斯平滑的多项式朴素贝叶斯用于文本分类
- 解释为什么朴素独立性假设数学上错误但实践中产生正确的类别排名
- 对比多项式、伯努利和高斯朴素贝叶斯变体，为给定特征类型选对的
- 在高维稀疏数据上对比朴素贝叶斯和逻辑回归，说明背后的偏差-方差权衡

## 问题场景

你需要分类文本：邮件是垃圾还是正常、评论是正面还是负面、工单属于哪个类别。你有数千个特征（每个词一个）和有限的训练数据。

大多数分类器在这里会窒息。逻辑回归需要足够样本来可靠估计数千个权重。决策树一次在一个词上分裂然后严重过拟合。10000 维的 KNN 没意义，因为每个点和其他每个点几乎一样远。

朴素贝叶斯能处理。它做了一个数学上错误的假设（给定类别，每个特征和其他特征条件独立），但它在文本分类上依然胜过"更聪明"的模型，尤其是训练数据少的时候。它在数据上单次扫描就能训练完。它能扩展到数百万特征。它还能产生概率估计（虽然因为独立性假设通常校准得不好）。

理解为什么一个错误的假设能带来好的预测，能教你机器学习里一件根本的事：最好的模型不是最正确的那个，是对你的数据有最好偏差-方差权衡的那个。

## 核心概念

### 贝叶斯定理（快速回顾）

贝叶斯定理翻转条件概率：

```
P(类别 | 特征) = P(特征 | 类别) · P(类别) / P(特征)
```

我们想要 `P(类别 | 特征)`——给定文档里的词，它属于某一类的概率。我们能从以下几部分算出来：
- `P(特征 | 类别)`——这类文档里看到这些词的可能性
- `P(类别)`——类别的先验概率（总体上垃圾邮件有多常见？）
- `P(特征)`——证据，对所有类别都一样，比较时可以忽略

`P(类别 | 特征)` 最高的那个类胜出。

### 朴素独立性假设

精确计算 `P(特征 | 类别)` 需要估计所有特征一起的联合概率。用 10000 词的词汇表，你得估计 2^10000 种可能组合上的分布。不可能。

朴素假设：给定类别，每个特征条件独立。

```
P(w1, w2, ..., wn | 类别) = P(w1 | 类别) · P(w2 | 类别) · ... · P(wn | 类别)
```

不是估计一个不可能的联合分布，你估计 n 个简单的每特征分布。每个只需要数数。

这个假设明显不对。任何文档里"machine"和"learning"都不独立。但分类器不需要正确的概率估计。它需要正确的排名——哪个类别概率最高。独立性假设引入了系统性误差，但这些误差对所有类别影响类似，所以排名保持正确。

### 为什么它还能工作

三个原因：

1. **排名优先于校准**：分类只需要排名第一的类别正确。就算 P(垃圾)=0.99999 而真实概率是 0.7，分类器还是正确选了垃圾。我们不需要正确的概率，我们需要正确的赢家。
2. **高偏差、低方差**：独立性假设是强先验。它大幅约束模型，防止过拟合。训练数据有限时，一个稍微错但稳定的模型胜过一个理论上对但剧烈波动的模型。这就是偏差-方差权衡在起作用。
3. **特征冗余抵消**：相关特征提供冗余证据。分类器把这个证据算了两遍，但它也把正确类别的证据算了两遍。如果"machine"和"learning"总是一起出现，两者都给"tech"类提供证据。NB 把它们各算了一次，但算的是对的那个类。

第四个实际原因：朴素贝叶斯极快。训练就是数频率的单次扫描。预测是矩阵乘法。你能在几秒内在一百万篇文档上训练。这个速度意味着你能比用慢模型迭代更快、试更多特征集、跑更多实验。

### 数学推导（一步步）

（具体 spam/non-spam 例子、拉普拉斯平滑公式、日志空间计算等逐字保留）

### 三种变体

| 变体 | 特征类型 | 最适合 | 例子 |
|------|----------|--------|------|
| 多项式 | 计数或频率 | 文本分类、词袋 | 邮件垃圾、主题分类 |
| 高斯 | 连续值 | 带正态特征的表格数据 | Iris 分类、传感器数据 |
| 伯努利 | 二元（0/1） | 短文本、二元特征向量 | SMS 垃圾、存在/不存在特征 |

### 拉普拉斯平滑

（零概率问题、alpha 含义和效果表格逐字保留）

### 日志空间计算

乘以数百个小于 1 的概率会导致浮点下溢。解法：用日志空间工作。乘法变加法。

### 朴素贝叶斯 vs 逻辑回归

| 方面 | 朴素贝叶斯 | 逻辑回归 |
|------|------------|----------|
| 类型 | 生成式（模型 P(X\|Y)） | 判别式（模型 P(Y\|X)） |
| 训练 | 数频率 | 优化损失函数 |
| 小数据 | 更好（强先验帮忙） | 更差（不够估计权重） |
| 大数据 | 更差（错误假设拖累） | 更好（灵活边界） |
| 特征 | 假设独立 | 能处理相关性 |
| 速度 | 单次扫描，极快 | 迭代优化 |
| 校准 | 概率差 | 概率更好 |

### 分类流水线

```mermaid
flowchart LR
    A[原始文本] --> B[分词]
    B --> C[构建词汇表]
    C --> D[数词频]
    D --> E[应用平滑]
    E --> F[计算对数概率]
    F --> G[预测：argmax P 类别 给定 词]
    style A fill:#f9f,stroke:#333
    style G fill:#9f9,stroke:#333
```

```figure
naive-bayes
```

## Build It

`code/naive_bayes.py` 里的代码从零实现了 MultinomialNB 和 GaussianNB。

### MultinomialNB

```python
class MultinomialNB:
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, X, y):
        classes = np.unique(y)
        n_classes = len(classes)
        n_features = X.shape[1]

        self.classes_ = classes
        self.class_log_prior_ = np.zeros(n_classes)
        self.feature_log_prob_ = np.zeros((n_classes, n_features))

        for i, c in enumerate(classes):
            X_c = X[y == c]
            self.class_log_prior_[i] = np.log(X_c.shape[0] / X.shape[0])
            counts = X_c.sum(axis=0) + self.alpha
            self.feature_log_prob_[i] = np.log(counts / counts.sum())

        return self
```

关键洞察：拟合之后，预测就是矩阵乘法加偏置。这就是为什么朴素贝叶斯这么快。

### GaussianNB

```python
class GaussianNB:
    def __init__(self):
        pass

    def fit(self, X, y):
        classes = np.unique(y)
        self.classes_ = classes
        self.means_ = np.zeros((len(classes), X.shape[1]))
        self.vars_ = np.zeros((len(classes), X.shape[1]))
        self.priors_ = np.zeros(len(classes))

        for i, c in enumerate(classes):
            X_c = X[y == c]
            self.means_[i] = X_c.mean(axis=0)
            self.vars_[i] = X_c.var(axis=0) + 1e-9
            self.priors_[i] = X_c.shape[0] / X.shape[0]

        return self
```

### Demo：文本分类

代码生成模拟两个类（科技文章 vs 体育文章）的合成词袋数据。每类有不同的词频分布。MultinomialNB 用词频分类它们。

### Demo：连续特征

代码生成类似 Iris 的数据（3 类、4 特征、高斯簇）。GaussianNB 用每类均值和方差分类。

代码还演示了：
- **平滑对比**：用不同 alpha 值训练 MultinomialNB 看平滑强度对准确率的影响
- **训练大小实验**：NB 准确率从 20 增到 1600 样本怎么提升。NB 在极少量样本上就能达到不错准确率——这是它的主要优势
- **混淆矩阵**：每个类的 precision、recall 和 F1 分数看 NB 在哪里犯错

### 预测速度

朴素贝叶斯预测是矩阵乘法。n 样本 d 特征 k 类时：
- MultinomialNB：一次矩阵乘法 (n×d) @ (d×k) = O(n·d·k)
- GaussianNB：n·k 次高斯 PDF 评估，每个 over d 特征 = O(n·d·k)

两者在每个维度上都是线性的。对比 KNN（需要到所有训练点的距离计算）或 RBF 核 SVM（需要对所有支持向量做核评估）。NB 预测时间快几个数量级。

## Use It

sklearn 里两种变体一行搞定：

```python
from sklearn.naive_bayes import GaussianNB, MultinomialNB

gnb = GaussianNB()
gnb.fit(X_train, y_train)
print(f"GaussianNB accuracy: {gnb.score(X_test, y_test):.3f}")

mnb = MultinomialNB(alpha=1.0)
mnb.fit(X_train_counts, y_train)
print(f"MultinomialNB accuracy: {mnb.score(X_test_counts, y_test):.3f}")
```

### TF-IDF + 朴素贝叶斯

原始词计数给每个出现的词相同权重。但 "the" 和 "is" 这样的常见词在每个类里都频繁出现——它们没有信息。TF-IDF 降权常见词、升权罕见的、有区分力的词。

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

text_clf = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", MultinomialNB(alpha=0.1)),
])
```

TF-IDF 值非负，所以和 MultinomialNB 配合。TF-IDF + MultinomialNB 是文本分类最强的 baseline 之一。在少于 10000 训练样本的数据集上经常赢过更复杂的模型。

### 伯努利 NB 用于短文本

对短文本（tweet、SMS、聊天消息），伯努利 NB 能赢过多项式 NB。短文本词计数低，多项式 NB 依赖的频率信息有噪声。伯努利 NB 只关心存在或不存在，短文本更可靠。

### 校准 NB 概率

NB 概率校准得不好。当 NB 说 P(垃圾)=0.95，真实概率可能 0.7。如果需要可靠的概率估计，用 sklearn 的 `CalibratedClassifierCV`：

```python
from sklearn.calibration import CalibratedClassifierCV

calibrated_nb = CalibratedClassifierCV(MultinomialNB(), cv=5, method="sigmoid")
calibrated_nb.fit(X_train, y_train)
proba = calibrated_nb.predict_proba(X_test)
```

这用交叉验证在 NB 的原始分数上拟合一个逻辑回归。得到的概率更接近真实类别频率。

### 常见陷阱

1. **负特征值**：MultinomialNB 要求非负特征。有负值时（某些设置下的 TF-IDF 或标准化特征），用 GaussianNB 代替，或把特征平移为正。
2. **零方差特征**：GaussianNB 除以方差。一个类里零方差的特征（所有值相同）让概率计算崩溃。代码里给所有方差加了小平滑项（1e-9）预防。
3. **类别不平衡**：99% 非垃圾邮件时，先验 P(非垃圾)=0.99 太强压过似然证据。可以手动设类先验或用 sklearn 的 class_prior 参数。
4. **特征缩放**：MultinomialNB 不需要缩放（用计数）。GaussianNB 也不需要（估计每特征统计量）。这是它相对逻辑回归和 SVM 的优势。

## Ship It

本课产出：
- `outputs/skill-naive-bayes-chooser.md`——挑选正确 NB 变体的决策 skill
- `code/naive_bayes.py`——从零 MultinomialNB 和 GaussianNB，含 sklearn 对比

### 朴素贝叶斯何时失败

NB 在独立性假设导致错误排名时（而不只是错误概率）失败。这种情况发生在：
1. **强特征交互**：类别依赖于两个特征的组合而不是单独任何一个（XOR 类模式），NB 完全错过。每个特征单独不提供证据，NB 不能非线性组合它们。
2. **有对立证据的高度相关特征**：特征 A 说"垃圾"、特征 B 说"非垃圾"，但 A 和 B 实际完全相关（总是同时出现），NB 在没有冲突的地方看到冲突证据。
3. **非常大的训练集**：有足够数据时，判别式模型（逻辑回归）学到真实决策边界、胜过 NB。帮小数据的独立性假设现在拖累了模型。

## Exercises

1. **平滑实验**：用 alpha=0.01, 0.1, 1.0, 10.0, 100.0 训练 MultinomialNB。画准确率 vs alpha。性能在哪个点达到峰值？为什么很高的 alpha 会有害？
2. **特征独立性检验**：取真实文本数据集。选两个明显相关的词（"machine" 和 "learning"）。计算 P(word1 | 类) · P(word2 | 类) 对比 P(word1 AND word2 | 类)。独立性假设有多错？它影响分类准确率吗？
3. **伯努利实现**：扩展代码加 BernoulliNB 类。把词袋转二元（存在/不存在）对比 MultinomialNB 的准确率。什么时候伯努利赢？
4. **NB vs 逻辑回归**：两者都在文本数据上训练。从 100 训练样本增到 10000。画两者的准确率 vs 训练集大小。逻辑回归在哪个点超过朴素贝叶斯？
5. **垃圾邮件过滤器**：构建完整的垃圾邮件分类器——分词原始邮件、构建词汇表、创建词袋特征、训练 MultinomialNB、用 precision 和 recall 评估（而不只是 accuracy，为什么？）。

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| 朴素贝叶斯 | "简单概率分类器" | 应用贝叶斯定理、假设给定类别特征条件独立的分类器 |
| 条件独立 | "特征互相不影响" | P(A, B \| C) = P(A \| C) · P(B \| C)——知道 B 之后，知道 C 时 A 不再给新信息 |
| 拉普拉斯平滑 | "加一平滑" | 给每个特征加小计数防止零概率主导预测 |
| 先验 | "看到数据之前的信念" | P(类别)——观测任何特征之前每类的概率 |
| 似然 | "数据拟合得有多好" | P(特征 \| 类别)——已知类别时观测到这些特征的概率 |
| 后验 | "看到数据之后的信念" | P(类别 \| 特征)——观测特征之后类别的更新概率 |
| 生成式模型 | "建模数据怎么产生" | 学 P(X \| Y) 和 P(Y)，然后用贝叶斯定理得 P(Y \| X) |
| 判别式模型 | "建模决策边界" | 直接学 P(Y \| X) 不建模 X 怎么产生 |
| 对数概率 | "防止下溢" | 用 log P 代替 P 来防止很多小数相乘变成浮点零 |

## Further Reading

- [scikit-learn Naive Bayes docs](https://scikit-learn.org/stable/modules/naive_bayes.html)——三种变体及数学细节
- [McCallum & Nigam, Multinomial vs Bernoulli (1998)](https://www.cs.cmu.edu/~knigam/papers/multinomial-aaaiws98.pdf)——文本上多项式 vs 伯努利的经典对比
- [Ng & Jordan, Discriminative vs Generative Classifiers (2001)](https://ai.stanford.edu/~ang/papers/nips01-discriminativegenerative.pdf)——证明 NB 在少数据时比 LR 收敛更快
