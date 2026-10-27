# 线性代数直觉

> 每个 AI 模型都只是戴着花哨帽子的矩阵运算。

**Type:** Learn
**Languages:** Python, Julia
**Prerequisites:** Phase 0
**Time:** ~60 minutes

## 学习目标

- 在 Python 中从零实现向量和矩阵运算（加法、点积、矩阵乘法）
- 从几何上解释点积、投影和 Gram-Schmidt 正交化过程做了什么
- 使用行化简确定一组向量的线性相关性、秩和基
- 将线性代数概念与它们的 AI 应用联系起来：嵌入、注意力分数和 LoRA

## 问题

翻开任意一篇 ML 论文。在第一页之内，你就会看到向量、矩阵、点积和变换。没有线性代数的直觉，这些只是一堆符号。有了它，你就能看到神经网络实际在做什么——在空间中移动点。

你不需要成为数学家。你需要看到这些运算在几何上意味着什么，然后自己动手写代码。

## 概念

### 向量是点（也是方向）

向量只是一个数字列表。但这些数字有含义——它们是空间中的坐标。

**二维向量 [3, 2]：**

| x | y | 点 |
|---|---|-------|
| 3 | 2 | 该向量从原点 (0,0) 指向平面上的 (3, 2) |

该向量的长度为 sqrt(3^2 + 2^2) = sqrt(13)，方向为右上方。

在 AI 中，向量代表一切：
- 一个词 → 由 768 个数字组成的向量（它在嵌入空间中的「含义」）
- 一张图像 → 由数百万个像素值组成的向量
- 一个用户 → 一个偏好向量

### 矩阵是变换

矩阵将一个向量变换成另一个向量。它可以旋转、缩放、拉伸或投影。

```mermaid
graph LR
    subgraph Before
        A["Point A"]
        B["Point B"]
    end
    subgraph Matrix["Matrix Multiplication"]
        M["M (transformation)"]
    end
    subgraph After
        A2["Point A'"]
        B2["Point B'"]
    end
    A --> M
    B --> M
    M --> A2
    M --> B2
```

在 AI 中，矩阵就是模型本身：
- 神经网络权重 → 将输入变换为输出的矩阵
- 注意力分数 → 决定关注什么的矩阵
- 嵌入 → 将词映射为向量的矩阵

### 点积衡量相似度

两个向量的点积告诉你它们有多相似。

```
a · b = a₁×b₁ + a₂×b₂ + ... + aₙ×bₙ

方向相同：      a · b > 0  （相似）
垂直：          a · b = 0  （无关）
方向相反：      a · b < 0  （不相似）
```

这正是搜索引擎、推荐系统和 RAG 的工作原理——找到点积高的向量。

### 线性相关性

如果集合中没有向量可以写成其他向量的组合，这些向量就是线性无关的。如果 v1、v2、v3 是无关的，它们张成一个 3D 空间。如果其中一个是其他向量的组合，它们就只张成一个平面。

为什么这对 AI 重要：你的特征矩阵应该有线性无关的列。如果两个特征完全相关（线性相关），模型就无法区分它们各自的影响。这会导致回归中的多重共线性——权重矩阵变得不稳定，输入的微小变化会造成输出的剧烈波动。

**具体例子：**

```
v1 = [1, 0, 0]
v2 = [0, 1, 0]
v3 = [2, 1, 0]   # v3 = 2*v1 + v2
```

v1 和 v2 是无关的——二者谁都不是对方的标量倍数或组合。但 v3 = 2*v1 + v2，所以 {v1, v2, v3} 是一个相关的集合。这三个向量都位于 xy 平面内。无论你如何组合它们，都无法到达 [0, 0, 1]。你有三个向量，但只有两个维度的自由度。

在数据集中：如果 feature_3 = 2*feature_1 + feature_2，那么加入 feature_3 给模型带来的新信息为零。更糟的是，它会让正规方程变得奇异——权重不存在唯一解。

### 基与秩

基是张成整个空间的最小线性无关向量集。基向量的数量就是空间的维数。

3D 空间的标准基是 {[1,0,0], [0,1,0], [0,0,1]}。但 3D 中任意三个无关向量也构成合法的基。基的选择就是坐标系的选择。

矩阵的秩 = 线性无关列的数量 = 线性无关行的数量。如果秩 < min(行数, 列数)，该矩阵就是秩亏的。这意味着：
- 方程组有无穷多解（或无解）
- 变换中丢失了信息
- 矩阵不可逆

| 情形 | 秩 | 对 ML 意味着什么 |
|-----------|------|---------------------|
| 满秩（秩 = min(m, n)） | 最大可能值 | 存在唯一最小二乘解。模型是良态的。 |
| 秩亏（秩 < min(m, n)） | 低于最大值 | 特征冗余。有无穷多个权重解。需要正则化。 |
| 秩 1 | 1 | 每一列都是某个向量的缩放副本。所有数据都落在一条直线上。 |
| 近似秩亏（奇异值很小） | 数值上很低 | 矩阵是病态的。微小输入噪声会造成巨大输出变化。使用 SVD 截断或岭回归。 |

### 投影

把向量 **a** 投影到向量 **b** 上，得到 **a** 在 **b** 方向上的分量：

```
proj_b(a) = (a dot b / b dot b) * b
```

残差 (a - proj_b(a)) 垂直于 b。这种正交分解是最小二乘拟合的基础。

投影在 ML 中无处不在：
- 线性回归最小化观测点到列空间的距离——解本身就是一次投影
- PCA 把数据投影到方差最大的方向上
- Transformer 中的注意力计算 query 到 key 的投影

```mermaid
graph LR
    subgraph Projection["Projection of a onto b"]
        direction TB
        O["Origin"] --> |"b (direction)"| B["b"]
        O --> |"a (original)"| A["a"]
        O --> |"proj_b(a)"| P["projection"]
        A -.-> |"residual (perpendicular)"| P
    end
```

**例子：** a = [3, 4], b = [1, 0]

proj_b(a) = (3*1 + 4*0) / (1*1 + 0*0) * [1, 0] = 3 * [1, 0] = [3, 0]

投影丢掉了 y 分量。这是最简单的降维形式——扔掉你不关心的方向。

### Gram-Schmidt 过程

把任意一组无关向量转换成正交规范基。正交规范意味着每个向量长度为 1，且每对向量相互垂直。

算法：
1. 取第一个向量，归一化
2. 取第二个向量，减去它到第一个向量上的投影，归一化
3. 取第三个向量，减去它到所有先前向量上的投影，归一化
4. 对剩余向量重复

```
Input:  v1, v2, v3, ... (linearly independent)

u1 = v1 / |v1|

w2 = v2 - (v2 dot u1) * u1
u2 = w2 / |w2|

w3 = v3 - (v3 dot u1) * u1 - (v3 dot u2) * u2
u3 = w3 / |w3|

Output: u1, u2, u3, ... (orthonormal basis)
```

QR 分解内部就是这么做的。Q 是正交规范基，R 记录投影系数。QR 分解用于：
- 求解线性方程组（比高斯消元更稳定）
- 计算特征值（QR 算法）
- 最小二乘回归（标准数值方法）

```figure
eigen-directions
```

## Build It

### 第 1 步：从零实现向量（Python）

```python
class Vector:
    def __init__(self, components):
        self.components = list(components)
        self.dim = len(self.components)

    def __add__(self, other):
        return Vector([a + b for a, b in zip(self.components, other.components)])

    def __sub__(self, other):
        return Vector([a - b for a, b in zip(self.components, other.components)])

    def dot(self, other):
        return sum(a * b for a, b in zip(self.components, other.components))

    def magnitude(self):
        return sum(x**2 for x in self.components) ** 0.5

    def normalize(self):
        mag = self.magnitude()
        return Vector([x / mag for x in self.components])

    def cosine_similarity(self, other):
        return self.dot(other) / (self.magnitude() * other.magnitude())

    def __repr__(self):
        return f"Vector({self.components})"


a = Vector([1, 2, 3])
b = Vector([4, 5, 6])

print(f"a + b = {a + b}")
print(f"a · b = {a.dot(b)}")
print(f"|a| = {a.magnitude():.4f}")
print(f"cosine similarity = {a.cosine_similarity(b):.4f}")
```

### 第 2 步：从零实现矩阵（Python）

```python
class Matrix:
    def __init__(self, rows):
        self.rows = [list(row) for row in rows]
        self.shape = (len(self.rows), len(self.rows[0]))

    def __matmul__(self, other):
        if isinstance(other, Vector):
            return Vector([
                sum(self.rows[i][j] * other.components[j] for j in range(self.shape[1]))
                for i in range(self.shape[0])
            ])
        rows = []
        for i in range(self.shape[0]):
            row = []
            for j in range(other.shape[1]):
                row.append(sum(
                    self.rows[i][k] * other.rows[k][j]
                    for k in range(self.shape[1])
                ))
            rows.append(row)
        return Matrix(rows)

    def transpose(self):
        return Matrix([
            [self.rows[j][i] for j in range(self.shape[0])]
            for i in range(self.shape[1])
        ])

    def __repr__(self):
        return f"Matrix({self.rows})"


rotation_90 = Matrix([[0, -1], [1, 0]])
point = Vector([3, 1])

rotated = rotation_90 @ point
print(f"Original: {point}")
print(f"Rotated 90°: {rotated}")
```

### 第 3 步：为什么这对 AI 很重要

```python
import random

random.seed(42)
weights = Matrix([[random.gauss(0, 0.1) for _ in range(3)] for _ in range(2)])
input_vector = Vector([1.0, 0.5, -0.3])

output = weights @ input_vector
print(f"Input (3D): {input_vector}")
print(f"Output (2D): {output}")
print("This is what a neural network layer does -- matrix multiplication.")
```

### 第 4 步：Julia 版本

```julia
a = [1.0, 2.0, 3.0]
b = [4.0, 5.0, 6.0]

println("a + b = ", a + b)
println("a · b = ", a ⋅ b)       # Julia supports unicode operators
println("|a| = ", √(a ⋅ a))
println("cosine = ", (a ⋅ b) / (√(a ⋅ a) * √(b ⋅ b)))

# Matrix-vector multiplication
W = [0.1 -0.2 0.3; 0.4 0.5 -0.1]
x = [1.0, 0.5, -0.3]
println("Wx = ", W * x)
println("This is a neural network layer.")
```

### 第 5 步：从零实现线性相关性与投影（Python）

```python
def is_linearly_independent(vectors):
    n = len(vectors)
    dim = len(vectors[0].components)
    mat = Matrix([v.components[:] for v in vectors])
    rows = [row[:] for row in mat.rows]
    rank = 0
    for col in range(dim):
        pivot = None
        for row in range(rank, len(rows)):
            if abs(rows[row][col]) > 1e-10:
                pivot = row
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][col]
        rows[rank] = [x / scale for x in rows[rank]]
        for row in range(len(rows)):
            if row != rank and abs(rows[row][col]) > 1e-10:
                factor = rows[row][col]
                rows[row] = [rows[row][j] - factor * rows[rank][j] for j in range(dim)]
        rank += 1
    return rank == n


def project(a, b):
    scalar = a.dot(b) / b.dot(b)
    return Vector([scalar * x for x in b.components])


def gram_schmidt(vectors):
    orthonormal = []
    for v in vectors:
        w = v
        for u in orthonormal:
            proj = project(w, u)
            w = w - proj
        if w.magnitude() < 1e-10:
            continue
        orthonormal.append(w.normalize())
    return orthonormal


v1 = Vector([1, 0, 0])
v2 = Vector([1, 1, 0])
v3 = Vector([1, 1, 1])
basis = gram_schmidt([v1, v2, v3])
for i, u in enumerate(basis):
    print(f"u{i+1} = {u}")
    print(f"  |u{i+1}| = {u.magnitude():.6f}")

print(f"u1 · u2 = {basis[0].dot(basis[1]):.6f}")
print(f"u1 · u3 = {basis[0].dot(basis[2]):.6f}")
print(f"u2 · u3 = {basis[1].dot(basis[2]):.6f}")
```

## Use It

现在用 NumPy 做同样的事——你在实践中真正会用的：

```python
import numpy as np

a = np.array([1, 2, 3], dtype=float)
b = np.array([4, 5, 6], dtype=float)

print(f"a + b = {a + b}")
print(f"a · b = {np.dot(a, b)}")
print(f"|a| = {np.linalg.norm(a):.4f}")
print(f"cosine = {np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)):.4f}")

W = np.random.randn(2, 3) * 0.1
x = np.array([1.0, 0.5, -0.3])
print(f"Wx = {W @ x}")
```

### 用 NumPy 计算秩、投影和 QR

```python
import numpy as np

A = np.array([[1, 2], [2, 4]])
print(f"Rank: {np.linalg.matrix_rank(A)}")

a = np.array([3, 4])
b = np.array([1, 0])
proj = (np.dot(a, b) / np.dot(b, b)) * b
print(f"Projection of {a} onto {b}: {proj}")

Q, R = np.linalg.qr(np.random.randn(3, 3))
print(f"Q is orthogonal: {np.allclose(Q @ Q.T, np.eye(3))}")
print(f"R is upper triangular: {np.allclose(R, np.triu(R))}")
```

### PyTorch —— 张量是带自动微分的向量

```python
import torch

x = torch.randn(3, requires_grad=True)
y = torch.tensor([1.0, 0.0, 0.0])

similarity = torch.dot(x, y)
similarity.backward()

print(f"x = {x.data}")
print(f"y = {y.data}")
print(f"dot product = {similarity.item():.4f}")
print(f"d(dot)/dx = {x.grad}")
```

点积关于 x 的梯度恰好是 y。PyTorch 自动算出了这一点。神经网络中的每一次运算都由这样的运算构成——矩阵乘法、点积、投影——而自动微分追踪贯穿所有这些运算的梯度。

你刚刚从零构建了 NumPy 一行代码就能完成的东西。现在你知道底层发生了什么。

## Ship It

本课产出：
- `outputs/prompt-linear-algebra-tutor.md` —— 一个提示词，让 AI 助手通过几何直觉来教线性代数

## 关联

本课中的每个内容都与现代 AI 的具体部分相关：

| 概念 | 它出现在哪里 |
|---------|------------------|
| 点积 | Transformer 中的注意力分数、RAG 中的余弦相似度 |
| 矩阵乘法 | 每一个神经网络层、每一次线性变换 |
| 线性相关性 | 特征选择、避免多重共线性 |
| 秩 | 判断方程组是否可解、LoRA（低秩适配） |
| 投影 | 线性回归（投影到列空间）、PCA |
| Gram-Schmidt / QR | 数值求解器、特征值计算 |
| 正交规范基 | 稳定的数值计算、白化变换 |

LoRA 值得特别提及。它通过把权重更新分解为低秩矩阵来微调大语言模型。与其更新一个 4096x4096 的权重矩阵（1600 万参数），LoRA 更新两个大小分别为 4096x16 和 16x4096 的矩阵（13.1 万参数）。秩 16 的约束意味着 LoRA 假设权重更新存在于整个 4096 维空间的一个 16 维子空间中。这就是线性代数在真正干活。

## 练习

1. 实现 `Vector.angle_between(other)`，返回两个向量之间以度为单位的角度
2. 创建一个 2D 缩放矩阵，将 x 坐标加倍、y 坐标变为三倍，然后把它应用到向量 [1, 1] 上
3. 给定 5 个随机的类词向量（维度 50），用余弦相似度找出最相似的两个
4. 验证 Gram-Schmidt 的输出确实正交规范：检查每一对点积为 0，且每个向量长度为 1
5. 创建一个秩为 2 的 3x3 矩阵。用 `rank()` 方法验证。然后解释这些列张成什么几何对象。
6. 把向量 [1, 2, 3] 投影到 [1, 1, 1] 上。结果在几何上代表什么？

## 关键术语

| 术语 | 人们的说法 | 它实际的含义 |
|------|----------------|----------------------|
| Vector | 「一个箭头」 | 一个数字列表，代表 n 维空间中的一个点或方向 |
| Matrix | 「一张数字表」 | 一种把向量从一个空间映射到另一个空间的变换 |
| Dot product | 「相乘再求和」 | 衡量两个向量对齐程度的量——相似度搜索的核心 |
| Embedding | 「某种 AI 魔法」 | 表示某物（词、图像、用户）含义的向量 |
| Linear independence | 「它们不重叠」 | 集合中没有任何向量能写成其他向量的组合 |
| Rank | 「有多少维」 | 矩阵中线性无关列（或行）的数量 |
| Projection | 「影子」 | 一个向量在另一个向量方向上的分量 |
| Basis | 「坐标轴」 | 张成整个空间的最小无关向量集 |
| Orthonormal | 「垂直的单位向量」 | 相互垂直且每个长度都为 1 的向量 |
