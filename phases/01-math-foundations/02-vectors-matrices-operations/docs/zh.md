# 向量、矩阵与运算

> 每一个神经网络，本质上都只是多了几步的矩阵乘法。

**Type:** Build
**Languages:** Python, Julia
**Prerequisites:** Phase 1, Lesson 01 (Linear Algebra Intuition)
**Time:** ~60 minutes

## 学习目标

- 构建一个矩阵（Matrix）类，支持逐元素运算、矩阵乘法、转置、行列式和逆矩阵
- 区分逐元素乘法与矩阵乘法，并说明各自适用于什么场景
- 只用从零实现的 Matrix 类实现一个单层全连接网络（`relu(W @ x + b)`）
- 解释广播（broadcasting）规则，以及偏置加法在神经网络框架中的工作原理

## 问题

你想构建一个神经网络。你阅读代码，看到这样一行：

```
output = activation(weights @ input + bias)
```

那个 `@` 就是矩阵乘法。`weights` 是一个矩阵，`input` 是一个向量。如果你不知道这些运算做了什么，这行代码就是魔法；如果你知道，它其实就是一层网络的整个前向传播，浓缩成三个运算。

你的模型处理的每一张图像都是像素值的矩阵。每一个词嵌入都是向量。每一个神经网络的每一层都是一次矩阵变换。你不能在不精通矩阵运算的情况下构建 AI 系统，就像你不能在不理解变量的情况下写代码一样。

本课将帮助你从零建立这种熟练度。

## 概念

### 向量：数字的有序列表

向量是一列带有方向和大小的数字。在 AI 中，向量代表数据点、特征或参数。

```
v = [3, 4]        -- 一个 2D 向量
w = [1, 0, -2]    -- 一个 3D 向量
```

一个 2D 向量 `[3, 4]` 指向平面上的坐标 (3, 4)。它的长度（模长）是 5（3-4-5 三角形）。

### 矩阵：数字的网格

矩阵是一个二维网格，包含行和列。一个 m x n 的矩阵有 m 行和 n 列。

```
A = | 1  2  3 |     -- 2x3 矩阵（2 行，3 列）
    | 4  5  6 |
```

在神经网络中，权重矩阵把输入向量变换为输出向量。一个有 784 个输入、128 个输出的层使用一个 128x784 的权重矩阵。

### 为什么形状（shape）很重要

矩阵乘法有一条严格规则：`(m x n) @ (n x p) = (m x p)`。内部维度必须匹配。

```
(128 x 784) @ (784 x 1) = (128 x 1)
  weights       input       output

内部维度：784 = 784  -- 有效
```

如果你在 PyTorch 里遇到形状不匹配（shape mismatch）的错误，原因就在这里。

### 运算对照表

| 运算 | 它做什么 | 神经网络中的用途 |
|-----------|-------------|-------------------|
| 加法 | 逐元素相加 | 给输出加偏置 |
| 标量乘法 | 缩放每个元素 | 学习率 * 梯度 |
| 矩阵乘法 | 变换向量 | 层的前向传播 |
| 转置 | 交换行和列 | 反向传播 |
| 行列式 | 单个数字的概括 | 检查可逆性 |
| 逆矩阵 | 撤销一次变换 | 求解线性方程组 |
| 单位矩阵 | 什么都不做的矩阵 | 初始化、残差连接 |

### 逐元素乘法 vs 矩阵乘法

这个区别不断让初学者栽跟头。

逐元素乘法：让对应位置相乘。两个矩阵必须有相同的形状。

```
| 1  2 |   | 5  6 |   | 5  12 |
| 3  4 | * | 7  8 | = | 21 32 |
```

矩阵乘法：行与列的点积。内部维度必须匹配。

```
| 1  2 |   | 5  6 |   | 1*5+2*7  1*6+2*8 |   | 19  22 |
| 3  4 | @ | 7  8 | = | 3*5+4*7  3*6+4*8 | = | 43  50 |
```

不同的运算、不同的结果、不同的规则。

### 广播（Broadcasting）

当你把一个偏置向量加到一个输出矩阵上时，两者的形状并不匹配。广播会把较小的数组拉伸到匹配。

```
| 1  2  3 |   +   [10, 20, 30]
| 4  5  6 |

广播会把向量在行方向上拉伸：

| 1  2  3 |   | 10  20  30 |   | 11  22  33 |
| 4  5  6 | + | 10  20  30 | = | 14  25  36 |
```

每一个现代框架都会自动做这件事。理解它，可以避免「形状看似不对但代码却能运行」时的困惑。

```figure
vector-projection
```

## Build It

### 第 1 步：Vector 类

```python
class Vector:
    def __init__(self, data):
        self.data = list(data)
        self.size = len(self.data)

    def __repr__(self):
        return f"Vector({self.data})"

    def __add__(self, other):
        return Vector([a + b for a, b in zip(self.data, other.data)])

    def __sub__(self, other):
        return Vector([a - b for a, b in zip(self.data, other.data)])

    def __mul__(self, scalar):
        return Vector([x * scalar for x in self.data])

    def dot(self, other):
        return sum(a * b for a, b in zip(self.data, other.data))

    def magnitude(self):
        return sum(x ** 2 for x in self.data) ** 0.5
```

### 第 2 步：带核心运算的 Matrix 类

```python
class Matrix:
    def __init__(self, data):
        self.data = [list(row) for row in data]
        self.rows = len(self.data)
        self.cols = len(self.data[0])
        self.shape = (self.rows, self.cols)

    def __repr__(self):
        rows_str = "\n  ".join(str(row) for row in self.data)
        return f"Matrix({self.shape}):\n  {rows_str}"

    def __add__(self, other):
        return Matrix([
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def __sub__(self, other):
        return Matrix([
            [self.data[i][j] - other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def scalar_multiply(self, scalar):
        return Matrix([
            [self.data[i][j] * scalar for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def element_wise_multiply(self, other):
        return Matrix([
            [self.data[i][j] * other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def matmul(self, other):
        return Matrix([
            [
                sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                for j in range(other.cols)
            ]
            for i in range(self.rows)
        ])

    def transpose(self):
        return Matrix([
            [self.data[j][i] for j in range(self.rows)]
            for i in range(self.cols)
        ])

    def determinant(self):
        if self.shape == (1, 1):
            return self.data[0][0]
        if self.shape == (2, 2):
            return self.data[0][0] * self.data[1][1] - self.data[0][1] * self.data[1][0]
        det = 0
        for j in range(self.cols):
            minor = Matrix([
                [self.data[i][k] for k in range(self.cols) if k != j]
                for i in range(1, self.rows)
            ])
            det += ((-1) ** j) * self.data[0][j] * minor.determinant()
        return det

    def inverse_2x2(self):
        det = self.determinant()
        if det == 0:
            raise ValueError("Matrix is singular, no inverse exists")
        return Matrix([
            [self.data[1][1] / det, -self.data[0][1] / det],
            [-self.data[1][0] / det, self.data[0][0] / det]
        ])

    @staticmethod
    def identity(n):
        return Matrix([
            [1 if i == j else 0 for j in range(n)]
            for i in range(n)
        ])
```

### 第 3 步：看看它如何工作

```python
A = Matrix([[1, 2], [3, 4]])
B = Matrix([[5, 6], [7, 8]])

print("A + B =", (A + B).data)
print("A @ B =", A.matmul(B).data)
print("A^T =", A.transpose().data)
print("det(A) =", A.determinant())
print("A^-1 =", A.inverse_2x2().data)

I = Matrix.identity(2)
print("A @ A^-1 =", A.matmul(A.inverse_2x2()).data)
```

### 第 4 步：与神经网络建立联系

```python
import random

inputs = Matrix([[0.5], [0.8], [0.2]])
weights = Matrix([
    [random.uniform(-1, 1) for _ in range(3)]
    for _ in range(2)
])
bias = Matrix([[0.1], [0.1]])

def relu_matrix(m):
    return Matrix([[max(0, val) for val in row] for row in m.data])

pre_activation = weights.matmul(inputs) + bias
output = relu_matrix(pre_activation)

print(f"Input shape: {inputs.shape}")
print(f"Weight shape: {weights.shape}")
print(f"Output shape: {output.shape}")
print(f"Output: {output.data}")
```

这就是一个单层全连接层：`output = relu(W @ x + b)`。每一个神经网络里的每一个全连接层，做的正是这件事。

## Use It

NumPy 用更少的代码、快几个数量级的速度完成上面所有操作。

```python
import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

print("A + B =\n", A + B)
print("A * B (element-wise) =\n", A * B)
print("A @ B (matrix multiply) =\n", A @ B)
print("A^T =\n", A.T)
print("det(A) =", np.linalg.det(A))
print("A^-1 =\n", np.linalg.inv(A))
print("I =\n", np.eye(2))

inputs = np.random.randn(3, 1)
weights = np.random.randn(2, 3)
bias = np.array([[0.1], [0.1]])
output = np.maximum(0, weights @ inputs + bias)

print(f"\nNeural network layer: {weights.shape} @ {inputs.shape} = {output.shape}")
print(f"Output:\n{output}")
```

Python 中的 `@` 运算符会调用 `__matmul__`。NumPy 用 C 和 Fortran 编写的优化 BLAS 例程来实现它。数学是一样的，但快了 100 倍。

NumPy 中的广播：

```python
matrix = np.array([[1, 2, 3], [4, 5, 6]])
bias = np.array([10, 20, 30])
print(matrix + bias)
```

NumPy 会自动把这个 1D 偏置广播到两行上。这就是偏置加法在每一个神经网络框架中的工作方式。

## Ship It

本课产出一个通过几何直觉教授矩阵运算的 prompt。参见 `outputs/prompt-matrix-operations.md`。

这里构建的 Matrix 类，是我们在 Phase 3、Lesson 10 中构建迷你神经网络框架的基础。

## 练习

1. **验证逆矩阵。** 计算 `A @ A.inverse_2x2()`，确认得到单位矩阵。用三个不同的 2x2 矩阵各试一次。当行列式为零时会发生什么？

2. **实现 3x3 逆矩阵。** 扩展 Matrix 类，用伴随矩阵（adjugate）方法计算 3x3 矩阵的逆。用 NumPy 的 `np.linalg.inv` 对照测试。

3. **构建一个两层网络。** 只使用你自己的 Matrix 类（不用 NumPy），创建一个两层神经网络：输入 (3) -> 隐藏层 (4) -> 输出 (2)。初始化随机权重，跑一次前向传播，并验证所有形状都正确。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Vector | “一个箭头” | 一个有序的数字列表。在 AI 中：高维空间中的一个点。 |
| Matrix | “一张数字表” | 一个线性变换。它把向量从一个空间映射到另一个空间。 |
| Matrix multiply | “把数字乘起来就行了” | 第一个矩阵的每一行与第二个矩阵的每一列之间的点积。顺序很重要。 |
| Transpose | “把它翻转” | 交换行和列。把 m x n 矩阵变成 n x m。在反向传播中至关重要。 |
| Determinant | “矩阵算出来的某个数” | 衡量矩阵缩放面积（2D）或体积（3D）的程度。为零意味着该变换把一个维度压扁了。 |
| Inverse | “撤销这个矩阵” | 逆转该变换的矩阵。仅当行列式不为零时才存在。 |
| Identity matrix | “无聊的矩阵” | 相当于乘以 1 的矩阵。用于残差连接（ResNet）。 |
| Broadcasting | “神奇的形状修复” | 通过沿着缺失维度重复，把较小数组拉伸到与较大数组匹配。 |
| Element-wise | “普通乘法” | 让对应位置相乘。两个数组必须有相同形状（或可广播）。 |

## 延伸阅读

- [3Blue1Brown: Essence of Linear Algebra](https://www.3blue1brown.com/topics/linear-algebra) - 对这里每一个运算的几何直觉
- [NumPy documentation on broadcasting](https://numpy.org/doc/stable/user/basics.broadcasting.html) - NumPy 所遵循的确切规则
- [Stanford CS229 Linear Algebra Review](http://cs229.stanford.edu/section/cs229-linalg.pdf) - 面向 ML 的线性代数简明参考
