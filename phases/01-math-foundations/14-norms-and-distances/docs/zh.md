# 范数与距离

> 你的距离函数定义了「相似」的含义。选错了，下游的一切都会崩溃。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 01 (Linear Algebra Intuition), 02 (Vectors, Matrices & Operations)
**Time:** ~90 minutes

## 学习目标

- 从零实现 L1、L2、余弦、Mahalanobis、Jaccard 和编辑距离函数
- 为给定的 ML 任务选择合适的距离度量，并解释为什么其他备选会失败
- 把 L1 和 L2 范数与 LASSO 和 Ridge 正则化及其几何约束区域联系起来
- 演示同一数据集在不同度量下如何产生不同的最近邻

## 问题

你有两个向量。也许它们是词嵌入。也许它们是用户画像。也许它们是像素数组。你需要知道：它们有多接近？

答案完全取决于你选择哪个距离函数。两个数据点在一个度量下可能是最近邻，在另一个度量下可能相距很远。你的 KNN 分类器、你的推荐引擎、你的向量数据库、你的聚类算法、你的损失函数——它们全都依赖这个选择。选错了，你的模型就会优化错误的目标。

不存在普适的最优距离。L2 适用于空间数据。余弦相似度主导 NLP。Jaccard 处理集合。编辑距离处理字符串。Mahalanobis 考虑相关性。Wasserstein 搬运概率质量。每一种都编码了对「相似」含义的不同假设。

本课从零构建每一个主要的距离函数，展示每一种何时是正确的工具，并演示同一数据在不同度量下如何产生完全不同的最近邻。

## 概念

### 范数：度量向量的大小

范数度量一个向量的「大小」。两个向量之间的每一个距离函数都可以写成它们差值的范数：d(a, b) = ||a - b||。所以理解范数就是理解距离。

### L1 范数（曼哈顿距离）

L1 范数对所有分量的绝对值求和。

```
||x||_1 = |x_1| + |x_2| + ... + |x_n|
```

它被称为曼哈顿距离，是因为它度量的是你在只能沿轴线移动的城市街区网格上走多远。没有对角线。

```
Point A = (1, 1)
Point B = (4, 5)

L1 distance = |4-1| + |5-1| = 3 + 4 = 7

On a grid, you walk 3 blocks east and 4 blocks north.
```

何时使用 L1：

- 高维稀疏数据（文本特征、独热编码）
- 当你想要抗异常值的鲁棒性时（单个巨大的差异不会主导）
- 特征选择问题（L1 正则化促进稀疏性）

与 L1 正则化（Lasso）的关联：给损失函数加上 ||w||_1 会惩罚权重的绝对值之和。这把小的权重精确推到零，实现自动特征选择。L1 惩罚在权重空间中创造菱形约束区域，而菱形的角位于坐标轴上，那里某些权重为零。

与损失函数的关联：平均绝对误差（MAE）是预测值与目标值之间的平均 L1 距离。它线性地惩罚所有误差，因此相比 MSE 对异常值更鲁棒。

### L2 范数（欧几里得距离）

L2 范数是直线距离。各分量平方和的平方根。

```
||x||_2 = sqrt(x_1^2 + x_2^2 + ... + x_n^2)
```

这是你在几何课上学到的距离。n 维空间中的毕达哥拉斯定理。

```
Point A = (1, 1)
Point B = (4, 5)

L2 distance = sqrt((4-1)^2 + (5-1)^2) = sqrt(9 + 16) = sqrt(25) = 5.0

The straight line, cutting diagonally through the grid.
```

何时使用 L2：

- 低到中维的连续数据
- 当特征尺度可比较时
- 物理距离（空间数据、传感器读数）
- 像素级的图像相似度

与 L2 正则化（Ridge）的关联：给损失函数加上 ||w||_2^2 会惩罚大的权重。与 L1 不同，它不会把权重推到零。它按比例把所有权重向零收缩。L2 惩罚创造圆形约束区域，所以坐标轴上没有角。权重会变小，但很少精确为零。

与损失函数的关联：均方误差（MSE）是 L2 距离平方的平均值。平方化对大误差的惩罚比小误差更重。

```
MAE (L1 loss):  |y - y_hat|         Linear penalty. Robust to outliers.
MSE (L2 loss):  (y - y_hat)^2       Quadratic penalty. Sensitive to outliers.
```

### Lp 范数：一般家族

L1 和 L2 是 Lp 范数的特例：

```
||x||_p = (|x_1|^p + |x_2|^p + ... + |x_n|^p)^(1/p)
```

不同的 p 值产生不同形状的「单位球」（到原点距离为 1 的所有点的集合）：

```
p=1:    Diamond shape      (corners on axes)
p=2:    Circle/sphere      (the usual round ball)
p=3:    Superellipse       (rounded square)
p=inf:  Square/hypercube   (flat sides along axes)
```

### L-无穷范数（切比雪夫距离）

当 p 趋近无穷时，Lp 范数收敛于最大绝对值分量。

```
||x||_inf = max(|x_1|, |x_2|, ..., |x_n|)
```

两点之间的距离由它们相差最大的那一个维度决定。所有其他维度都被忽略。

```
Point A = (1, 1)
Point B = (4, 5)

L-inf distance = max(|4-1|, |5-1|) = max(3, 4) = 4
```

何时使用 L-无穷：

- 当任何单一维度上的最坏情况偏差很重要时
- 棋盘（国际象棋中的国王按 L-无穷移动：朝任何方向走一步的代价都是 1）
- 制造公差（每个维度都必须在规格之内）

### 余弦相似度与余弦距离

余弦相似度度量两个向量之间的夹角，忽略它们的幅度。

```
cos_sim(a, b) = (a . b) / (||a||_2 * ||b||_2)
```

它的范围从 -1（方向相反）到 +1（方向相同）。垂直的向量余弦相似度为 0。

余弦距离把它转换成距离：cosine_distance = 1 - cosine_similarity。范围从 0（方向相同）到 2（方向相反）。

```
a = (1, 0)    b = (1, 1)

cos_sim = (1*1 + 0*1) / (1 * sqrt(2)) = 1/sqrt(2) = 0.707
cos_dist = 1 - 0.707 = 0.293
```

为什么余弦主导 NLP 和嵌入：在文本中，文档长度不应影响相似度。一篇关于猫的文档即使长度是另一篇关于猫的文档的两倍，它们仍然应该「相似」。余弦相似度忽略幅度（长度），只关心方向。两篇词分布相同但长度不同的文档指向同一方向，得到 1.0 的余弦相似度。

何时使用余弦相似度：

- 文本相似度（TF-IDF 向量、词嵌入、句子嵌入）
- 任何幅度是噪声、方向是信号的领域
- 推荐系统（用户偏好向量）
- 嵌入搜索（向量数据库几乎总用余弦或点积）

### 点积相似度 vs 余弦相似度

两个向量的点积是：

```
a . b = a_1*b_1 + a_2*b_2 + ... + a_n*b_n
      = ||a|| * ||b|| * cos(angle)
```

余弦相似度是以两个幅度归一化后的点积。当两个向量已经单位归一化（幅度 = 1）时，点积和余弦相似度相同。

```
If ||a|| = 1 and ||b|| = 1:
    a . b = cos(angle between a and b)
```

它们的不同之处：点积包含幅度信息。幅度更大的向量得到更高的点积分。在某些检索系统中这一点很重要——你想让「热门」条目排名更高。幅度充当隐式的质量或重要性信号。

```
a = (3, 0)    b = (1, 0)    c = (0, 1)

dot(a, b) = 3     dot(a, c) = 0
cos(a, b) = 1.0   cos(a, c) = 0.0

Both agree on direction, but dot product also reflects magnitude.
```

实践中：

- 当你想要纯粹的方向相似度时，使用余弦相似度
- 当幅度携带有意义的信息时，使用点积
- 许多向量数据库（Pinecone、Weaviate、Qdrant）让你在两者之间选择
- 如果你的嵌入是 L2 归一化的，这个选择无所谓

### Mahalanobis 距离

欧几里得距离平等地对待所有维度。但如果你的特征相关或尺度不同，L2 会给出误导性结果。

Mahalanobis 距离考虑了数据的协方差结构。

```
d_M(x, y) = sqrt((x - y)^T * S^(-1) * (x - y))
```

其中 S 是数据的协方差矩阵。

直观地说：Mahalanobis 距离先把数据去相关并归一化（白化），然后在这个变换后的空间中计算 L2 距离。如果 S 是单位矩阵（特征不相关、单位方差），Mahalanobis 距离退化为欧几里得距离。

```
Example: height and weight are correlated.
Someone 6'2" and 180 lbs is not unusual.
Someone 5'0" and 180 lbs is unusual.

Euclidean distance might say they are equally far from the mean.
Mahalanobis distance correctly identifies the second as an outlier
because it accounts for the height-weight correlation.
```

何时使用 Mahalanobis 距离：

- 异常检测（到均值的 Mahalanobis 距离大的点是异常点）
- 当特征有不同的尺度和相关性时的分类
- 当你有足够数据来估计可靠的协方差矩阵时
- 制造业的质量控制（多元过程监控）

### Jaccard 相似度（用于集合）

Jaccard 相似度度量两个集合之间的重叠。

```
J(A, B) = |A intersect B| / |A union B|
```

范围从 0（无重叠）到 1（集合相同）。Jaccard 距离 = 1 - Jaccard 相似度。

```
A = {cat, dog, fish}
B = {cat, bird, fish, snake}

Intersection = {cat, fish}         size = 2
Union = {cat, dog, fish, bird, snake}  size = 5

Jaccard similarity = 2/5 = 0.4
Jaccard distance = 0.6
```

何时使用 Jaccard：

- 比较标签、类别或特征的集合
- 基于词是否出现（而非词频）的文档相似度
- 近似重复检测（Jaccard 的 MinHash 近似）
- 比较二值特征向量（有无数据）
- 评估分割模型（交并比 = Jaccard）

### 编辑距离（Levenshtein 距离）

编辑距离计算把一个字符串转换成另一个字符串所需的最少单字符操作次数。操作包括：插入、删除或替换。

```
"kitten" -> "sitting"

kitten -> sitten  (substitute k -> s)
sitten -> sittin  (substitute e -> i)
sittin -> sitting (insert g)

Edit distance = 3
```

使用动态规划计算。填充一个矩阵，其中条目 (i, j) 是字符串 A 的前 i 个字符与字符串 B 的前 j 个字符之间的编辑距离。

```
        ""  s  i  t  t  i  n  g
    ""   0  1  2  3  4  5  6  7
    k    1  1  2  3  4  5  6  7
    i    2  2  1  2  3  4  5  6
    t    3  3  2  1  2  3  4  5
    t    4  4  3  2  1  2  3  4
    e    5  5  4  3  2  2  3  4
    n    6  6  5  4  3  3  2  3
```

何时使用编辑距离：

- 拼写检查和纠错
- DNA 序列比对（带加权操作）
- 模糊字符串匹配
- 杂乱文本数据的去重

### KL 散度（不是距离，但被当作距离用）

KL 散度度量一个概率分布与另一个的差异。它在第 09 课讲过，但它属于这里的讨论，因为人们把它当作「距离」来用，尽管它并不是距离。

```
D_KL(P || Q) = sum(p(x) * log(p(x) / q(x)))
```

关键性质：KL 散度不对称。

```
D_KL(P || Q) != D_KL(Q || P)
```

这意味着它不满足距离度量的基本要求。它也不满足三角不等式。它是散度，不是距离。

前向 KL（D_KL(P || Q)）是「均值追寻」：Q 试图覆盖 P 的所有众数。
反向 KL（D_KL(Q || P)）是「众数追寻」：Q 聚焦于 P 的单个众数。

当你看到 KL 散度时：

- VAE（ELBO 中的 KL 项把隐分布推向先验）
- 知识蒸馏（学生试图匹配教师的分布）
- RLHF（KL 惩罚让微调后的模型保持接近基座模型）
- 策略梯度方法（约束策略更新）

### Wasserstein 距离（推土机距离）

Wasserstein 距离度量把一个概率分布转换成另一个所需的最小「功」。可以这样想：如果一个分布是一堆泥土，而另一个是一个坑，你需要搬多少泥土、搬多远？

```
W(P, Q) = inf over all transport plans gamma of E[d(x, y)]
```

对于一维分布，它简化为累积分布函数绝对差的积分：

```
W_1(P, Q) = integral |CDF_P(x) - CDF_Q(x)| dx
```

为什么 Wasserstein 重要：

- 它是一个真正的度量（对称、满足三角不等式）
- 即使分布不重叠，它也提供梯度（KL 散度会趋于无穷）
- 这一性质使它成为 Wasserstein GAN（WGAN）的核心，解决了原始 GAN 的训练不稳定问题

```
Distributions with no overlap:

P: [1, 0, 0, 0, 0]    Q: [0, 0, 0, 0, 1]

KL divergence: infinity (log of zero)
Wasserstein: 4 (move all mass 4 bins)

Wasserstein gives a meaningful gradient. KL does not.
```

何时使用 Wasserstein：

- GAN 训练（WGAN、WGAN-GP）
- 比较可能不重叠的分布
- 最优传输问题
- 图像检索（比较颜色直方图）

### 为什么不同任务需要不同距离

| 任务 | 最佳距离 | 为什么 |
|------|--------------|-----|
| 文本相似度 | Cosine | 幅度是噪声，方向才是含义 |
| 图像像素比较 | L2 | 空间关系重要，特征尺度可比较 |
| 稀疏高维特征 | L1 | 鲁棒，不放大罕见的大差异 |
| 集合重叠（标签、类别） | Jaccard | 数据天然是集合值的，而非向量 |
| 字符串匹配 | Edit distance | 操作对应人类的编辑直觉 |
| 异常检测 | Mahalanobis | 考虑特征相关性和尺度 |
| 比较分布 | KL divergence | 度量用 Q 代替 P 所损失的信息 |
| GAN 训练 | Wasserstein | 即使分布不重叠也提供梯度 |
| 嵌入（向量数据库） | Cosine or dot product | 嵌入被训练为在方向上编码含义 |
| 推荐 | Dot product | 幅度可以编码流行度或置信度 |
| DNA 序列 | Weighted edit distance | 替换代价因核苷酸对而异 |
| 制造业质量控制 | L-infinity | 任何维度上的最坏情况偏差都很重要 |

### 与损失函数的关联

损失函数是应用到预测值与目标值上的距离函数。

```
Loss function       Distance it uses       Behavior
MSE                 L2 squared             Penalizes large errors heavily
MAE                 L1                     Penalizes all errors equally
Huber loss          L1 for large errors,   Best of both: robust to outliers,
                    L2 for small errors    smooth gradient near zero
Cross-entropy       KL divergence          Measures distribution mismatch
Hinge loss          max(0, margin - d)     Only penalizes below margin
Triplet loss        L2 (typically)         Pulls positives close, pushes
                                           negatives away
Contrastive loss    L2                     Similar pairs close, dissimilar
                                           pairs beyond margin
```

### 与正则化的关联

正则化给损失函数加上权重的范数惩罚。

```
L1 regularization (Lasso):   loss + lambda * ||w||_1
  -> Sparse weights. Some weights become exactly zero.
  -> Automatic feature selection.
  -> Solution has corners (non-differentiable at zero).

L2 regularization (Ridge):   loss + lambda * ||w||_2^2
  -> Small weights. All weights shrink toward zero.
  -> No feature selection (nothing goes to exactly zero).
  -> Smooth solution everywhere.

Elastic Net:                  loss + lambda_1 * ||w||_1 + lambda_2 * ||w||_2^2
  -> Combines sparsity of L1 with stability of L2.
  -> Groups of correlated features are kept or dropped together.
```

为什么 L1 产生稀疏而 L2 不会：想象二维权重空间中的约束区域。L1 是菱形，L2 是圆形。损失函数的等高线（椭圆）最可能在一个角上碰到菱形，那里某个权重为零。它们在圆形上则是碰在平滑点，那里两个权重都非零。

### 最近邻搜索

每个距离函数都隐含一个最近邻搜索问题：给定一个查询点，在数据集中找到最近的点。

精确最近邻搜索在 n 个点、d 维的数据集中每次查询的复杂度是 O(n * d)。对于大数据集，这太慢了。

近似最近邻（ANN）算法以少量准确率为代价换取巨大的速度提升：

```
Algorithm         Approach                      Used by
KD-trees          Axis-aligned space partition   scikit-learn (low-dim)
Ball trees        Nested hyperspheres            scikit-learn (medium-dim)
LSH               Random hash projections        Near-duplicate detection
HNSW              Hierarchical navigable         FAISS, Qdrant, Weaviate
                  small-world graph
IVF               Inverted file index with       FAISS (billion-scale)
                  cluster-based search
Product quant.    Compress vectors, search       FAISS (memory-constrained)
                  in compressed space
```

HNSW（Hierarchical Navigable Small World，分层可导航小世界）是现代向量数据库中的主导算法。它构建一个多层图，每个节点连接到它的近似最近邻。搜索从顶层（稀疏、长跳）开始，下降到最底层（密集、短跳）。

```figure
norm-unit-balls
```

## Build It

### 步骤 1：所有范数和距离函数

完整实现见 `code/distances.py`。每个函数都只用基础 Python 数学从零构建。

### 步骤 2：相同数据、不同距离、不同邻居

`distances.py` 中的演示创建一个数据集、挑选一个查询点，并展示最近邻如何随距离度量的不同而变化。在 L1 下「最近」的点，在 L2 或余弦下未必最近。

### 步骤 3：嵌入相似度搜索

代码包含一个模拟的嵌入相似度搜索，分别用余弦相似度和 L2 距离查找与查询最相似的「文档」，展示排名可能不同。

## Use It

最常见的实际用途：在向量数据库中查找相似项。

```python
import numpy as np

def cosine_similarity_matrix(X):
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    X_normalized = X / norms
    return X_normalized @ X_normalized.T

embeddings = np.random.randn(1000, 768)

sim_matrix = cosine_similarity_matrix(embeddings)

query_idx = 0
similarities = sim_matrix[query_idx]
top_k = np.argsort(similarities)[::-1][1:6]
print(f"Top 5 most similar to item 0: {top_k}")
print(f"Similarities: {similarities[top_k]}")
```

当你调用 `model.encode(text)` 然后在向量数据库中搜索时，底层发生的就是这些。嵌入模型把文本映射为向量。向量数据库计算你的查询向量与每个存储向量之间的余弦相似度（或点积），并使用 ANN 算法避免检查全部向量。

## 练习

1. **三种范数。** 计算 (1, 2, 3) 和 (4, 0, 6) 之间的 L1、L2 和 L-无穷距离。验证对任何一对点，L-无穷 <= L2 <= L1 始终成立。证明为什么这个排序有保证。

2. **余弦与 L2 的反差。** 构造两个向量，使余弦相似度高（> 0.9）但 L2 距离大（> 10）。从几何上解释发生了什么。然后构造两个向量，使余弦相似度低（< 0.3）但 L2 距离小（< 0.5）。

3. **四度量分歧。** 实现一个函数，接受一个数据集和一个查询点，返回 L1、L2、余弦和 Mahalanobis 距离下的最近邻。找一个数据集，使四种度量在哪个点最近上意见全部不一致。

4. **手算 Wasserstein。** 用手算（CDF 方法）计算 [0.5, 0.5, 0, 0] 和 [0, 0, 0.5, 0.5] 之间的 Wasserstein 距离。然后计算 [0.25, 0.25, 0.25, 0.25] 和 [0, 0, 0.5, 0.5] 之间的。哪个更大，为什么？

5. **MinHash 近似。** 实现 MinHash 做近似 Jaccard 相似度。生成 100 个随机集合，计算所有对的精确 Jaccard，并与使用 50、100、200 个哈希函数的 MinHash 近似比较。画出近似误差。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Norm | 「向量的大小」 | 把一个向量映射到一个非负标量的函数，满足三角不等式、绝对齐次性，且仅对零向量取零 |
| L1 norm | 「曼哈顿距离」 | 各分量绝对值之和。在优化中产生稀疏性。抗异常值 |
| L2 norm | 「欧几里得距离」 | 各分量平方和的平方根。欧几里得空间中的直线距离 |
| Lp norm | 「广义范数」 | 各分量绝对值的 p 次方之和的 p 次方根。L1 和 L2 是特例 |
| L-infinity norm | 「最大范数」或「切比雪夫距离」 | 最大绝对值分量。Lp 在 p 趋近无穷时的极限 |
| Cosine similarity | 「向量之间的夹角」 | 被两个幅度归一化后的点积。范围从 -1 到 +1。忽略向量长度 |
| Cosine distance | 「1 减余弦相似度」 | 把余弦相似度转换成距离。范围从 0 到 2 |
| Dot product | 「未归一化的余弦」 | 各分量乘积之和。等于余弦相似度乘以两个幅度 |
| Mahalanobis distance | 「相关性感知距离」 | 在用数据协方差矩阵白化（去相关并归一化）后的空间中的 L2 距离 |
| Jaccard similarity | 「集合重叠」 | 交集大小除以并集大小。用于集合，而非向量 |
| Edit distance | 「Levenshtein 距离」 | 把一个字符串转换成另一个所需的最少插入、删除和替换次数 |
| KL divergence | 「分布之间的距离」 | 不是真正的距离（不对称）。度量用 Q 编码 P 所需的额外比特数 |
| Wasserstein distance | 「推土机距离」 | 把质量从一个分布搬运到另一个所需的最小功。一个真正的度量 |
| Approximate nearest neighbor | 「ANN 搜索」 | 以远快于精确搜索的速度找到近似最近点的算法（HNSW、LSH、IVF） |
| HNSW | 「那个向量数据库算法」 | 分层可导航小世界图。用于快速近似最近邻搜索的多层图 |
| L1 regularization | 「Lasso」 | 给损失加上权重的 L1 范数。把权重推向零（稀疏性） |
| L2 regularization | 「Ridge」或「权重衰减」 | 给损失加上权重的平方 L2 范数。把权重向零收缩，但没有稀疏性 |
| Elastic Net | 「L1 + L2」 | 结合 L1 和 L2 正则化。比单独使用任一者更好地处理相关特征组 |

## 延伸阅读

- [FAISS: A Library for Efficient Similarity Search](https://github.com/facebookresearch/faiss) — Meta 用于十亿级 ANN 搜索的库
- [Wasserstein GAN (Arjovsky et al., 2017)](https://arxiv.org/abs/1701.07875) — 把推土机距离引入 GAN 的论文
- [Locality-Sensitive Hashing (Indyk & Motwani, 1998)](https://dl.acm.org/doi/10.1145/276698.276876) — 基础性的 ANN 算法
- [Efficient Estimation of Word Representations (Mikolov et al., 2013)](https://arxiv.org/abs/1301.3781) — Word2Vec，余弦相似度从此成为嵌入的默认选择
- [sklearn.neighbors documentation](https://scikit-learn.org/stable/modules/neighbors.html) — scikit-learn 中距离度量与邻居算法的实用指南