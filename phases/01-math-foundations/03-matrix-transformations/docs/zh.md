# 矩阵变换

> 矩阵是一台重塑空间的机器。弄懂它对每一个点做了什么，你就理解了整个变换。

**Type:** Build
**Languages:** Python, Julia
**Prerequisites:** Phase 1, Lessons 01-02 (Linear Algebra Intuition, Vectors & Matrices Operations)
**Time:** ~75 minutes

## 学习目标

- 构造旋转、缩放、剪切和反射矩阵，并将它们应用到 2D 和 3D 点上
- 通过矩阵乘法组合多个变换，并验证顺序确实重要
- 从特征方程计算 2x2 矩阵的特征值和特征向量
- 解释为什么特征值决定了 PCA 方向、RNN 稳定性以及谱聚类行为

## 问题

你阅读关于 PCA 的内容，看到「找出协方差矩阵的特征向量」。你阅读关于模型稳定性的内容，看到「检查是否所有特征值的模都小于 1」。你阅读关于数据增强的内容，看到「应用一个随机旋转」。在你理解矩阵对空间在几何上做了什么之前，这些都毫无意义。

矩阵不只是数字的网格。它们是空间机器。旋转矩阵转动点，缩放矩阵拉伸它们，剪切矩阵倾斜它们。神经网络对数据施加的每一个变换，都是这些运算之一或它们的组合。本课让这些运算变得具体。

## 概念

### 作为矩阵的变换

2D 中的每一个线性变换都可以写成一个 2x2 矩阵。矩阵精确地告诉你基向量 [1, 0] 和 [0, 1] 最终落在哪里。其余一切都随之确定。

```mermaid
graph LR
    subgraph Before["Standard Basis"]
        e1["e1 = [1, 0] (along x)"]
        e2["e2 = [0, 1] (along y)"]
    end
    subgraph Transform["Matrix M"]
        M["M = columns are new basis vectors"]
    end
    subgraph After["After Transformation M"]
        e1p["e1' = new x-basis"]
        e2p["e2' = new y-basis"]
    end
    e1 --> M --> e1p
    e2 --> M --> e2p
```

### 旋转

按角度 theta 的 2D 旋转会保持距离和角度不变。它让每个点沿圆弧移动。

```mermaid
graph LR
    subgraph Before["Before Rotation"]
        A["A(2, 1)"]
        B["B(0, 2)"]
    end
    subgraph Rot["Rotate 45 degrees"]
        R["R(θ) = [[cos θ, -sin θ], [sin θ, cos θ]]"]
    end
    subgraph After["After Rotation"]
        Ap["A'(0.71, 2.12)"]
        Bp["B'(-1.41, 1.41)"]
    end
    A --> R --> Ap
    B --> R --> Bp
```

在 3D 中，你绕着某条轴旋转。每条轴都有自己的旋转矩阵：

```
Rz(theta) = | cos  -sin  0 |     Rotate around z-axis
            | sin   cos  0 |     (x-y plane spins, z stays)
            |  0     0   1 |

Rx(theta) = | 1   0     0    |   Rotate around x-axis
            | 0  cos  -sin   |   (y-z plane spins, x stays)
            | 0  sin   cos   |

Ry(theta) = |  cos  0  sin |     Rotate around y-axis
            |   0   1   0  |     (x-z plane spins, y stays)
            | -sin  0  cos |
```

### 缩放

缩放沿每条轴独立地拉伸或压缩。

```mermaid
graph LR
    subgraph Before["Before Scaling"]
        A["A(2, 1)"]
        B["B(0, 2)"]
    end
    subgraph Scale["Scale sx=2, sy=0.5"]
        S["S = [[2, 0], [0, 0.5]]"]
    end
    subgraph After["After Scaling"]
        Ap["A'(4, 0.5)"]
        Bp["B'(0, 1)"]
    end
    A --> S --> Ap
    B --> S --> Bp
```

### 剪切

剪切倾斜一条轴，同时保持另一条轴不动。它把矩形变成平行四边形。

```mermaid
graph LR
    subgraph Before["Before Shear"]
        A["A(1, 0)"]
        B["B(0, 1)"]
    end
    subgraph Shear["Shear in x, k=1"]
        Sh["Shx = [[1, k], [0, 1]]"]
    end
    subgraph After["After Shear"]
        Ap["A(1, 0) unchanged"]
        Bp["B'(1, 1) shifted"]
    end
    A --> Sh --> Ap
    B --> Sh --> Bp
```

剪切矩阵：

- `Shx = [[1, k], [0, 1]]` 把 x 偏移 k * y
- `Shy = [[1, 0], [k, 1]]` 把 y 偏移 k * x

### 反射

反射把点关于某条轴或直线做镜像。

```mermaid
graph LR
    subgraph Before["Before Reflection"]
        A["A(2, 1)"]
    end
    subgraph Reflect["Reflect across y-axis"]
        R["[[-1, 0], [0, 1]]"]
    end
    subgraph After["After Reflection"]
        Ap["A'(-2, 1)"]
    end
    A --> R --> Ap
```

反射矩阵：

- 关于 y 轴反射：`[[-1, 0], [0, 1]]`
- 关于 x 轴反射：`[[1, 0], [0, -1]]`

### 组合：链式变换

先应用变换 A 再应用变换 B，等同于把它们的矩阵相乘：`result = B @ A @ point`。顺序很重要。先旋转再缩放，与先缩放再旋转，结果不同。

```mermaid
graph LR
    subgraph Path1["Rotate 90 then Scale (2, 0.5)"]
        P1["(1, 0)"] -->|"Rotate 90"| P2["(0, 1)"] -->|"Scale"| P3["(0, 0.5)"]
    end
```

组合结果：`S @ R = [[0, -2], [0.5, 0]]`

```mermaid
graph LR
    subgraph Path2["Scale (2, 0.5) then Rotate 90"]
        Q1["(1, 0)"] -->|"Scale"| Q2["(2, 0)"] -->|"Rotate 90"| Q3["(0, 2)"]
    end
```

组合结果：`R @ S = [[0, -0.5], [2, 0]]`

结果不同。矩阵乘法不可交换（non-commutative）。

### 特征值与特征向量

大多数向量在矩阵作用后会改变方向。特征向量是特殊的：矩阵只缩放它们，从不旋转它们。这个缩放因子就是特征值。

```
A @ v = lambda * v

v 是特征向量（存活下来的方向）
lambda 是特征值（它拉伸的程度）

示例：A = | 2  1 |
         | 1  2 |

特征值 3 对应的特征向量 [1, 1]：
  A @ [1,1] = [3, 3] = 3 * [1, 1]     （方向不变，被缩放 3 倍）

特征值 1 对应的特征向量 [1, -1]：
  A @ [1,-1] = [1, -1] = 1 * [1, -1]  （方向不变，未改变）
```

该矩阵沿着 [1, 1] 把空间拉伸 3 倍，并保持 [1, -1] 不变。其他所有方向都是这两个方向的混合。

### 特征分解

如果一个矩阵有 n 个线性无关的特征向量，它就可以被分解：

```
A = V @ D @ V^(-1)

V = 列向量为特征向量的矩阵
D = 特征值构成的对角矩阵
V^(-1) = V 的逆矩阵

这说的是：旋转到特征向量坐标系，沿每条轴缩放，再旋转回来。
```

### 为什么特征值很重要

**PCA。** 协方差矩阵的特征向量就是主成分。特征值告诉你每个成分捕获了多少方差。按特征值排序，保留前 k 个，你就得到了降维。

**稳定性。** 在循环网络和动态系统中，模大于 1 的特征值会导致输出爆炸；模小于 1 会导致输出消失。这就是梯度消失/爆炸问题用一句话概括。

**谱方法。** 图神经网络使用邻接矩阵的特征值。谱聚类使用拉普拉斯矩阵的特征值。特征向量揭示了图的结构。

### 作为体积缩放因子的行列式

变换矩阵的行列式告诉你它缩放面积（2D）或体积（3D）的程度。

```
det = 1:   面积保持（旋转）
det = 2:   面积翻倍
det = 0:   空间被压到更低维度（奇异）
det = -1:  面积保持但方向翻转（反射）

| det(Rotation) | = 1        （恒为）
| det(Scale sx, sy) | = sx * sy
| det(Shear) | = 1           （面积保持）
| det(Reflection) | = -1     （方向翻转）
```

```figure
matrix-transform
```

## Build It

### 第 1 步：从零构造变换矩阵（Python）

```python
import math

def rotation_2d(theta):
    c, s = math.cos(theta), math.sin(theta)
    return [[c, -s], [s, c]]

def scaling_2d(sx, sy):
    return [[sx, 0], [0, sy]]

def shearing_2d(kx, ky):
    return [[1, kx], [ky, 1]]

def reflection_x():
    return [[1, 0], [0, -1]]

def reflection_y():
    return [[-1, 0], [0, 1]]

def mat_vec_mul(matrix, vector):
    return [
        sum(matrix[i][j] * vector[j] for j in range(len(vector)))
        for i in range(len(matrix))
    ]

def mat_mul(a, b):
    rows_a, cols_b = len(a), len(b[0])
    cols_a = len(a[0])
    return [
        [sum(a[i][k] * b[k][j] for k in range(cols_a)) for j in range(cols_b)]
        for i in range(rows_a)
    ]

point = [1.0, 0.0]
angle = math.pi / 4

rotated = mat_vec_mul(rotation_2d(angle), point)
print(f"Rotate (1,0) by 45 deg: ({rotated[0]:.4f}, {rotated[1]:.4f})")

scaled = mat_vec_mul(scaling_2d(2, 3), [1.0, 1.0])
print(f"Scale (1,1) by (2,3): ({scaled[0]:.1f}, {scaled[1]:.1f})")

sheared = mat_vec_mul(shearing_2d(1, 0), [1.0, 1.0])
print(f"Shear (1,1) kx=1: ({sheared[0]:.1f}, {sheared[1]:.1f})")

reflected = mat_vec_mul(reflection_y(), [2.0, 1.0])
print(f"Reflect (2,1) across y: ({reflected[0]:.1f}, {reflected[1]:.1f})")
```

### 第 2 步：变换的组合

```python
R = rotation_2d(math.pi / 2)
S = scaling_2d(2, 0.5)

rotate_then_scale = mat_mul(S, R)
scale_then_rotate = mat_mul(R, S)

point = [1.0, 0.0]
result1 = mat_vec_mul(rotate_then_scale, point)
result2 = mat_vec_mul(scale_then_rotate, point)

print(f"Rotate 90 then scale: ({result1[0]:.2f}, {result1[1]:.2f})")
print(f"Scale then rotate 90: ({result2[0]:.2f}, {result2[1]:.2f})")
print(f"Same? {result1 == result2}")
```

### 第 3 步：从零计算特征值（2x2）

对于 2x2 矩阵 `[[a, b], [c, d]]`，特征值解特征方程：`lambda^2 - (a+d)*lambda + (ad - bc) = 0`。

```python
def eigenvalues_2x2(matrix):
    a, b = matrix[0]
    c, d = matrix[1]
    trace = a + d
    det = a * d - b * c
    discriminant = trace ** 2 - 4 * det
    if discriminant < 0:
        real = trace / 2
        imag = (-discriminant) ** 0.5 / 2
        return (complex(real, imag), complex(real, -imag))
    sqrt_disc = discriminant ** 0.5
    return ((trace + sqrt_disc) / 2, (trace - sqrt_disc) / 2)

def eigenvector_2x2(matrix, eigenvalue):
    a, b = matrix[0]
    c, d = matrix[1]
    if abs(b) > 1e-10:
        v = [b, eigenvalue - a]
    elif abs(c) > 1e-10:
        v = [eigenvalue - d, c]
    else:
        if abs(a - eigenvalue) < 1e-10:
            v = [1, 0]
        else:
            v = [0, 1]
    mag = (v[0] ** 2 + v[1] ** 2) ** 0.5
    return [v[0] / mag, v[1] / mag]

A = [[2, 1], [1, 2]]
vals = eigenvalues_2x2(A)
print(f"Matrix: {A}")
print(f"Eigenvalues: {vals[0]:.4f}, {vals[1]:.4f}")

for val in vals:
    vec = eigenvector_2x2(A, val)
    result = mat_vec_mul(A, vec)
    scaled = [val * vec[0], val * vec[1]]
    print(f"  lambda={val:.1f}, v={[round(x,4) for x in vec]}")
    print(f"    A@v = {[round(x,4) for x in result]}")
    print(f"    l*v = {[round(x,4) for x in scaled]}")
```

### 第 4 步：作为体积缩放因子的行列式

```python
def det_2x2(matrix):
    return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]

print(f"det(rotation 45) = {det_2x2(rotation_2d(math.pi/4)):.4f}")
print(f"det(scale 2,3)   = {det_2x2(scaling_2d(2, 3)):.1f}")
print(f"det(shear kx=1)  = {det_2x2(shearing_2d(1, 0)):.1f}")
print(f"det(reflect y)   = {det_2x2(reflection_y()):.1f}")

singular = [[1, 2], [2, 4]]
print(f"det(singular)     = {det_2x2(singular):.1f}")
print("Singular: columns are proportional, space collapses to a line.")
```

## Use It

NumPy 用优化例程处理所有这一切。

```python
import numpy as np

theta = np.pi / 4
R = np.array([[np.cos(theta), -np.sin(theta)],
              [np.sin(theta),  np.cos(theta)]])

point = np.array([1.0, 0.0])
print(f"Rotate (1,0) by 45 deg: {R @ point}")

S = np.diag([2.0, 3.0])
composed = S @ R
print(f"Scale(2,3) after Rotate(45): {composed @ point}")

A = np.array([[2, 1], [1, 2]], dtype=float)
eigenvalues, eigenvectors = np.linalg.eig(A)
print(f"\nEigenvalues: {eigenvalues}")
print(f"Eigenvectors (columns):\n{eigenvectors}")

for i in range(len(eigenvalues)):
    v = eigenvectors[:, i]
    lam = eigenvalues[i]
    print(f"  A @ v{i} = {A @ v}, lambda * v{i} = {lam * v}")

print(f"\ndet(R) = {np.linalg.det(R):.4f}")
print(f"det(S) = {np.linalg.det(S):.1f}")

B = np.array([[3, 1], [0, 2]], dtype=float)
vals, vecs = np.linalg.eig(B)
D = np.diag(vals)
V = vecs
reconstructed = V @ D @ np.linalg.inv(V)
print(f"\nEigendecomposition A = V @ D @ V^-1:")
print(f"Original:\n{B}")
print(f"Reconstructed:\n{reconstructed}")
```

### 用 NumPy 做 3D 旋转

```python
def rotation_3d_z(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def rotation_3d_x(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

point_3d = np.array([1.0, 0.0, 0.0])
rotated_z = rotation_3d_z(np.pi / 2) @ point_3d
rotated_x = rotation_3d_x(np.pi / 2) @ point_3d

print(f"\n3D point: {point_3d}")
print(f"Rotate 90 around z: {np.round(rotated_z, 4)}")
print(f"Rotate 90 around x: {np.round(rotated_x, 4)}")
```

## Ship It

本课为 PCA（Phase 2）和神经网络权重分析奠定了几何基础。这里构建的特征值/特征向量代码，正是驱动生产 ML 系统中降维、谱聚类和稳定性分析的同一套算法。

## 练习

1. 对单位正方形（四个角在 [0,0]、[1,0]、[1,1]、[0,1]）应用旋转、缩放和剪切。对每种变换打印变换后的角点。验证旋转保持角点之间的距离不变。

2. 用特征方程手工求出矩阵 [[4, 2], [1, 3]] 的特征值。然后用你的从零函数和 NumPy 验证。

3. 创建一个包含三个变换的组合（旋转 30 度、按 [1.5, 0.8] 缩放、以 kx=0.3 剪切），并将其应用到排列成圆的 8 个点上。打印变换前后的坐标。计算组合矩阵的行列式，验证它等于各变换行列式的乘积。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Rotation matrix | “转动东西” | 一个正交矩阵，让点沿圆弧移动，同时保持距离和角度。行列式恒为 1。 |
| Scaling matrix | “让东西变大” | 一个对角矩阵，沿每条轴独立地拉伸或压缩。行列式是各缩放因子的乘积。 |
| Shearing matrix | “让东西倾斜” | 一个使一个坐标随另一个坐标按比例偏移的矩阵，把矩形变成平行四边形。行列式为 1。 |
| Reflection | “镜像东西” | 一个让空间关于某条轴或平面翻转的矩阵。行列式为 -1。 |
| Composition | “做两件事” | 把变换矩阵相乘以链式组合运算。顺序很重要：B @ A 表示先应用 A，再应用 B。 |
| Eigenvector | “特殊方向” | 矩阵只缩放、从不旋转的方向。是变换的指纹。 |
| Eigenvalue | “它拉伸了多少” | 矩阵缩放其特征向量的标量因子。可以为负（翻转）或为复数（旋转）。 |
| Eigendecomposition | “把矩阵拆开” | 把矩阵写成 V @ D @ V^(-1)，将其分解为基本缩放方向和大小。 |
| Determinant | “矩阵算出的单个数字” | 变换缩放面积（2D）或体积（3D）的因子。为零意味着变换不可逆。 |
| Characteristic equation | “特征值的来源” | det(A - lambda * I) = 0。根为特征值的多项式。 |

## 延伸阅读

- [3Blue1Brown: Linear Transformations](https://www.3blue1brown.com/lessons/linear-transformations) -- 矩阵如何重塑空间的视觉直觉
- [3Blue1Brown: Eigenvectors and Eigenvalues](https://www.3blue1brown.com/lessons/eigenvalues) -- 对特征向量几何含义的最佳视觉解释
- [MIT 18.06 Lecture 21: Eigenvalues and Eigenvectors](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/) -- Gilbert Strang 的经典讲解
