# 线性方程组

> 求解 Ax = b 是数学中最古老的问题，而它至今仍在驱动你的神经网络。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 01 (Linear Algebra Intuition), 02 (Vectors & Matrices), 03 (Matrix Transformations)
**Time:** ~120 minutes

## 学习目标

- 使用带部分主元的高斯消元法和回代法求解 Ax = b
- 用 LU、QR 和 Cholesky 分解对矩阵进行因式分解，并解释各自适用的情况
- 推导最小二乘的正规方程，并将其与线性回归和岭回归联系起来
- 使用条件数诊断病态方程组，并应用正则化使其稳定

## 问题

每当你训练一个线性回归，你就在求解一个线性方程组。每当你计算最小二乘拟合，你就在求解一个线性方程组。每当一个神经网络层计算 `y = Wx + b`，它就在求值一个线性方程组的一侧。当你加入正则化时，你修改了这个方程组。当你使用高斯过程时，你对矩阵做因式分解。当你为马氏距离求协方差矩阵的逆时，你就在求解一个线性方程组。

方程 Ax = b 无处不在。A 是已知系数的矩阵。b 是已知输出的向量。x 是你要找的未知向量。在线性回归中，A 是你的数据矩阵，b 是你的目标向量，x 是权重向量。整个模型归结为：找到使 Ax 尽可能接近 b 的 x。

本课从头构建求解该方程的每一种主要方法。你会理解为什么有些方法快而另一些稳定，为什么有些只适用于方阵系统而另一些能处理超定系统，以及为什么矩阵的条件数决定了你的答案是否有意义。

## 概念

### Ax = b 的几何意义

线性方程组有几何解释。每个方程定义一个超平面。解是所有超平面相交的点（或点集）。

```
2x + y = 5          二维中的两条直线。
x - y  = 1          它们在 x=2, y=1 处相交。
```

```mermaid
graph LR
    A["2x + y = 5"] --- S["Solution: (2, 1)"]
    B["x - y = 1"] --- S
```

可能发生三种情况：

```mermaid
graph TD
    subgraph "One Solution"
        A1["Lines intersect at a single point"]
    end
    subgraph "No Solution"
        A2["Lines are parallel — no intersection"]
    end
    subgraph "Infinite Solutions"
        A3["Lines are identical — every point is a solution"]
    end
```

用矩阵形式来说，“一个解”意味着 A 可逆。“无解”意味着系统不相容。“无穷多解”意味着 A 有零空间。大多数 ML 问题属于“无精确解”这一类，因为你的方程（数据点）比未知数（参数）多。这正是最小二乘的用武之地。

### 列图景 vs 行图景

阅读 Ax = b 有两种方式。

**行图景。** A 的每一行定义一个方程。每个方程是一个超平面。解是它们全部相交的地方。

**列图景。** A 的每一列是一个向量。问题变成：A 的列的哪种线性组合能产生 b？

```
A = | 2  1 |    b = | 5 |
    | 1 -1 |        | 1 |

行图景：同时解 2x + y = 5 和 x - y = 1。

列图景：找 x1, x2 使得：
  x1 * [2, 1] + x2 * [1, -1] = [5, 1]
  2 * [2, 1] + 1 * [1, -1] = [4+1, 2-1] = [5, 1]   验证。
```

列图景更根本。如果 b 位于 A 的列空间中，系统有解。如果 b 不在，你就找列空间中最近的点。那个最近的点就是最小二乘解。

### 高斯消元法

高斯消元把 Ax = b 变换成上三角系统 Ux = c，然后你通过回代法求解。这是最直接的方法。

算法：

```
1. 对每一列 k（主元列）：
   a. 找到第 k 列中第 k 行及其以下绝对值最大的项（部分主元）。
   b. 把那一行与第 k 行交换。
   c. 对第 k 行以下的每一行 i：
      - 计算乘数 m = A[i][k] / A[k][k]
      - 从第 i 行中减去 m 倍的第 k 行。
2. 回代：从最后一个方程向上求解。
```

示例：

```
原始：
| 2  1  1 | 8 |       R2 = R2 - (2)R1     | 2  1   1 |  8 |
| 4  3  3 |20 |  -->  R3 = R3 - (1)R1 --> | 0  1   1 |  4 |
| 2  3  1 |12 |                            | 0  2   0 |  4 |

                       R3 = R3 - (2)R2     | 2  1   1 |  8 |
                                       --> | 0  1   1 |  4 |
                                           | 0  0  -2 | -4 |

回代：
  -2 * x3 = -4    -->  x3 = 2
  x2 + 2  = 4     -->  x2 = 2
  2*x1 + 2 + 2 = 8 --> x1 = 2
```

高斯消元成本为 O(n^3) 次运算。对于一个 1000x1000 的系统，大约是十亿次浮点运算。很快，但如果你需要用同一个 A 解多个系统，还可以做得更好。

### 部分主元：为什么它重要

没有主元，高斯消元可能失败或产生垃圾结果。如果主元元素为零，你会除以零。如果它很小，你会放大舍入误差。

```
坏主元：                         使用部分主元：
| 0.001  1 | 1.001 |            先交换行：
| 1      1 | 2     |            | 1      1 | 2     |
                                 | 0.001  1 | 1.001 |
m = 1/0.001 = 1000              m = 0.001/1 = 0.001
R2 = R2 - 1000*R1               R2 = R2 - 0.001*R1
| 0.001  1     | 1.001   |      | 1      1     | 2     |
| 0     -999   | -999.0  |      | 0      0.999 | 0.999 |

x2 = 1.000（正确）              x2 = 1.000（正确）
x1 = (1.001 - 1)/0.001          x1 = (2 - 1)/1 = 1.000（正确）
   = 0.001/0.001 = 1.000        稳定，因为乘数很小。
```

在精度有限的浮点运算中，不做主元的版本可能丢失有效数字。部分主元总是选择最大的可用主元，以最小化误差放大。

### LU 分解

LU 分解把 A 分解成下三角矩阵 L 和上三角矩阵 U：A = LU。L 矩阵存储高斯消元的乘数。U 矩阵是消元的结果。

```
A = L @ U

| 2  1  1 |   | 1  0  0 |   | 2  1   1 |
| 4  3  3 | = | 2  1  0 | @ | 0  1   1 |
| 2  3  1 |   | 1  2  1 |   | 0  0  -2 |
```

为什么分解而不是直接消元？因为一旦你有了 L 和 U，对任何新的 b 求解 Ax = b 只花费 O(n^2)：

```
Ax = b
LUx = b
令 y = Ux：
  Ly = b    （前代，O(n^2)）
  Ux = y    （回代，O(n^2)）
```

O(n^3) 的成本在分解时一次性付出。之后每次求解都是 O(n^2)。如果你需要用同一个 A 但不同 b 向量解 1000 个系统，LU 总共节省约 1000/3 倍的工作量。

使用部分主元时，你得到 PA = LU，其中 P 是记录行交换的置换矩阵。

### QR 分解

QR 分解把 A 分解成正交矩阵 Q 和上三角矩阵 R：A = QR。

正交矩阵具有性质 Q^T Q = I。它的列是标准正交向量。乘以 Q 保持长度和角度。

```
A = Q @ R

Q 的列标准正交：Q^T Q = I
R 是上三角矩阵

求解 Ax = b：
  QRx = b
  Rx = Q^T b    （只需乘以 Q^T，无需求逆）
  回代得到 x。
```

对于求解最小二乘问题，QR 比 LU 数值上更稳定。Gram-Schmidt 过程逐列构建 Q：

```
给定 A 的列 a1, a2, ...：

q1 = a1 / ||a1||

q2 = a2 - (a2 . q1) * q1        （减去到 q1 上的投影）
q2 = q2 / ||q2||                （归一化）

q3 = a3 - (a3 . q1) * q1 - (a3 . q2) * q2
q3 = q3 / ||q3||

对 i <= j，R[i][j] = qi . aj
```

每一步移除沿所有先前 q 向量的分量，只留下新的正交方向。

### Cholesky 分解

当 A 对称（A = A^T）且正定（所有特征值为正）时，你可以把它分解为 A = L L^T，其中 L 是下三角矩阵。这就是 Cholesky 分解。

```
A = L @ L^T

| 4  2 |   | 2  0 |   | 2  1 |
| 2  5 | = | 1  2 | @ | 0  2 |

L[i][i] = sqrt(A[i][i] - sum(L[i][k]^2 对 k < i))
对 i > j，L[i][j] = (A[i][j] - sum(L[i][k]*L[j][k] 对 k < j)) / L[j][j]
```

Cholesky 比 LU 快一倍，且只需一半存储。它只适用于对称正定矩阵，但这类矩阵不断出现：

- 协方差矩阵是对称半正定的（加正则化后正定）。
- 高斯过程中的核矩阵是对称正定的。
- 凸函数在最小值处的 Hessian 是对称正定的。
- A^T A 总是对称半正定的。

在高斯过程中，你用 Cholesky 分解核矩阵 K，然后解 K alpha = y 得到预测均值。Cholesky 因子还给你边际似然的 log 行列式：log det(K) = 2 * sum(log(diag(L)))。

### 最小二乘：当 Ax = b 无精确解时

如果 A 是 m x n 且 m > n（方程比未知数多），系统是超定的。没有精确解。相反，你最小化平方误差：

```
最小化 ||Ax - b||^2

这是残差平方和：
  sum((A[i,:] @ x - b[i])^2 对 range(m) 中的 i)
```

极小化器满足正规方程：

```
A^T A x = A^T b
```

推导：展开 ||Ax - b||^2 = (Ax - b)^T (Ax - b) = x^T A^T A x - 2 x^T A^T b + b^T b。对 x 求梯度并令其为零：2 A^T A x - 2 A^T b = 0。

```
原始系统（超定，4 个方程，2 个未知数）：
| 1  1 |         | 3 |
| 1  2 | x     = | 5 |       没有任何 x 能精确满足全部 4 个方程。
| 1  3 |         | 6 |
| 1  4 |         | 8 |

正规方程：
A^T A = | 4  10 |    A^T b = | 22 |
        | 10 30 |            | 63 |

求解：x = [1.5, 1.7]

这就是线性回归。x[0] 是截距，x[1] 是斜率。
```

### 正规方程 = 线性回归

这种联系是精确的。在线性回归中，你的数据矩阵 X 每个样本一行、每个特征一列。你的目标向量 y 每个样本一项。权重向量 w 满足：

```
X^T X w = X^T y
w = (X^T X)^(-1) X^T y
```

这是线性回归的闭式解。每次调用 `sklearn.linear_model.LinearRegression.fit()` 都会计算它（或通过 QR 或 SVD 计算等价结果）。

给矩阵加上一个正则化项 lambda * I，你就得到岭回归：

```
(X^T X + lambda * I) w = X^T y
w = (X^T X + lambda * I)^(-1) X^T y
```

正则化让矩阵条件更好（更容易精确求逆），并通过把权重向零收缩来防止过拟合。当 lambda > 0 时，矩阵 X^T X + lambda * I 总是对称正定的，所以你可以用 Cholesky 求解它。

### 伪逆（Moore-Penrose）

伪逆 A+ 把矩阵求逆推广到非方阵和奇异矩阵。对任何矩阵 A：

```
x = A+ b

其中 A+ = V Sigma+ U^T    （通过 SVD 计算）
```

Sigma+ 通过对每个非零奇异值取倒数并转置结果来构造。如果 A = U Sigma V^T，那么 A+ = V Sigma+ U^T。

```
A = U Sigma V^T        （SVD）

Sigma = | 5  0 |       Sigma+ = | 1/5  0  0 |
        | 0  2 |                | 0  1/2  0 |
        | 0  0 |

A+ = V Sigma+ U^T
```

伪逆给出最小范数最小二乘解。如果系统：
- 有一个解：A+ b 给出它。
- 无解：A+ b 给出最小二乘解。
- 无穷多解：A+ b 给出 ||x|| 最小的那个。

NumPy 的 `np.linalg.lstsq` 和 `np.linalg.pinv` 内部都使用 SVD。

### 条件数

条件数衡量解对输入的微小变化的敏感程度。对矩阵 A，条件数是：

```
kappa(A) = ||A|| * ||A^(-1)|| = sigma_max / sigma_min
```

其中 sigma_max 和 sigma_min 是最大和最小奇异值。

```
良态（kappa ~ 1）：        病态（kappa ~ 10^15）：
b 的微小变化 -->            b 的微小变化 -->
x 的微小变化                x 的巨大变化

| 2  0 |   kappa = 2/1 = 2  | 1   1          |   kappa ~ 10^15
| 0  1 |   求解安全          | 1   1+10^(-15) |   解是垃圾
```

经验法则：
- kappa < 100：安全，解是准确的。
- kappa ~ 10^k：你从浮点运算中损失大约 k 位精度。
- kappa ~ 10^16（对 float64）：解毫无意义。矩阵实际上奇异。

在 ML 中，病态发生在特征近乎共线时。正则化（加 lambda * I）把条件数从 sigma_max / sigma_min 改善为 (sigma_max + lambda) / (sigma_min + lambda)。

### 迭代方法：共轭梯度

对于非常大的稀疏系统（数百万个未知数），像 LU 或 Cholesky 这样的直接方法太昂贵。迭代方法通过多次迭代改进猜测来近似解。

共轭梯度（CG）在 A 对称正定时求解 Ax = b。它至多 n 次迭代（在精确算术中）找到精确解，但如果 A 的特征值聚集，通常收敛得快得多。

```
算法概要：
  x0 = 初始猜测（通常为零）
  r0 = b - A x0           （残差）
  p0 = r0                 （搜索方向）

  对 k = 0, 1, 2, ...：
    alpha = (rk . rk) / (pk . A pk)
    x_{k+1} = xk + alpha * pk
    r_{k+1} = rk - alpha * A pk
    beta = (r_{k+1} . r_{k+1}) / (rk . rk)
    p_{k+1} = r_{k+1} + beta * pk
    如果 ||r_{k+1}|| < 容差：停止
```

CG 用于：
- 大规模优化（Newton-CG 方法）
- 求解 PDE 离散化
- 核矩阵太大而无法分解的核方法
- 其他迭代求解器的预处理

收敛速度取决于条件数。条件更好的系统收敛更快，这也是正则化有帮助的另一个原因。

### 全景：何时用哪种方法

| 方法 | 要求 | 成本 | 用例 |
|--------|-------------|------|----------|
| 高斯消元 | 方阵、非奇异 A | O(n^3) | 一次性求解方阵系统 |
| LU 分解 | 方阵、非奇异 A | O(n^3) 分解 + O(n^2) 求解 | 用同一个 A 多次求解 |
| QR 分解 | 任何 A（m >= n） | O(mn^2) | 最小二乘，数值稳定 |
| Cholesky | 对称正定 A | O(n^3/3) | 协方差矩阵、高斯过程、岭回归 |
| 正规方程 | 超定（m > n） | O(mn^2 + n^3) | 线性回归（n 较小时） |
| SVD / 伪逆 | 任何 A | O(mn^2) | 秩亏系统、最小范数解 |
| 共轭梯度 | 对称正定、稀疏 A | O(n * k * nnz) | 大型稀疏系统，k = 迭代次数 |

### 与 ML 的联系

本课中的每种方法都出现在生产 ML 中：

**线性回归。** 闭式解求解正规方程 X^T X w = X^T y。这通过 Cholesky（如果 n 较小）、QR（如果数值稳定性重要）或 SVD（如果矩阵可能秩亏）完成。

**岭回归。** 给 X^T X 加 lambda * I。正则化系统 (X^T X + lambda * I) w = X^T y 总是能用 Cholesky 求解，因为对 lambda > 0，X^T X + lambda * I 对称正定。

**高斯过程。** 预测均值需要解 K alpha = y，其中 K 是核矩阵。K 的 Cholesky 分解是标准方法。log 边际似然使用 log det(K) = 2 sum(log(diag(L)))。

**神经网络初始化。** 正交初始化使用 QR 分解创建列为标准正交的权重矩阵。这防止深度网络中的信号崩溃。

**预处理。** 大规模优化器使用不完全 Cholesky 或不完全 LU 作为共轭梯度求解器的预处理器。

**特征工程。** X^T X 的条件数告诉你特征是否共线。如果 kappa 很大，丢弃特征或加正则化。

```figure
linear-system-conditioning
```

## Build It

### 第 1 步：带部分主元的高斯消元

```python
import numpy as np

def gaussian_elimination(A, b):
    n = len(b)
    Ab = np.hstack([A.astype(float), b.reshape(-1, 1).astype(float)])

    for k in range(n):
        max_row = k + np.argmax(np.abs(Ab[k:, k]))
        Ab[[k, max_row]] = Ab[[max_row, k]]

        if abs(Ab[k, k]) < 1e-12:
            raise ValueError(f"Matrix is singular or nearly singular at pivot {k}")

        for i in range(k + 1, n):
            m = Ab[i, k] / Ab[k, k]
            Ab[i, k:] -= m * Ab[k, k:]

    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (Ab[i, -1] - Ab[i, i+1:n] @ x[i+1:n]) / Ab[i, i]

    return x
```

### 第 2 步：LU 分解

```python
def lu_decompose(A):
    n = A.shape[0]
    L = np.eye(n)
    U = A.astype(float).copy()
    P = np.eye(n)

    for k in range(n):
        max_row = k + np.argmax(np.abs(U[k:, k]))
        if max_row != k:
            U[[k, max_row]] = U[[max_row, k]]
            P[[k, max_row]] = P[[max_row, k]]
            if k > 0:
                L[[k, max_row], :k] = L[[max_row, k], :k]

        for i in range(k + 1, n):
            L[i, k] = U[i, k] / U[k, k]
            U[i, k:] -= L[i, k] * U[k, k:]

    return P, L, U

def lu_solve(P, L, U, b):
    n = len(b)
    Pb = P @ b.astype(float)

    y = np.zeros(n)
    for i in range(n):
        y[i] = Pb[i] - L[i, :i] @ y[:i]

    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - U[i, i+1:] @ x[i+1:]) / U[i, i]

    return x
```

### 第 3 步：Cholesky 分解

```python
def cholesky(A):
    n = A.shape[0]
    L = np.zeros_like(A, dtype=float)

    for i in range(n):
        for j in range(i + 1):
            s = A[i, j] - L[i, :j] @ L[j, :j]
            if i == j:
                if s <= 0:
                    raise ValueError("Matrix is not positive definite")
                L[i, j] = np.sqrt(s)
            else:
                L[i, j] = s / L[j, j]

    return L
```

### 第 4 步：通过正规方程做最小二乘

```python
def least_squares_normal(A, b):
    AtA = A.T @ A
    Atb = A.T @ b
    return gaussian_elimination(AtA, Atb)

def ridge_regression(A, b, lam):
    n = A.shape[1]
    AtA = A.T @ A + lam * np.eye(n)
    Atb = A.T @ b
    L = cholesky(AtA)
    y = np.zeros(n)
    for i in range(n):
        y[i] = (Atb[i] - L[i, :i] @ y[:i]) / L[i, i]
    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - L.T[i, i+1:] @ x[i+1:]) / L.T[i, i]
    return x
```

### 第 5 步：条件数

```python
def condition_number(A):
    U, S, Vt = np.linalg.svd(A)
    return S[0] / S[-1]
```

## Use It

把各个部分拼起来，在真实数据上做线性回归和岭回归：

```python
np.random.seed(42)
X_raw = np.random.randn(100, 3)
w_true = np.array([2.0, -1.0, 0.5])
y = X_raw @ w_true + np.random.randn(100) * 0.1

X = np.column_stack([np.ones(100), X_raw])

w_ols = least_squares_normal(X, y)
print(f"OLS weights (ours):    {w_ols}")

w_np = np.linalg.lstsq(X, y, rcond=None)[0]
print(f"OLS weights (numpy):   {w_np}")
print(f"Max difference: {np.max(np.abs(w_ols - w_np)):.2e}")

w_ridge = ridge_regression(X, y, lam=1.0)
print(f"Ridge weights (ours):  {w_ridge}")

from sklearn.linear_model import Ridge
ridge_sk = Ridge(alpha=1.0, fit_intercept=False)
ridge_sk.fit(X, y)
print(f"Ridge weights (sklearn): {ridge_sk.coef_}")
```

## Ship It

本课产出：
- `code/linear_systems.py`，包含高斯消元、LU 分解、Cholesky 分解、最小二乘和岭回归的从零实现
- 一个展示正规方程与 sklearn 的 LinearRegression 产生相同权重的可运行演示

## 练习

1. 用你的高斯消元、你的 LU 求解器以及 `np.linalg.solve` 求解系统 `[[1,2,3],[4,5,6],[7,8,10]] x = [6, 15, 27]`。验证三者给出的答案在浮点容差内一致。

2. 生成一个 50x5 的随机矩阵 X 和目标 y = X @ w_true + noise。分别用正规方程、QR（通过 `np.linalg.qr`）、SVD（通过 `np.linalg.svd`）和 `np.linalg.lstsq` 求解 w。比较这四种解。测量 X^T X 的条件数并解释它如何影响你信任哪种方法。

3. 让两列几乎相同（例如，列 2 = 列 1 + 1e-10 * 噪声），创建一个近乎奇异的矩阵。计算它的条件数。用和不带正则化（加 0.01 * I）分别求解 Ax = b。比较解和残差。解释为什么正则化有帮助。

4. 对一个 100x100 的随机对称正定矩阵实现共轭梯度算法。统计它收敛到容差 1e-8 需要多少次迭代。与 n 次迭代的理论上限比较。

5. 在大小为 10、50、200、500 的对称正定矩阵上，计时你的 Cholesky 求解器 vs 你的 LU 求解器 vs `np.linalg.solve`。绘制结果。验证 Cholesky 大约比 LU 快 2 倍。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Linear system | “求解 x” | 一组线性方程 Ax = b。求 x 意味着找到在变换 A 下产生输出 b 的输入。 |
| Gaussian elimination | “行化简” | 用行运算系统地消去对角线以下的项，产生一个可通过回代求解的上三角系统。O(n^3)。 |
| Partial pivoting | “交换行以保证稳定” | 在消去第 k 列之前，把该列中绝对值最大的行交换到主元位置。防止除以小数。 |
| LU decomposition | “分解成三角形” | 把 A 写成 A = LU，其中 L 下三角（存储乘数）、U 上三角（消元后的矩阵）。把 O(n^3) 成本分摊到多次求解。 |
| QR decomposition | “正交分解” | 把 A 写成 A = QR，其中 Q 列标准正交、R 上三角。对最小二乘比 LU 更稳定。 |
| Cholesky decomposition | “矩阵的平方根” | 对对称正定 A，写成 A = LL^T。成本是 LU 的一半。用于协方差矩阵、核矩阵和岭回归。 |
| Least squares | “精确不可能时的最佳拟合” | 当系统超定（方程比未知数多）时，最小化残差平方和 ||Ax - b||^2。 |
| Normal equations | “微积分捷径” | A^T A x = A^T b。令 ||Ax - b||^2 的梯度为零。这就是线性回归的闭式解。 |
| Pseudoinverse | “非方阵的求逆” | 通过 SVD 得到 A+ = V Sigma+ U^T。对任何矩阵（方或非方、奇异或非奇异）给出最小范数最小二乘解。 |
| Condition number | “这个答案有多可信” | kappa = sigma_max / sigma_min。衡量对输入扰动的敏感度。损失约 log10(kappa) 位精度。 |
| Ridge regression | “正则化最小二乘” | 解 (X^T X + lambda I) w = X^T y。加 lambda I 改善条件数并把权重向零收缩。防止过拟合。 |
| Conjugate gradient | “大矩阵的迭代 Ax=b” | 对称正定系统的迭代求解器。至多 n 步收敛。对分解太昂贵的大型稀疏系统实用。 |
| Overdetermined system | “数据多于参数” | m x n 系统中 m > n。不存在精确解。最小二乘找到最佳近似。这就是每一个回归问题。 |
| Back substitution | “自下而上求解” | 给定上三角系统，先解最后一个方程，然后回代。O(n^2)。 |
| Forward substitution | “自上而下求解” | 给定下三角系统，先解第一个方程，然后前代。O(n^2)。用于 LU 求解的 L 步骤。 |

## 延伸阅读

- [MIT 18.06: Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)（Gilbert Strang）—— 关于线性方程组和矩阵分解的权威课程
- [Numerical Linear Algebra](https://people.maths.ox.ac.uk/trefethen/text.html)（Trefethen & Bau）—— 理解数值稳定性、条件数以及算法为何失败的标准参考
- [Matrix Computations](https://www.press.jhu.edu/books/title/10678/matrix-computations)（Golub & Van Loan）—— 每个矩阵算法的百科全书式参考
- [3Blue1Brown: Inverse Matrices](https://www.3blue1brown.com/lessons/inverse-matrices) —— 求解 Ax = b 几何意义的视觉直觉